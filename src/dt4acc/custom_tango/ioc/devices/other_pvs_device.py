from tango import AttrWriteType, DevState
from tango.server import Device, attribute, command

from ....core.utils.logger import get_logger
from ....custom_epics.data.constants import special_pvs

logger = get_logger()


class OtherPVsDevice(Device):
    """Tango device for managing other PVs (dummy and current values).
    
    This device matches the EPICS other PVs structure exactly, providing the same
    functionality as the EPICS SoftIOC implementation.
    
    Handles dummy values and current values that don't fit into other device categories.
    """

    def init_device(self):
        """Initialize the device with default values matching EPICS other PVs setup."""
        Device.init_device(self)
        self.set_state(DevState.ON)
        
        # Initialize other PVs data matching EPICS initialize_other_pvs()
        self._initialize_other_pvs_data()
        
        logger.info("OtherPVsDevice initialized successfully")

    def _initialize_other_pvs_data(self):
        """Initialize other PVs data matching EPICS initialize_other_pvs()."""
        self._dummy_x = 0
        self._dummy_y = 0
        self._current_current = 0

    @attribute(
        name="dummy/x",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        label="Dummy X value",
    )
    def dummy_x(self) -> float:
        """Dummy X value - equivalent to EPICS dummy:x."""
        return self._dummy_x

    @dummy_x.write
    def dummy_x(self, value: float):
        """Set dummy X value."""
        self._dummy_x = float(value)
        logger.info(f"Updated dummy_x to {value}")

    @attribute(
        name="dummy/y",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        label="Dummy Y value",
    )
    def dummy_y(self) -> float:
        """Dummy Y value - equivalent to EPICS dummy:y."""
        return self._dummy_y

    @dummy_y.write
    def dummy_y(self, value: float):
        """Set dummy Y value."""
        self._dummy_y = float(value)
        logger.info(f"Updated dummy_y to {value}")

    @attribute(
        name=f"{special_pvs['current']}/current",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        label="Current value",
    )
    def current_current(self) -> float:
        """Current value - equivalent to EPICS {special_pvs['current']}:current."""
        return self._current_current

    @current_current.write
    def current_current(self, value: float):
        """Set current value."""
        self._current_current = float(value)
        logger.info(f"Updated current_current to {value}")

    @command(dtype_in=None, doc_in="Reset other PVs to initial values")
    def reset(self):
        """Reset other PVs to initial values."""
        self._initialize_other_pvs_data()
        return "Other PVs reset to initial values"

    @command(dtype_in=None, doc_in="Get other PVs information")
    def get_other_pvs_info(self):
        """Get other PVs information."""
        return {
            "dummy_x": self._dummy_x,
            "dummy_y": self._dummy_y,
            "current_current": self._current_current
        } 