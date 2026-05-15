import asyncio
from typing import Sequence

from dt4acc.core.utils.logger import get_logger
from dt4acc_lib.interfaces.utils.command_execution_engine import CommandExecutionEngine
from dt4acc_lib.model.utils.command import Command, BehaviourOnError, ReadCommand

logger = get_logger()


class SyncMexecProxy:
    """Synchronous wrapper around mexec for crossing the process boundary."""

    def __init__(self,*, mexec: CommandExecutionEngine, service_loop: asyncio.AbstractServer):
        self.mexec = mexec
        self.service_loop = service_loop

    def sync_set(self, cmd_id: str, cmd_property: str, value: float):
        cmd = Command(
            id=cmd_id,
            property=cmd_property,
            value=value,
            behaviour_on_error=BehaviourOnError.stop,
        )
        fut = asyncio.run_coroutine_threadsafe(
            self.mexec.set([cmd]), self.service_loop
        )
        return fut.result(timeout=30)

    def sync_peek(self, element_id: str, prop: str) -> float:
        """Read a single element property directly from AT backend,
        bypassing liaison and translator. Used by MultipoleDevice polling
        to stay in sync with PC writes in device view.
        element_id is a FamName uuid (e.g. 'sqfi73'), prop is the AT
        property name (e.g. 'main_strength').
        """
        logger.debug("sync_peek: element_id=%r prop=%r", element_id, prop)

        async def _peek():
            return await self.mexec.backend.read(element_id, prop)

        fut = asyncio.run_coroutine_threadsafe(_peek(), self.service_loop)
        try:
            result = float(fut.result(timeout=5))
            logger.debug("sync_peek: element_id=%r -> %.6f", element_id, result)
            return result
        except Exception as exc:
            if prop == "main_strength" and element_id.startswith("B"):
                # Todo: delete this swith
                # logger.info("sync_peek failed for element_id=%r prop=%r: %s",
                #                element_id, prop, exc)
                return 0.0
                # return math.nan

            tmp = traceback.format_exception(type(exc), exc, exc.__traceback__)  #: delete me
            logger.warning("sync_peek failed for element_id=%r prop=%r: %s",
                           element_id, prop, exc)
            # Todo: No value was retrieved: better return an invalid value
            # return math.nan
            return 0.0

    def sync_trigger_read(self, rcmd_ids: Sequence[str], rcmd_properties: Sequence[str]):
        rcmds = [
            ReadCommand(id=i, property=p)
            for i, p in zip(rcmd_ids, rcmd_properties)
        ]
        fut = asyncio.run_coroutine_threadsafe(
            self.mexec.trigger_read(rcmds), self.service_loop
        )
        result = fut.result(timeout=30)
        out = []
        for translated in result.data:
            for reading in translated.readings:
                out.append((translated.cmd.id, translated.cmd.property, reading.payload))
        return out

    def sync_reset(self):
        """
        Reset backend to nominal state:
        1. Reload AT lattice from .m file
        2. Clear error state → pending
        3. Clear stored optics
        """
        import at
        logger.warning("SyncMexecProxy.sync_reset: reloading lattice from file...")
        try:
            new_acc = _load_lattice(LATTICE_FILE)
            self.mexec.backend.acc.acc = new_acc
            with self.mexec.backend.calculation_lock:
                if self.mexec.backend.model.is_error():
                    self.mexec.backend.model.clear()
                elif not self.mexec.backend.model.is_pending():
                    self.mexec.backend.model.changed()
                self.mexec.backend.optics = None
                self.mexec.backend.elem_names = None
            logger.warning("SyncMexecProxy.sync_reset: lattice reloaded, state=pending")
        except Exception as exc:
            logger.error("SyncMexecProxy.sync_reset failed: %s", exc)
            raise
