from dataclasses import dataclass
from typing import Sequence


@dataclass
class CalculatedPosition:
    fam_name: str
    uid: str
    x: float
    y: float


@dataclass
class CalculatedTrack:
    track : Sequence[CalculatedPosition]