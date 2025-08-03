#!/usr/bin/env python3
"""
Complete Device Exporter - exports ALL magnetic and power converter devices.
"""

import os
import sys
import time
import threading
from typing import Dict, List, Optional
from tango import Database, DbDevInfo, DevFailed

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_tango.ioc.devices.power_converter_device import PowerConverterDevice
from dt4acc.custom_tango.ioc.devices.magnet_device import MagnetDevice
from dt4acc.custom_tango.ioc.devices.twiss_orbit_device import TwissOrbitDevice
from dt4acc.custom_tango.ioc.devices.bpm_device import BPMDevice

logger = get_logger()

class CompleteDeviceExporter:
    """Complete device exporter - exports ALL devices."""
    
    def __init__(self, timeout_seconds: int = 60, batch_size: int = 50):
        self.timeout_seconds = timeout_seconds
        self.batch_size = batch_size  
        self.exported_devices = []
        self.db = None
        self._init_database()
    
    def _init_database(self):
        """Initialize database connection with timeout."""
        try:
            logger.info("🔗 Initializing database connection...")
            self.db = Database()
            servers = self.db.get_server_list()
            logger.info(f"Database connected, found {len(servers)} servers")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def _format_device_name(self, name: str, device_type: str) -> str:
        """Format device name according to Tango conventions."""
        clean_name = name.replace(" ", "_").replace("-", "_").upper()
        return f"{device_type}_{clean_name}"
    
    def _safe_database_operation(self, operation, operation_name: str, timeout: int = None):
        """Execute database operation with timeout."""
        if timeout is None:
            timeout = self.timeout_seconds
        
        result = None
        error = None
        
        def db_worker():
            nonlocal result, error
            try:
                result = operation()
            except Exception as e:
                error = e
        
        thread = threading.Thread(target=db_worker)
        thread.daemon = True
        thread.start()
        
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            raise TimeoutError(f"Database operation '{operation_name}' timed out after {timeout} seconds")
        elif error:
            raise error
        else:
            return result
    
    def _export_devices_in_batches(self, devices: List[str], device_type: str, device_class) -> int:
        """Export devices in batches to avoid overwhelming the system."""
        if not devices:
            logger.warning(f" No {device_type} devices found")
            return 0
        
        logger.info(f" Found {len(devices)} {device_type} devices")
        logger.info(f"Exporting in batches of {self.batch_size}...")
        
        exported_count = 0
        failed_count = 0
        
        for i in range(0, len(devices), self.batch_size):
            batch = devices[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(devices) + self.batch_size - 1) // self.batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} devices)...")
            
            for device_name in batch:
                try:
                    formatted_name = self._format_device_name(device_name, device_type)
                    device_info = DbDevInfo()
                    device_info._class = device_class.__name__
                    device_info.server = "tango_server/test"
                    device_info.name = f"tango_server/test/{formatted_name}"
                    
                    self.db.add_device(device_info)
                    self.exported_devices.append(device_info.name)
                    exported_count += 1
                    
                    if exported_count % 10 == 0:
                        logger.info(f" Exported {exported_count} {device_type} devices so far...")
                    
                except Exception as e:
                    failed_count += 1
                    logger.warning(f" Failed to export {device_type} {device_name}: {e}")
                    continue
            
            if i + self.batch_size < len(devices):
                time.sleep(0.1)
        
        logger.info(f"Exported {exported_count} {device_type} devices")
        if failed_count > 0:
            logger.warning(f" Failed to export {failed_count} {device_type} devices")
        
        return exported_count
    
    def export_magnet_devices(self) -> int:
        """Export ALL magnet devices with timeout protection."""
        try:
            
            def get_magnet_data():
                from dt4acc.custom_epics.data.querries import get_magnets
                magnets = list(get_magnets())
                unique_magnets = list(set(magnet.get('name', '') for magnet in magnets if magnet.get('name')))
                return unique_magnets
            
            magnets = self._safe_database_operation(
                get_magnet_data, 
                "get_unique_magnets", 
                timeout=30
            )
            
            return self._export_devices_in_batches(magnets, "MagnetDevice", MagnetDevice)
            
        except Exception as e:
            logger.error(f"Magnet export failed: {e}")
            return 0
    
    def export_power_converter_devices(self) -> int:
        """Export ALL power converter devices with timeout protection."""
        try:
            logger.info("🔧 Exporting ALL power converter devices...")
            
            def get_pc_data():
                from dt4acc.custom_epics.data.querries import get_unique_power_converters
                return get_unique_power_converters()
            
            power_converters = self._safe_database_operation(
                get_pc_data, 
                "get_unique_power_converters", 
                timeout=30
            )
            
            return self._export_devices_in_batches(power_converters, "PowerConverterDevice", PowerConverterDevice)
            
        except Exception as e:
            logger.error(f" Power converter export failed: {e}")
            return 0
    
    def export_twiss_orbit_device(self) -> int:
        """Export TwissOrbit device."""
        try:
            logger.info("Exporting TwissOrbit device...")
            
            device_info = DbDevInfo()
            device_info._class = TwissOrbitDevice.__name__
            device_info.server = "tango_server/test"
            device_info.name = "tango_server/test/TwissOrbitDevice_MAIN"
            
            self.db.add_device(device_info)
            self.exported_devices.append(device_info.name)
            
            logger.info("Exported TwissOrbitDevice_MAIN")
            return 1
            
        except Exception as e:
            logger.error(f"TwissOrbit device export failed: {e}")
            return 0
    
    def export_bpm_device(self) -> int:
        """Export BPM device."""
        try:
            logger.info(" Exporting BPM device...")
            
            device_info = DbDevInfo()
            device_info._class = BPMDevice.__name__
            device_info.server = "tango_server/test"
            device_info.name = "tango_server/test/BPMDevice_MAIN"
            
            self.db.add_device(device_info)
            self.exported_devices.append(device_info.name)
            
            logger.info(" Exported BPMDevice_MAIN")
            return 1
            
        except Exception as e:
            logger.error(f" BPM device export failed: {e}")
            return 0
    
    def export_all_devices(self) -> Dict[str, int]:
        """Export ALL devices with comprehensive error handling."""
        logger.info("Starting COMPLETE device export...")
        start_time = time.time()
        
        results = {
            'power_converters': 0,
            'magnets': 0,
            'twiss_orbit': 0,
            'bpm': 0,
            'total': 0
        }
        
        try:
            results['power_converters'] = self.export_power_converter_devices()
            
            results['magnets'] = self.export_magnet_devices()
            
            results['twiss_orbit'] = self.export_twiss_orbit_device()
            
            results['bpm'] = self.export_bpm_device()
            
            results['total'] = sum([
                results['power_converters'],
                results['magnets'],
                results['twiss_orbit'],
                results['bpm']
            ])
            
            end_time = time.time()
            duration = end_time - start_time
            
          
            return results
            
        except Exception as e:
            return results
    
    def get_exported_devices(self) -> List[str]:
        """Get list of exported device names."""
        return self.exported_devices.copy()
    
    def verify_device_export(self, device_name: str) -> bool:
        """Verify if a device is exported (ping test)."""
        try:
            from tango import DeviceProxy
            proxy = DeviceProxy(device_name)
            proxy.ping()
            return True
        except Exception:
            return False
    
    def get_export_summary(self) -> Dict[str, any]:
        """Get detailed export summary."""
        return {
            'total_devices': len(self.exported_devices),
            'device_types': {
                'power_converters': len([d for d in self.exported_devices if 'PowerConverterDevice' in d]),
                'magnets': len([d for d in self.exported_devices if 'MagnetDevice' in d]),
                'twiss_orbit': len([d for d in self.exported_devices if 'TwissOrbitDevice' in d]),
                'bpm': len([d for d in self.exported_devices if 'BPMDevice' in d])
            },
            'devices': self.exported_devices
        } 