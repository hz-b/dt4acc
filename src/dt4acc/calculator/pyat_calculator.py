import logging
from abc import ABCMeta
from concurrent.futures import ThreadPoolExecutor
from typing import Sequence

import at
import numpy as np

from ..interfaces.calculation_interface import TwissCalculator, OrbitCalculator
from ..model.orbit import Orbit
from ..model.twiss import TwissForPlane, TwissWithAggregatedKValues

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


class PyAtTwissCalculator(TwissCalculator, metaclass=ABCMeta):
    def __init__(self, acc):
        self.acc = acc
        self.executor = ThreadPoolExecutor()  # Executor for blocking calls

    def calculate(self) -> TwissWithAggregatedKValues:
        logger.warning("Starting Twiss calculation (get_optics)")
        twiss_in = {}
        twiss_in['beta'] = np.array([8.860461, 4.03432])
        twiss_in['alpha'] = np.array([1.030877, 0.602887])
        twiss_in['dispersion'] = np.array([0.013117, -0.031177, 0, 0])

        try:
            # _, __, twiss = self.acc.get_optics(at.All,twiss_in=twiss_in) # for transfer line

            _, __, twiss = self.acc.get_optics(at.All)
            alpha = twiss["alpha"]
            beta = twiss["beta"]
            nu = twiss["mu"]
            pv_names = []
            values = []
            for element in self.acc:
                element_str = str(element)
                element_split_by_space = element_str.split('\n')
                element_type = element_split_by_space[0]
                if element_type in ["Quadrupole:"]:
                    pv_names.append('Anonym:' + element.FamName + ':Cm:set')
                    values.append(element.K)
            return TwissWithAggregatedKValues(
                x=TwissForPlane(alpha=alpha[:, 0], beta=beta[:, 0], nu=nu[:, 0]),
                y=TwissForPlane(alpha=alpha[:, 1], beta=beta[:, 1], nu=nu[:, 1]),
                names=_construct_name_list(self.acc),
                # todo: rename the return model as it is not only twiss results but also it aggregates k values in it
                all_k_pv_names=pv_names,
                all_k_pv_values=values
            )
        except Exception as e:
            logger.error(f"Error during Twiss calculation: {e}")
            # Handle error or rethrow after logging to manage upstream
            raise RuntimeError("Failed to perform Twiss calculation due to invalid input data.") from e

        logger.warning("Twiss calculation completed.")


class PyAtOrbitCalculator(OrbitCalculator, metaclass=ABCMeta):
    def __init__(self, acc):
        self.acc = acc
        self.executor = ThreadPoolExecutor()  # Executor for blocking calls

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
