from dataclasses import dataclass
from typing import Sequence


@dataclass
class TwissParameters:
    """
    Todo:
        the phase advance has different abbreviations
        mu / nu

        should it be
    """
    beta: float
    alpha: float
    nu: float


@dataclass
class TwissAtPosition:
    fam_name: str
    uid: str
    x: TwissParameters
    y: TwissParameters


@dataclass
class Twiss:
    twiss: Sequence[TwissAtPosition]