from typing import List, Optional

from pydantic import BaseModel
from pydantic.dataclasses import dataclass


class Point(BaseModel):
    dep: float
    indep: float


class Harmonic(BaseModel):
    number: int

    def as_name(self):
        return {
            1: "normal_dipole",
            2: "normal_quadrupole",
            3: "normal_sextupole",
            4: "normal_octupole",
        }[self.number]


class Curve(BaseModel):
    curve: List[Point]
    harmonic: Harmonic


@dataclass
class MagnetElementSetup:
    name: str
    magnetic_strength: float
    uuids: List[str]
    curves: Optional[List[Curve]] = None
    k: Optional[float] = None
    pc: Optional[str] = None
    subtype: Optional[str] = None
    type: Optional[str] = None
    length: Optional[float] = None

    def order(self) -> int:
        """Return multipole order in European convention."""
        magnet_order = {
            "bend": 1,
            "quadrupole": 2,
            "sextupole": 3,
            "octupole": 4,
            "steerer": 1,
            "multipole": 2,
            "skewquadrupole": 2,
        }
        return magnet_order[self.type.lower()]


@dataclass
class PowerConverterElementSetup:
    type: str
    name: str