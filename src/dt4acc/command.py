"""

A bit like the controller part of MVC?

"""
import os

import gtpsa
import thor_scsi.lib as tslib
from thor_scsi.factory import accelerator_from_config

from src.dt4acc.accelerators.accelerator_impl import AcceleratorImpl
from src.dt4acc.calculator.thor_scsi_calculator import ThorScsiTwissCalculator, ThorScsiOrbitCalculator
from src.dt4acc.device_interface.bpm_mimikry import BPMMimikry
from src.dt4acc.model.orbit import Orbit
from src.dt4acc.view.calculation_result_view import ResultView

prefix = "Waheedullah"
# Todo: how to get the accelerators here
lattice_filename_default = os.environ["THOR_SCSI_LATTICE"]
acc = accelerator_from_config(lattice_filename_default)
named_index_d = dict(x=0, px=1, y=2, py=3, delta=4, ct=5)
named_index = gtpsa.IndexMapping(named_index_d)

# Create an instance of AcceleratorImpl for Thor_scsi engine
thor_scsi_accelerator = AcceleratorImpl(acc, ThorScsiTwissCalculator(tslib.ConfigType(), named_index, acc),
                                        ThorScsiOrbitCalculator(tslib.ConfigType(), named_index, acc))

view = ResultView(prefix=prefix)
bpm_names = [elem.name for elem in thor_scsi_accelerator.acc if "bpm" in elem.name]
bpm = BPMMimikry(prefix=prefix, bpm_names=bpm_names)
thor_scsi_accelerator.on_new_orbit.append(view.push_orbit)
def cb(orbit_data : Orbit):
    reduced_data = bpm.extract_bpm_data_from_orbit(orbit_data)
    view.push_bpms(reduced_data)
thor_scsi_accelerator.on_new_orbit.append(cb)
thor_scsi_accelerator.on_new_twiss.append(view.push_twiss)


def update(*, element_id, property_name, value=None):
    """
    What to do here:
        find the element
        get the property
        set the value
        see if further processing is required

        Who takes care of the read back
        Is value=None a value user wants to set?
        If so get an other place holder...
    """

    # add context manager for handling exception
    elem_proxy = thor_scsi_accelerator.get_element(element_id)
    elem_proxy.update(property_name, value)
