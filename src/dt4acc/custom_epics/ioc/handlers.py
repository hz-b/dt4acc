from bact_twin_architecture.bl.command_rewriter import CommandRewriter
# from dt4acc.custom_epics.ioc.liasion_translation_manager import build_managers

from .liasion_translation_manager import build_managers
from ..utils.context_proxy import ContextProxy
from ...core.accelerators.pyat_accelerator import setup_accelerator
from ...core.bl.behavior_tree import handle_power_converter_set_with_bt
from ...core.command import UpdateManager
from ...core.utils.logger import get_logger

logger = get_logger()

ctx = ContextProxy("pva")  # Create a context for EPICS PVA (PV Access)

#: todo replace soon by database service

lm, tm = build_managers()

# todo: should this be part of the controller
update_manager = UpdateManager(
    command_rewritter=CommandRewriter(
        liasion_manager=lm,
        translation_service=tm
    ),
    liaison_manager=lm,
    translator_service=tm,
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
        await handle_power_converter_set_with_bt(
            update_manager=update_manager,
            acc_mgr=update_manager.acc_mgr,
            pc_name=device_id,
            property_name=property_id,
            value=value)
        # await update_manager.update(device_id=device_id, property_name=property_id, value=value)
    except Exception as e:
        logger.warning(f"Error in updating element {device_id} with property_name: {property_id} value {value}")


async def forward_pc_change(pc_name: str, property: str, value: float) -> None:
    raise NotImplementedError("not yet forwarding current to magnets")
