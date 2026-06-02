"""

Todo:
    resolve dependency: orbit depends on custom epics
    Should be a separate package
"""
import logging
import os
import re
from collections import defaultdict

from accml.custom.epics.devices.orbit import Orbit
from accml_lib.core.interfaces.utils.devices_facade import DevicesFacade as DevicesFacadeInterface
from accml.core.utils.ophyd_async.multiplexer_for_settable_devices import (
    MultiplexerProxy,
)
from accml.custom.epics.devices.master_clock import MasterClock
from accml.custom.epics.devices.power_converter import PowerConverter
from accml.custom.epics.devices.tunes import Tunes
from dt4acc.custom_facility.als.liaison_translator_setup import load_managers
from dt4acc.custom_facility.als.model import Setpoint

# Todo: clarify with markus if this code will be contributed


logger = logging.getLogger("accml_lib")


match = re.compile(
    "SR(?P<sector>[a-zA-Z0-9]+)"
    "_+"
    "(?P<family>[a-zA-Z0-9]+)"
    "_+"
    "AC(?P<child>[0-9]+)"
)

class DevicesFacade(DevicesFacadeInterface):
    def __init__(self, d):
        self._devices = d

    def get(self, name: str):
        return self._devices.get(name)


def setup(prefix: str=None) -> DevicesFacade:
    """

    **NB** prefix as empty string is a valid str
    """
    # Todo: make it accml_user
    #
    if prefix is None:
        prefix = os.environ.get("USER", "Anonym") + ":"

    logger.info("using prefix=%s", prefix)

    yp, lm, __, epics_device_models = load_managers()

    signals_lut = defaultdict(list)
    for model in epics_device_models:
        signals_lut[model.rcmd].append(model)
    # single object per read command, lookup can be made
    assert not [v for v in signals_lut.values() if len(v) > 1]
    def extract_single_value(values):
        val, = values
        return val
    signals_lut = {k: extract_single_value(v) for k, v in signals_lut.items()}

    # This is a hack for now ... I know that I can match quadrupoles by name
    setpoints = [v for v in signals_lut.values() if isinstance(v, Setpoint)]
    # mml uses monitor, bluesky / ophyd-async readbacks
    # here I follow ophyd-async
    readbacks = [extract_single_value(setp.reads) for setp in setpoints]

    # I need setpoint and redaback pvs
    combined_setp_rdbk_pvs = {setp.pv_name: (setp.pv_name, signals_lut[rdbk].pv_name) for setp, rdbk in zip(setpoints, readbacks)}
    combined_setp_rdbk_pvs

    quad_pcs = (
        [name for name in combined_setp_rdbk_pvs if "QF" in name]
    )

    horizontal_steerer_pc_names = [name for name in combined_setp_rdbk_pvs if "HCM" in name]
    vertical_steerer_pc_names = [name for name in combined_setp_rdbk_pvs if "VCM" in name]
    quad_pc_names = [name for name in combined_setp_rdbk_pvs if "QF" in name or "QD" in name or "QFA" in name or "QDA" in name]


    def create_pc_device(setp_pv_name):
        r = match.match(setp_pv_name)
        if not r:
            assert 0
        d = r.groupdict()
        sector = d["sector"]
        if sector.endswith("C"):
          pass
        elif sector.endswith("U"):
            pass
        else:
            assert 0

        n_sec = int(sector[:-1])
        family = d["family"]
        child = int(d["child"])
        name = f"SR{n_sec:02}C__{family}__{child:02}"
        setpoint, readback = combined_setp_rdbk_pvs[setp_pv_name]
        r = PowerConverter(prefix, name=name, setpoint_suffix=setpoint, readback_suffix=readback)
        return r

    quad_pcs = {pv_name: create_pc_device(pv_name) for pv_name in quad_pc_names}
    # ALS seems not to have one
    # orbit = Orbit(f"{prefix}ORBITCC:", name="orbit")
    quadrupoles = MultiplexerProxy(
        name="quad_col", settable_devices=quad_pcs, default_name=list(quad_pcs)[0]
    )

    steerer_pcs = {pv_name: create_pc_device(pv_name) for pv_name in
                horizontal_steerer_pc_names + vertical_steerer_pc_names
    }

    steerers = MultiplexerProxy(
        name="steerer_col", settable_devices=steerer_pcs, default_name=list(steerer_pcs)[0]
    )


    master_clock = MasterClock(f'{prefix}:master_clock:ref_freq', name="mc")
    tune = Tunes(f"{prefix}TUNEZR", name="tune")

    #: todo: what to do if names can not be made to match easily
    # aux = { "mc-frequency" : master_clock.frequency}
    d = {
        **dict(
            quadrupole_pcs=quadrupoles,
            master_clock=master_clock,
            tune=tune,
            steerer_pcs=steerer_pcs,
            # orbit=orbit
        ),
        **quad_pcs,
        # **aux,
        **steerer_pcs,
    }
    return DevicesFacade(d)


if __name__ == "__main__":
    d = setup()
    d
