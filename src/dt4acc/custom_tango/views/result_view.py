from .calculation_result_view import CalculationResultView
from .repeated_publishing_view import RepeatedResultView
from ...core.model.element_upate import ElementUpdate
from ...core.model.orbit import Orbit
from ...core.model.twiss import TwissWithAggregatedKValues
from ...core.utils.logger import get_logger

logger = get_logger()


class ResultView:
    def __init__(self, *, prefix):
        self.calculation_result_view = CalculationResultView(prefix=prefix)
        self.periodic_update_view = RepeatedResultView(prefix=prefix)

    def set_bpm_mimicry(self, bpm_mimicry):
        self.periodic_update_view.set_bpm_mimicry(bpm_mimicry)

    async def push_twiss(self, twiss_result: TwissWithAggregatedKValues):
        logger.info(f"{self.__class__.__name__}.push_twiss: Starting Twiss push (tune_x={twiss_result.x.tune:.10f}, tune_y={twiss_result.y.tune:.10f})")
        await self.calculation_result_view.push_twiss(twiss_result)
        await self.periodic_update_view.push_twiss(twiss_result)
        logger.info(f"{self.__class__.__name__}.push_twiss: Completed Twiss push to both views")

    async def push_orbit(self, orbit_result: Orbit):
        await self.calculation_result_view.push_orbit(orbit_result)
        await self.periodic_update_view.push_orbit(orbit_result)

    async def push_value(self, elm_update: ElementUpdate):
        await self.calculation_result_view.push_value(elm_update)

    async def heart_beat(self):
        await self.periodic_update_view.heart_beat()