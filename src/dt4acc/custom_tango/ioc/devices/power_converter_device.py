from tango import DeviceProxy, DevState, AttrWriteType, AttrDataFormat, DevString, DevFailed
from tango.server import Device, attribute, command, device_property
import numpy as np
from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_epics.data.querries import get_unique_power_converters, get_magnets_per_power_converters
from dt4acc.custom_epics.ioc.handlers import update_manager, handle_device_update
from dt4acc.custom_epics.ioc.liasion_translation_manager import build_managers
from bact_twin_architecture.data_model.identifiers import DevicePropertyID, ConversionID
from dt4acc.custom_tango.ioc.devices.async_wrapper import run_async_in_background


logger = get_logger()

class PowerConverterDevice(Device):
    """
    Simplified Tango device class for controlling power converters in the accelerator.
    Removes unnecessary event loops and complex async logic.
    """
    
    # Device properties (matching EPICS)
    name = device_property(
        dtype=str,
        default_value="", 
        doc="Power converter name"
    )
    
    def init_device(self):
        """Initialize the device - simplified without event loops."""
        try:
            dev_prop = self.get_device_properties()
            
            if not hasattr(dev_prop, 'name') or not dev_prop.name:
                device_name = self.get_name()
                if device_name:
                    try:
                        self.name = device_name.split('_')[-1]
                    except:
                        raise DevFailed("Device name property not set")
                else:
                    raise DevFailed("Device name property not set")
            
            # Initialize liaison manager and translation service
            try:
                self.liaison_manager, self.translator_service = build_managers()
            except Exception as e:
                logger.error(f"Failed to initialize liaison manager: {str(e)}")
                raise
            
            try:
                self.update_manager = update_manager
            except Exception as e:
                raise
            
            # Initialize attributes
            try:
                self._init_attributes()
            except Exception as e:
                raise
            
            # Set device state to ON
            self.set_state(DevState.ON)
            
        except Exception as e:
            logger.error(f"Device initialization failed: {str(e)}")
            raise
            
    def _validate_power_converter_update(self, value, property_name):
        """Validate power converter parameter updates using liaison manager."""
        try:
            # Create device property ID for validation
            device_property_id = DevicePropertyID(device_name=self.name, property=property_name)
            
            # Check if this device property is known to the liaison manager
            lattice_properties = self.liaison_manager.inverse(device_property_id)
            
            if not lattice_properties:
                raise DevFailed(f"Device property {property_name} for power converter {self.name} not found in liaison manager - update not allowed")
            
            # Validate the value is numeric and reasonable
            if not isinstance(value, (int, float)) or np.isnan(value) or np.isinf(value):
                raise DevFailed(f"Invalid value {value} for property {property_name}")
            
            # Check if conversion is available
            for lattice_property in lattice_properties:
                conversion_id = ConversionID(
                    lattice_property_id=lattice_property,
                    device_property_id=device_property_id
                )
                try:
                    conversion = self.translator_service.get(conversion_id)
                    logger.info(f"Found conversion for {conversion_id}")
                except KeyError:
                    logger.warning(f"No conversion found for {conversion_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Validation failed for {property_name}: {str(e)}")
            raise DevFailed(f"Validation failed: {str(e)}")
            
    def _apply_power_converter_update(self, value, property_name):
        """Apply power converter parameter update using async wrapper."""
        try:
            # CALL THE EXACT SAME FUNCTIONS AS EPICS pv_setup.py
            # This matches the EPICS implementation exactly:
            # - handle_pc_update(pc_name, "set_current", val) for power converter current
            
            if property_name == "set_current":
                # Power converter current update (pc_name:set in EPICS)
                logger.info(f"{self.name}:set_current setting setpoint val={value}")
                # Use async wrapper to call handle_device_update
                run_async_in_background(handle_device_update)(self.name, "set_current", value)
                
            else:
                # Fallback to the property name
                logger.info(f"{self.name}:{property_name} setting setpoint val={value}")
                # Use async wrapper to call handle_device_update
                run_async_in_background(handle_device_update)(self.name, property_name, value)
                    
        except Exception as e:
            logger.error(f"Error in _apply_power_converter_update: {str(e)}")
            # Don't raise here, just log the error
        
    def _is_property_mapped(self, property_name):
        """Check if a property is mapped in the liaison manager."""
        try:
            device_property_id = DevicePropertyID(device_name=self.name, property=property_name)
            lattice_properties = self.liaison_manager.inverse(device_property_id)
            return bool(lattice_properties)
        except Exception as e:
            logger.error(f"Error checking property mapping: {str(e)}")
            return False
        
    def _init_attributes(self):
        """Initialize device attributes (matching EPICS exactly)."""
        try:
            # Get initial values from update manager (matching EPICS)
            vals = update_manager.device_value_from_peeking_engine(
                DevicePropertyID(device_name=self.name, property="set_current")
            )
            start_val = np.asarray(vals).mean()
            
            # Initialize attributes with values (matching EPICS exactly)
            self._current_setpoint = start_val  # Matches EPICS pc_name:set initial_value
            self._current_readback = start_val  # Matches EPICS pc_name:rdbk initial_value
                
        except Exception as e:
            logger.error(f"Error initializing attributes: {str(e)}")
            raise
        
    # EPICS-Matching Attributes (EXACTLY as in EPICS pv_setup.py)
    
    @attribute(dtype=float, access=AttrWriteType.READ_WRITE)
    def current_setpoint(self):
        """Get current setpoint (pc_name:set in EPICS)."""
        return self._current_setpoint
        
    @current_setpoint.write
    def current_setpoint(self, value):
        """Set current setpoint (pc_name:set in EPICS)."""
        try:
            # Check if this property is mapped in liaison manager
            if not self._is_property_mapped("set_current"):
                raise DevFailed(f"Current setpoint updates not allowed for power converter {self.name} - property not mapped in liaison manager")
            
            # Validate the update
            self._validate_power_converter_update(value, "set_current")
            
            # Apply the update using the same function as EPICS pv_setup.py
            # EPICS: handle_pc_update(pc_name, "set_current", val)
            self._apply_power_converter_update(value, "set_current")
            
            # Update local state (matching EPICS)
            self._current_setpoint = float(value)
            self._current_readback = value
            
            logger.info(f"Updated current setpoint to {value} for {self.name}")
            
        except Exception as e:
            logger.error(f"Error updating current setpoint: {str(e)}")
            raise
        
    @attribute(dtype=float)
    def current_readback(self):
        """Get current readback (pc_name:rdbk in EPICS)."""
        return self._current_readback
        
    # Commands
    @command(dtype_in=str, dtype_out=str)
    def get_power_converter_info(self, argin):
        """Get power converter information (matching EPICS info commands)."""
        try:
            info = f"Power Converter: {self.name}\n"
            info += f"Current Setpoint: {self._current_setpoint}\n"
            info += f"Current Readback: {self._current_readback}\n"
            info += f"State: {self.get_state()}\n"
            return info
        except Exception as e:
            logger.error(f"Error getting power converter info: {str(e)}")
            raise DevFailed(f"Error getting power converter info: {str(e)}")
    
    @command(dtype_in=str, dtype_out=str)
    def reset_power_converter(self, argin):
        """Reset the power converter to its default state (matching EPICS reset functionality)."""
        try:
            # Get initial values from update manager (matching EPICS)
            vals = update_manager.device_value_from_peeking_engine(
                DevicePropertyID(device_name=self.name, property="set_current")
            )
            start_val = np.asarray(vals).mean()
            
            self._current_setpoint = start_val
            self._current_readback = start_val
            
            logger.info(f"Power converter {self.name} reset to default values")
            return f"Power converter {self.name} reset successfully"
            
        except Exception as e:
            logger.error(f"Error resetting power converter: {str(e)}")
            raise DevFailed(f"Error resetting power converter: {str(e)}") 