# pyat_accelerator.py
import os
import getpass
import threading

from .accelerator_manager import AcceleratorManager
from ..utils.logger import get_logger

logger = get_logger()

_instance = None
_lock = threading.Lock()


def setup_accelerator():
    """
    Set up and initialize the accelerator.

    Retrieves the prefix from environment variables and initializes
    the accelerator manager. Returns the same instance on every call
    within the same process.

    Returns:
        AcceleratorManager: Singleton instance of the accelerator manager.
    """
    global _instance

    if _instance is not None:
        return _instance

    with _lock:
        if _instance is None:
            prefix = os.getenv("DT4ACC_PREFIX", getpass.getuser())
            manager = AcceleratorManager(prefix=prefix)
            manager.initialize()
            _instance = manager

    return _instance