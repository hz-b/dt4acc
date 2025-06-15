from tango import DevState, AttrWriteType
from tango.server import Device, attribute, command, device_property
import numpy as np
import itertools
from ....core.utils.logger import get_logger
from ....custom_epics.data.constants import special_pvs

logger = get_logger()

class BPMDevice(Device):
    """Tango device for managing BPM (Beam Position Monitor) data."""


    name = device_property(
        dtype=str,
        default_value="",
        doc="BPM device name"
    )

    def init_device(self):
        """Initialize the device."""
        Device.init_device(self)
        print(f"[INIT] Initializing {self.get_name()}...")
        self.set_state(DevState.ON)
        
        # Initialize BPM data with default values
        self._bpm_data = np.empty([2048], np.int16)
        self._bpm_data.fill(-(2 ** 15) + 1)
        self._bpm_counter = itertools.count()
        
        logger.info("BPM device initialized successfully")

    @attribute(
        name="bdata",
        dtype=('int16',),
        access=AttrWriteType.READ_WRITE,
        label="BPM data",
        max_dim_x=2048,
    )
    def bpm_data(self):
        """Get BPM data."""
        return self._bpm_data.tolist()

    @bpm_data.write
    def bpm_data(self, value):
        """Set BPM data."""
        if len(value) != 2048:
            raise ValueError("BPM data must have length 2048")
        self._bpm_data = np.array(value, dtype=np.int16)
        logger.info("Updated BPM data")

    @attribute(
        name="count",
        dtype=int,
        access=AttrWriteType.READ,
        label="BPM counter",
    )
    def bpm_count(self):
        """Get BPM counter value."""
        return next(self._bpm_counter)

    @command
    def reset(self):
        """Reset BPM data to default values."""
        self._bpm_data = np.empty([2048], np.int16)
        self._bpm_data.fill(-(2 ** 15) + 1)
        self._bpm_counter = itertools.count()
        logger.info("BPM device reset to default values") 