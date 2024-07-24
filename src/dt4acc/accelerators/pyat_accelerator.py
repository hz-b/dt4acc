import logging
import threading
import os

from ..accelerators.accelerator_impl import AcceleratorImpl
from ..accelerators.proxy_factory import PyATProxyFactory
from ..calculator.pyat_calculator import PyAtTwissCalculator, PyAtOrbitCalculator
from ..device_interface.bpm_mimikry import BPMMimikry
from ..model.orbit import Orbit
from ..view.calculation_result_view import ResultView, ElementParameterView
calculation_lock = threading.Lock()


def set_pyat_ring():
    from lat2db.model.accelerator import Accelerator
    return Accelerator().ring

acc = set_pyat_ring()
prefix = "Anonym" #os.environ["DT4ACC_PREFIX"]
# set_ring(acc)
accelerator = AcceleratorImpl(acc, PyATProxyFactory(lattice_model=None, at_lattice=acc),
                              PyAtTwissCalculator(acc, calculation_lock), PyAtOrbitCalculator(acc, calculation_lock))
view = ResultView(prefix=prefix + ":beam")
#: todo into a controller to pass prefix as parameter at start ?
elem_par_view = ElementParameterView(prefix=prefix)
bpm_names_pyat = [elem.FamName for elem in accelerator.acc if "BPM" == elem.FamName[:3]]
bpm_pyat = BPMMimikry(prefix=prefix, bpm_names=bpm_names_pyat)
accelerator.on_new_twiss.subscribe(view.push_twiss)
accelerator.on_new_orbit.subscribe(view.push_orbit)
accelerator.on_changed_value.subscribe(elem_par_view.push_value)

logger = logging.getLogger("dt4acc")


async def cb(orbit_data: Orbit):
    # Todo: push all orbit data to beam
    bpm_data = bpm_pyat.extract_bpm_data(orbit_data)
    # await view.push_bpms(bpm_data)


# accelerator.on_new_orbit.subscribe(cb)
# accelerator.on_new_twiss.subscribe(view.push_twiss)


def set_accelerator():
    return accelerator
