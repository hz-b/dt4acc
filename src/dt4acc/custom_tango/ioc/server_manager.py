#!/usr/bin/env python3
"""
server_manager.py
=================

Process topology
----------------

  Main process (this file)
  │
  ├── MexecService (mp.Process, daemon)
  │     One process owns the pyAT lattice and the
  │     TranslatingCommandExecutionEngine (mexec).
  │     Exposes a SyncMexecProxy via multiprocessing.managers TCP socket.
  │     The asyncio event loop inside this process runs forever so that
  │     backend state-machine transitions fire correctly between calls.
  │
  ├── TangoServerProcess × N  (one per domain/family from tango_device_setup)
  │     Each spawned by single_server.main_loop().
  │     Connects to MexecService and gets a SyncMexecProxy.
  │     single_server injects an AsyncMexecAdapter into the process so that
  │     TangoController and device write-handlers can call await mexec.set()/trigger_read().
  │
  └── magnet-heartbeat-thread
        Periodically writes to one magnet to keep calculations firing
        and verify the system is alive end-to-end.
"""
import math
import traceback

import at
import asyncio
import itertools
import logging
import multiprocessing as mp
import multiprocessing.managers
import multiprocessing.synchronize
import os
import signal
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from dt4acc.custom_tango.ioc.sync_mexec_proxy import SyncMexecProxy
from dt4acc.custom_tango.ioc.virtual_pass_through_command_rewriter import VirtualPassthroughCommandRewriter

# Suppress transitions state machine INFO logs across all processes
logging.getLogger("transitions").setLevel(logging.WARNING)
logging.getLogger("transitions.core").setLevel(logging.WARNING)

from dt4acc_lib.bl.command_rewritter import CommandRewriter





from dt4acc_lib.pyat_simulator.accelerator_simulator import PyATAcceleratorSimulator
from dt4acc_lib.pyat_simulator.simulator_backend import SimulatorBackend
from tango import DeviceProxy, DevFailed

from dt4acc.core.utils.logger import get_logger

logger = get_logger()

_MANAGER_HOST = "127.0.0.1"
_MANAGER_PORT = 50200
_MANAGER_AUTHKEY = b"dt4acc-tango-secret"

# ---------------------------------------------------------------------------
# Facility configuration — set by the launch script before calling main()
# ---------------------------------------------------------------------------

# Path to the AT lattice file (.m or .json)
LATTICE_FILE: Path = None

# Callable that returns (yellow_pages, liaison_manager, translator_service)
LOAD_MANAGERS_FN = None

# Expected view for output — "design" for SOLEIL (commands in lattice space)
EXPECTED_VIEW = "design"

# Heartbeat — pure recalculation, no lattice writes, no noise
# Set by the launch script. Period in seconds (0 = disabled).
HEARTBEAT_PERIOD = 1.0


def _load_lattice(path: Path):
    """
    Load an AT lattice from file. Supports:
      .m    — MATLAB/Octave format via at.load_m()
      .json — atjson v1 format via at.load_json()
    """
    suffix = path.suffix.lower()
    if suffix == ".json":
        return at.load_json(str(path))
    elif suffix == ".m":
        return at.load_m(path)
    else:
        raise ValueError(
            f"Unsupported lattice file format: {suffix!r}. "
            "Expected .m (MATLAB) or .json (atjson v1)."
        )


def _get_load_managers():
    """Return the load_managers callable set by the launch script."""
    if LOAD_MANAGERS_FN is None:
        raise ValueError(
            "LOAD_MANAGERS_FN not set — set server_manager.LOAD_MANAGERS_FN "
            "in the launch script before calling main()"
        )
    return LOAD_MANAGERS_FN


# ---------------------------------------------------------------------------
# MexecService — one process, one lattice, one mexec
# ---------------------------------------------------------------------------

class MexecManagerService(multiprocessing.managers.BaseManager):
    pass


def _build_mexec():
    """Build the TranslatingCommandExecutionEngine on the service process."""
    from dt4acc.core.bl.translating_command_execution_engine import (
        TranslatingCommandExecutionEngine,
    )

    filename = LATTICE_FILE
    if filename is None:
        raise ValueError(
            "LATTICE_FILE not set — set server_manager.LATTICE_FILE before main()"
        )
    acc = _load_lattice(filename)
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


def _run_mexec_service():
    """
    Entry point for the MexecService process.
    """
    import logging
    logging.getLogger("transitions").setLevel(logging.WARNING)
    logging.getLogger("transitions.core").setLevel(logging.WARNING)

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


# ---------------------------------------------------------------------------
# Heartbeat
# ---------------------------------------------------------------------------

def _wait_for_heartbeat_start(start_evt, stop_evt):
    start = time.time()
    for cnt in itertools.count():
        if start_evt.is_set():
            return True
        if stop_evt.is_set():
            return False
        time.sleep(0.2)
        if (cnt % (5 * 30)) == 0:
            dt = (time.time() - start) / 60
            logger.warning("%.1f min: waiting for tango devices to start", dt)


# ---------------------------------------------------------------------------
# Calculation heartbeat — no writes, no lattice perturbation
# ---------------------------------------------------------------------------

def _wait_for_heartbeat_start(start_evt, stop_evt):
    start = time.time()
    for cnt in itertools.count():
        if start_evt.is_set():
            return True
        if stop_evt.is_set():
            return False
        time.sleep(0.2)
        if (cnt % (5 * 30)) == 0:
            dt = (time.time() - start) / 60
            logger.warning("%.1f min: waiting for tango devices to start", dt)


def _calculation_heartbeat(start_evt, stop_evt, period_s=1.0):
    """
    Heartbeat that triggers a full twiss+orbit+tune recalculation every
    period_s seconds WITHOUT writing to or changing the lattice.

    The calculation uses the current lattice state — so:
    - On startup it reflects nominal values
    - After a magnet write it reflects the changed lattice
    - Between writes it is stable and does not add any noise

    Results are pushed to RingSimulatorDevice via the TangoController
    queue — the same path as a normal magnet write.
    """
    if not _wait_for_heartbeat_start(start_evt, stop_evt):
        logger.warning("Calculation heartbeat exiting before devices ready.")
        return

    logger.warning("Calculation heartbeat started — recalculating every %.1fs", period_s)

    # Connect to the RingSimulatorDevice to trigger recalculation via Recalculate command
    from tango import DeviceProxy, DevFailed
    from dt4acc.custom_tango.ioc.devices.virtual_devices import RING_SIM_DEV

    dev = None
    while not stop_evt.is_set():
        try:
            dev = DeviceProxy(RING_SIM_DEV)
            dev.ping()
            logger.warning("Calculation heartbeat: %s reachable", RING_SIM_DEV)
            break
        except Exception as exc:
            logger.warning("Calculation heartbeat: waiting for %s: %s", RING_SIM_DEV, exc)
            stop_evt.wait(5.0)

    if stop_evt.is_set():
        return

    while not stop_evt.is_set():
        try:
            dev.command_inout("Recalculate")
        except DevFailed as exc:
            logger.warning("Calculation heartbeat: Recalculate failed: %s", exc)
        except Exception as exc:
            logger.error("Calculation heartbeat error: %s", exc)
        stop_evt.wait(period_s)


# ---------------------------------------------------------------------------
# Process monitor
# ---------------------------------------------------------------------------

@dataclass
class ProcessMonitor:
    event: Any
    process: Any
    server_name: str
    instance_name: str

    def trl_prefix(self):
        return f"{self.server_name}/{self.instance_name}"


def _wait_all_started(monitors: Sequence[ProcessMonitor]) -> bool:
    start = time.time()
    remaining = {pm.trl_prefix(): pm for pm in monitors}

    for cnt in itertools.count():
        dt = (time.time() - start) / 60
        newly_ready = {k: pm for k, pm in remaining.items() if pm.event.is_set()}
        for k in newly_ready:
            logger.info("%.2f min: %s signalled startup", dt, k)
            remaining.pop(k)
        if not remaining:
            return True

        for pm in monitors:
            if not pm.process.is_alive() or pm.process.exitcode:
                logger.error("Process %s (pid=%s) died", pm.trl_prefix(), pm.process.pid)
                return False

        time.sleep(0.2)
        if (cnt % (5 * 30)) == 0:
            logger.warning("%.2f min: still waiting for %s", dt, list(remaining))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    os.environ.setdefault("TANGO_HOST", "localhost:10000")

    # 1. Start MexecService
    svc_proc = mp.Process(
        target=_run_mexec_service,
        name="mexec-service",
        daemon=True,
    )
    svc_proc.start()
    logger.warning("MexecService started (pid=%s) — waiting for lattice...", svc_proc.pid)

    for attempt in range(60):
        time.sleep(2.0)
        if not svc_proc.is_alive():
            logger.error("MexecService died during startup!")
            sys.exit(1)
        try:
            _connect_to_mexec_service()
            logger.warning("MexecService reachable after %.0fs", attempt * 2.0)
            break
        except Exception:
            logger.info("Waiting for MexecService... attempt %d", attempt + 1)
    else:
        logger.error("MexecService never became reachable.")
        sys.exit(1)

    # 2. Register Tango devices in DB
    from dt4acc.custom_tango.ioc.devices.tango_device_setup import register_all_devices
    servers = register_all_devices()
    logger.warning("DB registration done. Starting %d servers.", len(servers))

    # 3. Spawn one Tango server process per (server_name, instance_name)
    from dt4acc.custom_tango.ioc import single_server
    monitors = []
    for server_name, instance_name in servers:
        evt = mp.Event()
        p = mp.Process(
            target=single_server.main_loop,
            args=(server_name, instance_name, evt),
            name=f"tango-{server_name}-{instance_name}",
        )
        p.start()
        monitors.append(ProcessMonitor(
            event=evt, process=p,
            server_name=server_name, instance_name=instance_name,
        ))
        time.sleep(0.3)

    # 4. Calculation heartbeat — recalculates twiss+orbit+tune every second
    #    without writing to or changing the lattice (zero noise)
    start_evt = threading.Event()
    stop_evt  = threading.Event()
    if HEARTBEAT_PERIOD > 0:
        hb = threading.Thread(
            target=_calculation_heartbeat,
            args=(start_evt, stop_evt),
            kwargs=dict(period_s=HEARTBEAT_PERIOD),
            daemon=True,
            name="calculation-heartbeat",
        )
        hb.start()
    else:
        logger.warning("Calculation heartbeat disabled (HEARTBEAT_PERIOD=0)")

    def _shutdown(*_):
        logger.warning("Shutting down.")
        stop_evt.set()
        for pm in monitors:
            try:
                pm.process.terminate()
            except Exception:
                pass
        svc_proc.terminate()
        time.sleep(1.0)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # 5. Wait for all Tango processes to signal startup
    if not _wait_all_started(monitors):
        logger.error("A Tango process died during startup — shutting down.")
        _shutdown()

    logger.warning("All Tango processes ready.")
    start_evt.set()  # release heartbeat

    # 6. Watch forever
    while True:
        time.sleep(5)
        if not svc_proc.is_alive():
            logger.error("MexecService died — shutting down.")
            _shutdown()
        for pm in monitors:
            if not pm.process.is_alive() or pm.process.exitcode:
                logger.error("Server %s died — shutting down.", pm.trl_prefix())
                _shutdown()


if __name__ == "__main__":
    main()