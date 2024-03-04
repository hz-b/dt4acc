from collections import UserList
from typing import Union

from dt4acc.bl.event import Event
from dt4acc.bl.delay_execution import DelayExecution
from ..interfaces.accelerator_interface import AcceleratorInterface
from ..interfaces.element_interface import ElementInterface


class AcceleratorImpl(AcceleratorInterface, UserList):
    def __init__(self, acc, proxy_factory, twiss_calculator, orbit_calculator, *, delay=1e-1):
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

        self.twiss_calculation_delay = DelayExecution(callback=cb_twiss, delay=delay)
        self.orbit_calculation_delay = DelayExecution(callback=cb_orbit, delay=delay)

        self.on_changed_value = Event()

    def set_delay(self, delay: Union[float, None]):
        """How much to delay twiss and orbit calculation after last received comamnd
        """
        self.twiss_calculation_delay.set_delay(delay)
        self.orbit_calculation_delay.set_delay(delay)

    def get_element(self, element_id) -> ElementInterface:
        proxy = self.proxy_factory.get(element_id)
        proxy.on_changed_value.append(self.on_changed_value.trigger)

        def cb(unused):
            self.orbit_calculation_delay.request_execution()
            self.twiss_calculation_delay.request_execution()

        #: Todo: review if orbit and twiss are to be calculated
        #:       when ever something is updated
        proxy.on_update_finished.append(cb)
        return proxy

    def calculate_twiss(self):
        return self.twiss_calculator.calculate()

    def calculate_orbit(self):
        return self.orbit_calculator.calculate()
