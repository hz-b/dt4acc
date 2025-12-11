import asyncio
import os
import getpass

from softioc import softioc, builder, asyncio_dispatcher

from ...core.utils.logger import get_logger
from .tasks import monitor_heartbeat
from .pv_setup import (
    initialize_power_converter_pvs,
    initialize_cavity_pvs,
    initialize_master_clock_pvs,
    initialize_orbit_pvs,
    initialize_bpm_pvs,
    initialize_orbit_object_pvs,
    initialize_twiss_pvs,
    initialize_tune_pvs,
    initialize_other_pvs,
)

logger = get_logger()

# Create an asyncio dispatcher to handle asynchronous PV updates
dispatcher = asyncio_dispatcher.AsyncioDispatcher()


def startup():
    """
    Main function to initialize all the process variables (PVs) and start the IOC server.
    """
    # Retrieve the device name prefix from the environment, defaulting to getpass.getuser() if not set
    prefix = os.environ.get("DT4ACC_PREFIX", getpass.getuser())

    builder.SetDeviceName(prefix)

    # initialize_cavity_pvs(builder)  # Initialize cavity-related PVs
    # initialize_master_clock_pvs(builder)  # Initialize additional PVs such as master clock, dummy data
    initialize_other_pvs(builder, prefix)  # Initialize additional PVs such as master clock, dummy data

    # Initialize PVs for various accelerator components
    initialize_power_converter_pvs(builder, prefix)  # Initialize power converters and linked magnets
    initialize_orbit_pvs(builder)  # Initialize orbit-related PVs
    initialize_bpm_pvs(builder)  # Initialize Beam Position Monitor PVs
    initialize_orbit_object_pvs(builder)  # Initialize PV's of the new orbit object ... collection of bpms
    initialize_twiss_pvs(builder)  # Initialize Twiss parameter PVs
    initialize_tune_pvs(builder)
    logger.warning("All pvs set up")

    # Load the database of PVs defined above into the SoftIOC server
    builder.LoadDatabase()
    # Start the SoftIOC server to handle PV interactions
    softioc.iocInit(dispatcher)

    # Start monitoring the heartbeat to ensure the server is running correctly
    asyncio.create_task(monitor_heartbeat(), name="server-heartbeat-loop")


def main():
    # Start the IOC server by dispatching the main function
    dispatcher(startup)
    # Start the interactive IOC shell, allowing interaction with the server
    softioc.interactive_ioc(globals())


# Entry point of the script
if __name__ == "__main__":
    main()