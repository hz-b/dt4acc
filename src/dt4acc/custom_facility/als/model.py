from dataclasses import dataclass
from typing import Sequence, Tuple, Literal, Annotated

from pydantic import BaseModel, StringConstraints

from dt4acc_lib.model.utils.translator_manager_lookup_table import PolynomCoefficients
from dt4acc_lib.model.utils.command import ReadCommand


EpicsPVCompatibleString = Annotated[
    str,
    StringConstraints(
        pattern=r"^[A-Za-z0-9_\-:+\[\]<>.;]+$",
        min_length=1,
        max_length=60,
    ),
]


@dataclass(frozen=True)
class MMLStyleDeviceIdentifier:
    family: str
    sector: int
    child: int

    def mml_device_index(self):
        """matching how a device reference is stored in ao"""
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
