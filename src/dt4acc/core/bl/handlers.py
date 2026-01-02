from bact_twin_architecture.bl.command_rewriter import CommandRewriter
# from dt4acc.custom_epics.ioc.liasion_translation_manager import build_managers

from dt4acc.custom_epics.ioc.liasion_translation_manager import build_managers
from dt4acc.custom_epics.utils.context_proxy import ContextProxy
from dt4acc.core.accelerators.pyat_accelerator import setup_accelerator
from dt4acc.core.command import UpdateManager
from dt4acc.core.utils.logger import get_logger

logger = get_logger()

# ctx = ContextProxy("pva")  # Create a context for EPICS PVA (PV Access)

#: todo replace soon by database service

# lm, tm = build_managers()
#
# # todo: should this be part of the controller
# update_manager = UpdateManager(
#     command_rewritter=CommandRewriter(
#         liasion_manager=lm,
#         translation_service=tm
#     ),
#     liaison_manager=lm,
#     translator_service=tm,
#     acc_mgr=setup_accelerator()
# )
# 1. Initialize the global variable to None
_update_manager_instance = None


def get_update_manager():
    """
    Lazy loader for the UpdateManager.
    Ensures the heavy initialization logic runs only ONCE per process,
    upon the first call, rather than at import time.
    """
    global _update_manager_instance

    # 2. Check if it has already been created
    if _update_manager_instance is None:
        logger.info("Initializing UpdateManager backend (Lazy Load)...")

        # --- Heavy Initialization Logic Moved Here ---
        lm, tm = build_managers()

        _update_manager_instance = UpdateManager(
            command_rewritter=CommandRewriter(
                liasion_manager=lm,
                translation_service=tm
            ),
            liaison_manager=lm,
            translator_service=tm,
            acc_mgr=setup_accelerator()
        )
        # ---------------------------------------------

    return _update_manager_instance

async def handle_device_update(device_id: str, property_id: str, value: float):
    """Handles updates of devices

    Delegates ipdates the corresponding property in the lattice to the
    device updater


    Args:
        device_name (str): The process variable (PV) name of the magnet.
        value (float): The updated value for the PV.
        element (object): The magnet element being updated.

    Todo:
        should one directly call the update managers. update?

    """
    try:
        # Call the command update function to apply the value to the model
        update_manager = get_update_manager()
        await update_manager.update(device_id=device_id, property_name=property_id, value=value)
    except Exception as e:
        logger.warning(f"Error in updating element {device_id} with property_name: {property_id} value {value}")


async def forward_pc_change(pc_name: str, property: str, value: float) -> None:
    raise NotImplementedError("not yet forwarding current to magnets")
