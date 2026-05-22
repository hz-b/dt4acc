import itertools
import os
import pprint
from collections import defaultdict
from pathlib import Path
from typing import Dict, Tuple, Sequence, List, Union

import numpy as np
import pandas as pd
import xarray as xr
from scipy.io import loadmat

from bact_mml_json_importer.data_model.mml_ao import FamilyInfoCollection
from dt4acc.custom_facility.als.hcm_coefficients import hcm_coefficients
from dt4acc.custom_facility.als.model import MMLStyleDeviceIdentifier, Monitor, Setpoint
from dt4acc.custom_facility.als.read_lattice import als_load_lattice, default_filename
from dt4acc.custom_facility.als.readin_ao import als_ring_ao_data
from dt4acc.custom_facility.als.vcm_coefficients import vcm_coefficients
from dt4acc_lib.bl.liaison_manager import LiaisonManager
from dt4acc_lib.bl.translator_service import TranslatorService
from dt4acc_lib.bl.yellow_pages import YellowPages
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
)
from interfaces.utils.translator_service import TranslatorServiceBase


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
    device_index = sel.get_device_list().index(dev_id.mml_device_index())
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
            bpm_name, = get_element_uuids_for_device(
                ao_table=ao_table, lat=lat, dev_id=dev_name
            )
            sel = ao_table[dev_name.family]
            device_index = sel.get_device_list().index(
                dev_name.mml_device_index()
            )
            mon_pv = sel.Monitor.ChannelNames[device_index].strip()
            lat_prop = LatticeElementPropertyID(element_name=bpm_name, property=property)
            forward_lut.append(
                LiaisonManagerForwardLookupElement(
                    lat_id=lat_prop,
                    dev_ids=[dev_prop]
                )
            )
            inverse_lut.append(
                LiaisonManagerInverseLookupElement(
                    dev_id=dev_prop,
                    lat_ids=[lat_prop],
                )
            )
            process_variable_views.append(
                Monitor(pv_name=mon_pv, rcmd=ReadCommand(id=dev_name, property=property), prec=3, record_type="ai", update="delayed")
            )
            pass

    for family_name, property in [
        # just to get started
        # Need to take care that process variables occur again!
        # For quads and sextupoles more than one variable is
        # in a line
        # ("QUAD", "main_strength"),
        # ("SEXT", "main_strength"),
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
            device_index = sel.get_device_list().index(
                dev_prop.device_name.mml_device_index()
            )

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
    return fwd, inv, process_variable_views


def create_translator_luts(
    yp: YellowPagesBase,
    lm: LiaisonManagerBase,
    ao_table: Dict[str, FamilyInfoCollection],
    lat,
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

    scale = ao_table["BPMx"].Monitor.Physics2HWParams
    assert isinstance(scale, float)
    # just one for all of them
    conv = PolynomCoefficients(coeffs=[0.0, scale], energy_dependent=False)
    for dev_name in yp.get("BPMx"):
        element_name, = get_element_uuids_for_device(
            ao_table=ao_table, lat=lat, dev_id=dev_name
        )
        src = LatticeElementPropertyID(element_name, "dx")
        dst, = lm.forward(src)

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
        element_name, = get_element_uuids_for_device(
            ao_table=ao_table, lat=lat, dev_id=dev_name
        )
        src = LatticeElementPropertyID(element_name, "dy")
        dst, = lm.forward(src)

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
        device_index = sel.get_device_list().index(src.device_name.mml_device_index())

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
        device_index = sel.get_device_list().index(src.device_name.mml_device_index())

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


def to_single_vector(data) -> Sequence[float]:
    t_data = data
    # Go down as long as the contained element
    # still contains only one element
    while True:
        try:
            l = len(t_data)
        except TypeError:
            return t_data

        if len(t_data) == 1:
            (t_data,) = t_data
        else:
            break
        dtype = t_data.dtype
        pass
    dtype = t_data.dtype
    return t_data


def unpack_ramp_data(data):
    while True:
        data = to_single_vector(data)
        dtype = data.dtype
        if isinstance(dtype, np.dtypes.VoidDType):
            d = {
                dtype_name: unpack_ramp_data(data[dtype_name])
                for dtype_name in data.dtype.fields.keys()
            }
            return d
            pass
        else:
            break
    return data


def numrec_array_to_dict(data):
    return


def load_ramp_data():
    path = (
        Path(os.environ["HOME"])
        / "Devel/github/matlab-middle-layer/machine/ALS//StorageRingOpsData/"
    )
    filename = path / "Model/alsrampup.mat"
    filename = path / "Greg/alsrampup.mat"
    data = loadmat(filename)
    ramp_data = data["RampTable"]

    d = {
        dtype_name: unpack_ramp_data(ramp_data[dtype_name])
        for dtype_name in ramp_data.dtype.fields.keys()
    }
    gev_as_coor = d.pop("GeV")
    d.pop("UpperLattice")
    d.pop("LowerLattice")

    d2 = {
        k: xr.DataArray(data=v["Setpoint"], dims="GeV", coords=[gev_as_coor])
        for k, v in d.items()
    }
    r = xr.Dataset(d2)
    return r

    df = pd.DataFrame(d)
    return data


def load_managers():
    """
    Todo:
        return yellow pages manager
    """
    # ramp_data = load_ramp_data()
    pass

    lat = als_load_lattice(default_filename)
    ao_model = als_ring_ao_data()

    yp = create_yellow_pages_input(ao_model, lat)
    yp

    fwd_lut, inv_lut, process_variable_views = create_liaison_lut(yp, ao_model, lat)
    lm = LiaisonManager(forward_lut=fwd_lut, inverse_lut=inv_lut)
    ts_lut = create_translator_luts(yp, lm, ao_model, lat)
    # Todo: get the brho of the storage ring
    ts = TranslatorService(lut=ts_lut, brho=4.5)
    ts
    yp = YellowPages
    return yp, lm, ts, process_variable_views


if __name__ == "__main__":
    load_managers()
