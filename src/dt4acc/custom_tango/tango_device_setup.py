#!/usr/bin/env python3
"""
Tango Device Setup - Mirrors EPICS pv_setup.py structure
Registers all devices from ioc/devices folder and aligns with EPICS implementation.
"""

import numpy as np
from tango import Database, DbDevInfo, DevFailed, AttrWriteType, DevState
from tango.server import Device, attribute, command, device_property
from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_epics.data.querries import (
    get_unique_power_converters,
    get_magnets_per_power_converters,
)
from dt4acc.custom_epics.ioc.handlers import update_manager, handle_device_update
from dt4acc.custom_epics.data.constants import config, special_pvs, cavity_names
from bact_twin_architecture.data_model.identifiers import (
    LatticeElementPropertyID,
    DevicePropertyID,
)

# Import existing device classes
from dt4acc.custom_tango.ioc.devices.magnet_device import MagnetDevice
from dt4acc.custom_tango.ioc.devices.power_converter_device import PowerConverterDevice
from dt4acc.custom_tango.ioc.devices.twiss_orbit_device import TwissOrbitDevice
from dt4acc.custom_tango.ioc.devices.bpm_device import BPMDevice
from dt4acc.custom_tango.ioc.devices.cavity_device import CavityDevice
from dt4acc.custom_tango.ioc.devices.master_clock_device import MasterClockDevice
from dt4acc.custom_tango.ioc.devices.other_pvs_device import OtherPVsDevice

logger = get_logger()


def flag_not_handling(device_name: str, val: object):
    """Log when a device update is not being handled."""
    logger.warning("Not handling update of device %s to %s", device_name, val)


def initialize_magnet_devices():
    """
    Initialize all magnet devices - equivalent to initialize_magnet_pvs() in EPICS.
    
    Returns:
        list: List of magnet device names and properties
    """
    magnet_devices = []
    
    try:
        logger.info("🔧 Initializing magnet devices...")
        print("🔧 Initializing magnet devices...")
        
        for pc_name in get_unique_power_converters():
            magnets = get_magnets_per_power_converters(pc_name)
            for magnet in magnets:
                magnet_name = magnet["name"]
                logger.info(f"  - Creating magnet device: {magnet_name}")
                print(f"  - Creating magnet device: {magnet_name}")
                
                # Store magnet device info for registration
                magnet_info = {
                    "name": magnet_name,
                    "k_value": magnet.get("k", 0.0),
                    "type": magnet.get("type", "unknown"),
                    "class": "MagnetDevice"
                }
                
                magnet_devices.append(magnet_info)
        
        logger.info(f"✅ Created {len(magnet_devices)} magnet devices")
        print(f"✅ Created {len(magnet_devices)} magnet devices")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize magnet devices: {e}")
        print(f"❌ Failed to initialize magnet devices: {e}")
    
    return magnet_devices


def initialize_power_converter_devices():
    """
    Initialize all power converter devices - equivalent to initialize_power_converter_pvs() in EPICS.
    
    Returns:
        list: List of power converter device names and properties
    """
    power_converter_devices = []
    
    try:
        logger.info("🔧 Initializing power converter devices...")
        print("🔧 Initializing power converter devices...")
        
        for pc_name in get_unique_power_converters():
            logger.info(f"  - Creating power converter device: {pc_name}")
            print(f"  - Creating power converter device: {pc_name}")
            
            # Get associated magnets
            magnets = get_magnets_per_power_converters(pc_name)
            magnet_list = [item["name"] for item in magnets]
            
            # Store power converter device info for registration
            pc_info = {
                "name": pc_name,
                "magnet_list": magnet_list,
                "class": "PowerConverterDevice"
            }
            
            power_converter_devices.append(pc_info)
        
        logger.info(f"✅ Created {len(power_converter_devices)} power converter devices")
        print(f"✅ Created {len(power_converter_devices)} power converter devices")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize power converter devices: {e}")
        print(f"❌ Failed to initialize power converter devices: {e}")
    
    return power_converter_devices


def register_all_devices(server_name="SimpleTangoServer", instance_name="test"):
    """
    Register all devices in the Tango database.
    
    Args:
        server_name (str): Name of the Tango server
        instance_name (str): Instance name
    """
    try:
        logger.info("📝 Registering all devices in database...")
        print("📝 Registering all devices in database...")
        
        db = Database()
        
        # Register magnet devices
        magnet_devices = initialize_magnet_devices()
        for i, device_info in enumerate(magnet_devices):
            device_name = f"magnet_{device_info['name']}"
            db_device_info = DbDevInfo()
            db_device_info._class = device_info['class']
            db_device_info.server = f"{server_name}/{instance_name}"
            db_device_info.name = f"{server_name}/{instance_name}/{device_name}"
            try:
                db.add_device(db_device_info)
                logger.info(f"  ✅ Registered magnet device: {device_name}")
            except Exception as e:
                logger.info(f"  ⚠️ Magnet device {device_name} already registered: {e}")
        
        # Register power converter devices
        power_converter_devices = initialize_power_converter_devices()
        for i, device_info in enumerate(power_converter_devices):
            device_name = f"power_converter_{device_info['name']}"
            db_device_info = DbDevInfo()
            db_device_info._class = device_info['class']
            db_device_info.server = f"{server_name}/{instance_name}"
            db_device_info.name = f"{server_name}/{instance_name}/{device_name}"
            try:
                db.add_device(db_device_info)
                logger.info(f"  ✅ Registered power converter device: {device_name}")
            except Exception as e:
                logger.info(f"  ⚠️ Power converter device {device_name} already registered: {e}")
        
        # Register Twiss/Orbit device (contains all twiss, orbit, and BPM attributes)
        db_device_info = DbDevInfo()
        db_device_info._class = "TwissOrbitDevice"
        db_device_info.server = f"{server_name}/{instance_name}"
        db_device_info.name = f"{server_name}/{instance_name}/twiss_orbit_device"
        try:
            db.add_device(db_device_info)
            logger.info("  ✅ Registered Twiss/Orbit device (includes BPM attributes)")
        except Exception as e:
            logger.info(f"  ⚠️ Twiss/Orbit device already registered: {e}")
        
        # Register Master Clock device (dedicated device for master clock functionality)
        db_device_info = DbDevInfo()
        db_device_info._class = "MasterClockDevice"
        db_device_info.server = f"{server_name}/{instance_name}"
        db_device_info.name = f"{server_name}/{instance_name}/master_clock_device"
        try:
            db.add_device(db_device_info)
            logger.info("  ✅ Registered Master Clock device")
        except Exception as e:
            logger.info(f"  ⚠️ Master Clock device already registered: {e}")
        
        # Register Other PVs device (dedicated device for dummy and current values)
        db_device_info = DbDevInfo()
        db_device_info._class = "OtherPVsDevice"
        db_device_info.server = f"{server_name}/{instance_name}"
        db_device_info.name = f"{server_name}/{instance_name}/other_pvs_device"
        try:
            db.add_device(db_device_info)
            logger.info("  ✅ Registered Other PVs device")
        except Exception as e:
            logger.info(f"  ⚠️ Other PVs device already registered: {e}")
        
        # Register BPM device (if separate BPM functionality is needed)
        db_device_info = DbDevInfo()
        db_device_info._class = "BPMDevice"
        db_device_info.server = f"{server_name}/{instance_name}"
        db_device_info.name = f"{server_name}/{instance_name}/bpm_device"
        try:
            db.add_device(db_device_info)
            logger.info("  ✅ Registered BPM device")
        except Exception as e:
            logger.info(f"  ⚠️ BPM device already registered: {e}")
        
        # Register cavity devices (one per cavity)
        for cavity_name in cavity_names:
            device_name = f"cavity_{cavity_name}"
            db_device_info = DbDevInfo()
            db_device_info._class = "CavityDevice"
            db_device_info.server = f"{server_name}/{instance_name}"
            db_device_info.name = f"{server_name}/{instance_name}/{device_name}"
            # Note: Device properties are set in the device class itself, not during registration
            try:
                db.add_device(db_device_info)
                logger.info(f"  ✅ Registered cavity device: {device_name}")
            except Exception as e:
                logger.info(f"  ⚠️ Cavity device {device_name} already registered: {e}")
        
        logger.info("✅ All devices registered successfully")
        print("✅ All devices registered successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to register devices: {e}")
        print(f"❌ Failed to register devices: {e}")
        raise


def get_all_device_classes():
    """
    Get all device classes for the Tango server.
    
    Returns:
        list: List of all device classes
    """
    device_classes = []
    
    try:
        logger.info("🔧 Collecting all device classes...")
        print("🔧 Collecting all device classes...")
        
        # Add existing device classes - these contain all the attributes as methods
        device_classes.extend([
            MagnetDevice,
            PowerConverterDevice,
            TwissOrbitDevice,  # Contains all twiss, orbit, and BPM attributes
            BPMDevice,
            CavityDevice,  # Dedicated device for cavity management
            MasterClockDevice,  # Dedicated device for master clock management
            OtherPVsDevice,  # Dedicated device for other PVs (dummy, current)
        ])
        
        logger.info(f"✅ Collected {len(device_classes)} device classes")
        print(f"✅ Collected {len(device_classes)} device classes")
        
    except Exception as e:
        logger.error(f"❌ Failed to collect device classes: {e}")
        print(f"❌ Failed to collect device classes: {e}")
    
    return device_classes 