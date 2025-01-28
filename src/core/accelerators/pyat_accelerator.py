import os

from src.core.accelerators.accelerator_manager import AcceleratorManager


def setup_accelerator():
    """
    Set up and initialize the accelerator.

    Retrieves the prefix from environment variables and initializes
    the accelerator manager.

    Returns:
        AcceleratorManager: Singleton instance of the accelerator manager.
    """
    prefix = os.getenv("DT4ACC_PREFIX", "Anonym")
    manager = AcceleratorManager(prefix=prefix)
    manager.initialize()
    return manager
