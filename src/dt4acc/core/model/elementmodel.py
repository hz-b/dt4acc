from typing import Optional

from pydantic.dataclasses import dataclass

@dataclass
class MagnetElementSetup:
    type: str
    name: str
    hw2phys: float
    phys2hw: float
    energy: float
    magnetic_strength: float
    electron_rest_mass: float
    speed_of_light: float
    brho: float
    edf: float
    pc: str
    k: Optional[float] = None

@dataclass
class PowerConverterElementSetup:
    type: str
    name: str