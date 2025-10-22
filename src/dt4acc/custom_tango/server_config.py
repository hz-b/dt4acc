SERVER_NAME = "tango_server/test"
INSTANCE_NAME = "test"


SERVER_CLASS = "PowerConverterServer"
SERVER_INSTANCE = f"{SERVER_CLASS}/{INSTANCE_NAME}"


DEVICE_NAME_FORMAT = "{device_type}_{name}"
FULL_DEVICE_NAME_FORMAT = f"{SERVER_NAME}/{{device_name}}"