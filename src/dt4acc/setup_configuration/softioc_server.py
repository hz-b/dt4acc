import numpy as np
from p4p.client.asyncio import Context
from softioc import softioc, builder, asyncio_dispatcher

import dt4acc.command as cmd
from dt4acc.calculator.pyat_calculator import logger
from dt4acc.model.elementmodel import MagnetElementSetup
from dt4acc.setup_configuration.data_access import get_unique_power_converters, \
    get_magnets_per_power_converters

# Initialize the Asyncio Dispatcher for SoftIOC
dispatcher = asyncio_dispatcher.AsyncioDispatcher()

# Set device name for SoftIOC PVs
builder.SetDeviceName("Anonym")

# Cache for magnet elements and PVs
element_cache = {}


def get_property_id(pv_name):
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


# Helper function to handle the update logic
async def handle_element_update(pv_name, value, element):
    property_id = get_property_id(pv_name)
    try:
        # Call the cmd.update as in the previous server.py logic
        await cmd.update(element_id=element.name, property_name=property_id, value=value, element=element)
    except Exception as e:
        print(f"Error in updating element {element.name}: {e}")


# Create PVs for Magnets
def add_magnet_pvs(magnet):
    bessyii_brho =5.67229387129245
    magnet_name = magnet['name']
    element = MagnetElementSetup(
        type=magnet['type'],
        name=magnet['name'],
        hw2phys=magnet['magnetic_strength'],  # Adjusted for SoftIOC
        phys2hw=1 / magnet['magnetic_strength'],  # Adjusted
        energy=1.7e9,  # Hardcoded from previous server logic
        magnetic_strength=magnet['magnetic_strength'],
        electron_rest_mass=0.51099895e6,  # Hardcoded
        speed_of_light=299792458,
        brho=bessyii_brho,
        edf=1 / 5.67229387129245,
        pc=magnet['pc'],
        k=magnet['k']
    )
    # Store element in cache
    element_cache[magnet_name] = element

    # Create PVs and link to update logic
    k_value = element.k if element.k is not None else 0.0
    builder.aOut(f"{magnet_name}:Cm:set", initial_value=k_value,
                 on_update=lambda val: handle_element_update(f"{magnet_name}:Cm:set", val, element))
    builder.aOut(f"{magnet_name}:im:I", initial_value=k_value * element.phys2hw * element.brho,
                 on_update=lambda val: handle_element_update(f"{magnet_name}:im:I", val, element))
    builder.aOut(f"{magnet_name}:x:set", initial_value=0.0,
                 on_update=lambda val: handle_element_update(f"{magnet_name}:x:set", val, element))
    builder.aOut(f"{magnet_name}:y:set", initial_value=0.0,
                 on_update=lambda val: handle_element_update(f"{magnet_name}:y:set", val, element))
# Initialize all magnets from DB
# for magnet_data in get_magnets():
#     add_magnet_pvs(magnet_data)
async def update_power_converter(pc_name, value, connected_magnets):
    # Update the readback PV of the power converter
    ctx = Context("pva")
    try:
        await ctx.put(f"Anonym:{pc_name}:rdbk", value)
    except Exception as e:
        logger.info(f"Error updating power converter rdbk {pc_name}: {e}")
    # Update the `im:I` PVs of all connected magnets
    try:
        for magnet_name in connected_magnets:
            await ctx.put(f"Anonym:{magnet_name}:im:I", value)
    except Exception as e:
        logger.info(f"Error updating power converter {pc_name}: {e}")


# Initialize all power converters from DB
def add_pc_pvs(pc_name):
    magnets = get_magnets_per_power_converters(pc_name)
    element = {'magnets': [item['name'] for item in magnets]}
    # Store element in cache
    element_cache[pc_name] = element
    for magnet_data in magnets:
        add_magnet_pvs(magnet_data)
        # def on_update():
        """
        Todo:
            each power converter has list of magnets it is connected to
            this list is stored in the element, 
            we need to update all those magnets (the im:I fields) whenever there is an update to the power converter value
            also update the  rdbk pv as well

        """

    builder.aOut(f"{pc_name}:set", initial_value=0.0,
                 on_update=lambda val: update_power_converter(pc_name, val, element['magnets']))
    # print(f"Updating... {pc_name}:set with {val}"))
    builder.aOut(f"{pc_name}:rdbk", initial_value=0.0)


for pc_name in get_unique_power_converters():
    add_pc_pvs(pc_name)


def initialize_orbit_pvs():
    builder.WaveformOut(f"beam:orbit:x", initial_value=[0.0], length=1000)  # Specify max length
    builder.WaveformOut(f"beam:orbit:y", initial_value=[0.0], length=1000)
    builder.WaveformOut(f"beam:orbit:names", initial_value=[""], length=1000)
    builder.aOut(f"beam:orbit:found", initial_value=0)  # Bool array
    builder.WaveformOut(f"beam:orbit:x0", initial_value=[0.0], length=1000)


def initialize_twiss_pvs():
    builder.WaveformOut(f"beam:twiss:x:alpha", initial_value=[0.0], length=1000)
    builder.WaveformOut(f"beam:twiss:x:beta", initial_value=[0.0], length=1000)
    builder.WaveformOut(f"beam:twiss:x:nu", initial_value=[0.0], length=1000)
    builder.WaveformOut(f"beam:twiss:y:alpha", initial_value=[0.0], length=1000)
    builder.WaveformOut(f"beam:twiss:y:beta", initial_value=[0.0], length=1000)
    builder.WaveformOut(f"beam:twiss:y:nu", initial_value=[0.0], length=1000)
    builder.WaveformOut(f"beam:twiss:names", initial_value=[0.0], length=1000)


def initialize_bpm_pvs():
    tmp = np.empty([2048], np.int16)
    tmp.fill(-2 ** 15)
    builder.WaveformOut(f"MDIZ2T5G:bdata", initial_value=tmp, length=len(tmp),
                        SCAN='1 second')
    # builder.WaveformOut(f"bpm:y", initial_value=0.0)
    # builder.WaveformOut(f"bpm:names", initial_value=0.0)


# Call the initialization functions
initialize_twiss_pvs()
initialize_orbit_pvs()
initialize_bpm_pvs()

builder.longIn("MDIZ2T5G:count", initial_value=0)
builder.LoadDatabase()
softioc.iocInit(dispatcher)

softioc.interactive_ioc(globals())
