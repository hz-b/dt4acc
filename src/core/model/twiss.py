from dataclasses import dataclass
from enum import Enum
from typing import Sequence


class Planes(Enum):
    x = "x"
    y = "y"
@dataclass
class TwissForPlane:
    alpha: Sequence[float]
    beta: Sequence[float]
    nu: Sequence[float]

@dataclass
class TwissWithAggregatedKValues:
    x: TwissForPlane
    y: TwissForPlane
    names: Sequence
    all_k_pv_names: Sequence
    all_k_pv_values: Sequence[float]

@dataclass
class Twiss:
    x: TwissForPlane
    y: TwissForPlane
    names: Sequence

    def get_plane(self, plane: Planes):
        plane = Planes(plane)
        if plane == Planes.x:
            return self.x
        elif plane == Planes.y:
            return self.y
        else:
            raise AssertionError("How could I end up here")