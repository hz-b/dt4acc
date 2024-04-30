import logging
import threading

from ..accelerators.accelerator_impl import AcceleratorImpl
from ..accelerators.proxy_factory import PyATProxyFactory
from ..calculator.pyat_calculator import PyAtTwissCalculator, PyAtOrbitCalculator
from ..device_interface.bpm_mimikry import BPMMimikry
from ..model.orbit import Orbit
from ..resources.bessy2_sr_reflat import bessy2Lattice
from ..view.calculation_result_view import ResultView, ElementParameterView

calculation_lock = threading.Lock()


def set_pyat_ring():
    import at
    from lat2db.tools.factories.pyat import factory
    from pymongo import MongoClient

    return bessy2Lattice()
    # get database
    client = MongoClient("mongodb://127.0.0.1:27017/")
    db = client["bessyii"]
    collection = db["machines"]
    lattice_in_json_format = collection.find_one()
    # if there is no record in db, this means the lat2db project is not yet used.
    # todo: if someone does not have mongo installed at all?
    #   * maybe he should install and start mongo before getting to this point
    #   * remove the below two lines
    if lattice_in_json_format is None:
        return bessy2Lattice()
    seq = factory(lattice_in_json_format)

    ring = at.Lattice(seq, name='bessy2', periodicity=1, energy=1.7e9)
    if True:
        # set up of calculation choice
        ring.enable_6d()  # Should 6D be default?
        # Set main cavity phases
        ring.set_cavity_phase(cavpts='CAV*')
    return ring


acc = set_pyat_ring()
prefix = "Pierre:DT"
# set_ring(acc)
accelerator = AcceleratorImpl(acc, PyATProxyFactory(lattice_model=None, at_lattice=acc),
                              PyAtTwissCalculator(acc, calculation_lock), PyAtOrbitCalculator(acc, calculation_lock))
view = ResultView(prefix=prefix + ":beam")
#: todo into a controller to pass prefix as parameter at start ?
elem_par_view = ElementParameterView(prefix=prefix)
bpm_names_pyat = [elem.FamName for elem in accelerator.acc if "BPM" == elem.FamName[:3]]
bpm_pyat = BPMMimikry(prefix=prefix, bpm_names=bpm_names_pyat)
accelerator.on_new_orbit.append(view.push_orbit)
accelerator.on_changed_value.append(elem_par_view.push_value)

logger = logging.getLogger("dt4acc")


def cb(orbit_data: Orbit):
    # Todo: push all orbit data to beam
    bpm_data = bpm_pyat.extract_bpm_data(orbit_data)
    view.push_bpms(bpm_data)


accelerator.on_new_orbit.append(cb)
accelerator.on_new_twiss.append(view.push_twiss)


def set_accelerator():
    return accelerator
