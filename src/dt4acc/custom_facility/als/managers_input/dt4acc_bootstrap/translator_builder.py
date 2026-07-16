from __future__ import annotations

import logging
import math
from typing import Dict, List

import xarray as xr

from bact_mml_json_importer.data_model.mml_ao import FamilyInfoCollection
from dt4acc.custom_facility.als.hcm_coefficients import hcm_coefficients
from dt4acc.custom_facility.als.model import MMLStyleDeviceIdentifier
from dt4acc.custom_facility.als.vcm_coefficients import vcm_coefficients
from dt4acc_lib.interfaces.utils.liaison_manager import LiaisonManagerBase
from dt4acc_lib.interfaces.utils.yellow_pages import YellowPagesBase
from dt4acc_lib.model.utils.command import ReadCommand
from dt4acc_lib.model.utils.identifiers import ConversionID, DevicePropertyID, LatticeElementPropertyID
from dt4acc_lib.model.utils.translator_manager_lookup_table import (
    CurvePoint,
    IdentityMapper,
    MultiplyerScaledByEnergy,
    NeedsAReference,
    PolynomCoefficients,
    Range,
    TranslatorLookupTable,
    TranslatorLookupTableElement,
    TuneConversionCoefficients,
    RemapIdentifiersAndConvertDM,
)

logger = logging.getLogger("dt4acc")


def create_translator_luts(yp: YellowPagesBase, lm: LiaisonManagerBase, ao_table: Dict[str, FamilyInfoCollection], ramp_data: Dict[str, xr.Dataset], lat, mappings, reference_energy) -> TranslatorLookupTable:
    tl_ext_lut = create_translator_lut_for_turn_by_turn(mappings)
    tl_lut = _create_translator_luts(yp, lm, ao_table, ramp_data, lat, reference_energy)
    tl = TranslatorLookupTable(lut=list(tl_lut) + tl_ext_lut)
    tl.verify()
    return tl


def create_translator_lut_for_turn_by_turn(mappings) -> List[TranslatorLookupTableElement]:
    """Turn by turn data: need to rewrite the names of the table
    """
    return [
        TranslatorLookupTableElement(
            ConversionID(
                LatticeElementPropertyID(element_name="turn_by_turn", property="pos"),
                DevicePropertyID(device_name="turn_by_turn", property="pos")
            ),
            RemapIdentifiersAndConvertDM(
                name_mapping=mappings["turn_by_turn"],
                conversion=PolynomCoefficients(coeffs=[0, 1], energy_dependent=False),
            )
        )
    ]


def _create_translator_luts(yp: YellowPagesBase, lm: LiaisonManagerBase, ao_table: Dict[str, FamilyInfoCollection],
                            ramp_data: Dict[str, xr.Dataset], lat, reference_energy) -> List[TranslatorLookupTableElement]:
    """ What has been here before
    """
    translator_lut: List[TranslatorLookupTableElement] = []

    dev_name = "master_clock"
    d = lm.objects_for_device(dev_name=dev_name)
    for src, tmp in d.items():
        assert src.device_name == dev_name
        (tgt,) = tmp
        translator_lut.append(
            TranslatorLookupTableElement(
                conversion_id=ConversionID(tgt, src),
                conversion_info=PolynomCoefficients(coeffs=[0.0, 1.0], energy_dependent=False),
            )
        )

    for family_name in ("SHF", "SHD"):
        _ = ao_table[family_name]

    for family_name in ("QF", "QFA", "QD", "QDA", "SF", "SD"):
        ao_view = ao_table[family_name]
        t_ramp_data = ramp_data[family_name]
        scale_by_energy = [CurvePoint(float(indep) * 1e9, float(dep)) for indep, dep in zip(t_ramp_data.reference_energy, t_ramp_data.setpoint)]

        for device_index in ao_view.get_device_list():
            dev_idx = ao_view.get_device_index(*device_index)
            hw_range = ao_view.Setpoint.Range[dev_idx]
            assert ao_view.Setpoint.HW2PhysicsParams is None
            sector, child = device_index
            hw_range = t_ramp_data.range.sel(sector=sector, child=child)

            setp_pv = ao_view.Setpoint.ChannelNames[dev_idx].strip()
            mon_pv = ao_view.Monitor.ChannelNames[dev_idx].strip()

            src = DevicePropertyID(setp_pv, "set_current")
            delta_src = DevicePropertyID(setp_pv, "delta_set_current")
            targets = lm.inverse(src)
            delta_targets = lm.inverse(delta_src)
            assert targets, delta_targets
            assert len(targets) == len(delta_targets)

            for tgt, d_tgt in zip(targets, delta_targets):
                conv = MultiplyerScaledByEnergy(
                    reference_multiplyer=float(t_ramp_data.physics.sel(sector=sector, child=child)),
                    reference_energy=reference_energy,
                    range=Range(min=float(hw_range[0]), max=float(hw_range[1])),
                    scale_by_energy=scale_by_energy,
                )
                need_a_ref = NeedsAReference(
                    design_view_read_commnd=ReadCommand(tgt.element_name, tgt.property),
                    device_view_read_command=ReadCommand(src.device_name, src.property),
                    translation_object=conv,
                )
                translator_lut.append(TranslatorLookupTableElement(conversion_id=ConversionID(tgt, src), conversion_info=conv))
                translator_lut.append(TranslatorLookupTableElement(conversion_id=ConversionID(tgt, DevicePropertyID(device_name=setp_pv, property="set_current")), conversion_info=conv))
                translator_lut.append(TranslatorLookupTableElement(conversion_id=ConversionID(d_tgt, DevicePropertyID(device_name=setp_pv, property="delta_set_current")), conversion_info=need_a_ref))
                translator_lut.append(TranslatorLookupTableElement(conversion_id=ConversionID(tgt, DevicePropertyID(device_name=mon_pv, property="read_current")), conversion_info=conv))
                translator_lut.append(TranslatorLookupTableElement(conversion_id=ConversionID(d_tgt, DevicePropertyID(device_name=mon_pv, property="delta_read_current")), conversion_info=need_a_ref))

    for family_name, property_name in [("BPMx", "dx"), ("BPMy", "dy")]:
        ao_view = ao_table[family_name]
        scale = ao_view.Monitor.Physics2HWParams
        assert isinstance(scale, float)
        assert math.isclose(scale, 1.0 / ao_view.Monitor.HW2PhysicsParams)

        for dev_name in yp.get(family_name):
            (element_name,) = _get_element_uuids_for_device(ao_table=ao_table, lat=lat, dev_id=dev_name)
            src = LatticeElementPropertyID(element_name, property_name)
            (dst,) = lm.forward(src)
            offset = ao_view.Offset[ao_view.get_device_index(*dev_name.mml_device_index())]
            conv = PolynomCoefficients(coeffs=[offset, scale], energy_dependent=False)
            translator_lut.append(TranslatorLookupTableElement(conversion_id=ConversionID(src, dst), conversion_info=conv))

    for family_name, coeff_retrieval in [("HCM", hcm_coefficients), ("VCM", vcm_coefficients)]:
        for dev_name in yp.get(family_name):
            d = lm.objects_for_device(dev_name=dev_name)
            for src, targets in d.items():
                assert src.device_name == dev_name
                (tgt,) = targets
                coeffs = coeff_retrieval(src.device_name.mml_device_index())
                sel = ao_table[src.device_name.family]
                device_index = sel.get_device_index(*src.device_name.mml_device_index())
                mon_pv = sel.Monitor.ChannelNames[device_index].strip()
                set_pv = sel.Setpoint.ChannelNames[device_index].strip()
                mon_prop = DevicePropertyID(device_name=mon_pv, property="read_current")
                setp_prop = DevicePropertyID(device_name=set_pv, property="set_current")
                assert not math.isclose(coeffs[0], 0.0, abs_tol=1e-12)
                conv = PolynomCoefficients(coeffs=[0.0, 1.0 / coeffs[0]], energy_dependent=True)
                translator_lut.append(TranslatorLookupTableElement(conversion_id=ConversionID(tgt, src), conversion_info=conv))
                translator_lut.append(TranslatorLookupTableElement(conversion_id=ConversionID(tgt, DevicePropertyID(device_name=src.device_name, property="read_current")), conversion_info=conv))
                translator_lut.append(TranslatorLookupTableElement(conversion_id=ConversionID(tgt, mon_prop), conversion_info=conv))
                translator_lut.append(TranslatorLookupTableElement(conversion_id=ConversionID(tgt, setp_prop), conversion_info=conv))

    translator_lut.extend([
        TranslatorLookupTableElement(ConversionID(LatticeElementPropertyID(element_name="twiss", property="parameters"), DevicePropertyID(device_name="twiss", property="parameters")), IdentityMapper()),
        TranslatorLookupTableElement(ConversionID(LatticeElementPropertyID(element_name="track", property="pos"), DevicePropertyID(device_name="track", property="pos")), IdentityMapper()),
    ])

    floquet_to_frequency = 500e3 / 328
    translator_lut.append(
        TranslatorLookupTableElement(
            ConversionID(
                lattice_property_id=LatticeElementPropertyID(element_name="tune", property="transversal"),
                device_property_id=DevicePropertyID(device_name="tune", property="delta_set_current"),
            ),
            TuneConversionCoefficients(PolynomCoefficients([0e0, floquet_to_frequency], energy_dependent=False)),
        )
    )
    translator_lut += [
        TranslatorLookupTableElement(ConversionID(LatticeElementPropertyID(element_name="tune", property="transversal"), DevicePropertyID(device_name="tune", property="transversal")), TuneConversionCoefficients(PolynomCoefficients([0e0, floquet_to_frequency], energy_dependent=False))),
        TranslatorLookupTableElement(ConversionID(LatticeElementPropertyID(element_name="turn_by_turn_start", property="start"), DevicePropertyID(device_name="turn_by_turn_start", property="start")), IdentityMapper()),
        TranslatorLookupTableElement(ConversionID(LatticeElementPropertyID(element_name="turn_by_turn_start", property="n_turns"), DevicePropertyID(device_name="turn_by_turn_start", property="n_turns")), IdentityMapper()),
        TranslatorLookupTableElement(ConversionID(LatticeElementPropertyID(element_name="turn_by_turn_start", property="data_needed_at"), DevicePropertyID(device_name="turn_by_turn_start", property="data_needed_at")), IdentityMapper()),
        TranslatorLookupTableElement(ConversionID(LatticeElementPropertyID(element_name="turn_by_turn_start", property="p0"), DevicePropertyID(device_name="turn_by_turn_start", property="p0")), IdentityMapper()),
    ]

    return translator_lut


def _get_element_uuids_for_device(ao_table, lat, dev_id):
    sel = ao_table[dev_id.family]
    device_index = sel.get_device_index(*dev_id.mml_device_index())
    lattice_element_indices = __import__("numpy").asarray(sel.AT.get_element_indices()[device_index])
    assert (lattice_element_indices > 1).all()
    return [elem.UUID for elem in lat[lattice_element_indices - 1]]
