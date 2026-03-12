import asyncio
import os
import getpass
from abc import ABCMeta, abstractmethod
from typing import Dict, Union, Any, Sequence

from softioc import softioc, builder, asyncio_dispatcher, pythonSoftIoc



from accml.core.utils.basic_measurement_execution_engine import BasicMeasurementExecutionEngine
from accml_lib.core.bl.command_rewritter import CommandRewriter
from accml_lib.core.interfaces.backend.backend import BackendR, BackendRW
from accml_lib.core.interfaces.utils.measurement_execution_engine import MeasurementExecutionEngine
from accml_lib.core.model.utils.command import ReadCommand, Command
from accml_lib.custom.bessyii.liasion_translator_setup import load_managers
from dt4acc.core.accelerators.pyat_accelerator import setup_accelerator
from ...core.utils.logger import get_logger
from .tasks import monitor_heartbeat
from .pv_setup import (
    initialize_power_converter_pvs,
    initialize_cavity_pvs,
    initialize_master_clock_pvs,
    initialize_orbit_pvs,
    # obsolete ... such data do not exist any more for BESSY II
    # initialize_bpm_pvs,
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
            mexec: MeasurementExecutionEngine,
            prefix: str = os.environ.get("DT4ACC_PREFIX", getpass.getuser()),
            builder: builder
    ):
        self.prefix = prefix
        self.process_variables: Dict[ReadCommand, pythonSoftIoc.RecordWrapper] = dict()
        self.mexec = mexec
        self.builder = builder

    async def startup(self):
        """
        Main function to initialize all the process variables (PVs) and start the IOC server.
        """
        # Retrieve the device name prefix from the environment, defaulting to getpass.getuser() if not set
        prefix = self.prefix

        self.builder.SetDeviceName(self.prefix)

        self.process_variables.update({
            # Initialize additional PVs such as master clock, dummy data
            **await initialize_master_clock_pvs(self.builder, mexec=self.mexec),
            **await initialize_cavity_pvs(self.builder, mexec=self.mexec),
              # Initialize power converters and linked magnets
            **await initialize_power_converter_pvs(self.builder, self.prefix, mexec=self.mexec),
            **initialize_machine_info_pvs(self.builder),
            # Initialize PV's of the new orbit object ... collection of bpms
            #   (ca access possible)
            **initialize_orbit_object_pvs(self.builder),
            # orbit all around the machine (at each element)
            **initialize_orbit_pvs(self.builder),
            # as calculated from the model
            **initialize_twiss_pvs(self.builder),
            # as calculated from the model
            **initialize_tune_pvs(self.builder),
            **initialize_other_pvs(self.builder, prefix)  # Initialize additional PVs such as master clock, dummy data
        })

        # Initialize PVs for various accelerator components
        # Initialize Beam Position Monitor PVs
        # which are not used like that any more at BESSY II
        # initialize_bpm_pvs(self.builder)
          # Initialize Twiss parameter PVs
        logger.warning("All pvs set up")

        # Load the database of PVs defined above into the SoftIOC server
        builder.LoadDatabase()
        # Start the SoftIOC server to handle PV interactions
        softioc.iocInit(dispatcher)

        # Start monitoring the heartbeat to ensure the server is running correctly
        asyncio.create_task(monitor_heartbeat(), name="server-heartbeat-loop")

class ControllerInterface(metaclass=ABCMeta):
    @abstractmethod
    async def update(
            self,
            cmd: Command,
            reads: Sequence[ReadCommand],
            delayed_reads: Sequence[ReadCommand]
    ):
        """update a value (in the back engine) and update views accordingly

        Args:
            cmd: command that changes value in the back engine
            reads: read commands to peek into the back engine and update
                   immediately
            delayed_reads: read commands that typically require calculations
                           these are only updated with a delay
                           e.g. calculation of twiss or orbit
        """

class Controller:
    def __init__(
        self,
        *,
        view: View,
    ):
        self.view = view
        self.mexec = mexec
        self.builder = builder
        self.prefix = prefix

    async def update(
            self,
            cmd: Command,
            reads: Sequence[ReadCommand],
            delayed_reads: Sequence[ReadCommand]
    ):
        """update a value (in the back engine) and update views accordingly

        Args:
            cmd: command that changes value in the back engine
            reads: read commands to peek into the back engine and update
                   immediately
            delayed_reads: read commands that typically require calculations
                           these are only updated with a delay
                           e.g. calculation of twiss or orbit
        """

        await self.mexec.set([cmd])
        read_data = self.mexec.trigger_read(reads)
        # now push these into the view

        # push delayed data where they belong to


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
    # Todo: should be rather a controller
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