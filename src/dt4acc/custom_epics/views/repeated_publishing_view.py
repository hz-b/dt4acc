import asyncio
import itertools
from datetime import datetime
import numpy as np

from ..utils.context_proxy import ContextProxy
from ...core.interfaces.view_interface import ViewInterface
from ...core.model.orbit import Orbit
from ...core.model.twiss import TwissWithAggregatedKValues, TuneData
from ...core.utils.logger import get_logger
from ...core.utils.periodic_publisher import PeriodicPublisher
from ..data.constants import special_pvs


logger = get_logger()

ctx = ContextProxy("pva")


def tune_to_frequency(tune: float, rf_frequency: float, n_rf_buckets: int) -> float:
    """
    Todo: move to the correct place
    """
    assert tune > 0, "Expect tune to be positive"
    fractional_tune = tune % 1
    # Inverse of the time around the ring
    rev_freq = rf_frequency / n_rf_buckets

    # Some sytems only can measure half of it so ...
    # The measurement system can only measure the half tune
    # if tune is above 0.5 it is "mirrored in"
    # if fractional_tune > 0.5:
    #     assert fractional_tune <= 1.0
    #     fractional_tune = 1.0 - fractional_tune

    tune_freq = rev_freq * fractional_tune
    return tune_freq


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

    async def push(self, data):
        if data is None:
            logger.warning(f"{self.__class__.__name__} can't publish, data is None")
        await asyncio.sleep(0.0)
        # data = np.asarray(data, dtype=np.int16)
        logger.debug(f"{self.__class__.__name__} publishing to {self.prefix}:count")
        await ctx.put(f"{self.prefix}:count", next(self.counter))
        await ctx.put(f"{self.prefix}:bdata", data)
        logger.info(f"{self.__class__.__name__} published to {self.prefix}")


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
            pos = np.array(data.loc[:, ["x", "y"]]).ravel()
            await ctx.put(f"{prefix}:rdPos", pos)
            await ctx.put(f"{prefix}:rdBpmNames", [str(val) for val in data.index])
            await ctx.put(f"{prefix}:count", next(self.counter))
        except Exception as e:
            logger.error(f"Error processing orbit object data: {e}")


class TuneView(ViewInterface):
    def __init__(self, prefix: str, *, synchrotron_frequency_scale: float=1.0):
        self.prefix = prefix
        self.counter = itertools.count()
        self.synchrotron_frequency_scale = synchrotron_frequency_scale

    async def push(self, data: TuneData):
        if data is None:
            logger.warning("Updating tune view: data is None")
            return
        tune_x = float(data.x)
        tune_y = float(data.y)
        # currently adding very small noise to get data republished
        # need to check softioc what its records can do
        tune_x += np.random.uniform(-1e-12, 1e-12)
        tune_y += np.random.uniform(-1e-12, 1e-12)

        try:
            prefix = f"{self.prefix}:TUNEZR:flq"
            await ctx.put(f"{prefix}:rdH", tune_x)
            await ctx.put(f"{prefix}:rdV", tune_y)
            # Todo: check that the dimensions are properly made
        except Exception as e:
            logger.error(f"Error publishing tune (Floquet) data: {e}")

        try:
            n_rf_buckets = await ctx.get(f"{self.prefix}:beam:machine:info:n_rf_buckets")
        except Exception as e:
            logger.error(f"Error getting  n_rf_buckets: {e}")
            return

        pv_name = f"{self.prefix}:{special_pvs['master_clock']}:freq"
        try:
            freq = await ctx.get(pv_name)
        except Exception as e:
            logger.error(f"Error getting master clock freq using '{pv_name}': {e}")
            return

        tune_freq_x = tune_to_frequency(tune=tune_x, rf_frequency=freq, n_rf_buckets=n_rf_buckets)
        tune_freq_y = tune_to_frequency(tune=tune_y, rf_frequency=freq, n_rf_buckets=n_rf_buckets)
        tune_freq_x *= self.synchrotron_frequency_scale
        tune_freq_y *= self.synchrotron_frequency_scale

        # currently adding very small noise to get data republished
        # need to check softioc what its records can do
        tune_freq_x += np.random.uniform(-1e-12, 1e-12)
        tune_freq_y += np.random.uniform(-1e-12, 1e-12)

        try:
            prefix = f"{self.prefix}:TUNEZR"
            await ctx.put(f"{prefix}:rdH", tune_freq_x)
            await ctx.put(f"{prefix}:rdV", tune_freq_y)
            await ctx.put(f"{prefix}:count", int(next(self.counter)))
            # Todo: check that the dimensions are properly made
        except Exception as e:
            logger.error(f"Error publishing tune as synchrotron frequency: {e}")


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
