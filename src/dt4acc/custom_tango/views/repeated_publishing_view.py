import asyncio
import itertools
from datetime import datetime
import numpy as np

from tango import DeviceProxy

from ...core.interfaces.view_interface import ViewInterface
from ...core.model.orbit import Orbit
from ...core.model.twiss import TwissWithAggregatedKValues, TuneData
from ...core.utils.logger import get_logger
from ...core.utils.periodic_publisher import PeriodicPublisher
from ...custom_epics.data.constants import special_pvs
from ...custom_epics.utils.bpm_mimicry import BPMMimicry


logger = get_logger()


def _to_python_float(value):
    """Convert numpy float to Python native float."""
    if isinstance(value, np.floating):
        return float(value.item())
    elif isinstance(value, np.ndarray):
        # If it's a 0-d array (scalar), extract the value
        if value.ndim == 0:
            return float(value.item())
        else:
            # For arrays, convert to list first
            return float(value.flat[0].item())
    elif isinstance(value, (float, int)):
        return float(value)
    else:
        # Try to convert, handling any numpy types
        try:
            if hasattr(value, 'item'):
                return float(value.item())
        except (AttributeError, ValueError):
            pass
        return float(value)


def _to_python_int(value):
    """Convert numpy int to Python native int."""
    if isinstance(value, np.integer):
        return int(value.item())
    elif isinstance(value, np.ndarray):
        # If it's a 0-d array (scalar), extract the value
        if value.ndim == 0:
            return int(value.item())
        else:
            # For arrays, convert to list first
            return int(value.flat[0].item())
    elif isinstance(value, (int, float)):
        return int(value)
    else:
        # Try to convert, handling any numpy types
        try:
            if hasattr(value, 'item'):
                return int(value.item())
        except (AttributeError, ValueError):
            pass
        return int(value)


def _to_python_float_list(arr):
    """Convert numpy array to Python list of floats."""
    if isinstance(arr, np.ndarray):
        # Convert numpy array to list, ensuring all elements are Python floats
        return [float(np.float64(v).item()) if isinstance(v, (np.floating, np.integer)) else float(v) for v in arr.flat]
    elif isinstance(arr, (list, tuple)):
        # Already a sequence, convert each element
        return [_to_python_float(v) for v in arr]
    else:
        # Single value
        return [_to_python_float(arr)]


class ExtractBPMFromOrbitFilter:
    def __init__(self):
        self.bpm_mimicry = None

    def set_bpm_mimicry(self, bpm_mimicry):
        assert callable(bpm_mimicry.extract_bpm_legacy_data_to_df)
        assert callable(bpm_mimicry.bpm_legacy_data_df_to_array)
        self.bpm_mimicry = bpm_mimicry

    def is_ready(self) -> bool:
        return self.bpm_mimicry is not None

    def process(self, orbit_data: Orbit):
        assert self.bpm_mimicry is not None, f"BPM Mimicry was not set to {self.__class__.__name__}"

        df_bpm = self.bpm_mimicry.extract_bpm_legacy_data_to_df(orbit_data)
        bpm_legacy_data = self.bpm_mimicry.bpm_legacy_data_df_to_array(df_bpm)
        orbit_object_data = df_bpm.copy()
        mm2nm = 1e6
        orbit_object_data.x = df_bpm.x * mm2nm
        orbit_object_data.y = df_bpm.y * mm2nm
        return bpm_legacy_data, orbit_object_data


class LegacyBPMView(ViewInterface):
    def __init__(self, prefix):
       
        self.prefix = prefix
        self.counter = itertools.count()
        if ':' in prefix:
            self.base_prefix = prefix.split(':')[0]
        else:
            self.base_prefix = prefix

    async def push(self, data):
        if data is None:
            pass
        await asyncio.sleep(0.0)
        try:
            if self.base_prefix and "/" in self.base_prefix:
                device_name = f"{self.base_prefix}/TWISS_ORBIT"
            else:
                device_name = "PHYSICS/SOLEIL/TWISS_ORBIT"
            device = DeviceProxy(device_name)
            
            if isinstance(data, np.ndarray):
                # Clean NaN/INF values and convert to int16
                data_clean = np.nan_to_num(data, nan=-2**15+1, posinf=-2**15+1, neginf=-2**15+1)
                data_clean = data_clean.astype(np.int16)
            else:
                data_clean = data
            
            
            data_py = [_to_python_int(v) for v in (data_clean.tolist() if hasattr(data_clean, 'tolist') else list(data_clean))]
            
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: device.write_attribute("beam/bpm/data", data_py)
            )
        except Exception as e:
            logger.error(f"Failed to publish BPM data: {e}")


class OrbitView(ViewInterface):
    def __init__(self, prefix):
        self.prefix = prefix
        self.counter = itertools.count()

    async def push(self, data):
        if data is None:
            await asyncio.sleep(0.0)
            return

        try:
           
            x_positions = data.loc[:, "x"].fillna(0.0).values  # Replace NaN with 0.0
            y_positions = data.loc[:, "y"].fillna(0.0).values  # Replace NaN with 0.0
            
            
            x_positions = np.nan_to_num(x_positions, nan=0.0, posinf=0.0, neginf=0.0)
            y_positions = np.nan_to_num(y_positions, nan=0.0, posinf=0.0, neginf=0.0)
            
            
            pos = np.concatenate([x_positions, y_positions])
            
            
            if np.isnan(pos).any() or np.isinf(pos).any():
            
                pos = np.nan_to_num(pos, nan=0.0, posinf=0.0, neginf=0.0)
            
            
            if self.prefix and "/" in self.prefix:
                device_name = f"{self.prefix}/TWISS_ORBIT"
            else:
                device_name = "PHYSICS/SOLEIL/TWISS_ORBIT"
            device = DeviceProxy(device_name)
            
            mid_point = len(pos) // 2
            x_pos = pos[:mid_point]
            y_pos = pos[mid_point:]
            
            
            x_pos_arr = np.asarray(x_pos, dtype=np.float64)
            y_pos_arr = np.asarray(y_pos, dtype=np.float64)
            x_pos_py = _to_python_float_list(x_pos_arr)
            y_pos_py = _to_python_float_list(y_pos_arr)
            
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: device.write_attribute("beam/orbit/x", x_pos_py)
            )
            await loop.run_in_executor(
                None,
                lambda: device.write_attribute("beam/orbit/y", y_pos_py)
            )
            await loop.run_in_executor(
                None,
                lambda: device.write_attribute("beam/orbit/names", [str(val) for val in data.index])
            )
          
            _ = next(self.counter)
        except Exception as e:
            logger.error(f"Error processing orbit object data: {e}")


class TuneView(ViewInterface):
    def __init__(self, prefix):
        self.prefix = prefix
        self.counter = itertools.count()

    async def push(self, data: TuneData):
        if data is None:
            #logger.warning("tune data is None")
            return
        tune_x = float(data.x)
        tune_y = float(data.y)

        try:
            
            if self.prefix and "/" in self.prefix:
                device_name = f"{self.prefix}/TUNE"
            else:
                device_name = "PHYSICS/SOLEIL/TUNE"
            device = DeviceProxy(device_name)
            
            logger.debug(f"TuneView.push: Writing tune X={tune_x:.10f}, Y={tune_y:.10f} to {device_name}")
            
            # Convert to pure Python float (not numpy float)
            tune_x_py = _to_python_float(tune_x)
            tune_y_py = _to_python_float(tune_y)
            
            # TuneDevice has tune_x_attr and tune_y_attr attributes (method names become attribute names)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: device.write_attribute("tune_x_attr", tune_x_py)
            )
            await loop.run_in_executor(
                None,
                lambda: device.write_attribute("tune_y_attr", tune_y_py)
            )
            
            logger.info(f"TuneView.push: >>>>>>>> Successfully wrote tune X={tune_x:.10f}, Y={tune_y:.10f}")
        
        except Exception as e:
            logger.error(f"TuneView.push: ❌ Error writing tune values: {e}")


class RepeatedResultView:
    def __init__(self, *, prefix):
        self.prefix = prefix
        tmp = np.empty([2048], np.int16)
        tmp.fill(-2 ** 15 + 1)


        self.legacy_bpm_publisher = PeriodicPublisher(view=LegacyBPMView(prefix=f"{prefix}:{special_pvs['bpm_pv']}"), name="legacy-bpm")
        self.legacy_bpm_publisher.set_data(tmp)
        self.orbit_object_publisher = PeriodicPublisher(view=OrbitView(prefix=prefix), name="orbit")
        self.tune_publisher = PeriodicPublisher(view=TuneView(prefix=prefix), name="tune")
        
        self.bpm_mimicry = None
        self.bpm_filter = ExtractBPMFromOrbitFilter()

    def set_bpm_mimicry(self, bpm_mimicry):
        self.bpm_filter.set_bpm_mimicry(bpm_mimicry)

    async def heart_beat(self):
        
        
        await self.orbit_object_publisher.publish()
        await self.legacy_bpm_publisher.publish()

    async def push_twiss(self, twiss_result: TwissWithAggregatedKValues):
        tune_x = float(twiss_result.x.tune)
        tune_y = float(twiss_result.y.tune)
        
        logger.info(f"{self.__class__.__name__}.push_twiss: Publishing tune values X={tune_x:.10f}, Y={tune_y:.10f}")
        logger.info(f"  Twiss data: X-plane alpha={twiss_result.x.alpha[:3] if len(twiss_result.x.alpha) > 3 else twiss_result.x.alpha}, "
                   f"beta={twiss_result.x.beta[:3] if len(twiss_result.x.beta) > 3 else twiss_result.x.beta}")
        logger.info(f"  Twiss data: Y-plane alpha={twiss_result.y.alpha[:3] if len(twiss_result.y.alpha) > 3 else twiss_result.y.alpha}, "
                   f"beta={twiss_result.y.beta[:3] if len(twiss_result.y.beta) > 3 else twiss_result.y.beta}")
        
        self.tune_publisher.set_data(TuneData(x=tune_x, y=tune_y))
        await self.tune_publisher.publish()
        logger.info(f"{self.__class__.__name__}.push_twiss: Successfully published tune values")

    async def push_orbit(self, orbit_result: Orbit):
        return await self.push_bpms(orbit_result)

    async def push_bpms(self, orbit_data: Orbit):
        if not self.bpm_filter.is_ready():
            
            await asyncio.sleep(0.0)
            return

        try:
            bpm_legacy_data, orbit_object_data = self.bpm_filter.process(orbit_data)
            if bpm_legacy_data is None:
                pass
                
            else:
                self.legacy_bpm_publisher.set_data(bpm_legacy_data)
            self.orbit_object_publisher.set_data(orbit_object_data)

            await self.legacy_bpm_publisher.publish()
            await self.orbit_object_publisher.publish()
            await asyncio.sleep(0.0)
            return
        except Exception as e:
            logger.error(f"Error processing orbit data: {e}")