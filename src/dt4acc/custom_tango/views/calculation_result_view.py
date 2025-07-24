from datetime import datetime
from typing import Sequence, List, Union, Optional
import time
import asyncio
import itertools
import pandas as pd

import numpy as np
from tango import DeviceProxy, DevFailed, Database, DevState

from ...core.model.element_upate import ElementUpdate
from ...core.model.orbit import Orbit
from ...core.model.twiss import TwissWithAggregatedKValues, TwissForPlane
from ...core.utils.logger import get_logger
from ..config import SERVER_NAME, SERVER_INSTANCE, DEVICE_NAME_FORMAT
from ...custom_epics.data.constants import special_pvs, config
from ...custom_epics.utils.bpm_mimicry import BPMMimicry
from .bpm_data import BeamPositionPVs

logger = get_logger()

# Counter for orbit object updates (matching EPICS implementation)
counter = itertools.count()

def convert_to_list(data: Union[Sequence, np.ndarray]) -> List:
    """Convert sequence or numpy array to list with proper type handling"""
    if isinstance(data, np.ndarray):

        data = np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)
        return data.tolist()
    return list(data)

def update_orbit_device(device_name: str, orbit_result: Orbit):
    """Update orbit values in the Tango device"""
    try:
        device = DeviceProxy(device_name)

        device.write_attribute("orbit_x", convert_to_list(orbit_result.x))
        device.write_attribute("orbit_y", convert_to_list(orbit_result.y))
        device.write_attribute("orbit_names", convert_to_list(orbit_result.names))
        device.write_attribute("orbit_found", int(orbit_result.found))
        device.write_attribute("orbit_x0", convert_to_list(orbit_result.x0))
        logger.info(f"Successfully updated orbit values in device {device_name}")
    except Exception as e:
        logger.error(f"Failed to update orbit values in device {device_name}: {e}")
        raise

def update_twiss_device(device_name: str, twiss_result: TwissWithAggregatedKValues):
    """Update Twiss parameters in the Tango device"""
    try:
        device = DeviceProxy(device_name)

        device.write_attribute("twiss_alpha_x", convert_to_list(twiss_result.x.alpha))
        device.write_attribute("twiss_beta_x", convert_to_list(twiss_result.x.beta))
        device.write_attribute("twiss_nu_x", convert_to_list(twiss_result.x.nu))
        device.write_attribute("twiss_alpha_y", convert_to_list(twiss_result.y.alpha))
        device.write_attribute("twiss_beta_y", convert_to_list(twiss_result.y.beta))
        device.write_attribute("twiss_nu_y", convert_to_list(twiss_result.y.nu))
        device.write_attribute("twiss_names", convert_to_list(twiss_result.names))
        
        # Add tune values (missing in current Tango implementation)
        tune_x = float(twiss_result.x.tune) + np.random.uniform(-1e-12, 1e-12)  # Match EPICS noise
        tune_y = float(twiss_result.y.tune) + np.random.uniform(-1e-12, 1e-12)
        device.write_attribute("twiss_x_tune", tune_x)
        device.write_attribute("twiss_y_tune", tune_y)

        if hasattr(twiss_result, 'main_values') and twiss_result.main_values:
            for k in twiss_result.main_values:
                try:

                    value = float(k.value) if isinstance(k.value, (int, float, str)) else k.value
                    device.write_attribute(k.pv_name, value)
                    logger.debug(f"Updated magnet strength {k.pv_name} to {value}")
                except Exception as e:
                    logger.error(f"Failed to update magnet strength {k.pv_name}: {e}")
        
        logger.info(f"Successfully updated Twiss parameters in device {device_name}")
    except Exception as e:
        logger.error(f"Failed to update Twiss parameters in device {device_name}: {e}")
        raise



class ResultView:
    def __init__(self, *, prefix):
        """Initialize the ResultView with a prefix."""
        self.prefix = prefix

        self.device_name = f"tango_server/test/TwissOrbitDevice_MAIN"
        self.device = None
        self._initialized = False
        self.bpm_data = None  # Initialize bpm_data as None
        # Update BPM device name format
        self.bpm_pvs = BeamPositionPVs(prefix="tango_server/test")
        self.default_bpm_legacy_data = np.empty([2048], np.int16)
        self.default_bpm_legacy_data.fill(-2 ** 15 + 1)
        self.bpm_mimicry = None  # Will be set by set_bpm_mimicry
        self._last_update = datetime.now()
        self._update_interval = 1.0  # Increased to 1 second to reduce warnings
        self._is_monitoring = False
        self._monitor_task = None
        # Add reconnection parameters
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 3
        self._reconnect_delay = 1.0  # seconds
        
        # Add missing attributes to match EPICS implementation
        self.orbit_object_data = None
        self.default_twiss = None

    async def initialize(self):
        """Initialize the view and establish device connection."""
        try:
            await self._get_device()
            self._last_update = time.time()
            logger.info("ResultView initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize ResultView: {e}")
            return False

    async def _get_device(self):
        """Get or create device proxy with reconnection logic."""
        if self.device is None:
            try:
                device_name = "tango_server/test/TwissOrbitDevice_MAIN"
                self.device = DeviceProxy(device_name)
                self._reconnect_attempts = 0
                logger.info(f"Created device proxy for {device_name}")
            except Exception as e:
                self._reconnect_attempts += 1
                if self._reconnect_attempts >= self._max_reconnect_attempts:
                    logger.error(f"Max reconnection attempts reached: {e}")
                    raise
                logger.warning(f"Connection attempt {self._reconnect_attempts} failed: {e}")
                await asyncio.sleep(self._reconnect_delay)
                return await self._get_device()
        return self.device

    async def monitor_updates(self):
        """Monitor device updates and maintain connection."""
        if self._is_monitoring:
            logger.warning("Monitoring is already active")
            return

        self._is_monitoring = True
        logger.info("Starting update monitoring")

        while self._is_monitoring:
            try:
                current_time = time.time()
                if self._last_update is None or (current_time - self._last_update) >= self._update_interval:
                    await self.heart_beat()
                    self._last_update = current_time
                await asyncio.sleep(0.1)  # Small sleep to prevent CPU overuse
            except Exception as e:
                logger.error(f"Error in update monitoring: {e}")

                await asyncio.sleep(1.0)  # Longer sleep on error

    async def heart_beat(self):
        """
        Periodic heartbeat function to push default BPM data.
        Matches EPICS implementation behavior.
        """
        try:
            # Push default BPM data (matching EPICS behavior)
            try:
                await self.push_legacy_bpm_data(self.default_bpm_legacy_data)
            except Exception as e:
                logger.warning(f"BPM data push failed in heartbeat: {e}")
            
            # Push default Twiss data if available (matching EPICS behavior)
            if hasattr(self, 'default_twiss') and self.default_twiss is not None:
                try:
                    await self.push_twiss(self.default_twiss)
                except Exception as e:
                    logger.warning(f"Twiss data push failed in heartbeat: {e}")
            
            logger.debug(f"Heartbeat check at {datetime.now()}")
            
        except Exception as e:
            logger.error(f"Heartbeat check failed: {e}")
            # Don't raise the exception to keep heartbeat running
            logger.warning("Continuing heartbeat despite errors")

    def set_bpm_mimicry(self, bpm_mimicry):
        """Set BPM mimicry for legacy data handling."""
        if bpm_mimicry is None:
            logger.warning("BPM mimicry is None, BPM data updates will be disabled")
        self.bpm_mimicry = bpm_mimicry

    async def push_value(self, elm_update: ElementUpdate):
        """Push a single value update to the device (like EPICS)"""
        if elm_update.property_name == "K":
            pass  # Like EPICS
        else:
            property_name = 'x:set' if 'x' in elm_update.property_name else (
                'y:set' if 'dy' in elm_update.property_name else elm_update.property_name)
            
            try:
                # Log like EPICS - show what's being updated
                logger.info(f"Updating {elm_update.element_id}:{property_name} to {elm_update.value}")
                print(f"🔧 Updating {elm_update.element_id}:{property_name} to {elm_update.value}")  # Visible logging
                
                device_name = f"{self.prefix}/PowerConverterDevice_VS3P2T8R"
                device = DeviceProxy(device_name)
                device.write_attribute(property_name, elm_update.value)
                
                # Log successful update like EPICS
                logger.info(f"Successfully updated {elm_update.element_id}:{property_name}")
                print(f"✅ Successfully updated {elm_update.element_id}:{property_name}")  # Visible logging
                
            except Exception as e:
                logger.error(f"Failed to update {elm_update.element_id}:{property_name}: {e}")
                print(f"❌ Failed to update {elm_update.element_id}:{property_name}: {e}")  # Visible logging

    def _check_bpm_attributes(self, device):
        """Check all BPM device attributes."""
        try:
            print("\nChecking BPM device attributes:")
            # Get list of all attributes
            attr_list = device.get_attribute_list()
            print(f"Available attributes: {attr_list}")
            
            # Try to read each attribute
            for attr_name in attr_list:
                try:
                    attr_value = device.read_attribute(attr_name)
                    print(f"Attribute: {attr_name}")
                    print(f"  - Value: {attr_value.value}")
                    print(f"  - Type: {type(attr_value.value)}")
                    print(f"  - Quality: {attr_value.quality}")
                except Exception as e:
                    print(f"  - Error reading {attr_name}: {e}")
            print("\n")
        except Exception as e:
            print(f"Error checking BPM attributes: {e}")

    async def push_orbit(self, orbit_result: Orbit):
        """Push orbit data to the device."""
        try:
            logger.info('Orbit pushing view')  # Like EPICS
            print('🔧 Orbit pushing view')  # Visible logging
            device = await self._get_device()
            

            def pad_array(arr, target_length=config.n_elements):
                if len(arr) < target_length:
                    return np.pad(arr, (0, target_length - len(arr)), mode='constant', constant_values=0)
                return arr[:target_length]
            

            orbit_x = pad_array(convert_to_list(orbit_result.x))
            orbit_y = pad_array(convert_to_list(orbit_result.y))
            orbit_x0 = pad_array(convert_to_list(orbit_result.x0))
            orbit_names = pad_array(convert_to_list(orbit_result.names))
            

            # Write orbit attributes
            device.write_attribute("beam/orbit/x", orbit_x)
            device.write_attribute("beam/orbit/y", orbit_y)
            device.write_attribute("beam/orbit/x0", orbit_x0)
            device.write_attribute("beam/orbit/names", orbit_names)

            found_value = bool(orbit_result.found) if isinstance(orbit_result.found, (int, float)) else orbit_result.found
            device.write_attribute("beam/orbit/found", found_value)
            
            logger.info('Orbit pushed view')  # Like EPICS
            print('✅ Orbit pushed view')  # Visible logging
        except Exception as exc:
            logger.warning('Orbit view pushing failed: %s', exc)  # Like EPICS
            print(f'❌ Orbit view pushing failed: {exc}')  # Visible logging
            raise exc

    async def push_twiss(self, twiss_result: TwissWithAggregatedKValues):
        """Push Twiss data to the device."""
        if twiss_result is None:
            return
            
        try:
            # logger.warning('Twiss pushing view')  # Like EPICS (commented out)
            device = await self._get_device()
            
            # Store default Twiss data (matching EPICS behavior)
            self.default_twiss = twiss_result

            def pad_array(arr, target_length=config.n_elements):
                if len(arr) < target_length:
                    return np.pad(arr, (0, target_length - len(arr)), mode='constant', constant_values=0)
                return arr[:target_length]  # Truncate if longer
            
            # Convert and pad Twiss data
            alpha_x = pad_array(convert_to_list(twiss_result.x.alpha))
            beta_x = pad_array(convert_to_list(twiss_result.x.beta))
            nu_x = pad_array(convert_to_list(twiss_result.x.nu))
            alpha_y = pad_array(convert_to_list(twiss_result.y.alpha))
            beta_y = pad_array(convert_to_list(twiss_result.y.beta))
            nu_y = pad_array(convert_to_list(twiss_result.y.nu))
            names = pad_array(convert_to_list(twiss_result.names))
            
            # Write attributes
            device.write_attribute("beam/twiss/x/alpha", alpha_x)
            device.write_attribute("beam/twiss/x/beta", beta_x)
            device.write_attribute("beam/twiss/x/nu", nu_x)
            device.write_attribute("beam/twiss/y/alpha", alpha_y)
            device.write_attribute("beam/twiss/y/beta", beta_y)
            device.write_attribute("beam/twiss/y/nu", nu_y)
            device.write_attribute("beam/twiss/names", names)
            
            # Add tune values (matching EPICS implementation)
            tune_x = float(twiss_result.x.tune) + np.random.uniform(-1e-12, 1e-12)
            tune_y = float(twiss_result.y.tune) + np.random.uniform(-1e-12, 1e-12)
            device.write_attribute("beam/twiss/x/tune", tune_x)
            device.write_attribute("beam/twiss/y/tune", tune_y)
            
            # Update magnet strengths if available
            if hasattr(twiss_result, 'main_values') and twiss_result.main_values:
                for k in twiss_result.main_values:
                    try:
                        value = float(k.value) if isinstance(k.value, (int, float, str)) else k.value
                        device.write_attribute(k.pv_name, value)
                        logger.debug(f"Updated magnet strength {k.pv_name} to {value}")
                    except Exception as e:
                        logger.error(f"Failed to update magnet strength {k.pv_name}: {e}")
            
            logger.info('Twiss pushed view')  # Like EPICS
        except Exception as exc:
            logger.error(f"Twiss view pushing failed: {exc}")
            raise exc

    async def push_bpms(self, orbit_data):
        """
        BESSY specific way of setting BPM and pushing it.
        Matches EPICS implementation behavior.
        """
        if not self.bpm_mimicry:
            raise ValueError("BPM Mimicry not set in ResultView")
        try:
            logger.info(f"pushing legacy bpm data")  # Like EPICS
            df_bpm = self.bpm_mimicry.extract_bpm_legacy_data_to_df(orbit_data)
            bpm_legacy_data = self.bpm_mimicry.bpm_legacy_data_df_to_array(df_bpm)
            self.default_bpm_legacy_data = bpm_legacy_data
            await self.push_legacy_bpm_data(bpm_legacy_data)
            
            # Create orbit object data (matching EPICS implementation)
            orbit_object_data = df_bpm.copy()
            mm2nm = 1e6
            orbit_object_data.x = df_bpm.x * mm2nm
            orbit_object_data.y = df_bpm.y * mm2nm
            self.orbit_object_data = orbit_object_data
            await self.push_orbit_object(self.orbit_object_data)
            
        except Exception as e:
            logger.error(f"Error processing orbit data: {e}")
            raise

    async def push_legacy_bpm_data(self, bpm_legacy_data: Sequence[np.int16] = None):
        """
        Push BPM data to Tango. If no data is provided, push the default data.
        Matches EPICS implementation behavior.
        """
        if bpm_legacy_data is None:
            logger.info(f"Pushing legacy BPM data at {datetime.now()}")  # Like EPICS
            bpm_legacy_data = self.default_bpm_legacy_data
            
        try:
            if not isinstance(bpm_legacy_data, np.ndarray):
                bpm_legacy_data = np.asarray(bpm_legacy_data, dtype=np.int16)
            elif bpm_legacy_data.dtype != np.int16:
                bpm_legacy_data = bpm_legacy_data.astype(np.int16)
                
            if bpm_legacy_data.shape != (2048,):
                logger.warning(f"Reshaping BPM data from {bpm_legacy_data.shape} to (2048,)")
                if len(bpm_legacy_data) > 2048:
                    bpm_legacy_data = bpm_legacy_data[:2048]
                else:
                    padded_data = np.zeros(2048, dtype=np.int16)
                    padded_data[:len(bpm_legacy_data)] = bpm_legacy_data
                    bpm_legacy_data = padded_data
            
            # Check if bpm_data is initialized
            if self.bpm_data is None:
                logger.warning("BPM data object is not initialized, skipping BPM data push")
                return
            
            await self.bpm_data.set_data(bpm_legacy_data)
            
            # Push orbit object data if available (matching EPICS behavior)
            if hasattr(self, 'orbit_object_data') and self.orbit_object_data is not None:
                logger.info(f"Pushing orbit object data at {datetime.now()}")  # Like EPICS
                await self.push_orbit_object(self.orbit_object_data)
                
        except Exception as e:
            logger.error(f"Failed to push BPM data: {e}")
            # Don't raise the exception to prevent heartbeat from failing
            logger.warning("Continuing heartbeat despite BPM data error")

    async def push_orbit_object(self, bpm_data: pd.DataFrame):
        """
        Push orbit object data to Tango device.
        Matches EPICS implementation for ORBITCC data.
        """
        try:
            device = await self._get_device()
            
            # Convert to numpy array and ravel (matching EPICS implementation)
            pos = np.array(bpm_data.loc[:, ["x", "y"]]).ravel()
            bpm_names = [str(val) for val in bpm_data.index]
            count = next(counter)
            
            # Write to device attributes (matching EPICS PV structure)
            device.write_attribute("ORBITCC:rdPos", pos.tolist())
            device.write_attribute("ORBITCC:rdBpmNames", bpm_names)
            device.write_attribute("ORBITCC:count", count)
            
            logger.info(f"Orbit object data pushed successfully, count: {count}")
        except Exception as e:
            logger.error(f"Error processing orbit object data: {e}")  # Like EPICS
            raise
