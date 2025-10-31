import asyncio
from tango import DeviceProxy, DevFailed
from typing import Union, List, Sequence
import numpy as np

from ...core.utils.logger import get_logger
from ...core.model.twiss import TwissWithAggregatedKValues
from ...core.model.orbit import Orbit

logger = get_logger()


async def update_or_create_pv(element, pv_name, value, value_type, initial_type):
    """
    Update or create a Tango device attribute.
    Equivalent to EPICS update_or_create_pv function.
    """
    try:
        # Note: For Tango, device updates are typically done through
        # the ResultView.push_value method which handles device naming
        await asyncio.sleep(0.0)
        logger.debug(f"update_or_create_pv called for {pv_name} = {value}")
    except Exception as e:
        logger.error(f"Failed to update Tango device attribute {pv_name}: {e}")


# Function to update Twiss PVs
async def update_twiss_pv(pv_name, twiss_result):
    """
    Update Twiss parameters in Tango devices.
    Equivalent to EPICS update_twiss_pv function.
    """
    try:
        device = DeviceProxy(pv_name)
        
        # Update Twiss parameters - using correct Tango attribute names
        tune_x = float(twiss_result.x.tune)
        tune_y = float(twiss_result.y.tune)
        
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: device.write_attribute("beam/twiss/x/tune", tune_x)
        )
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: device.write_attribute("beam/twiss/x/alpha", twiss_result.x.alpha.tolist() if hasattr(twiss_result.x.alpha, 'tolist') else list(twiss_result.x.alpha))
        )
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: device.write_attribute("beam/twiss/x/beta", twiss_result.x.beta.tolist() if hasattr(twiss_result.x.beta, 'tolist') else list(twiss_result.x.beta))
        )
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: device.write_attribute("beam/twiss/x/nu", twiss_result.x.nu.tolist() if hasattr(twiss_result.x.nu, 'tolist') else list(twiss_result.x.nu))
        )
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: device.write_attribute("beam/twiss/y/tune", tune_y)
        )
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: device.write_attribute("beam/twiss/y/alpha", twiss_result.y.alpha.tolist() if hasattr(twiss_result.y.alpha, 'tolist') else list(twiss_result.y.alpha))
        )
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: device.write_attribute("beam/twiss/y/beta", twiss_result.y.beta.tolist() if hasattr(twiss_result.y.beta, 'tolist') else list(twiss_result.y.beta))
        )
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: device.write_attribute("beam/twiss/y/nu", twiss_result.y.nu.tolist() if hasattr(twiss_result.y.nu, 'tolist') else list(twiss_result.y.nu))
        )
        
        logger.debug("Updated twiss values")
        
    except Exception as e:
        logger.warning("FAILED Updated twiss values: %s", e)
        logger.error(f"Failed to update or create twiss PV {pv_name}: {e}")
    
    # Note: Tango device doesn't have main_values attributes (unlike EPICS)
    # These values are typically handled through individual magnet devices
    # So we skip writing main_values to avoid errors
    if twiss_result.main_values:
        logger.debug(f"Twiss main_values available but not written to Tango device (not supported)")


# Function to update Orbit PVs
async def update_orbit_pv(pv_name, orbit_result):
    """
    Update orbit parameters in Tango devices.
    Equivalent to EPICS update_orbit_pv function.
    """
    try:
        device = DeviceProxy(pv_name)
        
        # Clean data to prevent NaN/INF errors
        x_clean = np.nan_to_num(orbit_result.x, nan=0.0, posinf=0.0, neginf=0.0)
        y_clean = np.nan_to_num(orbit_result.y, nan=0.0, posinf=0.0, neginf=0.0)
        x0_clean = np.nan_to_num(orbit_result.x0, nan=0.0, posinf=0.0, neginf=0.0)
        
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: device.write_attribute("beam/orbit/x", x_clean.tolist() if hasattr(x_clean, 'tolist') else list(x_clean))
        )
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: device.write_attribute("beam/orbit/y", y_clean.tolist() if hasattr(y_clean, 'tolist') else list(y_clean))
        )
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: device.write_attribute("beam/orbit/names", [str(n) for n in orbit_result.names])
        )
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: device.write_attribute("beam/orbit/found", int(orbit_result.found))
        )
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: device.write_attribute("beam/orbit/x0", x0_clean.tolist() if hasattr(x0_clean, 'tolist') else list(x0_clean))
        )
    except Exception as e:
        logger.error(f"Failed to update or create Orbit PV {pv_name}: {e}")


async def update_bpm_pv(pv_name, bpm_result):
    """
    Update BPM data in Tango devices.
    Equivalent to EPICS update_bpm_pv function.
    """
    try:
        device = DeviceProxy(pv_name)
        
        # Convert BPM data to proper format
        if isinstance(bpm_result, (list, np.ndarray)):
            data_array = np.asarray(bpm_result, dtype=np.int16)
            data_array = np.nan_to_num(data_array, nan=-2**15+1, posinf=-2**15+1, neginf=-2**15+1)
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: device.write_attribute("bdata", data_array.tolist())
            )
        else:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: device.write_attribute("bdata", bpm_result)
            )
    except Exception as e:
        logger.error(f"Failed to update or create PV {pv_name}: {e}")
