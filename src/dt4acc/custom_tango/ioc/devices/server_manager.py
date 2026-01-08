#!/usr/bin/env python3
import os
import sys
import time
import signal
import subprocess
import threading

from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_tango.ioc.devices.tango_device_setup import register_all_devices

# minimal tango import for heartbeat
from tango import DeviceProxy, DevFailed

logger = get_logger()


def _magnet_monitor_and_heartbeat(stop_evt: threading.Event,
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
            logger.debug(f"Waiting for magnet {device_name} (DevFailed): {e}")
        except Exception as e:
            logger.debug(f"Waiting for magnet {device_name} (exc): {e}")
        stop_evt.wait(wait_connect_s)

    if stop_evt.is_set():
        logger.info("Magnet monitor exiting before starting heartbeat (stop event set).")
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
                    logger.debug(f"Reconnect attempt failed: {e}")
                stop_evt.wait(wait_connect_s)
        except Exception as e:
            logger.error(f"Magnet heartbeat unexpected error: {e}")
            # a small pause before retrying to avoid busy loop in error storms
            stop_evt.wait(1.0)

        # wait with ability to be interrupted
        stop_evt.wait(period_s)

    logger.info("Magnet heartbeat thread exiting (stop event set).")


def main():
    os.environ.setdefault("TANGO_HOST", "localhost:10000")

    # 1) register all devices (DB only)
    servers = register_all_devices()
    logger.info(f"DB registration done. Need to start {len(servers)} servers.")

    # 2) spawn one process per server
    procs = []
    script_dir = os.path.dirname(os.path.abspath(__file__))
    single_server_path = os.path.join(script_dir, "single_server.py")

    for server_name, instance_name in servers:
        cmd = [sys.executable, "-u", single_server_path, server_name, instance_name]

        logger.info(f"Starting process: {' '.join(cmd)}")

        p = subprocess.Popen(
            cmd,
            env=os.environ.copy(),
        )
        procs.append((server_name, instance_name, p))
        time.sleep(0.3)  # small stagger

    # -- start magnet monitor + heartbeat thread AFTER launching servers --
    stop_event = threading.Event()
    hb_thread = threading.Thread(
        target=_magnet_monitor_and_heartbeat,
        args=(stop_event,),
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
    logger.info("Magnet monitor/heartbeat thread started (daemon).")

    # 3) wait + allow Ctrl+C clean shutdown
    def shutdown(*_):
        logger.warning("Shutting down all servers...")
        # first tell background thread to stop
        stop_event.set()

        for s, i, p in procs:
            try:
                p.terminate()
            except Exception:
                pass
        time.sleep(1.0)
        for s, i, p in procs:
            try:
                if p.poll() is None:
                    p.kill()
            except Exception:
                pass
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    logger.info("All server processes launched. Waiting...")
    while True:
        time.sleep(5)


if __name__ == "__main__":
    main()
