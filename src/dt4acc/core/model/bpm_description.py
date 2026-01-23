"""
Todo:
    compare to what is or will be abailabe in accml_lib
"""
from dataclasses import dataclass
from typing import Sequence


@dataclass
class BPMDescription:
    """Beam Position Monitor configuration data

    Data which are not measured by themselves but useful to
    provide
    """

    name: str
    used: bool
    longitudinal_position: float


@dataclass
class BPMDescriptionCollection:
    col: Sequence[BPMDescription]
