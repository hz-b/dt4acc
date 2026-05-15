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


# Process-global cache: uuid → {property: value}
# Populated by _preload_initial_values() before init_device() runs.
# Re-populated by refresh_cache_from_lattice() after reset.
_initial_strength_cache: dict = {}  # uuid → float (main_strength)
_nominal_cache: dict = {}           # uuid → {"main_strength": f, "x_kick": f, "y_kick": f}
_my_magnet_uuids: list = []         # UUIDs of magnets in this server process
_sync_proxy = None                  # MexecService proxy for live reads
_device_view = False                # True only for device-view facilities (e.g. MAX IV)


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
    global _sync_proxy, _device_view # noqa: F824
    if not _device_view or _sync_proxy is None:
        return 0.0
    try:
        return _sync_proxy.sync_peek(element_id, prop)
    except Exception:
        return 0.0


def get_initial_strength(uuid: str) -> float:
    """Called by MagnetDevice.init_device() to get cached initial value."""
    return _initial_strength_cache.get(uuid, 0.0)


def get_nominal_values(uuid: str) -> dict:
    """Called by MagnetDevice.RefreshFromCache() after reset."""
    return _nominal_cache.get(uuid, {"main_strength": 0.0, "x_kick": 0.0, "y_kick": 0.0})


def refresh_cache_from_lattice(sync_proxy, magnet_uuids: list) -> None:
    """
    Bulk-read main_strength, x_kick, y_kick for all magnets in one batch.
    Called after reset to refresh the nominal cache without individual RPCs.
    One sync_trigger_read per property = 3 cross-process calls total,
    regardless of the number of magnets.
    """
    global _initial_strength_cache, _nominal_cache
    if not magnet_uuids:
        return

    logger.warning("Refreshing nominal cache for %d magnets...", len(magnet_uuids))
    new_cache = {uuid: {"main_strength": 0.0, "x_kick": 0.0, "y_kick": 0.0}
                 for uuid in magnet_uuids}

    for prop in ("main_strength", "x_kick", "y_kick"):
        try:
            ids  = list(magnet_uuids)
            props = [prop] * len(ids)
            raw = sync_proxy.sync_trigger_read(ids, props)
            for rcmd_id, rcmd_prop, payload in raw:
                if payload is not None and rcmd_id in new_cache:
                    try:
                        new_cache[rcmd_id][prop] = float(payload)
                    except (TypeError, ValueError):
                        pass
        except Exception as exc:
            logger.warning("refresh_cache_from_lattice: %s failed: %s", prop, exc)

    _nominal_cache = new_cache
    _initial_strength_cache = {uuid: v["main_strength"] for uuid, v in new_cache.items()}
    logger.warning("Nominal cache refreshed for %d magnets.", len(new_cache))


def _preload_initial_values(sync_proxy, magnet_uuids: list) -> None:
    """
    Bulk-read main_strength for all magnets in one batch before Tango starts.
    Populates _initial_strength_cache so init_device() needs no RPC calls.
    """
    global _initial_strength_cache # noqa: F824
    if not magnet_uuids:
        return

    logger.warning("Pre-loading initial values for %d magnets...", len(magnet_uuids))
    try:
        ids   = list(magnet_uuids)
        props = ["main_strength"] * len(ids)
        raw = sync_proxy.sync_trigger_read(ids, props)
        for rcmd_id, rcmd_prop, payload in raw:
            if payload is not None:
                try:
                    _initial_strength_cache[rcmd_id] = float(payload)
                except (TypeError, ValueError):
                    pass
        logger.warning("Pre-loaded %d initial values.", len(_initial_strength_cache))
    except Exception as exc:
        logger.warning("Bulk pre-load failed: %s — devices will start at 0.0", exc)

def _inject_controller(prefix: str) -> None:
    """
    Build AsyncMexecAdapter + TangoController and register in controller_registry.
    Called before tango.server.run() so init_device() can call get_controller().
    """
    from dt4acc.custom_tango.ioc.server_manager import _connect_to_mexec_service
    sync_proxy, sync_reset = _connect_to_mexec_service()
    global _sync_proxy
    _sync_proxy = sync_proxy
    mexec = AsyncMexecAdapter(sync_proxy)

    controller = TangoController(
        mexec=mexec,
        prefix=prefix,
        default_delayed_reads=DEFAULT_DELAYED_READS,
        sync_reset=sync_reset,
    )
    set_controller(controller)
    logger.info("TangoController created and registered for prefix=%s", prefix)


# ---------------------------------------------------------------------------
# main_loop — called by server_manager for each (server_name, instance_name)
# ---------------------------------------------------------------------------

def main_loop(server_name: str, instance_name: str, event=None):
    import logging
    logging.getLogger("transitions").setLevel(logging.WARNING)
    logging.getLogger("transitions.core").setLevel(logging.WARNING)

    os.nice(4)

    prefix = os.environ.get("DT4ACC_PREFIX", os.getlogin())

    # Inject controller BEFORE Tango initialises any device
    _inject_controller(prefix)

    # Bulk pre-load initial values for all magnets in this server/instance.
    # One RPC call for all magnets instead of one per magnet in init_device().
    try:
        from dt4acc.custom_epics.data.querries import get_magnets_per_power_converters, get_unique_power_converters
        from dt4acc.custom_tango.ioc.server_manager import _connect_to_mexec_service
        sync_proxy, _ = _connect_to_mexec_service()

        # Collect UUIDs for magnets belonging to this server/instance
        my_uuids = []
        for pc_name in get_unique_power_converters():
            for m in get_magnets_per_power_converters(pc_name):
                magnet_name = m["name"]  # e.g. AN01-AR/EM/CQLN.03
                parts = magnet_name.split("/")
                if len(parts) == 3 and parts[0] == server_name and parts[1] == instance_name:
                    uuid = m.get("uuid", "")
                    if uuid:
                        my_uuids.append(uuid)

        # Store as process-global so _refresh_all_magnet_devices can reuse after reset
        global _my_magnet_uuids
        _my_magnet_uuids = my_uuids

        _preload_initial_values(sync_proxy, my_uuids)
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