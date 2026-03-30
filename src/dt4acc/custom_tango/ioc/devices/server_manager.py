#!/usr/bin/env python3
import itertools
import multiprocessing.managers
import multiprocessing.synchronize
import os
import sys
import time
import signal
import threading
from dataclasses import dataclass
from typing import Sequence

from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_tango.ioc.devices.tango_device_setup import register_all_devices
import single_server
from tango import DeviceProxy, DevFailed
import multiprocessing as mp

logger = get_logger()

_MANAGER_HOST = "127.0.0.1"
_MANAGER_PORT = 50200
_MANAGER_AUTHKEY = b"dt4acc-tango-secret"


# ── UpdateManager service ─────────────────────────────────────────────────────

class UpdateManagerService(multiprocessing.managers.BaseManager):
    pass

def _run_update_manager_service():
    import asyncio
    import concurrent.futures
    from dt4acc.core.bl.handlers import get_update_manager

    # Start a persistent event loop in a background thread.
    # This loop runs forever so DelayExecution's scheduled tasks
    # (call_later, ensure_future) actually fire between update calls.
    service_loop = asyncio.new_event_loop()

    def run_loop():
        asyncio.set_event_loop(service_loop)
        service_loop.run_forever()

    loop_thread = threading.Thread(
        target=run_loop,
        daemon=True,
        name="service-event-loop"
    )
    loop_thread.start()

    # Load the accelerator on the service loop so all its internal
    # async machinery (DelayExecution etc.) is bound to that loop.
    future = asyncio.run_coroutine_threadsafe(
        _async_get_update_manager(), service_loop
    )
    instance = future.result(timeout=120)
    logger.warning("UpdateManagerService: lattice ready, serving.")

    class SyncUpdateManagerProxy:
        def peek_engine(self, lat_elem_prop):
            return instance.peek_engine(lat_elem_prop)

        def device_value_from_peeking_engine(self, dev_prop):
            return instance.device_value_from_peeking_engine(dev_prop)

        def sync_update(self, device_id: str, property_name: str, value: float):
            # Submit to the running loop and block until done.
            # The loop keeps running between calls so delayed tasks fire.
            fut = asyncio.run_coroutine_threadsafe(
                instance.update(
                    device_id=device_id,
                    property_name=property_name,
                    value=value,
                ),
                service_loop
            )
            return fut.result(timeout=30)

    sync_instance = SyncUpdateManagerProxy()
    UpdateManagerService.register("get_update_manager", callable=lambda: sync_instance)

    mgr = UpdateManagerService(
        address=(_MANAGER_HOST, _MANAGER_PORT),
        authkey=_MANAGER_AUTHKEY
    )
    mgr.get_server().serve_forever()


async def _async_get_update_manager():
    """Load the UpdateManager on the service loop."""
    from dt4acc.core.bl.handlers import get_update_manager
    return get_update_manager()
def _connect_to_update_manager_service():
    UpdateManagerService.register("get_update_manager")
    client = UpdateManagerService(
        address=(_MANAGER_HOST, _MANAGER_PORT),
        authkey=_MANAGER_AUTHKEY
    )
    client.connect()
    return client.get_update_manager()


# ── Heartbeat ─────────────────────────────────────────────────────────────────

def wait_for_start_of_heartbeat(start_evt, stop_evt):
    start = time.time()
    for cnt in itertools.count():
        if start_evt.is_set():
            return True
        if stop_evt.is_set():
            return False
        time.sleep(0.2)
        if (cnt % (5 * 30)) == 0:
            dt = (time.time() - start) / 60
            logger.warning(f"{dt=:.1f} min, magnet monitor: waiting for starting calculations")


def _magnet_monitor_and_heartbeat(
        start_evt, stop_evt,
        device_name="an01-ar/em/cqln.03",
        attr_name="magnetic_strength",
        delta=0.001, period_s=1.0, wait_connect_s=5.0):

    logger.info(f"Magnet monitor thread starting; waiting for device {device_name}...")
    dev, base, sign = None, None, +1.0

    if not wait_for_start_of_heartbeat(start_evt, stop_evt):
        logger.warning("Magnet monitor exiting before heartbeat.")
        return

    logger.warning("Magnet monitor: starting heart beat")
    while not stop_evt.is_set():
        try:
            dev = DeviceProxy(device_name)
            base = float(dev.read_attribute(attr_name).value)
            logger.warning(f"Magnet {device_name} reachable; base={base}")
            break
        except DevFailed as e:
            logger.warning(f"Heartbeat DevFailed for {device_name}: {e}")
        except Exception as e:
            logger.error(f"Waiting for {device_name}: {e}")
        stop_evt.wait(wait_connect_s)

    if stop_evt.is_set():
        return

    logger.warning(f"Starting heartbeat for {device_name}/{attr_name}")
    while not stop_evt.is_set():
        try:
            dev.write_attribute(attr_name, float(base + sign * delta))
            sign *= -1.0
        except DevFailed as e:
            logger.warning(f"Heartbeat write failed: {e}")
            base = None
            while not stop_evt.is_set():
                try:
                    base = float(dev.read_attribute(attr_name).value)
                    break
                except Exception as e:
                    logger.warning(f"Reconnect failed: {e}")
                stop_evt.wait(wait_connect_s)
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            stop_evt.wait(1.0)
        stop_evt.wait(period_s)

    logger.warning("Heartbeat thread exiting.")


# ── Process monitor ───────────────────────────────────────────────────────────

@dataclass
class ProcessMonitor:
    event: mp.synchronize.Event
    process: mp.process.BaseProcess
    server_name: str
    instance_name: str

    def trl_prefix(self):
        return f"{self.server_name}/{self.instance_name}"


def wait_all_events_cleared(process_monitors: Sequence[ProcessMonitor]) -> bool:
    start = time.time()
    lut = {pm.trl_prefix(): pm for pm in process_monitors}
    for cnt in itertools.count():
        dt = (time.time() - start) / 60
        now_set = {k: pm for k, pm in lut.items() if pm.event.is_set()}
        if now_set:
            logger.warning(
                f"{dt=:.2f} min: following processing signaled initialisation: {list(now_set)}"
            )
            for k in now_set:
                lut.pop(k)
            if not lut:
                return True
        for pm in process_monitors:
            if not pm.process.is_alive() or pm.process.exitcode:
                logger.error("Process %s pid %s died", pm.trl_prefix(), pm.process.pid)
                return False
        time.sleep(0.2)
        if (cnt % (5 * 30)) == 0:
            logger.warning(f"{dt=:.2f} min still waiting for {list(lut)}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    os.environ.setdefault("TANGO_HOST", "localhost:10000")

    # 1. Start the UpdateManager service process — loads lattice ONCE
    svc_proc = mp.Process(
        target=_run_update_manager_service,
        name="update-manager-service",
        daemon=True,
    )
    svc_proc.start()
    logger.warning("UpdateManagerService started (pid=%s) — waiting for lattice...", svc_proc.pid)

    # Wait until the service is reachable before spawning Tango processes
    for attempt in range(60):
        time.sleep(2.0)
        if not svc_proc.is_alive():
            logger.error("UpdateManagerService died during startup!")
            sys.exit(1)
        try:
            _connect_to_update_manager_service()
            logger.warning("UpdateManagerService reachable after %.0fs.", attempt * 2.0)
            break
        except Exception:
            logger.info("Waiting for UpdateManagerService... attempt %d", attempt + 1)
    else:
        logger.error("UpdateManagerService never became reachable.")
        sys.exit(1)

    # 2. Register devices in Tango DB
    servers = register_all_devices()
    logger.warning(f"DB registration done. Need to start {len(servers)} servers.")

    # 3. Spawn one Tango server process per server/instance
    procs_mon = []
    for server_name, instance_name in servers:
        logger.info(f"Starting mp process: {server_name}-{instance_name}")
        t_event = mp.Event()
        p = mp.Process(
            target=single_server.main_loop,
            args=(server_name, instance_name, t_event),
            name=f"process-{server_name}-{instance_name}",
        )
        p.start()
        procs_mon.append(ProcessMonitor(
            event=t_event, process=p,
            server_name=server_name, instance_name=instance_name,
        ))
        time.sleep(0.3)

    del server_name, instance_name

    logger.warning("All server processes launched. Waiting for startup...")

    start_event = threading.Event()
    stop_event = threading.Event()
    hb_thread = threading.Thread(
        target=_magnet_monitor_and_heartbeat,
        args=(start_event, stop_event),
        kwargs={
            "device_name": "an01-ar/em/cqln.03",
            "attr_name": "magnetic_strength",
            "delta": 0.001,
            "period_s": 1.0,
            "wait_connect_s": 5.0,
        },
        daemon=True,
        name="magnet-heartbeat-thread",
    )
    hb_thread.start()
    logger.warning("Magnet monitor/heartbeat thread started.")

    def shutdown(*_):
        logger.warning("Shutting down all servers...")
        stop_event.set()
        for pm in procs_mon:
            try:
                pm.process.terminate()
            except Exception:
                pass
        svc_proc.terminate()
        time.sleep(1.0)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    if wait_all_events_cleared(procs_mon):
        pass
    else:
        logger.error("Error during startup — shutting down.")
        shutdown()

    logger.warning("All tango processes signaled startup!")
    start_event.set()

    while True:
        time.sleep(5)
        if not svc_proc.is_alive():
            logger.error("UpdateManagerService died — shutting down.")
            shutdown()
        for pm in procs_mon:
            if not pm.process.is_alive() or pm.process.exitcode:
                logger.error(f"Server process {pm.trl_prefix()} died — shutting down.")
                shutdown()


if __name__ == "__main__":
    main()