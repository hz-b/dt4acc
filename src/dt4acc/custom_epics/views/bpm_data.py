import itertools
from typing import Sequence

import numpy as np
from p4p.client.asyncio import Context

from ...core.utils.logger import get_logger

logger = get_logger()

ctx = Context("pva")


class BeamPositionPVs:
    def __init__(self, prefix: str):
        self.prefix = prefix
        self.counter = itertools.count()
        # could be None ... no new data before
        # calculation starts
        self.bdata_cache = None

    async def update_values(self):
        # as it should be an array
        if self.bdata_cache is None:
            logger.warning("No bpm data (yet)")
            return

        # tod: need await here ?
        await ctx.put(f"{self.prefix}:bdata", self.bdata_cache)
        await ctx.put(f"{self.prefix}:count", next(self.counter))

    async def heart_beat(self):
        await self.update_values()

    async def set_data(self, bdata: Sequence[np.int16]):
        self.bdata_cache = np.asarray(bdata)
        await self.update_values()
