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
        method_name = "set_" + property_id
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
        element = self.acc.find(element_id, 0)
        if element:
            proxy = ElementProxy(element)

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
