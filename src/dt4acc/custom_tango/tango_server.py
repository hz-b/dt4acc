import os
import sys
import time
from tango.server import run
from tango import Database, DbDevInfo, DbDatum, DevFailed
from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_tango.ioc.utils.device_initializer import DeviceInitializer

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dt4acc.custom_tango.ioc.devices.power_converter_device import PowerConverterDevice
from dt4acc.custom_tango.ioc.devices.magnet_device import MagnetDevice
from dt4acc.custom_tango.server_config import (
    SERVER_NAME,
    SERVER_CLASS,
    SERVER_INSTANCE
)

logger = get_logger()

def list_server_devices():
    """
    List all devices registered with the server.
    """
    try:
        db = Database()
        device_list = db.get_device_name(SERVER_INSTANCE, "*")
        print("\nRegistered devices:")
        print("-" * 50)
        for device in device_list:
            print(f"Device: {device}")
        print("-" * 50)
        return device_list
    except Exception as e:
        print(f"Error listing devices: {e}")
        return []

def start_tango_server():
    """
    Start the Tango server and initialize all devices.
    """
    try:
        # Initialize database
        db = Database()
        
        # Initialize device initializer
        initializer = DeviceInitializer()
        
        # Initialize all devices
        devices = initializer.initialize_all_devices()
        
        logger.info(f"Tango server started with {len(devices)} devices")
        return devices
        
    except Exception as e:
        logger.error(f"Error starting Tango server: {str(e)}")
        raise

def main():

    print(f"Starting Tango server: {SERVER_NAME}")
    
    # Create Tango database
    db = Database()
    
    try:
        server_list = db.get_server_list()
        if SERVER_INSTANCE in server_list:
            print(f"Server {SERVER_INSTANCE} already exists, skipping registration")
            list_server_devices()
        else:
            device_info = DbDevInfo()
            device_info._class = SERVER_CLASS
            device_info.server = SERVER_INSTANCE
            device_info.name = SERVER_NAME
            
            try:
                db.add_device(device_info)
                print("Server registered in database successfully")
            except Exception as e:
                print(f"Warning: Server registration error: {e}")
    except Exception as e:
        print(f"Warning: Could not check server existence: {e}")
    
    device_classes = [PowerConverterDevice, MagnetDevice]
    
    print("Starting server...")
    run(device_classes)

if __name__ == "__main__":
    main() 