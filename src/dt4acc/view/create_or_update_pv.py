import asyncio
import logging

from bact_device_models.devices.bpm_elem import BpmElementList
from p4p.server.asyncio import SharedPV
from p4p.wrapper import Value, Type

from ..model.orbit import Orbit
from ..model.twiss import Twiss
from ..setup_configuration.pv_manager import PVManager
from ..setup_configuration.server import create_pv

manager = PVManager()
logger = logging.getLogger(__name__)


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


async def update_or_create_pv_bulk(element, pv_data):
    pv_names = []
    pv_values = []
    for name, value, value_type, initial_type in pv_data:
        pv = manager.get_pv(name)
        if pv is None:
            logger.debug(f"Creating new PV for {name}.")
            new_pv = create_pv(initial_value_type=value_type, initial_type=initial_type, element=element)
            await asyncio.get_running_loop().run_in_executor(None, manager.add_pv, name, new_pv)
            logger.debug(f"PV {name} created and added to manager.")
        pv_names.append(name)
        pv_values.append(value)
    await manager.update_pv_list(pv_names, value)


# Define the structure for the Twiss PV using Type
twiss_type = Type([
    ('x', ('S', None, [
        ('alpha', 'ad'),
        ('beta', 'ad'),
        ('nu', 'ad'),
    ])),
    ('y', ('S', None, [
        ('alpha', 'ad'),
        ('beta', 'ad'),
        ('nu', 'ad'),
    ])),
    ('names', 'as'),  # Assuming names is a sequence of strings
])


async def update_twiss_pv(pv_name, twiss_result: Twiss):
    # Check if the structured PV exists
    pv = manager.get_pv(pv_name)
    if pv is None:
        logger.debug(f"Creating new structured PV for {pv_name}.")

        # Create the structured PV with initial data
        initial_data = {
            'x': {
                'alpha': twiss_result.x.alpha,
                'beta': twiss_result.x.beta,
                'nu': twiss_result.x.nu,
            },
            'y': {
                'alpha': twiss_result.y.alpha,
                'beta': twiss_result.y.beta,
                'nu': twiss_result.y.nu,
            },
            'names': twiss_result.names
        }

        new_pv = SharedPV(initial=Value(twiss_type, initial_data))
        await asyncio.get_running_loop().run_in_executor(None, manager.add_pv, pv_name, new_pv)
        logger.debug(f"Structured PV {pv_name} created and added to manager.")
    else:
        logger.debug(f"Updating existing structured PV {pv_name} with new data.")

        # Prepare the new data
        new_data = {
            'x': {
                'alpha': twiss_result.x.alpha,
                'beta': twiss_result.x.beta,
                'nu': twiss_result.x.nu,
            },
            'y': {
                'alpha': twiss_result.y.alpha,
                'beta': twiss_result.y.beta,
                'nu': twiss_result.y.nu,
            },
            'names': twiss_result.names
        }

        # Convert the dictionary to a Value object
        value_to_post = Value(twiss_type, new_data)

        # Post the Value object to the PV
        pv.post(value_to_post)
        logger.info(f"Successfully updated structured PV {pv_name} with new data.")


orbit_type = Type([
    ('x', 'ad'),  # Array of doubles for x positions
    ('y', 'ad'),  # Array of doubles for y positions
    ('names', 'as'),  # Array of strings for element names
    ('found', '?'),  # Boolean to indicate if orbit was found
    ('x0', 'ad'),  # Array of doubles for x0 fixed points
])


async def update_orbit_pv(pv_name, orbit_result: Orbit):
    # Get or create the PV manager

    # Check if the structured PV exists
    pv = manager.get_pv(pv_name)
    if pv is None:
        logger.debug(f"Creating new structured PV for {pv_name}.")

        # Create the structured PV with initial data
        initial_data = {
            'x': orbit_result.x,
            'y': orbit_result.y,
            'names': orbit_result.names,
            'found': orbit_result.found,
            'x0': orbit_result.x0,
        }

        new_pv = SharedPV(initial=Value(orbit_type, initial_data))
        await asyncio.get_running_loop().run_in_executor(None, manager.add_pv, pv_name, new_pv)
        logger.debug(f"Structured PV {pv_name} created and added to manager.")
    else:
        logger.debug(f"Updating existing structured PV {pv_name} with new data.")

        # Prepare the new data
        new_data = {
            'x': orbit_result.x,
            'y': orbit_result.y,
            'names': orbit_result.names,
            'found': orbit_result.found,
            'x0': orbit_result.x0,
        }

        # Convert the dictionary to a Value object
        value_to_post = Value(orbit_type, new_data)

        # Post the Value object to the PV
        pv.post(value_to_post)
        logger.info(f"Successfully updated structured PV {pv_name} with new data.")


bpm_position_type = Type([
    ('x', 'd'),  # Double for x position
    ('y', 'd'),  # Double for y position
])

bpm_element_type = Type([
    ('name', 's'),
    ('pos', ('S', None, [
        ('x', 'd'),
        ('y', 'd'),
    ])),
])


bpm_type = Type([
    ('bpms', ('aS', None, [
        ('name', 's'),
        ('pos', bpm_position_type),
    ])),
])
async def update_bpm_pv(pv_name, bpm_result):

    # Prepare the BPM data in the expected format
    bpm_data = [{
        'name': bpm.name,
        'pos': {'x': bpm.pos.x, 'y': bpm.pos.y},
    } for bpm in bpm_result.bpms]

    # Check if the structured PV exists
    pv = manager.get_pv(pv_name)
    if pv is None:
        logger.debug(f"Creating new structured PV for {pv_name}.")

        # Create the structured PV with initial data
        initial_data = {'bpms': bpm_data}

        new_pv = SharedPV(initial=Value(bpm_type, initial_data))
        await asyncio.get_running_loop().run_in_executor(None, manager.add_pv, pv_name, new_pv)
        logger.debug(f"Structured PV {pv_name} created and added to manager.")
    else:
        logger.debug(f"Updating existing structured PV {pv_name} with new data.")

        # Prepare the new data
        new_data = {'bpms': bpm_data}

        # Convert the dictionary to a Value object
        value_to_post = Value(bpm_type, new_data)

        # Post the Value object to the PV
        pv.post(value_to_post)
        logger.info(f"Successfully updated structured PV {pv_name} with new BPM data.")