#!/usr/bin/env python3
import os
import sys
import asyncio
import threading
from tango.server import run
from dt4acc.custom_tango.ioc.devices.tango_device_setup import get_all_device_classes
from dt4acc.core.utils.logger import get_logger

logger = get_logger()

# created global event loop for the tango server thread
global_event_loop = None


def main():
    
    if len(sys.argv) != 3:
        print("Usage: single_server.py <server_name> <instance_name>")
        sys.exit(1)

    server_name = sys.argv[1]
    instance_name = sys.argv[2]

    os.nice(4)
  
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
        run(device_classes, args=[server_name, instance_name])
        
    except Exception as e:
        logger.error(f"Tango server {server_name}/{instance_name} failed: {e}")
        raise
    finally:
        if global_event_loop and not global_event_loop.is_closed():
            try:
                global_event_loop.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
