from typing import Optional

from pydantic.dataclasses import dataclass

@dataclass
class MagnetElementSetup:
    type: str
    name: str
    #: power converter it is connected to
    pc: str
    magnetic_strength: float
    hw2phys: Optional[float] = None
    k: Optional[float] = None


    def order(self) -> int:
        """return order in European Convention
        """
        magnet_order = dict(bend=1, quadrupole=2, sextupole=3, octupole=4, steerer=1)
        return magnet_order[self.type.lower()]

@dataclass
class PowerConverterElementSetup:
    type: str
    name: str