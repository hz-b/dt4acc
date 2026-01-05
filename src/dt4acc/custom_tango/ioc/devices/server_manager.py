#!/usr/bin/env python3
import os
import sys
import time
import signal
import subprocess

from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_tango.ioc.devices.tango_device_setup import register_all_devices

logger = get_logger()

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

    # 3) wait + allow Ctrl+C clean shutdown
    def shutdown(*_):
        logger.warning("Shutting down all servers...")
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