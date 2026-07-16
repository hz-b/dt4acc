from __future__ import annotations

import itertools
import logging
from collections import defaultdict
from typing import Dict, Sequence

import numpy as np

from bact_mml_json_importer.data_model.mml_ao import FamilyInfoCollection
from dt4acc.custom_facility.als.model import MMLStyleDeviceIdentifier

from .config import BootstrapConfig

logger = logging.getLogger("dt4acc")


def uuids_of_at_elements(elements: Sequence, family_name: str, indices: Sequence[int], alternative_family_names: Sequence[str] = ()) -> Sequence[str]:
    """Return UUIDs for lattice elements identified by 1-based AT indices."""
    indices = np.asarray(indices)
    assert np.all(indices > 0)
    indices = indices - 1
    names = [elements[idx].UUID for idx in indices]

    for cnt, (idx, name) in enumerate(zip(indices, names)):
        if name.startswith(family_name):
            continue
        for alternate in alternative_family_names:
            if name.startswith(alternate):
                break
        else:
            raise ValueError(
                f"family {family_name}: element no {cnt} at index {idx} name {name} not coherent to family name"
            )
    return names


def extract_family_member_names(lat, ao_table: Dict[str, FamilyInfoCollection], family_name: str, alternative_family_names: Sequence[str] = ()):
    alternative_family_names = alternative_family_names or ()
    ao_view = ao_table[family_name]
    if ao_view.AT is None:
        logger.warning("No AT info given for %s, thus not building yp field", family_name)
        return None
    indices = ao_view.AT.get_element_indices()
    dev_list = ao_view.get_device_list()
    assert len(indices) == len(dev_list), (
        f"Check failed for family {family_name} n indices = {len(indices)}, n devs = {len(dev_list)}"
    )
    uuids_of_at_elements(
        lat,
        family_name,
        list(itertools.chain.from_iterable(indices)),
        alternative_family_names=alternative_family_names,
    )
    return [
        MMLStyleDeviceIdentifier(family=family_name, sector=int(sector), child=int(child))
        for sector, child in dev_list
    ]


def create_yellow_pages_input_from_ao_table(ao_table: Dict[str, FamilyInfoCollection], lat, config: BootstrapConfig) -> Dict[str, Sequence[str]]:
    names = {
        fam: extract_family_member_names(lat, ao_table, fam)
        for fam in config.standard_families
    }
    names = {fam: fam_names for fam, fam_names in names.items() if fam_names is not None}

    for family_name, aliases in config.special_family_aliases.items():
        if family_name in names:
            continue
        names[family_name] = extract_family_member_names(lat, ao_table, family_name, alternative_family_names=aliases)

    yp_dict = defaultdict(list)
    yp_dict[config.master_clock_name] = [config.master_clock_name]

    for ref_fam_name, family_members in names.items():
        if family_members is None:
            continue
        members_of = ao_table[ref_fam_name].member_of()
        for family_name in members_of:
            yp_dict[str(family_name)].extend(family_members)

    for alias_name, canonical_name in config.yp_tag_aliases.items():
        yp_dict[alias_name] = yp_dict[canonical_name]

    return dict(yp_dict)


def extract_fast_bpm_entry(ao_table: Dict[str, FamilyInfoCollection], yp_dict: Dict[str, Sequence[str]]) -> Sequence[str]:
    # For now, I assume that all devices listed in BPM are fast ones
    assumed_fast_bpms = ao_table["BPM"]
    bpm_plane_x = ao_table["BPMx"]
    bpm_plane_y = ao_table["BPMy"]

    def check_entry(dev_id) -> bool:
        pv_x = bpm_plane_x.Monitor.ChannelNames[bpm_plane_x.get_device_index(*dev_id)].strip()
        pv_y = bpm_plane_y.Monitor.ChannelNames[bpm_plane_y.get_device_index(*dev_id)].strip()
        if pv_x.endswith("SA:X") and pv_y.endswith("SA:Y"):
            return True
        logger.warning(
            "I assumed that BPM device %s is a fast bpm"
            " but the pv names (x=%s, y=%s, don't match expected ones",
            dev_id, pv_x, pv_y
        )
        return False

    def create_entry(dev_id) -> MMLStyleDeviceIdentifier:
        sector, child = dev_id
        return MMLStyleDeviceIdentifier(family="BPM", sector=sector, child=child)

    fast_bpm_entries = [
        create_entry(dev_id) for dev_id in ao_table["BPM"].DeviceList if check_entry(dev_id)
    ]
    return fast_bpm_entries


def create_yellow_pages_input(ao_table: Dict[str, FamilyInfoCollection], lat, config: BootstrapConfig) -> Dict[str, Sequence[str]]:
    d = create_yellow_pages_input_from_ao_table(ao_table, lat, config)
    d.update(dict(TBT_BPM=extract_fast_bpm_entry(ao_table, d)))
    return d

