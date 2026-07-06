import functools
import os
from pathlib import Path
from typing import Sequence

import at

from dt4acc.custom_facility.als.augment_names_on_famnames import (
    NameAugmenter,
    SectorRegistry,
)
import logging
logger = logging.getLogger("dt4acc-custom-als")

default_energy = 1.89086196873342e9


def als_add_uuid_to_lattice_elements(elements: Sequence) -> Sequence:
    nm = NameAugmenter(sector_registry=SectorRegistry())

    def add_uuid(elem):
        if elem.FamName.startswith("SECT"):
            nm.new_sector(elem.FamName)
        sector, child = nm.sector_child_for_family_name(elem.FamName)
        elem.UUID = f"{elem.FamName}-sec_{sector}-child_{child}"
        return elem

    return [add_uuid(elem) for elem in elements]


_default_filename = (
    Path(os.environ.get("HOME"))
    / "Documents"
    / "dt4acc_als_data"
    / "als_thering_tst.json"
)

default_filename = None

test_filename = (
    Path(os.environ.get("HOME"))
    / "Documents"
    / "dt4acc_als_data"
    / "als_thering_at_compat_tst.json"
)

_default_filename = test_filename


def als_load_lattice(filename: str = None, energy: float = default_energy):
    if filename is None:
        filename = os.environ.get("DT4ACC_ALS_LATTICE_FILE", None)
        if filename is None:
            logger.warning(
                f"No DT4ACC_ALS_LATTICE_FILE environment variable defined using {default_filename}"
            )
            filename = _default_filename

    logger.info(f"als_load_lattice: Using filename  {filename}")
    if not Path(filename).exists():
        logger.warning("File not found at {filename}")

    r = at.load_json(filename, from_at=True, energy=default_energy)
    als_add_uuid_to_lattice_elements(r)

    r.enable_6d()
    r.cavpts = "CAV*"
    r.set_cavity_phase(cavpts=r.cavpts)

    # Test that start setup is stable
    r.get_optics()
    print(f"Read a lattice with {len(r)} elements")
    return r


@functools.lru_cache(maxsize=None)
def als_get_lattice(filename: str =  None, energy: float = default_energy):
    return als_load_lattice(filename, energy)
import numpy as np


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
