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
    manager = AcceleratorManager(prefix=prefix, bpm_names_as_in_machine=None)
    manager.initialize()
    return manager
