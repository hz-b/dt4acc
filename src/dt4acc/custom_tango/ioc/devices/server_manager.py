#!/usr/bin/env python3
"""Start servers and heart beat process

Only start heartbeat when everything else is running
"""
import itertools
import multiprocessing.synchronize
import os
import sys
import time
import signal
import threading
from dataclasses import dataclass
from typing import Dict, Tuple, Sequence

from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_tango.ioc.devices.tango_device_setup import register_all_devices
from dt4acc.custom_tango.ioc.devices import single_server

# minimal tango import for heartbeat
from tango import DeviceProxy, DevFailed

import multiprocessing as mp

logger = get_logger()


def wait_for_start_of_heartbeat(
        start_evt: threading.Event,
        stop_evt: threading.Event,
):
    start = time.time()
    for cnt in itertools.count():
        if start_evt.is_set():
            return True
        if stop_evt.is_set():
            return False

        time.sleep(0.2)
        if (cnt % (5 * 5)) == 0:
            dt = time.time() - start
            dt /=60e0
            logger.warning(f"{dt=:.1f} min, magnet monitor: waiting for starting calculations")


def _magnet_monitor_and_heartbeat(
        start_evt: threading.Event,
        stop_evt: threading.Event,
        device_name: str = "an01-ar/em/cqln.03",
        attr_name: str = "magnetic_strength",
        delta: float = 0.01,
        period_s: float = 1.0,
        wait_connect_s: float = 5.0):
    """
    Wait for the real magnet device to be reachable, then toggle
    `attr_name` = base +/- delta every `period_s` seconds until stop_evt is set.

    - Does not raise on failures; logs and retries.
    - Non-blocking when launched as a daemon thread.
    """
    logger.info(f"Magnet monitor thread starting; waiting for device {device_name}...")
    dev = None
    base = None
    sign = +1.0

    if not wait_for_start_of_heartbeat(start_evt, stop_evt):
        logger.warning("Magnet monitor exiting before starting heartbeat (start event not send, but stop event set).")
        return

    logger.warning("Magnet monitor: starting heart beat")
    # Phase 1: wait until device is reachable and attribute can be read
    while not stop_evt.is_set():
        try:
            dev = DeviceProxy(device_name)
            # attempt to read the attribute to ensure device is up
            val = dev.read_attribute(attr_name).value
            base = float(val)
            logger.warning(f"Magnet {device_name} reachable; base {attr_name}={base}")
            break
        except DevFailed as e:
            logger.warning(f"Heartbead: Devfailed for magnet {device_name} (DevFailed) perhaps calling too early?")
            logger.info(f"Waiting for magnet {device_name} (DevFailed): {e}")
        except Exception as e:
            logger.error(f"Waiting for magnet {device_name} (exc): {e}")
        stop_evt.wait(wait_connect_s)

    if stop_evt.is_set():
        logger.warning("Magnet monitor exiting before starting heartbeat (stop event set).")
        return

    # Phase 2: heartbeat loop toggling value
    logger.warning(f"Starting magnet heartbeat for {device_name}/{attr_name} delta={delta}, period={period_s}s")
    while not stop_evt.is_set():
        try:
            val = base + sign * delta
            dev.write_attribute(attr_name, float(val))
            sign *= -1.0
        except DevFailed as e:
            # device may have restarted; re-enter wait loop to re-acquire base
            logger.warning(f"Magnet write failed (DevFailed). Will wait and retry: {e}")
            base = None
            # try to re-establish base
            while not stop_evt.is_set():
                try:
                    val = dev.read_attribute(attr_name).value
                    base = float(val)
                    logger.warning(f"Reconnected magnet {device_name}; new base {attr_name}={base}")
                    break
                except Exception as e:
                    logger.warning(f"Reconnect attempt failed: {e}")
                stop_evt.wait(wait_connect_s)
        except Exception as e:
            logger.error(f"Magnet heartbeat unexpected error: {e}")
            # a small pause before retrying to avoid busy loop in error storms
            stop_evt.wait(1.0)

        # wait with ability to be interrupted
        stop_evt.wait(period_s)

    logger.warning("Magnet heartbeat thread exiting (stop event set).")


@dataclass
class ProcessMonitor:
    event : mp.synchronize.Event
    process : mp.process.BaseProcess
    server_name : str
    instance_name : str

    def trl_prefix(self):
        return f"{self.server_name}/{self.instance_name}"


def wait_all_events_cleared(process_monitors: Sequence[ProcessMonitor]) -> bool:
    """are processes still active that are accociated with the events ?
    """
    start = time.time()

    lut = {pm.trl_prefix() : pm  for pm in process_monitors}
    for cnt in itertools.count():
        dt = time.time() - start
        dt /= 60e0
        now_set = {trl_prefix: pm for trl_prefix, pm in lut.items() if pm.event.is_set()}
        if now_set:
            logger.warning(
                f"{dt=:.1f} min: following events set this time %s",
                list(now_set)
            )
            for trl_prefix in now_set:
                lut.pop(trl_prefix)
            if not lut:
                return True
        # refrain to reduce to non set ... be exact on what
        # is reported

        for _, pm in lut.items():
            if not pm.process.is_alive() or pm.process.exitcode:
                logger.error("Process %s pid %s died: trying to stop", pm.trl_prefix(), pm.process.pid)
                return False

        time.sleep(0.2)
        if (cnt % (5 * 30)) == 0:
            logger.warning(f"{dt=:.1f} min still waiting for {list(lut)}")


def main():
    os.environ.setdefault("TANGO_HOST", "localhost:10000")

    # 1) register all devices (DB only)
    servers = register_all_devices()
    logger.warning(f"DB registration done. Need to start {len(servers)} servers.")

    # 2) spawn one process per server
    script_dir = os.path.dirname(os.path.abspath(__file__))
    single_server_path = os.path.join(script_dir, "single_server.py")

    procs_mon = []
    for server_name, instance_name in servers:
        logger.info(f"Starting mp process: {server_name}-{instance_name}")
        # if server_name.startswith("AN01"):
        #     logger.warning(f'You need to start single server with: "{server_name}"-"{instance_name}" manually!')
        # else:
        if True:
            t_event = mp.Event()
            p = mp.Process(
                target=single_server.main_loop,
                args=(server_name, instance_name, t_event),
                name=f"process-{server_name}-{instance_name}"
            )
            p.start()
            procs_mon.append(ProcessMonitor(event=t_event, process=p, server_name=server_name, instance_name=instance_name))
            time.sleep(.3)  # small stagger

    del server_name, instance_name
    # waiting for events to clear

    # Todo: clear this race condition here
    logger.warning(
        "%s:"
        "\n\t All server processes launched apart from heartbeat,"
        "\n\t waiting for databases to be initialised for 10 s...",
        __name__)
    logger.warning("Server processes are %s", [{pm.trl_prefix(): pm.process.pid for pm in procs_mon}])
    logger.warning("%s trying to start heart beat loop", __name__)
    # -- start magnet monitor + heartbeat thread AFTER launching servers --
    start_event = threading.Event()
    stop_event = threading.Event()
    hb_thread = threading.Thread(
        target=_magnet_monitor_and_heartbeat,
        args=(start_event, stop_event,),
        kwargs={
            # use default device_name and attr_name shown above; change here if needed
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
    logger.warning("Magnet monitor/heartbeat thread started (daemon).")

    # 3) wait + allow Ctrl+C clean shutdown
    def shutdown(*_):
        logger.warning("Shutting down all servers...")
        # first tell background thread to stop
        stop_event.set()

        for pm in procs_mon:
            try:
                pm.process.terminate()
            except Exception:
                pass
        time.sleep(1.0)
        for pm in procs_mon:
            try:
                if pm.process.poll() is None:
                    pm.process.kill()
            except Exception:
                pass
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    if wait_all_events_cleared(procs_mon):
        # all events here go on
        pass
    else:
        logger.error("Error occured while waiting for statup of all tango servers trying to shut down!")
        shutdown()

    # only needed if you want to start some process by hand
    # input("> hit any key when all other servers were started")
    logger.warning("All tango processes signaled startup!")
    logger.warning("Signaling heart beat to start")
    start_event.set()
    logger.warning("Signaled heart beat to start")

    logger.warning("All server processes launched. Monitoring the status of subprocessed!")
    while True:
        time.sleep(5)
        for pm in procs_mon:
            if not pm.process.is_alive() or pm.process.exitcode:
                logger.error(f"server process {pm.trl_prefix()} with pid {pm.process.pid} died!, shutting down")
                shutdown()

if __name__ == "__main__":
    main()
