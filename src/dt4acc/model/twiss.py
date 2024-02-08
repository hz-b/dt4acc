from dataclasses import dataclass
from typing import Sequence


@dataclass
class TwissForPlane:
    alpha: Sequence[float]
    beta: Sequence[float]
    nu: Sequence[float]


@dataclass
class Twiss:
    x: TwissForPlane
    y: TwissForPlane
    names: Sequence
