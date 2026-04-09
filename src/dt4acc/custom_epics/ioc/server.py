import asyncio
import itertools
import os
import getpass
import time
import traceback
from typing import Dict, Optional, Sequence

from softioc import softioc, builder, asyncio_dispatcher, pythonSoftIoc

from dt4acc_lib.core.interfaces.utils.command_execution_engine import CommandExecutionEngine
from dt4acc_lib.core.model.output.result import ReadTogether
from dt4acc_lib.core.model.utils.command import ReadCommand, Command
from dt4acc.core.interfaces.controller_interface import ControllerInterface
from ...core.utils.logger import get_logger
from .orbit_pva import OrbitTwinServer
from .pv_setup import (
    initialize_power_converter_pvs,
    initialize_cavity_pvs,
    initialize_master_clock_pvs,
    initialize_orbit_pvs,
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
    """Key/value interface to process variables.

    Each key is a :class:`ReadCommand`; each value is the corresponding
    ``RecordWrapper`` from pythonSoftIoc.

    Special cases (twiss, track/orbit, tune) are dispatched explicitly.
    The orbit path additionally pushes to the PVA NTTable via
    :class:`OrbitTwinServer` when one is registered.
    """

    def __init__(self, *, orbit_server: Optional[OrbitTwinServer] = None):
        self.process_variables: Dict[ReadCommand, pythonSoftIoc.RecordWrapper] = dict()
        self.orbit_server = orbit_server

    def update_process_variables(
        self, variables: Dict[ReadCommand, pythonSoftIoc.RecordWrapper]
    ):
        self.process_variables.update(variables)

    def update_value(self, var: ReadCommand, pkg):
        """Update the value of a process variable.

        Special-cased variables (tune, twiss, track) are dispatched to their
        own handlers; everything else takes the generic path.
        """
        if self.update_special_values(var, pkg):
            return

        record_wrapper = self.process_variables.get(var)
        (single_reading,) = pkg.readings
        value = single_reading.payload
        assert record_wrapper is not None, f"No process variable registered for {var}"
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

    def update_track(self, var: ReadCommand, pkg):
        assert var.id == "track", f"Only prepared to process 'track' but got {var}"
        (single_reading,) = pkg.readings
        value = single_reading.payload

        if var.property == "pos":
            x_vals = [pos.x for pos in value.track]
            y_vals = [pos.y for pos in value.track]
            names = [pos.name for pos in value.track]

            rw_x = self.process_variables.get(ReadCommand(id="beam", property="x"))
            rw_y = self.process_variables.get(ReadCommand(id="beam", property="y"))
            assert rw_x is not None
            assert rw_y is not None
            rw_x.set(x_vals)
            rw_y.set(y_vals)

            rw_names = self.process_variables.get(ReadCommand(id="beam", property="name"))
            if rw_names is not None:
                rw_names.set(names)

            rw_found = self.process_variables.get(ReadCommand(id="beam", property="found"))
            if rw_found is not None:
                rw_found.set(True)

            # PVA NTTable
            if self.orbit_server is not None:
                try:
                    self.orbit_server.push(x=x_vals, y=y_vals, names=names)
                except Exception as exc:
                    logger.error("OrbitTwinServer.push failed: %s", exc)
        else:
            raise AssertionError(f"Don't know track property {var.property}")

    def update_tune(self, var: ReadCommand, pkg):
        assert var.id == "tune", f"Only prepared to process 'tune' but got {var}"
        logger.warning("Tune view needs to be implemented")
        return

    def update_twiss(self, var: ReadCommand, pkg):
        assert var.id == "twiss", f"Only prepared to process 'twiss' but got {var}"

        (single_reading,) = pkg.readings
        value = single_reading.payload
        for plane in ("x", "y"):
            for param in ("beta", "alpha", "nu"):
                rw = self.process_variables.get(
                    ReadCommand("twiss", f"{plane}:{param}")
                )
                assert rw is not None
                rw.set([getattr(getattr(pos, plane), param) for pos in value.twiss])

        rw_names = self.process_variables.get(ReadCommand("twiss", "names"))
        assert rw_names is not None
        rw_names.set([pos.name for pos in value.twiss])


class Controller(ControllerInterface):
    """Async orchestrator between the backend engine and the EPICS/PVA views.

    Responsibilities:
    - Build all PVs at startup and hand them to the View
    - Route immediate reads back to the View after each set()
    - Batch and debounce expensive delayed reads (twiss, orbit, tune)
      via an asyncio.Queue
    """

    def __init__(
        self,
        *,
        view: View,
        mexec: CommandExecutionEngine,
        prefix: str = os.environ.get("DT4ACC_PREFIX", getpass.getuser()),
        builder: builder,
        default_delayed_reads: Sequence[ReadCommand],
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
        """Initialise all PVs, load the IOC database, and start the delayed
        execution loop."""
        self.builder.SetDeviceName(self.prefix)

        self.view.update_process_variables(
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

        builder.LoadDatabase()
        softioc.iocInit(dispatcher)

        self.start_delayed_execution_task()

    async def update(
        self,
        *,
        cmd: Command,
        reads: Sequence[ReadCommand],
        delayed_reads: Sequence[ReadCommand],
    ):
        """Apply a command to the backend, push immediate reads, queue delayed ones."""
        await self.mexec.set([cmd])
        read_data = await self.trigger_read(reads)
        for rcmd, rdata in zip(reads, read_data.data):
            self.view.update_value(rcmd, rdata)
        await self.request_delayed_reads(
            list(self.default_delayed_reads) + list(delayed_reads)
        )

    async def trigger_read(self, reads: Sequence[ReadCommand]) -> ReadTogether:
        return await self.mexec.trigger_read(reads)

    async def request_delayed_reads(self, reads: Sequence[ReadCommand]):
        """Enqueue delayed reads. Returns as soon as items are on the queue."""
        await asyncio.wait_for(
            asyncio.gather(*[self.cmd_queue.put(r) for r in reads]), timeout=0.1
        )

    def start_delayed_execution_task(self):
        assert self.pending_task is None
        task_count = next(self.task_counter)
        self.pending_task = asyncio.create_task(
            self._operate_on_queue_loop(),
            name=f"controller-delayed-execution-task-{task_count}",
        )

    async def _operate_on_queue_loop(self):
        for cnt in itertools.count():
            logger.debug("Operating on queue step %s", cnt)
            await self._operate_on_queue_step()

    async def _operate_on_queue_step(self):
        rcmds = await consume(queue=self.cmd_queue, delay=0.05)
        if not rcmds:
            return

        t_rcmds = tuple(set(rcmds))
        logger.info("Executing delayed commands %s", t_rcmds)
        try:
            read_data = await self.trigger_read(t_rcmds)
        except Exception as exc:
            logger.error(
                "Failed to retrieve data from backend using %s: %s", t_rcmds, exc
            )
            traceback.print_exc()
            # Log and continue — don't kill the queue loop on transient errors
            return

        l_cmds = len(t_rcmds)
        l_data = len(read_data.data)
        if l_cmds != l_data:
            logger.error(
                "Used %d read commands but received %d results — skipping", l_cmds, l_data
            )
            return

        for rc, rd in zip(t_rcmds, read_data.data):
            try:
                self.view.update_value(rc, rd)
            except Exception as exc:
                logger.error(
                    "Failed to push view for %s using data %s: %s", rc, rd, exc
                )
                traceback.print_exc()
                # Continue processing remaining commands


async def consume(queue: asyncio.Queue, delay: float) -> Sequence[ReadCommand]:
    """Drain the queue, waiting up to ``delay`` seconds for the first item.

    Subsequent items are collected without additional delay so the loop
    drains as fast as possible before the next sleep cycle.
    """
    rcmds = []
    while True:
        try:
            rcmd = await asyncio.wait_for(queue.get(), timeout=delay)
        except asyncio.TimeoutError:
            logger.debug("No new command arrived within %s s", delay)
            break

        logger.debug("Controller cmd queue, got item: %s", rcmd)
        rcmds.append(rcmd)
        queue.task_done()

    logger.debug("Controller cmd queue: accumulated commands: %s", rcmds)
    return rcmds