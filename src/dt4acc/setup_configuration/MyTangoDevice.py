from itertools import count

from tango import AttrWriteType, DevState
from tango.server import (
    Device,
    attribute,
    command,
    device_property
)

import dt4acc.command as cmd


class MyTangoDevice(Device):
    # Define device attributes
    DeviceName = device_property(dtype=str)
    bdata = attribute(dtype=('double',), max_dim_x=2, access=AttrWriteType.READ_WRITE,
                      unit="mm", format="%8.2f", doc="Block data as an array of doubles")

    def init_device(self):
        Device.init_device(self)
        self.set_state(DevState.ON)
        self.set_status("Device is in ON state")
        self._bdata = [0.0, 0.0]
        self.counter = count()

    def read_bdata(self):
        cnt = next(self.counter)
        return [cnt, -cnt]

    def write_bdata(self, value):
        FamName = self.DeviceName
        cmd.update(element_id=FamName, property_name="dx", value=value)
        self._bdata = value

    @command
    def resetbdata(self):
        self._bdata = [0.0, 0.0]
        return "block data reset to [0.0, 0.0]"

    # Define methods for specific functionalities
    @command
    def update_value(self, value):
        # Implement logic to update the internal value based on received value
        # You can access other attributes using self.name, etc.
        # ...
        pass

    # Add more commands as needed


# Run the server
if __name__ == "__main__":
    MyTangoDevice.run_server()
