#!/usr/bin/env python3
import sys
from tango.server import run
from dt4acc.custom_tango.ioc.devices.tango_device_setup import get_all_device_classes

def main():
    if len(sys.argv) != 3:
        print("Usage: single_server.py <server_name> <instance_name>")
        sys.exit(1)

    server_name = sys.argv[1]
    instance_name = sys.argv[2]

    device_classes = get_all_device_classes()
    run(device_classes, args=[server_name, instance_name])

if __name__ == "__main__":
    main()
