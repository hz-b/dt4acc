from __future__ import annotations

import itertools
import logging
from collections import defaultdict
from typing import Dict, List, Sequence, Tuple, Union

import numpy as np
import pydantic

from bact_mml_json_importer.data_model.mml_ao import FamilyInfoCollection
from dt4acc.core.model.view import Monitor, Setpoint
from dt4acc.custom_facility.als.model import MMLStyleDeviceIdentifier
from dt4acc_lib.interfaces.utils.yellow_pages import YellowPagesBase
from dt4acc_lib.model.utils.command import ReadCommand
from dt4acc_lib.model.utils.identifiers import DevicePropertyID, LatticeElementPropertyID
from dt4acc_lib.model.utils.liaison_manager_lookup_table import (
    LiaisonManagerForwardLookupElement,
    LiaisonManagerForwardLookupTable,
    LiaisonManagerInverseLookupElement,
    LiaisonManagerInverseLookupTable,
)

logger = logging.getLogger("dt4acc")


def get_element_uuids_for_device(ao_table, lat, dev_id: MMLStyleDeviceIdentifier):
    sel = ao_table[dev_id.family]
    device_index = sel.get_device_index(*dev_id.mml_device_index())
    lattice_element_indices = np.asarray(sel.AT.get_element_indices()[device_index])
    assert (lattice_element_indices > 1).all()
    return [elem.UUID for elem in lat[lattice_element_indices - 1]]


# def add_forward_inverse_for_element_group(device_id, elem_props, *, mon_prop, setp_prop, delta_mon_prop=None, delta_setp_prop=None, target_mon_only=True):
#     if target_mon_only:
#         for elm_prop in elem_props:
#             forward_lut.append(LiaisonManagerForwardLookupElement(lat_id=elm_prop, dev_ids=[mon_prop]))
#     if delta_mon_prop is not None:
#         for elm_prop in elem_props:
#             forward_lut.append(LiaisonManagerForwardLookupElement(lat_id=elm_prop, dev_ids=[delta_mon_prop]))
#     inverse_lut.append(LiaisonManagerInverseLookupElement(dev_id=setp_prop, lat_ids=elem_props))
#     inverse_lut.append(LiaisonManagerInverseLookupElement(dev_id=mon_prop, lat_ids=elem_props))
#     if delta_mon_prop is not None and delta_setp_prop is not None:
#         inverse_lut.append(LiaisonManagerInverseLookupElement(dev_id=delta_mon_prop, lat_ids=elem_props))
#         inverse_lut.append(LiaisonManagerInverseLookupElement(dev_id=delta_setp_prop, lat_ids=elem_props))
#

def _add_process_view(process_variable_views, pv_name, rcmd, *, is_setpoint=False, **kwargs):
    cls = Setpoint if is_setpoint else Monitor
    process_variable_views.append(cls(pv_name=pv_name, rcmd=rcmd, **kwargs))


def create_liaison_lut(yp: YellowPagesBase, ao_table: Dict[str, FamilyInfoCollection], lat) -> Tuple[LiaisonManagerForwardLookupTable, LiaisonManagerInverseLookupTable, Sequence[Union[Monitor, Setpoint]], Dict[str, Dict[str,str]]]:
    forward_lut = []
    inverse_lut = []
    process_variable_views: List[Union[Monitor, Setpoint]] = []

    def add_pv_pair(mon_pv: str, set_pv: str, dev_name: str, read_prop: str = "read_current", set_prop: str = "set_current", *, monitor_kwargs=None, setpoint_kwargs=None):
        monitor_kwargs = monitor_kwargs or {}
        setpoint_kwargs = setpoint_kwargs or {}
        mon_rcmd = ReadCommand(mon_pv, read_prop)
        set_rcmd = ReadCommand(set_pv, set_prop)
        _add_process_view(process_variable_views, mon_pv, mon_rcmd, is_setpoint=False, **monitor_kwargs)
        _add_process_view(process_variable_views, set_pv, set_rcmd, is_setpoint=True, reads=[mon_rcmd], **setpoint_kwargs)
        return mon_rcmd, set_rcmd

    inv_lut_tmp = defaultdict(list)
    pv_views = defaultdict(list)

    for family_name, property_name in [("QUAD", "main_strength"), ("SEXT", "main_strength")]:
        for dev_name in yp.get(family_name):
            dev_prop_set = DevicePropertyID(device_name=dev_name, property=property_name)
            element_names = get_element_uuids_for_device(ao_table=ao_table, lat=lat, dev_id=dev_name)
            elem_props = [LatticeElementPropertyID(element_name=name, property=property_name) for name in element_names]
            delta_elem_props = [LatticeElementPropertyID(element_name=name, property="delta_" + property_name) for name in element_names]

            inv_lut_tmp[dev_prop_set].append(elem_props)
            sel = ao_table[dev_prop_set.device_name.family]
            device_index = sel.get_device_index(*dev_prop_set.device_name.mml_device_index())
            mon_pv = sel.Monitor.ChannelNames[device_index].strip()
            set_pv = sel.Setpoint.ChannelNames[device_index].strip()
            pv_views[set_pv].append(mon_pv)

            mon_prop = DevicePropertyID(device_name=mon_pv, property="read_current")
            setp_prop = DevicePropertyID(device_name=set_pv, property="set_current")
            delta_mon_prop = DevicePropertyID(device_name=mon_pv, property="delta_read_current")
            delta_setp_prop = DevicePropertyID(device_name=set_pv, property="delta_set_current")

            for elm_prop in elem_props:
                forward_lut.append(LiaisonManagerForwardLookupElement(lat_id=elm_prop, dev_ids=[mon_prop]))
            for delta_elm_prop in delta_elem_props:
                forward_lut.append(LiaisonManagerForwardLookupElement(lat_id=delta_elm_prop, dev_ids=[delta_mon_prop]))

            inv_lut_tmp[mon_prop].append(elem_props)
            inv_lut_tmp[setp_prop].append(elem_props)
            inv_lut_tmp[delta_mon_prop].append(delta_elem_props)
            inv_lut_tmp[delta_setp_prop].append(delta_elem_props)

    inverse_lut.extend([
        LiaisonManagerInverseLookupElement(dev_id=dev_id, lat_ids=list(itertools.chain.from_iterable(lat_ids)))
        for dev_id, lat_ids in inv_lut_tmp.items()
    ])

    def reduce_mon_pvs(mon_pvs: Sequence[str]) -> str:
        if len(mon_pvs) > 1:
            tmp = list(set(mon_pvs))
            assert len(tmp) == 1
            mon_pvs = tmp
        (r,) = mon_pvs
        return r

    pv_views = {set_pv: reduce_mon_pvs(mon_pvs) for set_pv, mon_pvs in pv_views.items()}
    for set_pv, mon_pv in pv_views.items():
        add_pv_pair(mon_pv, set_pv, set_pv, monitor_kwargs={"prec": 3, "record_type": "ai", "treat_returned_data": "average"}, setpoint_kwargs={"prec": 3, "record_type": "ao", "treat_returned_data": "average"})

    # standard bpms map orbit to device
    # here one receives a table too
    # this should be renamed as well
    orbit_map_lat_id_to_dev_id = {}
    for family_name, property_name in [("BPMx", "dx"), ("BPMy", "dy")]:
        for dev_name in yp.get(family_name):
            dev_prop_bpm = DevicePropertyID(device_name=dev_name, property=property_name)
            (bpm_name,) = get_element_uuids_for_device(ao_table=ao_table, lat=lat, dev_id=dev_name)
            sel = ao_table[dev_name.family]
            device_index = sel.get_device_index(*dev_name.mml_device_index())
            mon_pv = sel.Monitor.ChannelNames[device_index].strip()
            lat_prop = LatticeElementPropertyID(element_name=bpm_name, property=property_name)
            forward_lut.append(LiaisonManagerForwardLookupElement(lat_id=lat_prop, dev_ids=[dev_prop_bpm]))
            inverse_lut.append(LiaisonManagerInverseLookupElement(dev_id = dev_prop_bpm, lat_ids = [lat_prop]))
            try:
                mon = Monitor(pv_name=mon_pv, rcmd=ReadCommand(id=dev_name, property=property_name), prec=3, record_type="ai", update="delayed")
            except pydantic.ValidationError as ex:
                logger.error("Failed to add monitor for %s: %s", dev_name, ex)
                continue
            process_variable_views.append(mon)

    ao_bpmx_data = ao_table["BPMx"]
    ao_bpmy_data = ao_table["BPMy"]


    # simulator backend needs to be informed beforehand for whom to collect turn by turn
    # data
    # Todo: need to review if this should not be handled differently
    lat_prop = LatticeElementPropertyID(element_name="turn_by_turn", property="pos")
    dev_prop = DevicePropertyID(device_name="turn_by_turn", property="pos")
    forward_lut.append(LiaisonManagerForwardLookupElement(lat_id=lat_prop, dev_ids=[dev_prop]))
    inverse_lut.append(LiaisonManagerInverseLookupElement(dev_id=dev_prop, lat_ids=[lat_prop]))

    # track data come as a table. these contain as identifiers the lattice name
    # now one needs to know how to rename these
    tbt_map_lat_id_to_dev_id = {}
    # the ones that have tbt data
    for dev_name in yp.get("TBT_BPM"):
        # I assume that turn by turn bpm capable bpm always provide both planes
        dev_prop_bpm = DevicePropertyID(device_name=dev_name, property="pos")
        (bpm_name,) = get_element_uuids_for_device(ao_table=ao_table, lat=lat, dev_id=dev_name)
        # Translation object needs later to know which data to pick and extract
        tbt_map_lat_id_to_dev_id[bpm_name] = dev_prop_bpm

        pv_x = ao_bpmx_data.Monitor.ChannelNames[ao_bpmx_data.get_device_index(dev_name.sector, dev_name.child)].strip()
        pv_y = ao_bpmy_data.Monitor.ChannelNames[ao_bpmy_data.get_device_index(dev_name.sector, dev_name.child)].strip()
        assert pv_x.endswith(":SA:X") and pv_y.endswith(":SA:Y"), (
            f"Guessing tbt PV, check for libera field for {dev_name}: pv_x = {pv_x}, pv_y = {pv_y}"
        )
        mon_pv = pv_x[:-5]
        assert pv_x[:-5] == pv_y[:-5] == mon_pv
        process_variable_views += [
            Monitor(
                pv_name=f"{mon_pv}:{signal}",
                rcmd=ReadCommand(id=dev_name, property=f"tbt_{ch}"),
                prec=3,
                record_type="waveform_in[float]",
                update="delayed",
                default_waveform_length=64 * 1024,
            )
            for ch, signal in [
                ("x", "signals:tdp_synth:X"), ("y", "signals:tdp_synth:Y"), ("sum","signals:tdp_synth:SUM")
            ]
        ]
    mappings = dict(turn_by_turn=tbt_map_lat_id_to_dev_id)
    del tbt_map_lat_id_to_dev_id

    for family_name, property_name in [("HCM", "x_kick"), ("VCM", "y_kick")]:
        for corr in yp.get(family_name):
            element_names = get_element_uuids_for_device(ao_table=ao_table, lat=lat, dev_id=corr)
            elem_props = [LatticeElementPropertyID(element_name=name, property=property_name) for name in element_names]
            dev_prop_set = DevicePropertyID(device_name=corr, property="set_current")
            dev_prop_read = DevicePropertyID(device_name=corr, property="read_current")
            inverse_lut.extend([
                LiaisonManagerInverseLookupElement(dev_id=dev_prop_set, lat_ids=elem_props),
                LiaisonManagerInverseLookupElement(dev_id=dev_prop_read, lat_ids=elem_props),
            ])
            sel = ao_table[dev_prop_set.device_name.family]
            device_index = sel.get_device_index(*dev_prop_set.device_name.mml_device_index())
            mon_pv = sel.Monitor.ChannelNames[device_index].strip()
            set_pv = sel.Setpoint.ChannelNames[device_index].strip()
            mon_prop = DevicePropertyID(device_name=mon_pv, property="read_current")
            setp_prop = DevicePropertyID(device_name=set_pv, property="set_current")
            for elm_prop in elem_props:
                forward_lut.append(LiaisonManagerForwardLookupElement(lat_id=elm_prop, dev_ids=[mon_prop]))
            inverse_lut.append(LiaisonManagerInverseLookupElement(dev_id=mon_prop, lat_ids=elem_props))
            inverse_lut.append(LiaisonManagerInverseLookupElement(dev_id=setp_prop, lat_ids=elem_props))
            add_pv_pair(mon_pv, set_pv, corr, monitor_kwargs={"prec": 3, "record_type": "ai"}, setpoint_kwargs={"prec": 3, "record_type": "ao"})

    dev_prop_mc_ref = DevicePropertyID(device_name="master_clock", property="reference_frequency")
    dev_prop_mc = DevicePropertyID(device_name="master_clock", property="frequency")

    for cav in yp.get("RF"):
        element_names = get_element_uuids_for_device(ao_table=ao_table, lat=lat, dev_id=cav)
        elem_props = [LatticeElementPropertyID(element_name=name, property="frequency") for name in element_names]
        for elm_prop in elem_props:
            forward_lut.append(LiaisonManagerForwardLookupElement(lat_id=elm_prop, dev_ids=[dev_prop_mc]))
        inverse_lut += [
            LiaisonManagerInverseLookupElement(dev_id=dev_prop_mc_ref, lat_ids=elem_props),
            LiaisonManagerInverseLookupElement(dev_id=dev_prop_mc, lat_ids=elem_props),
        ]

    sel = ao_table["RF"]
    mon_pv = str(sel.Monitor.ChannelNames).strip()
    set_pv = str(sel.Setpoint.ChannelNames).strip()
    master_clock_monitor = Monitor(pv_name=mon_pv, rcmd=ReadCommand("master_clock", "frequency"), prec=9, record_type="ai", treat_returned_data="average")
    setp = Setpoint(pv_name=set_pv, rcmd=ReadCommand("master_clock", "reference_frequency"), prec=9, record_type="ao", reads=[master_clock_monitor.rcmd], treat_returned_data="average")
    process_variable_views.extend([master_clock_monitor, setp])

    inverse_lut += [
        LiaisonManagerInverseLookupElement(dev_id=DevicePropertyID(device_name="twiss", property="parameters"), lat_ids=[LatticeElementPropertyID(element_name="twiss", property="parameters")]),
        LiaisonManagerInverseLookupElement(dev_id=DevicePropertyID(device_name="track", property="pos"), lat_ids=[LatticeElementPropertyID(element_name="track", property="pos")]),
        LiaisonManagerInverseLookupElement(dev_id=DevicePropertyID(device_name="turn_by_turn_start", property="start"), lat_ids=[LatticeElementPropertyID(element_name="turn_by_turn_start", property="start")]),
        LiaisonManagerInverseLookupElement(dev_id=DevicePropertyID(device_name="turn_by_turn_start", property="n_turns"), lat_ids=[LatticeElementPropertyID(element_name="turn_by_turn_start", property="n_turns")]),
        LiaisonManagerInverseLookupElement(dev_id=DevicePropertyID(device_name="turn_by_turn_start", property="data_needed_at"), lat_ids=[LatticeElementPropertyID(element_name="turn_by_turn_start", property="data_needed_at")]),
        LiaisonManagerInverseLookupElement(dev_id=DevicePropertyID(device_name="turn_by_turn_start", property="p0"), lat_ids=[LatticeElementPropertyID(element_name="turn_by_turn_start", property="p0")]),
    ]

    forward_lut += [
        LiaisonManagerForwardLookupElement(lat_id=LatticeElementPropertyID(element_name="twiss", property="parameters"), dev_ids=[DevicePropertyID(device_name="twiss", property="parameters")]),
        LiaisonManagerForwardLookupElement(lat_id=LatticeElementPropertyID(element_name="track", property="pos"), dev_ids=[DevicePropertyID(device_name="track", property="pos")]),
        LiaisonManagerForwardLookupElement(lat_id=LatticeElementPropertyID(element_name="turn_by_turn_start", property="start"), dev_ids=[DevicePropertyID(device_name="turn_by_turn_start", property="start")]),
        LiaisonManagerForwardLookupElement(lat_id=LatticeElementPropertyID(element_name="turn_by_turn_start", property="n_turns"), dev_ids=[DevicePropertyID(device_name="turn_by_turn_start", property="n_turns")]),
        LiaisonManagerForwardLookupElement(lat_id=LatticeElementPropertyID(element_name="turn_by_turn_start", property="data_needed_at"), dev_ids=[DevicePropertyID(device_name="turn_by_turn_start", property="data_needed_at")]),
        LiaisonManagerForwardLookupElement(lat_id=LatticeElementPropertyID(element_name="turn_by_turn_start", property="p0"), dev_ids=[DevicePropertyID(device_name="turn_by_turn_start", property="p0")]),
        LiaisonManagerForwardLookupElement(lat_id=LatticeElementPropertyID(element_name="tune", property="transversal"), dev_ids=[DevicePropertyID(device_name="tune", property="delta_set_current")]),
    ]
    inverse_lut.append(LiaisonManagerInverseLookupElement(dev_id=DevicePropertyID(device_name="tune", property="transversal"), lat_ids=[LatticeElementPropertyID(element_name="tune", property="transversal")]))

    process_variable_views.extend([
        Setpoint(pv_name="simulator_ring:turn_by_turn:n_turns", rcmd=ReadCommand("turn_by_turn_start", "n_turns"), record_type="longout", treat_returned_data="single", prec=0, reads=[]),
        Setpoint(pv_name="simulator_ring:turn_by_turn:data_needed_at", rcmd=ReadCommand("turn_by_turn_start", "data_needed_at"), record_type="waveform_out[str]", treat_returned_data="single", default_waveform_length=2048, prec=0, reads=[]),
        Setpoint(pv_name="simulator_ring:turn_by_turn:run", always_update=True, rcmd=ReadCommand("turn_by_turn_start", "start"), record_type="longout", treat_returned_data="single", default_waveform_length=2048, update="immediate", prec=0, reads=[ReadCommand("turn_by_turn", "pos")]),
    ])

    fwd = LiaisonManagerForwardLookupTable(forward_lut)
    inv = LiaisonManagerInverseLookupTable(inverse_lut)
    fwd.verify()
    inv.verify()
    assert not inv.non_unique_entries()
    return fwd, inv, process_variable_views, mappings
