from tango.server import run
from .ioc.BPM_setup import setup_bpm_device


SERVER_NAME = "tango_server"
SERVER_CLASS = "TangoServer"
SERVER_INSTANCE = "test"


DEVICE_NAME_FORMAT = "{device_type}_{name}"
FULL_DEVICE_NAME_FORMAT = f"{SERVER_NAME}/{SERVER_INSTANCE}/{{device_name}}"


DEVICE_CLASSES = {
    "MagnetDevice": "MagnetDevice",
    "PowerConverterDevice": "PowerConverterDevice",
    "TwissOrbitDevice": "TwissOrbitDevice",
    "BPMDevice": "BPMDevice"
}

def run_server():
    """Run the Tango server with all device classes."""
    from .ioc.devices.magnet_device import MagnetDevice
    from .ioc.devices.power_converter_device import PowerConverterDevice
    from .ioc.devices.twiss_orbit_device import TwissOrbitDevice
    from .ioc.devices.bpm_device import BPMDevice


    setup_bpm_device()


    run([MagnetDevice, PowerConverterDevice, TwissOrbitDevice, BPMDevice])