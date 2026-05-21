from dataclasses import dataclass
from typing import Sequence, Tuple

from dt4acc_lib.model.utils.translator_manager_lookup_table import PolynomCoefficients


@dataclass(frozen=True)
class MMLStyleDeviceIdentifier:
    family: str
    sector: int
    child: int

    def mml_device_index(self):
        """matching how a device reference is stored in ao
        """
        return (self.sector, self.child)


@dataclass(frozen=True)
class PolynomialCoefficientsForDevices:
    for_child_indices: Sequence[int]
    coefficients: PolynomCoefficients


@dataclass(frozen=True)
class CoefficientsForDevices:
    # child number is enough
    for_child_indices: Sequence[int] = ()
    # only for device / child pair
    for_device_pairs: Sequence[Tuple[int, int]] = ()
    coefficients: PolynomCoefficients = None