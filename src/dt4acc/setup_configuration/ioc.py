import asyncio
from softioc import softioc, builder, asyncio_dispatcher
from dt4acc.setup_configuration.data_access import get_unique_power_converters, get_magnets
import dt4acc.command as cmd
# Initialize the dispatcher for asyncio
dispatcher = asyncio_dispatcher.AsyncioDispatcher()

# Setup CA PVs
builder.SetDeviceName("Anonym")

# Define the on_update callback function for each power converter PV
async def update_pc(pv, value, type):
    print(f"Updating PV {pv} with value {value}")
    if type in ["pc"]:
        #find all magnets and their power converters and pvput the pc value and cmd.update the k value
        # element_id, property_name, value = None, element
        await cmd.update(element_id=pv, property_name="im", value=value, element=pv)
    # Here you would call your actual logic for pvput to update the twin or process the value
    # Example: `await pva_context.put(pv_name, value)`
    # In your case, call the necessary function to handle the update
    # The pv name can be passed or derived from the context if necessary

# Create the PVs for each power converter from the database
pv_list = []
for magnet_data in get_magnets():
    magnet_name = magnet_data["name"]
    pv = builder.aOut(
        magnet_name + ":Cm:set",
        initial_value=0
    )
    pv_list.append(pv)
    pv = builder.aOut(
        magnet_name + ":x:set",
        initial_value=0
    )
    pv_list.append(pv)
    pv = builder.aOut(
        magnet_name + ":y:set",
        initial_value=0
    )
    pv_list.append(pv)
    pv = builder.aOut(
        magnet_name + ":im:I",
        initial_value=0,
        always_update=True,
        on_update=lambda v, pc=magnet_name: asyncio.create_task(update_pc(pc, v, "magnet"))  # Use async task for updates
    )
    pv_list.append(pv)

for power_converter in get_unique_power_converters():
    pv = builder.aOut(
        power_converter + ":set",
        initial_value=0,
        always_update=True,
        on_update=lambda v, pc=power_converter: asyncio.create_task(update_pc(pc, v, "pc"))  # Use async task for updates
    )
    pv_list.append(pv)

# Boilerplate to start the IOC
builder.LoadDatabase()
softioc.iocInit(dispatcher)

# Example update loop for additional tasks if needed
async def update():
    while True:
        # Your periodic tasks can go here
        await asyncio.sleep(1)

# Start the dispatcher with the update loop
dispatcher(update)

# Start the interactive IOC
softioc.interactive_ioc(globals())