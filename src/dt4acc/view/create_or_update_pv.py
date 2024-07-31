import asyncio
import logging

from ..setup_configuration.pv_manager import PVManager
from ..setup_configuration.server import create_pv

logger = logging.getLogger(__name__)

# Instantiate the PVManager
manager = PVManager()


async def update_or_create_pv(element, pv_name, value, value_type, initial_type):
    try:
        logger.debug(f"Checking if PV {pv_name} exists.")
        pv = manager.get_pv(pv_name)
        if pv is None:
            logger.debug(f"Creating new PV for {pv_name}.")
            new_pv = create_pv(initial_value_type=value_type, initial_type=initial_type, element=element)
            await asyncio.get_running_loop().run_in_executor(None, manager.add_pv, pv_name, new_pv)
            logger.debug(f"PV {pv_name} created and added to manager.")

        logger.debug(f"Updating PV {pv_name} with value: {value}.")
        await manager.update_pv(pv_name, value)
        logger.debug(f"PV {pv_name} updated successfully.")
    except Exception as e:
        logger.error(f"Failed to update or create PV {pv_name}: {e}")
