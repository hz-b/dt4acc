import logging
import functools
import numpy as np
import thor_scsi.lib as tslib
from thor_scsi.utils.accelerator import instrument_with_standard_observers
import gtpsa

    # extract_orbit_from_standard_observers,
    # extract_orbit_from_accelerator_with_standard_observers,
# )
from python.calculator import TwissCalculator, OrbitCalculator

logger = logging.getLogger("thor-scsi-lib")

# neeed to find out where to place it
# standard_canonocail_variable_dimensions?
named_index_d = dict(x=0, px=1, y=2, py=3, delta=4, ct=5)
named_index = gtpsa.IndexMapping(named_index_d)

class AcceleratorFacade:
    """
    Facade class for Accelerator object
    """

    def __init__(self, acc):
        self._acc = acc
        self.mapping = named_index
        self.observers = instrument_with_standard_observers(self._acc, mapping=self.mapping)
        self.conf = tslib.ConfigType()
        self.twiss = TwissCalculator(parent=self)
        self.orbit = OrbitCalculator(parent=self)
        self.eps = None

        # just a check if it is not None
        self.acc

    @property
    def acc(self):
        acc = self._acc
        assert(acc is not None)
        return acc

    def get_bpm_data(self):
        """
        Extract orbit offset from BPM objects
        """
        bpms = getBPMs(self._acc)
        def extract_orbit_offset(elem):
            ob = elem.get_observer()
            if not ob:
                return np.array([np.nan, np.nan])

            if ob.has_phase_space():
                a = ob.get_phase_space()
            elif ob.has_truncated_power_series_a():
                a_tpsa = ob.get_truncated_power_series_a().cst()
            else:
                raise ValueError("No observed bpm data")
            return a_tpsa.x, a_tpsa.y
        orbit_offsets = np.array([extract_orbit_offset(bpm) for bpm in bpms])
        names = [bpm.name for bpm in bpms]
        return orbit_offsets, names

    def find_element(self, element_name: str = None, element_index: int = None) -> tslib.ElemType:
        """
        Find accelerator element by name or index
        """
        if not element_name:
            return self._acc[element_index]
        else:
            try:
                r = self._acc.find(element_name, element_index)
            except Exception as exc:
                logger.error(f"Failed to find element {element_name} {element_index}: {exc}")
                raise exc
            return r

    def get_method(self, element, method_name: str):
        """
        Find element method by name
        """
        try:
            method = getattr(element, method_name)
        except Exception as exc:
            logger.error(f"Failed to find method {method_name} on element {element}")
            logger.error(f"element has methods {dir(element)}")
            raise exc
        return method

    def walk_to_method(self, element, method_names):
        """
        Recursively walks to a method of a given element
        """
        method = self.get_method(element=element, method_name=method_names[0])
        if len(method_names) == 1:
            return method
        try:
            child = method()
        except Exception as exc:
            logger.error(f"Failed to execute method {method}")
            raise exc
        return self.walk_to_method(element=child, method_names=method_names[1:])

    def get_property(self, method_names, element_name: str="", element_index: int=-1,  element = None):
        """
        Get property of an element

        todo:
            check if element name or index are ever used
        """
        if not element:
            element = self.find_element(element_name=element_name, element_index=element_index)
        else:
            logger.info(f"Directly using {element} ignoring element:{element_name} with index:{element_index}")
        method = self.walk_to_method(element=element, method_names=method_names)
        return method()

    def set_property(self, element_name: str, element_index: int, method_names, value):
        """
        Set property of an element
        """
        elem = self.find_element(element_name=element_name, element_index=element_index)
        if elem is None:
            raise AssertionError(f"can not find element with name {element_name}")
        method = self.walk_to_method(element=elem, method_names=method_names)
        logger.debug(f"Setting element {elem} using method {method} to value {value}")
        try:
            method(value)
        except Exception as exc:
            logger.error(f"Set element {elem} using method {method} to value {value} failed: {exc}")
        else:
            logger.debug(f"Set element {elem} using method {method} to value {value}")
        return elem

    def calculate_twiss(self):
        """
        Calculate Twiss parameters and return the result.

        TODO: Determine if computed result should be saved.
        """
        result = self.twiss.calculate()
        logger.info("Twiss parameters calculated.")
        return result

    def calculate_orbit(self):
        """
        Calculate the orbit and return the result.

        TODO: Determine if computed result should be saved.
        """
        result = self.orbit.calculate(mapping=named_index)
        return result




@functools.lru_cache(maxsize=1)
def getBPMs(acc):
    """Extract the names of beam position monitors in the accelerator.

    Args:
        acc (Accelerator): The accelerator.

    Returns:
        List: A list of the names of beam position monitors in the accelerator.

    Todo:
        Determine what this function is used for.

    """
    # Find all elements in the accelerator with names starting with "bpm"
    bpms = [element for element in acc if element.name[:3] == "bpm"]

    # Extract the names of the beam position monitors
    bpm_names = [bpm.name for bpm in bpms]

    # Log the names of the beam position monitors being used
    logger.debug(f"Using bpms {bpm_names}")

    return bpms
