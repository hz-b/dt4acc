"""
Todo:
    consider to move it to accml
"""
import functools
import logging
import datetime
import pprint
from collections import defaultdict
from dataclasses import asdict
from importlib.resources import files
from typing import Dict, Sequence, Tuple, List

import jsons
import yaml

from dt4acc.custom_facility.model.config.elementmodel import MagnetElementSetup
from dt4acc.custom_facility.model.config.magnet import MagneticObject
from dt4acc.custom_facility.model.config.power_converter import PowerConverter
from dt4acc_lib.bl.yellow_pages import YellowPages
from dt4acc_lib.bl.unit_conversion import EnergyDependentLinearUnitConversion
from dt4acc_lib.interfaces.utils.yellow_pages import YellowPagesBase
from dt4acc_lib.model.utils.identifiers import DevicePropertyID, LatticeElementPropertyID, ConversionID
from dt4acc_lib.model.utils.liaison_manager_lookup_table import LiaisonManagerInverseLookupElement, \
    LiaisonManagerInverseLookupTable, LiaisonManagerForwardLookupElement, LiaisonManagerForwardLookupTable
from dt4acc_lib.model.utils.translator_manager_lookup_table import TranslatorLookupTable, \
    TranslatorLookupTableElement, PolynomCoefficients, TuneConversionCoefficients, IdentityMapper

from dt4acc.custom_epics.data.constants import ring_parameters
from dt4acc.custom_epics.data.querries import get_magnets

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


def build_liaison_manager_lut(
        data_path: Tuple[str], *, yp: YellowPagesBase
) -> (Sequence[LiaisonManagerForwardLookupElement], Sequence[LiaisonManagerInverseLookupElement]):
    """A first poor mans implementation of liaison manager BessyII

    Todo:
        Which info is already in database and better obtained from database?
    """
    magnet_info = get_magnet_info(data_path=data_path)

    magnet_types = set([info.type for info in magnet_info])
    # Make sure that names are unique ... everything down the list depends on it
    magnet_names = set([info.elem_id for info in magnet_info])
    assert len(magnet_names) == len(magnet_info), "Magnet names seem not to be unique, but is assumption of all further processing"

    power_converter_names = set([info.dev_id for info in magnet_info])
    power_converter_feeds = {
        pc_name: [info.elem_id for info in magnet_info if info.dev_id == pc_name]
        for pc_name in power_converter_names
    }

    pc_magnet_is_connected_to = {
        entry.elem_id: entry.power_converter_id for entry in magnet_info
    }

    # magnet_lut = {info.name: info for info in magnet_info}
    # todo: check if property must be different for the different magnets ...

    # These contain a one to one mapping (for quadrupoles and sextupoles)
    # therefore I need to group them as they belong together
    inv_d = defaultdict(list)
    fwd_d = defaultdict(list)
    for family_name, lattice_property, at_property in (
        # fmt:off
        ( "quadrupoles"         , "main_strength", "K" ),
        ( "sextupoles"          , "main_strength", "H" ),
        # fmt:on
    ):
        for entry in magnet_info:
            if entry.elem_id in yp.get(family_name):
                dev_name = str(pc_magnet_is_connected_to[entry.elem_id])
                lat_p  = LatticeElementPropertyID(element_name=str(entry.elem_id), property=lattice_property)
                pc_dev_p = DevicePropertyID(device_name=dev_name, property="set_current")
                mag_dev_p = DevicePropertyID(device_name=str(entry.dev_id), property="main_strength")
                fwd_d[lat_p].append(pc_dev_p)
                inv_d[pc_dev_p].append(lat_p)
                inv_d[mag_dev_p].append(lat_p)
                # Readback current only needs to go one way
                inv_d[DevicePropertyID(device_name=dev_name, property="rdbk_current")].append(lat_p)
                # Todo: review naming of the properties
                inv_d[DevicePropertyID(device_name=entry.dev_id, property="main_strength_rdbk")].append(lat_p)

    # special treatment for horizontal and vertical steerers as these are cowound ..
    # so the magnet name is the sextupole but the
    # power converter
    lut_fwd = []
    lut_inv = []

    for family_name, lattice_property, co_wound_prefix in (
        # fmt:off
        ( "horizontal_steerers" , "x_kick", "H"),
        ( "vertical_steerers"   , "y_kick", "V"),
        # fmt:on
    ):
        names_in_family = [f"{co_wound_prefix}{name}" for name in yp.get(family_name)]
        for entry in magnet_info:
            if entry.elem_id in names_in_family:
                dev_name = str(pc_magnet_is_connected_to[entry.elem_id])
                assert entry.elem_id.startswith(co_wound_prefix)
                host_sextupole = entry.elem_id[1:]
                lat_p = LatticeElementPropertyID(element_name=str(host_sextupole), property=lattice_property)
                pc_dev_p = DevicePropertyID(device_name=dev_name, property="set_current")
                mag_dev_p = DevicePropertyID(device_name=str(entry.dev_id), property="main_strength")
                fwd_d[lat_p].append(pc_dev_p)
                inv_d[pc_dev_p].append(lat_p)
                inv_d[mag_dev_p].append(lat_p)

                # Readback current only needs to go one way
                inv_d[DevicePropertyID(device_name=dev_name, property="rdbk_current")].append(lat_p)

    lut_fwd += [LiaisonManagerForwardLookupElement(lat_id=k, dev_ids=v) for k,v in fwd_d.items()]
    lut_inv += [LiaisonManagerInverseLookupElement(dev_id=k, lat_ids=v) for k,v in inv_d.items()]
    del fwd_d, inv_d

    for family, same_property in [
        # fmt:off
        ( "quadrupoles" , "x" ),
        ( "sextupoles"  , "x" ),
        ( "quadrupoles" , "y" ),
        ( "sextupoles"  , "y" ),
        # fmt:on
        ("cavities", "frequency")
    ]:
        lut_inv += [
            LiaisonManagerInverseLookupElement(
                dev_id=DevicePropertyID(device_name=entry.dev_id, property=same_property),
                lat_ids=[LatticeElementPropertyID(element_name=entry.elem_id, property=same_property)]
            )
            for entry in magnet_info if entry.elem_id in yp.get(family)
        ]

    lut_inv += [
        LiaisonManagerInverseLookupElement(
            dev_id=DevicePropertyID(device_name="master_clock", property="reference_frequency"),
            lat_ids=[
                LatticeElementPropertyID(element_name=cavity_name, property="frequency")
                for cavity_name in yp.get("cavities")
            ]
        )
    ]
    lut_fwd += [
        LiaisonManagerForwardLookupElement(
            lat_id=LatticeElementPropertyID(element_name=cavity_name, property="frequency"),
            dev_ids=[DevicePropertyID(device_name="master_clock", property="reference_frequency")]
        )
        for cavity_name in yp.get("cavities")
    ]

    # Dedicate elements that represent calculation results
    lut_fwd += [
        LiaisonManagerForwardLookupElement(
            lat_id=LatticeElementPropertyID(element_name="tune", property="transversal"),
            dev_ids=[
                DevicePropertyID(device_name="tune", property=prop)
                for prop in ("x", "y", "flq_x", "flq_y", "transversal", "transversal_frequency")
            ]
        )
    ]
    lut_inv += [
        LiaisonManagerInverseLookupElement(
            dev_id=DevicePropertyID(device_name="tune", property=prop),
            lat_ids=[LatticeElementPropertyID(element_name="tune", property="transversal")]
        )
        for prop in ("x", "y", "flq_x", "flq_y", "transversal", "transversal_frequency")
    ]

    lut_inv += [
        LiaisonManagerInverseLookupElement(
            dev_id=DevicePropertyID(device_name="orbit", property="pos"),
            lat_ids=[LatticeElementPropertyID(element_name="orbit", property="pos")]
        )
    ]
    lut_inv += [
        LiaisonManagerInverseLookupElement(
            dev_id=DevicePropertyID(device_name="twiss", property="parameters"),
            lat_ids=[LatticeElementPropertyID(element_name="twiss", property="parameters")]
        ),
        LiaisonManagerInverseLookupElement(
            dev_id=DevicePropertyID(device_name="track", property="pos"),
            lat_ids=[LatticeElementPropertyID(element_name="track", property="pos")]
        ),
        LiaisonManagerInverseLookupElement(
            dev_id=DevicePropertyID(device_name="survey", property="s"),
            lat_ids=[LatticeElementPropertyID(element_name="survey", property="s")]
        )
    ]
    lut_fwd += [
        LiaisonManagerForwardLookupElement(
            lat_id=LatticeElementPropertyID(element_name="twiss", property="parameters"),
            dev_ids=[DevicePropertyID(device_name="twiss", property="parameters")]
        ),
        LiaisonManagerForwardLookupElement(
            lat_id=LatticeElementPropertyID(element_name="track", property="pos"),
            dev_ids=[DevicePropertyID(device_name="track", property="pos")]
        ),
        LiaisonManagerForwardLookupElement(
            lat_id=LatticeElementPropertyID(element_name="survey", property="s"),
            dev_ids=[DevicePropertyID(device_name="survey", property="s")]
        )
    ]


    return lut_fwd, lut_inv


def build_translator_manager_lut(
        data_path: Tuple[str], *, yp: YellowPagesBase, lm_inv: LiaisonManagerInverseLookupTable
)-> Sequence[TranslatorLookupTableElement]:
    """A first poor mans implementation of liaison manager BessyII"""
    # start to build it for the magnets ... power converter feed

    magnet_infos = get_magnet_info(data_path=data_path)
    pc_infos = get_pc_info(data_path=data_path)

    lut: List[TranslatorLookupTableElement] = []

    # lets make the easy ones our selves first
    for cavity_name in yp.get("cavities"):
        lut.append(
            TranslatorLookupTableElement(
                ConversionID(
                    lattice_property_id=LatticeElementPropertyID(element_name=cavity_name, property="frequency"),
                    device_property_id=DevicePropertyID(device_name="master_clock", property="reference_frequency")
                ),
                PolynomCoefficients([0.0, 1.0], energy_dependent=False)
            )
        )

    all_keys = [key for key in lm_inv.keys()]

    # Find out which power converter feeds what
    pc_feeds = defaultdict(list)
    for mag_info in magnet_infos:
        pc_feeds[mag_info.power_converter_id].append(mag_info.elem_id)

    # Simplify look up by magnet name
    mag_info_lut = {mag_info.elem_id: mag_info for mag_info in magnet_infos}

    unhandled = []
    for dev_p in all_keys:
        feed_by_pc = pc_feeds.get(dev_p.device_name)
        if not feed_by_pc:
            unhandled.append(dev_p)
            continue
        lat_ps = lm_inv.get(dev_p)
        for lat_p in lat_ps:
            if mag_info_lut.get(lat_p.element_name, None) is None:
                logger.warning("No magnet info for %s", lat_p.element_name)
                continue
            conv = mag_info_lut[lat_p.element_name].conversion
            assert conv.conversion_type == "linear"
            lut.append(
                TranslatorLookupTableElement(
                    ConversionID(lat_p, dev_p),
                    PolynomCoefficients([conv.intercept, conv.slope], energy_dependent=True)
                )
            )

    all_keys, unhandled = unhandled, []
    for dev_p in all_keys:
        if dev_p.property not in ["x", "y"]:
            unhandled.append(dev_p)
            continue
        lat_p, = lm_inv.get(dev_p)

        if lat_p.element_name not in yp.get("quadrupoles") and lat_p.element_name not in yp.get("sextupoles"):
            unhandled.append(dev_p)
            continue

        lut.append(
            TranslatorLookupTableElement(
                ConversionID(lat_p, dev_p),
                PolynomCoefficients([0.0, 1.0], energy_dependent=False)
            )
        )

    # handle corrector main strength
    all_keys, unhandled = unhandled, []
    for dev_p in all_keys:
        if dev_p.device_name not in yp.get("steerers"):
            unhandled.append(dev_p)
            continue
        # assuming that there is only one for the steerer main strength
        lat_p, = lm_inv.get(dev_p)
        # Todo: find out the coefficient for magnet to steerer
        lut.append(
            TranslatorLookupTableElement(
                ConversionID(lat_p, dev_p),
                PolynomCoefficients([0.0, 1.0], energy_dependent=False)
            )
        )

    all_keys, unhandled = unhandled, []
    dev_names = list(yp.get("quadrupoles")) + list(yp.get("sextupoles"))
    for dev_p in all_keys:
        if dev_p.property == "main_strength" and dev_p.device_name in dev_names:
            lat_p, = lm_inv.get(dev_p)
            lut.append(
                TranslatorLookupTableElement(
                    ConversionID(lat_p, dev_p),
                    PolynomCoefficients([0.0, 1.0], energy_dependent=False)
                )
            )
        elif dev_p.property == "main_strength_rdbk" and dev_p.device_name in dev_names:
            lat_p, = lm_inv.get(dev_p)
            lut.append(
                TranslatorLookupTableElement(
                    ConversionID(lat_p, dev_p),
                    PolynomCoefficients([0.0, 1.0], energy_dependent=False)
                )
            )
        else:
            unhandled.append(dev_p)

    lat_p = LatticeElementPropertyID(element_name="tune", property="transversal")
    lut.extend([
        TranslatorLookupTableElement(
            ConversionID(lat_p, DevicePropertyID(device_name="tune", property=prop)),
            IdentityMapper()
        )
        for prop in ("flq_x", "flq_y", "transversal")
    ])

    # These are just a hack ... here we have interdependence of different
    #                           values
    #     to calculate it one would also need the reference frequency
    # Warning: Frequency needs to be read from master clock or similar
    floquet_to_frequency = 500e3 / 400.0
    lut.extend([
        TranslatorLookupTableElement(
             ConversionID(lat_p, DevicePropertyID(device_name="tune", property=prop)),
             TuneConversionCoefficients(PolynomCoefficients([0.0, floquet_to_frequency], energy_dependent=False))
        )
        for prop in ("x", "y", "transversal_frequency")
    ])

    lut.extend([
        TranslatorLookupTableElement(
            ConversionID(LatticeElementPropertyID(element_name="twiss", property="parameters"),
                         DevicePropertyID(device_name="twiss", property="parameters"),
                         ),
            IdentityMapper()
        ),
        TranslatorLookupTableElement(
            ConversionID(LatticeElementPropertyID(element_name="track", property="pos"),
                         DevicePropertyID(device_name="track", property="pos"),
                         ),
            IdentityMapper()
        ),
        TranslatorLookupTableElement(
            ConversionID(
                LatticeElementPropertyID(element_name="survey", property="s"),
                DevicePropertyID(device_name="survey", property="s"),
            ),
            IdentityMapper()
        ),
    ])

    print("No translation objects for")
    pprint.pprint(unhandled)
    return lut


def create_yellow_pages_entries() ->  Dict[str, Sequence[str]]:
    # standard quadrupoles
    quadrupoles = [
        f"Q{family}M{child}{sector_type}{sector}R"
        for family in range(1, 6)
        for child in range(1, 3)
        for sector_type in ["D", "T"]
        for sector in range(1, 9)
    ]
    # Emil straight
    quadrupoles += ["QIT6R"]

    sextupoles = [
        f"S{family}M{sector_type}{sector}R"
        for family in range(1, 2)
        for sector_type in ["D", "T"]
        for sector in range(1, 9)
    ]
    sextupoles += [
        f"S{family}M{child}{sector_type}{sector}R"
        for family in range(2, 6)
        for child in range(1, 3)
        for sector_type in ["D", "T"]
        for sector in range(1, 9)
    ]
    horizontal_steerers = [
        f"H{sextupole}" for sextupole in sextupoles if sextupole[1] in ["1", "4"]
    ]
    vertical_steerers = [
        f"V{sextupole}" for sextupole in sextupoles if sextupole[1] in ["2", "3"]
    ]
    d = dict(
        quadrupoles=quadrupoles,
        sextupoles=sextupoles,
        horizontal_steerers=horizontal_steerers,
        vertical_steerers=vertical_steerers,
    )

    return d


class CompressedSequenceDumper(yaml.SafeDumper):
    def represent_sequence(self, tag, seq, flow_style=None):
        if len(seq) <= 12:  # threshold
            flow = True
        else:
            flow = False
        return super().represent_sequence(tag, seq, flow_style=flow)


@functools.lru_cache(maxsize=None)
def load_yaml_data_config(data_path: Tuple[str], module="dt4acc_lib"):
    t_file = files("dt4acc").joinpath(*(data_path))
    with open(t_file, "rt") as fp:
        obj = yaml.load(fp, yaml.SafeLoader)
    return obj


@functools.lru_cache(maxsize=None)
def get_magnet_info(data_path: Tuple[str], module="dt4acc_lib") -> Sequence[MagneticObject]:
    t_path = data_path + ("magnets.yaml",)
    return [MagneticObject(**d) for d in load_yaml_data_config(t_path)]


@functools.lru_cache(maxsize=None)
def get_pc_info(data_path: Tuple[str], module="dt4acc_lib") -> Sequence[PowerConverter]:
    t_path = data_path + ("power_converters.yaml",)
    return [PowerConverter(**d) for d in load_yaml_data_config(t_path)]


def create_yellow_pages_lut_from_config(data_path: Tuple[str]) -> Dict[str, Sequence[str]]:

    magnet_info = get_magnet_info(data_path)

    magnet_types = set([info.type for info in magnet_info])
    # check that standard names are there
    assert "quadrupole" in magnet_types
    assert "sextupole" in magnet_types

    magnet_families = set([tuple(info.family_member) for info in magnet_info])

    # I need this info for a check
    sextupoles = [m.elem_id for m in magnet_info if m.type == "sextupole"]

    # This info should be in the config ... family info
    # furthermore these steerer names should not really exist
    # they are all rather correction coils on sextupoles
    # there are some special ones that are air coils,
    # I do not address them here
    steerers = [m.elem_id for m in magnet_info if m.type == "steerer"]
    # All
    horizontal_steerers = [st[1:] for st in steerers if st.startswith("H")]
    vertical_steerers = [st[1:] for st in steerers if st.startswith("V")]

    horizontal_steerer_not_co_wound = [
        st  for st in horizontal_steerers if st not in sextupoles
    ]
    if horizontal_steerer_not_co_wound:
        logger.warning("Following horizontal steerers are not on sextupoles ? %s", horizontal_steerer_not_co_wound)
    vertical_steerer_not_co_wound = [
        st  for st in vertical_steerers if st not in sextupoles
    ]
    if vertical_steerer_not_co_wound:
        logger.warning("Following vertical steerers are not on sextupoles ? %s", vertical_steerer_not_co_wound)

    r = dict(
        horizontal_steerers=horizontal_steerers,
        vertical_steerers=vertical_steerers,
        steerers=steerers,
        quadrupoles=[m.elem_id for m in magnet_info if m.type == "quadrupole"],
        sextupoles=sextupoles,
        cavities=[f"CAVH{cnt:01d}T8R" for cnt  in range(1, 4+1)]
    )
    return r


def main():
    header_fmt = """# 
# BESSY II {data_type}: {date}
# WARNING: automatically generated data
#          please check when it is updated if you edit it by hand!
"""
    yp_fname = "bessyii_yellow_pages_lookup_table.yml"
    lm_inv_fname = "bessyii_liaison_manager_inverse_lookup_table.yml"
    lm_fwd_fname = "bessyii_liaison_manager_forward_lookup_table.yml"
    ts_fname = "bessyii_translation_service_lookup_table.yml"
    data_path = ("custom_facility", "bessyii", "resources", "storage_ring", "input")

    yp_lut = create_yellow_pages_lut_from_config(data_path=data_path)
    now = datetime.datetime.now()

    with open(yp_fname, "wt") as fp:
        fp.write(header_fmt.format(**dict(data_type="yellow pages", date=now)))
        yaml.dump(yp_lut, fp, Dumper=CompressedSequenceDumper)
        fp.write("# EOF\n")
    del yp_lut, fp

    with open(yp_fname, "rt") as fp:
        yp_lut = yaml.safe_load(fp)
    del fp
    yp = YellowPages(yp_lut)

    lut_fwd_, lut_inv_ = build_liaison_manager_lut(data_path=data_path, yp=yp)
    lut_fwd = LiaisonManagerForwardLookupTable(lut_fwd_)
    lut_inv = LiaisonManagerInverseLookupTable(lut_inv_)
    mismatched = lut_inv.non_unique_entries()
    if mismatched:
        print("Following items look up can be misleading!")
        pprint.pprint(mismatched)
        print(" ===========================================")

    del mismatched

    mismatched = lut_fwd.non_unique_entries()
    if mismatched:
        print("Following items look up can be misleading!")
        pprint.pprint(mismatched)
        print(" ===========================================")

    del mismatched

    with open(lm_inv_fname, "wt") as fp:
        fp.write(header_fmt.format(data_type="Liaison manager inverse table", date=now))
        yaml.dump(asdict(lut_inv), fp, Dumper=CompressedSequenceDumper)
        fp.write("# EOF\n")

    with open(lm_inv_fname, "rt") as fp:
        tmp = yaml.load(fp, Loader=yaml.SafeLoader)

    # verify that it gets reloaded
    lmt_inv = jsons.load(tmp, LiaisonManagerInverseLookupTable)
    lmt_inv.verify()

    with open(lm_fwd_fname, "wt") as fp:
        fp.write(header_fmt.format(data_type="Liaison manager forward table", date=now))
        yaml.dump(asdict(lut_fwd), fp, Dumper=CompressedSequenceDumper)
        fp.write("# EOF\n")
    del yp_lut

    with open(lm_fwd_fname, "rt") as fp:
        tmp = yaml.load(fp, Loader=yaml.SafeLoader)

    # verify that it gets reloaded
    lmt_fwd = jsons.load(tmp, LiaisonManagerForwardLookupTable)
    lmt_fwd.verify()

    tlut = TranslatorLookupTable(lut=build_translator_manager_lut(data_path=data_path, yp=yp, lm_inv=lmt_inv))

    with open(ts_fname, "wt") as fp:
        fp.write(header_fmt.format(**dict(data_type="Translation service table", date=now)))
        yaml.dump(asdict(tlut), fp, Dumper=CompressedSequenceDumper)
        fp.write("# EOF\n")
    del tlut


    with open(ts_fname, "rt") as fp:
        tmp = yaml.load(fp, Loader=yaml.SafeLoader)
    tlut = jsons.load(tmp, TranslatorLookupTable)
    tlut
    # pprint.pprint(tlut)


if __name__ == "__main__":
    main()