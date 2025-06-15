import os
import sys
import time
import asyncio
import threading
from tango.server import run
from tango import Database, DbDevInfo, DbDatum, DevFailed
from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_tango.ioc.utils.device_initializer import DeviceInitializer
from dt4acc.custom_tango.config import (
    SERVER_NAME,
    SERVER_CLASS,
    SERVER_INSTANCE,
    DEVICE_CLASSES
)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dt4acc.custom_tango.ioc.devices.power_converter_device import PowerConverterDevice
from dt4acc.custom_tango.ioc.devices.magnet_device import MagnetDevice
from dt4acc.custom_tango.ioc.devices.twiss_orbit_device import TwissOrbitDevice
from dt4acc.custom_tango.ioc.devices.bpm_device import BPMDevice
from dt4acc.custom_tango.ioc.BPM_setup import setup_bpm_device

logger = get_logger()

def register_server():
    try:
        db = Database()
        if SERVER_INSTANCE in db.get_server_list():
            logger.info(f"Server {SERVER_INSTANCE} already exists")
            return
        server_info = DbDevInfo()
        server_info._class = SERVER_CLASS
        server_info.server = SERVER_INSTANCE
        server_info.name = f"{SERVER_NAME}/{SERVER_INSTANCE}/{SERVER_CLASS}"
        db.add_device(server_info)
        logger.info(f"Server {SERVER_INSTANCE} registered successfully")
    except Exception as e:
        logger.error(f"Failed to register server: {e}")
        raise

def register_devices():
    try:
        db = Database()
        for device_type, device_class in DEVICE_CLASSES.items():
            device_info = DbDevInfo()
            device_info._class = device_class
            device_info.server = SERVER_INSTANCE
            device_info.name = f"{SERVER_NAME}/{SERVER_INSTANCE}/{device_class}"
            try:
                db.add_device(device_info)
                print(f"Registered device class: {device_class}")
            except Exception as e:
                print(f"Device class {device_class} already registered: {e}")
    except Exception as e:
        logger.error(f"Failed to register devices: {e}")
        raise

class TangoServer:
    def __init__(self):
        self.device_classes = [TwissOrbitDevice, BPMDevice,PowerConverterDevice,MagnetDevice]

    def run_server(self):
        try:
            print("Starting Tango server initialization...")
            register_server()
            register_devices()
            print("Starting server with devices:")
            for device_class in self.device_classes:
                print(f"  - {device_class.__name__}")
            print("Starting Tango server...")
            run(self.device_classes)
        except Exception as e:
            print(f"Failed to start server: {e}")
            raise

def main():
    TangoServer().run_server()

if __name__ == "__main__":
    main()