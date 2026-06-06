"""

Todo:
    review how to factor view out of controller
"""
import logging

from softioc import softioc
from dt4acc.custom_epics.ioc.pv_setup import (
    initialize_power_converter_pvs,
    initialize_master_clock_pvs,
    initialize_cavity_pvs,
    initialize_machine_info_pvs,
    initialize_orbit_object_pvs,
    initialize_orbit_pvs,
    initialize_twiss_pvs,
    initialize_tune_pvs,
    initialize_other_pvs,
    initialize_survey_info_pvs,
)
from dt4acc.custom_epics.ioc.controller import Controller as EpicsController, dispatcher

logger = logging.getLogger("dt4acc")


class BESSYIIEpicsController(EpicsController):
    pass