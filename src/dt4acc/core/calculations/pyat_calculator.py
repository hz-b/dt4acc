import getpass
import os
from abc import ABCMeta
from concurrent.futures import ThreadPoolExecutor
from typing import Sequence

import at
import numpy as np

from ..interfaces.calculation_interface import TwissCalculator, OrbitCalculator
from ..model.orbit import Orbit
from ..model.twiss import TwissForPlane, TwissWithAggregatedKValues, MainValue

from ...core.utils.logger import get_logger
logger = get_logger()


"""
@INFO:
Responsible for performing Twiss and Orbit calculations using PyAT.
Takes the accelerator lattice (acc) as input.
Returns processed Twiss and Orbit data wrapped in specific data classes.
"""

def _construct_name_list(acc: at.Lattice) -> Sequence[str]:
    """
    Constructs a list of element names from the AT lattice.

    Args:
        acc (at.Lattice): Accelerator lattice.

    Returns:
        Sequence[str]: List of element names.
    """
    assert acc.periodicity == 1, "Lattice periodicity must be 1"
    return ["XXX_START"] + [elem.FamName for elem in acc]


class PyAtTwissCalculator(TwissCalculator, metaclass=ABCMeta):
    """
    Twiss parameter calculator using PyAT.

    Attributes:
        acc (at.Lattice): The AT lattice.
        machine (object): Machine object with properties.
        executor (ThreadPoolExecutor): Executor to handle parallel computation.
    """

    def __init__(self, acc):
        self.acc = acc
        # self.machine = acc.machine
        self.executor = ThreadPoolExecutor(max_workers=2)  # Limit to prevent over-utilization


    def calculate(self) -> TwissWithAggregatedKValues:
        """
        Perform Twiss parameter calculation.

        Returns:
            TwissWithAggregatedKValues: Twiss results including aggregated K values.

        Raises:
            RuntimeError: If the calculation fails due to invalid input.
        """

        # logger.info("Starting Twiss calculation (get_optics)")

        twiss_in = {
            'beta': np.array([8.860461, 4.03432]),
            'alpha': np.array([1.030877, 0.602887]),
            'dispersion': np.array([0.013117, -0.031177, 0, 0])
        }
        try:
            if True:  # this means it is a ring
                _, summary, twiss = self.acc.get_optics(at.All)
            else:
                _, summary, twiss = self.acc.get_optics(at.All, twiss_in=twiss_in)  # for transfer line

            main_values = self._extract_pv_values()

            return TwissWithAggregatedKValues(
                x=TwissForPlane(alpha=twiss["alpha"][:, 0], beta=twiss["beta"][:, 0], nu=twiss["mu"][:, 0], tune= summary["tune"][0]),
                y=TwissForPlane(alpha=twiss["alpha"][:, 1], beta=twiss["beta"][:, 1], nu=twiss["mu"][:, 1], tune= summary["tune"][1]),
                names=_construct_name_list(self.acc),
                main_values=main_values
            )
        except Exception as e:
            logger.error(f"Error during Twiss calculation: {e}")
            raise RuntimeError("Failed to perform Twiss calculation.") from e

    def _extract_pv_values(self) -> Sequence[MainValue]:
        """
        Extract PV names and K values from the lattice elements.

        Returns:
            tuple: PV names and their corresponding K values.
        """
        main_values = []
        prefix = os.environ.get('DT4ACC_PREFIX', getpass.getuser())
        for element in self.acc:
            if element.__class__.__name__ == "Quadrupole":
                main_values.append(
                    MainValue(
                        pv_name=(f"{prefix}:{element.FamName}:Cm:set"),
                        value=element.K
                    )
                )
            elif element.__class__.__name__ == "Sextupole":
                try:
                    value = element.H
                except:
                    element
                    raise
                main_values.append(
                    MainValue(
                        pv_name=(f"{prefix}:{element.FamName}:Cm:set"),
                        value=element.H
                    )
                )

        return main_values


class PyAtOrbitCalculator(OrbitCalculator, metaclass=ABCMeta):
    """
    Orbit calculator using PyAT.

    Attributes:
        acc (at.Lattice): The AT lattice.
        executor (ThreadPoolExecutor): Executor to handle parallel computation.
    """

    def __init__(self, acc):
        self.acc = acc
        self.executor = ThreadPoolExecutor(max_workers=2)

    def calculate(self) -> Orbit:
        """
        Perform orbit calculation.

        Returns:
            Orbit: Calculated orbit data.

        Raises:
            RuntimeError: If the calculation fails.
        """
        # logger.info("Starting orbit calculation (find_orbit)")

        try:
            x0, orbit = self.acc.find_orbit(at.All)
            found = True
            names = _construct_name_list(self.acc)
            return Orbit(x=orbit[:, 0], y=orbit[:, 2], names=names, x0=x0, found=found)
        except Exception as e:
            logger.error(f"Error during orbit calculation: {e}")
            raise RuntimeError("Failed to perform orbit calculation.") from e