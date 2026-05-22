from dataclasses import dataclass
from typing import Sequence, Tuple, Literal

from pydantic import BaseModel

from dt4acc_lib.model.utils.translator_manager_lookup_table import PolynomCoefficients
from dt4acc_lib.model.utils.command import ReadCommand


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


class _ProcessVariableView(BaseModel):
    rcmd: ReadCommand
    pv_name: str
    prec: int
    # Most values will be updated immediately
    # some like BPM or similar only delayewd.
    # review if it should be handled differently ?
    # e.g. all BPM declare a read command of ['track', 'pos']
    # then view dispatches it to them
    # or converter object does it ...
    update: Literal["immediate", "delayed"] = "immediate"


class Monitor(_ProcessVariableView):
    record_type: Literal["ai", "longin"]


class Setpoint(_ProcessVariableView):
    record_type: Literal["ao", "longout"]
    reads: Sequence[ReadCommand]
