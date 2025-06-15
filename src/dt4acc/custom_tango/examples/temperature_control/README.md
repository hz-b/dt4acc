# Tango Temperature Control Example

This example demonstrates a complete Tango-based temperature control system with detailed explanations of Tango concepts, server-client architecture, and device management.

## Project Structure
```
temperature_control/
├── devices/
│   ├── __init__.py
│   ├── temperature_device.py    # Temperature sensor device
│   └── heater_device.py        # Heater control device
├── client/
│   ├── __init__.py
│   └── temperature_client.py    # Client application
├── server/
│   ├── __init__.py
│   ├── server.py               # Server implementation
│   └── device_factory.py       # Device registration
├── utils/
│   ├── __init__.py
│   └── helpers.py              # Utility functions
└── tests/
    ├── __init__.py
    ├── test_temperature.py     # Temperature device tests
    └── test_heater.py         # Heater device tests
```

## 1. Device Implementation

### Temperature Device
```python
# devices/temperature_device.py
from tango import Device, DevState, AttrWriteType, DevFailed
from tango.server import attribute, command, device_property

class TemperatureDevice(Device):
    # Device properties
    sensor_id = device_property(dtype=str, default_value="TEMP001")
    max_temperature = device_property(dtype=float, default_value=100.0)
    
    def init_device(self):
        """Initialize device attributes and state"""
        Device.init_device(self)
        self._temperature = 25.0
        self._humidity = 50.0
        self._error = ""
        self.set_state(DevState.ON)
    
    # Attributes
    @attribute(dtype=float, label="Temperature", unit="Celsius")
    def temperature(self):
        return self._temperature
    
    @attribute(dtype=float, label="Humidity", unit="%")
    def humidity(self):
        return self._humidity
    
    @attribute(dtype=str, label="Error Message")
    def error(self):
        return self._error
    
    # Commands
    @command(dtype_in=float, dtype_out=bool)
    def set_temperature(self, value):
        """Set target temperature"""
        try:
            if value > self.max_temperature:
                raise ValueError(f"Temperature exceeds maximum {self.max_temperature}C")
            self._temperature = value
            return True
        except Exception as e:
            self._error = str(e)
            return False
    
    @command
    def reset(self):
        """Reset device to default state"""
        self._temperature = 25.0
        self._humidity = 50.0
        self._error = ""
        self.set_state(DevState.ON)
```

### Heater Device
```python
# devices/heater_device.py
from tango import Device, DevState, AttrWriteType
from tango.server import attribute, command, device_property

class HeaterDevice(Device):
    # Device properties
    heater_id = device_property(dtype=str, default_value="HEAT001")
    max_power = device_property(dtype=float, default_value=1000.0)
    
    def init_device(self):
        """Initialize device attributes and state"""
        Device.init_device(self)
        self._power = 0.0
        self._mode = "AUTO"
        self.set_state(DevState.ON)
    
    # Attributes
    @attribute(dtype=float, label="Power", unit="Watt")
    def power(self):
        return self._power
    
    @attribute(dtype=str, label="Operation Mode")
    def mode(self):
        return self._mode
    
    # Commands
    @command(dtype_in=float, dtype_out=bool)
    def set_power(self, value):
        """Set heater power"""
        try:
            if value > self.max_power:
                raise ValueError(f"Power exceeds maximum {self.max_power}W")
            self._power = value
            return True
        except Exception as e:
            self.set_state(DevState.FAULT)
            return False
    
    @command(dtype_in=str)
    def set_mode(self, mode):
        """Set operation mode (AUTO/MANUAL)"""
        if mode not in ["AUTO", "MANUAL"]:
            raise ValueError("Mode must be AUTO or MANUAL")
        self._mode = mode
```

## 2. Server Implementation

### Device Factory
```python
# server/device_factory.py
from tango import Database, DbDevInfo
from devices.temperature_device import TemperatureDevice
from devices.heater_device import HeaterDevice

def register_devices():
    """Register devices in Tango database"""
    db = Database()
    
    # Register Temperature Device
    temp_info = DbDevInfo()
    temp_info.name = "test/temperature/1"
    temp_info._class = "TemperatureDevice"
    temp_info.server = "TemperatureControlServer/test"
    db.add_device(temp_info)
    
    # Register Heater Device
    heater_info = DbDevInfo()
    heater_info.name = "test/heater/1"
    heater_info._class = "HeaterDevice"
    heater_info.server = "TemperatureControlServer/test"
    db.add_device(heater_info)
```

### Server
```python
# server/server.py
from tango.server import run
from devices.temperature_device import TemperatureDevice
from devices.heater_device import HeaterDevice

def main():
    """Start the Tango server"""
    run([TemperatureDevice, HeaterDevice])

if __name__ == "__main__":
    main()
```

## 3. Client Implementation

```python
# client/temperature_client.py
from tango import DeviceProxy
import time

class TemperatureControlClient:
    def __init__(self):
        """Initialize device proxies"""
        self.temp_device = DeviceProxy("test/temperature/1")
        self.heater_device = DeviceProxy("test/heater/1")
    
    def set_temperature(self, target_temp):
        """Set target temperature and control heater"""
        try:
            # Set temperature
            if not self.temp_device.set_temperature(target_temp):
                raise Exception(self.temp_device.error)
            
            # Control heater based on current temperature
            current_temp = self.temp_device.temperature
            if current_temp < target_temp:
                self.heater_device.set_power(1000.0)  # Full power
            else:
                self.heater_device.set_power(0.0)     # Turn off
            
            return True
        except Exception as e:
            print(f"Error: {str(e)}")
            return False
    
    def monitor_temperature(self, duration=60):
        """Monitor temperature for specified duration"""
        start_time = time.time()
        while time.time() - start_time < duration:
            temp = self.temp_device.temperature
            power = self.heater_device.power
            print(f"Temperature: {temp}C, Heater Power: {power}W")
            time.sleep(1)
```

## 4. Setup and Running

### 1. Start Tango Database
```bash
# Start Tango database server
sudo DataBaseds 2 -ORBendPoint giop:tcp::10000
```

### 2. Register Devices
```bash
# Register devices in Tango database
python -m temperature_control.server.device_factory
```

### 3. Start Server
```bash
# Start the Tango server
python -m temperature_control.server.server
```

### 4. Run Client
```python
from temperature_control.client.temperature_client import TemperatureControlClient

# Create client
client = TemperatureControlClient()

# Set temperature to 30°C
client.set_temperature(30.0)

# Monitor for 60 seconds
client.monitor_temperature(60)
```

## 5. Key Tango Concepts

### Device Properties
- Defined using `device_property` decorator
- Configured in database or code
- Accessible via `get_device_properties()`

### Attributes
- Read-only: `@attribute(dtype=type)`
- Read-write: `@attribute(dtype=type, access=AttrWriteType.READ_WRITE)`
- Dynamic: `@attribute(dtype=type, polling_period=1000)`

### Commands
- Basic: `@command`
- With parameters: `@command(dtype_in=type, dtype_out=type)`
- Asynchronous: `@command(dtype_in=type, dtype_out=type, async=True)`

### Device States
- `DevState.ON`: Normal operation
- `DevState.OFF`: Device off
- `DevState.FAULT`: Error condition
- `DevState.ALARM`: Warning condition

### Error Handling
```python
try:
    device.set_temperature(50.0)
except DevFailed as e:
    print(f"Tango error: {str(e)}")
except Exception as e:
    print(f"General error: {str(e)}")
```

## 6. Testing

### Unit Tests
```python
# tests/test_temperature.py
import unittest
from tango.test_context import DeviceTestContext
from devices.temperature_device import TemperatureDevice

class TestTemperatureDevice(unittest.TestCase):
    def setUp(self):
        self.context = DeviceTestContext(TemperatureDevice)
        self.context.start()
        self.device = self.context.get_device()
    
    def test_set_temperature(self):
        result = self.device.set_temperature(30.0)
        self.assertTrue(result)
        self.assertEqual(self.device.temperature, 30.0)
    
    def test_max_temperature(self):
        result = self.device.set_temperature(150.0)
        self.assertFalse(result)
        self.assertIn("exceeds maximum", self.device.error)
    
    def tearDown(self):
        self.context.stop()
```

## 7. Best Practices

1. **Error Handling**
   - Use specific exception types
   - Provide meaningful error messages
   - Update device state on errors

2. **State Management**
   - Initialize all attributes in `init_device()`
   - Update state on significant changes
   - Use appropriate state transitions

3. **Attribute Updates**
   - Use polling for dynamic attributes
   - Implement proper data validation
   - Handle type conversions

4. **Command Implementation**
   - Validate input parameters
   - Return meaningful results
   - Use async commands for long operations

5. **Device Properties**
   - Use meaningful default values
   - Document property purposes
   - Validate property values

## 8. Troubleshooting

### Common Issues

1. **Connection Problems**
   - Check database server is running
   - Verify device names are correct
   - Check network connectivity

2. **Attribute Access**
   - Verify attribute names
   - Check access rights
   - Validate data types

3. **Command Execution**
   - Check parameter types
   - Verify device state
   - Look for error messages

### Debug Tools

1. **Jive**
   - Device browser
   - Attribute viewer
   - Command executor

2. **Astor**
   - Server management
   - Device registration
   - Log viewer

3. **Logging**
   - Enable debug logging
   - Check server logs
   - Monitor device states 