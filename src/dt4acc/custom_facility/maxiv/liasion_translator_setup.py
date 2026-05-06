"""
maxiv_r1_liasion_translator_setup.py
=====================================
Liaison manager and translator service for MAX IV R1.

Follows the BESSY II pattern from liasion_translation_manager.py:
  - Inverse LUT keyed by PC (DevicePropertyID) → list of magnets (LatticeElementPropertyID)
  - One PC can drive multiple magnets (e.g. SQFI: 1 PC → 12 magnets)
  - Translator keyed by ConversionID(lattice_prop, device_prop) → UnitConversion

Device view — current ↔ field conversion via excitation curves
(EnergyIndependentCurveUnitConversion) for magnets with curves, fallback to
LinearUnitConversion for thin correctors and skew quads.

Harmonic selection per subtype:
  Quad (SQFI/SQFO)   → harmonic 2 (PolynomB[1])
  Sext (SXDI/etc.)   → harmonic 3 (PolynomB[2])
  Bend               → harmonic 1 (PolynomB[0])
  Steerer H/V        → harmonic 1 (kick)
"""

import functools
import logging
from collections import defaultdict
from typing import Dict, List, Mapping, Optional, Sequence

from dt4acc_lib.bl.liaison_manager import LiaisonManager
from dt4acc_lib.model.utils.liaison_manager_lookup_table import (
    LiaisonManagerInverseLookupTable,
    LiaisonManagerInverseLookupElement,
)
from dt4acc_lib.bl.unit_conversion import (
    LinearUnitConversion,
    EnergyIndependentCurveUnitConversion,
)
from dt4acc_lib.interfaces.utils.state_conversion import StateConversion
from dt4acc_lib.model.utils.identifiers import (
    ConversionID,
    DevicePropertyID,
    LatticeElementPropertyID,
    CurvePoint,
)

from dt4acc.config.data.querries import get_magnets, get_magnets_per_power_converters
from dt4acc.custom_facility.model.config.elementmodel import MagnetElementSetup
from dt4acc.custom_facility.maxiv.maxiv_r1_yellow_pages import YellowPages, maxiv_r1_yellow_pages
from dt4acc.config.data.constants import ring_parameters


class TranslatorService:
    """Local TranslatorService — mirrors dt4acc_lib interface but takes lut directly."""
    def __init__(self, lut: Mapping[ConversionID, StateConversion]):
        self.lut = lut

    def get(self, id_: ConversionID) -> StateConversion:
        try:
            return self.lut[id_]
        except KeyError as ke:
            logger.error(
                "%s: id %s not found in LUT: %s", self.__class__.__name__, id_, ke
            )
            raise ke



logger = logging.getLogger("dt4acc")

_SUBTYPE_TO_HARMONIC = {
    "Quad": 2,
    "Sext": 3,
    "Bend": 1,
    "H":    1,
    "V":    1,
}


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _remove_id(d: Dict) -> Dict:
    nd = d.copy()
    del nd["_id"]
    return nd


def _dev(name: str) -> str:
    """Return device name as-is — Tango preserves registration case."""
    return name

def _make_magnet_setup(d: Dict) -> Optional[MagnetElementSetup]:
    """
    Construct MagnetElementSetup from a DB entry.
    MagnetElementSetup accepts all fields from the JSON (name, uuids, curves,
    length, subtype, type, pc, k, magnetic_strength). Unknown keys are dropped.
    """
    known = {"name", "magnetic_strength", "uuids", "curves", "length",
             "subtype", "type", "pc", "k"}
    filtered = {k: v for k, v in d.items() if k in known}
    try:
        return MagnetElementSetup(**filtered)
    except Exception as e:
        logger.error("Failed to create MagnetElementSetup for %s: %s", d.get("name"), e)
        return None


def magnet_infos_from_db() -> Sequence[MagnetElementSetup]:
    raw = [_remove_id(info) for info in get_magnets()]
    return [i for i in (_make_magnet_setup(d) for d in raw) if i is not None]


def _get_cavity_names() -> list:
    from dt4acc.config.data.querries import get_unique_power_converters_type_specified
    names = []
    for pc in get_unique_power_converters_type_specified(["RFCavity"]):
        for m in get_magnets_per_power_converters(pc):
            names.append(m["name"])
    return names


# ---------------------------------------------------------------------------
# Curve-based conversion
# ---------------------------------------------------------------------------

def _curve_points_for_harmonic(
    curves, harmonic: int
) -> Optional[List[CurvePoint]]:
    """Works with both Curve pydantic objects and raw dicts."""
    for entry in curves:
        if isinstance(entry, dict):
            h = entry.get("harmonic", {}).get("number")
            pts = [CurvePoint(indep=pt["indep"], dep=pt["dep"]) for pt in entry["curve"]]
        else:
            # Curve pydantic object
            h = entry.harmonic.number
            pts = [CurvePoint(indep=pt.indep, dep=pt.dep) for pt in entry.curve]
        if h == harmonic:
            return pts
    return None


def build_curve_conversion(info: MagnetElementSetup) -> StateConversion:
    """
    Build EnergyIndependentCurveUnitConversion from a magnet DB entry.
    Falls back to LinearUnitConversion if no curves or length=0.
    """
    curves = getattr(info, "curves", None) or []
    harmonic = _SUBTYPE_TO_HARMONIC.get(getattr(info, "subtype", ""), 1)
    length = getattr(info, "length", 0.0) or 0.0

    if not curves or length == 0.0:
        return LinearUnitConversion(slope=1.0, intercept=0.0)

    points = _curve_points_for_harmonic(curves, harmonic)
    if points is None:
        logger.warning("No harmonic %d curve for %s, using linear", harmonic, info.name)
        return LinearUnitConversion(slope=1.0, intercept=0.0)

    return EnergyIndependentCurveUnitConversion(
        fwd_points=points,
        bwd_points=points,
        brho=ring_parameters.brho,
        flip_dep_sign=True,
        length=length,
    )


# ---------------------------------------------------------------------------
# element_method / extract_host_element_name
# ---------------------------------------------------------------------------

# Subtype → explicit property name for PolynomB index disambiguation
# Avoids guessing from zero PolynomB values in generic Multipole AT elements
_SUBTYPE_TO_PROPERTY = {
    "Quad":     "main_strength_k",   # PolynomB[1] = K
    "Sext":     "main_strength_h",   # PolynomB[2] = H
    "SkewSext": "main_strength_h",   # PolynomB[2] = H
    "Bend":     "main_strength_b0",  # PolynomB[0] = dipole
}


def element_method(info_or_name, yp: YellowPages) -> str:
    """Return the AT property name for a given element.
    Accepts either a MagnetElementSetup object or a name string.
    """
    name = info_or_name if isinstance(info_or_name, str) else info_or_name.name
    subtype = None if isinstance(info_or_name, str) else getattr(info_or_name, 'subtype', None)

    if name in yp.horizontal_steerer_names():
        return "x_kick"
    elif name in yp.vertical_steerer_names():
        return "y_kick"
    elif name in yp.skew_quad_names():
        return "skew_quad_strength"
    elif name in yp.multipole_names():
        # Use explicit property name to avoid PolynomB[0] ambiguity
        return _SUBTYPE_TO_PROPERTY.get(subtype, "main_strength")
    elif name in yp.get("cavities"):
        return "frequency"
    else:
        raise AssertionError(f"MAX IV R1: unknown element {name!r}")


def extract_host_element_name(info, yp: YellowPages) -> str:
    """
    Return the element_name to use in LatticeElementPropertyID.
    - Skew quads: compound uuid "skew:sci69" → triggers ADDON_PROXY_REGISTRY
    - All others: uuids[0] (FamName) so acc.get() can find the AT element
    """
    name = info if isinstance(info, str) else info.name
    uuids = None if isinstance(info, str) else getattr(info, 'uuids', None)

    if name in yp.skew_quad_names():
        return yp.skew_quad_host_id(name)
    # Use first uuid (FamName) for all other element types
    if uuids:
        return uuids[0]
    return name


# ---------------------------------------------------------------------------
# load_managers / build_managers
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=1)
def load_managers():
    from dt4acc_lib.pyat_simulator.element_proxies import (
        ADDON_PROXY_REGISTRY,
        SkewQuadCorrectorProxy,
    )
    ADDON_PROXY_REGISTRY["skew"] = lambda el, eid, hid: SkewQuadCorrectorProxy(
        el, element_id=eid, host_element_id=hid, corrector_type="skew"
    )
    return build_managers()


def build_managers():
    yp = maxiv_r1_yellow_pages()
    infos = magnet_infos_from_db()
    cavity_names = _get_cavity_names()

    names = [info.name for info in infos]
    if len(set(names)) != len(infos):
        raise AssertionError("Magnet names are not unique")

    # ------------------------------------------------------------------
    # Group magnets by power converter — one PC can drive many magnets
    # (e.g. SQFI: 1 PC → 12 magnets; HCM: 1 PC → 1 magnet)
    # ------------------------------------------------------------------
    pc_feeds: Dict[str, List[MagnetElementSetup]] = defaultdict(list)
    for info in infos:
        pc_feeds[info.pc].append(info)

    magnet_lut = {info.name: info for info in infos}

    # ------------------------------------------------------------------
    # Inverse LUT — keyed by PC (DevicePropertyID) → lattice elements
    # Following BESSY II pattern exactly
    # ------------------------------------------------------------------
    inverse_lut: Dict = {}

    # Steerers — one PC per steerer, keyed by PC
    for info in infos:
        if info.name in yp.horizontal_steerer_names():
            uuid = info.uuids[0] if info.uuids else info.name
            inverse_lut[
                DevicePropertyID(device_name=_dev(info.pc), property="set_current")
            ] = (
                LatticeElementPropertyID(element_name=uuid, property="x_kick"),
            )
        elif info.name in yp.vertical_steerer_names():
            uuid = info.uuids[0] if info.uuids else info.name
            inverse_lut[
                DevicePropertyID(device_name=_dev(info.pc), property="set_current")
            ] = (
                LatticeElementPropertyID(element_name=uuid, property="y_kick"),
            )

    steerer_pcs = {key.device_name for key in inverse_lut}

    # Multipoles — keyed by PC, one PC may drive multiple magnets
    # element_name = first uuid (FamName) so acc.get() can find the AT element
    # property = subtype-specific name so element_proxies sets the right PolynomB index
    for pc_name, pc_infos in pc_feeds.items():
        if pc_name in steerer_pcs:
            continue
        multipole_magnets = [i for i in pc_infos if i.name in yp.multipole_names()]
        if multipole_magnets:
            inverse_lut[
                DevicePropertyID(device_name=_dev(pc_name), property="set_current")
            ] = tuple(
                LatticeElementPropertyID(
                    element_name=info.uuids[0] if info.uuids else info.name,
                    property=element_method(info, yp=yp)
                )
                for info in multipole_magnets
            )

    # SkewQuadrupoles — keyed by PC, routed via compound uuid "skew:<famnum>"
    # The compound uuid triggers ADDON_PROXY_REGISTRY["skew"] in accelerator_simulator
    # which returns a SkewQuadCorrectorProxy instead of a plain ElementProxy.
    for pc_name, pc_infos in pc_feeds.items():
        skew_infos = [i for i in pc_infos if i.name in yp.skew_quad_names()]
        if skew_infos:
            inverse_lut[
                DevicePropertyID(device_name=_dev(pc_name), property="set_current")
            ] = tuple(
                LatticeElementPropertyID(
                    element_name=yp.skew_quad_host_id(info.name),  # "skew:69" etc.
                    property="skew_quad_strength",
                )
                for info in skew_infos
            )

    # Direct magnet→magnet passthrough (device name = magnet name)
    # Allows writing directly to magnet Tango devices in addition to PCs.
    for info in infos:
        if info.name in yp.multipole_names():
            inverse_lut[
                DevicePropertyID(device_name=_dev(info.name), property="main_strength")
            ] = (
                LatticeElementPropertyID(
                    element_name=info.name, property="main_strength"
                ),
            )
        elif info.name in yp.horizontal_steerer_names():
            inverse_lut[
                DevicePropertyID(device_name=_dev(info.name), property="x_kick")
            ] = (
                LatticeElementPropertyID(
                    element_name=info.name, property="x_kick"
                ),
            )
        elif info.name in yp.vertical_steerer_names():
            inverse_lut[
                DevicePropertyID(device_name=_dev(info.name), property="y_kick")
            ] = (
                LatticeElementPropertyID(
                    element_name=info.name, property="y_kick"
                ),
            )

    # Cavities
    for name in cavity_names:
        inverse_lut[
            DevicePropertyID(device_name=_dev(name), property="frequency")
        ] = (LatticeElementPropertyID(element_name=name, property="frequency"),)

    inverse_lut[
        DevicePropertyID(device_name="master_clock", property="reference_frequency")
    ] = tuple(
        LatticeElementPropertyID(element_name=name, property="frequency")
        for name in cavity_names
    )

    # ------------------------------------------------------------------
    # Fixed internal read commands — required by TangoController heartbeat
    # These route the physics calculation results (twiss, tune, track)
    # back into the simulator backend. Every liaison must include them.
    # ------------------------------------------------------------------
    for prop in ("transversal", "x", "y", "flq_x", "flq_y", "transversal_frequency"):
        inverse_lut[
            DevicePropertyID(device_name="tune", property=prop)
        ] = (LatticeElementPropertyID(element_name="tune", property="transversal"),)

    inverse_lut[
        DevicePropertyID(device_name="twiss", property="parameters")
    ] = (LatticeElementPropertyID(element_name="twiss", property="parameters"),)

    inverse_lut[
        DevicePropertyID(device_name="track", property="pos")
    ] = (LatticeElementPropertyID(element_name="track", property="pos"),)

    inverse_lut[
        DevicePropertyID(device_name="orbit", property="pos")
    ] = (LatticeElementPropertyID(element_name="orbit", property="pos"),)

    # Wrap plain dict into LiaisonManagerInverseLookupTable as required by dt4acc_lib
    inverse_lut_table = LiaisonManagerInverseLookupTable(
        lut=[
            LiaisonManagerInverseLookupElement(dev_id=dev_id, lat_ids=lat_ids)
            for dev_id, lat_ids in inverse_lut.items()
        ]
    )
    inverse_lut_table.verify()
    lm = LiaisonManager(forward_lut=None, inverse_lut=inverse_lut_table)
    translator_lut: Dict = {}

    # All magnets — primary conversion keyed by (magnet, PC)
    translator_lut.update({
        ConversionID(
            LatticeElementPropertyID(
                element_name=extract_host_element_name(info, yp=yp),
                property=element_method(info, yp=yp),
            ),
            DevicePropertyID(device_name=_dev(info.pc), property="set_current"),
        ): build_curve_conversion(info)
        for info in infos
    })

    # Multipoles — additional main_strength entry (for direct device passthrough)
    translator_lut.update({
        ConversionID(
            LatticeElementPropertyID(
                element_name=info.name, property="main_strength"
            ),
            DevicePropertyID(device_name=_dev(info.name), property="main_strength"),
        ): LinearUnitConversion(slope=1.0, intercept=0.0)
        for info in infos
        if info.name in yp.multipole_names()
    })

    # Cavities
    translator_lut.update({
        ConversionID(
            LatticeElementPropertyID(element_name=name, property="frequency"),
            DevicePropertyID(device_name=_dev(name), property="frequency"),
        ): LinearUnitConversion(slope=1.0, intercept=0.0)
        for name in cavity_names
    })
    translator_lut.update({
        ConversionID(
            LatticeElementPropertyID(element_name=name, property="frequency"),
            DevicePropertyID(device_name="master_clock", property="reference_frequency"),
        ): LinearUnitConversion(slope=1.0, intercept=0.0)
        for name in cavity_names
    })

    # Magnet-level steerer passthrough — identity conversion when writing
    # directly to a steerer magnet device (not via PC)
    translator_lut.update({
        ConversionID(
            LatticeElementPropertyID(element_name=info.name, property="x_kick"),
            DevicePropertyID(device_name=_dev(info.name), property="x_kick"),
        ): LinearUnitConversion(slope=1.0, intercept=0.0)
        for info in infos
        if info.name in yp.horizontal_steerer_names()
    })
    translator_lut.update({
        ConversionID(
            LatticeElementPropertyID(element_name=info.name, property="y_kick"),
            DevicePropertyID(device_name=_dev(info.name), property="y_kick"),
        ): LinearUnitConversion(slope=1.0, intercept=0.0)
        for info in infos
        if info.name in yp.vertical_steerer_names()
    })

    # ------------------------------------------------------------------
    # Fixed virtual result conversions — identity passthrough for twiss,
    # tune, track, orbit. These are physics results not magnet properties;
    # no unit conversion needed, value passes through unchanged.
    # ------------------------------------------------------------------
    for virtual_id, prop in [
        ("twiss", "parameters"),
        ("tune",  "transversal"),
        ("track", "pos"),
        ("orbit", "pos"),
    ]:
        translator_lut[ConversionID(
            LatticeElementPropertyID(element_name=virtual_id, property=prop),
            DevicePropertyID(device_name=virtual_id, property=prop),
        )] = LinearUnitConversion(slope=1.0, intercept=0.0)

    tm = TranslatorService(translator_lut)
    return yp, lm, tm


if __name__ == "__main__":
    build_managers()