import functools
import logging
from collections import defaultdict
from importlib.resources import files
from pathlib import Path
from typing import Tuple

import jsons
import yaml

from dt4acc_lib.core.bl.liaison_manager import LiaisonManager
from dt4acc_lib.core.bl.translator_service import TranslatorService
from dt4acc_lib.core.bl.unit_conversion import LinearUnitConversion, EnergyDependentLinearUnitConversion
from dt4acc_lib.core.bl.yellow_pages import YellowPages
from dt4acc_lib.core.interfaces.utils.liaison_manager import LiaisonManagerBase
from dt4acc_lib.core.interfaces.utils.translator_service import TranslatorServiceBase
from dt4acc_lib.core.interfaces.utils.yellow_pages import YellowPagesBase
from dt4acc_lib.core.model.utils.identifiers import LatticeElementPropertyID, DevicePropertyID, ConversionID
from dt4acc_lib.core.model.utils.liaison_manager_lookup_table import LiaisonManagerInverseLookupTable, LiaisonManagerForwardLookupTable
from dt4acc_lib.core.model.utils.translator_manager_lookup_table import TranslatorLookupTable

logger = logging.getLogger("accml")


@functools.lru_cache(maxsize=1)
def load_managers() -> (YellowPagesBase, LiaisonManagerBase, TranslatorServiceBase):
    """

    Todo:
        appropriate to separate caching from loading?
    """
    return build_managers(("custom_facility", "bessyii", "resources", "storage_ring", "created"))


def build_managers(config_dir: Tuple[str]):
    obj = load_file(config_dir + ("bessyii_yellow_pages_lookup_table.yml",))
    yp_lut = jsons.load(obj)
    yp = YellowPages(yp_lut)

    obj = load_file(config_dir + ("bessyii_liaison_manager_forward_lookup_table.yml",))
    lm_fwd = jsons.load(obj, LiaisonManagerForwardLookupTable)
    obj = load_file(config_dir + ("bessyii_liaison_manager_inverse_lookup_table.yml",))
    lm_inv = jsons.load(obj, LiaisonManagerInverseLookupTable)
    lm = LiaisonManager(forward_lut=lm_fwd, inverse_lut=lm_inv)

    obj = load_file(config_dir + ("bessyii_translation_service_lookup_table.yml",))
    ts_lut = jsons.load(obj, TranslatorLookupTable)
    #: Todo: use correct brho!
    ts = TranslatorService(lut=ts_lut, brho=5.4)
    return yp, lm, ts

def load_file(config_dir: Tuple[str]):
    t_file = files("dt4acc").joinpath(*(config_dir))
    with open(t_file, "rt") as fp:
        obj = yaml.load(fp, yaml.SafeLoader)
    return obj

def build_managers_to_delete(config_dir: Path) -> (YellowPagesBase, LiaisonManagerBase, TranslatorServiceBase):
    """A first poor mans implementation of liaison manager and Translation service for accml_lib

    Todo:
        Which info is already in database and better obtained from database?

    """

    # Load data from YAML config files
    config_service = ConfigService(magnet_path=full_data_path(Path(config_dir) / "magnets.yaml"),
                                   pc_path=full_data_path(Path(config_dir) / "power_converters.yaml"))
    config_service.load()
    # magnets = magnet_infos_from_db()
    magnets = config_service.get_magnets()
    # Make sure that names are unique ... everything down the list depends on it
    magnet_names = set([magnet.dev_id for magnet in magnets])
    if len(list(magnet_names)) != len(magnets):
        raise AssertionError("Magnet names seem not to be unique, but is assumption of all further processing")

    # TODO: identify a generic way based on data from different labs to build YP
    # at the moment just a hardcoded list of families
    yp = YellowPages(
        dict(
            quadrupoles=[elem.dev_id for elem in magnets if elem.type == "quadrupole"],
            tune_correction_quadrupoles=[elem.dev_id for elem in magnets if
                                         elem.type == "quadrupole" and "tune_correction" in elem.family_member],
            master_clock="master_clock",  # TODO: should power converter sources be a separate part here
            quadrupole_pcs=tuple(set([elem.power_converter_id for elem in magnets if elem.type == "quadrupole"]))
        )
    )
    # TODO: check if property must be different for the different magnets ...

    forward_lut = {LatticeElementPropertyID(element_name=magnet.dev_id, property="main_strength"): DevicePropertyID(
        device_name=magnet.power_converter_id, property="set_current") for magnet in magnets if
        magnet.dev_id in yp.quadrupole_names()}
    forward_lut.update({
        LatticeElementPropertyID(element_name=magnet.dev_id, property="delta_main_strength"): DevicePropertyID(
            device_name=magnet.power_converter_id, property="delta_set_current") for magnet in magnets if
        magnet.dev_id in yp.quadrupole_names()})

    forward_lut.update(
        {LatticeElementPropertyID(element_name="tune", property="transversal") :  DevicePropertyID(
            device_name="tune", property="delta_set_current")}
    )

    # inverse_lut = {
    #     DevicePropertyID(device_name=m.power_converter_id, property="set_current"): [
    #         LatticeElementPropertyID(element_name=m.dev_id, property="main_strength")] for m in magnets}

    inverse_lut_dd = defaultdict(list)

    for m in magnets:
        # currently only setting up the quadrupoles
        if m.dev_id not in yp.quadrupole_names():
            continue

        dp_main = DevicePropertyID(device_name=m.power_converter_id, property="set_current")
        lep_main = LatticeElementPropertyID(element_name=m.dev_id, property="main_strength")
        inverse_lut_dd[dp_main].append(lep_main)

        dp_main = DevicePropertyID(device_name=m.power_converter_id, property="delta_set_current")
        lep_main = LatticeElementPropertyID(element_name=m.dev_id, property="delta_main_strength")
        inverse_lut_dd[dp_main].append(lep_main)

    inverse_lut = dict(inverse_lut_dd)
    inverse_lut[DevicePropertyID(device_name="tune", property="transversal")] = [LatticeElementPropertyID(element_name="tune", property="transversal")]
    lm = LiaisonManager(forward_lut=forward_lut, inverse_lut=inverse_lut)
    del forward_lut, inverse_lut

    translator_lut = {
        ConversionID(lattice_property_id=LatticeElementPropertyID(element_name=m.dev_id, property="main_strength"),
                     device_property_id=DevicePropertyID(device_name=m.power_converter_id,
                                                         property="set_current")): EnergyDependentLinearUnitConversion(
            # TODO: find out if it is the correct converion
            #  magnetic strength is most proably None
            slope=1./m.conversion.slope, intercept=m.conversion.intercept, brho=ring_parameters.brho, ) for m in magnets}

    # as its only a liner interpolation, its simple to do the delta interpolation
    # for complex curves this interpolation will fail ...
    # there the measurement execution engine has to peek into the machine state
    # and apply it
    translator_lut.update({ConversionID(
        lattice_property_id=LatticeElementPropertyID(element_name=m.dev_id, property="delta_main_strength"),
        device_property_id=DevicePropertyID(device_name=m.power_converter_id,
                                            property="delta_set_current")): EnergyDependentLinearUnitConversion(
        # TODO: find out if it is the correct conversion
        #  magnetic strength is most proably None
        slope=1.0/m.conversion.slope, intercept=0.0, brho=ring_parameters.brho) for m in magnets})

    floquet_to_frequency = 500e3 / 400.0
    # Todo: analyse if this setup is appropriate
    translator_lut.update({
        ConversionID(
            lattice_property_id=LatticeElementPropertyID(element_name="tune", property="transversal"),
            device_property_id=DevicePropertyID(device_name="tune", property="delta_set_current")
        ) : TuneConversion(LinearUnitConversion(intercept=0e0, slope=floquet_to_frequency))
    })
    translator_lut.update({
        ConversionID(
            lattice_property_id=LatticeElementPropertyID(element_name="tune", property="transversal"),
            device_property_id=DevicePropertyID(device_name="tune", property="transversal")
        ) : TuneConversion(LinearUnitConversion(intercept=0e0, slope=floquet_to_frequency))
    })
    tm = TranslatorService(translator_lut)
    return yp, lm, tm


if __name__ == "__main__":
    yp, lm, tm = build_managers("custom/accml_lib/config_data")
    # lat_prop_id = LatticeElementPropertyID(element_name="QF1C01A", property="set_current")
    # r, = lm.forward(lat_prop_id)
    # dev_prop_id = DevicePropertyID(device_name="PC_QF1C01A", property="set_current")
    # r, = lm.inverse(dev_prop_id)
    # to = tm.get(ConversionID(lattice_property_id=r, device_property_id=dev_prop_id))  # pprint.pprint(to)
