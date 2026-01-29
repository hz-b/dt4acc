#!/usr/bin/env python3
import os
import sys
import asyncio
import threading
from tango.server import run
from dt4acc.custom_tango.ioc.devices.tango_device_setup import get_all_device_classes
from dt4acc.core.utils.logger import get_logger
import time

logger = get_logger()

# created global event loop for the tango server thread
global_event_loop = None


def _enable_debugger(port=5678):
    import pydevd_pycharm
    pydevd_pycharm.settrace(
            "localhost",
            port=port,
            stdout_to_server=True,
            stderr_to_server=True,
            suspend=True,
        )


def enable_debugger():
    port=5678
    while True:
        try:
            _enable_debugger(port)
        except ImportError as ie:
            raise ie
        except ConnectionRefusedError:
            logger.warning(f"waiting for debug process for {os.getpid()=} {port=}")
            time.sleep(10)

def post_init_callback():
    logger.warning(f"Server {sys.argv} instaniated")

def main_loop(server_name: str, instance_name: str, event=None):
    if server_name.upper().startswith("A"):
        logger.warning(f"preparing debug for process {server_name=} {os.getpid()}")
        enable_debugger()
    os.nice(4)

    if event is None:
        cb = post_init_callback
    else:
        def cb():
            logger.warning(f"Server {server_name}, {instance_name} instaniated... setting event")
            event.set()
            logger.warning(f"Server {server_name}, {instance_name} event is set")
    global global_event_loop
    try:
      
        global_event_loop = asyncio.get_event_loop()
        if global_event_loop.is_closed():
            global_event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(global_event_loop)
            
    except RuntimeError:
        
        global_event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(global_event_loop)
    
    try:
        device_classes = get_all_device_classes()
        run(device_classes, args=[server_name, instance_name], post_init_callback=cb, raises=True)
        sys.stderr(f"Tango server {server_name}/{instance_name} finished")
    except Exception as e:
        sys.stderr(f"Tango server {server_name}/{instance_name} failed: {e}")
        logger.error(f"Tango server {server_name}/{instance_name} failed: {e}")
        raise
    finally:
        if global_event_loop and not global_event_loop.is_closed():
            try:
                global_event_loop.close()
            except Exception:
                pass


def main():

    if len(sys.argv) != 3:
        print("Usage: single_server.py <server_name> <instance_name>")
        sys.exit(1)

    main_loop(server_name = sys.argv[1], instance_name = sys.argv[2])


if __name__ == "__main__":
    main()
