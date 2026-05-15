"""
controller_registry.py
======================

Single source of truth for the process-global TangoController instance.

This module has NO imports from the devices package, breaking the circular
dependency:

    magnet_device → single_server → tango_device_setup → magnet_device  ❌

New dependency graph:

    single_server      → controller_registry  (sets the controller)
    magnet_device      → controller_registry  (reads the controller)
    tango_device_setup → (no controller dependency at all)           ✔
"""
from typing import Union

from dt4acc.core.interfaces.controller_interface import ControllerInterface
from dt4acc.core.utils.logger import get_logger

logger = get_logger()

_controller : Union[ControllerInterface, None] = None


def set_controller(controller: ControllerInterface) -> None:
    """Called once by single_server before tango.server.run()."""
    global _controller
    _controller = controller
    logger.info("TangoController registered in controller_registry")


def get_controller() -> ControllerInterface:
    """Called by device write-handlers to reach the shared controller."""
    if _controller is None:
        raise RuntimeError(
            "TangoController not yet initialised — "
            "get_controller() called before single_server._inject_controller()"
        )
    return _controller
