#!/usr/bin/env python3

import os
import sys
import time
import threading
from tango.server import run
from tango import Database

from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_tango.ioc.devices.tango_device_setup import (
    register_all_devices,
    get_all_device_classes,
)

logger = get_logger()


# ----------------------------------------------------------------------
# UTIL: Extract server name and instance from Soleil Tango name
#
#   AN10-AR/EM/SCF.11   → server = "AN10-AR/EM"
#                      → instance = "EM"
# ----------------------------------------------------------------------
def extract_server_from_name(device_name: str):
    parts = device_name.split("/")
    if len(parts) != 3:
        raise ValueError(f"Invalid Soleil device name: {device_name}")
    domain, family, _ = parts
    return f"{domain}/{family}", family     # server string, instance


# ----------------------------------------------------------------------
# START A SINGLE TANGO SERVER
# ----------------------------------------------------------------------
def start_server_for(domain, family, device_classes):
    server = f"{domain}/{family}"
    instance = family

    logger.info(f"🚀 Starting Tango server {server} (instance={instance})")

    try:
        # IMPORTANT:
        # run() EXPECTS: run(device_classes, args=[server, instance])
        run(device_classes, args=[server, instance])
    except Exception as e:
        logger.error(f"❌ Failed to start server {server}: {e}")


# ----------------------------------------------------------------------
# MAIN ENTRYPOINT
# ----------------------------------------------------------------------
def main():
    logger.info("📡 Starting Soleil Tango Server Manager")

    # STEP 1 — Register devices into DB
    logger.info("📡 Registering ALL Soleil devices into Tango DB...")
    register_all_devices()   # NO server_name/instance_name → Soleil style
    logger.info("✔ Device registration DONE.")

    # STEP 2 — Retrieve all Tango devices from DB
    logger.info("📡 Fetching device list from Tango DB")
    db = Database()
    all_devs = [d.name for d in db.get_device_list("*/*/*")]

    # STEP 3 — Determine unique Soleil servers (domain/family pairs)
    servers = set()
    for devname in all_devs:
        try:
            domain, family, member = devname.split("/")
            servers.add((domain, family))
        except ValueError:
            # Skip virtual (PHYSICS/SOLEIL/...) and dservers
            continue

    logger.info(f"🔎 Found {len(servers)} Soleil Tango servers to start.")

    # STEP 4 — Start each Soleil server in its own thread
    device_classes = get_all_device_classes()

    threads = []
    for domain, family in servers:
        t = threading.Thread(
            target=start_server_for,
            args=(domain, family, device_classes),
            daemon=False,
        )
        t.start()
        threads.append(t)
        time.sleep(0.5)  # small stagger is good for Tango DB load

        logger.info(f"🚀 Launched server thread for {domain}/{family}")

    # STEP 5 — Wait for all servers (unless user Ctrl+C)
    logger.info("📡 All servers launched. Waiting for them to run forever.")
    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
