from tango import DeviceProxy, DevState, AttrWriteType, AttrDataFormat, DevString, DevFailed
from tango.server import Device, attribute, command, device_property
import numpy as np
from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_epics.data.querries import get_unique_power_converters, get_magnets_per_power_converters
from dt4acc.custom_epics.ioc.handlers import update_manager, handle_device_update
from dt4acc.custom_epics.data.constants import special_pvs, cavity_names
from dt4acc.core.command import UpdateManager
from bact_twin_architecture.data_model.identifiers import DevicePropertyID
from dt4acc.custom_tango.ioc.devices.async_wrapper import run_async_in_background

logger = get_logger()

class PowerConverterDevice(Device):
    """
    Tango device class for controlling power converters in the accelerator.

    """
    
    # Device properties
    magnet_list = device_property(
        dtype=(str,),
        default_value=[],
        doc="List of associated magnets"
    )
    
    name = device_property(
        dtype=str,
        default_value="",  # Add default value
        doc="Power converter name"
    )
    
    def init_device(self):
        """Initialize the device."""
        try:
            print("\n[DEBUG] Initializing PowerConverterDevice:")
            print("  - Getting device properties")
            dev_prop = self.get_device_properties()
            print(f"  - Device properties: {dev_prop}")
            
            # Get device name from properties
            if not hasattr(dev_prop, 'name') or not dev_prop.name:
                print("  - ERROR: Device name property not set")
                # Try to get name from device name
                device_name = self.get_name()
                print(f"  - Device name from get_name(): {device_name}")
                if device_name:
                    # Extract name from device name (format: tango_server/test/PowerConverterDevice_HS1MD4R)
                    try:
                        self.name = device_name.split('_')[-1]
                        print(f"  - Extracted name from device name: {self.name}")
                    except:
                        print("  - Could not extract name from device name")
                        raise DevFailed("Device name property not set")
                else:
                    raise DevFailed("Device name property not set")
            
            print(f"  - Device name: {self.name}")
            
            # Initialize update manager
            try:
                print("  - Initializing update manager")
                # Use the global update_manager from handlers
                self.update_manager = update_manager
                print("  - Update manager initialized successfully")
            except Exception as e:
                print(f"  - ERROR: Failed to initialize update manager: {str(e)}")
                raise
            
            # Initialize attributes
            try:
                print("  - Initializing attributes")
                self._init_attributes()
                print("  - Attributes initialized successfully")
            except Exception as e:
                print(f"  - ERROR: Failed to initialize attributes: {str(e)}")
                raise
            
            print("  - Device initialization completed successfully")
            
        except Exception as e:
            print(f"\n[ERROR] Device initialization failed:")
            print(f"  - Error: {str(e)}")
            raise
        
        # Get associated magnets from EPICS query
        try:
            magnets = get_magnets_per_power_converters(self.name)
            if magnets:
                self._magnets = [item["name"] for item in magnets]
                self._element_cache = {self.name: {"magnets": self._magnets}}
            else:
                self._magnets = list(self.magnet_list)  # Fallback to property value
                self._element_cache = {self.name: {"magnets": self._magnets}}
        except Exception as e:
            logger.warning(f"Could not get magnets from EPICS query: {str(e)}")
            self._magnets = list(self.magnet_list)  # Fallback to property value
            self._element_cache = {self.name: {"magnets": self._magnets}}
        
        # Get initial values from update manager (matching EPICS implementation)
        try:
            vals = update_manager.device_value_from_peeking_engine(
                DevicePropertyID(device_name=self.name, property="set_current")
            )
            start_val = np.asarray(vals).mean() if isinstance(vals, (list, np.ndarray)) else vals
        except Exception as e:
            logger.warning(f"Could not get initial values from update manager: {str(e)}")
            start_val = 0.0
        
        # Initialize attributes with default values
        self._current_setpoint = start_val  # :set in EPICS
        self._current_readback = start_val  # :rdbk in EPICS
        self._voltage = 0.0
        self._status = "OFF"
        
        # Initialize frequency from master clock if this is a cavity power converter
        try:
            if self.name in cavity_names:
                vals = update_manager.device_value_from_peeking_engine(
                    DevicePropertyID(device_name="master_clock", property="reference_frequency")
                )
                self._frequency = np.asarray(vals).mean() if isinstance(vals, (list, np.ndarray)) else vals
            else:
                self._frequency = 0.0
        except Exception as e:
            logger.warning(f"Could not get frequency from master clock: {str(e)}")
            self._frequency = 0.0
            
        logger.info(f"Initialized power converter device {self.name} with {len(self._magnets)} associated magnets")
        
    def _init_attributes(self):
        """Initialize device attributes with default values."""
        try:
            print("  - Initializing device attributes")
            
            # Get associated magnets from EPICS query
            try:
                magnets = get_magnets_per_power_converters(self.name)
                if magnets:
                    self._magnets = [item["name"] for item in magnets]
                    self._element_cache = {self.name: {"magnets": self._magnets}}
                else:
                    self._magnets = list(self.magnet_list)  # Fallback to property value
                    self._element_cache = {self.name: {"magnets": self._magnets}}
                print(f"    * Associated magnets: {self._magnets}")
            except Exception as e:
                logger.warning(f"Could not get magnets from EPICS query: {str(e)}")
                self._magnets = list(self.magnet_list)  # Fallback to property value
                self._element_cache = {self.name: {"magnets": self._magnets}}
            
            # Get initial values from update manager
            try:
                vals = update_manager.device_value_from_peeking_engine(
                    DevicePropertyID(device_name=self.name, property="set_current")
                )
                start_val = np.asarray(vals).mean() if isinstance(vals, (list, np.ndarray)) else vals
                print(f"    * Initial current value: {start_val}")
            except Exception as e:
                logger.warning(f"Could not get initial values from update manager: {str(e)}")
                start_val = 0.0
            
            # Initialize attributes with default values
            self._current_setpoint = start_val  # :set in EPICS
            self._current_readback = start_val  # :rdbk in EPICS
            self._voltage = 0.0
            self._status = "OFF"
            
            # Initialize frequency from master clock if this is a cavity power converter
            try:
                if self.name in cavity_names:
                    vals = update_manager.device_value_from_peeking_engine(
                        DevicePropertyID(device_name="master_clock", property="reference_frequency")
                    )
                    self._frequency = np.asarray(vals).mean() if isinstance(vals, (list, np.ndarray)) else vals
                    print(f"    * Initial frequency value: {self._frequency}")
                else:
                    self._frequency = 0.0
            except Exception as e:
                logger.warning(f"Could not get frequency from master clock: {str(e)}")
                self._frequency = 0.0
            
            print("    * All attributes initialized successfully")
            
        except Exception as e:
            print(f"    * ERROR: Failed to initialize attributes: {str(e)}")
            raise

    # Current control attributes
    @attribute(dtype=float, access=AttrWriteType.READ_WRITE)
    def current_setpoint(self):
        """Get current setpoint (:set in EPICS)."""
        return self._current_setpoint
        
    @current_setpoint.write
    def current_setpoint(self, value):
        """Set current setpoint (:set in EPICS)."""
        try:
            self._current_setpoint = float(value)
            # Use EPICS update handler with async wrapper to avoid coroutine warning
            run_async_in_background(handle_device_update)(self.name, "set_current", value)
            # Update readback to match EPICS behavior
            self._current_readback = value
            logger.info(f"Updated current setpoint to {value}")
        except Exception as e:
            logger.error(f"Error updating current setpoint: {str(e)}")
            raise
        
    @attribute(dtype=float)
    def current_readback(self):
        """Get current readback (:rdbk in EPICS)."""
        return self._current_readback
        
    @attribute(dtype=float)
    def voltage(self):
        """Get voltage."""
        return self._voltage
        
    @attribute(dtype=str)
    def status(self):
        """Get status."""
        return self._status
        
    @attribute(dtype=float, access=AttrWriteType.READ_WRITE)
    def frequency(self):
        """Get frequency (freq in EPICS for cavities)."""
        return self._frequency
        
    @frequency.write
    def frequency(self, value):
        """Set frequency (freq in EPICS for cavities)."""
        try:
            if self.name in cavity_names:
                self._frequency = float(value)
                # Use EPICS update handler for master clock with async wrapper to avoid coroutine warning
                run_async_in_background(handle_device_update)("master_clock", "reference_frequency", value)
                logger.info(f"Updated frequency to {value}")
            else:
                logger.warning(f"Frequency control not available for non-cavity power converter {self.name}")
        except Exception as e:
            logger.error(f"Error updating frequency: {str(e)}")
            raise
        
    @attribute(dtype=(str,), format=AttrDataFormat.SPECTRUM)
    def associated_magnets(self):
        """Get associated magnets."""
        return self._magnets
        
    # Commands
    @command(dtype_in=None, doc_in="Turn on the power converter")
    def turn_on(self):
        """Turn on the power converter."""
        try:
            self._status = "ON"
            self.set_state(DevState.ON)
            logger.info(f"Power converter {self.name}: Turned on")
        except Exception as e:
            logger.error(f"Error turning on power converter: {str(e)}")
            raise
        
    @command(dtype_in=None, doc_in="Turn off the power converter")
    def turn_off(self):
        """Turn off the power converter."""
        try:
            self._status = "OFF"
            self.set_state(DevState.OFF)
            logger.info(f"Power converter {self.name}: Turned off")
        except Exception as e:
            logger.error(f"Error turning off power converter: {str(e)}")
            raise
        
    @command(dtype_in=None, doc_in="Reset the power converter to its default state")
    def reset(self):
        """Reset the power converter to its default state."""
        try:
            self._current_setpoint = 0.0
            self._current_readback = 0.0
            self._voltage = 0.0
            if self.name in cavity_names:
                vals = update_manager.device_value_from_peeking_engine(
                    DevicePropertyID(device_name="master_clock", property="reference_frequency")
                )
                self._frequency = np.asarray(vals).mean() if isinstance(vals, (list, np.ndarray)) else vals
            else:
                self._frequency = 0.0
            self.set_state(DevState.OFF)
            logger.info(f"Power converter {self.name}: Reset to default state")
        except Exception as e:
            logger.error(f"Error resetting power converter: {str(e)}")
            raise 