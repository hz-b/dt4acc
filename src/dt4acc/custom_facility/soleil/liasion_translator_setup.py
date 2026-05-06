"""
liasion_translator_setup.py  —  SOLEIL II liaison & translator
==============================================================

Design-view architecture: the magnet Tango device IS the control source.
There are no power converters — the magnet device writes K/H/x_kick/y_kick
directly to the AT element. The liaison maps device properties to lattice
element properties 1:1.
"""

import functools
import logging
from dataclasses import dataclass
from abc import ABCMeta, abstractmethod
from typing import Dict, Sequence, Mapping, Hashable

from dt4acc_lib.bl.unit_conversion import LinearUnitConversion
from dt4acc_lib.bl.yellow_pages import YellowPages
from dt4acc_lib.interfaces.utils.liaison_manager import LiaisonManagerBase
from dt4acc_lib.interfaces.utils.state_conversion import StateConversion
from dt4acc_lib.interfaces.utils.translator_service import TranslatorServiceBase
from dt4acc_lib.model.utils.identifiers import (
    LatticeElementPropertyID, DevicePropertyID, ConversionID
)

from dt4acc.custom_facility.model.config.elementmodel import MagnetElementSetup
from dt4acc.config.data.constants import ring_parameters
from dt4acc.config.data.querries import get_magnets
from dt4acc.custom_facility.soleil.soleil_yellow_pages import soleil_yellow_pages

logger = logging.getLogger("dt4acc_lm")


# ---------------------------------------------------------------------------
# LiaisonManager
# ---------------------------------------------------------------------------
class LiaisonManager(LiaisonManagerBase):
    def __init__(
        self,
        forward_lut: Mapping[LatticeElementPropertyID, Sequence[DevicePropertyID]],
        inverse_lut: Mapping[DevicePropertyID, Sequence[LatticeElementPropertyID]],
    ):
        self.forward_lut = forward_lut
        self.inverse_lut = inverse_lut

    def forward(self, id_: LatticeElementPropertyID) -> Sequence[DevicePropertyID]:
        return self.forward_lut[id_]

    def inverse(self, id_: DevicePropertyID) -> Sequence[LatticeElementPropertyID]:
        try:
            return self.inverse_lut[id_]
        except KeyError:
            logger.error("LiaisonManager id %s not found in lookup table", id_)
            logger.warning("LiaisonManager: For the device I know %s",
                           {k: v for k, v in self.inverse_lut.items()
                            if k.device_name == id_.device_name})


# ---------------------------------------------------------------------------
# TranslatorService
# ---------------------------------------------------------------------------
class TranslatorService(TranslatorServiceBase):
    def __init__(self, lut: Mapping[ConversionID, StateConversion]):
        self.lut = lut

    def get(self, id_: ConversionID) -> StateConversion:
        try:
            return self.lut[id_]
        except KeyError as ke:
            logger.error("=== TRANSLATOR LOOKUP FAILURE ===")
            logger.error("Requested ID: %s", id_)
            same_device = [k for k in self.lut
                           if k.device_property_id == id_.device_property_id]
            logger.error("Keys with SAME DEVICE (%d):", len(same_device))
            for k in same_device[:10]:
                logger.error("  %s", k)
            same_element = [k for k in self.lut
                            if k.lattice_property_id.element_name
                            == id_.lattice_property_id.element_name]
            logger.error("Keys with SAME ELEMENT (%d):", len(same_element))
            for k in same_element[:10]:
                logger.error("  %s", k)
            raise ke


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _remove_id(d: Dict) -> Dict:
    """Strip _id and normalise uuid → uuids for MagnetElementSetup."""
    nd = d.copy()
    nd.pop("_id", None)
    # SOLEIL JSON has singular "uuid" string; MagnetElementSetup expects "uuids" list
    if "uuid" in nd and "uuids" not in nd:
        nd["uuids"] = [nd.pop("uuid")]
    elif "uuid" in nd:
        nd.pop("uuid")
    return nd


def magnet_infos_from_db() -> Sequence[MagnetElementSetup]:
    known = {
        "name", "magnetic_strength", "uuids", "curves", "length",
        "subtype", "type", "pc", "k", "FamName",
    }
    result = []
    for raw in get_magnets():
        d = _remove_id(raw)
        filtered = {k: v for k, v in d.items() if k in known}
        try:
            result.append(MagnetElementSetup(**filtered))
        except Exception as e:
            logger.error("Failed to create MagnetElementSetup for %s: %s",
                         d.get("name"), e)
    return result


def element_method(element_name: str, yp: YellowPages) -> str:
    if element_name in yp.horizontal_steerer_names():
        return "x_kick"
    elif element_name in yp.vertical_steerer_names():
        return "y_kick"
    elif element_name in yp.quadrupole_names():
        return "K"
    elif element_name in yp.sextupole_names():
        return "H"
    elif element_name in yp.octupole_names():
        return "main_strength"
    elif element_name in yp.skew_quad_names():
        return "skew_quad_strength"
    elif element_name in yp.cavity_names():
        return "frequency"
    else:
        raise AssertionError(f"Don't know how to handle {element_name!r}")


def extract_host_element_name(element_name: str, yp: YellowPages) -> str:
    """Steerers live on the sextupole host element. Skew quads use compound uuid."""
    if (element_name in yp.horizontal_steerer_names()
            or element_name in yp.vertical_steerer_names()):
        host = element_name.rsplit("-", 1)[0]
        return host
    if element_name in yp.skew_quad_names():
        return yp.skew_quad_host_id(element_name)
    return element_name


# ---------------------------------------------------------------------------
# build_managers
# ---------------------------------------------------------------------------
def build_managers():
    """
    Build and return (yp, lm, tm) for the SOLEIL II design-view twin.

    Design-view: no power converters. Magnet devices write K/H/kicks directly.
    All unit conversions use LinearUnitConversion(slope=1.0, intercept=0.0).
    """
    yp = soleil_yellow_pages()
    infos = magnet_infos_from_db()
    cavity_names = yp.cavity_names()

    # Sanity check: names must be unique
    magnet_names = [info.name for info in infos]
    if len(set(magnet_names)) != len(infos):
        raise AssertionError("Magnet names are not unique — required for LUT correctness")

    # ------------------------------------------------------------------
    # Inverse LUT  (DevicePropertyID → LatticeElementPropertyID)
    # Design view: device_name == magnet name, no PC indirection.
    # ------------------------------------------------------------------
    inverse_lut: dict = {}

    # Horizontal steerers → x_kick on host sextupole
    inverse_lut.update({
        DevicePropertyID(device_name=info.name, property="x_kick"): (
            LatticeElementPropertyID(
                element_name=extract_host_element_name(info.name, yp=yp),
                property="x_kick",
            ),
        )
        for info in infos if info.name in yp.horizontal_steerer_names()
    })

    # Vertical steerers → y_kick on host sextupole
    inverse_lut.update({
        DevicePropertyID(device_name=info.name, property="y_kick"): (
            LatticeElementPropertyID(
                element_name=extract_host_element_name(info.name, yp=yp),
                property="y_kick",
            ),
        )
        for info in infos if info.name in yp.vertical_steerer_names()
    })

    # Quadrupoles → K
    inverse_lut.update({
        DevicePropertyID(device_name=info.name, property="K"): (
            LatticeElementPropertyID(element_name=info.name, property="K"),
        )
        for info in infos if info.name in yp.quadrupole_names()
    })

    # Sextupoles → H
    inverse_lut.update({
        DevicePropertyID(device_name=info.name, property="H"): (
            LatticeElementPropertyID(element_name=info.name, property="H"),
        )
        for info in infos if info.name in yp.sextupole_names()
    })

    # x/y attributes on quads and sextupoles (for orbit correction readback)
    for axis in ("x", "y"):
        inverse_lut.update({
            DevicePropertyID(device_name=info.name, property=axis): (
                LatticeElementPropertyID(element_name=info.name, property=axis),
            )
            for info in infos if info.type in ("Quadrupole", "Sextupole")
        })

    # Octupoles → main_strength
    inverse_lut.update({
        DevicePropertyID(device_name=info.name, property="main_strength"): (
            LatticeElementPropertyID(element_name=info.name, property="main_strength"),
        )
        for info in infos if info.type == "Octupole"
    })

    # SkewQuadrupoles (CQLN/CQLT) → skew_quad_strength on compound uuid
    inverse_lut.update({
        DevicePropertyID(device_name=info.name, property="skew_quad_strength"): (
            LatticeElementPropertyID(
                element_name=extract_host_element_name(info.name, yp=yp),
                property="skew_quad_strength",
            ),
        )
        for info in infos if info.type == "SkewQuadrupole"
    })

    # Cavities → frequency
    inverse_lut.update({
        DevicePropertyID(device_name=name, property="frequency"): (
            LatticeElementPropertyID(element_name=name, property="frequency"),
        )
        for name in cavity_names
    })

    # Master clock → all cavity frequencies
    inverse_lut[
        DevicePropertyID(device_name="master_clock", property="reference_frequency")
    ] = tuple(
        LatticeElementPropertyID(element_name=name, property="frequency")
        for name in cavity_names
    )

    # Virtual result IDs (tune, twiss, track, orbit, chromaticity) — passthrough
    for virtual_id, prop in [
        ("twiss",        "parameters"),
        ("tune",         "transversal"),
        ("chromaticity", "transversal"),
        ("track",        "pos"),
        ("orbit",        "pos"),
    ]:
        inverse_lut[
            DevicePropertyID(device_name=virtual_id, property=prop)
        ] = (LatticeElementPropertyID(element_name=virtual_id, property=prop),)

    lm = LiaisonManager(forward_lut=None, inverse_lut=inverse_lut)

    # ------------------------------------------------------------------
    # Translator LUT  (ConversionID → StateConversion)
    # Design view: slope=1.0, intercept=0.0 for all magnets.
    # ------------------------------------------------------------------
    _linear = lambda: LinearUnitConversion(slope=1.0, intercept=0.0)

    translator_lut: dict = {}

    # Steerers
    for info in infos:
        if info.name in yp.horizontal_steerer_names():
            translator_lut[ConversionID(
                LatticeElementPropertyID(
                    element_name=extract_host_element_name(info.name, yp=yp),
                    property="x_kick",
                ),
                DevicePropertyID(device_name=info.name, property="x_kick"),
            )] = _linear()
        elif info.name in yp.vertical_steerer_names():
            translator_lut[ConversionID(
                LatticeElementPropertyID(
                    element_name=extract_host_element_name(info.name, yp=yp),
                    property="y_kick",
                ),
                DevicePropertyID(device_name=info.name, property="y_kick"),
            )] = _linear()

    # Quadrupoles — K and main_strength
    translator_lut.update({
        ConversionID(
            LatticeElementPropertyID(element_name=info.name, property="K"),
            DevicePropertyID(device_name=info.name, property="K"),
        ): _linear()
        for info in infos if info.name in yp.quadrupole_names()
    })
    translator_lut.update({
        ConversionID(
            LatticeElementPropertyID(element_name=info.name, property="main_strength"),
            DevicePropertyID(device_name=info.name, property="K"),
        ): _linear()
        for info in infos if info.name in yp.quadrupole_names()
    })

    # Sextupoles — H and main_strength
    translator_lut.update({
        ConversionID(
            LatticeElementPropertyID(element_name=info.name, property="H"),
            DevicePropertyID(device_name=info.name, property="H"),
        ): _linear()
        for info in infos if info.name in yp.sextupole_names()
    })
    translator_lut.update({
        ConversionID(
            LatticeElementPropertyID(element_name=info.name, property="main_strength"),
            DevicePropertyID(device_name=info.name, property="H"),
        ): _linear()
        for info in infos if info.name in yp.sextupole_names()
    })

    # x/y axes on quads and sextupoles
    for axis in ("x", "y"):
        translator_lut.update({
            ConversionID(
                LatticeElementPropertyID(element_name=info.name, property=axis),
                DevicePropertyID(device_name=info.name, property=axis),
            ): _linear()
            for info in infos if info.type in ("Quadrupole", "Sextupole")
        })

    # Octupoles — main_strength
    translator_lut.update({
        ConversionID(
            LatticeElementPropertyID(element_name=info.name, property="main_strength"),
            DevicePropertyID(device_name=info.name, property="main_strength"),
        ): _linear()
        for info in infos if info.type == "Octupole"
    })

    # SkewQuadrupoles
    translator_lut.update({
        ConversionID(
            LatticeElementPropertyID(
                element_name=extract_host_element_name(info.name, yp=yp),
                property="skew_quad_strength",
            ),
            DevicePropertyID(device_name=info.name, property="skew_quad_strength"),
        ): _linear()
        for info in infos if info.type == "SkewQuadrupole"
    })

    # Cavities — frequency (Hz ↔ Hz, slope=1.0 for SOLEIL)
    translator_lut.update({
        ConversionID(
            LatticeElementPropertyID(element_name=name, property="frequency"),
            DevicePropertyID(device_name=name, property="frequency"),
        ): _linear()
        for name in cavity_names
    })

    # Master clock
    translator_lut.update({
        ConversionID(
            LatticeElementPropertyID(element_name=name, property="frequency"),
            DevicePropertyID(device_name="master_clock", property="reference_frequency"),
        ): LinearUnitConversion(slope=1e-3, intercept=0.0)  # kHz on master clock
        for name in cavity_names
    })

    # Virtual result IDs — passthrough
    for virtual_id, prop in [
        ("twiss",        "parameters"),
        ("tune",         "transversal"),
        ("chromaticity", "transversal"),
        ("track",        "pos"),
        ("orbit",        "pos"),
    ]:
        translator_lut[ConversionID(
            LatticeElementPropertyID(element_name=virtual_id, property=prop),
            DevicePropertyID(device_name=virtual_id, property=prop),
        )] = _linear()

    tm = TranslatorService(translator_lut)
    return yp, lm, tm


@functools.lru_cache(maxsize=1)
def load_managers():
    """Cached entry point. Registers SOLEIL addon proxies then calls build_managers()."""
    from dt4acc_lib.pyat_simulator.element_proxies import ADDON_PROXY_REGISTRY, SkewQuadCorrectorProxy
    # CQLN (Normal)  → PolynomB[1]  corrector_type="normal"
    # CQLT (Tourné)  → PolynomA[1]  corrector_type="skew"
    ADDON_PROXY_REGISTRY["CQLN"] = lambda el, eid, hid: SkewQuadCorrectorProxy(
        el, element_id=eid, host_element_id=hid, corrector_type="normal"
    )
    ADDON_PROXY_REGISTRY["CQLT"] = lambda el, eid, hid: SkewQuadCorrectorProxy(
        el, element_id=eid, host_element_id=hid, corrector_type="skew"
    )
    return build_managers()


if __name__ == "__main__":
    build_managers()