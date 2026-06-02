from collections import defaultdict
from typing import Sequence, Union

from dt4acc.custom_facility.als.model import MMLStyleDeviceIdentifier
from dt4acc_lib.interfaces.utils.liaison_manager import LiaisonManagerBase
from dt4acc_lib.model.utils.identifiers import DevicePropertyID


def get_power_converters_from_tune_correction_quads(
        lm: LiaisonManagerBase,
        tune_correction_quads: Sequence[Union[str, MMLStyleDeviceIdentifier]]) -> Sequence:
    """
    Warning:
        This function should not be required: it goes back to inconsistencies
        of the current liaison manager / translation service setup

    Lessons learned from ALS: device names are essential. The view takes care
    where to root each signal to. A power converter should be settable readable
    and so on.
    """
    d = defaultdict(int)
    for quad in tune_correction_quads:
        lat_prop, = lm.inverse(DevicePropertyID(quad, "main_strength"))
        dev_prop, = lm.forward(lat_prop)
        # Here I get the variables back I read from ... now I have to guess how
        # the set commands are called
        if dev_prop.device_name[:-2].endswith("AM"):
            suffix = dev_prop.device_name[-4:].replace("AM", "AC")
            dev_prop = DevicePropertyID(dev_prop.device_name[:-4] + suffix, "set_current")
            # check that it points to a lattice elemet
            assert lm.inverse(dev_prop)
        else:
            assert 0
        d[dev_prop.device_name] += 1

    return list(d.keys())
