from typing import Optional, Dict

from softioc import pythonSoftIoc

from dt4acc.core.interfaces.view_interface import ViewInterface
from dt4acc.core.utils.logger import get_logger
from dt4acc_lib.model.output.result import TranslatedReading
from .orbit_pva import OrbitTwinServer
from dt4acc_lib.model.utils.command import ReadCommand

logger = get_logger()


class View(ViewInterface):
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

    async def push_invalid(self) -> None:
        raise NotImplementedError("push_invalid needs to be implemented or epics view")

    async def dispatch(self, var: ReadCommand, pkg):
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
