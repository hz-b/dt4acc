import itertools
import logging
from collections import defaultdict
from typing import Dict, Tuple, Sequence, List, Union

import numpy as np
import pandas as pd
import xarray as xr

from bact_mml_json_importer.data_model.mml_ao import FamilyInfoCollection

from dt4acc.custom_facility.als.hcm_coefficients import hcm_coefficients
from dt4acc.custom_facility.als.model import MMLStyleDeviceIdentifier, Monitor, Setpoint
from dt4acc.custom_facility.als.read_lattice import (
    als_load_lattice,
    default_filename,
    default_energy,
)
from dt4acc.custom_facility.als.readin_ao import als_ring_ao_data, load_ramp_data
from dt4acc.custom_facility.als.vcm_coefficients import vcm_coefficients
from dt4acc_lib.bl.liaison_manager import LiaisonManager
from dt4acc_lib.bl.translator_service import TranslatorService
from dt4acc_lib.bl.yellow_pages import YellowPages
from dt4acc_lib.bl.unit_conversion import calculate_brho
from dt4acc_lib.interfaces.utils.liaison_manager import LiaisonManagerBase
from dt4acc_lib.interfaces.utils.yellow_pages import YellowPagesBase
from dt4acc_lib.model.utils.command import ReadCommand
from dt4acc_lib.model.utils.identifiers import (
    DevicePropertyID,
    LatticeElementPropertyID,
    ConversionID,
)
from dt4acc_lib.model.utils.liaison_manager_lookup_table import (
    LiaisonManagerInverseLookupTable,
    LiaisonManagerForwardLookupTable,
    LiaisonManagerForwardLookupElement,
    LiaisonManagerInverseLookupElement,
)
from dt4acc_lib.model.utils.translator_manager_lookup_table import (
    TranslatorLookupTable,
    TranslatorLookupTableElement,
    PolynomCoefficients,
    IdentityMapper,
    MultiplyerScaledByEnergy,
    Range,
    CurvePoint,
)

logger = logging.getLogger("dt4acc")


def uuids_of_at_elements(
    elements: Sequence,
    family_name: str,
    indices: Sequence[int],
    alternative_family_names: Sequence[str] = [],
) -> Sequence[str]:
    """Returns uuids of the lattice elments whose index is found at ATIndex

    Checks that the stored AT element index points to an AT element with expected family name

    Todo:
        separate responsibility

        build the names here
        check that its points to the correct place in the lattice
        at a second step

    """
    indices = np.asarray(indices)
    assert np.all(indices > 0)
    indices = indices - 1
    names = [elements[idx].UUID for idx in indices]

    for cnt, tmp in enumerate(zip(indices, names)):
        idx, name = tmp
        if not name.startswith(family_name):
            for alternate in alternative_family_names:
                if name.startswith(alternate):
                    break
            else:
                raise ValueError(
                    f"family {family_name}: element no {cnt} at index {idx} name {name} not cohereent to family name"
                )
    return names


def extract_family_member_names(
    lat,
    ao_table: Dict[str, FamilyInfoCollection],
    family_name: str,
    alternative_family_names: Sequence[str] = None,
) -> Sequence[str]:
    alternative_family_names = alternative_family_names or []
    indices = ao_table[family_name].AT.get_element_indices()
    dev_list = ao_table[family_name].get_device_list()

    assert len(indices) == len(
        dev_list
    ), f"Check failed for family {family_name} n indices = {len(indices)}, n devs = {len(dev_list)}"

    uuids_of_at_elements(
        lat,
        family_name,
        list(itertools.chain.from_iterable(indices)),
        alternative_family_names=alternative_family_names,
    )
    identifiers = [
        MMLStyleDeviceIdentifier(
            family=family_name, sector=int(sector), child=int(child)
        )
        for sector, child in dev_list
    ]
    return identifiers


standard_ao_families = dict(
    focusing_quadrupoles="QF",
    defocusing_quadrupoles="QD",
    horizontal_steerers="HCM",
    vertical_steerers="VCM",
    quadrupoles="QUAD",
)


def create_yellow_pages_input(
    ao_table: Dict[str, FamilyInfoCollection], lat
) -> Dict[str, Sequence[str]]:
    """

    Todo:
        use standard family names?

    """
    standard_families = [
        "QF",
        "QD",
        "SF",
        "SD",
        "SHF",
        "SHD",
        "QFA",
        "QDA",
        "BPM",
    ]
    names = {
        fam: extract_family_member_names(lat, ao_table, fam)
        for fam in standard_families
    }

    names["BPMx"] = extract_family_member_names(
        lat, ao_table, "BPMx", alternative_family_names=["BPM"]
    )
    names["BPMy"] = extract_family_member_names(
        lat, ao_table, "BPMy", alternative_family_names=["BPM"]
    )

    names["BEND"] = extract_family_member_names(
        lat, ao_table, "BEND", alternative_family_names=["BS"]
    )
    names["HCM"] = extract_family_member_names(
        lat, ao_table, "HCM", alternative_family_names=["COR"]
    )
    names["VCM"] = extract_family_member_names(
        lat, ao_table, "VCM", alternative_family_names=["COR"]
    )

    # what are these ?
    names["BSC"] = extract_family_member_names(
        lat, ao_table, "BSC", alternative_family_names=["BS"]
    )
    names["SQSF"] = extract_family_member_names(
        lat, ao_table, "SQSF", alternative_family_names=["SFF"]
    )
    names["SQSD"] = extract_family_member_names(
        lat, ao_table, "SQSD", alternative_family_names=["SDD"]
    )

    names["RF"] = extract_family_member_names(
        lat, ao_table, "RF", alternative_family_names=["CAV"]
    )
    defocusing_quads = extract_family_member_names(lat, ao_table, "QD")
    # dict(quadrupoles=)

    # now build the yellow pages using member of
    # here one item can belong to more than one family
    yp_dict = defaultdict(list)

    # always there
    yp_dict["master_clock"] = ["master_clock"]

    for ref_fam_name, family_members in names.items():
        # These should be rather tags, and always a sequence!
        members_of = ao_table[ref_fam_name].member_of()
        for family_name in members_of:
            yp_dict[str(family_name)].extend(family_members)

    # print("names sorted to reference families")
    # pprint.pprint(names, compact=True)

    # print("families (rather tags)")
    # pprint.pprint(yp_dict, compact=True)
    # print(f"Total number of elements {np.sum([len(v) for v in names.values()])}")
    # print("Families not exported to yp:", set(tuple(ao_table)).difference(tuple(names)))

    return dict(yp_dict)


def get_element_uuids_for_device(
    ao_table, lat, dev_id: MMLStyleDeviceIdentifier
) -> Sequence[str]:
    sel = ao_table[dev_id.family]
    device_index = sel.get_device_index(*dev_id.mml_device_index())
    lattice_element_indices = np.asarray(sel.AT.get_element_indices()[device_index])
    assert (lattice_element_indices > 1).all()
    uuid = [elem.UUID for elem in lat[lattice_element_indices - 1]]
    return uuid


def create_liaison_lut(
    yp: YellowPagesBase, ao_table: Dict[str, FamilyInfoCollection], lat
) -> Tuple[
    LiaisonManagerForwardLookupTable,
    LiaisonManagerInverseLookupTable,
    Sequence[Union[Monitor, Setpoint]],
]:
    forward_lut = []
    inverse_lut = []
    process_variable_views: List[Union[Monitor, Setpoint]] = []

    # Here one than more quadrupole or pv maps to one magnet
    # so collect them first before building the elements
    inv_lut_tmp = defaultdict(list)
    for family_name, property in [
        ("QUAD", "main_strength"),
        ("SEXT", "main_strength"),
        ]:
        for dev_name in yp.get(family_name):
            # expect only one for forward but more than one for backward
            dev_prop = DevicePropertyID(device_name=dev_name, property=property)
            element_names = get_element_uuids_for_device(
                ao_table=ao_table, lat=lat, dev_id=dev_name
            )
            elem_props = [
                LatticeElementPropertyID(element_name=name, property=property)
                for name in element_names
            ]

            # for elm_prop in elem_props:
            #    forward_lut.append(LiaisonManagerForwardLookupElement(lat_id=elm_prop, dev_ids=[dev_prop]))
            inv_lut_tmp[dev_prop].append(elem_props)

            rcmd = ReadCommand(id=dev_name, property="set_current")
            sel = ao_table[dev_prop.device_name.family]
            device_index = sel.get_device_index(*dev_prop.device_name.mml_device_index())

            mon_pv = sel.Monitor.ChannelNames[device_index].strip()
            set_pv = sel.Setpoint.ChannelNames[device_index].strip()

            # where it starts to call
            mon_prop = DevicePropertyID(device_name=mon_pv, property="read_current")
            setp_prop = DevicePropertyID(device_name=set_pv, property="set_current")

            for elm_prop in elem_props:
                forward_lut.append(
                    LiaisonManagerForwardLookupElement(
                        lat_id=elm_prop, dev_ids=[mon_prop]
                    )
                )
                # forward_lut.append(LiaisonManagerForwardLookupElement(lat_id=elm_prop, dev_ids=[setp_prop]))
            inv_lut_tmp[mon_prop].append(elem_props)
            inv_lut_tmp[setp_prop].append(elem_props)

            monitor = Monitor(pv_name=mon_pv, rcmd=rcmd, prec=3, record_type="ai")
            setp = Setpoint(
                pv_name=set_pv,
                rcmd=rcmd,
                prec=3,
                record_type="ao",
                reads=[monitor.rcmd],
            )
            process_variable_views.extend([monitor, setp])

    # now work on the inv_lut_tmp and stretch it out
    tmp = [
        LiaisonManagerInverseLookupElement(
            dev_id=dev_id,
            lat_ids=list(itertools.chain.from_iterable(lat_ids))
        )
        for dev_id, lat_ids in inv_lut_tmp.items()
    ]
    inverse_lut.extend(tmp)
    del tmp
    del inv_lut_tmp


    # BPMs are not directly handled within in translating
    # mexec engine (yet)
    # but the view can use this information
    for family_name, property in [
        ("BPMx", "dx"),
        ("BPMy", "dy"),
    ]:
        for dev_name in yp.get(family_name):
            # expect only one
            dev_prop = DevicePropertyID(device_name=dev_name, property=property)
            (bpm_name,) = get_element_uuids_for_device(
                ao_table=ao_table, lat=lat, dev_id=dev_name
            )
            sel = ao_table[dev_name.family]
            device_index = sel.get_device_index(*dev_name.mml_device_index())
            mon_pv = sel.Monitor.ChannelNames[device_index].strip()
            lat_prop = LatticeElementPropertyID(
                element_name=bpm_name, property=property
            )
            forward_lut.append(
                LiaisonManagerForwardLookupElement(lat_id=lat_prop, dev_ids=[dev_prop])
            )
            inverse_lut.append(
                LiaisonManagerInverseLookupElement(
                    dev_id=dev_prop,
                    lat_ids=[lat_prop],
                )
            )
            process_variable_views.append(
                Monitor(
                    pv_name=mon_pv,
                    rcmd=ReadCommand(id=dev_name, property=property),
                    prec=3,
                    record_type="ai",
                    update="delayed",
                )
            )
            pass

    for family_name, property in [
        # just to get started
        # Need to take care that process variables occur again!
        # For quads and sextupoles more than one variable is
        # in a line
        ("HCM", "x_kick"),
        ("VCM", "y_kick"),
    ]:
        for corr in yp.get(family_name):
            # As if you could set current to a magnet
            dev_prop = DevicePropertyID(device_name=corr, property="set_current")

            element_names = get_element_uuids_for_device(
                ao_table=ao_table, lat=lat, dev_id=corr
            )
            elem_props = [
                LatticeElementPropertyID(element_name=name, property=property)
                for name in element_names
            ]

            # for elm_prop in elem_props:
            #    forward_lut.append(LiaisonManagerForwardLookupElement(lat_id=elm_prop, dev_ids=[dev_prop]))
            inverse_lut.append(
                LiaisonManagerInverseLookupElement(dev_id=dev_prop, lat_ids=elem_props)
            )

            rcmd = ReadCommand(id=corr, property="set_current")
            sel = ao_table[dev_prop.device_name.family]
            device_index = sel.get_device_index(*dev_prop.device_name.mml_device_index())

            mon_pv = sel.Monitor.ChannelNames[device_index].strip()
            set_pv = sel.Setpoint.ChannelNames[device_index].strip()

            # where it starts to call
            mon_prop = DevicePropertyID(device_name=mon_pv, property="read_current")
            setp_prop = DevicePropertyID(device_name=set_pv, property="set_current")

            for elm_prop in elem_props:
                forward_lut.append(
                    LiaisonManagerForwardLookupElement(
                        lat_id=elm_prop, dev_ids=[mon_prop]
                    )
                )
                # forward_lut.append(LiaisonManagerForwardLookupElement(lat_id=elm_prop, dev_ids=[setp_prop]))
            inverse_lut.append(
                LiaisonManagerInverseLookupElement(dev_id=mon_prop, lat_ids=elem_props)
            )
            inverse_lut.append(
                LiaisonManagerInverseLookupElement(dev_id=setp_prop, lat_ids=elem_props)
            )

            monitor = Monitor(pv_name=mon_pv, rcmd=rcmd, prec=3, record_type="ai")
            setp = Setpoint(
                pv_name=set_pv,
                rcmd=rcmd,
                prec=3,
                record_type="ao",
                reads=[monitor.rcmd],
            )
            process_variable_views.extend([monitor, setp])
            pass

    # master clock defines frequency of cavity
    for cav in yp.get("RF"):
        dev_prop = DevicePropertyID(device_name=cav, property="frequency")
        dev_prop_mc = DevicePropertyID(
            device_name="master_clock", property="reference_frequency"
        )
        element_names = get_element_uuids_for_device(
            ao_table=ao_table, lat=lat, dev_id=cav
        )
        elem_props = [
            LatticeElementPropertyID(element_name=name, property="frequency")
            for name in element_names
        ]

        for elm_prop in elem_props:
            # forward_lut.append(LiaisonManagerForwardLookupElement(lat_id=elm_prop, dev_ids=[dev_prop]))
            forward_lut.append(
                LiaisonManagerForwardLookupElement(
                    lat_id=elm_prop, dev_ids=[dev_prop_mc]
                )
            )
        # inverse_lut.append(LiaisonManagerInverseLookupElement(dev_id=dev_prop, lat_ids=elem_props))
        inverse_lut.append(
            LiaisonManagerInverseLookupElement(dev_id=dev_prop_mc, lat_ids=elem_props)
        )

    inverse_lut += [
        LiaisonManagerInverseLookupElement(
            dev_id=DevicePropertyID(device_name="twiss", property="parameters"),
            lat_ids=[
                LatticeElementPropertyID(element_name="twiss", property="parameters")
            ],
        ),
        LiaisonManagerInverseLookupElement(
            dev_id=DevicePropertyID(device_name="track", property="pos"),
            lat_ids=[LatticeElementPropertyID(element_name="track", property="pos")],
        ),
    ]
    forward_lut += [
        LiaisonManagerForwardLookupElement(
            lat_id=LatticeElementPropertyID(
                element_name="twiss", property="parameters"
            ),
            dev_ids=[DevicePropertyID(device_name="twiss", property="parameters")],
        ),
        LiaisonManagerForwardLookupElement(
            lat_id=LatticeElementPropertyID(element_name="track", property="pos"),
            dev_ids=[DevicePropertyID(device_name="track", property="pos")],
        ),
    ]

    fwd = LiaisonManagerForwardLookupTable(forward_lut)
    inv = LiaisonManagerInverseLookupTable(inverse_lut)
    fwd.verify()
    inv.verify()
    # what's the better way: this would be explicit
    assert not inv.non_unique_entries()
    return fwd, inv, process_variable_views


def create_translator_luts(
    yp: YellowPagesBase,
    lm: LiaisonManagerBase,
    ao_table: Dict[str, FamilyInfoCollection],
    ramp_data: Dict[str, xr.Dataset],
    lat,
    reference_energy,
) -> TranslatorLookupTable:
    translator_lut: List[TranslatorLookupTableElement] = []

    # for dev_name in yp.get("RF"):
    dev_name = "master_clock"
    d = lm.objects_for_device(dev_name=dev_name)
    (src,) = d
    assert src.device_name == dev_name
    (tmp,) = d.values()
    (tgt,) = tmp

    translator_lut.append(
        TranslatorLookupTableElement(
            conversion_id=ConversionID(tgt, src),
            # As cavities are treated differently from magnets
            # energy is a property of the beam as well as the
            # energy of the reference particle
            #
            # "design energy" is what belongs to the lattice ant its
            # design!
            conversion_info=PolynomCoefficients(
                coeffs=[0.0, 1.0], energy_dependent=False
            ),
        )
    )
    del d, src, tgt, tmp, dev_name

    # now to the energy dependent part: main magnets
    for family_name in "QF", "QD", "SF", "SD", "SHF", "SHD":
        ao_view = ao_table[family_name]
        try:
            t_ramp_data = ramp_data[family_name]
        except KeyError:
            logger.info(f"{family_name} has no ramp data, thus not adding translation for this family")
            continue
        for dev_name in yp.get(family_name):
            # Todo: change to this interface as soon as it is available
            # dev_idx = ao_table[family_name].get_device_index(sector=dev_name.sector, child=dev_name.child)
            dev_idx = ao_view.DeviceList.index((dev_name.sector, dev_name.child))
            range = ao_view.Setpoint.Range[dev_idx]
            assert ao_view.Setpoint.HW2PhysicsParams is None

            range = t_ramp_data.range.sel(sector=dev_name.sector, child=dev_name.child)

            d = lm.objects_for_device(dev_name=dev_name)
            (src,) = d
            assert src.device_name == dev_name

            # Need to understand why I get that many ...
            targets, = d.values()

            for tgt in targets:
                # Need to understand why its a lost
                conv = MultiplyerScaledByEnergy(
                    reference_multiplyer=float(
                        t_ramp_data.physics.sel(sector=dev_name.sector, child=dev_name.child)
                    ),
                    reference_energy=reference_energy,
                    range=Range(min=float(range[0]), max=float(range[1])),
                    scale_by_energy=[
                        CurvePoint(float(indep), float(dep))
                        for indep, dep in zip(
                            t_ramp_data.reference_energy, t_ramp_data.setpoint
                        )
                    ],
                )

                translator_lut.append(
                    TranslatorLookupTableElement(
                        conversion_id=ConversionID(tgt, src),
                        conversion_info=conv,
                    )
                )

    scale = ao_table["BPMx"].Monitor.Physics2HWParams
    assert isinstance(scale, float)
    # just one for all of them
    conv = PolynomCoefficients(coeffs=[0.0, scale], energy_dependent=False)
    for dev_name in yp.get("BPMx"):
        (element_name,) = get_element_uuids_for_device(
            ao_table=ao_table, lat=lat, dev_id=dev_name
        )
        src = LatticeElementPropertyID(element_name, "dx")
        (dst,) = lm.forward(src)

        translator_lut.append(
            TranslatorLookupTableElement(
                conversion_id=ConversionID(src, dst),
                conversion_info=conv,
            )
        )

    scale = ao_table["BPMy"].Monitor.Physics2HWParams
    assert isinstance(scale, float)
    # just one for all of them
    conv = PolynomCoefficients(coeffs=[0.0, scale], energy_dependent=False)
    for dev_name in yp.get("BPMy"):
        (element_name,) = get_element_uuids_for_device(
            ao_table=ao_table, lat=lat, dev_id=dev_name
        )
        src = LatticeElementPropertyID(element_name, "dy")
        (dst,) = lm.forward(src)

        translator_lut.append(
            TranslatorLookupTableElement(
                conversion_id=ConversionID(src, dst),
                conversion_info=conv,
            )
        )

    for dev_name in yp.get("HCM"):
        d = lm.objects_for_device(dev_name=dev_name)
        (src,) = d
        assert src.device_name == dev_name
        (tmp,) = d.values()
        (tgt,) = tmp
        coeffs = hcm_coefficients(src.device_name.mml_device_index())

        sel = ao_table[src.device_name.family]
        device_index = sel.get_device_index(*src.device_name.mml_device_index())

        mon_pv = sel.Monitor.ChannelNames[device_index].strip()
        set_pv = sel.Setpoint.ChannelNames[device_index].strip()

        # where it starts to call
        mon_prop = DevicePropertyID(device_name=mon_pv, property="read_current")
        setp_prop = DevicePropertyID(device_name=set_pv, property="set_current")

        # Need to check if that is the correct coefficient
        # For now I assume it returns a scale factor for k and B
        conv = PolynomCoefficients(coeffs=[0.0, coeffs[0]], energy_dependent=True)
        translator_lut.append(
            TranslatorLookupTableElement(
                conversion_id=ConversionID(tgt, src),
                conversion_info=conv,
            )
        )
        # Todo: this should be more automatic
        translator_lut.append(
            TranslatorLookupTableElement(
                conversion_id=ConversionID(
                    tgt,
                    DevicePropertyID(
                        device_name=src.device_name, property="read_current"
                    ),
                ),
                conversion_info=conv,
            )
        )

        translator_lut.append(
            TranslatorLookupTableElement(
                conversion_id=ConversionID(tgt, mon_prop), conversion_info=conv
            )
        )
        translator_lut.append(
            TranslatorLookupTableElement(
                conversion_id=ConversionID(tgt, setp_prop), conversion_info=conv
            )
        )
        pass

    for dev_name in yp.get("VCM"):

        d = lm.objects_for_device(dev_name=dev_name)
        (src,) = d
        assert src.device_name == dev_name
        (tmp,) = d.values()
        (tgt,) = tmp

        coeffs = vcm_coefficients(src.device_name.mml_device_index())
        # Need to check if that is the correct coefficient
        conv = PolynomCoefficients(coeffs=[0.0, coeffs[0]], energy_dependent=True)
        translator_lut.append(
            TranslatorLookupTableElement(
                conversion_id=ConversionID(tgt, src), conversion_info=conv
            )
        )
        translator_lut.append(
            TranslatorLookupTableElement(
                conversion_id=ConversionID(
                    tgt,
                    DevicePropertyID(
                        device_name=src.device_name, property="read_current"
                    ),
                ),
                conversion_info=conv,
            )
        )

        sel = ao_table[src.device_name.family]
        device_index = sel.get_device_index(*src.device_name.mml_device_index())

        mon_pv = sel.Monitor.ChannelNames[device_index].strip()
        set_pv = sel.Setpoint.ChannelNames[device_index].strip()

        # where it starts to call
        mon_prop = DevicePropertyID(device_name=mon_pv, property="read_current")
        setp_prop = DevicePropertyID(device_name=set_pv, property="set_current")

        translator_lut.append(
            TranslatorLookupTableElement(
                conversion_id=ConversionID(tgt, mon_prop), conversion_info=conv
            )
        )
        translator_lut.append(
            TranslatorLookupTableElement(
                conversion_id=ConversionID(tgt, setp_prop), conversion_info=conv
            )
        )
        pass

    translator_lut.extend(
        [
            TranslatorLookupTableElement(
                ConversionID(
                    LatticeElementPropertyID(
                        element_name="twiss", property="parameters"
                    ),
                    DevicePropertyID(device_name="twiss", property="parameters"),
                ),
                IdentityMapper(),
            ),
            TranslatorLookupTableElement(
                ConversionID(
                    LatticeElementPropertyID(element_name="track", property="pos"),
                    DevicePropertyID(device_name="track", property="pos"),
                ),
                IdentityMapper(),
            ),
        ]
    )

    # for dev_name in yp.get("QUAD"):
    #     d = lm.objects_for_device(dev_name=dev_name)
    #     src, = d
    #     assert src.device_name == dev_name
    #     tmp, = d.values()
    #     tgt, = tmp
    #
    # for dev_name in yp.get("SEXT"):
    #    d = lm.objects_for_device(dev_name=dev_name)
    #     # needs to be implemented

    r = TranslatorLookupTable(lut=translator_lut)
    r.verify()
    return r


def load_managers():
    """
    Todo:
        return yellow pages manager
    """
    pass

    lat = als_load_lattice(default_filename)
    ao_model = als_ring_ao_data()
    ramp_data = load_ramp_data(ao_model)

    yp = create_yellow_pages_input(ao_model, lat)
    yp

    fwd_lut, inv_lut, process_variable_views = create_liaison_lut(yp, ao_model, lat)
    lm = LiaisonManager(forward_lut=fwd_lut, inverse_lut=inv_lut)
    ts_lut = create_translator_luts(
        yp, lm, ao_model, ramp_data, lat, reference_energy=default_energy
    )

    # Todo: get the brho of the storage ring
    ts = TranslatorService(lut=ts_lut, brho=4.5)
    ts
    yp = YellowPages
    return yp, lm, ts, process_variable_views


if __name__ == "__main__":
    load_managers()
