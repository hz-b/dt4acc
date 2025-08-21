"""

Todo:
    improve periodic update of data e.g. orbit data
    * Should that be provided by an periodic publisher?
    * Should there be a central instance that informs
      periodic publishers that
      * calculations have been requested: i.e. update
        was called
      * that these cache data internally until it needs
        being republished
"""
import itertools
from datetime import datetime
from typing import Sequence

import numpy as np
import pandas as pd
from p4p.client.asyncio import Context

from ...core.model.element_upate import ElementUpdate
from ...core.model.orbit import Orbit
from ...core.model.twiss import TwissWithAggregatedKValues, TwissForPlane, Twiss
from ...core.utils.logger import get_logger
from ..data.constants import special_pvs
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
    tune_x = float(twiss_result.x.tune)
    tune_y = float(twiss_result.y.tune)

    # todo: remove me
    # currently adding very small noise to get data republished
    # need to check softioc what its records can do
    tune_x += np.random.uniform(-1e-12, 1e-12)
    tune_y += np.random.uniform(-1e-12, 1e-12)

    # logger.warning(f"Updating twiss values {tune_x, tune_y}")
    try:
        # todo: use translation service to provide the calc
        await ctx.put(f"{pv_name}:x:tune", tune_x)
        await ctx.put(f"{pv_name}:x:alpha", twiss_result.x.alpha)
        await ctx.put(f"{pv_name}:x:beta", twiss_result.x.beta)
        await ctx.put(f"{pv_name}:x:nu", twiss_result.x.nu)
        await ctx.put(f"{pv_name}:y:tune", tune_y )
        await ctx.put(f"{pv_name}:y:alpha", twiss_result.y.alpha)
        await ctx.put(f"{pv_name}:y:beta", twiss_result.y.beta)
        await ctx.put(f"{pv_name}:y:nu", twiss_result.y.nu)
        logger.debug("Updated twiss values")
        # await ctx.put(f"{pv_name}:names", twiss_result.names)
    except Exception as e:
        logger.warning("FAILED Updated twiss values: %s", e)
        logger.error(f"Failed to update or create twiss PV {pv_name}: {e}")
    try:

        await ctx.put([k.pv_name for k in twiss_result.main_values], [k.value for k in twiss_result.main_values])
    except Exception as e:
        logger.error(f"Failed to update or create magnet_strength PV {pv_name}: {e}")

# Todo: a better mimicry
counter = itertools.count()

class ResultView:
    def __init__(self, *, prefix):
        self.prefix = prefix
        self.bpm_pvs = BeamPositionPVs(prefix=f"{self.prefix}:{special_pvs['bpm_pv']}")
        tmp = np.empty([2048], np.int16)
        tmp.fill(-2 ** 15 + 1)
        self.default_bpm_legacy_data = tmp
        self.orbit_object_data = None
        self.default_twiss = None
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
        logger.info('Orbit pushing view')

        # Define the PV name for the structured Orbit data
        pv_name = f"{self.prefix}:beam:orbit"

        # Use the new function to update the structured Orbit PV
        try:
            await update_orbit_pv(pv_name, orbit_result)
        except Exception as exc:
            logger.warning('Orbit view pushing failed: %s', exc)
            raise exc
        else:
            logger.info('Orbit pushed view')

    async def push_twiss(self, twiss_result: TwissWithAggregatedKValues):
        # logger.warning('Twiss pushing view')

        # Define the PV name for the structured Twiss data
        pv_name = f"{self.prefix}:beam:twiss"

        if twiss_result is None:
            return
        self.default_twiss = twiss_result
        # Use the bulk update function to update the structured PV
        await update_twiss_pv(pv_name, twiss_result)
        logger.info('Twiss pushed view')

    # bessy specific way of setting bpm and pushing it
    async def push_bpms(self, orbit_data):
        if not self.bpm_mimicry:
            raise ValueError("BPM Mimicry not set in ResultView")
        try:
            logger.info(f"pushing legacy bpm data")
            df_bpm = self.bpm_mimicry.extract_bpm_legacy_data_to_df(orbit_data)
            bpm_legacy_data = self.bpm_mimicry.bpm_legacy_data_df_to_array(df_bpm)
            self.default_bpm_legacy_data = bpm_legacy_data
            await self.push_legacy_bpm_data(bpm_legacy_data)
            orbit_object_data = df_bpm.copy()
            mm2nm = 1e6
            orbit_object_data.x = df_bpm.x * mm2nm
            orbit_object_data.y = df_bpm.y * mm2nm
            self.orbit_object_data = orbit_object_data
            await self.push_orbit_object(self.orbit_object_data)
        except Exception as e:
            logger.error(f"Error processing orbit data: {e}")

    async def push_orbit_object(self, bpm_data: pd.DataFrame):
        try:
            prefix = f"{self.prefix}:ORBITCC"
            # Todo: check that the dimensions are properly made
            pos = np.array(bpm_data.loc[:, ["x", "y"]]).ravel()
            await ctx.put(f"{prefix}:rdPos", pos)
            await ctx.put(f"{prefix}:rdBpmNames", [str(val) for val in bpm_data.index])
            await ctx.put(f"{prefix}:count", next(counter))
        except Exception as e:
            logger.error(f"Error processing orbit object data: {e}")

    async def push_legacy_bpm_data(self, bpm_legacy_data: Sequence[np.int16] = None):
        """
        Push BPM data to EPICS. If no data is provided, push the default data.
        """
        if bpm_legacy_data is None:
            logger.info(f"Pushing legacy BPM data at {datetime.now()}")
            bpm_legacy_data = self.default_bpm_legacy_data
        await self.bpm_pvs.set_data(bpm_legacy_data)

        if self.orbit_object_data is None:
            return
        logger.info(f"Pushing orbit object data at {datetime.now()}")
        await self.push_orbit_object(self.orbit_object_data)

    async def heart_beat(self):
        """
        Periodic heartbeat function to push default BPM data.
        """

        # logger.warning(f"view heartbeat {datetime.now()}")
        await self.push_legacy_bpm_data(self.default_bpm_legacy_data)
        await self.push_twiss(self.default_twiss)
        # Todo: remove this duplication ...
        #       currently
        #
        # await self.bpm_pvs.heart_beat()