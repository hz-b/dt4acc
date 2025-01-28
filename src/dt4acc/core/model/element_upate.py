from dataclasses import dataclass


@dataclass
class ElementUpdate:
    element_id: str
    property_name: str
    value: float
