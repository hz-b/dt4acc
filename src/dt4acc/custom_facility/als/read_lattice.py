import functools
import json
import os

from functools import partial
from pathlib import Path
from typing import Dict, Sequence

import at

from dt4acc.custom_facility.als.augment_names_on_famnames import (
    NameAugmenter,
    SectorRegistry,
)
from lat2db.tools.factories import pyat as pyatf

default_energy = 1.89086196873342e9

def factory(d: dict, energy: float):
    factory_dict = pyatf.factory_dict_default.copy()
    factory_dict.update(
        dict(
            Marker=pyatf.instantiate_marker_simple,
            Drift=pyatf.instantiate_drift_simple,
            Bend=pyatf.instantiate_bending_simple,
            Quadrupole=pyatf.instantiate_quadrupole_simple,
            Sextupole=pyatf.instantiate_sextupole_simple,
            Corrector=pyatf.instantiate_steerer_simple,
        )
    )

    factory_dict["RFCavity"] = partial(pyatf.instantiate_cavity_simple, energy=energy)

    def instantiate(elm_data: dict):
        r = pyatf.instantiate_element(elm_data, factory_dict=factory_dict)
        if r is None:
            return None
        return r

    elements = [instantiate(e) for e in d]
    return elements


def als_add_uuid_to_lattice_elements(elements: Sequence) -> Sequence:
    nm = NameAugmenter(sector_registry=SectorRegistry())

    def add_uuid(elem):
        if elem.FamName.startswith("SECT"):
            nm.new_sector(elem.FamName)
        sector, child = nm.sector_child_for_family_name(elem.FamName)
        elem.UUID = f"{elem.FamName}-sec_{sector}-child_{child}"
        return elem

    return [add_uuid(elem) for elem in elements]


default_filename = (
    Path(os.environ.get("HOME"))
    / "Documents"
    / "dt4acc_als_data"
    / "als_thering_tst.json"
)

test_filename = (
    Path(os.environ.get("HOME"))
    / "Documents"
    / "dt4acc_als_data"
    / "als_thering_at_compat_tst.json"
)

def als_load_lattice(filename: str, energy: float = default_energy):
    with open(filename, "rt") as fp:
        sequence_data = json.load(fp)

    # with open(test_filename, "wt") as fp:
    #    json.dump(
    #        dict(
    #            atjson=1,
    #            elements=sequence_data,
    #            energy=default_energy
    #        ),
    #        fp
    #    )
    #    # sequence_data =
    # r = at.load_json(test_filename, from_at=True, energy=default_energy)
    # als_add_uuid_to_lattice_elements(r)
    seq = als_add_uuid_to_lattice_elements(factory(sequence_data, energy))
    r = at.Lattice(seq, name="ALS storage ring", energy=energy)
    r.enable_6d()
    r.cavpts = "CAV*"
    r.set_cavity_phase(cavpts=r.cavpts)

    # Test that start setup is stable
    r.get_optics()
    print(f"Read a lattice with {len(r)} elements")
    return r


@functools.lru_cache(maxsize=None)
def als_get_lattice(filename: str, energy: float = default_energy):
    return als_load_lattice(filename, energy)


def main():
    # filename = (
    #        Path(os.environ.get("HOME"))
    #         / "Documents"
    #        / "dt4acc_soleil_twin_data"
    #         / "SOLEIL_II_V3631_sym1_V001_database.m"
    # )
    r = als_get_lattice(default_filename)
    pass


if __name__ == "__main__":
    main()
