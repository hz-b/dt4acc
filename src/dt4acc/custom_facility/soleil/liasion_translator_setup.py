import functools
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Dict, Sequence, Mapping, Hashable
import logging

from dt4acc_lib.bl.unit_conversion import LinearUnitConversion
from dt4acc_lib.bl.yellow_pages import YellowPages
from dt4acc_lib.interfaces.utils.liaison_manager import LiaisonManagerBase
from dt4acc_lib.interfaces.utils.state_conversion import StateConversion
from dt4acc_lib.interfaces.utils.translator_service import TranslatorServiceBase
from dt4acc_lib.interfaces.utils.yellow_pages import YellowPagesBase
from dt4acc_lib.model.utils.identifiers import LatticeElementPropertyID, DevicePropertyID, ConversionID

from dt4acc.config.data.querries import get_magnets, get_magnets_per_power_converters
from dt4acc.custom_facility.model.config.elementmodel import MagnetElementSetup
from dt4acc.custom_facility.soleil.soleil_yellow_pages import soleil_yellow_pages
from dt4acc.config.data.constants import ring_parameters


def _get_cavity_names() -> list:
    """Return cavity device names (not UUIDs) for use in liaison LUTs."""
    from dt4acc.config.data.querries import get_unique_power_converters_type_specified, get_magnets_per_power_converters
    cavity_names = []
    for pc in get_unique_power_converters_type_specified(["RFCavity"]):
        for m in get_magnets_per_power_converters(pc):
            cavity_names.append(m["name"])
    return cavity_names

logger = logging.getLogger("dt4acc")


@functools.lru_cache(maxsize=1)
def load_managers() -> (YellowPagesBase, LiaisonManagerBase, TranslatorServiceBase):
    """

    Todo:
        appropriate to separate caching from loading?
    """
    # Register SOLEIL-specific addon proxies.
    # CQLN (slow normal quadrupolar corrector) → PolynomA[1] → corrector_type="skew"
    # CQLT (slow turned quadrupolar corrector) → PolynomB[1] → corrector_type="normal"
    # The prefix in the UUID ("CQLN:<uuid>", "CQLT:<uuid>") is SOLEIL nomenclature.
    # The corrector_type values ("skew", "normal") are generic AT physics terms.
    from dt4acc_lib.pyat_simulator.element_proxies import ADDON_PROXY_REGISTRY, SkewQuadCorrectorProxy
    ADDON_PROXY_REGISTRY["CQLN"] = lambda el, eid, hid: SkewQuadCorrectorProxy(
        el, element_id=eid, host_element_id=hid, corrector_type="skew"
    )
    ADDON_PROXY_REGISTRY["CQLT"] = lambda el, eid, hid: SkewQuadCorrectorProxy(
        el, element_id=eid, host_element_id=hid, corrector_type="normal"
    )

    return build_managers()


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
        except KeyError as ke:
            logger.error(
                f"{self.__class__.__name__} I did not find id {id_} in lookup table: {ke}"
            )


class TranslatorService(TranslatorServiceBase):
    def __init__(self, lut: Mapping[ConversionID, StateConversion]):
        self.lut = lut

    def get(self, id_: ConversionID) -> StateConversion:
        try:
            return self.lut[id_]
        except KeyError as ke:
            logger.error(
                f"{self.__class__.__name__}: I did not find id {id_} in lookup table: {ke}"
            )
            od = self.objects_for_device(id_)
            logger.warning(f"{self.__class__.__name__}: For the device I know {od}")
            em = self.objects_for_lat_elem(id_)
            logger.warning(
                f"{self.__class__.__name__}: For the lattice element I know {em}"
            )
            raise ke

    def objects_for_lat_elem(self, id_: ConversionID):
        return {
            key: to
            for key, to in self.lut.items()
            if id_.lattice_property_id.element_name
            == key.lattice_property_id.element_name
        }

    def objects_for_device(self, id_: ConversionID):
        return {
            key: to
            for key, to in self.lut.items()
            if id_.device_property_id.device_name == key.device_property_id.device_name
        }


def remove_id(d: Dict) -> Dict:
    nd = d.copy()
    del d
    del nd["_id"]
    return nd


def magnet_infos_from_db() -> Sequence[MagnetElementSetup]:
    from dt4acc.config.data.querries import get_magnets
    return [MagnetElementSetup(**remove_id(info)) for info in get_magnets()]


def element_method(element_name: str, yp: YellowPages):
    if element_name in yp.horizontal_steerer_names():
        return "x_kick"
    elif element_name in yp.vertical_steerer_names():
        return "y_kick"
    elif element_name in yp.quadrupole_names():
        return "K"
    elif element_name in yp.sextupole_names():
        return "H"
    elif element_name in yp.octupole_names():
        return "main_strength"   # PolynomB[3] = K3 in AT
    elif element_name in yp.skew_quad_names():
        return "skew_quad_strength"
    elif element_name in yp.cavity_names():
        return "frequency"
    else:
        raise AssertionError(f"Don't know how to handle {element_name}")


def extract_host_element_name(element_name: str, yp: YellowPages) -> str:
    """
    If element_name is a horizontal or vertical steerer, return the
    corresponding sextupole name (host element). Otherwise return
    element_name unchanged.
    """

    # steerer → map to its host sextupole
    if (element_name in yp.vertical_steerer_names()
            or element_name in yp.horizontal_steerer_names()):

        # strip the last "-...." part
        host_name = element_name.rsplit("-", 1)[0]

        # optionally check that it’s actually a sextupole we know
        if host_name in yp.sextupole_names():
            return host_name

        # if for some reason it’s not in the sextupole list, still return the stripped name
        return host_name

    # skew quad corrector (CQLN/CQLT on octupole) → "CQLN:<host_uuid>" or "CQLT:<host_uuid>"
    if element_name in yp.skew_quad_names():
        return yp.skew_quad_host_id(element_name)

    # non-steerer: host is the element itself
    return element_name


def construct_energy_independent_linear_conversion(
    slope: float,
):
    if slope is None:
        raise AssertionError("Refusing creating linear unit conversion without slope")
    return EnergyIndependentLinearUnitConversionInfo(
        slope=1.0, intercept=0.0, brho=ring_parameters.brho
    )

class LookupElement(metaclass=ABCMeta):
    @abstractmethod
    def id(self) -> Hashable:
        raise AssertionError("use derived class instead")

@dataclass(frozen=True)
class EnergyIndependentLinearUnitConversionInfo(LookupElement):
    """The name says it"""
    intercept: float
    slope: float
    brho:float

    def id(self):
        return self.slope


def build_managers():
    """A first poor mans implementation of liasion manager and Translation service for BessyII

    Todo:
        Which info is already in database and better obtained from database?
    """
    yp = soleil_yellow_pages()
    infos = magnet_infos_from_db()
    cavity_names = _get_cavity_names()   # device names e.g. ["AN02-SD/RF-CAV/CAV", ...]

    magnet_types = set([info.type for info in infos])
    # Make sure that names are unique ... everything down the list depends on it
    magnet_names = set([info.name for info in infos])
    if len(list(magnet_names)) != len(infos):
        raise AssertionError(
            "Magnet names seem not to be unique, but is assumption of all further processing"
        )

    power_converter_names = set([info.pc for info in infos])
    power_converter_feeds = {
        pc_name: [info.name for info in infos if info.pc == pc_name]
        for pc_name in power_converter_names
    }

    magnet_lut = {info.name: info for info in infos}
    # todo: check if property must be different for the different magnets ...

    # first for steerers : for AT these are angles applied to the host magnet
    # I use that I know one pc goes to one steerer
    # first for steerers : for AT these are angles applied to the host magnet
    # I use that I know one pc goes to one steerer
    inverse_lut = {
        DevicePropertyID(device_name=info.pc, property="set_current"): (
            LatticeElementPropertyID(
                element_name=extract_host_element_name(info.name, yp=yp),
                property="x_kick",
            ),
        )
        for info in infos
        if info.name in yp.horizontal_steerer_names()
    }
    inverse_lut.update(
        {
            DevicePropertyID(device_name=info.pc, property="set_current"): (
                LatticeElementPropertyID(
                    element_name=extract_host_element_name(info.name, yp=yp),
                    property="y_kick",
                ),
            )
            for info in infos
            if info.name in yp.vertical_steerer_names()
        }
    )

    # Test that steerer power converters only feed one before going to the next step
    for key in inverse_lut:
        corr_pc = key.device_name
        magnet_names = power_converter_feeds[corr_pc]
        if len(magnet_names) != 1:
            raise AssertionError(
                f"Found {magnet_names} magnets on assumed corrector power supply {corr_pc}"
            )

    # quadrupoles and sextupoles
    steerer_pc_names = [key.device_name for key in inverse_lut]
    inverse_lut.update(
        {
            DevicePropertyID(device_name=pc_name, property="set_current"): tuple(
                [
                    LatticeElementPropertyID(element_name=magnet_name, property="K")
                    for magnet_name in magnet_names
                    if magnet_name in yp.quadrupole_names()
                ]
            )
            for pc_name, magnet_names in power_converter_feeds.items()
            if pc_name not in steerer_pc_names
        }
    )
    inverse_lut.update(
        {
            DevicePropertyID(device_name=pc_name, property="set_current"): tuple(
                [
                    LatticeElementPropertyID(element_name=magnet_name, property="H")
                    for magnet_name in magnet_names
                    if magnet_name in yp.sextupole_names()
                ]
            )
            for pc_name, magnet_names in power_converter_feeds.items()
            if pc_name not in steerer_pc_names
        }
    )

    inverse_lut.update(
        {
            DevicePropertyID(device_name=pc_name, property="set_current"): tuple(
                [
                    LatticeElementPropertyID(
                        element_name=magnet_name, property="main_strength"
                    )
                    for magnet_name in magnet_names
                ]
            )
            for pc_name, magnet_names in power_converter_feeds.items()
            if pc_name not in steerer_pc_names
        }
    )

    # Add lut for quadrupoles and sextupole
    # Furthermore to feed through the K value ...
    # Todo:
    #     is that appropriate ?
    #     Should one rather use a handler for lattice elements
    quad_updates = dict()
    for axis_name in "x", "y", "K":
        quad_updates.update(
            {
                DevicePropertyID(device_name=info.name, property=axis_name): (
                    LatticeElementPropertyID(
                        element_name=info.name, property=axis_name
                    ),
                )
                for info in infos
                if info.type in ["Sextupole", "Quadrupole"]
            }
        )
    inverse_lut.update(quad_updates)

    # Octupoles — direct main_strength property
    inverse_lut.update(
        {
            DevicePropertyID(device_name=info.pc, property="set_current"): (
                LatticeElementPropertyID(
                    element_name=info.name, property="main_strength"
                ),
            )
            for info in infos
            if info.type == "Octupole"
        }
    )

    # SkewQuadrupoles (CQLN/CQLT correctors on octupoles)
    # The element_name is the CQLN/CQLT Tango device name.
    # The host element id is "CQLN:<uuid>" or "CQLT:<uuid>" — parsed by
    # accelerator_simulator.get() to dispatch to SkewQuadCorrectorProxy.
    inverse_lut.update(
        {
            DevicePropertyID(device_name=info.name, property="skew_quad_strength"): (
                LatticeElementPropertyID(
                    element_name=extract_host_element_name(info.name, yp=yp),
                    property="skew_quad_strength",
                ),
            )
            for info in infos
            if info.type == "SkewQuadrupole"
        }
    )

    # Cavities and master clock
    inverse_lut.update(
        {
            DevicePropertyID(device_name=name, property="frequency"): (
                LatticeElementPropertyID(element_name=name, property="frequency"),
            )
            for name in cavity_names
        }
    )
    inverse_lut.update(
        {
            DevicePropertyID(
                device_name="master_clock", property="reference_frequency"
            ): tuple(
                [
                    LatticeElementPropertyID(element_name=name, property="frequency")
                    for name in cavity_names
                ]
            )
        }
    )

    forward_lut = None
    lm = LiaisonManager(forward_lut=forward_lut, inverse_lut=inverse_lut)

    # start to build it for the magnets ... power converter feed
    translator_lut = {
        ConversionID(
            LatticeElementPropertyID(
                element_name=extract_host_element_name(info.name, yp=yp),
                property=element_method(info.name, yp=yp),
            ),
            DevicePropertyID(device_name=info.pc, property="set_current"),
        ):
        # todo: check for the correct conversion
        construct_energy_independent_linear_conversion(slope=info.magnetic_strength)
        for info in infos
    }
    # add look up for value using main strength for quadrupoles and sextupoles
    translator_lut.update(
        {
            ConversionID(
                LatticeElementPropertyID(
                    element_name=extract_host_element_name(info.name, yp=yp),
                    property="main_strength",
                ),
                DevicePropertyID(device_name=info.pc, property="set_current"),
            ):
            # todo: check for the correct conversion
            construct_energy_independent_linear_conversion(slope=info.magnetic_strength)
            for info in infos
            if info.type in ["Sextupole", "Quadrupole"]
        }
    )

    axis_updates = dict()
    # start to build it for quadrupoles and sextupoles axes
    for axis_name in "x", "y":
        axis_updates.update(
            {
                ConversionID(
                    lattice_property_id=LatticeElementPropertyID(
                        element_name=info.name, property=axis_name
                    ),
                    device_property_id=DevicePropertyID(
                        device_name=info.name, property=axis_name
                    ),
                ): LinearUnitConversion(slope=1.0, intercept=0.0)
                for info in infos
                if info.type in ["Sextupole", "Quadrupole"]
            }
        )
    translator_lut.update(axis_updates)

    # K and H as requested from the device world ... should it be there?
    translator_lut.update(
        {
            ConversionID(
                lattice_property_id=LatticeElementPropertyID(
                    element_name=info.name, property="K"
                ),
                device_property_id=DevicePropertyID(
                    device_name=info.name, property="K"
                ),
            ): LinearUnitConversion(slope=1.0, intercept=0.0)
            for info in infos
            if info.type in ["Quadrupole"]
        }
    )
    # Todo: questionable if that should be handled here ...
    # view should know what to delegate to the lattice
    translator_lut.update(
        {
            ConversionID(
                lattice_property_id=LatticeElementPropertyID(
                    element_name=info.name, property="H"
                ),
                device_property_id=DevicePropertyID(
                    device_name=info.name, property="H"
                ),
            ): LinearUnitConversion(slope=1.0, intercept=0.0)
            for info in infos
            if info.type in ["Sextupole"]
        }
    )

    # Octupoles — main_strength = PolynomB[3] = K3, slope=1.0
    translator_lut.update(
        {
            ConversionID(
                lattice_property_id=LatticeElementPropertyID(
                    element_name=info.name, property="main_strength"
                ),
                device_property_id=DevicePropertyID(
                    device_name=info.pc, property="set_current"
                ),
            ): construct_energy_independent_linear_conversion(slope=info.magnetic_strength)
            for info in infos
            if info.type == "Octupole"
        }
    )

    # SkewQuadrupoles — slope=1.0, no unit conversion (strength in 1/m²)
    translator_lut.update(
        {
            ConversionID(
                lattice_property_id=LatticeElementPropertyID(
                    element_name=extract_host_element_name(info.name, yp=yp),
                    property="skew_quad_strength",
                ),
                device_property_id=DevicePropertyID(
                    device_name=info.name, property="skew_quad_strength"
                ),
            ): LinearUnitConversion(slope=1.0, intercept=0.0)
            for info in infos
            if info.type == "SkewQuadrupole"
        }
    )

    # cavities
    translator_lut.update(
        {
            ConversionID(
                lattice_property_id=LatticeElementPropertyID(
                    element_name=name, property="frequency"
                ),
                device_property_id=DevicePropertyID(
                    device_name=name, property="frequency"
                ),
            ): LinearUnitConversion(
                slope=1e-3, intercept=0.0
            )  # BESSY II uses kHz for the cavities clock
            for name in cavity_names
        }
    )

    translator_lut.update(
        {
            ConversionID(
                LatticeElementPropertyID(element_name=name, property="frequency"),
                DevicePropertyID(
                    device_name="master_clock", property="reference_frequency"
                ),
            ): LinearUnitConversion(
                slope=1e-3, intercept=0.0
            )  # BESSY II uses kHz for the master clock
            for name in cavity_names
        }
    )

    tm = TranslatorService(translator_lut)
    return yp, lm, tm


if __name__ == "__main__":
    build_managers()