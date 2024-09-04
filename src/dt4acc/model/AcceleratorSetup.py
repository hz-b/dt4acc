from pydantic.dataclasses import dataclass


@dataclass
class AcceleratorSetup():
    type: str
    name: str
    hw2phys: float
