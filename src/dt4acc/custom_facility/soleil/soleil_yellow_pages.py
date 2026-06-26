import json
import os
from abc import ABCMeta, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Sequence, Union


_DEFAULT_ACCELERATOR_SETUP_FILE = (
    Path.home() / "Documents" / "dt4acc_config_data" / "accelerator_setup.json"
)
_ACCELERATOR_SETUP_FILE = Path(
    os.environ.get("DT4ACC_ACCELERATOR_SETUP_FILE", _DEFAULT_ACCELERATOR_SETUP_FILE)
)


def configure_accelerator_setup_file(path: str | Path) -> None:
    global _ACCELERATOR_SETUP_FILE
    _ACCELERATOR_SETUP_FILE = Path(path)


def get_accelerator_setup_file() -> Path:
    return _ACCELERATOR_SETUP_FILE


class FamilyTree(metaclass=ABCMeta):
    """Handling lattice element and their family belonging

    Todo:
        Shall one distinguish that ?

    Two ways to see it:
    * family as seen by a lattice:
        typically some magnets that are split all over the place

    Imagine for some lattice e.g. some quadrupoles could be
    identically as they are produced. But they could still
    belong to different families
    """

    @abstractmethod
    def get(self, family_name: str) -> Sequence[str]:
        """Return a sequence with all identifiers belonging to base class"""
        raise NotImplementedError("use derived class instead")


class FamilyName(Enum):
    quadrupoles = "quadrupoles"
    sextupoles = "sextupoles"
    bends = "bends"
    multipoles = "multipoles"
    horizontal_steerers = "horizontal_steerers"
    vertical_steerers = "vertical_steerers"


class YellowPages(FamilyTree):
    def __init__(self, d: dict):
        self._d = d

    def get(self, family_name: Union[str, FamilyName]) -> Sequence[str]:
        if isinstance(family_name, FamilyName):
            key = family_name.value
        else:
            key = str(family_name)
        return self._d[key]

    def quadrupole_names(self) -> Sequence[str]:
        return self.get("quadrupoles")

    def sextupole_names(self) -> Sequence[str]:
        return self.get("sextupoles")

    def bend_names(self) -> Sequence[str]:
        return self.get("bends")

    def multipole_names(self) -> Sequence[str]:
        return self.get("multipoles")

    def horizontal_steerer_names(self) -> Sequence[str]:
        return self.get("horizontal_steerers")

    def vertical_steerer_names(self) -> Sequence[str]:
        return self.get("vertical_steerers")

    def skew_quad_names(self) -> Sequence[str]:
        """Return names of all CQLN/CQLT skew quadrupole correctors on octupoles."""
        return self.get("skew_quads")

    def cavity_names(self) -> Sequence[str]:
        return self.get("cavities")

    def octupole_names(self) -> Sequence[str]:
        return self.get("octupoles")


    def skew_quad_host_id(self, element_name: str) -> str:
        """
        Return the host element ID for a given skew quad corrector name.
        Returns "CQLN:<uuid>" or "CQLT:<uuid>" — parsed by accelerator_simulator.get().
        """
        return self._d["skew_quad_host_ids"][element_name]


def soleil_yellow_pages() -> YellowPages:
    """
    Creates a YellowPages instance for SOLEIL using the magnet names
    from ~/Documents/soleil/accelerator_setup.json.
    """

    data_file = _ACCELERATOR_SETUP_FILE
    elements = json.loads(data_file.read_text())

    def is_horizontal(e: dict) -> bool:
        name = e["name"]
        fam = e.get("FamName", "")
        return "CDLH" in name or "EM-COR/CH" in name or fam.endswith("_HCOR")

    def is_vertical(e: dict) -> bool:
        name = e["name"]
        fam = e.get("FamName", "")
        return "CDLV" in name or "EM-COR/CV" in name or fam.endswith("_VCOR")

    quadrupoles = [e["name"] for e in elements if e["type"] == "Quadrupole"]
    sextupoles = [e["name"] for e in elements if e["type"] == "Sextupole"]
    bends = [e["name"] for e in elements if e["type"] == "Bend"]
    multipoles = [e["name"] for e in elements if e["type"] == "Multipole"]

    # All steerers are `type == "Steerer"`, split by name/FamName
    horizontal_steerers = [
        e["name"] for e in elements
        if e["type"] == "Steerer" and is_horizontal(e)
    ]
    vertical_steerers = [
        e["name"] for e in elements
        if e["type"] == "Steerer" and is_vertical(e)
    ]

    # SkewQuadrupoles: CQLN/CQLT correctors on octupoles
    # uuid in JSON is "CQLN:<host_uuid>" or "CQLT:<host_uuid>"
    skew_quad_elements = [e for e in elements if e["type"] == "SkewQuadrupole"]
    skew_quads = [e["name"] for e in skew_quad_elements]
    # Map device name → prefixed host id e.g. "CQLN:OH2_QCORROCT_2_001"
    skew_quad_host_ids = {e["name"]: e["uuid"] for e in skew_quad_elements}
    cavities = [e["name"] for e in elements if e["type"] == "RFCavity"]
    octupoles = [e["name"] for e in elements if e["type"] == "Octupole"]

    d = dict(
        quadrupoles=quadrupoles,
        sextupoles=sextupoles,
        bends=bends,
        multipoles=multipoles,
        horizontal_steerers=horizontal_steerers,
        vertical_steerers=vertical_steerers,
        skew_quads=skew_quads,
        skew_quad_host_ids=skew_quad_host_ids,
        cavities=cavities,
        octupoles=octupoles
    )

    return YellowPages(d)
