import logging
from datetime import datetime
from typing import Sequence

import numpy as np
from bact_device_models.devices.bpm_elem import BpmElementList

from .create_or_update_pv import update_or_create_pv, update_orbit_pv, update_twiss_pv, update_bpm_pv
from ..model.element_upate import ElementUpdate
from ..model.orbit import Orbit
from ..model.twiss import TwissWithAggregatedKValues

logger = logging.getLogger("dt4acc")


class StatusFlagView:
    def __init__(self, *, prefix):
        self.prefix = prefix

    async def on_update(self, flag: bool):
        return
        if isinstance(flag, datetime):
            val = True  # or False, depending on your logic
        else:
            val = int(flag)
        await update_or_create_pv(self, self.prefix, val, 'bool', 'b')
        # pydev.iointr(self.prefix, val)
        logger.debug("sent label %s, val %s", self.prefix, val)


class ElementParameterView:
    def __init__(self, *, prefix):
        self.prefix = prefix

    async def push_value(self, elm_update: ElementUpdate):
        if elm_update.property_name == "K":
            pass
        else:
            property_name = 'x:set' if 'x' in elm_update.property_name else (
                'y:set' if 'dy' in elm_update.property_name else elm_update.property_name)
            label = f'{self.prefix}:{elm_update.element_id}:{property_name}'
            await update_or_create_pv(elm_update, label, elm_update.value, 'float', 'd')


class ResultView:
    def __init__(self, *, prefix):
        self.prefix = prefix

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

    async def push_bpms(self, bpm_result: BpmElementList):
        logger.warning('BPM pushing view')

        # Define the PV name for the structured BPM data
        pv_name = f"{self.prefix}:beam:bpm"

        # Use the new function to update the structured BPM PV
        await update_bpm_pv(pv_name, bpm_result)

    async def push_legacy_bpm_data(self, bpm_legacy_data: Sequence[np.int16]):
        # Define the PV name for the structured BPM data
        # todo: find out
        # todo: address prefix
        logger.warning(f'BPM pushing legacy bpm data  time: {datetime.now()}')
        pv_name = f"{self.prefix}:MDIZ2T5G:bdata"

        # Use the new function to update the structured BPM PV
        await update_bpm_pv(pv_name, bpm_legacy_data)
