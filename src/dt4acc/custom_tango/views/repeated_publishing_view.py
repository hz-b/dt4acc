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
        # For Tango, prefix is like "server_name/instance_name:bpm_pv_name"
        # We need to extract the server/instance part and construct the device name
        self.prefix = prefix
        self.counter = itertools.count()
        # Extract base prefix (server_name/instance_name) by splitting on ':'
        if ':' in prefix:
            self.base_prefix = prefix.split(':')[0]
        else:
            self.base_prefix = prefix

    async def push(self, data):
        if data is None:
            logger.warning(f"{self.__class__.__name__} can't publish, data is None")
        await asyncio.sleep(0.0)
        # data = np.asarray(data, dtype=np.int16)
        logger.debug(f"{self.__class__.__name__} publishing to {self.prefix}")
        try:
            device = DeviceProxy(f"{self.base_prefix}/bpm_device")
            # Use the special_pvs attribute names
            # Note: count attribute is READ_ONLY, so we only write bdata
            bdata_attr_name = f"{special_pvs['bpm_pv']}/bdata"
            
            # Clean data and ensure proper format
            if isinstance(data, np.ndarray):
                # Clean NaN/INF values and convert to int16
                data_clean = np.nan_to_num(data, nan=-2**15+1, posinf=-2**15+1, neginf=-2**15+1)
                data_clean = data_clean.astype(np.int16)
            else:
                data_clean = data
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: device.write_attribute(bdata_attr_name, data_clean.tolist() if hasattr(data_clean, 'tolist') else list(data_clean))
            )
            logger.info(f"{self.__class__.__name__} published to {self.prefix}")
        except Exception as e:
            logger.error(f"Failed to publish BPM data: {e}")


class OrbitView(ViewInterface):
    def __init__(self, prefix):
        self.prefix = prefix
        self.counter = itertools.count()

    async def push(self, data):
        if data is None:
            logger.warning(f"{self.__class__.__name__} data is None!")
            await asyncio.sleep(0.0)
            return

        try:
            prefix = f"{self.prefix}:ORBITCC"
            # Todo: check that the dimensions are properly made
            # Extract x and y positions
            x_positions = data.loc[:, "x"].fillna(0.0).values  # Replace NaN with 0.0
            y_positions = data.loc[:, "y"].fillna(0.0).values  # Replace NaN with 0.0
            
            # Clean NaN/INF values
            x_positions = np.nan_to_num(x_positions, nan=0.0, posinf=0.0, neginf=0.0)
            y_positions = np.nan_to_num(y_positions, nan=0.0, posinf=0.0, neginf=0.0)
            
            # Combine x and y positions
            pos = np.concatenate([x_positions, y_positions])
            
            # Additional safety check - ensure no NaN/INF remain
            if np.isnan(pos).any() or np.isinf(pos).any():
                logger.warning(f"Found NaN/INF in orbit data after cleaning, replacing with zeros")
                pos = np.nan_to_num(pos, nan=0.0, posinf=0.0, neginf=0.0)
            
            device_name = f"{self.prefix}/twiss_orbit_device"
            device = DeviceProxy(device_name)
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: device.write_attribute("ORBITCC/rdPos", pos.tolist())
            )
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: device.write_attribute("ORBITCC/rdBpmNames", [str(val) for val in data.index])
            )
            # Note: ORBITCC/count is read-only, so we skip writing it
            # The counter is still incremented for logging purposes
            _ = next(self.counter)
        except Exception as e:
            logger.error(f"Error processing orbit object data: {e}")


class TuneView(ViewInterface):
    def __init__(self, prefix):
        self.prefix = prefix
        self.counter = itertools.count()

    async def push(self, data: TuneData):
        if data is None:
            logger.warning("tune data is None")
            return
        tune_x = float(data.x)
        tune_y = float(data.y)

        # currently adding very small noise to get data republished
        # need to check softioc what its records can do
        tune_x += np.random.uniform(-1e-12, 1e-12)
        tune_y += np.random.uniform(-1e-12, 1e-12)

        try:
            prefix = f"{self.prefix}:TUNECC"
            device_name = f"{self.prefix}/tune_device"
            device = DeviceProxy(device_name)
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: device.write_attribute("x", tune_x)
            )
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: device.write_attribute("y", tune_y)
            )
            #await asyncio.get_event_loop().run_in_executor(
            #    None,
            #    lambda: device.write_attribute(f"{prefix}:count", int(next(self.counter)))
            #)
            # Todo: check that the dimensions are properly made
        except Exception as e:
            logger.error(f"Error processing tune object data: {e}")


class RepeatedResultView:
    def __init__(self, *, prefix):
        self.prefix = prefix
        tmp = np.empty([2048], np.int16)
        tmp.fill(-2 ** 15 + 1)


        self.legacy_bpm_publisher = PeriodicPublisher(view=LegacyBPMView(prefix=f"{prefix}:{special_pvs['bpm_pv']}"), name="legacy-bpm")
        self.legacy_bpm_publisher.set_data(tmp)
        self.orbit_object_publisher = PeriodicPublisher(view=OrbitView(prefix=prefix), name="orbit")
        self.tune_publisher = PeriodicPublisher(view=TuneView(prefix=prefix), name="tune")
        # todo: fix this design flaw
        self.bpm_mimicry = None
        self.bpm_filter = ExtractBPMFromOrbitFilter()

    def set_bpm_mimicry(self, bpm_mimicry):
        self.bpm_filter.set_bpm_mimicry(bpm_mimicry)

    async def heart_beat(self):
        """
        Periodic heartbeat function to push default BPM data.
        """
        logger.debug(f"{self.__class__.__name__} heartbeat {datetime.now()}, publishing bpm, orbit, twiss")
        await self.orbit_object_publisher.publish()
        await self.tune_publisher.publish()
        await self.legacy_bpm_publisher.publish()
        logger.info(f"{self.__class__.__name__} view heartbeat {datetime.now()}, published bpm, orbit, twiss")

    async def push_twiss(self, twiss_result: TwissWithAggregatedKValues):
        self.tune_publisher.set_data(TuneData(x=twiss_result.x.tune, y=twiss_result.y.tune))
        await self.tune_publisher.publish()

    async def push_orbit(self, orbit_result: Orbit):
        return await self.push_bpms(orbit_result)

    async def push_bpms(self, orbit_data: Orbit):
        if not self.bpm_filter.is_ready():
            logger.warning("Can not publish bpm data as bpm_filter is not ready")
            await asyncio.sleep(0.0)
            return

        try:
            bpm_legacy_data, orbit_object_data = self.bpm_filter.process(orbit_data)
            if bpm_legacy_data is None:
                logger.error("BPM Legacy data is None, not setting it")
            else:
                self.legacy_bpm_publisher.set_data(bpm_legacy_data)
            self.orbit_object_publisher.set_data(orbit_object_data)

            await self.legacy_bpm_publisher.publish()
            await self.orbit_object_publisher.publish()
            logger.warning("Pushed bpm / orbit data")
            await asyncio.sleep(0.0)
            return
        except Exception as e:
            logger.error(f"Error processing orbit data: {e}")
