from abc import ABCMeta

from ..interfaces.calculation_interface import TwissCalculator, OrbitCalculator
from ..model.orbit import Orbit
from ..model.twiss import Twiss


class PyAtTwissCalculator(TwissCalculator, metaclass=ABCMeta):
    def calculate(self) -> Twiss:
        # Implement calculation using pyAt
        pass


class PyAtOrbitCalculator(OrbitCalculator, metaclass=ABCMeta):
    def calculate(self) -> Orbit:
        # Implement calculation using pyAt
        pass
