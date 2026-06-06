"""
liasion_translator_setup.py  —  SOLEIL II liaison & translator
==============================================================

Design-view architecture: the magnet Tango device IS the control source.
There are no power converters — the magnet device writes main_strength/kicks
directly to the AT element via the new property proxy architecture.

Property name conventions (must match ElementPropertyInterface.handles_property()):
    Quadrupole  → "main_strength"  (MainStrengthForQuadrupole → K / PolynomB[1])
    Sextupole   → "main_strength"  (MainStrengthForSextupole  → H / PolynomB[2])
    Octupole    → "B4"             (Multipole(normal, 4)       → PolynomB[3])
    H-steerer   → "x_kick"        (XKick                      → KickAngle[0])
    V-steerer   → "y_kick"        (YKick                      → KickAngle[1])
    SkewQuad    → "A2"             (Multipole(skew, 2)         → PolynomA[1])
    Cavity      → "frequency"     (Frequency                  → obj.Frequency)

The liaison maps device properties to lattice element properties.
The proxy (in dt4acc_lib) then knows how to read/write each property on the AT object.

build_managers() always returns (yp, lm, tm) — three values.
"""

import functools
import logging
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Dict, Sequence, Mapping, Hashable

from dt4acc_lib.bl.unit_conversion import LinearUnitConversion
from dt4acc_lib.bl.yellow_pages import YellowPages
from dt4acc_lib.interfaces.utils.liaison_manager import LiaisonManagerBase
from dt4acc_lib.interfaces.utils.state_conversion import StateConversion
from dt4acc_lib.interfaces.utils.translator_service import TranslatorServiceBase
from dt4acc_lib.interfaces.utils.yellow_pages import YellowPagesBase
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
    if "uuid" in nd and "uuids" not in nd:
        nd["uuids"] = [nd.pop("uuid")]
    elif "uuid" in nd:
        nd.pop("uuid")
    return nd


def _get_cavity_names() -> list:
    """Return cavity device names directly from the setup JSON."""
    return [m["name"] for m in get_magnets() if m.get("type") == "RFCavity"]


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


def _lattice_property(element_name: str, yp: YellowPages) -> str:
    """
    Return the lattice element property name for a given magnet.
    These names must match ElementPropertyInterface.handles_property()
    in the dt4acc_lib property proxy classes.

        Quadrupole  → "main_strength"  (MainStrengthForQuadrupole)
        Sextupole   → "main_strength"  (MainStrengthForSextupole)
        Octupole    → "B4"             (Multipole(normal, 4))
        H-steerer   → "x_kick"        (XKick)
        V-steerer   → "y_kick"        (YKick)
        SkewQuad    → "A2"             (Multipole(skew, 2))
        Cavity      → "frequency"     (Frequency)
    """
    if element_name in yp.horizontal_steerer_names():
        return "x_kick"
    elif element_name in yp.vertical_steerer_names():
        return "y_kick"
    elif element_name in yp.quadrupole_names():
        return "main_strength"
    elif element_name in yp.sextupole_names():
        return "main_strength"
    elif element_name in yp.octupole_names():
        # Octupole in AT is a Multipole element — liaison maps to B4
        # Multipole(normal_skew=NormalSkew.normal, n_multipole=4).handles_property() == "B4"
        return "B4"
    elif element_name in yp.skew_quad_names():
        # Skew quadrupole corrector (CQLN/CQLT) — liaison maps to A2
        # Multipole(normal_skew=NormalSkew.skew, n_multipole=2).handles_property() == "A2"
        return "A2"
    elif element_name in yp.cavity_names():
        return "frequency"
    else:
        raise AssertionError(f"Don't know how to handle {element_name!r}")


def _host_element_name(element_name: str, yp: YellowPages) -> str:
    """
    Return the AT lattice element name (uuid) that the device property
    maps to. Steerers live on the sextupole host element. Skew quads
    use a compound uuid ("CQLN:<host_uuid>" or "CQLT:<host_uuid>").
    All other magnets are their own host.
    """
    if (element_name in yp.horizontal_steerer_names()
            or element_name in yp.vertical_steerer_names()):
        return element_name.rsplit("-", 1)[0]
    if element_name in yp.skew_quad_names():
        return yp.skew_quad_host_id(element_name)
    return element_name


# ---------------------------------------------------------------------------
# build_managers
# ---------------------------------------------------------------------------
def build_managers():
    """
    Build and return (yp, lm, tm) for the SOLEIL II design-view twin.

    Design-view: no power converters. Magnet devices map device properties
    directly to lattice element properties via the new property proxy architecture.
    All unit conversions use LinearUnitConversion(slope=1.0, intercept=0.0).
    """
    yp = soleil_yellow_pages()
    infos = magnet_infos_from_db()
    cavity_names = _get_cavity_names()

    magnet_names = [info.name for info in infos]
    if len(set(magnet_names)) != len(infos):
        raise AssertionError("Magnet names are not unique — required for LUT correctness")

    _linear = lambda: LinearUnitConversion(slope=1.0, intercept=0.0)

    # ------------------------------------------------------------------
    # Inverse LUT  (DevicePropertyID → LatticeElementPropertyID)
    # ------------------------------------------------------------------
    inverse_lut: dict = {}

    # All magnets — device property → lattice element property
    # The device property name is what the Tango device exposes (e.g. "main_strength")
    # The lattice property name is what the proxy handles (e.g. "main_strength", "B4", "A2")
    # Magnet types that have a control interface in SOLEIL design view.
    # Bends (dipoles) are not directly controlled — skip them.
    _CONTROLLED_TYPES = {
        "Quadrupole", "Sextupole", "Octupole", "Steerer",
        "SkewQuadrupole", "RFCavity"
    }

    for info in infos:
        if info.type not in _CONTROLLED_TYPES:
            continue
        dev_prop = _lattice_property(info.name, yp)  # device exposes same name as proxy
        lat_prop = _lattice_property(info.name, yp)  # proxy property name
        host = _host_element_name(info.name, yp)
        inverse_lut[
            DevicePropertyID(device_name=info.name, property=dev_prop)
        ] = (LatticeElementPropertyID(element_name=host, property=lat_prop),)

    # Cavities → frequency and voltage
    for name in cavity_names:
        inverse_lut[
            DevicePropertyID(device_name=name, property="frequency")
        ] = (LatticeElementPropertyID(element_name=name, property="frequency"),)
        inverse_lut[
            DevicePropertyID(device_name=name, property="voltage")
        ] = (LatticeElementPropertyID(element_name=name, property="voltage"),)

    # Master clock → all cavity frequencies
    inverse_lut[
        DevicePropertyID(device_name="master_clock", property="reference_frequency")
    ] = tuple(
        LatticeElementPropertyID(element_name=name, property="frequency")
        for name in cavity_names
    )

    # Virtual result IDs — passthrough (tune, twiss, track, orbit, chromaticity)
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
    # slope=1.0 for all SOLEIL magnets — design view, no current→field conversion.
    # ------------------------------------------------------------------
    translator_lut: dict = {}

    # All controlled magnets — same set as inverse_lut
    for info in infos:
        if info.type not in _CONTROLLED_TYPES:
            continue
        dev_prop = _lattice_property(info.name, yp)
        lat_prop = _lattice_property(info.name, yp)
        host = _host_element_name(info.name, yp)
        translator_lut[ConversionID(
            LatticeElementPropertyID(element_name=host, property=lat_prop),
            DevicePropertyID(device_name=info.name, property=dev_prop),
        )] = _linear()

    # Cavities — Hz ↔ Hz, slope=1.0 for direct frequency write
    for name in cavity_names:
        translator_lut[ConversionID(
            LatticeElementPropertyID(element_name=name, property="frequency"),
            DevicePropertyID(device_name=name, property="frequency"),
        )] = _linear()
        translator_lut[ConversionID(
            LatticeElementPropertyID(element_name=name, property="voltage"),
            DevicePropertyID(device_name=name, property="voltage"),
        )] = _linear()

    # Master clock — kHz on master clock device
    for name in cavity_names:
        translator_lut[ConversionID(
            LatticeElementPropertyID(element_name=name, property="frequency"),
            DevicePropertyID(device_name="master_clock", property="reference_frequency"),
        )] = LinearUnitConversion(slope=1e-3, intercept=0.0)

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
    """
    Cached entry point. Registers SOLEIL addon proxies then calls build_managers().

    Note: CQLN/CQLT skew quad correctors still use the ADDON_PROXY_REGISTRY
    mechanism from element_proxies.py until the new proxy_factory supports
    compound elements natively.
    """
    from dt4acc_lib.pyat_simulator.proxies.addon_registry import ADDON_PROXY_REGISTRY, SkewQuadCorrectorProxy
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