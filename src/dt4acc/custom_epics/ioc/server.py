import asyncio
import os
import getpass
from typing import Dict, Union

from softioc import softioc, builder, asyncio_dispatcher

from accml.core.utils.basic_measurement_execution_engine import BasicMeasurementExecutionEngine
from accml_lib.core.bl.command_rewritter import CommandRewriter
from accml_lib.core.interfaces.backend.backend import BackendR, BackendRW
from accml_lib.core.interfaces.utils.measurement_execution_engine import MeasurementExecutionEngine
from accml_lib.core.model.utils.command import ReadCommand
from accml_lib.custom.bessyii.liasion_translator_setup import load_managers
from dt4acc.core.accelerators.pyat_accelerator import setup_accelerator
from ...core.utils.logger import get_logger
from .tasks import monitor_heartbeat
from .pv_setup import (
    initialize_power_converter_pvs,
    initialize_cavity_pvs,
    initialize_master_clock_pvs,
    initialize_orbit_pvs,
    initialize_bpm_pvs,
    initialize_orbit_object_pvs,
    initialize_twiss_pvs,
    initialize_tune_pvs,
    initialize_other_pvs,
    initialize_machine_info_pvs,
)

logger = get_logger()

# Create an asyncio dispatcher to handle asynchronous PV updates
dispatcher = asyncio_dispatcher.AsyncioDispatcher()


class View:
    def __init__(
            self,
            *,
            prefix: str = os.environ.get("DT4ACC_PREFIX", getpass.getuser()),
            mexec: MeasurementExecutionEngine,
            builder
    ):
        self.prefix = prefix
        self.process_variable: Dict[ReadCommand, Union[BackendR, BackendRW]] = dict()
        self.mexec = mexec
        self.builder = builder

    async def startup(self):
        """
        Main function to initialize all the process variables (PVs) and start the IOC server.
        """
        # Retrieve the device name prefix from the environment, defaulting to getpass.getuser() if not set
        prefix = self.prefix

        self.builder.SetDeviceName(self.prefix)

        await initialize_master_clock_pvs(self.builder, mexec=self.mexec)  # Initialize additional PVs such as master clock, dummy data

        await initialize_power_converter_pvs(self.builder, self.prefix)  # Initialize power converters and linked magnets
        await initialize_cavity_pvs(self.builder)  # Initialize cavity-related PVs
        initialize_machine_info_pvs(self.builder)
        initialize_other_pvs(self.builder, prefix)  # Initialize additional PVs such as master clock, dummy data

        # Initialize PVs for various accelerator components
        initialize_bpm_pvs(self.builder)  # Initialize Beam Position Monitor PVs
        initialize_orbit_pvs(self.builder)  # Initialize orbit-related PVs
        initialize_orbit_object_pvs(self.builder)  # Initialize PV's of the new orbit object ... collection of bpms
        initialize_twiss_pvs(self.builder)  # Initialize Twiss parameter PVs
        initialize_tune_pvs(self.builder)
        logger.warning("All pvs set up")

        # Load the database of PVs defined above into the SoftIOC server
        builder.LoadDatabase()
        # Start the SoftIOC server to handle PV interactions
        softioc.iocInit(dispatcher)

        # Start monitoring the heartbeat to ensure the server is running correctly
        asyncio.create_task(monitor_heartbeat(), name="server-heartbeat-loop")


def main():
    # Start the IOC server by dispatching the main function
    _, lm, tm = load_managers()
    command_rewriter=CommandRewriter(
        liaison_manager=lm,
        translation_service=tm
    )
    # Todo: review if a dedicated execution engine
    #       View gets an engine to execute
    #       each trigger calls to the engine. When something happens
    mexec = BasicMeasurementExecutionEngine(
        backend=setup_accelerator(),
        cmd_rewriter=command_rewriter,
        storage=None,
        expected_view_for_output="device",
        num_readings=1,
    )
    view = View(
        mexec=mexec,
        builder=builder
    )
    dispatcher(view.startup)
    # Start the interactive IOC shell, allowing interaction with the server
    softioc.interactive_ioc(globals())


# Entry point of the script
if __name__ == "__main__":
    main()