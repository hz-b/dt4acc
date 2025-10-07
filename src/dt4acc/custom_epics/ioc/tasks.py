import asyncio
import getpass

from p4p.client.asyncio import Context

from ...core.utils.logger import get_logger
from ...core.views.shared_view import get_view_instance

ctx = Context("pva")
logger = get_logger()
view = get_view_instance()
heartbeat_task = None  # Global variable to store the heartbeat task reference


async def monitor_heartbeat():
    """
    Monitors the heartbeat loop and ensures it is running.
    If the heartbeat task is None or has completed, it restarts the task.
    This function runs in an infinite loop with a sleep interval of 1 second.
    """
    global heartbeat_task
    while True:
        if heartbeat_task is None or heartbeat_task.done():
            # todo hardcode the setpoint to a value, so real calculation runs. this needs to be addressed differently
            await ctx.put(f'{getpass.getuser()}:Q2P1L2RP:setCur', 60)
            # await ctx.put(f'{getpass.getuser()}:VS2P2L2RP:rdCur', 0e-3)
            logger.warning("Heartbeat loop initial start or it was terminated unexpectedly. Restarting...")
            heartbeat_task = asyncio.create_task(heartbeat_loop())
        await asyncio.sleep(1)


# Heartbeat loop to push default BPM data
async def heartbeat_loop():
    """
    Periodically triggers the heartbeat function to push default BPM data.
    Runs indefinitely and logs any errors encountered.
    """
    while True:
        try:
            await asyncio.sleep(1)  # Run every second
            # logger.warning("Heartbeat loop was running ...")
            await view.heart_beat()
        except asyncio.CancelledError:
            logger.warning("Heartbeat loop was cancelled.")
            break  # Exit cleanly on cancellation
        except Exception as exc:
            logger.error(f"Heartbeat encountered an error: {exc}")
