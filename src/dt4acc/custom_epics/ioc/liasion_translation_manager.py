from typing import Dict, Sequence, Mapping
import logging

from accml_lib.core.bl.unit_conversion import EnergyDependentLinearUnitConversion, LinearUnitConversion
from accml_lib.core.bl.liaison_manager import LiaisonManager
from accml_lib.core.bl.translator_service import TranslatorService
from accml_lib.core.interfaces.utils.liaison_manager import LiaisonManagerBase
from accml_lib.core.interfaces.utils.translator_service import TranslatorServiceBase
from accml_lib.core.interfaces.utils.yellow_pages import YellowPagesBase

from accml_lib.core.model.utils.identifiers import (
    LatticeElementPropertyID,
    DevicePropertyID,
    ConversionID,
)
from ..data.querries import get_magnets
from ..data.constants import ring_parameters, cavity_names
from ...core.model.elementmodel import MagnetElementSetup

logger = logging.getLogger("dt4acc")



def remove_id(d: Dict) -> Dict:
    nd = d.copy()
    del d
    del nd["_id"]
    return nd


def magnet_infos_from_db() -> Sequence[MagnetElementSetup]:
    return [MagnetElementSetup(**remove_id(info)) for info in get_magnets()]


def element_method(element_name: str, yp: YellowPagesBase):
    if element_name in yp.get("horizontal_steerers"):
        return "x_kick"
    elif element_name in yp.get("vertical_steerers"):
        return "y_kick"
    elif element_name in yp.get("quadrupoles"):
        return "K"
    elif element_name in yp.get("sextupoles"):
        return "H"
    else:
        raise AssertionError(f"Don't know how to handle {element_name}")


def extract_host_element_name(element_name: str, yp: YellowPagesBase) -> str:
    if element_name in yp.get("vertical_steerers") or element_name in yp.get("horizontal_steerers"):
        return element_name[1:]
    return element_name


def construct_energy_independent_linear_conversion(
    slope: float,
) -> EnergyDependentLinearUnitConversion:
    if slope is None:
        raise AssertionError("Refusing creating linear unit conversion without slope")
    return EnergyDependentLinearUnitConversion(
        slope=1.0 / slope, intercept=0.0, brho=ring_parameters.brho
    )


def build_managers(
    yp: YellowPagesBase = bessyii_yellow_pages(),
) -> (LiaisonManagerBase, TranslatorServiceBase):
    """A first poor mans implementation of liasion manager and Translation service for BessyII

    Todo:
        Which info is already in database and better obtained from database?
    """
    infos = magnet_infos_from_db()

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
    inverse_lut = {
        DevicePropertyID(device_name=info.pc, property="set_current"): (
            LatticeElementPropertyID(element_name=info.name[1:], property="x_kick"),
        )
        for info in infos
        if info.name in yp.get("horizontal_steerers")
    }
    inverse_lut.update(
        {
            DevicePropertyID(device_name=info.pc, property="set_current"): (
                LatticeElementPropertyID(element_name=info.name[1:], property="y_kick"),
            )
            for info in infos
            if info.name in yp.get("vertical_steerers")()
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
    return lm, tm


if __name__ == "__main__":
    build_managers()
