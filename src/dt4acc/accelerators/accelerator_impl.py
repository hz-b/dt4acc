from typing import Union

from dt4acc.bl.delay_execution import DelayExecution
from dt4acc.bl.event import Event
from ..interfaces.accelerator_interface import AcceleratorInterface
from ..interfaces.element_interface import ElementInterface


class AcceleratorImpl(AcceleratorInterface):
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

        async def cb_twiss():
            self.twiss = self.twiss_calculator.calculate()
            await self.on_new_twiss.trigger(self.twiss)

        async def cb_orbit():
            self.orbit = self.orbit_calculator.calculate()
            await self.on_new_orbit.trigger(self.orbit)

        self.twiss_calculation_delay = DelayExecution(callback=cb_twiss, delay=delay)
        self.orbit_calculation_delay = DelayExecution(callback=cb_orbit, delay=delay)

        self.on_changed_value = Event()

        self.on_orbit_calculation_request = self.orbit_calculation_delay.on_calculation_requested
        self.on_orbit_calculation = self.orbit_calculation_delay.on_calculation
        self.on_twiss_calculation_request = self.twiss_calculation_delay.on_calculation_requested
        self.on_twiss_calculation = self.twiss_calculation_delay.on_calculation

    def set_delay(self, delay: Union[float, None]):
        """How much to delay twiss and orbit calculation after last received command"""
        self.twiss_calculation_delay.set_delay(delay)
        self.orbit_calculation_delay.set_delay(delay)

    async def get_element(self, element_id) -> ElementInterface:
        proxy = self.proxy_factory.get(element_id)
        await proxy.on_changed_value.subscribe(self.on_changed_value.trigger)

        async def cb(unused):
            await self.orbit_calculation_delay.request_execution()
            await self.twiss_calculation_delay.request_execution()

        await proxy.on_update_finished.subscribe(cb)
        return proxy

    def calculate_twiss(self):
        return self.twiss_calculator.calculate()

    def calculate_orbit(self):
        return self.orbit_calculator.calculate()
