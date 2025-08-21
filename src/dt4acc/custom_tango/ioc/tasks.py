import asyncio
import getpass

from ...core.utils.logger import get_logger
from ...core.views.shared_view import get_view_instance

logger = get_logger()
view = get_view_instance()
heartbeat_task = None  


async def monitor_heartbeat():
    """
    Monitors the heartbeat loop and ensures it is running.
    If the heartbeat task is None or has completed, it restarts the task.
    This function runs in an infinite loop with a sleep interval of 1 second.
    """
    global heartbeat_task
    print("💓 monitor_heartbeat() started")
    logger.info("💓 monitor_heartbeat() started")
    
    iteration = 0
    while True:
        iteration += 1
        print(f"💓 monitor_heartbeat() iteration {iteration}")
        logger.info(f"💓 monitor_heartbeat() iteration {iteration}")
        
        if heartbeat_task is None or heartbeat_task.done():
            # todo hardcode the setpoint to a value, so real calculation runs. this needs to be addressed differently
            # This matches EPICS behavior exactly - setting initial values to trigger calculations
            try:
                print(f"💓 Starting new heartbeat task (iteration {iteration})")
                logger.info(f"💓 Starting new heartbeat task (iteration {iteration})")
                
                await set_initial_power_converter_values()
                logger.warning("Heartbeat loop initial start or it was terminated unexpectedly. Restarting...")
                heartbeat_task = asyncio.create_task(heartbeat_loop())
                
                print(f"💓 Heartbeat task created successfully (iteration {iteration})")
                logger.info(f"💓 Heartbeat task created successfully (iteration {iteration})")
                
            except Exception as e:
                logger.error(f"Failed to set initial values: {e}")
                print(f"❌ Failed to set initial values: {e}")
                # Continue anyway to avoid blocking heartbeat
                heartbeat_task = asyncio.create_task(heartbeat_loop())
        else:
            print(f"💓 Heartbeat task is running (iteration {iteration})")
            logger.debug(f"💓 Heartbeat task is running (iteration {iteration})")
        
        await asyncio.sleep(5)  # Increased interval to reduce conflicts


async def set_initial_power_converter_values():
    """
    Set initial power converter values to trigger real calculations.
    This matches EPICS behavior exactly.
    """
    try:
        from tango import DeviceProxy
        
        # Use the same element as EPICS: VS3P2T5R
        element_id = "VS3P2T5R"
        
        # Use correct Tango device naming format: server_name/instance_name/device_name
        device_patterns = [
            f"SimpleTangoServer/test/power_converter_{element_id}",
            f"SimpleTangoServer/test/PowerConverterDevice_{element_id}",
            f"SimpleTangoServer/test/power_converter_device_{element_id}"
        ]
        
        for device_name in device_patterns:
            try:
                device = DeviceProxy(device_name)
                # Set initial values to trigger calculations (matching EPICS behavior exactly)
                device.write_attribute("set", 1e-3)
                await asyncio.sleep(0.1)  # Brief pause like EPICS
                device.write_attribute("set", 0e-3)
                logger.info(f"Set initial values for power converter {device_name}")
                print(f"✅ Set initial values for power converter {device_name}")
                return  # Success, exit function
            except Exception as e:
                logger.debug(f"Could not set values for {device_name}: {e}")
                print(f"⚠️  Could not set values for {device_name}: {e}")
                continue
        
        # If all patterns fail, log warning but don't fail
        logger.warning(f"Could not set initial values for any power converter pattern")
        print(f"⚠️  Could not set initial values for any power converter pattern")
        
    except Exception as e:
        logger.error(f"Failed to set initial power converter values: {e}")
        print(f"❌ Failed to set initial power converter values: {e}")


# Heartbeat loop to push default BPM data
async def heartbeat_loop():
    """
    Periodically triggers the heartbeat function to push default BPM data.
    Runs indefinitely and logs any errors encountered.
    """
    print("💓 heartbeat_loop() started")
    logger.info("💓 heartbeat_loop() started")
    
    iteration = 0
    while True:
        iteration += 1
        try:
            print(f"💓 heartbeat_loop() iteration {iteration}")
            logger.debug(f"💓 heartbeat_loop() iteration {iteration}")
            
            await asyncio.sleep(5)  # Increased interval to reduce conflicts 
            
            
            print(f"💓 Calling view.heart_beat() (iteration {iteration})")
            logger.debug(f"💓 Calling view.heart_beat() (iteration {iteration})")
            
            await view.heart_beat()
            
            print(f"💓 view.heart_beat() completed (iteration {iteration})")
            logger.debug(f"💓 view.heart_beat() completed (iteration {iteration})")
            
        except asyncio.CancelledError:
            logger.warning("Heartbeat loop was cancelled.")
            print("💓 Heartbeat loop was cancelled.")
            break  # Exit cleanly on cancellation
        except Exception as exc:
            logger.error(f"Heartbeat encountered an error: {exc}")
            print(f"❌ Heartbeat encountered an error: {exc}") 