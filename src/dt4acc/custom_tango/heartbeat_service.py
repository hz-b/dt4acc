#!/usr/bin/env python3
"""
Heartbeat Service - Provides periodic updates to Tango devices
Mirrors EPICS heartbeat functionality with Tango-specific implementations.
"""

import asyncio
import threading
import time
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional

# Add the parent directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from tango import DeviceProxy, Database
from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_epics.data.constants import config, special_pvs
from dt4acc.custom_epics.data.querries import get_unique_power_converters

logger = get_logger()


class HeartbeatService:
    """
    Heartbeat service that provides periodic updates to Tango devices.
    Mirrors EPICS heartbeat functionality.
    """
    
    def __init__(self):
        """Initialize the heartbeat service."""
        self._running = False
        self._heartbeat_thread = None
        self._update_interval = 1.0  # 1 second interval (matching EPICS)
        self._last_update = datetime.now()
        self._device_cache = {}
        
        # Default BPM data (matching EPICS)
        self._default_bpm_data = [-32767] * 2048
        
        # Default Twiss data
        self._default_twiss_data = {
            'alpha_x': [0.0] * config.n_elements,
            'beta_x': [0.0] * config.n_elements,
            'nu_x': [0.0] * config.n_elements,
            'alpha_y': [0.0] * config.n_elements,
            'beta_y': [0.0] * config.n_elements,
            'nu_y': [0.0] * config.n_elements,
            'names': [''] * config.n_elements,
            'x_tune': 0.0,
            'y_tune': 0.0
        }
        
        # Default orbit data
        self._default_orbit_data = {
            'x': [0.0] * config.n_elements,
            'y': [0.0] * config.n_elements,
            'x0': [0.0] * config.n_elements,
            'names': [''] * config.n_elements,
            'found': False
        }
        
        logger.info("Heartbeat service initialized")

    def start(self):
        """Start the heartbeat service."""
        if self._running:
            logger.warning("Heartbeat service is already running")
            return
        
        self._running = True
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
        logger.info("Heartbeat service started")

    def stop(self):
        """Stop the heartbeat service."""
        self._running = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)
        logger.info("Heartbeat service stopped")

    def _heartbeat_loop(self):
        """Main heartbeat loop that runs in a separate thread."""
        while self._running:
            try:
                # Update all devices with heartbeat data
                self._update_all_devices()
                time.sleep(self._update_interval)
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
                time.sleep(self._update_interval)

    def _update_all_devices(self):
        """Update all registered devices with heartbeat data."""
        try:
            # Update BPM devices
            self._update_bpm_devices()
            
            # Update Twiss/Orbit devices
            self._update_twiss_orbit_devices()
            
            # Update power converter devices (with default values)
            self._update_power_converter_devices()
            
            self._last_update = datetime.now()
            logger.debug(f"Heartbeat update completed at {self._last_update}")
            
        except Exception as e:
            logger.error(f"Failed to update devices in heartbeat: {e}")

    def _update_bpm_devices(self):
        """Update BPM devices with default data."""
        try:
            db = Database()
            devices = db.get_device_exported("SimpleTangoServer/test/*")
            bpm_devices = [d for d in devices if "bpm" in d]
            
            for device_name in bpm_devices:
                try:
                    device = DeviceProxy(device_name)
                    
                    # Update BPM data
                    device.write_attribute("bdata", self._default_bpm_data)
                    
                    # Count is auto-incrementing, so we don't need to update it
                    
                except Exception as e:
                    logger.warning(f"Failed to update BPM device {device_name}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to update BPM devices: {e}")

    def _update_twiss_orbit_devices(self):
        """Update Twiss/Orbit devices with default data."""
        try:
            db = Database()
            devices = db.get_device_exported("SimpleTangoServer/test/*")
            twiss_orbit_devices = [d for d in devices if "twiss_orbit" in d]
            
            for device_name in twiss_orbit_devices:
                try:
                    device = DeviceProxy(device_name)
                    
                    # Update orbit data
                    device.write_attribute("beam/orbit/x", self._default_orbit_data['x'])
                    device.write_attribute("beam/orbit/y", self._default_orbit_data['y'])
                    device.write_attribute("beam/orbit/x0", self._default_orbit_data['x0'])
                    device.write_attribute("beam/orbit/names", self._default_orbit_data['names'])
                    device.write_attribute("beam/orbit/found", self._default_orbit_data['found'])
                    
                    # Update Twiss data
                    device.write_attribute("beam/twiss/x/alpha", self._default_twiss_data['alpha_x'])
                    device.write_attribute("beam/twiss/x/beta", self._default_twiss_data['beta_x'])
                    device.write_attribute("beam/twiss/x/nu", self._default_twiss_data['nu_x'])
                    device.write_attribute("beam/twiss/y/alpha", self._default_twiss_data['alpha_y'])
                    device.write_attribute("beam/twiss/y/beta", self._default_twiss_data['beta_y'])
                    device.write_attribute("beam/twiss/y/nu", self._default_twiss_data['nu_y'])
                    device.write_attribute("beam/twiss/names", self._default_twiss_data['names'])
                    device.write_attribute("beam/twiss/x/tune", self._default_twiss_data['x_tune'])
                    device.write_attribute("beam/twiss/y/tune", self._default_twiss_data['y_tune'])
                    
                    # Update BPM data in Twiss/Orbit device
                    device.write_attribute("beam/bpm/data", self._default_bpm_data)
                    
                    # Update orbit object data (use 0.0 instead of NaN for Tango compatibility)
                    orbit_pos = [0.0] * 256
                    orbit_buttons = [0.0] * 512
                    orbit_bpm_names = [''] * 128
                    device.write_attribute("ORBITCC/rdPos", orbit_pos)
                    device.write_attribute("ORBITCC/rdButtons", orbit_buttons)
                    device.write_attribute("ORBITCC/rdBpmNames", orbit_bpm_names)
                    
                    # Update master clock data
                    device.write_attribute("master_clock/freq", 500.0)
                    device.write_attribute("lattice_info/ref_freq", 500.0)
                    device.write_attribute("lattice_info/ref_freq/khz/up", 500)
                    device.write_attribute("lattice_info/ref_freq/khz/frac", 0)
                    
                    # Update cavity frequencies
                    cavity_freqs = [500.0] * 4  # Default for 4 cavities
                    device.write_attribute("cavity_frequencies", cavity_freqs)
                    
                except Exception as e:
                    logger.warning(f"Failed to update Twiss/Orbit device {device_name}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to update Twiss/Orbit devices: {e}")

    def _update_power_converter_devices(self):
        """Update power converter devices with default values."""
        try:
            power_converters = get_unique_power_converters()
            
            for pc_name in power_converters[:5]:  # Update first 5 power converters
                try:
                    device_name = f"SimpleTangoServer/test/power_converter_{pc_name}"
                    device = DeviceProxy(device_name)
                    
                    # Set default current values (only writable attributes)
                    device.write_attribute("current_setpoint", 0.0)
                    # Only writable attributes: current_setpoint and frequency
                    # current_readback, voltage, and status are read-only
                    device.write_attribute("frequency", 500.0)
                    
                except Exception as e:
                    logger.warning(f"Failed to update power converter {pc_name}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to update power converter devices: {e}")

    def set_default_bpm_data(self, bpm_data: List[int]):
        """Set default BPM data for heartbeat updates."""
        if len(bpm_data) != 2048:
            raise ValueError("BPM data must have length 2048")
        self._default_bpm_data = bpm_data
        logger.info("Default BPM data updated")

    def set_default_twiss_data(self, twiss_data: Dict):
        """Set default Twiss data for heartbeat updates."""
        self._default_twiss_data.update(twiss_data)
        logger.info("Default Twiss data updated")

    def set_default_orbit_data(self, orbit_data: Dict):
        """Set default orbit data for heartbeat updates."""
        self._default_orbit_data.update(orbit_data)
        logger.info("Default orbit data updated")

    def get_status(self) -> Dict:
        """Get the current status of the heartbeat service."""
        return {
            'running': self._running,
            'last_update': self._last_update.isoformat(),
            'update_interval': self._update_interval,
            'thread_alive': self._heartbeat_thread.is_alive() if self._heartbeat_thread else False
        }


# Global heartbeat service instance
_heartbeat_service = None


def get_heartbeat_service() -> HeartbeatService:
    """Get the global heartbeat service instance."""
    global _heartbeat_service
    if _heartbeat_service is None:
        _heartbeat_service = HeartbeatService()
    return _heartbeat_service


def start_heartbeat_service():
    """Start the global heartbeat service."""
    service = get_heartbeat_service()
    service.start()
    return service


def stop_heartbeat_service():
    """Stop the global heartbeat service."""
    global _heartbeat_service
    if _heartbeat_service:
        _heartbeat_service.stop()
        _heartbeat_service = None 