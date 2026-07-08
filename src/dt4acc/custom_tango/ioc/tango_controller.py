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
from typing import Sequence

from dt4acc.core.interfaces.controller_interface import ControllerInterface
from dt4acc_lib.model.output.result import ReadTogether
from dt4acc_lib.model.utils.command import ReadCommand, Command
from dt4acc.core.bl.shared_event_loop import get_shared_event_loop
from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_tango.ioc.mexec_server_for_physics_engine import _connect_to_mexec_service

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
        sync_reinit=None,
    ):
        self.delegate = controller_delegate
        self.name = name

        # a missing link to get running again ?
        self.mexec = self.delegate.mexec
        self._sync_reset = sync_reset  # callable: clears error state
        self._sync_reinit = sync_reinit  # callable: reloads lattice + clears error state

        self.cmd_queue: asyncio.Queue = None  # created in start() on running loop
        self._pending_task = None

    def get_backend_state(self):
        return self.mexec.get_state()

    def reinit(self) -> None:
        if self._sync_reinit is None:
            raise RuntimeError("TangoController: no sync_reinit callable registered")
        logger.warning("TangoController.reinit: reinitialising backend to nominal state...")

        shared_loop = get_shared_event_loop()

        # Reload lattice + clear error state
        self._sync_reinit()

        # Queue fresh full calculation
        asyncio.run_coroutine_threadsafe(
            self.delegate.reread_default_readings(),
            shared_loop
        ).result(timeout=10)

        # Refresh all MagnetDevice local attributes from the reloaded lattice
        self._refresh_all_magnet_devices()

        logger.warning("TangoController.reinit: done — recalculation queued")

    def acknowledge(self) -> None:
        logger.warning("TangoController.acknowledge: acknowledge that calculation engine in error state ...")

        shared_loop = get_shared_event_loop()

        # Todo: need to fix whne to call async and when to call sync
        self.mexec._proxy.sync_acknowledge()
        # asyncio.run_coroutine_threadsafe(
        #     self.delegate.backend.acknowledge(),
        #     shared_loop
        # ).result(timeout=10)

        # Refresh all MagnetDevice local attributes from the reloaded lattice
        self._refresh_all_magnet_devices()

        logger.warning("TangoController.reset: done — recalculation queued")

    def reset(self) -> None:
        """
        Clear backend error state and trigger fresh calculations on the current lattice.
        Called from TwissOrbitDevice.Reset command.

        NOTE: Do NOT call push_invalid() here — Reset runs inside the
        TwissOrbitDevice Tango thread which holds the serialization monitor.
        push_invalid() tries to call command_inout on TwissOrbitDevice via
        DeviceProxy → deadlock → 10s timeout → sync_reset never reached.
        The fresh calculation queued at the end will overwrite stale values.
        """
        if self._sync_reset is None:
            raise RuntimeError("TangoController: no sync_reset callable registered")
        logger.warning("TangoController.reset: clearing backend state...")

        shared_loop = get_shared_event_loop()

        # Clear error state
        self._sync_reset()

        # Queue fresh full calculation
        asyncio.run_coroutine_threadsafe(
            self.delegate.reread_default_readings(),
            shared_loop
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
                refresh_cache_from_lattice, _my_magnet_uuids, _uuid_to_prop
            )
            sync_proxy, _, _ = _connect_to_mexec_service()
            refresh_cache_from_lattice(sync_proxy, _my_magnet_uuids, _uuid_to_prop)

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

    async def reread_default_readings(self) -> None:
        """

        Todo:
            provide a public method for it and add it to the controller
            interface
        """
        return await self.delegate.reread_default_readings()