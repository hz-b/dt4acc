import math
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
        raise NotImplementedError("push_invalid needs to be implemented for epics view")

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
            logger.warning("Tune not handled explicitly any more, but as part of twiss")
            return True
        elif var.id == "twiss":
            self.update_twiss(var, value)
            self.update_tune(var, value)
            return True
        elif var.id == "track":
            self.update_track(var, value)
            return True
        elif var.id == "survey":
            self.update_survey(var, value)
            return True
        return False

    def update_track(self, var: ReadCommand, pkg):
        assert var.id == "track", f"Only prepared to process 'track' but got {var}"
        (single_reading,) = pkg.readings
        value = single_reading.payload

        if var.property == "pos":
            x_vals = [pos.x for pos in value.track]
            y_vals = [pos.y for pos in value.track]
            names = [pos.fam_name for pos in value.track]
            uids = [pos.uid for pos in value.track]

            rw_x = self.process_variables.get(ReadCommand(id="beam", property="x"))
            rw_y = self.process_variables.get(ReadCommand(id="beam", property="y"))
            assert rw_x is not None
            assert rw_y is not None
            rw_x.set(x_vals)
            rw_y.set(y_vals)

            rw_names = self.process_variables.get(
                ReadCommand(id="beam", property="names")
            )
            if rw_names is not None:
                rw_names.set(names)

            rw_uids = self.process_variables.get(
                ReadCommand(id="beam", property="uids")
            )
            if rw_uids is not None:
                rw_uids.set(uids)

            rw_found = self.process_variables.get(
                ReadCommand(id="beam", property="found")
            )
            if rw_found is not None:
                rw_found.set(True)

            # PVA NTTable
            if self.orbit_server is not None:
                try:
                    # BPM readings are in nanometer
                    self.orbit_server.push(
                        x=[v * 1e9 for v in x_vals],
                        y=[v * 1e9 for v in y_vals],
                    names=names
                    )
                except Exception as exc:
                    logger.error("OrbitTwinServer.push failed: %s", exc)
        else:
            raise AssertionError(f"Don't know track property {var.property}")

    def update_tune(self, var: ReadCommand, pkg):
        assert (
            var.id == "twiss"
        ), f"Only prepared to extract tune from 'twiss' but got {var}"
        (single_reading,) = pkg.readings
        value = single_reading.payload
        for plane in ("x", "y"):
            twiss_data_of_last_element = getattr(value.twiss[-1], plane)
            # Hard coded dependency for AT: returns phase advance times 2pi
            flq = twiss_data_of_last_element.nu / (2 * math.pi)
            rec = self.process_variables[
                ReadCommand(id="tune", property=f"flq_{plane}")
            ]
            rec.set(flq)

            mc_rec = self.process_variables.get(ReadCommand("master_clock", "freq"))
            # Todo: need to read the correct values e.g. from a variable
            n_buckets_rec = self.process_variables.get(
                ReadCommand("ring", "n_rf_buckets")
            )
            assert n_buckets_rec is not None
            n_buckets = n_buckets_rec.get()
            # todo: is this calculation in bact_math_utils ...
            #       then copy it together with tests
            #       further watch out ...
            #       some can do the whole integer fraction
            flq_frac = flq % 1.0
            rev_freq = mc_rec.get() / n_buckets
            tune_freq = flq_frac * rev_freq
            # Todo: need to readress where the scale should go
            #       perhaps tune should be handled over virtual devices
            tune_freq = tune_freq / 1000.0
            rec = self.process_variables[ReadCommand(id="tune", property=f"{plane}")]
            rec.set(tune_freq)
            logger.debug(f"Updated Tune for plane {plane}")
            pass


    def update_twiss(self, var: ReadCommand, pkg):
        """
        Todo:
            export uids too
        """
        assert var.id == "twiss", f"Only prepared to process 'twiss' but got {var}"

        (single_reading,) = pkg.readings
        value = single_reading.payload
        for plane in ("x", "y"):

            rw = self.process_variables.get(ReadCommand("twiss", f"{plane}:nu"))
            assert rw is not None
            rw.set([getattr(pos, plane).nu / (2 * math.pi) for pos in value.twiss])

            for param in ("beta", "alpha"):
                rw = self.process_variables.get(
                    ReadCommand("twiss", f"{plane}:{param}")
                )
                assert rw is not None
                rw.set([getattr(getattr(pos, plane), param) for pos in value.twiss])

        rw_names = self.process_variables.get(ReadCommand("twiss", "names"))
        assert rw_names is not None
        rw_names.set([pos.fam_name for pos in value.twiss])

        rw_names = self.process_variables.get(ReadCommand("twiss", "uids"))
        assert rw_names is not None
        rw_names.set([pos.uid for pos in value.twiss])

        pi2 = 2 * math.pi

        if self.orbit_server is not None:
            rec_s = self.process_variables.get(ReadCommand("survey", "s"))
            s_pos = rec_s.get()

            try:
                self.orbit_server.push_model_data(
                    bpm_names=[pos.fam_name for pos in value.twiss],
                    beta_hor=[pos.x.beta for pos in value.twiss],
                    beta_vert=[pos.y.beta for pos in value.twiss],
                    phase_advance_hor=[pos.x.nu / (pi2) for pos in value.twiss],
                    phase_advance_vert=[pos.y.nu / (pi2) for pos in value.twiss],
                    s_pos=s_pos,
                )
            except Exception as exc:
                logger.error("OrbitTwinServer.push failed: %s", exc)
