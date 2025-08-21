from tango import DeviceProxy, DevState, AttrWriteType, AttrDataFormat, DevString, DevFailed
from tango.server import Device, attribute, command, device_property
import numpy as np
from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_epics.data.querries import get_unique_power_converters, get_magnets_per_power_converters
from dt4acc.custom_epics.ioc.handlers import update_manager, handle_device_update
from dt4acc.custom_epics.ioc.liasion_translation_manager import build_managers, element_method
from bact_twin_architecture.data_model.identifiers import LatticeElementPropertyID, DevicePropertyID, ConversionID
from bact_twin_architecture.bl.bessyii_yellow_pages import bessyii_yellow_pages
from dt4acc.custom_tango.ioc.devices.async_wrapper import run_async_in_background


logger = get_logger()

class MagnetDevice(Device):
    """
    Simplified Tango device class for controlling magnets in the accelerator.
    Removes unnecessary event loops and complex async logic.
    """
    
    # Device properties (matching EPICS)
    k_value = device_property(
        dtype=float,
        default_value=0.0,
        doc="Magnet strength factor (k-value) - matches EPICS Cm:set"
    )
    
    name = device_property(
        dtype=str,
        default_value="",
        doc="Magnet name"
    )
    
    def init_device(self):
        """Initialize the device - simplified without event loops."""
        try:
            print("\n[DEBUG] Initializing Simplified MagnetDevice:")
            print("  - Getting device properties")
            dev_prop = self.get_device_properties()
            print(f"  - Device properties: {dev_prop}")
            
            if not hasattr(dev_prop, 'name') or not dev_prop.name:
                print("  - ERROR: Device name property not set")
                device_name = self.get_name()
                print(f"  - Device name from get_name(): {device_name}")
                if device_name:
                    try:
                        self.name = device_name.split('_')[-1]
                        print(f"  - Extracted name from device name: {self.name}")
                    except:
                        print("  - Could not extract name from device name")
                        raise DevFailed("Device name property not set")
                else:
                    raise DevFailed("Device name property not set")
            
            print(f"  - Device name: {self.name}")
            
            # Initialize liaison manager and translation service
            try:
                print("  - Initializing liaison manager and translation service")
                self.liaison_manager, self.translator_service = build_managers()
                print("  - Liaison manager and translation service initialized successfully")
            except Exception as e:
                print(f"  - ERROR: Failed to initialize liaison manager: {str(e)}")
                logger.error(f"Failed to initialize liaison manager: {str(e)}")
                raise
            
            try:
                print("  - Initializing attributes")
                self._init_attributes()
                print("  - Attributes initialized successfully")
            except Exception as e:
                print(f"  - ERROR: Failed to initialize attributes: {str(e)}")
                raise
            
            # Set device state to ON
            self.set_state(DevState.ON)
            print("  - Device state set to ON")
            print("  - Device initialization completed successfully")
            
        except Exception as e:
            print(f"\n[ERROR] Device initialization failed:")
            print(f"  - Error: {str(e)}")
            raise
            
    def _init_attributes(self):
        """Initialize device attributes (matching EPICS exactly)."""
        try:
            # Get initial values from update manager (matching EPICS)
            val = update_manager.peek_engine(
                LatticeElementPropertyID(element_name=self.name, property="main_strength")
            )
            
            # Initialize attributes with values (matching EPICS exactly)
            self._k_strength = self.k_value or 0.0  # Matches EPICS Cm:set initial_value
            self._k_strength_readback = val  # Matches EPICS Cm:rdbk initial_value
            self._current = 0.0  # Matches EPICS im:I initial_value
            self._x_position = 0.0  # Matches EPICS x:set initial_value
            self._y_position = 0.0  # Matches EPICS y:set initial_value
                
        except Exception as e:
            logger.error(f"Error initializing attributes: {str(e)}")
            raise
        
    def _validate_magnetic_update(self, value, property_name):
        """Validate magnetic parameter updates using liaison manager."""
        try:
            # Create device property ID for validation
            device_property_id = DevicePropertyID(device_name=self.name, property=property_name)
            
            # Check if this device property is known to the liaison manager
            lattice_properties = self.liaison_manager.inverse(device_property_id)
            
            if not lattice_properties:
                raise DevFailed(f"Device property {property_name} for magnet {self.name} not found in liaison manager - update not allowed")
            
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
            
    def _apply_magnetic_update(self, value, property_name):
        """Apply magnetic parameter update using async wrapper."""
        try:
            # CALL THE EXACT SAME FUNCTIONS AS EPICS pv_setup.py
            # This matches the EPICS implementation exactly:
            # - handle_device_update(magnet_name, "K", val) for magnetic strength (Cm:set)
            # - handle_magnet_update(magnet_name, "powersupply_current", val) for current (im:I)
            # - handle_device_update(magnet_name, "x", val) for x position (x:set)
            # - handle_device_update(magnet_name, "y", val) for y position (y:set)
            
            if property_name == "K":
                # Magnetic strength update (Cm:set in EPICS)
                logger.info(f"{self.name}:K setting setpoint val={value}")
                # Use async wrapper to call handle_device_update
                run_async_in_background(handle_device_update)(self.name, "K", value)
                
            elif property_name == "powersupply_current":
                # Power supply current update (im:I in EPICS)
                logger.info(f"{self.name}:powersupply_current setting setpoint val={value}")
                # Use async wrapper to call handle_device_update
                run_async_in_background(handle_device_update)(self.name, "powersupply_current", value)
                
            elif property_name == "x":
                # X position update (x:set in EPICS)
                logger.info(f"{self.name}:x setting setpoint val={value}")
                # Use async wrapper to call handle_device_update
                run_async_in_background(handle_device_update)(self.name, "x", value)
                
            elif property_name == "y":
                # Y position update (y:set in EPICS)
                logger.info(f"{self.name}:y setting setpoint val={value}")
                # Use async wrapper to call handle_device_update
                run_async_in_background(handle_device_update)(self.name, "y", value)
                
            else:
                # Fallback to the property name
                logger.info(f"{self.name}:{property_name} setting setpoint val={value}")
                # Use async wrapper to call handle_device_update
                run_async_in_background(handle_device_update)(self.name, property_name, value)
                
        except Exception as e:
            logger.error(f"Failed to call handle_device_update for {property_name}: {e}")
            raise
        
    def _is_property_mapped(self, property_name):
        """Check if a property is mapped in the liaison manager."""
        try:
            device_property_id = DevicePropertyID(device_name=self.name, property=property_name)
            lattice_properties = self.liaison_manager.inverse(device_property_id)
            return bool(lattice_properties)
        except Exception as e:
            logger.error(f"Error checking property mapping: {str(e)}")
            return False

    # EPICS-Matching Attributes (EXACTLY as in EPICS pv_setup.py)
    
    @attribute(dtype=float, access=AttrWriteType.READ_WRITE)
    def k_strength(self):
        """Get K strength (Cm:set in EPICS)."""
        return self._k_strength
        
    @k_strength.write
    def k_strength(self, value):
        """Set K strength (Cm:set in EPICS)."""
        try:
            # Check if this property is mapped in liaison manager
            if not self._is_property_mapped("K"):
                raise DevFailed(f"K strength updates not allowed for magnet {self.name} - property not mapped in liaison manager")
            
            # Validate the update
            self._validate_magnetic_update(value, "K")
            
            # Apply the update using the same function as EPICS pv_setup.py
            # EPICS: handle_device_update(magnet_name, "K", val)
            self._apply_magnetic_update(value, "K")
            
            # Update local state (matching EPICS)
            self._k_strength = float(value)
            self._k_strength_readback = value
            
            logger.info(f"Updated K strength to {value} for {self.name}")
            
        except Exception as e:
            logger.error(f"Error updating K strength: {str(e)}")
            raise
        
    @attribute(dtype=float)
    def k_strength_readback(self):
        """Get K strength readback (Cm:rdbk in EPICS)."""
        return self._k_strength_readback
        
    @attribute(dtype=float, access=AttrWriteType.READ_WRITE)
    def current(self):
        """Get current (im:I in EPICS)."""
        return self._current
        
    @current.write
    def current(self, value):
        """Set current (im:I in EPICS)."""
        try:
            # Check if this property is mapped in liaison manager
            if not self._is_property_mapped("powersupply_current"):
                raise DevFailed(f"Current updates not allowed for magnet {self.name} - property not mapped in liaison manager")
            
            # Validate the update
            self._validate_magnetic_update(value, "powersupply_current")
            
            # Apply the update using the same function as EPICS pv_setup.py
            # EPICS: handle_magnet_update(magnet_name, "powersupply_current", val)
            self._apply_magnetic_update(value, "powersupply_current")
            
            # Update local state
            self._current = float(value)
            
            logger.info(f"Updated current to {value} for {self.name}")
            
        except Exception as e:
            logger.error(f"Error updating current: {str(e)}")
            raise
        
    @attribute(dtype=float, access=AttrWriteType.READ_WRITE)
    def x_position(self):
        """Get x position (x:set in EPICS)."""
        return self._x_position
        
    @x_position.write
    def x_position(self, value):
        """Set x position (x:set in EPICS)."""
        try:
            # Check if this property is mapped in liaison manager
            if not self._is_property_mapped("x"):
                raise DevFailed(f"X position updates not allowed for magnet {self.name} - property not mapped in liaison manager")
            
            # Validate the update
            self._validate_magnetic_update(value, "x")
            
            # Apply the update using the same function as EPICS pv_setup.py
            # EPICS: handle_device_update(magnet_name, "x", val)
            self._apply_magnetic_update(value, "x")
            
            # Update local state
            self._x_position = float(value)
            
            logger.info(f"Updated x position to {value} for {self.name}")
            
        except Exception as e:
            logger.error(f"Error updating x position: {str(e)}")
            raise
        
    @attribute(dtype=float, access=AttrWriteType.READ_WRITE)
    def y_position(self):
        """Get y position (y:set in EPICS)."""
        return self._y_position
        
    @y_position.write
    def y_position(self, value):
        """Set y position (y:set in EPICS)."""
        try:
            # Check if this property is mapped in liaison manager
            if not self._is_property_mapped("y"):
                raise DevFailed(f"Y position updates not allowed for magnet {self.name} - property not mapped in liaison manager")
            
            # Validate the update
            self._validate_magnetic_update(value, "y")
            
            # Apply the update using the same function as EPICS pv_setup.py
            # EPICS: handle_device_update(magnet_name, "y", val)
            self._apply_magnetic_update(value, "y")
            
            # Update local state
            self._y_position = float(value)
            
            logger.info(f"Updated y position to {value} for {self.name}")
            
        except Exception as e:
            logger.error(f"Error updating y position: {str(e)}")
            raise

    # Commands (matching EPICS functionality)
    
    @command(dtype_in=str, dtype_out=str)
    def get_magnet_info(self, argin):
        """Get magnet information (matching EPICS info commands)."""
        try:
            info = f"Magnet: {self.name}\n"
            info += f"K Strength: {self._k_strength}\n"
            info += f"Current: {self._current}\n"
            info += f"X Position: {self._x_position}\n"
            info += f"Y Position: {self._y_position}\n"
            info += f"State: {self.get_state()}\n"
            return info
        except Exception as e:
            logger.error(f"Error getting magnet info: {str(e)}")
            raise DevFailed(f"Error getting magnet info: {str(e)}")
    
    @command(dtype_in=str, dtype_out=str)
    def reset_magnet(self, argin):
        """Reset magnet to default values (matching EPICS reset functionality)."""
        try:
            # Reset to default values
            self._k_strength = 0.0
            self._k_strength_readback = 0.0
            self._current = 0.0
            self._x_position = 0.0
            self._y_position = 0.0
            
            logger.info(f"Magnet {self.name} reset to default values")
            return f"Magnet {self.name} reset successfully"
            
        except Exception as e:
            logger.error(f"Error resetting magnet: {str(e)}")
            raise DevFailed(f"Error resetting magnet: {str(e)}") 