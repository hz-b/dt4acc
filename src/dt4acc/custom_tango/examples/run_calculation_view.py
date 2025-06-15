import asyncio
import numpy as np
from datetime import datetime
import os
import sys
from pathlib import Path
import signal
from dt4acc.core.accelerators.accelerator_manager import AcceleratorManager
from dt4acc.custom_tango.views.calculation_result_view import ResultView
from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_epics.data.constants import special_pvs

# Add the src directory to Python path
src_path = str(Path(__file__).parent.parent.parent.parent)
if src_path not in sys.path:
    sys.path.append(src_path)

from dt4acc.core.model.orbit import Orbit
from dt4acc.core.model.twiss import TwissWithAggregatedKValues, TwissForPlane
from dt4acc.core.model.element_upate import ElementUpdate

logger = get_logger()

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\nReceived interrupt signal. Cleaning up...")
    sys.exit(0)

async def main():
    # Get prefix from environment or use default
    prefix = os.environ.get("DT4ACC_PREFIX", "tango_server/test")
    
    # Initialize result view first
    result_view = ResultView(prefix=prefix)
    await result_view.initialize()
    print("ResultView initialized successfully")
    
    # Initialize accelerator manager with prefix
    accelerator_manager = AcceleratorManager(prefix=prefix)
    
    # Initialize the accelerator manager
    try:
        accelerator_manager.initialize()  # This is synchronous in core
        print("AcceleratorManager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize AcceleratorManager: {e}")
        return
    
    # Set up BPM mimicry
    if accelerator_manager.bpm_mimicry:
        result_view.set_bpm_mimicry(accelerator_manager.bpm_mimicry)
        print("BPM mimicry initialized successfully")
    else:
        logger.warning("Failed to initialize BPM mimicry")
    
    try:
        # Calculate orbit
        print("Starting orbit calculation")
        orbit_result = accelerator_manager.accelerator.calculate_orbit()
        print("Orbit pushing view")
        await result_view.push_orbit(orbit_result)
        
        # Calculate Twiss
        print("Starting Twiss calculation")
        twiss_result = accelerator_manager.accelerator.calculate_twiss()
        print("Twiss pushing view")
        await result_view.push_twiss(twiss_result)
        
        # Push BPM data
        await result_view.push_bpms(orbit_result)
        
        # Start monitoring updates
        print("Starting update monitoring")
        await result_view.monitor_updates()
        
    except Exception as e:
        logger.error(f"Error during calculations: {e}")
        raise

if __name__ == "__main__":
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the async main function
    asyncio.run(main()) 