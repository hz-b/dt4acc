import numpy as np
import asyncio
from tango import AttrWriteType, DevState, DevFailed
from tango.server import Device, attribute, command

from ....core.utils.logger import get_logger
from ....custom_epics.data.constants import special_pvs
from ....custom_epics.ioc.handlers import update_manager, handle_device_update
from bact_twin_architecture.data_model.identifiers import DevicePropertyID

logger = get_logger()


class MasterClockDevice(Device):
    """Tango device for managing master clock parameters.
    
    This device matches the EPICS master clock PV structure exactly, providing the same
    functionality as the EPICS SoftIOC implementation.
    
    Master clock controls the reference frequency for the entire system.
    """

    def init_device(self):
        """Initialize the device with default values matching EPICS master clock PV setup."""

        logger.warning("\n[DEBUG] Master Clock Device initialized successfully:")
        Device.init_device(self)
        self.set_state(DevState.ON)

        # Initialize master clock data matching EPICS initialize_master_clock_pvs()
        self._initialize_master_clock_data()

        logger.warning(f"  - Device properties: {self._frequency=}, {self._ref_freq=}, {self._ref_freq_khz_up=}, {self._ref_freq_khz_frac=}")
        # logger.info("MasterClockDevice initialized successfully")

        # logger.warning(f"  - Device name from get_name(): {self.name}")
    def _initialize_master_clock_data(self):
        """Initialize master clock data matching EPICS initialize_master_clock_pvs()."""
        try:
            # Get initial value from update manager (matching EPICS behavior)
            vals = update_manager.device_value_from_peeking_engine(
                DevicePropertyID(device_name="master_clock", property="reference_frequency")
            )
            start_val = np.asarray(vals).mean()
        except:
            start_val = 500.0  # Default fallback
            
        self._frequency = start_val
        self._ref_freq = start_val
        self._ref_freq_khz_up = int(start_val)
        self._ref_freq_khz_frac = int((start_val % 1) * 1e6)

    def _run_async_update(self, update_func):
        """Helper method to run async updates."""
        try:
            # Create a new event loop if one doesn't exist
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run the async function
            if loop.is_running():
                # If loop is already running, use run_coroutine_threadsafe
                future = asyncio.run_coroutine_threadsafe(update_func, loop)
                future.result(timeout=10.0)
            else:
                # If loop is not running, run it directly
                loop.run_until_complete(update_func)
                
        except Exception as e:
            logger.error(f"Error in async update: {str(e)}")
            raise DevFailed(f"Update failed: {str(e)}")

    @attribute(
        name=f"{special_pvs['master_clock']}/freq",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        label="Master clock frequency",
        unit="kHz",
        format="%8.3f",
    )
    def frequency(self) -> float:
        """Master clock frequency - equivalent to EPICS {special_pvs['master_clock']}:freq."""
        return self._frequency

    @frequency.write
    def frequency(self, value: float):
        """Set master clock frequency."""
        self._frequency = float(value)
        # Update related values (matching EPICS behavior)
        self._ref_freq = value
        self._ref_freq_khz_up = int(value)
        self._ref_freq_khz_frac = int((value % 1) * 1e6)
        self._run_async_update(handle_device_update("master_clock", "reference_frequency", value))
        logger.info(f"Updated master clock frequency to {value}")

    @attribute(
        name="lattice_info/ref_freq",
        dtype=float,
        access=AttrWriteType.READ,
        label="Lattice reference frequency",
        unit="kHz",
        format="%8.1f",
    )
    def ref_freq(self) -> float:
        """Reference frequency - equivalent to EPICS lattice_info:ref_freq (READ-ONLY).
        
        This value is automatically updated when the main frequency is changed.
        In EPICS, this is implemented as aIn (analog input - read-only).
        """
        return self._ref_freq

    @attribute(
        name="lattice_info/ref_freq/khz/up",
        dtype=int,
        access=AttrWriteType.READ,
        label="Lattice ref freq integer part",
        unit="kHz",
    )
    def ref_freq_khz_up(self) -> int:
        """Reference frequency integer part - equivalent to EPICS lattice_info:ref_freq:khz:up (READ-ONLY).
        
        This value is automatically updated when the main frequency is changed.
        In EPICS, this is implemented as longIn (long integer input - read-only).
        """
        return self._ref_freq_khz_up

    @attribute(
        name="lattice_info/ref_freq/khz/frac",
        dtype=int,
        access=AttrWriteType.READ,
        label="Lattice ref freq fractional part",
        unit="mHz",
    )
    def ref_freq_khz_frac(self) -> int:
        """Reference frequency fractional part - equivalent to EPICS lattice_info:ref_freq:khz:frac (READ-ONLY).
        
        This value is automatically updated when the main frequency is changed.
        In EPICS, this is implemented as longIn (long integer input - read-only).
        """
        return self._ref_freq_khz_frac

    @command(dtype_in=None, doc_in="Reset master clock to initial values")
    def reset(self):
        """Reset master clock to initial values."""
        self._initialize_master_clock_data()
        return "Master clock reset to initial values"

    @command(dtype_in=None, doc_in="Get master clock information")
    def get_master_clock_info(self):
        """Get master clock information."""
        return {
            "frequency": self._frequency,
            "ref_freq": self._ref_freq,
            "ref_freq_khz_up": self._ref_freq_khz_up,
            "ref_freq_khz_frac": self._ref_freq_khz_frac
        } 