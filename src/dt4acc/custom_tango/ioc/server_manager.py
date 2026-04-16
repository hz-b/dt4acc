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

# Suppress transitions state machine INFO logs across all processes
logging.getLogger("transitions").setLevel(logging.WARNING)
logging.getLogger("transitions.core").setLevel(logging.WARNING)

from dt4acc_lib.bl.command_rewritter import CommandRewriter
from dt4acc_lib.model.utils.command import BehaviourOnError, Command, ReadCommand
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

# Path to the AT lattice .m file
LATTICE_FILE: Path = None

# Callable that returns (yellow_pages, liaison_manager, translator_service)
# Default: BESSY II / SOLEIL setup from liasion_translator_setup
LOAD_MANAGERS_FN = None

# Heartbeat device and attribute
HEARTBEAT_DEVICE = "AN01-AR/EM-QP/QF01.01"  # "an01-ar/em/cqln.03"
HEARTBEAT_ATTR   = "magnetic_strength"


def _get_load_managers():
    """Return the load_managers callable, falling back to default if not set."""
    if LOAD_MANAGERS_FN is not None:
        return LOAD_MANAGERS_FN
    from dt4acc.custom_facility.bessyii.liasion_translator_setup import load_managers
    return load_managers


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
        raise ValueError("LATTICE_FILE not set — call configure() or set server_manager.LATTICE_FILE before main()")
    acc = at.load_m(filename)
    backend = SimulatorBackend(
        name="Facility speficic PYAT",
        acc=PyATAcceleratorSimulator(at_lattice=acc),
    )
    load_managers = _get_load_managers()
    _, lm, ts = load_managers()

    cmd_rewriter = CommandRewriter(liaison_manager=lm, translation_service=ts)

    return TranslatingCommandExecutionEngine(
        backend=backend,
        cmd_rewriter=cmd_rewriter,
        expected_view_for_output="design",
        num_readings=1,
    )


def _run_mexec_service():
    """
    Entry point for the MexecService process.

    Starts a persistent asyncio event loop so that the backend's
    state-machine tasks (DelayExecution etc.) fire between RPC calls.
    Exposes SyncMexecProxy via multiprocessing.managers.
    """
    import logging
    logging.getLogger("transitions").setLevel(logging.WARNING)
    logging.getLogger("transitions.core").setLevel(logging.WARNING)

    service_loop = asyncio.new_event_loop()

    def _run_loop():
        asyncio.set_event_loop(service_loop)
        service_loop.run_forever()

    threading.Thread(target=_run_loop, daemon=True, name="mexec-service-loop").start()

    # Build mexec on the service loop so its internals are bound to it
    future = asyncio.run_coroutine_threadsafe(_async_build_mexec(), service_loop)
    mexec = future.result(timeout=120)
    logger.warning("MexecService: lattice ready, mexec built.")

    class SyncMexecProxy:
        """
        Synchronous wrapper around mexec for crossing the process boundary.
        All async calls are submitted to the service loop and block until done.
        """

        def sync_set(self, cmd_id: str, cmd_property: str, value: float):
            cmd = Command(
                id=cmd_id,
                property=cmd_property,
                value=value,
                behaviour_on_error=BehaviourOnError.stop,
            )
            fut = asyncio.run_coroutine_threadsafe(
                mexec.set([cmd]), service_loop
            )
            return fut.result(timeout=30)

        def sync_trigger_read(self, rcmd_ids: Sequence[str], rcmd_properties: Sequence[str]):
            """
            Accepts plain strings (serialisable across process boundary).
            Returns a list of (name, payload) tuples — simple pickable data.
            """
            rcmds = [
                ReadCommand(id=i, property=p)
                for i, p in zip(rcmd_ids, rcmd_properties)
            ]
            fut = asyncio.run_coroutine_threadsafe(
                mexec.trigger_read(rcmds), service_loop
            )
            result = fut.result(timeout=30)
            # Return only picklable data: list of (rcmd_id, rcmd_property, payload)
            out = []
            for translated in result.data:
                for reading in translated.readings:
                    out.append((translated.cmd.id, translated.cmd.property, reading.payload))
            return out

        def sync_reset(self):
            """
            Reset the backend to nominal state:
            1. Reload the AT lattice from the original .m file
            2. Clear the error state → pending
            3. Clear stored optics so next read recalculates fresh

            Called by TwissOrbitDevice.Reset command via the Tango process.
            """
            import at
            logger.warning("SyncMexecProxy.sync_reset: reloading lattice from file...")
            try:
                new_acc = at.load_m(LATTICE_FILE)
                mexec.backend.acc.acc = new_acc
                with mexec.backend.calculation_lock:
                    if mexec.backend.model.is_error():
                        mexec.backend.model.clear()
                    elif not mexec.backend.model.is_pending():
                        mexec.backend.model.changed()
                    mexec.backend.optics = None
                    mexec.backend.elem_names = None
                logger.warning("SyncMexecProxy.sync_reset: lattice reloaded, state=pending")
            except Exception as exc:
                logger.error("SyncMexecProxy.sync_reset failed: %s", exc)
                raise

    proxy = SyncMexecProxy()
    MexecManagerService.register("get_mexec_proxy", callable=lambda: proxy)
    MexecManagerService.register("sync_reset", callable=proxy.sync_reset)

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


def _magnet_heartbeat(
        start_evt, stop_evt,
        device_name="an01-ar/em/cqln.03",
        attr_name="magnetic_strength",
        delta=0.001,
        period_s=1.0,
        wait_connect_s=5.0,
):
    if not _wait_for_heartbeat_start(start_evt, stop_evt):
        logger.warning("Heartbeat exiting before devices ready.")
        return

    logger.warning("Heartbeat: connecting to %s", device_name)
    dev, base, sign = None, None, +1.0

    while not stop_evt.is_set():
        try:
            dev = DeviceProxy(device_name)
            base = float(dev.read_attribute(attr_name).value)
            logger.warning("Heartbeat: %s reachable, base=%.6f", device_name, base)
            break
        except DevFailed as e:
            logger.warning("Heartbeat DevFailed: %s", e)
        except Exception as e:
            logger.error("Heartbeat connect error: %s", e)
        stop_evt.wait(wait_connect_s)

    if stop_evt.is_set():
        return

    while not stop_evt.is_set():
        try:
            dev.write_attribute(attr_name, float(base + sign * delta))
            sign *= -1.0
        except DevFailed as e:
            logger.warning("Heartbeat write failed: %s", e)
            while not stop_evt.is_set():
                try:
                    base = float(dev.read_attribute(attr_name).value)
                    break
                except Exception as e:
                    logger.warning("Heartbeat reconnect: %s", e)
                stop_evt.wait(wait_connect_s)
        except Exception as e:
            logger.error("Heartbeat error: %s", e)
            stop_evt.wait(1.0)
        stop_evt.wait(period_s)


# ---------------------------------------------------------------------------
# Process monitor
# ---------------------------------------------------------------------------

@dataclass
class ProcessMonitor:
    event: Any  # multiprocessing.synchronize.Event
    process: Any  # multiprocessing.process.BaseProcess
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
            logger.warning("%.2f min: %s signalled startup", dt, k)
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

    # 1. Start the MexecService — loads lattice ONCE, serves via TCP socket
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

    # 4. Heartbeat thread — starts writing to a magnet once all devices are up
    start_evt = threading.Event()
    stop_evt = threading.Event()
    hb = threading.Thread(
        target=_magnet_heartbeat,
        args=(start_evt, stop_evt),
        kwargs=dict(
            device_name=HEARTBEAT_DEVICE,
            attr_name=HEARTBEAT_ATTR,
            delta=0.001,
            period_s=1.0,
            wait_connect_s=5.0,
        ),
        daemon=True,
        name="magnet-heartbeat",
    )
    hb.start()

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