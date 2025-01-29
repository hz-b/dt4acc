from bact_twin_bessyii_impl.bl.command_rewritter import CommandRewriter
from bact_twin_bessyii_impl.bl.io.pytac_repositories import PyTACRepository
from bact_twin_bessyii_impl.bl.translation_service import TranslationService
from p4p.client.asyncio import Context

from ...core.accelerators.pyat_accelerator import setup_accelerator
from ...core.command import UpdateManager
from ...core.utils.logger import get_logger

logger = get_logger()

ctx = Context("pva")  # Create a context for EPICS PVA (PV Access)

#: todo replace soon by database service
repo = PyTACRepository()

# todo: should this be part of the controller
update_manager = UpdateManager(
    command_rewritter=CommandRewriter(
        TranslationService(conversion_info=repo.state_conversion_repo)
    ),
    acc_mgr=setup_accelerator()
)


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
        await update_manager.update(device_id=device_id, property_name=property_id, value=value)
    except Exception as e:
        logger.warning(f"Error in updating element {device_id} with property_name: {property_id} value {value}")
