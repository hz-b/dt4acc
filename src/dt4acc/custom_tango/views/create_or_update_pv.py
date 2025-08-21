from tango import DeviceProxy, DevFailed
from typing import Union, List, Sequence
import numpy as np

from ...core.utils.logger import get_logger
from ...core.model.twiss import TwissWithAggregatedKValues
from ...core.model.orbit import Orbit

logger = get_logger()

def convert_to_list(data: Union[Sequence, np.ndarray]) -> List:
    """Convert sequence or numpy array to list with proper type handling"""
    if isinstance(data, np.ndarray):
        data = np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)
        return data.tolist()
    return list(data)

def update_or_create_pv(element, pv_name: str, value, value_type: str, initial_type: str):
    """
    Update or create a Tango device attribute.
    Equivalent to EPICS update_or_create_pv function.
    
    Note: This function needs to be called with proper device context.
    The device name should be determined by the caller based on element information.
    """
    try:
        # This function should be updated to work with the dynamic device naming
        # from the ResultView class. For now, we'll log that it needs proper implementation.
        logger.warning(f"update_or_create_pv called for {element.element_id}:{element.property_name} = {value}")
        logger.warning(f"This function needs proper device context. Use the ResultView.push_value method instead.")
        
    except Exception as e:
        logger.error(f"Failed to update Tango device attribute {pv_name}: {e}")

def update_twiss_pv(device_name: str, twiss_result: TwissWithAggregatedKValues):
    """
    Update Twiss parameters in Tango devices.
    Uses the correct attribute names from TwissOrbitDevice.
    """
    try:
        # Update the main Twiss/Orbit device using the provided device name
        device = DeviceProxy(device_name)
        
        # Update Twiss parameters - using correct Tango attribute names
        device.write_attribute("beam/twiss/x/alpha", convert_to_list(twiss_result.x.alpha))
        device.write_attribute("beam/twiss/x/beta", convert_to_list(twiss_result.x.beta))
        device.write_attribute("beam/twiss/x/nu", convert_to_list(twiss_result.x.nu))
        device.write_attribute("beam/twiss/y/alpha", convert_to_list(twiss_result.y.alpha))
        device.write_attribute("beam/twiss/y/beta", convert_to_list(twiss_result.y.beta))
        device.write_attribute("beam/twiss/y/nu", convert_to_list(twiss_result.y.nu))
        
        # Add noise to tune values (matching EPICS behavior)
        tune_x = float(twiss_result.x.tune) + np.random.uniform(-1e-12, 1e-12)
        tune_y = float(twiss_result.y.tune) + np.random.uniform(-1e-12, 1e-12)
        device.write_attribute("beam/twiss/x/tune", tune_x)
        device.write_attribute("beam/twiss/y/tune", tune_y)
        
        # Update Twiss names
        device.write_attribute("beam/twiss/names", convert_to_list(twiss_result.names))
        
        logger.info(f"Successfully updated Twiss parameters in device {device_name}")
        
    except Exception as e:
        logger.error(f"Failed to update Twiss parameters: {e}")
        raise

def update_orbit_pv(device_name: str, orbit_result: Orbit):
    """
    Update orbit parameters in Tango devices.
    Uses the correct attribute names from TwissOrbitDevice.
    """
    try:
        # Update the main Twiss/Orbit device using the provided device name
        device = DeviceProxy(device_name)
        
        # Clean the data before pushing to Tango to prevent NaN/INF errors
        
        # Clean X positions
        x_positions = np.nan_to_num(orbit_result.x, nan=0.0, posinf=0.0, neginf=0.0)
        y_positions = np.nan_to_num(orbit_result.y, nan=0.0, posinf=0.0, neginf=0.0)
        x0_positions = np.nan_to_num(orbit_result.x0, nan=0.0, posinf=0.0, neginf=0.0)
        
        # Ensure names are valid strings
        names = [str(name) if name is not None else f"Element_{i}" for i, name in enumerate(orbit_result.names)]
        
        logger.debug(f"📊 Cleaned orbit data:")
        logger.debug(f"   X positions: {len(x_positions)} elements, range: [{x_positions.min():.6f}, {x_positions.max():.6f}]")
        logger.debug(f"   Y positions: {len(y_positions)} elements, range: [{y_positions.min():.6f}, {y_positions.max():.6f}]")
        logger.debug(f"   X0 positions: {len(x0_positions)} elements, range: [{x0_positions.min():.6f}, {x0_positions.max():.6f}]")
        logger.debug(f"   Names: {len(names)} elements")
        logger.debug(f"   Found: {orbit_result.found}")
        
        # Update orbit parameters - using correct Tango attribute names
        device.write_attribute("beam/orbit/x", convert_to_list(x_positions))
        device.write_attribute("beam/orbit/y", convert_to_list(y_positions))
        device.write_attribute("beam/orbit/names", names)
        device.write_attribute("beam/orbit/found", int(orbit_result.found))
        device.write_attribute("beam/orbit/x0", convert_to_list(x0_positions))
        
        logger.info(f"Successfully updated orbit parameters in device {device_name}")
        
    except Exception as e:
        logger.error(f"Failed to update orbit parameters: {e}")
        raise

def update_bpm_pv(device_name: str, bpm_result):
    """
    Update BPM data in Tango devices.
    Equivalent to EPICS update_bpm_pv function.
    """
    try:
        # Update the BPM device using the provided device name
        device = DeviceProxy(device_name)
        
        # Convert BPM data to proper format
        if isinstance(bpm_result, (list, np.ndarray)):
            data_array = np.asarray(bpm_result, dtype=np.float32)
            data_array = np.nan_to_num(data_array, nan=0.0, posinf=0.0, neginf=0.0)
            data_array = data_array.astype(np.int16)
            
            device.write_attribute("bdata", data_array.tolist())
            logger.debug(f"Updated BPM data: {len(data_array)} elements")
            
        else:
            # Handle non-array data
            device.write_attribute("bdata", bpm_result)
            logger.debug(f"Updated BPM data with non-array value")
        
    
        
        logger.info(f"Successfully updated BPM data in device {device_name}")
        
    except Exception as e:
        logger.error(f"Failed to update BPM data: {e}") 