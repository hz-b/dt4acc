import asyncio
import functools
import importlib
import logging
import multiprocessing.managers
import os
import threading
import time
from collections import defaultdict

from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_tango.ioc.handle_lattice import lattice_loader
from dt4acc.custom_tango.ioc import mexec_config
from dt4acc.custom_tango.ioc.sync_mexec_proxy import SyncMexecProxy
from dt4acc.custom_tango.ioc.virtual_pass_through_command_rewriter import VirtualPassthroughCommandRewriter
from dt4acc_lib.pyat_simulator.accelerator_simulator import PyATAcceleratorSimulator
from dt4acc_lib.pyat_simulator.simulator_backend import SimulatorBackend

# Suppress transitions state machine INFO logs across all processes
logging.getLogger("transitions").setLevel(logging.WARNING)
logging.getLogger("transitions.core").setLevel(logging.WARNING)

logger = get_logger()

# Callable that returns (yellow_pages, liaison_manager, translator_service)
LOAD_MANAGERS_FN = None

# Expected view for output — "design" for SOLEIL (commands in lattice space)
EXPECTED_VIEW = "design"
MEXEC_CONNECT_RETRY_TIMEOUT_S = float(os.environ.get("DT4ACC_MEXEC_CONNECT_RETRY_TIMEOUT_S", "15"))
MEXEC_CONNECT_RETRY_INTERVAL_S = float(os.environ.get("DT4ACC_MEXEC_CONNECT_RETRY_INTERVAL_S", "0.2"))


def _get_load_managers():
    """Return the load_managers callable set by the launch script."""
    if LOAD_MANAGERS_FN is not None:
        return LOAD_MANAGERS_FN

    spec = os.environ.get("DT4ACC_LOAD_MANAGERS")
    if spec:
        module_name, _, function_name = spec.partition(":")
        if not module_name or not function_name:
            raise ValueError("DT4ACC_LOAD_MANAGERS must use 'module:function' syntax")
        module = importlib.import_module(module_name)
        return getattr(module, function_name)

    if LOAD_MANAGERS_FN is None:
        raise ValueError(
            f"LOAD_MANAGERS_FN not set — set {__name__}.LOAD_MANAGERS_FN "
            "in the launch script before calling main(), or set DT4ACC_LOAD_MANAGERS"
        )


@functools.lru_cache(maxsize=1)
def _device_to_lattice_properties() -> dict:
    """device_name -> sorted list of AT lattice-element properties it controls.

    Read straight from the active facility's liaison manager inverse table
    (LOAD_MANAGERS_FN, set by the facility's run_*_twin.py) — the single
    source of truth for how a Tango device name maps onto the AT lattice.
    load_managers() is a pure function (it just parses static facility
    config), so calling it again here in the Tango device-server process is
    safe and yields the identical mapping the mexec service process built,
    without needing any IPC.

    Use this instead of re-deriving the mapping from device-name patterns
    (e.g. "CDLV"/"CRFCY" substrings) or magnet type/subtype heuristics —
    those duplicate what the facility's liasion_translator_setup.py already
    computes correctly, and can drift out of sync with it.
    """
    _, lm, _ = _get_load_managers()()
    by_device = defaultdict(set)
    for elem in lm.inverse_lut.lut:
        for lat_p in elem.lat_ids:
            by_device[elem.dev_id.device_name].add(lat_p.property)
    return {name: sorted(props) for name, props in by_device.items()}


def lattice_properties_for_device(device_name: str, default=("main_strength",)) -> list:
    """Return the AT lattice-element properties the given Tango device name
    controls (e.g. ["main_strength"], ["B1"], ["A1"], ["frequency", "voltage"]),
    per the active facility's liaison manager. Falls back to `default` if the
    device has no liaison entry (shouldn't normally happen for a registered
    controlled element).
    """
    return _device_to_lattice_properties().get(device_name, list(default))


def _build_mexec():
    """Build the TranslatingCommandExecutionEngine on the service process."""
    from dt4acc.core.bl.translating_command_execution_engine import (
        TranslatingCommandExecutionEngine,
    )

    acc = lattice_loader.load()
    backend = SimulatorBackend(
        name="Facility specific PYAT",
        acc=PyATAcceleratorSimulator(at_lattice=acc),
    )
    load_managers = _get_load_managers()
    _, lm, ts = load_managers()

    cmd_rewriter = VirtualPassthroughCommandRewriter(liaison_manager=lm, translation_service=ts)

    return TranslatingCommandExecutionEngine(
        backend=backend,
        cmd_rewriter=cmd_rewriter,
        expected_view_for_output=os.environ.get("DT4ACC_VIEW", EXPECTED_VIEW),
        num_readings=1,
    )

# ---------------------------------------------------------------------------
# MexecService — one process, one lattice, one mexec
# ---------------------------------------------------------------------------
class MexecManagerService(multiprocessing.managers.BaseManager):
    pass


def _run_mexec_service():
    """
    Entry point for the MexecService process.
    """
    service_loop = asyncio.new_event_loop()

    def _run_loop():
        logger.warning("Mexec service loop runing on pid %d", os.getpid())
        asyncio.set_event_loop(service_loop)
        service_loop.run_forever()

    threading.Thread(target=_run_loop, daemon=True, name="mexec-service-loop").start()

    future = asyncio.run_coroutine_threadsafe(_async_build_mexec(), service_loop)
    mexec = future.result(timeout=120)
    logger.warning("MexecService: lattice ready, mexec built. running on pid %d", os.getpid())


    proxy = SyncMexecProxy(mexec=mexec, service_loop=service_loop)
    MexecManagerService.register("get_mexec_proxy", callable=lambda: proxy)
    MexecManagerService.register("sync_reset", callable=proxy.sync_reset)
    MexecManagerService.register("sync_reinit", callable=proxy.sync_reinit)
    MexecManagerService.register("sync_peek", callable=proxy.sync_peek)

    mgr = MexecManagerService(
        address=(mexec_config._MANAGER_HOST, mexec_config._MANAGER_PORT),
        authkey=mexec_config._MANAGER_AUTHKEY,
    )
    mgr.get_server().serve_forever()


async def _async_build_mexec():
    return _build_mexec()


def _connect_to_mexec_service():
    MexecManagerService.register("get_mexec_proxy")
    MexecManagerService.register("sync_reset")
    MexecManagerService.register("sync_reinit")
    MexecManagerService.register("sync_peek")
    deadline = time.monotonic() + MEXEC_CONNECT_RETRY_TIMEOUT_S

    while True:
        try:
            client = MexecManagerService(
                address=(mexec_config._MANAGER_HOST, mexec_config._MANAGER_PORT),
                authkey=mexec_config._MANAGER_AUTHKEY,
            )
            client.connect()
            return client.get_mexec_proxy(), client.sync_reset, client.sync_reinit
        except (ConnectionRefusedError, EOFError, OSError):
            if time.monotonic() >= deadline:
                raise
            time.sleep(MEXEC_CONNECT_RETRY_INTERVAL_S)
