from p4p.client.asyncio import Context

from ...core import command
from ...core.utils.logger import get_logger

logger = get_logger()

ctx = Context("pva")  # Create a context for EPICS PVA (PV Access)


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
        await command.update(device_id=device_id, property_name=property_id, value=value)
    except Exception as e:
        logger.warning(f"Error in updating element {device_id} with property_name: {property_id} value {value}")


async def handle_magnet_update(device_id: str, property_id: str, value: float):
    """
    Handles updates to magnet PVs.

    Args:
        device_name (str): The process variable (PV) name of the magnet.
        value (float): The updated value for the PV.
        element (object): The magnet element being updated.

    Updates the corresponding magnet property in the accelerator model.
    """
    try:
        # Call the command update function to apply the value to the model
        await command.update(device_id=device_id, property_name=property_id, value=value)
    except Exception as e:
        logger.warning(f"Error in updating {device_id=} {property_id=} {value=}: {e}")



async def handle_power_converter_update(pc_name, value, prefix, connected_magnets):
    """
    Handles updates to power converters and propagates changes to connected magnets.

    Args:
        pc_name (str): The name of the power converter.
        value (float): The updated value for the power converter.
        prefix (str): The prefix used for naming PVs.
        connected_magnets (list): List of magnets connected to this power converter.

    Updates the power converter readback value and the connected magnets.
    """
    try:
        await ctx.put(f"{prefix}:{pc_name}:rdbk", value)
    except Exception as e:
        logger.warning(f"Error updating power converter rdbk {pc_name}: {e}")
    # Update the `im:I` PVs of all connected magnets
    try:
        for magnet in connected_magnets:
            await ctx.put(f"{prefix}:{magnet['name']}:im:I", value)
    except Exception as e:
        logger.warning(f"Error updating power converter {pc_name}: {e}")


async def handle_master_clock_update(cavity_names, value, prefix):
    """
    Handles updates to the master clock and updates frequency PVs for cavities.

    Args:
        cavity_names (list): List of cavity PV names to update.
        value (float): The updated frequency value.
        prefix (str): The prefix used for naming PVs.

    Updates the frequency of all cavities and applies it to the accelerator model.
    """
    for cavity in cavity_names:
        try:
            await ctx.put(f"{prefix}:{cavity}:freq", value)
            await command.update(element_id=cavity, property_name='freq', value=value, element=cavity_names)
        except Exception as e:
            logger.info(f"Error updating cavity frequency {cavity}: {e}")


def get_property_id(pv_name):
    """
    todo: this is ugly at the moment
    Determines the property ID based on the provided PV name.

    Args:
        pv_name (str): The process variable (PV) name.

    Returns:
        str: The corresponding property ID, or None if not recognized.
    """
    if ':Cm:set' in pv_name:
        return 'K'
    elif ':x:set' in pv_name:
        return 'x'
    elif ':y:set' in pv_name:
        return 'y'
    elif ':im:I' in pv_name:
        return 'im'
    elif ':rdbk' in pv_name:
        return 'rdbk'
    else:
        return None
