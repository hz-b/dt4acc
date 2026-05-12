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

from dt4acc_lib.interfaces.utils.command_execution_engine import CommandExecutionEngine
from dt4acc_lib.model.output.result import TranslatedReading, ReadTogetherAndTranslated
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
# TangoView — dispatches TranslatedReading results to CalculationResultView
# ---------------------------------------------------------------------------

class TangoView:
    """
    Receives calculation results from the new backend (dt4acc_lib types) and
    adapts them into what CalculationResultView expects (old model types),
    then calls the appropriate push method.

    Backend types → CalculationResultView interface:

        ReadCommand("track", "pos")         → CalculatedTrack
          CalculatedTrack.track             = list[CalculatedPosition(.name, .x, .y)]
          CalculationResultView.push_orbit  expects .x, .y, .names (flat arrays)
          → _OrbitAdapter bridges this

        ReadCommand("twiss", "parameters")  → Twiss
          Twiss.twiss                       = list[TwissAtPosition(.name, .x, .y)]
          TwissAtPosition.x/y               = TwissParameters(.beta, .alpha, .nu)
          CalculationResultView.push_twiss  expects .x.alpha, .x.beta, .x.nu (flat arrays)
          → _TwissAdapter bridges this

        ReadCommand("tune", "x"/"y")        → Tune(.x, .y)
          TuneDevice attributes: .hor, .vert (plain floats written via DeviceProxy)
          CalculationResultView has no push_tune — we push directly
    """

    def __init__(self, *, prefix: str):
        self._calc_view = CalculationResultView(prefix=prefix)
        self._prefix = prefix

    async def dispatch(self, rcmd: ReadCommand, result: TranslatedReading) -> None:
        """Route a single translated reading to the appropriate push method."""
        try:
            if rcmd.id == "track" and rcmd.property == "pos":
                await self._push_orbit(result)
            elif rcmd.id == "twiss":
                await self._push_twiss(result)
            elif rcmd.id == "tune":
                await self._push_tune(result)
            elif rcmd.id == "chromaticity":
                await self._push_chromaticity(result)
            else:
                logger.debug("TangoView: no handler for %s — skipping", rcmd)
        except Exception as exc:
            logger.error("TangoView.dispatch failed for %s: %s", rcmd, exc)

    async def _push_orbit(self, result: TranslatedReading) -> None:
        (reading,) = result.readings
        track = reading.payload          # CalculatedTrack from new backend
        await self._calc_view.push_orbit(_OrbitAdapter(track))

    async def _push_twiss(self, result: TranslatedReading) -> None:
        (reading,) = result.readings
        twiss = reading.payload          # Twiss from new backend
        await self._calc_view.push_twiss(_TwissAdapter(twiss))

    async def _push_tune(self, result: TranslatedReading) -> None:
        (reading,) = result.readings
        tune = reading.payload
        await self._calc_view.push_tune(tune)

    async def _push_chromaticity(self, result: TranslatedReading) -> None:
        (reading,) = result.readings
        chroma = reading.payload           # Tune(.x, .y) reused for xi_x, xi_y
        await self._calc_view.push_chromaticity(chroma)

    async def push_invalid(self) -> None:
        """
        Push NaN arrays to all virtual devices — called when beam is lost
        so clients can detect invalid/stale data rather than seeing old values.
        """
        await self._calc_view.push_invalid()




class _OrbitAdapter:
    __slots__ = ("x", "y", "names", "x0", "found")

    def __init__(self, track):
        self.x     = [p.x    for p in track.track]
        self.y     = [p.y    for p in track.track]
        self.names = [p.name for p in track.track]
        self.x0    = []
        self.found = True


# ---------------------------------------------------------------------------
# Adapter: Twiss (new) → TwissWithAggregatedKValues-compatible (old)
#
# CalculationResultView.push_twiss expects:
#   twiss_result.x.alpha  : array-like
#   twiss_result.x.beta   : array-like
#   twiss_result.x.nu     : array-like
#   twiss_result.y.alpha  : array-like
#   twiss_result.y.beta   : array-like
#   twiss_result.y.nu     : array-like
#   (tune is derived separately — not needed here)
#
# Twiss (new backend) has:
#   twiss: list[TwissAtPosition(name, x=TwissParameters(beta,alpha,nu),
#                                    y=TwissParameters(beta,alpha,nu))]
# ---------------------------------------------------------------------------

class _PlaneAdapter:
    """Presents per-plane arrays from a list of TwissAtPosition."""
    __slots__ = ("alpha", "beta", "nu")

    def __init__(self, positions, plane: str):
        self.alpha = [getattr(p, plane).alpha for p in positions]
        self.beta  = [getattr(p, plane).beta  for p in positions]
        self.nu    = [getattr(p, plane).nu    for p in positions]


class _TwissAdapter:
    __slots__ = ("x", "y")

    def __init__(self, twiss):
        positions = twiss.twiss          # list[TwissAtPosition]
        self.x = _PlaneAdapter(positions, "x")
        self.y = _PlaneAdapter(positions, "y")



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

class TangoController:
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
        mexec: TranslatingCommandExecutionEngine,
        prefix: str,
        default_delayed_reads: Sequence[ReadCommand] = DEFAULT_DELAYED_READS,
        sync_reset=None,
    ):
        self.mexec = mexec
        self.view = TangoView(prefix=prefix)
        self.default_delayed_reads = tuple(default_delayed_reads)
        self._sync_reset = sync_reset  # callable: reloads lattice + clears error state

        self.cmd_queue: asyncio.Queue = None  # created in start() on running loop
        self._pending_task = None
        self._task_counter = itertools.count()

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

        from dt4acc.custom_tango.ioc.devices.shared_event_loop import get_shared_event_loop
        shared_loop = get_shared_event_loop()

        # Reload lattice + clear error state
        self._sync_reset()

        # Queue fresh full calculation
        asyncio.run_coroutine_threadsafe(
            self._enqueue(list(self.default_delayed_reads)), shared_loop
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

    def start(self) -> None:
        """Start the delayed execution loop on the shared event loop."""
        assert self._pending_task is None, "TangoController.start() called twice"
        from dt4acc.custom_tango.ioc.devices.shared_event_loop import get_shared_event_loop
        shared_loop = get_shared_event_loop()

        # Always use the shared loop — it's the one we control and is
        # guaranteed to be running. Tango's own loop is not reliable here.
        async def _create_queue_and_start():
            self.cmd_queue = asyncio.Queue()

        asyncio.run_coroutine_threadsafe(_create_queue_and_start(), shared_loop).result(timeout=5)

        fut = asyncio.run_coroutine_threadsafe(self._queue_loop(), shared_loop)
        self._pending_task = fut
        logger.info("TangoController delayed execution task started on shared loop")

    async def update(
        self,
        *,
        cmd: Command,
        reads: Sequence[ReadCommand],
        delayed_reads: Sequence[ReadCommand] = (),
    ) -> None:
        """
        Apply a command to the backend, push immediate reads to the view,
        then queue delayed reads (twiss, orbit, tune).

        Called from Tango device write handlers via _async().
        """
        # 1. Mutate the backend lattice
        await self.mexec.set([cmd])

        # 2. Immediate reads — e.g. readback current after setting a magnet
        if reads:
            read_result = await self.mexec.trigger_read(reads)
            for rcmd, translated in zip(reads, read_result.data):
                await self.view.dispatch(rcmd, translated)

        # 3. Queue delayed reads
        all_delayed = list(self.default_delayed_reads) + list(delayed_reads)
        await self._enqueue(all_delayed)

    async def trigger_read(self, reads: Sequence[ReadCommand]) -> ReadTogetherAndTranslated:
        """Direct read from the backend — used for initial value peek at startup."""
        return await self.mexec.trigger_read(reads)

    async def _push_invalid(self) -> None:
        """
        Push NaN arrays to all virtual devices when backend calculation fails.
        This signals to clients that the data is invalid (beam lost).
        """
        try:
            await self.view.push_invalid()
        except Exception as exc:
            logger.error("TangoController: failed to push invalid state: %s", exc)

    async def _enqueue(self, reads: Sequence[ReadCommand]) -> None:
        if self.cmd_queue is None:
            logger.debug("TangoController: queue not yet started — delayed reads dropped")
            return
        try:
            await asyncio.wait_for(
                asyncio.gather(*[self.cmd_queue.put(r) for r in reads]),
                timeout=0.1,
            )
        except asyncio.TimeoutError:
            logger.warning("TangoController: queue put timed out — delayed reads dropped")

    async def _queue_loop(self) -> None:
        for step in itertools.count():
            logger.debug("TangoController queue loop step %d", step)
            await self._queue_step()

    async def _queue_step(self) -> None:
        rcmds = await consume(queue=self.cmd_queue, delay=0.05)
        if not rcmds:
            return

        t_rcmds = tuple(set(rcmds))
        logger.debug("TangoController: executing delayed reads %s", t_rcmds)

        try:
            read_result = await self.mexec.trigger_read(t_rcmds)
        except Exception as exc:
            logger.error("TangoController: backend read failed for %s: %s", t_rcmds, exc)
            traceback.print_exc()
            # Push NaN to all virtual devices so clients know data is invalid
            await self._push_invalid()
            return   # never kill the loop

        if len(read_result.data) != len(t_rcmds):
            logger.error(
                "TangoController: sent %d read commands, got %d results — skipping",
                len(t_rcmds), len(read_result.data),
            )
            await self._push_invalid()
            return

        for rcmd, translated in zip(t_rcmds, read_result.data):
            try:
                await self.view.dispatch(rcmd, translated)
            except Exception as exc:
                logger.error(
                    "TangoController: view dispatch failed for %s: %s", rcmd, exc
                )
                traceback.print_exc()
                # continue processing remaining results