import functools

from tango import DeviceProxy, DevState, AttrWriteType, AttrDataFormat, DevString, DevFailed
from tango.server import Device, attribute, command, device_property
import numpy as np
import asyncio
import threading
from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_epics.data.querries import get_unique_power_converters, get_magnets_per_power_converters
from dt4acc.custom_epics.ioc.handlers import update_manager, handle_device_update
from dt4acc.custom_epics.ioc.liasion_translation_manager import build_managers, element_method
from bact_twin_architecture.data_model.identifiers import LatticeElementPropertyID, DevicePropertyID
from bact_twin_architecture.bl.bessyii_yellow_pages import bessyii_yellow_pages

logger = get_logger()

class MagnetDevice(Device):
    """
    Tango device class for controlling magnets in the accelerator.

    """
    
    # Device properties
    k_value = device_property(
        dtype=float,
        default_value=0.0,
        doc="Magnet strength factor (k-value)"
    )
    
    name = device_property(
        dtype=str,
        default_value="",
        doc="Magnet name"
    )
    
    type = device_property(
        dtype=str,
        default_value="unknown",
        doc="Magnet type"
    )

    @functools.lru_cache(maxsize=1)
    def init_device(self):
        """Initialize the device."""
        try:
            print("\n[DEBUG] Initializing MagnetDevice:")
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
                    # Extract name from device name (format: tango_server/test/MagnetDevice_HS1MD4R)
                    try:
                        self.name = device_name.split('_')[-1]
                        print(f"  - Extracted name from device name: {self.name}")
                    except:
                        print("  - Could not extract name from device name")
                        raise DevFailed("Device name property not set")
                else:
                    raise DevFailed("Device name property not set")
            
            print(f"  - Device name: {self.name}")
            
            # Initialize attributes
            try:
                print("  - Initializing attributes")
                self._init_attributes()
                print("  - Attributes initialized successfully")
            except Exception as e:
                print(f"  - ERROR: Failed to initialize attributes: {str(e)}")
                raise
            
            # Initialize event loop
            try:
                self._loop = asyncio.get_event_loop_policy().get_event_loop()
                asyncio.set_event_loop(self._loop)
                # Start event loop in a separate thread
                self._loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
                self._loop_thread.start()
                print("  - Event loop initialized successfully")
            except Exception as e:
                print(f"  - ERROR: Failed to initialize event loop: {str(e)}")
                raise
            
            print("  - Device initialization completed successfully")
            
        except Exception as e:
            print(f"\n[ERROR] Device initialization failed:")
            print(f"  - Error: {str(e)}")
            raise
            
    def _run_event_loop(self):
        """Run the event loop in a separate thread."""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()
            
    def _init_attributes(self):
        """Initialize device attributes with default values."""
        try:
            print("  - Initializing device attributes")
            
            # Get initial values from update manager
            try:
                val = update_manager.peek_engine(
                    LatticeElementPropertyID(element_name=self.name, property="main_strength")
                )
                print(f"    * Initial magnetic strength value: {val}")
            except Exception as e:
                logger.warning(f"Could not get initial values from update manager: {str(e)}")
                val = 0.0
            
            # Get associated power converter from EPICS query
            try:
                print(f"    * Looking up power converter for magnet {self.name}")
                power_converters = get_unique_power_converters()
                print(f"    * Found {len(power_converters)} power converters")
                
                # Debug print all power converters and their magnets
                for pc in power_converters:
                    magnets = get_magnets_per_power_converters(pc)
                    print(f"    * Power converter {pc} has magnets: {[m['name'] for m in magnets]}")
                
                # Find power converter for this magnet
                self._power_converter = None
                for pc in power_converters:
                    magnets = get_magnets_per_power_converters(pc)
                    if any(m['name'] == self.name for m in magnets):
                        self._power_converter = pc
                        print(f"    * Found power converter {pc} for magnet {self.name}")
                        break
                
                if not self._power_converter:
                    print(f"    * WARNING: No power converter found for magnet {self.name}")
                    logger.warning(f"No power converter found for magnet {self.name}")
                else:
                    logger.info(f"Found associated power converter: {self._power_converter}")
            except Exception as e:
                print(f"    * ERROR: Failed to get power converter: {str(e)}")
                logger.warning(f"Could not get power converter from EPICS query: {str(e)}")
                self._power_converter = None
            
            # Initialize attributes with default values
            self._magnetic_strength = self.k_value or 0.0  # as like Cm:set in EPICS
            self._magnetic_strength_readback = val  # like Cm:rdbk in EPICS
            self._current = 0.0  # im:I in EPICS
            self._power_supply_current = 0.0
            self._x_position = 0.0  # x:set like  in EPICS
            self._y_position = 0.0  # y:set like  in EPICS
            self._cm_set = val
            
            print("    * All attributes initialized successfully")
            
        except Exception as e:
            print(f"    * ERROR: Failed to initialize attributes: {str(e)}")
            raise
        
    def _run_async_update(self, update_func):
        """Helper method to run async updates in the event loop."""
        try:
            future = asyncio.run_coroutine_threadsafe(update_func, self._loop)
            future.result(timeout=10.0)  # Increased timeout to 10 seconds
        except asyncio.TimeoutError:
            logger.error("Async update timed out after 10 seconds")
            raise DevFailed("Update operation timed out")
        except Exception as e:
            logger.error(f"Error in async update: {str(e)}")
            raise
        
    # Magnetic field control attributes
    @attribute(dtype=float, access=AttrWriteType.READ_WRITE)
    def magnetic_strength(self):
        """Get magnetic strength (Cm:set in EPICS)."""
        return self._magnetic_strength
        
    @magnetic_strength.write
    def magnetic_strength(self, value):
        """Set magnetic strength (Cm:set in EPICS)."""
        try:
            self._magnetic_strength = float(value)
            
            # Get associated power converter
            if not hasattr(self, '_power_converter') or self._power_converter is None:
                print(f"Looking up power converter for magnet {self.name}")
                power_converters = get_unique_power_converters()
                print(f"Found {len(power_converters)} power converters")
                
                # Find power converter for this magnet
                self._power_converter = None
                for pc in power_converters:
                    magnets = get_magnets_per_power_converters(pc)
                    if any(m['name'] == self.name for m in magnets):
                        self._power_converter = pc
                        print(f"Found power converter {pc} for magnet {self.name}")
                        break
                
                if not self._power_converter:
                    raise DevFailed(f"No power converter found for magnet {self.name}")
            
            print(f"Using power converter {self._power_converter} for magnet {self.name}")
            print(f"Current magnetic strength: {self._magnetic_strength}")
            print(f"Previous magnetic strength: {self._magnetic_strength_readback}")
            
            try:
                # Update only the power converter's set_current
                # The LiaisonManager will handle mapping this to the appropriate lattice property
                print(f"Updating power converter {self._power_converter} set_current to {value}")
                self._run_async_update(handle_device_update(self._power_converter, "set_current", value))
                
                # Update readback to match EPICS behavior
                self._magnetic_strength_readback = value
                logger.info(f"Updated magnetic strength to {value} using power converter {self._power_converter}")
                
            except Exception as e:
                if "array must not contain infs or NaNs" in str(e):
                    logger.warning("Twiss calculation error - continuing with update")
                    logger.warning(f"Error occurred with magnetic strength value: {value}")
                    # Still update the readback since the value was set
                    self._magnetic_strength_readback = value
                else:
                    raise
            
        except Exception as e:
            logger.error(f"Error updating magnetic strength: {str(e)}")
            raise
        
    @attribute(dtype=float)
    def magnetic_strength_readback(self):
        """Get magnetic strength readback (Cm:rdbk in EPICS)."""
        return self._magnetic_strength_readback
        
    @attribute(dtype=float, access=AttrWriteType.READ_WRITE)
    def current(self):
        """Get current (im:I in EPICS)."""
        return self._current
        
    @current.write
    def current(self, value):
        """Set current (im:I in EPICS)."""
        try:
            self._current = float(value)
            # Use EPICS update handler with set_current property
            if self._power_converter:
                self._run_async_update(handle_device_update(self._power_converter, "set_current", value))
            logger.info(f"Updated current to {value}")
        except Exception as e:
            logger.error(f"Error updating current: {str(e)}")
            raise
        
    @attribute(dtype=float)
    def power_supply_current(self):
        """Get power supply current."""
        return self._power_supply_current
        
    @attribute(dtype=float, access=AttrWriteType.READ_WRITE)
    def x_position(self):
        """Get x position (x:set in EPICS)."""
        return self._x_position
        
    @x_position.write
    def x_position(self, value):
        """Set x position (x:set in EPICS)."""
        try:
            self._x_position = float(value)
            # Use EPICS update handler with x_kick property
            self._run_async_update(handle_device_update(self.name, "x_kick", value))
            logger.info(f"Updated x position to {value}")
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
            self._y_position = float(value)
            # Use EPICS update handler with y_kick property
            self._run_async_update(handle_device_update(self.name, "y_kick", value))
            logger.info(f"Updated y position to {value}")
        except Exception as e:
            logger.error(f"Error updating y position: {str(e)}")
            raise
        
    @attribute(dtype=float)
    def cm_set(self):
        """Get Cm set value."""
        return self._cm_set
        
    # Commands
    @command(dtype_in=None, doc_in="Reset the magnet to its default state")
    def reset(self):
        """Reset the magnet to its default state."""
        try:
            self._magnetic_strength = self.k_value or 0.0
            self._magnetic_strength_readback = self.k_value or 0.0
            self._current = 0.0
            self._power_supply_current = 0.0
            self._x_position = 0.0
            self._y_position = 0.0
            self.set_state(DevState.OFF)
            logger.info(f"Magnet {self.name}: Reset to default state")
        except Exception as e:
            logger.error(f"Error resetting magnet: {str(e)}")
            raise
        
    @command(dtype_in=None, doc_in="Calibrate the magnet")
    def calibrate(self):
        """Calibrate the magnet."""
        try:
            # Here you would implement the actual calibration logic
            logger.info(f"Magnet {self.name}: Calibration started")
            # Simulate calibration
            self._magnetic_strength_readback = self._magnetic_strength
            logger.info(f"Magnet {self.name}: Calibration completed")
        except Exception as e:
            logger.error(f"Error calibrating magnet: {str(e)}")
            raise 