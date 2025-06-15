
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