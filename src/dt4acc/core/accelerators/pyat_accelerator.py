import importlib
import os
import getpass
from importlib import resources

from .accelerator_manager import BackendRW
from ...custom_epics.data.bpm_configuration import load_bpm_configuration_data
from accml_lib.custom.bessyii.bessyii_pyat_lattice import bessyii_pyat_lattice_from_dics
from accml_lib.custom.bessyii.pyat_simulator_backend import create_simulator_backend


def load_structure(data_json_path):
    import json
    from lat2db.tools.factories.pyat import factory

    with open(data_json_path, "rt") as fp:
        d = json.load(fp)

    # Todo: have energy stored in configuration
    energy = 1.7185e9
    return factory(d, energy=energy)


def setup_accelerator() -> BackendRW:
    """
    Set up and initialize the accelerator.

    Retrieves the prefix from environment variables and initializes
    the accelerator manager.

    Todo:
        Make input arguments available (providing good defaults if feasible)

    Returns:
        BackendRW: Singleton instance of the accelerator manager.
    """
    prefix = os.getenv("DT4ACC_PREFIX", getpass.getuser())
    top, *_ = __name__.split(".")
    mod_path = importlib.resources.files(top)
    t_path = mod_path.joinpath(
        "custom_epics", "data", "standard", "bpm_cfg_as_in_machine.json"
    )
    with open(t_path) as fp:
        bpm_cfg = load_bpm_configuration_data(fp)
    bpm_names = [c.name for c in bpm_cfg.col]
    # manager = AcceleratorManager(prefix=prefix, bpm_names_as_in_machine=bpm_names)
    # manager.initialize()
    # return manager

    backend = create_simulator_backend(
        bessyii_pyat_lattice_from_dics(
            load_structure(
                resources.files("dt4acc").joinpath(
                    "custom_epics/data/standard/bessy2_storage_ring_reflat.json"
                )
            )
        )
    )
    return backend

