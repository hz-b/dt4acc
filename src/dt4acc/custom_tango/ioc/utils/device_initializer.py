import numpy as np
from typing import Dict, List, Optional
from tango import DeviceProxy, DevFailed, Database, DbDevInfo, DbDatum
from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_epics.ioc.liasion_translation_manager import LatticeElementPropertyID, DevicePropertyID
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
import time

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
        try:

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
        

        device_type = device_type.strip()
        if device_type.lower() == "powerconverterdevice":
            device_type = "PowerConverterDevice"
        elif device_type.lower() == "magnetdevice":
            device_type = "MagnetDevice"
        elif device_type.lower() == "twissorbitdevice":
            device_type = "TwissOrbitDevice"
        elif device_type.lower() == "bpmdevice":
            device_type = "BPMDevice"
        
        device_name = DEVICE_NAME_FORMAT.format(device_type=device_type, name=name)
        print(f"  - After DEVICE_NAME_FORMAT: {device_name}")
        
        full_name = FULL_DEVICE_NAME_FORMAT.format(device_name=device_name)
        print(f"  - Final full name: {full_name}")
        
        return full_name
        
    def _create_device(self, device_name: str, device_class: str) -> None:
        """Create a Tango device in the database."""
        try:
            print(f"\n[DEBUG] Creating device:")
            print(f"  - Input device_name: {device_name}")
            print(f"  - Input device_class: {device_class}")
            
            formatted_name = self._format_device_name(device_name, device_class)
            print(f"  - Formatted name: {formatted_name}")
            
            dev_info = DbDevInfo()
            dev_info.name = formatted_name
            dev_info._class = device_class
            dev_info.server = SERVER_INSTANCE
            

            dev_info.properties = {
                "name": [device_name],
                "magnet_list": []  
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
            
           
            print("  - Device registered in database (proxy creation deferred)")
            
            return None
            
        except Exception as e:
            print(f"\n[ERROR] Failed to create device:")
            print(f"  - Error: {str(e)}")
            logger.error(f"Error creating device {device_name}: {str(e)}")
            raise
        
    def _set_device_property(self, device: DeviceProxy, prop_name: str, prop_value: any):
        """Set a device property using the device update method."""
        try:
            if isinstance(prop_value, list):
                value_list = [str(v) for v in prop_value]
            else:
                value_list = [str(prop_value)]
                

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
        device_count = 0
        try:
            for pc_name in get_unique_power_converters():
                magnets = get_magnets_per_power_converters(pc_name)
                self.initialize_power_converter_device(pc_name, magnets)
                device_count += 1
                
            logger.info(f"Registered {device_count} power converter devices in database")
            return {"status": "registered", "count": device_count}
            
        except Exception as e:
            logger.error(f"Error initializing devices: {str(e)}")
            raise
        
    def initialize_magnet_device(self, device_name: str, magnet_data: dict) -> None:
        """
        Initializes a magnet device with the given configuration.
        same as  to EPICS initialize_magnet_pvs.
        """
        try:
            print(f"\n[DEBUG] Initializing magnet device:")
            print(f"  - Device name: {device_name}")
            print(f"  - Magnet data: {magnet_data}")
            
            self._create_device(device_name, "MagnetDevice")
            print(f"  - Device registered successfully")
            
            print(f"  - Properties and attributes will be set when server is running")
            
            return None
            
        except Exception as e:
            print(f"\n[ERROR] Failed to initialize magnet device:")
            print(f"  - Error: {str(e)}")
            logger.error(f"Error initializing magnet device {device_name}: {str(e)}")
            raise
    
    def initialize_power_converter_device(self, pc_name: str, associated_magnets: List[dict]) -> None:
        """
        Initializes a power converter device and its associated magnets.
        as like  to EPICS add_pc_pvs.

        """
        try:
            print(f"\n[DEBUG] Initializing power converter device:")
            print(f"  - PC name: {pc_name}")
            print(f"  - Associated magnets: {associated_magnets}")
            
            self._create_device(pc_name, "PowerConverterDevice")
            print(f"  - Device registered successfully")
            
            print(f"  - Properties will be set when server is running")
            
            for magnet_data in associated_magnets:
                self.initialize_magnet_device(magnet_data["name"], magnet_data)
                
            logger.info(f"Initialized power converter device {pc_name} with {len(associated_magnets)} associated magnets")
            return None
            
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
            update_manager.update_value(device_name, property_id, value)
            
            device = self._get_device_proxy(device_name)
            
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
        
        val = update_manager.peek_engine(
            LatticeElementPropertyID(element_name=magnet_name, property="main_strength")
        )
        
        device = DeviceProxy(f"tango_server/test/MagnetDevice_{magnet_name}")
        
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
        vals = update_manager.device_value_from_peeking_engine(
            DevicePropertyID(device_name=pc_name, property="set_current")
        )
        start_val = np.asarray(vals).mean() if isinstance(vals, (list, np.ndarray)) else vals
        
        device = DeviceProxy(f"tango_server/test/PowerConverterDevice_{pc_name}")
        
        device.write_attribute("current_setpoint", start_val)
        device.write_attribute("current_readback", start_val)
        device.write_attribute("voltage", 0.0)
        device.write_attribute("status", "OFF")
        device.write_attribute("frequency", 0.0)
        
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