from pathlib import Path

import gtpsa
import thor_scsi.lib as tslib
from thor_scsi.factory import accelerator_from_config

from ..accelerators.accelerator_impl import AcceleratorImpl
from ..calculator.thor_scsi_calculator import ThorScsiTwissCalculator, ThorScsiOrbitCalculator
from ..device_interface.bpm_mimikry import BPMMimikry
from ..model.orbit import Orbit
from ..view.calculation_result_view import ResultView

t_dir = Path(__file__).resolve().parent.parent
lattice_filename_default = f"{t_dir}/resources/b2_stduser_beamports_blm_tracy_corr.lat"
acc = accelerator_from_config(lattice_filename_default)
named_index_d = dict(x=0, px=1, y=2, py=3, delta=4, ct=5)
named_index = gtpsa.IndexMapping(named_index_d)

# Create an instance of AcceleratorImpl for Thor_scsi engine
thor_scsi_accelerator = AcceleratorImpl(acc, ThorScsiTwissCalculator(tslib.ConfigType(), named_index, acc),
                                        ThorScsiOrbitCalculator(tslib.ConfigType(), named_index, acc))

view = ResultView(prefix="WS")
bpm_names = [elem.name for elem in thor_scsi_accelerator.acc if "bpm" in elem.name]
bpm = BPMMimikry(prefix="WS", bpm_names=bpm_names)
thor_scsi_accelerator.on_new_orbit.append(view.push_orbit)


def cb(orbit_data: Orbit):
    reduced_data = bpm.pyat_orbit_data_to_model(orbit_data)
    view.push_bpms(reduced_data)


thor_scsi_accelerator.on_new_orbit.append(cb)
thor_scsi_accelerator.on_new_twiss.append(view.push_twiss)


def set_accelerator():
    return thor_scsi_accelerator
