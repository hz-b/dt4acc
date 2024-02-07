from collections import UserList

from ..interfaces.accelerator_interface import AcceleratorInterface
from ..interfaces.element_interface import ElementInterface


class Event(UserList):
    def append(self, item):
        assert (callable(item))
        super().append(item)

    def trigger(self, obj):
        for callback in self:
            callback(obj)


class ElementProxy(ElementInterface):
    def __init__(self, obj):
        self._obj = obj
        self.on_update_finished = Event()

    def update(self, property_id: str, value):
        """
        Todo:
            set property
        """
        sub_lattice = self._obj
        element, = sub_lattice
        method_name = "set_" + property_id
        if method_name == "set_dx":
            # Todo: check that lattice placement works on the original lattice
            #       and that this is not a copy
            shift = sub_lattice.shift.copy()
            shift[0] = value
            sub_lattice.set_shift(shift, absolute=True)
        elif method_name == "set_dy":
            shift = sub_lattice.shift.copy()
            shift[1] = value
            sub_lattice.set_shift(shift, absolute=True)
        elif method_name == "set_main_multipole_strength":
            # Check that it is a quadrupole
            element.update(K=value)
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

    def get_element(self, element_id) -> ElementInterface:
        # TODO: see how the  data is structured  than return the element by id
        sub_lattice = self.acc[element_id]
        # single element expected in sublattice
        _, = sub_lattice
        if sub_lattice:
            proxy = ElementProxy(sub_lattice)

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
