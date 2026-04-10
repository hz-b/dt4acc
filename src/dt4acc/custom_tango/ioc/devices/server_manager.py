#!/usr/bin/env python3
import itertools
import multiprocessing.managers
import multiprocessing.synchronize
import os
import queue
import sys
import time
import signal
import threading
from dataclasses import dataclass
from typing import Sequence

from dt4acc.config.accelerator_config import accelerator_config
from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_tango.ioc.devices.tango_device_setup import register_all_devices
from . import single_server
from tango import DeviceProxy, DevFailed
import multiprocessing as mp

logger = get_logger()

_MANAGER_HOST = "127.0.0.1"
_MANAGER_AUTHKEY = b"dt4acc-tango-secret"

def _select_heartbeat_device_name(elements) -> str:
    wanted = {"Quadrupole", "Sextupole", "Steerer"}

    for element in elements:
        if element.get("type") in wanted:
            name = element.get("name")
            if name:
                return name

    raise RuntimeError(
        "No suitable MagnetDevice candidate found in accelerator setup "
        "(expected a Quadrupole, Sextupole or Steerer with a name)."
    )

# ── UpdateManager service ─────────────────────────────────────────────────────

class UpdateManagerService(multiprocessing.managers.BaseManager):
    pass

def _run_update_manager_service(port_queue, elements=None, lattice_file: str | None = None):
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
        _async_get_update_manager(elements=elements, lattice_file=lattice_file), service_loop
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
        address=(_MANAGER_HOST, 0),
        authkey=_MANAGER_AUTHKEY
    )
    server = mgr.get_server()
    _, manager_port = server.address
    port_queue.put(manager_port)
    try:
        server.serve_forever()
    except OSError as e:
        logger.error(
            f"Failed to start UpdateManagerService on {_MANAGER_HOST}:{manager_port}: {e}"
        )
        raise

async def _async_get_update_manager(elements=None, lattice_file: str | None = None):
    """Load the UpdateManager on the service loop."""
    from dt4acc.core.bl.handlers import get_update_manager
    return get_update_manager(elements=elements, lattice_file=lattice_file)


def _connect_to_update_manager_service(manager_port: int):
    UpdateManagerService.register("get_update_manager")
    client = UpdateManagerService(
        address=(_MANAGER_HOST, manager_port),
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
        device_name="an01-ar/em-cor/scd.03-cdlh.03",
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
    elements = accelerator_config.get_accelerator_setup()
    lattice_file = accelerator_config.get_lattice_file()
    if elements is None:
        raise RuntimeError("Accelerator setup is not loaded before starting UpdateManagerService")
    if lattice_file is None:
        raise RuntimeError("Lattice file is not loaded before starting UpdateManagerService")

    heartbeat_device_name = _select_heartbeat_device_name(elements)
    logger.info("Selected heartbeat device: %s", heartbeat_device_name)

    # 1. Start the UpdateManager service process — loads lattice ONCE
    manager_port_queue = mp.Queue()
    svc_proc = mp.Process(
        target=_run_update_manager_service,
        args=(manager_port_queue, elements, lattice_file),
        name="update-manager-service",
        daemon=True,
    )
    svc_proc.start()
    logger.warning("UpdateManagerService started (pid=%s) — waiting for lattice...", svc_proc.pid)

    try:
        manager_port = manager_port_queue.get(timeout=30)
    except queue.Empty:
        logger.error("UpdateManagerService did not publish its listening port.")
        sys.exit(1)

    logger.warning("UpdateManagerService listening on %s:%s", _MANAGER_HOST, manager_port)

    # Wait until the service is reachable before spawning Tango processes
    for attempt in range(60):
        time.sleep(2.0)
        if not svc_proc.is_alive():
            logger.error("UpdateManagerService died during startup!")
            sys.exit(1)
        try:
            _connect_to_update_manager_service(manager_port)
            logger.warning("UpdateManagerService reachable after %.0fs.", attempt * 2.0)
            break
        except Exception:
            logger.info("Waiting for UpdateManagerService... attempt %d", attempt + 1)
    else:
        logger.error("UpdateManagerService never became reachable.")
        sys.exit(1)

    # 2. Register devices in Tango DB
    servers = register_all_devices(elements)
    logger.warning(f"DB registration done. Need to start {len(servers)} servers.")

    # 3. Spawn one Tango server process per server/instance
    procs_mon = []
    start_event = threading.Event()
    stop_event = threading.Event()

    def shutdown(*_):
        logger.warning("Shutting down all servers...")
        stop_event.set()
        for pm in procs_mon:
            try:
                pm.process.terminate()
            except Exception:
                pass
        try:
            svc_proc.terminate()
        except Exception:
            pass
        time.sleep(1.0)
        sys.exit(0)

    hb_thread = threading.Thread(
        target=_magnet_monitor_and_heartbeat,
        args=(start_event, stop_event),
        kwargs={
            "device_name": heartbeat_device_name,
            "attr_name": "magnetic_strength",
            "period_s": 1.0,
            "wait_connect_s": 5.0,
        },
        daemon=True,
        name="magnet-heartbeat-thread",
    )
    hb_thread.start()
    logger.warning("Magnet monitor/heartbeat thread started.")

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Sequential start
    global_start = time.time()
    for server_name, instance_name in servers:
        logger.info(f"Starting mp process: {server_name}-{instance_name}")
        t_event = mp.Event()
        p = mp.Process(
            target=single_server.main_loop,
            args=(server_name, instance_name, manager_port, t_event),
            name=f"process-{server_name}-{instance_name}",
        )
        p.start()

        pm = ProcessMonitor(
            event=t_event,
            process=p,
            server_name=server_name,
            instance_name=instance_name,
        )
        procs_mon.append(pm)

        logger.warning("Waiting for startup of %s", pm.trl_prefix())
        start = time.time()
        while not t_event.is_set():
            if not p.is_alive() or p.exitcode:
                logger.error("Process %s pid %s died", pm.trl_prefix(), p.pid)
                shutdown()
            if time.time() - start > 120:
                logger.error("Timeout while starting %s", pm.trl_prefix())
                shutdown()
            time.sleep(0.1)

        elapsed_time = time.time() - global_start
        logger.warning(f"Server {pm.trl_prefix()} started. Elapsed time: {elapsed_time}")
        time.sleep(0.5)

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
