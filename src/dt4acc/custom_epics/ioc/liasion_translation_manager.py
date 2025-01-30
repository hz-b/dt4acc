from typing import Dict, Sequence, Mapping
import logging

from bact_twin_architecture.data_model.identifiers import LatticeElementPropertyID, DevicePropertyID, ConversionID
from bact_twin_architecture.interfaces.liaison_manager import LiaisonManagerBase
from bact_twin_architecture.interfaces.state_conversion import StateConversion
from bact_twin_architecture.interfaces.translator_service import TranslatorServiceBase
from bact_twin_architecture.utils.unit_conversion import LinearUnitConversion
from bact_twin_bessyii_impl.bl.bessyii_nomen_clature import name_matches_horizontal_steerer_name, \
    name_matches_vertical_steerer_name, name_matches_steerer_name

from ..data.querries import get_magnets
from ..data.constants import DEFAULTS
from ...core.model.elementmodel import MagnetElementSetup

logger = logging.getLogger("dt4acc")


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
            logger.error(f"{self.__class__.__name__} I did not find id {id_} in lookup table: {ke}")


class TranslatorService(TranslatorServiceBase):
    def __init__(self, lut: Mapping[ConversionID, StateConversion]):
        self.lut = lut

    def get(self, id_: ConversionID) -> StateConversion:
        try:
            return self.lut[id_]
        except KeyError as ke:
            logger.error(f"{self.__class__.__name__}: I did not find id {id_} in lookup table: {ke}")


def remove_id(d: Dict) -> Dict:
    nd = d.copy()
    del d
    del nd["_id"]
    return nd


def magnet_infos_from_db() -> Sequence[MagnetElementSetup]:
    return [MagnetElementSetup(**remove_id(info)) for info in get_magnets().to_list()]


def build_managers() -> (LiaisonManagerBase, TranslatorServiceBase):
    """A first poor mans implementation of the database

    Todo:
        Which info is already in database and better obtained from database?
    """
    infos = magnet_infos_from_db()

    magnet_types = set([info.type for info in infos])
    # Make sure that names are unique ... everything down the list depends on it
    magnet_names = set([info.name for info in infos])
    if len(list(magnet_names)) != len(infos):
        raise AssertionError("Magnet names seem not to be unique, but is assumption of all further processing")

    power_converter_names = set([info.pc for info in infos])
    power_converter_feeds = {
        pc_name: [info.name for info in infos if info.pc == pc_name] for pc_name in power_converter_names
    }

    magnet_lut = {info.name: info for info in infos}
    # todo: check if property must be different for the different magnets ...



    # first for steerers : for AT these are angles applied to the host magnet
    # I use that I know one pc goes to one steerer
    inverse_lut = {
        DevicePropertyID(device_name=info.pc, property="set_current"):
            (LatticeElementPropertyID(element_name=info.name[1:], property="x_kick"),)
        for info in infos if name_matches_horizontal_steerer_name(info.name)

    }
    inverse_lut.update({
        DevicePropertyID(device_name=info.pc, property="set_current"):
            (LatticeElementPropertyID(element_name=info.name[1:], property="y_kick"),)
        for info in infos if name_matches_vertical_steerer_name(info.name)

    })

    # Test that steerer power converters only feed one before going to the next step
    for key in inverse_lut:
        corr_pc = key.device_name
        magnet_names = power_converter_feeds[corr_pc]
        if len(magnet_names) != 1:
            raise AssertionError(f"Found {magnet_names} magnets on assumed corrector power supply {corr_pc}")

    # quadrupoles and sextupoles
    steerer_pc_names = [key.device_name for key in inverse_lut]
    inverse_lut.update({
        DevicePropertyID(device_name=pc_name, property="set_current"):
            tuple([LatticeElementPropertyID(element_name=magnet_name, property="K") for magnet_name in magnet_names])
        for pc_name, magnet_names in power_converter_feeds.items() if pc_name not in steerer_pc_names
    })

    # Add lut for quadrupoles and sextupole
    # Furthermore to feed through the K value ...
    # Todo:
    #     is that appropriate ?
    #     Should one rather use a handler for lattice elements
    quad_updates = dict()
    for axis_name  in "x", "y", "K":
        quad_updates.update({
            DevicePropertyID(device_name=info.name, property=axis_name):
                (LatticeElementPropertyID(element_name=info.name, property=axis_name),)
            for info in infos if info.type in ["Sextupole", "Quadrupole"]
        })
    inverse_lut.update(quad_updates)


    forward_lut = None
    lm = LiaisonManager(forward_lut=forward_lut, inverse_lut=inverse_lut)

    def element_method(element_name):
        device_name = "HS4M2D1R"
        if element_name == device_name:
            pass
        if name_matches_horizontal_steerer_name(element_name):
            return "x_kick"
        elif name_matches_vertical_steerer_name(element_name):
            return "y_kick"
        else:
            return "K"

    def extract_host_element_name(element_name: str) -> str:
        if name_matches_steerer_name(element_name):
            return element_name[1:]
        return element_name

    def construct_linear_conversion(slope: float) -> LinearUnitConversion:
        if slope is None:
            raise AssertionError("Refusing creating linear unit conversion without slope")
        return LinearUnitConversion(slope=slope, intercept=0.0)

    # start to build it for the magnets ... power converter feed
    translator_lut = {
        # todo: replace it with an energy independent version
        ConversionID(
            LatticeElementPropertyID(
                element_name=extract_host_element_name(info.name),
                property=element_method(info.name)
            ),
            DevicePropertyID(device_name=info.pc, property="set_current")
        ):
            # todo: check for the correct conversion
            construct_linear_conversion(slope=info.magnetic_strength)
        for info in infos
    }

    axis_updates = dict()
    for axis_name  in "x", "y", "K":
        axis_updates.update({
            ConversionID(
                lattice_property_id=LatticeElementPropertyID(element_name=info.name, property=axis_name),
                device_property_id=DevicePropertyID(device_name=info.name, property=axis_name)
            )
            : LinearUnitConversion(slope=1.0, intercept=0.0)
            for info in infos if info.type in ["Sextupole", "Quadrupole"]
        })
    translator_lut.update(axis_updates)
    # start to build it for quadrupoles and sextupoles axes

    tm = TranslatorService(translator_lut)
    return lm, tm

if __name__ == "__main__":
    build_managers()