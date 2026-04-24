from pydantic import BaseModel
from typing import Hashable, Sequence


class EnergyDependentConversionModel(BaseModel):
    """Energy-dependent conversion model for magnetic objects.

    Todo:
        - Add metadata describing the units
    """

    intercept: float  # y-intercept of the calibration curve
    slope: float  # slope of the calibration curve
    conversion_type: str  # e.g., 'linear'


class MagneticObject(BaseModel):
    elem_id: Hashable  # e.g., 'QF1C01A'
    dev_id: Hashable  # e.g., 'QF1C01A' or 'QF1C01'
    type: str  # e.g., 'quadrupole'
    family_member: Sequence[str]
    power_converter_id: Hashable  # reference to PowerConverter.id
    conversion: EnergyDependentConversionModel
