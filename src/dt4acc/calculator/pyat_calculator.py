import logging
from abc import ABCMeta
from typing import Sequence

import at

from ..interfaces.calculation_interface import TwissCalculator, OrbitCalculator
from ..model.orbit import Orbit
from ..model.twiss import Twiss, TwissForPlane

logger = logging.Logger("pyat-calc")


def _construct_name_list(acc: at.Lattice) -> Sequence[str]:
    """
    Todo:
        * length difference of orbit and twiss data
          find out where to add this one extra name

          Or just to skip it given that the first is a marker anyway?

        * FamName would be the same for ach element if period is more than one
    """
    assert acc.periodicity == 1
    return ["XXX_START"] + [elem.FamName for elem in acc]


class PyAtTwissCalculator(TwissCalculator):
    def __init__(self, acc):
        self.acc = acc

    def calculate(self) -> Twiss:
        # Implement calculation using pyAt
        # with self.calculation_lock:  # Acquire the lock
        logger.warning("pyat twiss calculation starting (get_optics)")
        _, __, twiss = self.acc.get_optics(at.All)
        alpha = twiss["alpha"]
        beta = twiss["beta"]
        nu = twiss["mu"]
        #: todo: find out how to store mu ..
        return Twiss(
            x=TwissForPlane(alpha=alpha[:, 0], beta=beta[:, 0], nu=nu[:, 0]),
            y=TwissForPlane(alpha=alpha[:, 1], beta=beta[:, 1], nu=nu[:, 1]),
            names=_construct_name_list(self.acc)
        )


class PyAtOrbitCalculator(OrbitCalculator):
    def __init__(self, acc):
        self.acc = acc

    def calculate(self) -> Orbit:
        # with self.calculation_lock:  # Acquire the lock
        # Implement calculation using pyAt
        logger.warning("pyat orbit calculation starting (find_orbit)")

        x0, orbit = self.acc.find_orbit(at.All)
        # assuming always True ?
        #: Todo: correct
        found = True
        names = _construct_name_list(self.acc)
        return Orbit(x=orbit[:, 0], y=orbit[:, 2], names=names, x0=x0, found=found)
