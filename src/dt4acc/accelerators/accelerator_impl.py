from collections import UserList

import numpy as np
from at import shift_elem

from ..device_interface.event import Event
from ..device_interface.delay_execution import DelayExecution

from ..interfaces.accelerator_interface import AcceleratorInterface
from ..interfaces.element_interface import ElementInterface
from ..model.element_upate import ElementUpdate


def estimate_shift(element, eps=1e-8):
    """
    Todo: get it upstreamed into pyat
    """
    try:
        down_stream_shift = element.T1
    except AttributeError:
        down_stream_shift = np.zeros([6], float)
    try:
        up_stream_shift = element.T2
    except AttributeError:
        up_stream_shift = np.zeros([6], float)

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
            # Todo: Check that it is a quadrupole
            element.update(K=value)
            self.on_changed_value.trigger(
                ElementUpdate(element_id=self.element_id, property_name="K", value=self._obj[0].K)
            )
        else:
            method = getattr(self._obj, method_name)
            method(value)

        self.on_update_finished.trigger(None)


class AddOnElementProxy(ElementProxy):
    """Proxy for an element whose update is to be relayed to an
    other element
    """
    def __init__(self, obj, *, element_id, host_element_id):
        super().__init__(obj, element_id)
        host_element_id = element_id

    def update(self, property_id: str, value):
        raise NotImplementedError("Needs to be implementd for specific case")


class KickAngleCorrectorProxy(AddOnElementProxy):
    """
    Todo:
        already third layer
    """
    def __init__(self, obj, *, updates, **kwargs):
        assert updates is in ["x", "y"]
        self.updates = updates
        super().__init__(*obj, **kwargs)

    def update_kick(self, *, kick_x=None, kick_y=None):
        """Similar to shift
        """

    def update(self, property_id: str, value):
        assert property_id == "K"
        method_name = "set_" + property_id
        if method_name == "set_K":
            """needs to know if it is x or y
            """
            if self.updates == "x":
                self.update_kick(value)
            elif self.updates == "y":
                self.update_kick(value)
            else:
                raise ValueError()
        else:
            raise ValueError()


class AcceleratorImpl(AcceleratorInterface, UserList):
    def __init__(self, acc, proxy_factory, twiss_calculator, orbit_calculator):
        super().__init__()
        self.acc = acc
        self.proxy_factory = proxy_factory
        self.twiss_calculator = twiss_calculator
        self.orbit_calculator = orbit_calculator

        self.twiss = twiss_calculator.calculate()
        self.orbit = orbit_calculator.calculate()

        self.on_new_orbit = Event()
        self.on_new_twiss = Event()

        # need to create delayed execution for these two above
        # these need the to trigger the events below if they are finished
        # or their trigger is passed here
        def cb_twiss():
            self.twiss = self.twiss_calculator.calculate()
            self.on_new_twiss.trigger(self.twiss)

        def cb_orbit():
            self.orbit = self.orbit_calculator.calculate()
            self.on_new_orbit.trigger(self.orbit)

        self.twiss_calculation_delay = DelayExecution(callback=cb_twiss, delay=1e-1)
        self.orbit_calculation_delay = DelayExecution(callback=cb_orbit, delay=1e-1)

        self.on_changed_value = Event()

    def get_element(self, element_id) -> ElementInterface:
        proxy = self.proxy_factory(element_id)
        self._proxy_add_callbacks(proxy)
        return proxy

        # see if the elemnt id is known to the lattice
        sub_lattice = self._get_element(element_id)
        if sub_lattice:
            return self._element_add_callbacks(sub_lattice)
        else:
            raise ValueError(f"Element with ID {element_id} not found")

    def _proxy_add_callbacks(self, proxy):
        proxy.on_changed_value.append(self.on_changed_value.trigger)

        def cb(unused):
            self.orbit_calculation_delay.request_execution()
            self.twiss_calculation_delay.request_execution()

        proxy.on_update_finished.append(cb)
        return proxy

    def _get_element(self, element_id):
        # TODO: see how the  data is structured  than return the element by id
        sub_lattice = self.acc[element_id]
        # single element expected in sublattice
        _, = sub_lattice
        if sub_lattice:
            proxy = ElementProxy(sub_lattice, element_id=element_id)
            self._element_add_callbacks(proxy)

        element_id_of host = self._get_element_id_of_host(element_id)
        sub_lattice = self.acc[element_id]
        # single element expected in sublattice
        _, = sub_lattice
        if not sub_lattice:
            raise ValueError(f"Element with ID {element_id} not found")

        proxy = AddOnElementProxy(sub_lattice, element_id=element_id, host_element_id=element_id)
        self._element_add_callbacks(proxy)
        return proxy

    def _get_element_id_of_host(self, element_id):
        """find an element that is hosted on an other element
        """
        return self.substituion_database[element_id]

    def calculate_twiss(self):
        return self.twiss_calculator.calculate()

    def calculate_orbit(self):
        return self.orbit_calculator.calculate()
