import importlib
import os
import getpass

from .accelerator_manager import AcceleratorManager
from ...custom_epics.data.bpm_configuration import load_bpm_configuration_data


def setup_accelerator():
    """
    Set up and initialize the accelerator.

    Retrieves the prefix from environment variables and initializes
    the accelerator manager.

    Returns:
        AcceleratorManager: Singleton instance of the accelerator manager.
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
    manager = AcceleratorManager(prefix=prefix, bpm_names_as_in_machine=bpm_names)
    manager.initialize()
    return manager
