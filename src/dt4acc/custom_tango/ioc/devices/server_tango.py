#!/usr/bin/env python3

import threading
import time

from tango.server import run
from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_tango.ioc.devices.tango_device_setup import (
    register_all_devices,
    get_all_device_classes,
)

logger = get_logger()


def start_server_for(server_name: str, instance_name: str, device_classes):
    """
    Start one Tango server process (thread) for:
        server_name / instance_name

    - Example: server_name='AN10-AR', instance_name='EM'
      -> device server: AN10-AR/EM
      -> dserver:       dserver/AN10-AR/EM
    """
    logger.info(f"🚀 Starting Tango server {server_name}/{instance_name}")
    try:
        # Very important: args[0] = server_name, args[1] = instance_name
        run(device_classes, args=[server_name, instance_name])
    except Exception as e:
        logger.error(f"❌ Failed to start server {server_name}/{instance_name}: {e}")


def main():
    logger.info("📡 Starting Soleil Tango Server Manager")

    # STEP 1 — Register all devices -> get all (server_name, instance_name) pairs
    servers = register_all_devices()
    logger.info(f"✔ Device registration DONE. We have {len(servers)} servers to start.")

    # STEP 2 — Get device classes
    device_classes = get_all_device_classes()

    # STEP 3 — Start each server in its own thread
    threads = []
    for server_name, instance_name in servers:
        t = threading.Thread(
            target=start_server_for,
            args=(server_name, instance_name, device_classes),
            daemon=False,
        )
        t.start()
        threads.append(t)
        logger.info(f"🚀 Launched server thread for {server_name}/{instance_name}")
        time.sleep(0.5)  # small stagger for Tango DB

    logger.info("📡 All servers launched. Waiting for them to run forever.")
    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
