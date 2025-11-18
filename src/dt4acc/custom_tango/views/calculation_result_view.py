"""
Tango version of CalculationResultView - matches EPICS structure

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

from ...core.model.element_upate import ElementUpdate
from ...core.model.orbit import Orbit
from ...core.model.twiss import TwissWithAggregatedKValues
from ...core.utils.logger import get_logger
from .create_or_update_pv import update_or_create_pv

logger = get_logger()


async def update_orbit_pv(pv_name, orbit_result):
    """Update orbit PV in Tango device."""
    try:
        from .create_or_update_pv import update_orbit_pv as _update_orbit_pv
        await _update_orbit_pv(pv_name, orbit_result)
    except Exception as e:
        logger.error(f"Failed to update or create Orbit PV {pv_name}: {e}")


async def update_twiss_pv(pv_name, twiss_result):
    """Update twiss PV in Tango device."""
    tune_x = float(twiss_result.x.tune)
    tune_y = float(twiss_result.y.tune)

    # logger.warning(f"Updating twiss values {tune_x, tune_y}")
    try:
        # todo: use translation service to provide the calc may be i will ask waheed on this 
        from .create_or_update_pv import update_twiss_pv as _update_twiss_pv
        await _update_twiss_pv(pv_name, twiss_result)
        #logger.debug("Updated twiss values")
    except Exception as e:
        logger.warning("FAILED Updated twiss values: %s", e)
        logger.error(f"Failed to update or create twiss PV {pv_name}: {e}")


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

        #logger.warning(
            #f"{self.__class__.__name__} Orbit pushing view orbit result is none ? {orbit_result is None}")

        # Define the device name for Tango (prefix is already server_name/instance_name) becuase already defined in the prefix and during the initialization of the view
        device_name = f"{self.prefix}/twiss_orbit_device"

        
        try:
            await update_orbit_pv(device_name, orbit_result)
        except Exception as exc:
            logger.warning('Orbit view pushing failed: %s', exc)
            raise exc
        else:
            logger.info('Orbit pushed view')

    async def push_twiss(self, twiss_result: TwissWithAggregatedKValues):
        
        device_name = f"{self.prefix}/twiss_orbit_device"

        if twiss_result is None:
            return
        
        await update_twiss_pv(device_name, twiss_result)
        #logger.info('Twiss pushed view')
