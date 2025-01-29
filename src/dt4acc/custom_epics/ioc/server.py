import asyncio
import os

from softioc import softioc, builder, asyncio_dispatcher

from .tasks import monitor_heartbeat
from .pv_setup import (
    initialize_power_converter_pvs,
    initialize_orbit_pvs,
    initialize_bpm_pvs,
    initialize_twiss_pvs,
    initialize_other_pvs,
    initialize_cavity_pvs
)

# Create an asyncio dispatcher to handle asynchronous PV updates
dispatcher = asyncio_dispatcher.AsyncioDispatcher()
# Retrieve the device name prefix from the environment, defaulting to "Anonym" if not set
prefix = os.environ.get("DT4ACC_PREFIX", "Anonym")
builder.SetDeviceName(prefix)


def main():
    """
    Main function to initialize all the process variables (PVs) and start the IOC server.
    """
    # Initialize PVs for various accelerator components
    initialize_power_converter_pvs(builder, prefix)  # Initialize power converters and linked magnets
    initialize_orbit_pvs(builder)  # Initialize orbit-related PVs
    initialize_bpm_pvs(builder)  # Initialize Beam Position Monitor PVs
    initialize_twiss_pvs(builder)  # Initialize Twiss parameter PVs
    initialize_cavity_pvs(builder)  # Initialize cavity-related PVs
    initialize_other_pvs(builder, prefix)  # Initialize additional PVs such as master clock, dummy data

    # Load the database of PVs defined above into the SoftIOC server
    builder.LoadDatabase()
    # Start the SoftIOC server to handle PV interactions
    softioc.iocInit(dispatcher)

    # Start monitoring the heartbeat to ensure the server is running correctly
    asyncio.create_task(monitor_heartbeat())


# Entry point of the script
if __name__ == "__main__":
    # Start the IOC server by dispatching the main function
    dispatcher(main)
    # Start the interactive IOC shell, allowing interaction with the server
    softioc.interactive_ioc(globals())
    # for testing purpose issue a command
