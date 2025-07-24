#!/usr/bin/env python3
"""
Clean Tango Server - no heartbeat, runs independently.
Heartbeat is handled by separate update monitor service.
"""

import os
import sys
import time
from tango.server import run
from tango import Database, DbDevInfo, DevFailed

# Add the src directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dt4acc.core.utils.logger import get_logger
from dt4acc.core.views.shared_view import get_view_instance
from dt4acc.custom_tango.config import (
    SERVER_NAME,
    SERVER_CLASS,
    SERVER_INSTANCE,
    DEVICE_CLASSES
)

# Import device classes
from dt4acc.custom_tango.ioc.devices.power_converter_device import PowerConverterDevice
from dt4acc.custom_tango.ioc.devices.magnet_device import MagnetDevice
from dt4acc.custom_tango.ioc.devices.twiss_orbit_device import TwissOrbitDevice

logger = get_logger()

# Global variables
view = None

def register_server():
    """Register the Tango server in the database."""
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

def register_device_classes():
    """Register device classes in the database."""
    try:
        db = Database()
        for device_type, device_class in DEVICE_CLASSES.items():
            device_info = DbDevInfo()
            device_info._class = device_class
            device_info.server = SERVER_INSTANCE
            device_info.name = f"{SERVER_NAME}/{SERVER_INSTANCE}/{device_class}"
            try:
                db.add_device(device_info)
                logger.info(f"Registered device class: {device_class}")
            except Exception as e:
                logger.info(f"Device class {device_class} already registered: {e}")
    except Exception as e:
        logger.error(f"Failed to register device classes: {e}")
        raise

def startup_with_complete_export():
    """
    Startup function with complete device export (no heartbeat).
    """
    global view
    
    try:
        logger.info("🚀 Starting Tango server initialization (no heartbeat)...")
        print("🚀 Starting Tango server initialization (no heartbeat)...")
        
        # Set environment variable for Tango view
        os.environ["server"] = "tango"
        
        # Get the Tango view instance
        view = get_view_instance()
        logger.info(f"Using view: {type(view).__name__}")
        print(f"✅ Using view: {type(view).__name__}")
        
        # Initialize accelerator manager (like EPICS) to connect view to updates
        logger.info("🔧 Initializing accelerator manager to connect view to updates...")
        print("🔧 Initializing accelerator manager to connect view to updates...")
        try:
            from dt4acc.core.accelerators.accelerator_manager import AcceleratorManager
            accelerator_manager = AcceleratorManager(prefix="tango_server/test")
            accelerator_manager.initialize()  # This calls setup_event_subscriptions()
            logger.info("✅ Accelerator manager initialized - view now connected to updates")
            print("✅ Accelerator manager initialized - view now connected to updates")
        except Exception as acc_error:
            logger.warning(f"⚠️ Accelerator manager initialization failed: {acc_error}")
            print(f"⚠️ Accelerator manager initialization failed: {acc_error}")
            logger.warning("⚠️ View will not receive magnetic updates")
            print("⚠️ View will not receive magnetic updates")
        
        # Register server and device classes
        logger.info("Registering server and device classes...")
        print("✅ Registering server and device classes...")
        register_server()
        register_device_classes()
        
        # Export ALL devices using the complete device exporter
        logger.info("🔧 EXPORTING ALL DEVICES WITH COMPLETE DEVICE EXPORTER...")
        print("🔧 EXPORTING ALL DEVICES WITH COMPLETE DEVICE EXPORTER...")
        try:
            from dt4acc.custom_tango.device_exporter_complete import CompleteDeviceExporter
            logger.info("✅ CompleteDeviceExporter imported successfully")
            print("✅ CompleteDeviceExporter imported successfully")

            exporter = CompleteDeviceExporter(timeout_seconds=60, batch_size=50)
            logger.info("✅ CompleteDeviceExporter created successfully")
            print("✅ CompleteDeviceExporter created successfully")

            export_results = exporter.export_all_devices()
            logger.info("✅ Complete device export completed")
            print("✅ Complete device export completed")

            logger.info(f"📊 COMPLETE DEVICE EXPORT SUMMARY:")
            logger.info(f"  - Power converters: {export_results.get('power_converters', 0)}")
            logger.info(f"  - Magnets: {export_results.get('magnets', 0)}")
            logger.info(f"  - TwissOrbit devices: {export_results.get('twiss_orbit', 0)}")
            logger.info(f"  - BPM devices: {export_results.get('bpm', 0)}")
            logger.info(f"  - Total exported: {export_results.get('total', 0)}")
            
            print(f"📊 COMPLETE DEVICE EXPORT SUMMARY:")
            print(f"  - Power converters: {export_results.get('power_converters', 0)}")
            print(f"  - Magnets: {export_results.get('magnets', 0)}")
            print(f"  - TwissOrbit devices: {export_results.get('twiss_orbit', 0)}")
            print(f"  - BPM devices: {export_results.get('bpm', 0)}")
            print(f"  - Total exported: {export_results.get('total', 0)}")

        except Exception as export_error:
            logger.error(f"❌ COMPLETE DEVICE EXPORT FAILED: {export_error}")
            print(f"❌ COMPLETE DEVICE EXPORT FAILED: {export_error}")
            logger.error(f"❌ Continuing without device export...")
            print(f"❌ Continuing without device export...")
        
        logger.info("✅ Tango server initialization completed (no heartbeat)")
        print("✅ Tango server initialization completed (no heartbeat)")
        
    except Exception as e:
        logger.error(f"Failed to initialize Tango server: {e}")
        print(f"❌ Failed to initialize Tango server: {e}")
        raise

class TangoServer:
    """Clean Tango server class (no heartbeat)."""
    
    def __init__(self, instance_name="test"):
        self.instance_name = instance_name
        self.device_classes = [TwissOrbitDevice, PowerConverterDevice, MagnetDevice]
        self.view = None
    

    
    def run_server(self):
        """Run the clean Tango server (no heartbeat)."""
        try:
            logger.info(f"🚀 Starting clean Tango server, instance: {self.instance_name}")
            print(f"🚀 Starting clean Tango server, instance: {self.instance_name}")
            
            # Set environment variable for Tango view
            os.environ["server"] = "tango"
            
            # Initialize devices with complete export
            startup_with_complete_export()
            
            # Test view initialization
            try:
                test_view = get_view_instance()
                logger.info(f"Main thread: Got view instance: {type(test_view).__name__}")
                print(f"✅ Main thread: Got view instance: {type(test_view).__name__}")
            except Exception as e:
                logger.error(f"Failed to get view instance in main thread: {e}")
                print(f"❌ Failed to get view instance in main thread: {e}")
            
            # Start the Tango server with proper instance name
            logger.info("🚀 Starting Tango server with device classes:")
            print("🚀 Starting Tango server with device classes:")
            for device_class in self.device_classes:
                logger.info(f"  - {device_class.__name__}")
                print(f"  - {device_class.__name__}")
            
            # Use the tango.server.run function with proper arguments
            logger.info("🚀 Calling tango.server.run()...")
            print("🚀 Calling tango.server.run()...")
            run(self.device_classes)
            
        except Exception as e:
            logger.error(f"Failed to start Tango server: {e}")
            print(f"❌ Failed to start Tango server: {e}")
            raise

def main():
    """Main entry point for clean Tango server (no heartbeat)."""
    try:
        print("🚀 STARTING CLEAN TANGO SERVER (NO HEARTBEAT)...")
        logger.info("🚀 STARTING CLEAN TANGO SERVER (NO HEARTBEAT)...")
        
        # Check if instance name is provided as command line argument
        if len(sys.argv) > 1:
            instance_name = sys.argv[1]
            logger.info(f"Using instance name: {instance_name}")
        else:
            # Use default instance name
            instance_name = "test"
            logger.info(f"No instance name provided, using default: {instance_name}")
        
        # Set the instance name in the global configuration
        global SERVER_INSTANCE
        SERVER_INSTANCE = instance_name
        
        server = TangoServer(instance_name)
        server.run_server()
        logger.info("✅ Clean Tango server started!")
        print("✅ Clean Tango server started!")
    except KeyboardInterrupt:
        logger.info("Tango server stopped by user")
        print("Tango server stopped by user")
    except Exception as e:
        logger.error(f"Tango server failed: {e}")
        print(f"❌ Tango server failed: {e}")
        raise

if __name__ == "__main__":
    main() 