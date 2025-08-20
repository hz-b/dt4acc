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
import asyncio

import numpy as np

from ..utils.context_proxy import ContextProxy
from ...core.model.element_upate import ElementUpdate
from ...core.model.orbit import Orbit
from ...core.model.twiss import TwissWithAggregatedKValues
from ...core.utils.logger import get_logger
from ..views.create_or_update_pv import update_or_create_pv

logger = get_logger()

ctx = ContextProxy("pva")


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


class CalculationResultView:
    def __init__(self, *, prefix):
        self.prefix = prefix

    async def push_value(self, elm_update: ElementUpdate):
        if elm_update.property_name == "K":
            # to create a future
            await asyncio.sleep(0.0)
        else:
            property_name = 'x:set' if 'x' in elm_update.property_name else (
                'y:set' if 'dy' in elm_update.property_name else elm_update.property_name)
            label = f'{self.prefix}:{elm_update.element_id}:{property_name}'
            await update_or_create_pv(elm_update, label, elm_update.value, 'float', 'd')

    async def push_orbit(self, orbit_result: Orbit):

        logger.warning(
            f"{self.__class__.__name__} Orbit pushing view orbit result is none ? {orbit_result is None}")

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
        # Use the bulk update function to update the structured PV
        await update_twiss_pv(pv_name, twiss_result)
        logger.info('Twiss pushed view')
