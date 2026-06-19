import asyncio
import logging
import multiprocessing.managers
import threading

from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_tango.ioc.handle_lattice import lattice_loader
from dt4acc.custom_tango.ioc.mexec_config import _MANAGER_HOST, _MANAGER_PORT, _MANAGER_AUTHKEY
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


def _get_load_managers():
    """Return the load_managers callable set by the launch script."""
    if LOAD_MANAGERS_FN is None:
        raise ValueError(
            f"LOAD_MANAGERS_FN not set — set {__name__}.LOAD_MANAGERS_FN "
            "in the launch script before calling main()"
        )
    return LOAD_MANAGERS_FN


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
        expected_view_for_output=EXPECTED_VIEW,
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
        asyncio.set_event_loop(service_loop)
        service_loop.run_forever()

    threading.Thread(target=_run_loop, daemon=True, name="mexec-service-loop").start()

    future = asyncio.run_coroutine_threadsafe(_async_build_mexec(), service_loop)
    mexec = future.result(timeout=120)
    logger.warning("MexecService: lattice ready, mexec built.")


    proxy = SyncMexecProxy(mexec=mexec, service_loop=service_loop)
    MexecManagerService.register("get_mexec_proxy", callable=lambda: proxy)
    MexecManagerService.register("sync_reset", callable=proxy.sync_reset)
    MexecManagerService.register("sync_peek", callable=proxy.sync_peek)

    mgr = MexecManagerService(
        address=(_MANAGER_HOST, _MANAGER_PORT),
        authkey=_MANAGER_AUTHKEY,
    )
    mgr.get_server().serve_forever()


async def _async_build_mexec():
    return _build_mexec()


def _connect_to_mexec_service():
    MexecManagerService.register("get_mexec_proxy")
    MexecManagerService.register("sync_reset")
    MexecManagerService.register("sync_peek")
    client = MexecManagerService(
        address=(_MANAGER_HOST, _MANAGER_PORT),
        authkey=_MANAGER_AUTHKEY,
    )
    client.connect()
    return client.get_mexec_proxy(), client.sync_reset

