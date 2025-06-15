from datetime import datetime
from typing import Sequence, List, Union, Optional
import time
import asyncio

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






# class TwissOrbitView:
#     def __init__(self, *, device_name: str):
#         self.device_name = device_name
#         self.device = DeviceProxy(device_name)
#         self.default_bpm_data = np.empty([2048], np.int16)
#         self.default_bpm_data.fill(-2 ** 15 + 1)
#         self.bpm_mimicry = None

#     def set_bpm_mimicry(self, bpm_mimicry):
#         """Set BPM mimicry for legacy data handling."""
#         self.bpm_mimicry = bpm_mimicry

#     def push_value(self, elm_update: ElementUpdate):
#         """Push a single element update to the device."""
#         if elm_update.property_name == "K":
#             return
        
#         property_name = 'x:set' if 'x' in elm_update.property_name else (
#             'y:set' if 'dy' in elm_update.property_name else elm_update.property_name)
        
#         try:
#             self.device.write_attribute(f"{elm_update.element_id}:{property_name}", elm_update.value)
#             logger.info(f"Updated {elm_update.element_id}:{property_name}")
#         except Exception as e:
#             logger.error(f"Failed to update {elm_update.element_id}:{property_name}: {e}")

#     def _check_bpm_attributes(self, device):
#         """Check all BPM device attributes."""
#         try:
#             print("\nChecking BPM device attributes:")
#             # Get list of all attributes
#             attr_list = device.get_attribute_list()
#             print(f"Available attributes: {attr_list}")
            
#             # Try to read each attribute
#             for attr_name in attr_list:
#                 try:
#                     attr_value = device.read_attribute(attr_name)
#                     print(f"Attribute: {attr_name}")
#                     print(f"  - Value: {attr_value.value}")
#                     print(f"  - Type: {type(attr_value.value)}")
#                     print(f"  - Quality: {attr_value.quality}")
#                 except Exception as e:
#                     print(f"  - Error reading {attr_name}: {e}")
#             print("\n")
#         except Exception as e:
#             print(f"Error checking BPM attributes: {e}")

#     async def push_orbit(self, orbit: Orbit):
#         """Push orbit data to the device."""
#         try:
#             logger.info("Pushing orbit data to device")
#             device = await self._get_device()
#             print(f"orbit.found: {orbit.found}")
#             print("device is", device)
#             print(f"type of orbit.found: {type(orbit.found)}")
#             print("***")
            
#             # Check BPM device attributes before writing
#             self._check_bpm_attributes(device)
            
#             # Pad arrays to match expected length
#             def pad_array(arr, target_length=config.n_elements):
#                 if len(arr) < target_length:
#                     return np.pad(arr, (0, target_length - len(arr)), mode='constant', constant_values=0)
#                 return arr[:target_length]  # Truncate if longer
            
#             # Convert and pad orbit data
#             orbit_x = pad_array(convert_to_list(orbit.x))
#             orbit_y = pad_array(convert_to_list(orbit.y))
#             orbit_x0 = pad_array(convert_to_list(orbit.x0))
#             orbit_names = pad_array(convert_to_list(orbit.names))
            
#             # Write attributes
#             print("writing attributes...")
#             print(f"Type orbit.x: {type(orbit.x)}")
#             device.write_attribute("beam/orbit/x", orbit_x)
#             print("wrote the x")
#             device.write_attribute("beam/orbit/y", orbit_y)
#             device.write_attribute("beam/orbit/x0", orbit_x0)
#             device.write_attribute("beam/orbit/names", orbit_names)
#             print("now writing found")
#             # Convert found to proper boolean type
#             found_value = bool(orbit.found) if isinstance(orbit.found, (int, float)) else orbit.found
#             device.write_attribute("beam/orbit/found", found_value)
#             print("write the found*")
            
#             # Check BPM device attributes after writing
#             self._check_bpm_attributes(device)
            
#             # Try to read back the found attribute to verify
#             try:
#                 found_value = device.read_attribute("beam/orbit/found").value
#                 print(f"Successfully wrote and read back found attribute: {found_value}")
#             except Exception as e:
#                 print(f"Warning: Could not read back found attribute: {e}")
            
#             logger.info("Orbit data pushed successfully")
#         except Exception as exc:
#             logger.error(f"Orbit view pushing failed: {exc}")
#             raise exc

#     def push_twiss(self, twiss_result: TwissWithAggregatedKValues):
#         """Push Twiss data to the device."""
#         logger.info('Pushing Twiss data')
#         try:
#             # Push Twiss parameters
#             self.device.write_attribute("beam/twiss/x/alpha", twiss_result.x.alpha)
#             self.device.write_attribute("beam/twiss/x/beta", twiss_result.x.beta)
#             self.device.write_attribute("beam/twiss/x/nu", twiss_result.x.nu)
#             self.device.write_attribute("beam/twiss/y/alpha", twiss_result.y.alpha)
#             self.device.write_attribute("beam/twiss/y/beta", twiss_result.y.beta)
#             self.device.write_attribute("beam/twiss/y/nu", twiss_result.y.nu)
            
#             # Push magnet strengths
#             if twiss_result.main_values:
#                 pv_names = [k.pv_name for k in twiss_result.main_values]
#                 values = [k.value for k in twiss_result.main_values]
#                 self.device.update_magnet_strengths(pv_names, values)
            
#             logger.info('Twiss data pushed successfully')
#         except Exception as e:
#             logger.error(f'Failed to push Twiss data: {e}')
#             raise

#     async def push_bpms(self, orbit: Orbit):
#         """Push BPM data to the device."""
#         try:
#             logger.info("Pushing BPM data to device")
#             device = await self._get_device()
            
#             # Initialize BPM data if not already done
#             if self.bpm_data is None:
#                 self.bpm_data = BeamPositionPVs(prefix=self.device_name)
            
#             # Create BPM data array with fixed length of 2048
#             bpm_data = np.zeros(2048, dtype=np.int16)
            
#             # Fill the first part with orbit data converted to microns
#             for i in range(min(len(orbit.x), 2048)):
#                 bpm_data[i] = int(orbit.x[i] * 1000)  # Convert to microns
            
#             # Set BPM data
#             await self.bpm_data.set_data(bpm_data)
#             logger.info("BPM data pushed successfully")
            
#         except Exception as exc:
#             logger.error(f"BPM data pushing failed: {exc}")
#             raise exc

#     async def push_legacy_bpm_data(self, bpm_legacy_data: Optional[Sequence[np.int16]] = None):
#         """Push BPM data to the device"""
#         if bpm_legacy_data is None:
#             bpm_legacy_data = self.default_bpm_data
            
#         try:
#             # Ensure data is in the correct format
#             if not isinstance(bpm_legacy_data, np.ndarray):
#                 bpm_legacy_data = np.asarray(bpm_legacy_data, dtype=np.int16)
#             elif bpm_legacy_data.dtype != np.int16:
#                 bpm_legacy_data = bpm_legacy_data.astype(np.int16)
                
#             # Ensure data has correct shape
#             if bpm_legacy_data.shape != (2048,):
#                 logger.warning(f"Reshaping BPM data from {bpm_legacy_data.shape} to (2048,)")
#                 if len(bpm_legacy_data) > 2048:
#                     bpm_legacy_data = bpm_legacy_data[:2048]
#                 else:
#                     padded_data = np.zeros(2048, dtype=np.int16)
#                     padded_data[:len(bpm_legacy_data)] = bpm_legacy_data
#                     bpm_legacy_data = padded_data
            
#             logger.info(f"Pushing legacy BPM data at {datetime.now()}")
#             # Use BeamPositionPVs to set data
#             await self.bpm_data.set_data(bpm_legacy_data)
#             logger.info("BPM data pushed successfully")
#         except Exception as e:
#             logger.error(f"Failed to push BPM data: {e}")
#             raise

#     async def heart_beat(self):
#         """Periodic heartbeat function"""
#         try:
#             # Use BeamPositionPVs heartbeat
#             await self.bpm_data.heart_beat()
#             # Also ping the TwissOrbit device
#             device = self.device
#             device.ping()
#             logger.debug(f"Heartbeat check at {datetime.now()}")
#         except Exception as e:
#             logger.error(f"Heartbeat check failed: {e}")

#     def _check_server_running(self):
#         """Check if the Tango server is running."""
#         try:
#             db = Database()
#             server_list = db.get_server_list()
#             if SERVER_INSTANCE not in server_list:
#                 logger.error(f"Tango server {SERVER_INSTANCE} is not running")
#                 raise RuntimeError(f"Tango server {SERVER_INSTANCE} is not running")
#             logger.info(f"Tango server {SERVER_INSTANCE} is running")
#         except Exception as e:
#             logger.error(f"Failed to check server status: {e}")
#             raise

#     def _get_device(self):
#         """Get the TwissOrbit device proxy with retry mechanism."""
#         # First check if server is running
#         self._check_server_running()
        
#         max_retries = 3
#         retry_delay = 1  # seconds
        
#         for attempt in range(max_retries):
#             try:
#                 device = DeviceProxy(self.device_name)
#                 # Test connection
#                 device.ping()
#                 print(f"Successfully connected to device {self.device_name}")
#                 return device
#             except Exception as e:
#                 if attempt < max_retries - 1:
#                     logger.warning(f"Attempt {attempt + 1} failed to connect to device {self.device_name}: {e}")
#                     logger.info(f"Retrying in {retry_delay} seconds...")
#                     time.sleep(retry_delay)
#                 else:
#                     logger.error(f"Failed to connect to device {self.device_name} after {max_retries} attempts: {e}")
#                     raise






class ResultView:
    def __init__(self, prefix: str):
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
        """Enhanced periodic heartbeat function with comprehensive checks."""
        try:

            device = await self._get_device()
            
            # Check BPM device
            if not self.bpm_data:
                logger.warning("BPM device not connected, attempting to reconnect...")
                await self.bpm_data.initialize()
            
            # Perform heartbeat checks
            await self.bpm_data.heart_beat()
            device.ping()
            
            # Verify device state
            state = device.state()
            if state != DevState.ON:
                logger.warning(f"Device not in ON state: {state}")
            
            # Check last update time
            if self._last_update:
                time_since_update = time.time() - self._last_update
                if time_since_update > self._update_interval * 2:
                    logger.warning(f"Long delay since last update: {time_since_update:.1f}s")
            
            logger.debug(f"Heartbeat check successful at {datetime.now()}")
            
        except Exception as e:
            logger.error(f"Heartbeat check failed: {e}")
            # Reset device connection on failure
            self.device = None
            self.bpm_data = None
            raise

    def set_bpm_mimicry(self, bpm_mimicry):
        """Set BPM mimicry for legacy data handling."""
        if bpm_mimicry is None:
            logger.warning("BPM mimicry is None, BPM data updates will be disabled")
        self.bpm_mimicry = bpm_mimicry

    async def push_value(self, elm_update: ElementUpdate):
        """Push a single value update to the device"""
        if elm_update.property_name == "K":
            return
        
        property_name = 'x:set' if 'x' in elm_update.property_name else (
            'y:set' if 'dy' in elm_update.property_name else elm_update.property_name)
        
        try:
            device_name = f"{self.prefix}/PowerConverterDevice_VS3P2T8R"
            device = DeviceProxy(device_name)
            device.write_attribute(property_name, elm_update.value)
            logger.info(f"Updated {elm_update.element_id}:{property_name}")
        except Exception as e:
            logger.error(f"Failed to update {elm_update.element_id}:{property_name}: {e}")

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

    async def push_orbit(self, orbit: Orbit):
        """Push orbit data to the device."""
        try:
            logger.info("Pushing orbit data to device")
            device = await self._get_device()
            print(f"orbit.found: {orbit.found}")
            print("device is", device)
            print(f"type of orbit.found: {type(orbit.found)}")
            print("***")
            

            def pad_array(arr, target_length=config.n_elements):
                if len(arr) < target_length:
                    return np.pad(arr, (0, target_length - len(arr)), mode='constant', constant_values=0)
                return arr[:target_length]
            

            orbit_x = pad_array(convert_to_list(orbit.x))
            orbit_y = pad_array(convert_to_list(orbit.y))
            orbit_x0 = pad_array(convert_to_list(orbit.x0))
            orbit_names = pad_array(convert_to_list(orbit.names))
            

            print("writing attributes...")
            print(f"Type orbit.x: {type(orbit.x)}")
            device.write_attribute("beam/orbit/x", orbit_x)
            print("wrote the x")
            device.write_attribute("beam/orbit/y", orbit_y)
            device.write_attribute("beam/orbit/x0", orbit_x0)
            device.write_attribute("beam/orbit/names", orbit_names)
            print("now writing found")

            found_value = bool(orbit.found) if isinstance(orbit.found, (int, float)) else orbit.found
            device.write_attribute("beam/orbit/found", found_value)
            print("write the found*")
            
            try:
                found_value = device.read_attribute("beam/orbit/found").value
                print(f"Successfully wrote and read back found attribute: {found_value}")
            except Exception as e:
                print(f"Warning: Could not read back found attribute: {e}")
            
            print("Orbit data pushed successfully")
        except Exception as exc:
            logger.error(f"Orbit view pushing failed: {exc}")
            raise exc

    async def push_twiss(self, twiss_result: TwissWithAggregatedKValues):
        """Push Twiss data to the device."""
        try:
            logger.info("Pushing Twiss data to device")
            device = await self._get_device()
            print("device is", device)
            print("***")
            

            def pad_array(arr, target_length=config.n_elements):
                if len(arr) < target_length:
                    return np.pad(arr, (0, target_length - len(arr)), mode='constant', constant_values=0)
                return arr[:target_length]  # Truncate if longer
            
            print("Converting and padding Twiss data...")
            alpha_x = pad_array(convert_to_list(twiss_result.x.alpha))
            beta_x = pad_array(convert_to_list(twiss_result.x.beta))
            nu_x = pad_array(convert_to_list(twiss_result.x.nu))
            alpha_y = pad_array(convert_to_list(twiss_result.y.alpha))
            beta_y = pad_array(convert_to_list(twiss_result.y.beta))
            nu_y = pad_array(convert_to_list(twiss_result.y.nu))
            names = pad_array(convert_to_list(twiss_result.names))
            
            # Write attributes
            print("Writing Twiss attributes...")
            print(f"Type twiss_alpha_x: {type(alpha_x)}")
            device.write_attribute("beam/twiss/x/alpha", alpha_x)
            print("wrote alpha_x")
            device.write_attribute("beam/twiss/x/beta", beta_x)
            print("wrote beta_x")
            device.write_attribute("beam/twiss/x/nu", nu_x)
            print("wrote nu_x")
            device.write_attribute("beam/twiss/y/alpha", alpha_y)
            print("wrote alpha_y")
            device.write_attribute("beam/twiss/y/beta", beta_y)
            print("wrote beta_y")
            device.write_attribute("beam/twiss/y/nu", nu_y)
            print("wrote nu_y")
            device.write_attribute("beam/twiss/names", names)
            print("wrote names")
            

            try:
                alpha_x_value = device.read_attribute("beam/twiss/x/alpha").value
                print(f"Successfully wrote and read back alpha_x attribute: {alpha_x_value[:5]}...")
            except Exception as e:
                print(f"Warning: Could not read back alpha_x attribute: {e}")
            
            logger.info("Twiss data pushed successfully")
        except Exception as exc:
            logger.error(f"Twiss view pushing failed: {exc}")
            raise exc

    async def push_bpms(self, orbit: Orbit):
        """Push BPM data to the device."""
        try:
            logger.info("Pushing BPM data to device")
            device = await self._get_device()
            
            if self.bpm_data is None:
                self.bpm_data = BeamPositionPVs(prefix=self.prefix)
            
            bpm_data = np.zeros(2048, dtype=np.int16)
            
            for i in range(min(len(orbit.x), 2048)):
                bpm_data[i] = int(orbit.x[i] * 1000)  # Convert to microns
            
            # Set BPM data
            await self.bpm_data.set_data(bpm_data)
            logger.info("BPM data pushed successfully")
            
        except Exception as exc:
            logger.error(f"BPM data pushing failed: {exc}")
            raise exc

    async def push_legacy_bpm_data(self, bpm_legacy_data: Optional[Sequence[np.int16]] = None):
        """Push BPM data to the device"""
        if bpm_legacy_data is None:
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
            
            logger.info(f"Pushing legacy BPM data at {datetime.now()}")
            await self.bpm_data.set_data(bpm_legacy_data)
            logger.info("BPM data pushed successfully")
        except Exception as e:
            logger.error(f"Failed to push BPM data: {e}")
            raise
