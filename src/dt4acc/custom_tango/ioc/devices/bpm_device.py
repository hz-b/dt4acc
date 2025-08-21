from tango import DevState, AttrWriteType
from tango.server import Device, attribute, command, device_property
import numpy as np
import itertools
import time
from ....core.utils.logger import get_logger
from ....custom_epics.data.constants import special_pvs, config

logger = get_logger()

class BPMDevice(Device):
    """Tango device for managing BPM (Beam Position Monitor) data.
    
    This device matches the EPICS PV structure exactly, providing the same
    functionality as the EPICS SoftIOC implementation.
    
    Special PVs supported:
    - bpm_pv: MDIZ2T5G (BPM data)
    """

    name = device_property(
        dtype=str,
        default_value="",
        doc="BPM device name"
    )

    def init_device(self):
        """Initialize the device with default values matching EPICS PV setup."""
        Device.init_device(self)
        print(f"[INIT] Initializing {self.get_name()}...")
        self.set_state(DevState.ON)
        
        # Initialize BPM data with default values matching EPICS initialize_bpm_pvs()
        self._initialize_bpm_data()
        self._initialize_special_pvs_data()
        
        logger.info("BPM device initialized successfully")

    def _initialize_bpm_data(self):
        """Initialize BPM data matching EPICS initialize_bpm_pvs()."""
        # BPM data - matching EPICS WaveformOut initialization
        self._bpm_data = np.empty([2048], np.int16)
        self._bpm_data.fill(-(2 ** 15) + 1)
        self._bpm_counter = itertools.count()
        
        # Additional BPM-related data
        self._bpm_x_position = 0.0
        self._bpm_y_position = 0.0
        self._bpm_status = 0
        self._bpm_timestamp = 0.0

    def _initialize_special_pvs_data(self):
        """Initialize special PVs data matching EPICS special_pvs usage."""
        # Special BPM data using special_pvs['bpm_pv']
        self._special_bpm_data = np.empty([2048], np.int16)
        self._special_bpm_data.fill(-(2 ** 15) + 1)
        self._special_bpm_counter = itertools.count()

    @attribute(
        name="bdata",
        dtype=('int16',),
        access=AttrWriteType.READ_WRITE,
        label="BPM data",
        max_dim_x=2048,
    )
    def bpm_data(self):
        """Get BPM data - matching EPICS WaveformOut."""
        return self._bpm_data.tolist()

    @bpm_data.write
    def bpm_data(self, value):
        """Set BPM data - matching EPICS WaveformOut."""
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
        """Get BPM counter value - matching EPICS longOut."""
        return next(self._bpm_counter)

    # Special PVs - matching EPICS special_pvs usage
    @attribute(
        name=f"{special_pvs['bpm_pv']}/bdata",
        dtype=('int16',),
        access=AttrWriteType.READ_WRITE,
        label="Special BPM data",
        max_dim_x=2048,
    )
    def special_bpm_data(self):
        """Get special BPM data using special_pvs['bpm_pv'] name."""
        return self._special_bpm_data.tolist()

    @special_bpm_data.write
    def special_bpm_data(self, value):
        """Set special BPM data using special_pvs['bpm_pv'] name."""
        if len(value) != 2048:
            raise ValueError("Special BPM data must have length 2048")
        self._special_bpm_data = np.array(value, dtype=np.int16)
        logger.info("Updated special BPM data")

    @attribute(
        name=f"{special_pvs['bpm_pv']}/count",
        dtype=int,
        access=AttrWriteType.READ,
        label="Special BPM counter",
    )
    def special_bpm_count(self):
        """Get special BPM counter using special_pvs['bpm_pv'] name."""
        return next(self._special_bpm_counter)

    @attribute(
        name="x_position",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        label="BPM X position",
        unit="mm",
        format="%6.3f",
    )
    def bpm_x_position(self):
        """Get BPM X position."""
        return self._bpm_x_position

    @bpm_x_position.write
    def bpm_x_position(self, value):
        """Set BPM X position."""
        self._bpm_x_position = float(value)
        logger.info("Updated BPM X position")

    @attribute(
        name="y_position",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        label="BPM Y position",
        unit="mm",
        format="%6.3f",
    )
    def bpm_y_position(self):
        """Get BPM Y position."""
        return self._bpm_y_position

    @bpm_y_position.write
    def bpm_y_position(self, value):
        """Set BPM Y position."""
        self._bpm_y_position = float(value)
        logger.info("Updated BPM Y position")

    @attribute(
        name="status",
        dtype=int,
        access=AttrWriteType.READ_WRITE,
        label="BPM status",
    )
    def bpm_status(self):
        """Get BPM status."""
        return self._bpm_status

    @bpm_status.write
    def bpm_status(self, value):
        """Set BPM status."""
        self._bpm_status = int(value)
        logger.info("Updated BPM status")

    @attribute(
        name="timestamp",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        label="BPM timestamp",
        unit="s",
        format="%12.6f",
    )
    def bpm_timestamp(self):
        """Get BPM timestamp."""
        return self._bpm_timestamp

    @bpm_timestamp.write
    def bpm_timestamp(self, value):
        """Set BPM timestamp."""
        self._bpm_timestamp = float(value)
        logger.info("Updated BPM timestamp")

    @command
    def reset(self):
        """Reset BPM data to default values - matching EPICS initialization."""
        self._initialize_bpm_data()
        self._initialize_special_pvs_data()
        logger.info("BPM device reset to default values")

    @command
    def update_data(self, data):
        """Update BPM data with new values."""
        if len(data) != 2048:
            raise ValueError("BPM data must have length 2048")
        self._bpm_data = np.array(data, dtype=np.int16)
        self._bpm_timestamp = time.time()
        logger.info("Updated BPM data via command")

    @command
    def update_position(self, x, y):
        """Update BPM position values."""
        self._bpm_x_position = float(x)
        self._bpm_y_position = float(y)
        self._bpm_timestamp = time.time()
        logger.info(f"Updated BPM position: x={x}, y={y}")

    @command
    def get_special_pvs_info(self):
        """Get information about special PVs configuration."""
        return {
            "bpm_pv": special_pvs["bpm_pv"],
            "description": "Special BPM PV mapping from EPICS constants"
        } 