from src.dt4acc.accelerators.accelerator_impl import AcceleratorImpl
from src.dt4acc.calculator.pyat_calculator import PyAtTwissCalculator, PyAtOrbitCalculator
from src.dt4acc.device_interface.bpm_mimikry import BPMMimikry
from src.dt4acc.model.orbit import Orbit
from src.dt4acc.resources.bessy2_sr_reflat import bessy2Lattice
from src.dt4acc.view.calculation_result_view import ResultView

acc = bessy2Lattice()

pyat_accelerator = AcceleratorImpl(acc, PyAtTwissCalculator(acc), PyAtOrbitCalculator(acc))
view = ResultView(prefix="WS")
bpm_names_pyat = [elem.FamName for elem in pyat_accelerator.acc if "bpm" in elem.FamName]
bpm_pyat = BPMMimikry(prefix="WS", bpm_names=bpm_names_pyat)
pyat_accelerator.on_new_orbit.append(view.push_orbit)


def cb(orbit_data: Orbit):
    reduced_data_pyat = bpm_pyat.extract_bpm_data_from_orbit(orbit_data)
    view.push_bpms(reduced_data_pyat)


pyat_accelerator.on_new_orbit.append(cb)
pyat_accelerator.on_new_twiss.append(view.push_twiss)


def set_accelerator():
    return pyat_accelerator
