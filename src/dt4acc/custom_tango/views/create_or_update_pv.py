import asyncio
from functools import partial
from tango import DeviceProxy, DevFailed
from typing import Union, List, Sequence
import numpy as np

from ...core.utils.logger import get_logger
from ...core.model.twiss import TwissWithAggregatedKValues
from ...core.model.orbit import Orbit

logger = get_logger()


async def update_or_create_pv(element, pv_name, value, value_type, initial_type):
    try:
        
        # ResultView.push_value method which handles device naming
        await asyncio.sleep(0.0)
        logger.debug(f"update_or_create_pv called for {pv_name} = {value}")
    except Exception as e:
        logger.error(f"Failed to update Tango device attribute {pv_name}: {e}")


def _to_python_float_list(arr):
    """Convert numpy array to Python list"""
    if isinstance(arr, np.ndarray):
        arr_clean = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
        return [float(x) for x in arr_clean.tolist()]
    elif isinstance(arr, (list, tuple)):
        arr_np = np.asarray(arr, dtype=np.float64)
        arr_clean = np.nan_to_num(arr_np, nan=0.0, posinf=0.0, neginf=0.0)
        return [float(x) for x in arr_clean.tolist()]
    else:
        try:
            val = float(arr)
            if np.isnan(val) or np.isinf(val):
                val = 0.0
            return [val]
        except (TypeError, ValueError):
            return [0.0]


# Function to update Twiss PVs
async def update_twiss_pv(pv_name, twiss_result):
   
    try:
        device = DeviceProxy(pv_name)
        
        tune_x = float(twiss_result.x.tune)
        tune_y = float(twiss_result.y.tune)
        
        alpha_x_py = _to_python_float_list(twiss_result.x.alpha)
        beta_x_py = _to_python_float_list(twiss_result.x.beta)
        nu_x_py = _to_python_float_list(twiss_result.x.nu)
        alpha_y_py = _to_python_float_list(twiss_result.y.alpha)
        beta_y_py = _to_python_float_list(twiss_result.y.beta)
        nu_y_py = _to_python_float_list(twiss_result.y.nu)
        
        # Ensure arrays are not empty 
        if not alpha_x_py:
            alpha_x_py = [0.0]
        if not beta_x_py:
            beta_x_py = [0.0]
        if not nu_x_py:
            nu_x_py = [0.0]
        if not alpha_y_py:
            alpha_y_py = [0.0]
        if not beta_y_py:
            beta_y_py = [0.0]
        if not nu_y_py:
            nu_y_py = [0.0]
        
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(
                None,
                partial(device.write_attribute, "beam/twiss/x/tune", tune_x)
            )
        except Exception as e:
            logger.error(f"Failed to write beam/twiss/x/tune: {e}, value: {tune_x}, type: {type(tune_x)}")
            raise
        
        try:
            await loop.run_in_executor(
                None,
                partial(device.write_attribute, "beam/twiss/x/alpha", alpha_x_py)
            )
        except Exception as e:
            logger.error(f"Failed to write beam/twiss/x/alpha: {e}, type: {type(alpha_x_py)}, first element type: {type(alpha_x_py[0]) if alpha_x_py else 'empty'}")
            raise
        
        try:
            await loop.run_in_executor(
                None,
                partial(device.write_attribute, "beam/twiss/x/beta", beta_x_py)
            )
        except Exception as e:
            logger.error(f"Failed to write beam/twiss/x/beta: {e}, type: {type(beta_x_py)}, first element type: {type(beta_x_py[0]) if beta_x_py else 'empty'}")
            raise
        
        try:
            await loop.run_in_executor(
                None,
                partial(device.write_attribute, "beam/twiss/x/nu", nu_x_py)
            )
        except Exception as e:
            logger.error(f"Failed to write beam/twiss/x/nu: {e}, type: {type(nu_x_py)}, first element type: {type(nu_x_py[0]) if nu_x_py else 'empty'}")
            raise
        
        try:
            await loop.run_in_executor(
                None,
                partial(device.write_attribute, "beam/twiss/y/tune", tune_y)
            )
        except Exception as e:
            logger.error(f"Failed to write beam/twiss/y/tune: {e}, value: {tune_y}, type: {type(tune_y)}")
            raise
        
        try:
            await loop.run_in_executor(
                None,
                partial(device.write_attribute, "beam/twiss/y/alpha", alpha_y_py)
            )
        except Exception as e:
            logger.error(f"Failed to write beam/twiss/y/alpha: {e}, type: {type(alpha_y_py)}, first element type: {type(alpha_y_py[0]) if alpha_y_py else 'empty'}")
            raise
        
        try:
            await loop.run_in_executor(
                None,
                partial(device.write_attribute, "beam/twiss/y/beta", beta_y_py)
            )
        except Exception as e:
            logger.error(f"Failed to write beam/twiss/y/beta: {e}, type: {type(beta_y_py)}, first element type: {type(beta_y_py[0]) if beta_y_py else 'empty'}")
            raise
        
        try:
            await loop.run_in_executor(
                None,
                partial(device.write_attribute, "beam/twiss/y/nu", nu_y_py)
            )
        except Exception as e:
            logger.error(f"Failed to write beam/twiss/y/nu: {e}, type: {type(nu_y_py)}, first element type: {type(nu_y_py[0]) if nu_y_py else 'empty'}")
            raise
        
        logger.debug("Updated twiss values")
        
    except Exception as e:
        logger.warning("FAILED Updated twiss values: %s", e)
        logger.error(f"Failed to update or create twiss PV {pv_name}: {e}")
        raise  
    
 
    if twiss_result.main_values:
        logger.debug(f"Twiss main_values available but not written to Tango device (not supported)")


# Function to update Orbit PVs
async def update_orbit_pv(pv_name, orbit_result):
    
    try:
        device = DeviceProxy(pv_name)
        
        x_clean = np.nan_to_num(orbit_result.x, nan=0.0, posinf=0.0, neginf=0.0)
        y_clean = np.nan_to_num(orbit_result.y, nan=0.0, posinf=0.0, neginf=0.0)
        x0_clean = np.nan_to_num(orbit_result.x0, nan=0.0, posinf=0.0, neginf=0.0)
        
        loop = asyncio.get_running_loop()
        
        x_list = x_clean.tolist() if hasattr(x_clean, 'tolist') else list(x_clean)
        y_list = y_clean.tolist() if hasattr(y_clean, 'tolist') else list(y_clean)
        x0_list = x0_clean.tolist() if hasattr(x0_clean, 'tolist') else list(x0_clean)
        names_list = [str(n) for n in orbit_result.names]
        found_value = int(orbit_result.found)
        
        await loop.run_in_executor(
            None,
            partial(device.write_attribute, "beam/orbit/x", x_list)
        )
        await loop.run_in_executor(
            None,
            partial(device.write_attribute, "beam/orbit/y", y_list)
        )
        await loop.run_in_executor(
            None,
            partial(device.write_attribute, "beam/orbit/names", names_list)
        )
        await loop.run_in_executor(
            None,
            partial(device.write_attribute, "beam/orbit/found", found_value)
        )
        await loop.run_in_executor(
            None,
            partial(device.write_attribute, "beam/orbit/x0", x0_list)
        )
    except Exception as e:
        logger.error(f"Failed to update or create Orbit PV {pv_name}: {e}")


async def update_bpm_pv(pv_name, bpm_result):
  
    try:
        device = DeviceProxy(pv_name)
        
        # Convert BPM data to proper format
        if isinstance(bpm_result, (list, np.ndarray)):
            data_array = np.asarray(bpm_result, dtype=np.int16)
            data_array = np.nan_to_num(data_array, nan=-2**15+1, posinf=-2**15+1, neginf=-2**15+1)
            
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: device.write_attribute("bdata", data_array.tolist())
            )
        else:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: device.write_attribute("bdata", bpm_result)
            )
    except Exception as e:
        logger.error(f"Failed to update or create PV {pv_name}: {e}")