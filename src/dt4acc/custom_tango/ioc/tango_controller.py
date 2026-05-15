"""
tango_controller.py
===================

TANGO equivalent of the EPICS Controller in custom_epics/ioc/server.py.

Architecture
------------

MagnetDevice / PowerConverterDevice
  └─ _async(controller.update(cmd, reads, delayed_reads))
       ├─ mexec.set([cmd])                         # mutate backend lattice
       ├─ mexec.trigger_read(reads)                # immediate readback
       │     └─ view.dispatch(rcmd, translated)    # push to Tango virtual devices
       └─ queue delayed_reads                      # twiss, orbit, tune
             └─ consume + deduplicate
                   └─ mexec.trigger_read(t_rcmds)
                         └─ view.dispatch(...)

The TANGO View dispatches results to CalculationResultView, which pushes
data into TwissOrbitDevice / BPMManagerDevice / TuneDevice via DeviceProxy.
"""

import asyncio
import itertools
import traceback
from typing import Sequence

from dt4acc.core.interfaces.controller_interface import ControllerInterface
from dt4acc.custom_tango.ioc.view import TangoView
from dt4acc_lib.model.output.result import TranslatedReading, ReadTogetherAndTranslated, ReadTogether
from dt4acc_lib.model.utils.command import ReadCommand, Command
from dt4acc.core.bl.translating_command_execution_engine import TranslatingCommandExecutionEngine
from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_tango.views.calculation_result_view import CalculationResultView

logger = get_logger()

# ---------------------------------------------------------------------------
# Default delayed reads — same as EPICS default_delayed_reads
# These are queued after every magnet/PC/clock update and calculated lazily.
# ---------------------------------------------------------------------------
DEFAULT_DELAYED_READS: Sequence[ReadCommand] = (
    ReadCommand("track", "pos"),
    ReadCommand("twiss", "parameters"),
    ReadCommand("tune", "transversal"),
    ReadCommand("chromaticity", "transversal"),
)


# ---------------------------------------------------------------------------
# consume() — same pattern as EPICS, no double-delay
# ---------------------------------------------------------------------------

async def consume(queue: asyncio.Queue, delay: float) -> Sequence[ReadCommand]:
    """Drain the queue, waiting up to `delay` seconds for the first item."""
    rcmds = []
    while True:
        try:
            rcmd = await asyncio.wait_for(queue.get(), timeout=delay)
        except asyncio.TimeoutError:
            break
        rcmds.append(rcmd)
        queue.task_done()
    return rcmds


# ---------------------------------------------------------------------------
# TangoController
# ---------------------------------------------------------------------------

class TangoController(ControllerInterface):
    """
    Orchestrates backend updates and view pushes for the TANGO server.

    Parallel to the EPICS Controller in custom_epics/ioc/server.py.
    Owns:
      - mexec  : TranslatingCommandExecutionEngine (shared across Tango processes
                 via the SyncMexecProxy in server_manager.py)
      - view   : TangoView (pushes results to virtual Tango devices)
      - queue  : asyncio.Queue for delayed reads (twiss, orbit, tune)

    Lifecycle
    ---------
    Call start() once after the asyncio event loop is running.
    The delayed execution task runs forever in the background.
    """

    def __init__(
        self,
        *,
        controller_delegate: ControllerInterface,
        name: str,
        # mexec: TranslatingCommandExecutionEngine,
        # prefix: str,
        # default_delayed_reads: Sequence[ReadCommand] = DEFAULT_DELAYED_READS,
        sync_reset=None,
    ):
        self.delegate = controller_delegate
        self.name = name

        # a missing link to get running again ?
        self.mexec = self.delegate.mexec
        self._sync_reset = sync_reset  # callable: reloads lattice + clears error state

        self.cmd_queue: asyncio.Queue = None  # created in start() on running loop
        self._pending_task = None

    def reset(self) -> None:
        """
        Reset backend to nominal state and trigger fresh calculations.
        Called from TwissOrbitDevice.Reset command.

        NOTE: Do NOT call push_invalid() here — Reset runs inside the
        TwissOrbitDevice Tango thread which holds the serialization monitor.
        push_invalid() tries to call command_inout on TwissOrbitDevice via
        DeviceProxy → deadlock → 10s timeout → sync_reset never reached.
        The fresh calculation queued at the end will overwrite stale values.
        """
        if self._sync_reset is None:
            raise RuntimeError("TangoController: no sync_reset callable registered")
        logger.warning("TangoController.reset: resetting backend to nominal state...")

        from dt4acc.core.bl.shared_event_loop import get_shared_event_loop
        shared_loop = get_shared_event_loop()

        # Reload lattice + clear error state
        self._sync_reset()

        # Queue fresh full calculation
        asyncio.run_coroutine_threadsafe(
            # Todo: solve this dependency
            self.delegate._enqueue(list(self.delegate.default_delayed_reads)), shared_loop
        ).result(timeout=10)

        # Refresh all MagnetDevice local attributes from the reloaded lattice
        self._refresh_all_magnet_devices()

        logger.warning("TangoController.reset: done — recalculation queued")

    def _refresh_all_magnet_devices(self) -> None:
        """
        Refresh all MagnetDevice local attributes from the reloaded lattice.
        Bulk cache refresh (3 cross-process calls) then RefreshFromCache per device.
        """
        try:
            from dt4acc.custom_tango.ioc.single_server import (
                refresh_cache_from_lattice, _my_magnet_uuids
            )
            from dt4acc.custom_tango.ioc.server_manager import _connect_to_mexec_service
            sync_proxy, _ = _connect_to_mexec_service()
            refresh_cache_from_lattice(sync_proxy, _my_magnet_uuids)

            from tango import Database, DeviceProxy
            db = Database()
            dev_list = db.get_device_exported_for_class("MagnetDevice")
            count = 0
            for dev_name in dev_list.value_string:
                try:
                    dp = DeviceProxy(str(dev_name))
                    dp.set_timeout_millis(1000)
                    dp.command_inout("RefreshFromCache")
                    count += 1
                except Exception as exc:
                    logger.debug("RefreshFromCache failed for %s: %s", dev_name, exc)
            logger.warning("TangoController.reset: RefreshFromCache sent to %d magnets", count)
        except Exception as exc:
            logger.warning("TangoController.reset: could not refresh magnets: %s", exc)

    def start(self):
        return self.delegate.start()

    async def update(self, cmd: Command, reads: Sequence[ReadCommand], delayed_reads: Sequence[ReadCommand]):
        return await self.delegate.update(cmd=cmd, reads=reads, delayed_reads=delayed_reads)

    async def trigger_read(self, reads: Sequence[ReadCommand]) -> ReadTogether:
        return await self.delegate.trigger_read(reads=reads)

    async def enqueue(self, reads: Sequence[ReadCommand]) -> None:
        """

        Todo:
            provide a public method for it and add it to the controller
            interface
        """
        return await self.delegate.enqueue(reads)

    def get_default_delayed_reads(self) -> Sequence[ReadCommand]:
        return self.delegate.get_default_delayed_reads()

    # def start(self) -> None:
    #     """Start the delayed execution loop on the shared event loop."""
    #     assert self._pending_task is None, "TangoController.start() called twice"
    #     from dt4acc.core.bl.shared_event_loop import get_shared_event_loop
    #     shared_loop = get_shared_event_loop()
    #
    #     # Always use the shared loop — it's the one we control and is
    #     # guaranteed to be running. Tango's own loop is not reliable here.
    #     async def _create_queue_and_start():
    #         self.cmd_queue = asyncio.Queue()
    #
    #     asyncio.run_coroutine_threadsafe(_create_queue_and_start(), shared_loop).result(timeout=5)
    #
    #     fut = asyncio.run_coroutine_threadsafe(self._queue_loop(), shared_loop)
    #     self._pending_task = fut
    #     logger.info("TangoController delayed execution task started on shared loop")
    #
    # async def update(
    #     self,
    #     *,
    #     cmd: Command,
    #     reads: Sequence[ReadCommand],
    #     delayed_reads: Sequence[ReadCommand] = (),
    # ) -> None:
    #     """
    #     Apply a command to the backend, push immediate reads to the view,
    #     then queue delayed reads (twiss, orbit, tune).
    #
    #     Called from Tango device write handlers via _async().
    #     """
    #     # 1. Mutate the backend lattice
    #     await self.mexec.set([cmd])
    #
    #     # 2. Immediate reads — e.g. readback current after setting a magnet
    #     if reads:
    #         read_result = await self.mexec.trigger_read(reads)
    #         for rcmd, translated in zip(reads, read_result.data):
    #             await self.view.dispatch(rcmd, translated)
    #
    #     # 3. Queue delayed reads
    #     all_delayed = list(self.default_delayed_reads) + list(delayed_reads)
    #     await self._enqueue(all_delayed)
    #
    # async def trigger_read(self, reads: Sequence[ReadCommand]) -> ReadTogetherAndTranslated:
    #     """Direct read from the backend — used for initial value peek at startup."""
    #     return await self.mexec.trigger_read(reads)
    #
    # async def _push_invalid(self) -> None:
    #     """
    #     Push NaN arrays to all virtual devices when backend calculation fails.
    #     This signals to clients that the data is invalid (beam lost).
    #     """
    #     try:
    #         await self.view.push_invalid()
    #     except Exception as exc:
    #         logger.error("TangoController: failed to push invalid state: %s", exc)
    #
    # async def _enqueue(self, reads: Sequence[ReadCommand]) -> None:
    #     if self.cmd_queue is None:
    #         logger.debug("TangoController: queue not yet started — delayed reads dropped")
    #         return
    #     try:
    #         await asyncio.wait_for(
    #             asyncio.gather(*[self.cmd_queue.put(r) for r in reads]),
    #             timeout=0.1,
    #         )
    #     except asyncio.TimeoutError:
    #         logger.warning("TangoController: queue put timed out — delayed reads dropped")
    #
    # async def _queue_loop(self) -> None:
    #     for step in itertools.count():
    #         logger.debug("TangoController queue loop step %d", step)
    #         await self._queue_step()
    #
    # async def _queue_step(self) -> None:
    #     rcmds = await consume(queue=self.cmd_queue, delay=0.05)
    #     if not rcmds:
    #         return
    #
    #     t_rcmds = tuple(set(rcmds))
    #     logger.debug("TangoController: executing delayed reads %s", t_rcmds)
    #
    #     try:
    #         read_result = await self.mexec.trigger_read(t_rcmds)
    #     except Exception as exc:
    #         logger.error("TangoController: backend read failed for %s: %s", t_rcmds, exc)
    #         traceback.print_exc()
    #         # Push NaN to all virtual devices so clients know data is invalid
    #         await self._push_invalid()
    #         return   # never kill the loop
    #
    #     if len(read_result.data) != len(t_rcmds):
    #         logger.error(
    #             "TangoController: sent %d read commands, got %d results — skipping",
    #             len(t_rcmds), len(read_result.data),
    #         )
    #         await self._push_invalid()
    #         return
    #
    #     for rcmd, translated in zip(t_rcmds, read_result.data):
    #         try:
    #             await self.view.dispatch(rcmd, translated)
    #         except Exception as exc:
    #             logger.error(
    #                 "TangoController: view dispatch failed for %s: %s", rcmd, exc
    #             )
    #             traceback.print_exc()
                # continue processing remaining results