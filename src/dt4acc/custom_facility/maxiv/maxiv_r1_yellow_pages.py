"""
maxiv_r1_yellow_pages.py
========================
YellowPages for MAX IV R1, following the same pattern as soleil_yellow_pages.py.
Defines a local YellowPages subclass with convenience methods, including
skew_quad_names() and skew_quad_host_id() which are MAX IV specific.
"""

import json
from abc import ABCMeta, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Dict, Sequence, Union


class FamilyTree(metaclass=ABCMeta):
    @abstractmethod
    def get(self, family_name: str) -> Sequence[str]:
        raise NotImplementedError("use derived class instead")


class FamilyName(Enum):
    quadrupoles         = "quadrupoles"
    sextupoles          = "sextupoles"
    bends               = "bends"
    multipoles          = "multipoles"
    horizontal_steerers = "horizontal_steerers"
    vertical_steerers   = "vertical_steerers"
    skew_quads          = "skew_quads"
    cavities            = "cavities"


class YellowPages(FamilyTree):
    def __init__(self, d: dict, skew_quad_host_ids: Dict[str, str] = None):
        self._d = d
        self._skew_quad_host_ids = skew_quad_host_ids or {}

    def get(self, family_name: Union[str, FamilyName]) -> Sequence[str]:
        if isinstance(family_name, FamilyName):
            key = family_name.value
        else:
            key = str(family_name)
        return self._d.get(key, [])

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
        return self.get("skew_quads")

    def skew_quad_host_id(self, name: str) -> str:
        """
        Return the host element uuid for a skew quad corrector.
        uuid format: "skew:<first_elem_index>", e.g. "skew:69"
        This is the key used in ADDON_PROXY_REGISTRY.
        """
        return self._skew_quad_host_ids[name]


def maxiv_r1_yellow_pages(data_file: Path = None) -> YellowPages:
    """
    Build a YellowPages for MAX IV R1 from accelerator_setup_maxiv_r1.json.

    Parameters
    ----------
    data_file : Path, optional
        Defaults to ~/Documents/dt4acc_maxiv_r1_twin_data/accelerator_setup.json
    """
    if data_file is None:
        data_file = (
            Path.home()
            / "Documents"
            / "dt4acc_config_data"
            / "accelerator_setup.json"
        )

    elements = json.loads(data_file.read_text())

    quadrupoles = [
        e["name"] for e in elements
        if e["type"] == "Multipole" and e.get("subtype") == "Quad"
    ]
    sextupoles = [
        e["name"] for e in elements
        if e["type"] == "Multipole" and e.get("subtype") == "Sext"
    ]
    bends = [
        e["name"] for e in elements
        if e["type"] == "Multipole" and e.get("subtype") == "Bend"
    ]
    multipoles = [
        e["name"] for e in elements if e["type"] == "Multipole"
    ]
    horizontal_steerers = [
        e["name"] for e in elements
        if e["type"] == "Steerer" and e.get("subtype") == "H"
    ]
    vertical_steerers = [
        e["name"] for e in elements
        if e["type"] == "Steerer" and e.get("subtype") == "V"
    ]
    skew_quad_elements = [e for e in elements if e["type"] == "SkewQuadrupole"]
    skew_quads = [e["name"] for e in skew_quad_elements]
    # name → compound uuid e.g. "R1-101/MAG/CRSKWI-01" → "skew:sci69"
    # The "skew:" prefix triggers ADDON_PROXY_REGISTRY["skew"] in acc.get()
    # which returns a SkewQuadCorrectorProxy instead of a plain ElementProxy.
    skew_quad_host_ids = {
        e["name"]: f"skew:{e['uuids'][0]}" for e in skew_quad_elements
    }
    cavities = [e["name"] for e in elements if e["type"] == "RFCavity"]

    d = dict(
        quadrupoles=quadrupoles,
        sextupoles=sextupoles,
        bends=bends,
        multipoles=multipoles,
        horizontal_steerers=horizontal_steerers,
        vertical_steerers=vertical_steerers,
        skew_quads=skew_quads,
        cavities=cavities,
    )

    return YellowPages(d, skew_quad_host_ids=skew_quad_host_ids)