import os
import sys
from tango import Database, DbDevInfo
from dt4acc.custom_tango.config import SERVER_NAME, SERVER_INSTANCE, DEVICE_NAME_FORMAT
from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_epics.data.constants import special_pvs

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = get_logger()

def register_bpm_device(bpm_name: str):
    """Register a BPM device in the Tango database."""
    try:
        # Connect to the Tango database
        db = Database()
        
        # Create device info
        dev_info = DbDevInfo()
        dev_info.name = f"{SERVER_NAME}/{SERVER_INSTANCE}/{DEVICE_NAME_FORMAT.format(device_type='BPMDevice', name=bpm_name)}"
        dev_info._class = "BPMDevice"
        dev_info.server = f"{SERVER_NAME}/{SERVER_INSTANCE}"
        
        # Add device to database
        db.add_device(dev_info)
        print(f"Successfully registered BPM device: {dev_info.name}")
        
    except Exception as e:
        logger.error(f"Failed to register BPM device: {e}")
        raise

def setup_bpm_device():
    """Set up BPM device in the Tango database."""
    # Register BPM device
    register_bpm_device(special_pvs['bpm_pv'])
    logger.info("BPM device registered successfully")

def main():
    """Main function to run BPM setup independently."""
    try:
        logger.info("Starting BPM device setup...")
        setup_bpm_device()
        logger.info("BPM device setup completed successfully")
    except Exception as e:
        logger.error(f"BPM device setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 