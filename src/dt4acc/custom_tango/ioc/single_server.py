#!/usr/bin/env python3
"""
single_server.py
================

Entry point for each Tango server process.

Responsibilities
----------------
1. Connect to MexecService via multiprocessing.managers and get a SyncMexecProxy.
2. Wrap it in AsyncMexecAdapter so Tango devices and TangoController can
   `await mexec.set()` / `await mexec.trigger_read()` as if mexec were local.
3. Build a TangoController and store it in a process-global so device
   write-handlers can reach it via get_controller().
4. Call tango.server.run() which blocks until the server exits.
"""

import asyncio
import importlib
import getpass
import logging
import os
import sys
from typing import Sequence

# Suppress transitions state machine INFO logs — they fire on every
# backend.set() call and flood the output (4 lines per state transition)
logging.getLogger("transitions").setLevel(logging.WARNING)
logging.getLogger("transitions.core").setLevel(logging.WARNING)

from dt4acc_lib.model.output.result import TranslatedReading, ReadTogetherAndTranslated, SingleReading
from dt4acc_lib.model.utils.command import ReadCommand, Command
from tango.server import run

from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_tango.ioc.controller_registry import set_controller
from dt4acc.custom_tango.ioc.tango_controller import TangoController, DEFAULT_DELAYED_READS

logger = get_logger()


# ---------------------------------------------------------------------------
# AsyncMexecAdapter — makes SyncMexecProxy look async to TangoController
# ---------------------------------------------------------------------------

class AsyncMexecAdapter:
    """
    Wraps the synchronous multiprocessing proxy (SyncMexecProxy) and exposes
    the async interface that TangoController expects:
        await mexec.set([cmd])
        await mexec.trigger_read([rcmd, ...])

    The sync calls run in a thread-pool executor so they don't block the
    asyncio event loop while waiting for the service process to respond.
    """

    def __init__(self, sync_proxy):
        self._proxy = sync_proxy

    async def set(self, cmds: Sequence[Command]) -> None:
        loop = asyncio.get_running_loop()
        for cmd in cmds:
            # Use lambda to capture args explicitly — multiprocessing.managers
            # proxy methods don't accept positional args via run_in_executor
            _id, _prop, _val = cmd.id, cmd.property, cmd.value
            await loop.run_in_executor(
                None,
                lambda: self._proxy.sync_set(_id, _prop, _val),
            )

    async def reference_frequency(self) -> float:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._proxy.sync_reference_frequency(),
        )

    async def trigger_read(self, rcmds: Sequence[ReadCommand]) -> ReadTogetherAndTranslated:
        loop = asyncio.get_running_loop()
        ids   = [r.id for r in rcmds]
        props = [r.property for r in rcmds]

        raw = await loop.run_in_executor(
            None,
            lambda: self._proxy.sync_trigger_read(ids, props),
        )
        # raw is list of (rcmd_id, rcmd_property, payload) tuples
        # Reconstruct ReadTogetherAndTranslated for TangoController.view.dispatch()
        import datetime
        now = datetime.datetime.now()

        # Group by (id, property) — one TranslatedReading per ReadCommand
        from collections import defaultdict
        groups = defaultdict(list)
        for rcmd_id, rcmd_prop, payload in raw:
            groups[(rcmd_id, rcmd_prop)].append(
                SingleReading(
                    name=f"{rcmd_id}-{rcmd_prop}",
                    payload=payload,
                    cmd=ReadCommand(id=rcmd_id, property=rcmd_prop),
                )
            )

        data = [
            TranslatedReading(
                cmd=ReadCommand(id=k[0], property=k[1]),
                readings=readings,
            )
            for k, readings in groups.items()
        ]
        return ReadTogetherAndTranslated(data=data, start=now, end=now)


# Process-global cache: element id → {property: value}
# Populated by _preload_initial_values() before init_device() runs.
# Re-populated by refresh_cache_from_lattice() after reset.
_initial_strength_cache: dict = {}  # uuid → float (main_strength)
_nominal_cache: dict = {}           # element id → {property: value}
_static_nominal_cache: dict = {}    # values derived without backend RPC
_my_magnet_uuids: list = []         # UUIDs of magnets in this server process
_my_nominal_reads: dict = {}        # element id → set[property]
_sync_proxy = None                  # MexecService proxy for live reads
_device_view = False                # True only for device-view facilities (e.g. MAX IV)

_PROPERTIES_BY_DEVICE_TYPE = {
    "Quadrupole": ("main_strength",),
    "Sextupole": ("main_strength",),
    "Octupole": ("main_strength",),
    "Multipole": ("main_strength",),
    "Bend": ("main_strength",),
    "Steerer": ("x_kick", "y_kick"),
    "SkewQuadrupole": ("skew_quad_strength",),
    "RFCavity": ("frequency", "voltage"),
}


def enable_device_view_readback() -> None:
    """Call from facility startup script to enable live AT readback on polling.
    Must be called before tango.server.run() — e.g. in run_maxiv_r1_twin.py.
    In design view (SOLEIL) this is never called so peek_from_lattice returns 0.0.
    """
    global _device_view
    _device_view = True


def peek_from_lattice(element_id: str, prop: str) -> float:
    """Live read of a single element property from AT via MexecService.
    Only active in device view (MAX IV). Returns 0.0 in design view (SOLEIL)
    so the cached value is kept unchanged — no regression for SOLEIL.
    """
    global _sync_proxy, _device_view
    if not _device_view or _sync_proxy is None:
        return 0.0
    try:
        return _sync_proxy.sync_peek(element_id, prop)
    except Exception:
        return 0.0


def get_initial_strength(uuid: str) -> float:
    """Called by MagnetDevice.init_device() to get cached initial value."""
    return get_initial_value(uuid, "main_strength")


def get_initial_value(element_id: str, property_name: str, default: float = 0.0) -> float:
    """Called by Tango devices to get cached initial values."""
    try:
        return float(_nominal_cache.get(element_id, {}).get(property_name, default))
    except (TypeError, ValueError):
        return default


def get_nominal_values(uuid: str) -> dict:
    """Called by MagnetDevice.RefreshFromCache() after reset."""
    return _nominal_cache.get(
        uuid,
        {
            "main_strength": 0.0,
            "x_kick": 0.0,
            "y_kick": 0.0,
            "skew_quad_strength": 0.0,
            "frequency": 0.0,
            "voltage": 0.0,
            "reference_frequency": 0.0,
        },
    )


def refresh_nominal_values(element_id: str, properties: Sequence[str]) -> dict:
    """Refresh this server process cache for one element from the backend."""
    if _sync_proxy is None:
        return get_nominal_values(element_id)
    id_to_properties = {element_id: set(properties)}
    values = _read_values_from_lattice(_sync_proxy, id_to_properties)
    _nominal_cache.setdefault(element_id, {}).update(values.get(element_id, {}))
    return get_nominal_values(element_id)


def _read_values_from_lattice(sync_proxy, id_to_properties: dict) -> dict:
    new_cache = {
        element_id: {prop: 0.0 for prop in properties}
        for element_id, properties in id_to_properties.items()
    }
    properties = sorted({prop for props in id_to_properties.values() for prop in props})
    for prop in properties:
        ids = [
            element_id
            for element_id, props in id_to_properties.items()
            if prop in props and element_id != "master_clock"
        ]
        if not ids:
            continue
        try:
            raw = sync_proxy.sync_trigger_read(ids, [prop] * len(ids))
            for rcmd_id, rcmd_prop, payload in raw:
                if payload is None or rcmd_id not in new_cache:
                    continue
                try:
                    new_cache[rcmd_id][rcmd_prop] = float(payload)
                except (TypeError, ValueError):
                    pass
        except Exception as exc:
            logger.warning("refresh_cache_from_lattice: %s failed: %s", prop, exc)
    for element_id, values in _static_nominal_cache.items():
        new_cache.setdefault(element_id, {}).update(values)
    return new_cache


def refresh_cache_from_lattice(sync_proxy, id_to_properties) -> None:
    """
    Bulk-read nominal properties for all devices in one batch per property.
    Called after reset to refresh the nominal cache without individual RPCs.
    """
    global _initial_strength_cache, _nominal_cache
    if not id_to_properties:
        return
    if isinstance(id_to_properties, (list, tuple, set)):
        id_to_properties = {
            element_id: {"main_strength", "x_kick", "y_kick"}
            for element_id in id_to_properties
        }

    logger.warning("Refreshing nominal cache for %d element ids...", len(id_to_properties))
    new_cache = _read_values_from_lattice(sync_proxy, id_to_properties)
    _nominal_cache = new_cache
    _initial_strength_cache = {
        element_id: values.get("main_strength", 0.0)
        for element_id, values in new_cache.items()
    }
    logger.warning("Nominal cache refreshed for %d element ids.", len(new_cache))


def _preload_initial_values(sync_proxy, id_to_properties: dict) -> None:
    """
    Bulk-read nominal values before Tango starts so init_device() needs no RPCs.
    """
    global _initial_strength_cache, _nominal_cache
    if not id_to_properties:
        return

    logger.warning("Pre-loading initial values for %d element ids...", len(id_to_properties))
    try:
        _nominal_cache = _read_values_from_lattice(sync_proxy, id_to_properties)
        _initial_strength_cache = {
            element_id: values.get("main_strength", 0.0)
            for element_id, values in _nominal_cache.items()
        }
        logger.warning("Pre-loaded initial values for %d element ids.", len(_nominal_cache))
    except Exception as exc:
        logger.warning("Bulk pre-load failed: %s — devices will start at 0.0", exc)


def _element_id_from_config_entry(entry: dict):
    uuid = entry.get("uuid")
    if uuid:
        return uuid
    uuids = entry.get("uuids")
    if uuids:
        return uuids[0]
    return None


def _device_properties(entry: dict) -> tuple:
    return _PROPERTIES_BY_DEVICE_TYPE.get(entry.get("type", ""), ("main_strength",))


def _nominal_reads_for_server(server_name: str, instance_name: str) -> dict:
    from dt4acc.config.data.querries import get_magnets

    reads: dict[str, set[str]] = {}
    for entry in get_magnets():
        device_name = entry.get("name", "")
        parts = device_name.split("/")
        if len(parts) != 3 or parts[0] != server_name or parts[1] != instance_name:
            continue
        element_id = _element_id_from_config_entry(entry)
        if not element_id:
            continue
        reads.setdefault(element_id, set()).update(_device_properties(entry))
    return reads


def _reference_frequency_from_lattice(lattice_file=None) -> float:
    if lattice_file is None:
        return 0.0
    try:
        import at
        from pathlib import Path

        path = Path(lattice_file)
        if path.suffix.lower() == ".json":
            lattice = at.load_json(str(path))
        elif path.suffix.lower() == ".m":
            lattice = at.load_m(path)
        else:
            return 0.0

        cavities = [
            element
            for element in lattice
            if getattr(element, "Frequency", 0.0)
        ]
        if not cavities:
            return 0.0

        harmonic_number = getattr(lattice, "harmonic_number", None)
        if harmonic_number is not None:
            matching = [
                element for element in cavities
                if getattr(element, "HarmNumber", None) == harmonic_number
            ]
            if matching:
                return float(matching[0].Frequency) * 1e-3

        return min(float(element.Frequency) for element in cavities if element.Frequency > 0) * 1e-3
    except Exception as exc:
        logger.warning("Could not derive RF reference frequency from lattice: %s", exc)
        return 0.0


def _add_reference_frequency_if_needed(
    id_to_properties: dict,
    server_name: str,
    instance_name: str,
    lattice_file=None,
) -> None:
    global _static_nominal_cache
    if (server_name, instance_name) != ("simulator", "ringsimulator"):
        return
    reference_frequency = _reference_frequency_from_lattice(lattice_file)
    id_to_properties.setdefault("master_clock", set()).add("reference_frequency")
    _static_nominal_cache.setdefault("master_clock", {})[
        "reference_frequency"
    ] = reference_frequency

def _resolve_position_name_resolver(position_name_resolver, lattice_file=None):
    if position_name_resolver is None:
        return None
    if callable(position_name_resolver):
        return position_name_resolver

    module_name, _, function_name = str(position_name_resolver).partition(":")
    if not module_name or not function_name:
        raise ValueError("position_name_resolver must use 'module:function' syntax")

    module = importlib.import_module(module_name)
    configure = getattr(module, "configure_lattice_file", None)
    if configure is not None and lattice_file is not None:
        configure(lattice_file)
    return getattr(module, function_name)


def _inject_controller(
    prefix: str,
    manager_port=None,
    position_name_resolver=None,
    lattice_file=None,
) -> None:
    """
    Build AsyncMexecAdapter + TangoController and register in controller_registry.
    Called before tango.server.run() so init_device() can call get_controller().
    """
    from dt4acc.custom_tango.ioc.server_manager import _connect_to_mexec_service
    sync_proxy, sync_reset = _connect_to_mexec_service(manager_port)
    global _sync_proxy
    _sync_proxy = sync_proxy
    mexec = AsyncMexecAdapter(sync_proxy)

    controller = TangoController(
        mexec=mexec,
        prefix=prefix,
        default_delayed_reads=DEFAULT_DELAYED_READS,
        sync_reset=sync_reset,
        position_name_resolver=_resolve_position_name_resolver(
            position_name_resolver,
            lattice_file=lattice_file,
        ),
    )
    set_controller(controller)
    logger.info("TangoController created and registered for prefix=%s", prefix)


# ---------------------------------------------------------------------------
# main_loop — called by server_manager for each (server_name, instance_name)
# ---------------------------------------------------------------------------

def _configure_accelerator_setup_file(accelerator_setup_file=None) -> None:
    if accelerator_setup_file is None:
        return

    from dt4acc.config.data import querries as config_queries
    from dt4acc.custom_epics.data import querries as epics_queries
    from dt4acc.custom_facility.soleil import liasion_translator_setup
    from dt4acc.custom_facility.soleil import soleil_yellow_pages

    config_queries.configure_data_file(accelerator_setup_file)
    epics_queries.configure_data_file(accelerator_setup_file)
    soleil_yellow_pages.configure_accelerator_setup_file(accelerator_setup_file)
    liasion_translator_setup.load_managers.cache_clear()


def main_loop(
    server_name: str,
    instance_name: str,
    event=None,
    manager_port=None,
    accelerator_setup_file=None,
    position_name_resolver=None,
    lattice_file=None,
):
    import logging
    logging.getLogger("transitions").setLevel(logging.WARNING)
    logging.getLogger("transitions.core").setLevel(logging.WARNING)
    _configure_accelerator_setup_file(accelerator_setup_file)

    if hasattr(os, "nice"):
        os.nice(4)

    prefix = os.environ.get("DT4ACC_PREFIX", getpass.getuser())

    # Inject controller BEFORE Tango initialises any device
    _inject_controller(
        prefix,
        manager_port,
        position_name_resolver=position_name_resolver,
        lattice_file=lattice_file,
    )

    # Bulk pre-load initial values for all devices in this server/instance.
    # One RPC call per property instead of one per device in init_device().
    try:
        from dt4acc.custom_tango.ioc.server_manager import _connect_to_mexec_service
        sync_proxy, _ = _connect_to_mexec_service(manager_port)

        my_nominal_reads = _nominal_reads_for_server(server_name, instance_name)
        _add_reference_frequency_if_needed(
            my_nominal_reads,
            server_name,
            instance_name,
            lattice_file=lattice_file,
        )

        # Store as process-global so _refresh_all_magnet_devices can reuse after reset
        global _my_magnet_uuids, _my_nominal_reads
        _my_nominal_reads = my_nominal_reads
        _my_magnet_uuids = list(my_nominal_reads)

        _preload_initial_values(sync_proxy, my_nominal_reads)
    except Exception as exc:
        logger.warning("Pre-load setup failed: %s — devices will start at 0.0", exc)

    def _post_init_cb():
        # Start the controller's delayed queue loop inside the Tango event loop
        from dt4acc.custom_tango.ioc.controller_registry import get_controller
        try:
            get_controller().start()
            logger.warning("Server %s/%s ready — TangoController started", server_name, instance_name)
        except Exception as exc:
            logger.error("TangoController.start() failed: %s", exc)
        if event is not None:
            event.set()

    # Ensure an event loop exists for this process
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        # Import lazily here — after _inject_controller — to avoid circular imports
        from dt4acc.custom_tango.ioc.devices.tango_device_setup import get_all_device_classes
        device_classes = get_all_device_classes()
        logger.warning(
            "Starting %s/%s with %d device classes",
            server_name, instance_name, len(device_classes),
        )
        run(
            device_classes,
            args=[server_name, instance_name],
            post_init_callback=_post_init_cb,
            raises=True,
            verbose=True,
        )
    except Exception as exc:
        sys.stderr.write(f"Tango server {server_name}/{instance_name} failed: {exc}\n")
        sys.stderr.flush()
        logger.error("Tango server %s/%s failed: %s", server_name, instance_name, exc)
        raise
    finally:
        try:
            asyncio.get_event_loop().close()
        except Exception:
            pass


def main():
    if len(sys.argv) != 3:
        print("Usage: single_server.py <server_name> <instance_name>")
        sys.exit(1)
    main_loop(server_name=sys.argv[1], instance_name=sys.argv[2])


if __name__ == "__main__":
    main()
