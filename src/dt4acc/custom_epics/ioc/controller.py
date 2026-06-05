import asyncio
import itertools
import os
import getpass
from typing import Sequence

from softioc import builder, asyncio_dispatcher

from dt4acc_lib.interfaces.utils.command_execution_engine import CommandExecutionEngine
from dt4acc_lib.model.output.result import ReadTogether
from dt4acc_lib.model.utils.command import ReadCommand, Command
from dt4acc.core.interfaces.controller_interface import ControllerInterface
from .view import View
from ...core.utils.logger import get_logger
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
        name: str,
        prefix: str = os.environ.get("DT4ACC_PREFIX", getpass.getuser()),
        builder: builder,
        controller_delegate: ControllerInterface
    ):
        self.name = name
        self.delegate = controller_delegate
        self.builder = builder
        self.prefix = prefix

        self.pending_task = None
        self.task_counter = itertools.count()

    async def startup(self):
        """Initialise all PVs, load the IOC database, and start the delayed
        execution loop.

        Todo:
            needs to be refactored
        """
        raise NotImplementedError("Need to implement this method for your machine")

    async def update(
        self,
        *,
        cmd: Command,
        reads: Sequence[ReadCommand],
        delayed_reads: Sequence[ReadCommand]
    ):
        return await self.delegate.update(
            cmd=cmd, reads=reads, delayed_reads=delayed_reads
        )

    async def trigger_read(self, reads: Sequence[ReadCommand]) -> ReadTogether:
        return await self.delegate.trigger_read(reads=reads)

    async def reread_default_readings(self) -> None:
        """Enqueue delayed reads. Returns as soon as items are on the queue."""
        return await self.delegate.reread_default_readings()
