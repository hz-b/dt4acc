from .calculation_result_view import CalculationResultView
from .repeated_publishing_view import RepeatedResultView
from ...core.model.element_upate import ElementUpdate
from ...core.model.orbit import Orbit
from ...core.model.twiss import TwissWithAggregatedKValues


class ResultView:
    def __init__(self, *, prefix):
        """
        Follows a bit the proxy pattern
        A start to split responsibility

        Todo:
            address if prefix is still required here
        """
        self.calculation_result_view = CalculationResultView(prefix=prefix)
        self.periodic_update_view = RepeatedResultView(prefix=prefix)

    def set_bpm_mimicry(self, bpm_mimicry):
        return
        self.periodic_update_view.set_bpm_mimicry(bpm_mimicry)

    async def push_twiss(self, twiss_result: TwissWithAggregatedKValues):
        await self.calculation_result_view.push_twiss(twiss_result)
        await self.periodic_update_view.push_twiss(twiss_result)

    async def push_orbit(self, orbit_result: Orbit):
        await self.calculation_result_view.push_orbit(orbit_result)
        return
        await self.periodic_update_view.push_orbit(orbit_result)

    async def push_value(self, elm_update: ElementUpdate):
        return
        await self.calculation_result_view.push_value(elm_update)

    async def heart_beat(self):
        await self.periodic_update_view.heart_beat()