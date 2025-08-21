import numpy as np
from tango import AttrWriteType, DevState
from tango.server import Device, attribute, command

from ....core.utils.logger import get_logger
from ....custom_epics.data.constants import cavity_names
from dt4acc.custom_tango.ioc.devices.async_wrapper import run_async_in_background
from dt4acc.custom_epics.ioc.handlers import update_manager, handle_device_update
from bact_twin_architecture.data_model.identifiers import DevicePropertyID

logger = get_logger()


class CavityDevice(Device):
    """Tango device for managing RF cavity parameters.
    
    This device matches the EPICS cavity PV structure exactly, providing the same
    functionality as the EPICS SoftIOC implementation.
    
    Each cavity device represents a single RF cavity with its frequency control.
    """

    def init_device(self):
        """Initialize the device with default values matching EPICS cavity PV setup."""
        Device.init_device(self)
        self.set_state(DevState.ON)
        
        # Extract cavity name from device name (e.g., "cavity_CAVH4T8R" -> "CAVH4T8R")
        device_name = self.get_name()
        if "cavity_" in device_name:
            self._cavity_name = device_name.split("cavity_")[-1]
        else:
            # Fallback: try to get from device property
            try:
                self._cavity_name = self.cavity_name
            except:
                # Final fallback: use first cavity name
                from ....custom_epics.data.constants import cavity_names
                self._cavity_name = cavity_names[0] if cavity_names else "CAVH4T8R"
        
        if not self._cavity_name:
            raise ValueError("Could not determine cavity name from device name or properties")
        
        # Initialize cavity data matching EPICS initialize_cavity_pvs()
        self._initialize_cavity_data()
        
        logger.info(f"CavityDevice {self._cavity_name} initialized successfully")

    def _initialize_cavity_data(self):
        """Initialize cavity data matching EPICS initialize_cavity_pvs()."""
        try:
            # Get initial value from update manager (matching EPICS behavior)
            vals = update_manager.device_value_from_peeking_engine(
                DevicePropertyID(device_name=self._cavity_name, property="frequency")
            )
            start_val = np.asarray(vals).mean()
        except:
            start_val = 500.0  # Default fallback
            
        self._frequency = start_val

    @attribute(
        name="frequency",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        label="Cavity frequency",
        unit="kHz",
        format="%8.3f",
    )
    def frequency(self) -> float:
        """Cavity frequency - equivalent to EPICS {cavity_name}:freq."""
        return self._frequency

    @frequency.write
    def frequency(self, value: float):
        """Set cavity frequency."""
        self._frequency = float(value)
        # Use async wrapper to call handle_device_update
        run_async_in_background(handle_device_update)(self._cavity_name, "frequency", value)
        logger.info(f"Updated cavity {self._cavity_name} frequency to {value}")

    @command(dtype_in=None, doc_in="Reset the cavity")
    def reset(self):
        """Reset cavity to default values."""
        self._initialize_cavity_data()
        return f"Cavity {self._cavity_name} reset to default values"

    @command(dtype_in=None, doc_in="Get cavity information")
    def get_cavity_info(self):
        """Get cavity information."""
        return {
            "cavity_name": self._cavity_name,
            "frequency": self._frequency
        } 