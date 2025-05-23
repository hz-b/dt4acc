import numpy as np
from typing import Dict, List, Optional
from tango import DeviceProxy, DevFailed, Database, DbDevInfo, DbDatum
from dt4acc.core.utils.logger import get_logger
from dt4acc.data_model.identifiers import LatticeElementPropertyID, DevicePropertyID
from dt4acc.custom_epics.data.querries import get_unique_power_converters, get_magnets_per_power_converters
from dt4acc.custom_epics.ioc.handlers import update_manager, handle_device_update
from dt4acc.custom_tango.ioc.devices.magnet_device import MagnetDevice
from dt4acc.custom_tango.ioc.devices.power_converter_device import PowerConverterDevice
from dt4acc.custom_tango.server_config import (
    SERVER_NAME,
    SERVER_CLASS,
    SERVER_INSTANCE,
    DEVICE_NAME_FORMAT,
    FULL_DEVICE_NAME_FORMAT
)

logger = get_logger()

class DeviceInitializer:
    """
    Utility class for initializing Tango devices and their attributes.
    This class provides functionality similar to the EPICS PV initialization
    but using Tango's device and attribute system.
    """
    
    def __init__(self):
        self.element_cache: Dict[str, Dict] = {}
        self.device_cache: Dict[str, DeviceProxy] = {}
        # Initialize database
        try:
            # Try connecting to the database using the correct format
            self.db = Database()
            logger.info("Connected to Tango database using default connection")
        except Exception as e:
            logger.error(f"Failed to connect to Tango database: {str(e)}")
            raise
        
    def _format_device_name(self, name: str, device_type: str) -> str:
        """Format device name according to Tango convention."""
        print(f"\n[DEBUG] Formatting device name:")
        print(f"  - Input name: {name}")
        print(f"  - Device type: {device_type}")
        
        device_name = DEVICE_NAME_FORMAT.format(device_type=device_type, name=name)
        print(f"  - After DEVICE_NAME_FORMAT: {device_name}")
        
        full_name = FULL_DEVICE_NAME_FORMAT.format(device_name=device_name)
        print(f"  - Final full name: {full_name}")
        
        return full_name
        
    def _create_device(self, device_name: str, device_class: str) -> DeviceProxy:
        """Create a Tango device in the database."""
        try:
            print(f"\n[DEBUG] Creating device:")
            print(f"  - Input device_name: {device_name}")
            print(f"  - Input device_class: {device_class}")
            
            # Format device name according to Tango convention
            formatted_name = self._format_device_name(device_name, device_class)
            print(f"  - Formatted name: {formatted_name}")
            
            # Create device info
            dev_info = DbDevInfo()
            dev_info.name = formatted_name
            dev_info._class = device_class
            dev_info.server = SERVER_INSTANCE
            
            # Set device properties
            dev_info.properties = {
                "name": [device_name],  # Required property
                "magnet_list": []  # Will be set later if needed
            }
            
            print(f"  - Server instance: {SERVER_INSTANCE}")
            print(f"  - Device info:")
            print(f"    * Name: {dev_info.name}")
            print(f"    * Class: {dev_info._class}")
            print(f"    * Server: {dev_info.server}")
            print(f"    * Properties: {dev_info.properties}")
            
            # Add device to database
            self.db.add_device(dev_info)
            print("  - Device added to database successfully")
            
            # Create device proxy and wait for it to be ready
            device = DeviceProxy(formatted_name)
            device.ping()  # Wait for device to be ready
            print(f"  - Device proxy created and pinged successfully")
            
            # Set properties on the device
            try:
                print(f"  - Setting device properties:")
                print(f"    * Setting name property to: {device_name}")
                # First try to set properties using put_property
                device.put_property({"name": [device_name]})
                print(f"    * Name property set successfully")
                
                # Verify property was set
                props = device.get_property(["name"])
                print(f"    * Retrieved properties: {props}")
                if "name" in props and props["name"]:
                    print(f"    * Name property verified: {props['name']}")
                else:
                    print(f"    * WARNING: Name property not found in retrieved properties")
                    # Try alternative method to set property
                    print(f"    * Trying alternative method to set property")
                    self.db.put_device_property(formatted_name, {"name": [device_name]})
                    print(f"    * Property set using database method")
            except Exception as e:
                print(f"  - ERROR: Could not set name property: {str(e)}")
                raise
            
            self.device_cache[device_name] = device
            return device
            
        except Exception as e:
            print(f"\n[ERROR] Failed to create device:")
            print(f"  - Error: {str(e)}")
            logger.error(f"Error creating device {device_name}: {str(e)}")
            raise
        
    def _set_device_property(self, device: DeviceProxy, prop_name: str, prop_value: any):
        """Set a device property using the device update method."""
        try:
            # Convert value to string list properly
            if isinstance(prop_value, list):
                value_list = [str(v) for v in prop_value]
            else:
                value_list = [str(prop_value)]
                
            # Set the property directly on the device
            device.put_property({prop_name: value_list})
            logger.info(f"Set property {prop_name} to {prop_value} for device {device.dev_name()}")
            
        except Exception as e:
            logger.error(f"Error setting property {prop_name} for device {device.dev_name()}: {str(e)}")
            raise
        
    def initialize_all_devices(self):
        """
        Initializes all power converters and their associated magnets.
        same like to EPICS initialize_power_converter_pvs.
        """
        devices = {}
        try:
            for pc_name in get_unique_power_converters():
                magnets = get_magnets_per_power_converters(pc_name)
                pc = self.initialize_power_converter_device(pc_name, magnets)
                devices[pc_name] = pc
                
            logger.info(f"Initialized {len(devices)} power converter devices")
            return devices
            
        except Exception as e:
            logger.error(f"Error initializing devices: {str(e)}")
            raise
        
    def initialize_magnet_device(self, device_name: str, magnet_data: dict) -> DeviceProxy:
        """
        Initializes a magnet device with the given configuration.
        same as  to EPICS initialize_magnet_pvs.
        """
        try:
            print(f"\n[DEBUG] Initializing magnet device:")
            print(f"  - Device name: {device_name}")
            print(f"  - Magnet data: {magnet_data}")
            
            # Create device
            device = self._create_device(device_name, "MagnetDevice")
            print(f"  - Device created successfully")
            
            # Set properties
            self._set_device_property(device, "name", device_name)
            self._set_device_property(device, "type", magnet_data.get("type", "unknown"))
            print(f"  - Properties set successfully")
            
            # Initialize attributes
            device.write_attribute("magnetic_strength", 0.0)
            device.write_attribute("magnetic_strength_readback", 0.0)
            device.write_attribute("current", 0.0)
            device.write_attribute("power_supply_current", 0.0)
            device.write_attribute("x_position", 0.0)
            device.write_attribute("y_position", 0.0)
            print(f"  - Attributes initialized successfully")
            
            return device
            
        except Exception as e:
            print(f"\n[ERROR] Failed to initialize magnet device:")
            print(f"  - Error: {str(e)}")
            logger.error(f"Error initializing magnet device {device_name}: {str(e)}")
            raise
    
    def initialize_power_converter_device(self, pc_name: str, associated_magnets: List[dict]) -> DeviceProxy:
        """
        Initializes a power converter device and its associated magnets.
        as like  to EPICS add_pc_pvs.

        """
        try:
            print(f"\n[DEBUG] Initializing power converter device:")
            print(f"  - PC name: {pc_name}")
            print(f"  - Associated magnets: {associated_magnets}")
            
            # Create device
            device = self._create_device(pc_name, "PowerConverterDevice")
            print(f"  - Device created successfully")
            
            # Set properties
            try:
                print(f"  - Setting device properties:")
                props = {
                    "name": [pc_name],
                    "magnet_list": [magnet["name"] for magnet in associated_magnets]
                }
                print(f"    * Properties to set: {props}")
                device.put_property(props)
                print(f"    * Properties set successfully")
                
                # Verify properties were set
                retrieved_props = device.get_property(["name", "magnet_list"])
                print(f"    * Retrieved properties: {retrieved_props}")
                if "name" in retrieved_props and retrieved_props["name"]:
                    print(f"    * Name property verified: {retrieved_props['name']}")
                else:
                    print(f"    * WARNING: Name property not found in retrieved properties")
            except Exception as e:
                print(f"  - ERROR: Could not set properties: {str(e)}")
                raise
            
            # Initialize associated magnets
            for magnet_data in associated_magnets:
                self.initialize_magnet_device(magnet_data["name"], magnet_data)
                
            logger.info(f"Initialized power converter device {pc_name} with {len(associated_magnets)} associated magnets")
            return device
            
        except Exception as e:
            print(f"\n[ERROR] Failed to initialize power converter device:")
            print(f"  - Error: {str(e)}")
            logger.error(f"Error initializing power converter device {pc_name}: {str(e)}")
            raise
        
    def _get_device_proxy(self, device_name: str) -> DeviceProxy:
        """
        Get or create a device proxy for the given device name.

        """
        if device_name not in self.device_cache:
            formatted_name = self._format_device_name(device_name, "PowerConverterDevice" if "PC" in device_name else "MagnetDevice")
            self.device_cache[device_name] = DeviceProxy(formatted_name)
        return self.device_cache[device_name]
        
    def handle_device_update(self, device_name: str, property_id: str, value: any) -> None:
        """
        Handle device updates, similar to EPICS handle_device_update.

        """
        try:
            # Update the value in the update manager
            update_manager.update_value(device_name, property_id, value)
            
            # Get device proxy
            device = self._get_device_proxy(device_name)
            
            # Update device attribute based on property_id
            if property_id == "set_current":
                device.write_attribute("current_setpoint", value)
                device.write_attribute("current_readback", value)
            elif property_id == "K":
                device.write_attribute("magnetic_strength", value)
            elif property_id == "x":
                device.write_attribute("x_position", value)
            elif property_id == "y":
                device.write_attribute("y_position", value)
            elif property_id == "powersupply_current":
                device.write_attribute("current", value)
            elif property_id == "reference_frequency":
                device.write_attribute("frequency", value)
                
            logger.info(f"Updated device {device_name} property {property_id} to {value}")
            
        except Exception as e:
            logger.error(f"Error updating device {device_name}: {str(e)}")
            raise

def initialize_magnet_device(device_name: str, magnet_data: dict) -> DeviceProxy:
    """
    Initializes a magnet device with the given configuration.

    """
    try:
        magnet_name = magnet_data["name"]
        k_value = magnet_data.get("k", 0.0)
        
        # Get initial values from update manager
        val = update_manager.peek_engine(
            LatticeElementPropertyID(element_name=magnet_name, property="main_strength")
        )
        
        # Create device in database
        device = DeviceProxy(f"tango_server/test/MagnetDevice_{magnet_name}")
        
        # Initialize attributes
        device.write_attribute("magnetic_strength", k_value)
        device.write_attribute("magnetic_strength_readback", val)
        device.write_attribute("current", 0.0)
        device.write_attribute("power_supply_current", 0.0)
        device.write_attribute("x_position", 0.0)
        device.write_attribute("y_position", 0.0)
        device.write_attribute("Cm_set", k_value)
        
        logger.info(f"Initialized magnet device {magnet_name} with k_value {k_value}")
        return device
        
    except Exception as e:
        logger.error(f"Error initializing magnet device {magnet_data.get('name', 'unknown')}: {str(e)}")
        raise

def initialize_power_converter_device(pc_name: str, associated_magnets: List[dict]) -> DeviceProxy:
    """
    Initializes a power converter device and its associated magnets.
    i will enhacn this more
    """
    try:
        # Get initial current value from update manager
        vals = update_manager.device_value_from_peeking_engine(
            DevicePropertyID(device_name=pc_name, property="set_current")
        )
        start_val = np.asarray(vals).mean() if isinstance(vals, (list, np.ndarray)) else vals
        
        device = DeviceProxy(f"tango_server/test/PowerConverterDevice_{pc_name}")
        
        # Initialize attributes
        device.write_attribute("current_setpoint", start_val)
        device.write_attribute("current_readback", start_val)
        device.write_attribute("voltage", 0.0)
        device.write_attribute("status", "OFF")
        device.write_attribute("frequency", 0.0)
        
        # Initialize associated magnets
        for magnet_data in associated_magnets:
            initialize_magnet_device(pc_name, magnet_data)
            
        logger.info(f"Initialized power converter device {pc_name} with {len(associated_magnets)} associated magnets")
        return device
        
    except Exception as e:
        logger.error(f"Error initializing power converter device {pc_name}: {str(e)}")
        raise

def initialize_all_devices() -> Dict[str, DeviceProxy]:
    """
    Initializes all power converters and their associated magnets.
    same as like to EPICS initialize_power_converter_pvs.
    """
    devices = {}
    try:
        for pc_name in get_unique_power_converters():
            magnets = get_magnets_per_power_converters(pc_name)
            pc = initialize_power_converter_device(pc_name, magnets)
            devices[pc_name] = pc
            
        logger.info(f"Initialized {len(devices)} power converter devices")
        return devices
        
    except Exception as e:
        logger.error(f"Error initializing devices: {str(e)}")
        raise 