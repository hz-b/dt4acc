"""

Todo:
    resolve dependency: orbit depends on custom epics
    Should be a separate package
"""
# import json
import logging
import os
import re
from collections import defaultdict
from itertools import zip_longest
from typing import Sequence

from accml.custom.epics.devices.bpm import BPMTbTPosition
from accml.custom.epics.devices.orbit import Orbit
from accml.custom.epics.devices.turn_by_turn_data_config import TurnByTurnDataConfig
from accml_lib.core.interfaces.utils.devices_facade import DevicesFacade as DevicesFacadeInterface
from accml.core.utils.ophyd_async.multiplexer_for_settable_devices import (
    MultiplexerProxy,
)
from accml.custom.epics.devices.master_clock import MasterClock
from accml.custom.epics.devices.power_converter import PowerConverter
from accml.custom.epics.devices.tunes import Tunes
from dt4acc.core.model.view import Setpoint
from dt4acc.custom_facility.als.gpt.dt4acc_bootstrap import load_managers
from dt4acc.custom_facility.als.model import MMLStyleDeviceIdentifier

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

    def names(self) -> Sequence[str]:
        return tuple(self._devices.keys())


def try_put_bpms_into_nomencalutra(signal_lut):
    """
    I can not derive the BPM's directly from the signal lut
    So I create them manually
    I use signal_lut to see which I should create
    """
    bpm_pv_names = defaultdict(list)
    bpm_tbt_names = defaultdict(list)

    tmp = [v for rcmd, v in signal_lut.items() if isinstance(rcmd.id, MMLStyleDeviceIdentifier) ]
    for rcmd, v in signal_lut.items():
        if isinstance(rcmd.id, MMLStyleDeviceIdentifier) and rcmd.id.family.startswith("BPM"):
            if v.pv_name.endswith(":SA:X") or v.pv_name.endswith(":SA:Y"):
                # Turn by turn BPM's
                bpm_tbt_names[v.pv_name[:-5]].append(v)
            elif "X" in v.pv_name or "Y" in v.pv_name:
                # single value bpms
                bpm_pv_names[v.pv_name].append(v)

    # now lets find which names we have here
    bpm_names = defaultdict(list)
    # combinable bpm pv_names
    bpm_pv_names_ctl = {k: False for k in bpm_pv_names}
    for k, v in bpm_pv_names.items():
        if "X" in k:
            k_for_y = k.replace("X", "Y")
            # need to take out the X
            k_without_coor = k.replace("X", "?")
            bpm_names[k_without_coor].append(k)
            bpm_pv_names_ctl[k] = True
            bpm_pv_names_ctl[k_for_y] = True

        if "Y" in k:
            k_for_x = k.replace("Y", "X")
            k_without_coor = k.replace("Y", "?")
            bpm_names[k_without_coor].append(k)
            bpm_pv_names_ctl[k] = True
            bpm_pv_names_ctl[k_for_x] = True
    assert not {k: v for k, v in bpm_pv_names_ctl.items() if v == False}

    reduced = bpm_names.copy()
    two_dim = {k: v  for k, v in reduced.items() if len(v) == 2}
    for k, v in two_dim.items():
        reduced.pop(k)
    single_dim = {k: v  for k, v in reduced.items() if len(v) == 1}
    for k, v in single_dim.items():
        reduced.pop(k)
    assert not reduced
    return dict(bpm_tbt_names), (two_dim, single_dim)


def setup_bpms(signals_lut, prefix):
    bpms_with_tbt, _ = try_put_bpms_into_nomencalutra(signals_lut)
    # Todo: find out how that could slip here
    #       or why the twin does not create an interface for it
    bpms_with_tbt =  {k: v for k, v in bpms_with_tbt.items() if k != "SR01C:BPM4"}
    # json.dump(dict(bpm_tbt_names=list(bpms_with_tbt)), open("als_bpm_tbt_data.json", "wt"))

    d = {
        k: BPMTbTPosition(f"{prefix}{k}:", name=k)
        for k in bpms_with_tbt.keys()
    }
    return d


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

    def extract_single_rcmd(k, values):
        val, = values
        return val

    signals_lut = {k: extract_single_rcmd(k, v) for k, v in signals_lut.items()}

    tbt_bpms = setup_bpms(signals_lut, prefix)
    # This is a hack for now ... I know that I can match quadrupoles by name
    # **NB**: I assume that there is a least a single read there, otherwise it is ignored
    setpoints = [v for v in signals_lut.values() if isinstance(v, Setpoint) and len(v.reads) > 0]
    # mml uses monitor, bluesky / ophyd-async readbacks
    # here I follow ophyd-async
    readbacks = [extract_single_rcmd(setp.rcmd, setp.reads) for setp in setpoints]
    assert len(setpoints) == len(readbacks)
    # some need to be removed as these readbacks have no signal assigned to them

    # I need setpoint and readback pvs ... but the rdbk do not necessarily have
    # a signal assigned to them
    not_handled = [(setp, rdbk) for setp, rdbk in zip_longest(setpoints, readbacks) if signals_lut.get(rdbk, None) == None]
    for setp, rdbk in not_handled:
        logger.info(
            f"%s.setup Can not handle automatically setpoint pv name {setp.pv_name} with associated {rdbk} as no signal is assigned to this rcmd",
            __name__,
        )

    combined_setp_rdbk_pvs = {
        setp.pv_name: (setp.pv_name, signals_lut[rdbk].pv_name)
        for setp, rdbk in zip_longest(setpoints, readbacks) if signals_lut.get(rdbk, None) != None
    }
    pass

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

    turn_by_turn = TurnByTurnDataConfig(f"{prefix}simulator_ring:turn_by_turn:", name="tbt")
    # need to handle BPMs
    [rcmd for rcmd in list(signals_lut) if isinstance(rcmd, MMLStyleDeviceIdentifier)]

    #: todo: what to do if names can not be made to match easily
    # aux = { "mc-frequency" : master_clock.frequency}
    d = {
        **dict(
            quadrupole_pcs=quadrupoles,
            master_clock=master_clock,
            tune=tune,
            steerer_pcs=steerer_pcs,
            steerer_mux=steerers,
            tbt_bpms=tbt_bpms,
            turn_by_turn=turn_by_turn,
            # orbit=orbit
        ),
        # so that these can be accessed individually
        **tbt_bpms,
        **quad_pcs,
        # **aux,
        **steerer_pcs,
    }
    return DevicesFacade(d)


if __name__ == "__main__":
    d = setup()
    d
