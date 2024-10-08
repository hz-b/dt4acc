from softioc import softioc, builder, asyncio_dispatcher

import dt4acc.command as cmd
from dt4acc.model.elementmodel import MagnetElementSetup
from dt4acc.setup_configuration.data_access import get_magnets, get_unique_power_converters

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
        brho=5.67229387129245,
        edf=1 / 5.67229387129245,
        pc=magnet['pc']
    )
    # Store element in cache
    element_cache[magnet_name] = element

    # Create PVs and link to update logic
    builder.aOut(f"{magnet_name}:Cm:set", initial_value=0.0,
                 on_update=lambda val: handle_element_update(f"{magnet_name}:Cm:set", val, element))
    builder.aOut(f"{magnet_name}:im:I", initial_value=0.0,
                 on_update=lambda val: handle_element_update(f"{magnet_name}:im:I", val, element))


# Initialize all magnets from DB
for magnet_data in get_magnets():
    add_magnet_pvs(magnet_data)


# Initialize all power converters from DB
def add_pc_pvs(pc_name):
    builder.aOut(f"{pc_name}:set", initial_value=0.0, on_update=lambda val: print(f"Update {pc_name}:set with {val}"))
    builder.aOut(f"{pc_name}:rdbk", initial_value=0.0)


for pc_name in get_unique_power_converters():
    add_pc_pvs(pc_name)

def initialize_orbit_pvs():
    builder.aOut(f"orbit:x", initial_value=0.0)
    builder.aOut(f"orbit:y", initial_value=0.0)
    builder.aOut(f"orbit:names", initial_value=0.0)
    builder.aOut(f"orbit:found", initial_value=0)
    builder.aOut(f"orbit:x0", initial_value=0.0)

def initialize_twiss_pvs():
    builder.aOut(f"twiss:x:alpha", initial_value=0.0)
    builder.aOut(f"twiss:x:beta", initial_value=0.0)
    builder.aOut(f"twiss:x:nu", initial_value=0.0)
    builder.aOut(f"twiss:y:alpha", initial_value=0.0)
    builder.aOut(f"twiss:y:beta", initial_value=0.0)
    builder.aOut(f"twiss:y:nu", initial_value=0.0)
    builder.aOut(f"twiss:names", initial_value=0.0)

def initialize_bpm_pvs():
    builder.aOut(f"bpm:x", initial_value=0.0)
    builder.aOut(f"bpm:y", initial_value=0.0)
    builder.aOut(f"bpm:names", initial_value=0.0)

# Call the initialization functions
initialize_twiss_pvs()
initialize_orbit_pvs()
initialize_bpm_pvs()

builder.LoadDatabase()
softioc.iocInit(dispatcher)

softioc.interactive_ioc(globals())
