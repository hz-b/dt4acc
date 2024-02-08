from collections import UserList

import numpy as np
from at import shift_elem

from ..interfaces.accelerator_interface import AcceleratorInterface
from ..interfaces.element_interface import ElementInterface
from ..model.element_upate import ElementUpdate


class Event(UserList):
    def append(self, item):
        assert (callable(item))
        super().append(item)

    def trigger(self, obj):
        for callback in self:
            callback(obj)


def estimate_shift(element, eps=1e-8):
    """
    Todo: get it upstreamed into pyat
    """
    try:
        down_stream_shift = element.T1
    except AttributeError:
        down_stream_shift = np.zeros([6], np.float)
    try:
        up_stream_shift = element.T2
    except AttributeError:
        up_stream_shift = np.zeros([6], np.float)

    prep = np.array([down_stream_shift, -up_stream_shift])
    shift = prep.mean(axis=0)

    assert (np.absolute(prep.std(axis=0)) < eps).all()
    return shift


class ElementProxy(ElementInterface):
    def __init__(self, obj, *, element_id):
        self._obj = obj
        self.element_id = element_id
        self.on_update_finished = Event()
        self.on_changed_value = Event()

    def update_roll(self, *, roll):
        """
        Todo: implement setting roll

        """
        return
        self._obj.set_tilt(roll)

    def update_shift(self, *, dx=None, dy=None):
        """
        todo: find out if there is a shift

        Push updated value back to sender?
        """

        assert dx is not None or dy is not None

        element, = self._obj

        shift = estimate_shift(element)
        if dx is None:
            dx = shift[0]
        if dy is None:
            dy = shift[1]
        shift_elem(element, dx, dy)

        # look what really happened
        element, = self._obj
        dxr, _, dyr, _, _, _ = estimate_shift(element)
        self.on_changed_value.trigger(
            ElementUpdate(element_id=self._obj.name, property_name="dx", value=dxr)
        )
        self.on_changed_value.trigger(
            ElementUpdate(element_id=self._obj.name, property_name="dy", value=dyr)
        )

    def update(self, property_id: str, value):
        """
        Todo:
            activate update calculations again
        """
        if value is not None:
            assert np.isfinite(value)

        element, = self._obj
        method_name = "set_" + property_id
        if method_name == "set_dx":
            # Todo: check that lattice placement works on the original lattice
            #       and that this is not a copy
            self.update_shift(dx=value)
        elif method_name == "set_dy":
            self.update_shift(dy=value)
        elif method_name == "set_roll":
            self.update_roll(roll=value)
        elif method_name == "set_K":
            # Check that it is a quadrupole
            element.update(K=value)
            self.on_changed_value.trigger(
                ElementUpdate(element_id=self.element_id, property_name="K", value=self._obj[0].K)
            )
        else:
            method = getattr(self._obj, method_name)
            method(value)

        self.on_update_finished.trigger(None)


class AcceleratorImpl(AcceleratorInterface, UserList):
    def __init__(self, acc, twiss_calculator, orbit_calculator):
        super().__init__()
        self.acc = acc
        self.twiss_calculator = twiss_calculator
        self.orbit_calculator = orbit_calculator
        self.twiss = twiss_calculator.calculate()
        self.orbit = orbit_calculator.calculate()

        self.on_new_orbit = Event()
        self.on_new_twiss = Event()
        self.on_changed_value = Event()

    def get_element(self, element_id) -> ElementInterface:
        # TODO: see how the  data is structured  than return the element by id
        sub_lattice = self.acc[element_id]
        # single element expected in sublattice
        _, = sub_lattice
        if sub_lattice:
            proxy = ElementProxy(sub_lattice, element_id=element_id)
            proxy.on_changed_value.append(self.on_changed_value.trigger)

            def cb(unused):
                self.twiss = self.twiss_calculator.calculate()
                self.orbit = self.orbit_calculator.calculate()
                self.on_new_orbit.trigger(self.orbit)
                self.on_new_twiss.trigger(self.twiss)

            proxy.on_update_finished.append(cb)
            return proxy
        else:
            raise ValueError(f"Element with ID {element_id} not found")

    def calculate_twiss(self):
        return self.twiss_calculator.calculate()

    def calculate_orbit(self):
        return self.orbit_calculator.calculate()
