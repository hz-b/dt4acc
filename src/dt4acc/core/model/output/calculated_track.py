from dataclasses import dataclass
from typing import Sequence


@dataclass
class CalculatedPosition:
    name: str
    x: float
    y: float


@dataclass
class CalculatedTrack:
    track : Sequence[CalculatedPosition]