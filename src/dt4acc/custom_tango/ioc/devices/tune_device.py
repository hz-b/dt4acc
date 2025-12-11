import numpy as np
from tango import AttrWriteType, DevState
from tango.server import Device, attribute, command

from ....core.utils.logger import get_logger

logger = get_logger()


class TuneDevice(Device):
    """Tango device for managing tune parameters.
    
    This device matches the EPICS tune PV structure exactly, providing the same
    functionality as the EPICS SoftIOC implementation.
    
    Tune devices manage the betatron tune values for x and y planes and a counter.
    
    EPICS PVs:
        - TUNEZR:rdH (analog output, precision 9)
        - TUNEZR:rdV (analog output, precision 9)
        - TUNEZR:count (long output)

    Todo:
        need to correct the tune names. Will be done as soon
        as tests are run using this twin
    """

    def init_device(self):
        """Initialize the device with default values matching EPICS tune PV setup."""
        Device.init_device(self)
        self.set_state(DevState.ON)

        # Initialize tune data matching EPICS initialize_tune_pvs()
        self._tune_x = 0.0
        self._tune_y = 0.0
        self._count = 0

        logger.warning("TuneDevice initialized successfully")


    @attribute(
        # name="TUNEZR/rdH",
        name="TUNECC/x",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        label="Tune X",
        format="%12.9f",
    )
    def tune_x(self) -> float:
        """Tune value for X plane - equivalent to EPICS TUNECC:x."""
        return self._tune_x

    @tune_x.write
    def tune_x(self, value: float):
        """Set tune X value."""
        self._tune_x = float(value)
        logger.warning(f"Updated tune X to {value}")

    @attribute(
        # name="TUNEZR/rdV",
        name="TUNECC/y",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        label="Tune Y",
        format="%12.9f",
    )
    def tune_y(self) -> float:
        """Tune value for Y plane - equivalent to EPICS TUNECC:y."""
        return self._tune_y

    @tune_y.write
    def tune_y(self, value: float):
        """Set tune Y value."""
        self._tune_y = float(value)
        logger.warning(f"Updated tune Y to {value}")

    @attribute(
        # name="TUNEZR/count",
        name="TUNECC/count",
        dtype=int,
        access=AttrWriteType.READ_WRITE,
        label="Tune count: updates",
    )
    def count(self) -> int:
        """Tune count - equivalent to EPICS TUNEZR:count."""
        return self._count

    @count.write
    def count(self, value: int):
        """Set tune count."""
        self._count = int(value)
        logger.warning(f"Updated tune count to {value}")

    @command(dtype_in=None, doc_in="Reset tune values to defaults")
    def reset(self):
        """Reset tune values to defaults."""
        self._tune_x = 0.0
        self._tune_y = 0.0
        self._count = 0
        logger.warning("Tune device reset to default values")
        return "Tune device reset to default values"

    @command(dtype_in=None, doc_in="Get tune information")
    def get_tune_info(self):
        """Get tune information."""
        return {
            "tune_x": self._tune_x,
            "tune_y": self._tune_y,
            "count": self._count
        }

