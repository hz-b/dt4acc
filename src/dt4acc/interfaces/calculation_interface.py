from abc import ABCMeta, abstractmethod

from ..model.orbit import Orbit
from ..model.twiss import Twiss


class TwissCalculator(metaclass=ABCMeta):
    @abstractmethod
    def calculate(self) -> Twiss:
        pass


class OrbitCalculator(metaclass=ABCMeta):
    @abstractmethod
    def calculate(self) -> Orbit:
        pass
