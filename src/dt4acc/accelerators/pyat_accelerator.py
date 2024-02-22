from ..accelerators.accelerator_impl import AcceleratorImpl
from ..calculator.pyat_calculator import PyAtTwissCalculator, PyAtOrbitCalculator
from ..device_interface.bpm_mimikry import BPMMimikry
from ..model.orbit import Orbit
from ..resources.bessy2_sr_reflat import bessy2Lattice
from ..view.calculation_result_view import ResultView, ElementParameterView

import threading

calculation_lock = threading.Lock()
acc = bessy2Lattice()
prefix = "Pierre:DT"
accelerator = AcceleratorImpl(acc, PyAtTwissCalculator(acc,calculation_lock), PyAtOrbitCalculator(acc,calculation_lock))
view = ResultView(prefix=prefix +":beam")
#: todo into a controller to pass prefix as parameter at start ?
elem_par_view = ElementParameterView(prefix=prefix)
bpm_names_pyat = [elem.FamName for elem in accelerator.acc if "bpm" in elem.FamName]
bpm_pyat = BPMMimikry(prefix=prefix, bpm_names=bpm_names_pyat)
accelerator.on_new_orbit.append(view.push_orbit)
accelerator.on_changed_value.append(elem_par_view.push_value)


def cb(orbit_data: Orbit):
    reduced_data_pyat = bpm_pyat.extract_bpm_data_from_orbit(orbit_data)
    view.push_bpms(reduced_data_pyat)


accelerator.on_new_orbit.append(cb)
accelerator.on_new_twiss.append(view.push_twiss)


def set_accelerator():
    return accelerator
