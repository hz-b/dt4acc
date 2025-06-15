import os
import sys
from tango import Database, DbDevInfo
from dt4acc.custom_tango.config import SERVER_NAME, SERVER_INSTANCE, DEVICE_NAME_FORMAT
from dt4acc.core.utils.logger import get_logger

path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = get_logger()

def register_twiss_orbit_device():
    """Register the TwissOrbit device in the Tango database."""
    try:

        db = Database()
        

        dev_info = DbDevInfo()
        dev_info.name = f"{SERVER_NAME}/{SERVER_INSTANCE}/{DEVICE_NAME_FORMAT.format(device_type='TwissOrbitDevice', name='twiss_orbit')}"
        dev_info._class = "TwissOrbitDevice"
        dev_info.server = f"{SERVER_NAME}/{SERVER_INSTANCE}"
        

        db.add_device(dev_info)
        logger.info(f"Successfully registered TwissOrbit device: {dev_info.name}")
        
    except Exception as e:
        logger.error(f"Failed to register TwissOrbit device: {e}")
        raise

def setup_twiss_orbit_device():
    """Set up TwissOrbit device in the Tango database."""

    register_twiss_orbit_device()
    logger.info("TwissOrbit device registered successfully")

if __name__ == "__main__":
    setup_twiss_orbit_device() 