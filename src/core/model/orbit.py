from dataclasses import dataclass
from typing import Sequence


@dataclass
class Orbit:
    x: Sequence[float]
    y: Sequence[float]
    names: Sequence[str]
    found: bool
    x0: Sequence[float]
