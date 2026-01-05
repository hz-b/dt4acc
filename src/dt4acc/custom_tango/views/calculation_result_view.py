import asyncio

import numpy as np

from ...core.model.element_upate import ElementUpdate
from ...core.model.orbit import Orbit
from ...core.model.twiss import TwissWithAggregatedKValues
from ...core.utils.logger import get_logger
from .create_or_update_pv import update_or_create_pv

logger = get_logger()


async def update_orbit_pv(pv_name, orbit_result):
    try:
        from .create_or_update_pv import update_orbit_pv as _update_orbit_pv
        await _update_orbit_pv(pv_name, orbit_result)
    except Exception as e:
        logger.error(f"Failed to update or create Orbit PV {pv_name}: {e}")


async def update_twiss_pv(pv_name, twiss_result):
    tune_x = float(twiss_result.x.tune)
    tune_y = float(twiss_result.y.tune)

    try:
        
        from .create_or_update_pv import update_twiss_pv as _update_twiss_pv
        await _update_twiss_pv(pv_name, twiss_result)
    except Exception as e:
        logger.warning("FAILED Updated twiss values: %s", e)


class CalculationResultView:
    def __init__(self, *, prefix):
        self.prefix = prefix

    async def push_value(self, elm_update: ElementUpdate):
        if elm_update.property_name == "K":
            
            await asyncio.sleep(0.0)
        else:
            property_name = 'x:set' if 'x' in elm_update.property_name else (
                'y:set' if 'dy' in elm_update.property_name else elm_update.property_name)
            label = f'{self.prefix}:{elm_update.element_id}:{property_name}'
            await update_or_create_pv(elm_update, label, elm_update.value, 'float', 'd')

    async def push_orbit(self, orbit_result: Orbit):
        # If prefix is PHYSICS/SOLEIL, use it directly, otherwise use the registered name
        if self.prefix and "/" in self.prefix:
            # Prefix is like "PHYSICS/SOLEIL", construct device name
            device_name = f"{self.prefix}/TWISS_ORBIT"
        else:
            # Use the standard registered device name
            device_name = "PHYSICS/SOLEIL/TWISS_ORBIT"
        
        try:
            await update_orbit_pv(device_name, orbit_result)
        except Exception as exc:
            logger.warning('Orbit view pushing failed: %s', exc)
            raise exc
        else:
            logger.info('Orbit pushed view')

    async def push_twiss(self, twiss_result: TwissWithAggregatedKValues):
        if self.prefix and "/" in self.prefix:
            device_name = f"{self.prefix}/TWISS_ORBIT"
        else:
            device_name = "PHYSICS/SOLEIL/TWISS_ORBIT"

        if twiss_result is None:
            return
        
        await update_twiss_pv(device_name, twiss_result)