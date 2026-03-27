import asyncio
import itertools
import os
import getpass
import traceback
from typing import Dict, Sequence

from softioc import softioc, builder, asyncio_dispatcher, pythonSoftIoc

from accml_lib.core.interfaces.utils.measurement_execution_engine import MeasurementExecutionEngine
from accml_lib.core.model.output.result import ReadTogether
from accml_lib.core.model.utils.command import ReadCommand, Command
from accml_lib.core.model.utils.identifiers import ConversionID, DevicePropertyID
from accml_lib.custom.pyat_simulator.accelerator_simulator import PyATAcceleratorSimulator
from dt4acc.custom_epics.ioc.controller_interface import ControllerInterface
from ...core.model.twiss import TwissForPlane
from ...core.utils.logger import get_logger
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
    """Basically a key/value interface to process variables

    * Each key is a :class:`ReadCommand`
    * it contains the appropriate process variable

    Please note:
       * additional context is required for
    """
    def __init__(self):
        self.process_variables: Dict[ReadCommand, pythonSoftIoc.RecordWrapper] = dict()

    def update_process_variables(self, variables: Dict[ReadCommand, pythonSoftIoc.RecordWrapper]):
        """Update process variables with their key

        Todo:
            better register process variables ?
        """
        self.process_variables.update(variables)

    def update_value(self, var: ReadCommand, value):
        """Update the value of a process variable

        **NB** some variables need post processings, these are handled by
        :meth:`update_special_values`
        """
        if self.update_special_values(var, value):
            # processed
            return

        # not processed .. go on standard path
        record_wrapper = self.process_variables.get(var)
        # todo: a better error reporting
        assert record_wrapper is not None
        record_wrapper.set(value)

    def update_special_values(self, var: ReadCommand, value) -> bool:
        if var.id == "tune":
            self.update_tune(var, value)
            return True
        elif var.id == "twiss":
            self.update_twiss(var, value)
            return True
        elif var.id == "track":
            self.update_track(var, value)
            return True
        return False

    def update_track(self, var: ReadCommand, value):
        """

        """
        assert var.id == "track", f"Only prepared to process 'track' but got {var}"
        if var.property == "pos":
            record_wrapper = self.process_variables.get(ReadCommand(id="beam", property="x"))
            assert record_wrapper is not None
            record_wrapper.set([pos.x for pos in value.track])

            record_wrapper = self.process_variables.get(ReadCommand(id="beam", property="y"))
            assert record_wrapper is not None
            record_wrapper.set([pos.y for pos in value.track])

        else:
            # Todo: fix exception type
            raise AssertionError(f"Don't know track property {var.property}")

    def update_tune(self, var: ReadCommand, value):
        """
        Todo:
            need to avoid this hack

        Warning:
            NB: the frequency tune can only be calculated using
            the frequency of master clock or cavities

            This is currently missing
        """
        assert var.id == "tune", f"Only prepared to process 'tune' but got {var}"

        if var.property == "x":
            rcmd = ReadCommand("tune", "x")
            record_wrapper = self.process_variables.get(rcmd)
            assert record_wrapper is not None, f"No process variable for {rcmd}"
            record_wrapper.set(value.x)
            return

        elif var.property == "y":
            rcmd = ReadCommand("tune", "y")
            record_wrapper = self.process_variables.get(rcmd)
            assert record_wrapper is not None, f"No process variable for {rcmd}"
            record_wrapper.set(value.y)
            return

        else:
            # Todo: better exception
            raise AssertionError(f"For tune: don't know how to handle {var}")

        raise AssertionError("Should not end up here")

    def update_twiss(self, var: ReadCommand, value):
        assert var.id == "twiss", f"Only prepared to process 'twiss' but got {var}"
        for plane in ("x", "y"):
            record_wrapper = self.process_variables.get(ReadCommand("twiss", f"{plane}:beta"))
            assert record_wrapper is not None
            record_wrapper.set([getattr(pos, plane).beta for pos in value.twiss])

            record_wrapper = self.process_variables.get(ReadCommand("twiss", f"{plane}:alpha"))
            assert record_wrapper is not None
            record_wrapper.set([getattr(pos, plane).alpha for pos in value.twiss])

            record_wrapper = self.process_variables.get(ReadCommand("twiss", f"{plane}:nu"))
            assert record_wrapper is not None
            record_wrapper.set([getattr(pos, plane).nu for pos in value.twiss])

        record_wrapper = self.process_variables.get(ReadCommand("twiss", "names"))
        assert record_wrapper is not None
        record_wrapper.set([pos.name for pos in value.twiss])


class Controller(ControllerInterface):
    """
    Todo:
        * add heart beat / periodic update variables
        * review integration with asyncio
    """
    def __init__(
        self,
        *,
        view: View,
        mexec: MeasurementExecutionEngine,
        prefix: str = os.environ.get("DT4ACC_PREFIX", getpass.getuser()),
        builder: builder,
        default_delayed_reads : Sequence[ReadCommand]
    ):
        self.view = view
        self.mexec = mexec
        self.builder = builder
        self.prefix = prefix

        self.pending_task = None
        self.task_counter = itertools.count()
        self.cmd_queue = asyncio.Queue()
        self.default_delayed_reads = default_delayed_reads

    async def startup(self):
        """
        Main function to initialize all the process variables (PVs) and start the IOC server.
        """
        # Retrieve the device name prefix from the environment, defaulting to getpass.getuser() if not set
        prefix = self.prefix

        self.builder.SetDeviceName(self.prefix)

        self.view.update_process_variables({
            # Initialize additional PVs such as master clock, dummy data
            **await initialize_master_clock_pvs(self.builder, controller=self),
            **await initialize_cavity_pvs(self.builder, controller=self),
              # Initialize power converters and linked magnets
            **await initialize_power_converter_pvs(self.builder, self.prefix, controller=self),
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
        logger.warning("All pvs set up")

        # Initialize PVs for various accelerator components
        # Initialize Beam Position Monitor PVs
        # which are not used like that any more at BESSY II
        # initialize_bpm_pvs(self.builder)

        # Load the database of PVs defined above into the SoftIOC server
        builder.LoadDatabase()
        # Start the SoftIOC server to handle PV interactions
        softioc.iocInit(dispatcher)

        self.start_delayed_execution_task()
        # Start monitoring the heartbeat to ensure the server is running correctly
        # asyncio.create_task(monitor_heartbeat(), name="server-heartbeat-loop")

    async def update(
            self,
            *,
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

        Todo:
            push delayed records ...
        """
        r = await self.mexec.set([cmd])
        # now push these into the view
        read_data = await self.trigger_read(reads)
        for rcmd, rdata in zip(reads, read_data.data):
            self.view.update_value(rcmd, rdata.payload)
        # push delayed data where they belong to
        await self.request_delayed_reads(
            list(self.default_delayed_reads) + list(delayed_reads)
        )

    async def trigger_read(self, reads: Sequence[ReadCommand]) -> ReadTogether:
        return await self.mexec.trigger_read(reads)

    async def request_delayed_reads(self, reads: Sequence[ReadCommand]):
        """Put delayed commands on queue

        Warning:
                returns as soon as commands are on queue
        """
        await asyncio.wait_for(
            asyncio.gather(*[self.cmd_queue.put(r) for r in reads]) , timeout=0.1
        )

    def start_delayed_execution_task(self):
        assert self.pending_task is None
        task_count = next(self.task_counter)
        self.pending_task = asyncio.create_task(
            self._operate_on_queue_loop(),
            name=f"controller-delayed-execution-task-{task_count}"
        )

    async def _operate_on_queue_loop(self):
        for cnt in itertools.count():
            logger.debug("Operating on queue step %s", cnt)
            await self._operate_on_queue_step()

    async def _operate_on_queue_step(self):
        """
        Todo:
            Review where/what to report when delayed execution or
            view updates go wrong
        """
        logger.debug("Waiting for cmd queue for new data")
        rcmds = await consume(queue=self.cmd_queue, delay=0.05)
        # Assuming that I can drop all rcmds which are doubled
        if rcmds:
            t_rcmds = tuple(set(rcmds))
            logger.info("Executing delayed commands %s", t_rcmds)
            try:
                read_data = await self.trigger_read(t_rcmds)
            except Exception as exc:
                logger.error("Failed to retrieve data from backend using %s: reason %s", t_rcmds, exc)
                traceback.print_exc()
                raise exc
            finally:
                logger.debug("Retrieved data from backend using %s", t_rcmds)

            for rc, rd in zip(t_rcmds, read_data.data):
                try:
                    self.view.update_value(rc, rd.payload)
                except Exception as exc:
                    # Todo: should this be handled by the view?
                    logger.error("Failed to push view %s using data %s: reason %s", rc, rd, exc)
                    traceback.print_exc()
                    raise exc


async def consume(queue: asyncio.Queue, delay: float) -> Sequence[ReadCommand]:
    """
    Todo:
        consider if a total delay should be respected
        If data are arriving constantly, perhaps some processing should happen
        then to


    """
    rcmds = []
    while True:
        try:
            # Wait for next item but only up to `delay`
            rcmd = await asyncio.wait_for(queue.get(), timeout=delay)
        except asyncio.TimeoutError:
            logger.debug("No new command arrived within %s", delay)
            break

        logger.debug(f"controller cmd queue, got item: %s", rcmd)
        rcmds.append(rcmd)
        queue.task_done()

        # Wait fixed delay after each item
        await asyncio.sleep(delay)

    logger.debug(f"controller cmd queue: accumulated commands: %s", rcmds)
    return rcmds
