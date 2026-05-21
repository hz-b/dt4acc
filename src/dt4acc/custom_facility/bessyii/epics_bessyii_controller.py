"""

Todo:
    review how to factor view out of controller
"""
import logging

from softioc import softioc, asyncio_dispatcher
from dt4acc.custom_epics.ioc.pv_setup import initialize_power_converter_pvs, initialize_master_clock_pvs, \
    initialize_cavity_pvs, initialize_machine_info_pvs, initialize_orbit_object_pvs, initialize_orbit_pvs, \
    initialize_twiss_pvs, initialize_tune_pvs, initialize_other_pvs
from dt4acc.custom_epics.ioc.controller import Controller as EpicsController, dispatcher

logger = logging.getLogger("dt4acc")


class BESSYIIEpicsController(EpicsController):
    async def startup(self):
        self.builder.SetDeviceName(self.prefix)

        self.delegate.view.update_process_variables(
            {
                **await initialize_master_clock_pvs(self.builder, controller=self),
                **await initialize_cavity_pvs(self.builder, controller=self),
                **await initialize_power_converter_pvs(
                    self.builder, self.prefix, controller=self
                ),
                **initialize_machine_info_pvs(self.builder),
                **initialize_orbit_object_pvs(self.builder),
                **initialize_orbit_pvs(self.builder),
                **initialize_twiss_pvs(self.builder),
                **initialize_tune_pvs(self.builder),
                **initialize_other_pvs(self.builder, self.prefix),
            }
        )
        logger.warning("All PVs set up")

        self.builder.LoadDatabase()
        softioc.iocInit(dispatcher)
