# DT4ACC Tango Implementation

## Overview
This module implements the Tango-based control system for the DT4ACC (Digital Twin for Accelerator Control) project. It provides device servers and clients for managing accelerator components through the Tango control system.

## Architecture

### System Components
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Tango DB     │     │  Tango Server   │     │  Tango Client   │
│  (Device Info)  │◄────┤  (Devices)      │◄────┤  (ResultView)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Component Structure
```
Tango System
├── Server Side
│   ├── Device Classes
│   │   ├── TwissOrbitDevice
│   │   │   ├── Attributes
│   │   │   │   ├── orbit_x, orbit_y
│   │   │   │   ├── twiss_alpha_x, twiss_beta_x
│   │   │   │   └── magnet_strengths
│   │   │   └── Commands
│   │   │       ├── update_orbit
│   │   │       └── update_twiss
│   │   ├── BPMDevice
│   │   │   ├── Attributes
│   │   │   │   └── bpm_data
│   │   │   └── Commands
│   │   │       └── update_bpm
│   │   ├── MagnetDevice
│   │   │   ├── Attributes
│   │   │   │   ├── main_strength
│   │   │   │   ├── x_kick
│   │   │   │   ├── y_kick
│   │   │   │   ├── powersupply_current
│   │   │   │   └── device_state
│   │   │   └── Commands
│   │   │       ├── set_strength
│   │   │       ├── set_kick
│   │   │       └── reset
│   │   └── PowerConverterDevice
│   │       ├── Attributes
│   │       │   ├── set_current
│   │       │   ├── readback_current
│   │       │   └── device_state
│   │       └── Commands
│   │           ├── set_current
│   │           └── reset
│   └── Device Registration
│       ├── Database Setup
│       └── Device Info
└── Client Side
    ├── ResultView
    │   ├── Device Proxies
    │   ├── Update Methods
    │   └── Error Handling
    ├── BPM Data Handling
    └── Heartbeat Monitoring
```

## Installation

### Prerequisites
- Python 3.8+
- Tango Control System
- pytango
- PyTango
- NumPy

### Setup
1. running Tango Control System
```bash
# For Ubuntu/Debian
 sudo DataBaseds 2 -ORBendPoint giop:tcp::10000
```

## Usage

### Starting the Server
```bash
# Start Tango server
python -m dt4acc.custom_tango.tango_server test
```

### Using the Client
```python
from dt4acc.custom_tango.views.calculation_result_view import ResultView

# Initialize ResultView
view = ResultView(prefix="tango_server/test")

# Update orbit data
await view.push_orbit(orbit_data)

# Update Twiss parameters
await view.push_twiss(twiss_data)

# Update BPM data
await view.push_bpms(bpm_data)

# Update magnet strength
await view.push_value(ElementUpdate(
    element_id="magnet_name",
    property_name="K",
    value=new_strength
))
```

## Device Details

### MagnetDevice
The MagnetDevice class manages individual magnets in the accelerator:

```python
class MagnetDevice(Device):
    def __init__(self):
        # Attributes
        self.main_strength = 0.0  # Main magnetic field strength
        self.x_kick = 0.0        # Horizontal kick
        self.y_kick = 0.0        # Vertical kick
        self.powersupply_current = 0.0  # Current power supply value
        self.device_state = DevState.ON  # Device state

    def set_strength(self, value):
        """Set the main magnetic field strength"""
        self.main_strength = value
        self._update_power_supply()

    def set_kick(self, x_kick=None, y_kick=None):
        """Set horizontal and/or vertical kicks"""
        if x_kick is not None:
            self.x_kick = x_kick
        if y_kick is not None:
            self.y_kick = y_kick
        self._update_power_supply()

    def _update_power_supply(self):
        """Update power supply based on strength and kicks"""
        # Implementation of power supply update logic
        pass
```

### PowerConverterDevice
Manages the power supply for magnets:

```python
class PowerConverterDevice(Device):
    def __init__(self):
        # Attributes
        self.set_current = 0.0
        self.readback_current = 0.0
        self.device_state = DevState.ON

    def set_current(self, value):
        """Set the current value"""
        self.set_current = value
        self._update_readback()

    def _update_readback(self):
        """Update readback value"""
        pass
```

## Data Flow

### Magnet Update Flow
```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Client  │     │ResultView│     │  Magnet  │     │  Power   │
│          │     │          │     │  Device  │     │ Converter│
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                 │                │
     │ push_value()   │                 │                │
     │───────────────►│                 │                │
     │                │ set_strength()  │                │
     │                │────────────────►│                │
     │                │                 │ _update_ps()   │
     │                │                 │───────────────►│
     │                │                 │                │
     │                │                 │     OK         │
     │                │                 │◄───────────────│
     │                │     OK          │                │
     │                │◄────────────────│                │
     │     OK         │                 │                │
     │◄───────────────│                 │                │
```

### Orbit Update Flow
```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Client  │     │ResultView│     │ Device   │     │  Server  │
│          │     │          │     │  Proxy   │     │          │
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                 │                │
     │ push_orbit()   │                 │                │
     │───────────────►│                 │                │
     │                │ _get_device()   │                │
     │                │────────────────►│                │
     │                │                 │ write_attribute│
     │                │                 │───────────────►│
     │                │                 │                │
     │                │                 │     OK         │
     │                │                 │◄───────────────│
     │                │                 │                │
     │                │     OK          │                │
     │                │◄────────────────│                │
     │     OK         │                 │                │
     │◄───────────────│                 │                │
```

### Heartbeat Flow
```
┌──────────┐     ┌──────────┐     ┌──────────┐
│Heartbeat │     │ResultView│     │  Device  │
│  Loop    │     │          │     │  Proxy   │
└────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                 │
     │  heart_beat()  │                 │
     │───────────────►│                 │
     │                │    ping()       │
     │                │────────────────►│
     │                │                 │
     │                │      OK         │
     │                │◄────────────────│
     │      OK        │                 │
     │◄───────────────│                 │
```

## Error Handling

### Connection Errors
The system implements automatic reconnection with exponential backoff:
```python
async def _get_device(self):
    try:
        return DeviceProxy(self.device_name)
    except DevFailed as e:
        if self._reconnect_attempts < self._max_reconnect_attempts:
            self._reconnect_attempts += 1
            await asyncio.sleep(self._reconnect_delay)
            return await self._get_device()
        else:
            logger.error(f"Max reconnection attempts reached: {e}")
            raise
```

### Data Validation
All data is validated before being sent to devices:
```python
def convert_to_list(data: Union[Sequence, np.ndarray]) -> List:
    if isinstance(data, np.ndarray):
        data = np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)
        return data.tolist()
    return list(data)
```

## Key Features

1. **Device Management**
   - Automatic device registration
   - Device state monitoring
   - Reconnection handling

2. **Data Handling**
   - Type conversion
   - Data validation
   - Error checking

3. **Communication**
   - Asynchronous updates
   - Heartbeat monitoring
   - Error recovery

4. **Security**
   - Device access control
   - Data validation
   - Error logging

## Testing

Run the test suite:
```bash
python -m pytest tests/
```



 