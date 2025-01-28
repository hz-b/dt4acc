from datetime import datetime
from typing import Sequence

import numpy as np
from p4p.client.asyncio import Context

from ...core.model.element_upate import ElementUpdate
from ...core.model.orbit import Orbit
from ...core.model.twiss import TwissWithAggregatedKValues
from ...core.utils.logger import get_logger
from ..data.constants import DEFAULTS
from ..views.bpm_data import BeamPositionPVs
from ..views.create_or_update_pv import update_or_create_pv

logger = get_logger()

ctx = Context("pva")


async def update_orbit_pv(pv_name, orbit_result):
    try:
        await ctx.put(f"{pv_name}:x", orbit_result.x)
        await ctx.put(f"{pv_name}:y", orbit_result.y)
        await ctx.put(f"{pv_name}:names", orbit_result.names)
        await ctx.put(f"{pv_name}:found", orbit_result.found)
        await ctx.put(f"{pv_name}:x0", orbit_result.x0)
    except Exception as e:
        logger.error(f"Failed to update or create Orbit PV {pv_name}: {e}")


async def update_twiss_pv(pv_name, twiss_result):
    try:
        await ctx.put(f"{pv_name}:x:alpha", twiss_result.x.alpha)
        await ctx.put(f"{pv_name}:x:beta", twiss_result.x.beta)
        await ctx.put(f"{pv_name}:x:nu", twiss_result.x.nu)
        await ctx.put(f"{pv_name}:y:alpha", twiss_result.y.alpha)
        await ctx.put(f"{pv_name}:y:beta", twiss_result.y.beta)
        await ctx.put(f"{pv_name}:y:nu", twiss_result.y.nu)
        # await ctx.put(f"{pv_name}:names", twiss_result.names)
    except Exception as e:
        logger.error(f"Failed to update or create twiss PV {pv_name}: {e}")
    try:
        await ctx.put(twiss_result.all_k_pv_names, twiss_result.all_k_pv_values)
    except Exception as e:
        logger.error(f"Failed to update or create magnet_strength PV {pv_name}: {e}")


class ResultView:
    def __init__(self, *, prefix):
        self.prefix = prefix
        self.bpm_pvs = BeamPositionPVs(prefix=f"{self.prefix}:{DEFAULTS['bpm_pv']}")
        tmp = np.empty([2048], np.int16)
        tmp.fill(-2 ** 15 + 1)
        self.default_bpm_legacy_data = tmp
        self.bpm_mimicry = None

    # dependency injection (push bpm mimicry when it is available
    def set_bpm_mimicry(self, bpm_mimicry):
        self.bpm_mimicry = bpm_mimicry

    async def push_value(self, elm_update: ElementUpdate):
        if elm_update.property_name == "K":
            pass
        else:
            property_name = 'x:set' if 'x' in elm_update.property_name else (
                'y:set' if 'dy' in elm_update.property_name else elm_update.property_name)
            label = f'{self.prefix}:{elm_update.element_id}:{property_name}'
            await update_or_create_pv(elm_update, label, elm_update.value, 'float', 'd')

    async def push_orbit(self, orbit_result: Orbit):
        logger.warning('Orbit pushing view')

        # Define the PV name for the structured Orbit data
        pv_name = f"{self.prefix}:beam:orbit"

        # Use the new function to update the structured Orbit PV
        try:
            await update_orbit_pv(pv_name, orbit_result)
        except Exception as exc:
            logger.warning('Orbit view pushing failed: %s', exc)
            raise exc
        else:
            logger.warning('Orbit pushed view')

    async def push_twiss(self, twiss_result: TwissWithAggregatedKValues):
        logger.warning('Twiss pushing view')

        # Define the PV name for the structured Twiss data
        pv_name = f"{self.prefix}:beam:twiss"

        # Use the bulk update function to update the structured PV
        await update_twiss_pv(pv_name, twiss_result)
        logger.warning('Twiss pushed view')

    # bessy specific way of setting bpm and pushing it
    async def push_bpms(self, orbit_data):
        if not self.bpm_mimicry:
            raise ValueError("BPM Mimicry not set in ResultView")
        try:
            logger.warning(f"pushing legacy bpm data")
            bpm_legacy_data = self.bpm_mimicry.extract_bpm_legacy_data(orbit_data)
            self.default_bpm_legacy_data = bpm_legacy_data
            await self.push_legacy_bpm_data(bpm_legacy_data)
        except Exception as e:
            logger.error(f"Error processing orbit data: {e}")

    async def push_legacy_bpm_data(self, bpm_legacy_data: Sequence[np.int16] = None):
        """
        Push BPM data to EPICS. If no data is provided, push the default data.
        """
        if bpm_legacy_data is None:
            bpm_legacy_data = self.default_bpm_legacy_data
        logger.info(f"Pushing legacy BPM data at {datetime.now()}")
        await self.bpm_pvs.set_data(bpm_legacy_data)

    async def heart_beat(self):
        """
        Periodic heartbeat function to push default BPM data.
        """

        # logger.warning(f"view heartbeat {datetime.now()}")
        await self.push_legacy_bpm_data(self.default_bpm_legacy_data)
        await self.bpm_pvs.heart_beat()
