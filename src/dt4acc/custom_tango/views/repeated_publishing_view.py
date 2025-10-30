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

logger = get_logger()


class TuneView(ViewInterface):
    def __init__(self, prefix):
        self.prefix = prefix
        self.counter = itertools.count()

    async def push(self, data: TuneData):
        if data is None:
            logger.warning(f"{self.__class__.__name__} data is None!")
            await asyncio.sleep(0.0)
            return

        try:
            prefix = f"{self.prefix}"
            # Todo: check that the dimensions are properly made
            pos = np.array(data.loc[:, ["x", "y"]]).ravel()
            device = DeviceProxy(f"{prefix}/tune_device")

            # Update Twiss parameters - using correct Tango attribute names
            device.write_attribute("x", pos.x)
            device.write_attribute("y", pos.y)
            device.write_attribute("count", next(self.counter))
        except Exception as e:
            logger.error(f"Error processing orbit object data: {e}")


class RepeatedResultView:
    def __init__(self, *, prefix):
        self.prefix = prefix
        tmp = np.empty([2048], np.int16)
        tmp.fill(-2 ** 15 + 1)
        self.tune_publisher = PeriodicPublisher(view=TuneView(prefix=prefix), name="tune")
        self.bpm_mimicry = None

    async def heart_beat(self):
        """
        Periodic heartbeat function to push default BPM data.
        """
        logger.debug(f"{self.__class__.__name__} heartbeat {datetime.now()}, publishing bpm, orbit, twiss")
        # await self.orbit_object_publisher.publish()
        await self.tune_publisher.publish()
        # await self.legacy_bpm_publisher.publish()
        logger.info(f"{self.__class__.__name__} view heartbeat {datetime.now()}, published tune")

    async def push_twiss(self, twiss_result: TwissWithAggregatedKValues):
        self.tune_publisher.set_data(TuneData(x=twiss_result.x.tune, y=twiss_result.y.tune))
        await self.tune_publisher.publish()

    async def push_orbit(self, orbit_result: Orbit):
        return await self.push_bpms(orbit_result)

    async def push_bpms(self, orbit_data: Orbit):
        return
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
