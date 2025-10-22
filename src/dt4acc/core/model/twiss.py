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
    tune: float

@dataclass
class MainValue:
    #: todo should one here not use a lattice element identifier
    pv_name: str
    value: str

@dataclass
class TwissWithAggregatedKValues:
    x: TwissForPlane
    y: TwissForPlane
    names: Sequence
    #: Todo does it belong here?
    main_values: Sequence[MainValue]

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

@dataclass
class TuneData:
    """extracted tune data for the tune device
    """
    x: float
    y: float