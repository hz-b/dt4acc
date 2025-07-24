#  Custom Tango Framework - Complete Implementation Guide

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Installation Steps](#installation-steps)
4. [Framework Architecture](#framework-architecture)
5. [Implementation Guide](#implementation-guide)
6. [Running the System](#running-the-system)
7. [Troubleshooting](#troubleshooting)
8. [API Reference](#api-reference)

##  Overview

This custom Tango framework provides a complete implementation for managing accelerator devices (magnets, power converters, BPMs) with real-time monitoring and EPICS-style logging. It's designed for containerized deployment and includes:

- **Clean Tango Server**: Exports 550+ devices without heartbeat interference
- **Update Monitor Service**: EPICS-style logging for magnetic updates
- **Device Management**: Complete device export and management
- **Real-time Monitoring**: Heartbeat and update detection
- **EPICS Compatibility**: Logging patterns matching EPICS implementation

##  Prerequisites

### System Requirements
- **OS**: Linux (Ubuntu 20.04+ recommended) or macOS
- **Python**: 3.8+ (3.9+ recommended)
- **Memory**: 4GB+ RAM
- **Storage**: 10GB+ free space
- **Network**: Internet access for package installation

### Required Software
- **Python pip** and **virtualenv**
- **Git** (for source code management)
- **Tango Database** (for device registration)

##  Installation Steps

### Step 1: Environment Setup

#### 1.1 Create Python Virtual Environment
```bash
python3 -m venv pytango-env1

source pytango-env1/bin/activate  # Linux/macOS
# or
pytango-env1\Scripts\activate     # Windows
```

#### 1.2 Install Core Dependencies
```bash
# Upgrade pip
pip install --upgrade pip

# Install core packages
pip install numpy pandas asyncio
pip install PyTango
pip install p4p  # For EPICS compatibility
```

### Step 2: Tango Framework Installation

#### 2.1 Install Tango Database
```bash
# Ubuntu/Debian
sudo apt-get update


# macOS (using Homebrew)
brew install tango

# Start Tango database
 udo DataBaseds 2 -ORBendPoint giop:tcp::10000

```

#### 2.2 Install Project Dependencies
```bash
# Navigate to project root
cd /path/to/dt4acc

# Install project dependencies
pip install -r requirements.txt

# Install additional dependencies
pip install bact-twin-architecture
pip install lat2db
```

### Step 3: Configuration Setup

#### 3.1 Environment Variables
```bash
# Set environment variables
export TANGO_HOST=localhost:10000
export DT4ACC_PREFIX=tango_server/test
export MONGODB_URL=mongodb://localhost:27017/bessyii


```

```

## 🏗️ Framework Architecture

### Directory Structure
```
src/dt4acc/custom_tango/
├── README.md                           # This file
├── tango_server.py                     # Main Tango server
├── update_monitor_service.py           # EPICS-style update monitor
├── run_separated_services.py           # Service management script
├── test_magnetic_updates.py            # Test script
├── device_exporter_complete.py         # Complete device exporter
├── ioc/                                # IOC components
│   ├── devices/                        # Tango device implementations
│   │   ├── twiss_orbit_device.py       # Twiss/Orbit device
│   │   ├── magnet_device.py            # Magnet device
│   │   ├── power_converter_device.py   # Power converter device
│   │   └── bpm_device.py               # BPM device
│   ├── utils/                          # Utility functions
│   └── heartbeat_process.py            # Heartbeat process
├── views/                              # View implementations
│   ├── calculation_result_view.py      # Main result view
│   ├── bpm_data.py                     # BPM data view
│   └── __init__.py
└── data/                               # Data files
    └── constants.py                    # Configuration constants
```

### Core Components

#### 1. Tango Server (`tango_server.py`)
- **Purpose**: Main server for device export and management
- **Features**: 
  - Exports 550+ devices (magnets, power converters, BPMs)
  - Clean operation without heartbeat interference
  - Accelerator manager integration
  - Device registration and management

#### 2. Update Monitor Service (`update_monitor_service.py`)
- **Purpose**: EPICS-style update monitoring
- **Features**:
  - Independent operation from Tango server
  - EPICS-style logging: "Orbit pushing view", "Twiss pushed view"
  - Magnetic update detection and logging
  - Minimal heartbeat logging every 10 iterations

#### 3. Device Exporter (`device_exporter_complete.py`)
- **Purpose**: Complete device export with batch processing
- **Features**:
  - Batch processing for large device sets
  - Progress tracking and logging
  - Error handling and recovery
  - Timeout management

## Implementation Guide

### Step 1: Basic Setup

#### 1.1 Clone and Setup Project
```bash
# Clone the repository
git clone <repository-url>
cd dt4acc

# Setup virtual environment
python3 -m venv pytango-env1
source pytango-env1/bin/activate

#### 1.2 Verify Installation
```bash
# Test Tango installation
python -c "import tango; print('Tango installed successfully')"


```

### Step 2: Device Configuration

#### 2.1 Configure Device Classes
```python
# In tango_server.py
DEVICE_CLASSES = {
    'TwissOrbitDevice': TwissOrbitDevice,
    'MagnetDevice': MagnetDevice,
    'PowerConverterDevice': PowerConverterDevice,
    'BPMDevice': BPMDevice
}
```

#### 2.2 Setup Device Properties
```python
# Example device property configuration
class TwissOrbitDevice(Device):
    Host = device_property(dtype=str, default_value="localhost")
    Port = device_property(dtype=int, default_value=10000)
    Prefix = device_property(dtype=str, default_value="beam")
```

### Step 3: View Implementation

#### 3.1 Configure Result View
```python
# In calculation_result_view.py
class ResultView:
    def __init__(self, *, prefix):
        self.prefix = prefix
        self.device = None
        self._initialized = False
        # ... other initializations
```

#### 3.2 Implement Update Methods
```python
async def push_value(self, elm_update: ElementUpdate):
    """Push magnetic updates with EPICS-style logging"""
    if elm_update.property_name == "K":
        pass
    else:
        property_name = 'x:set' if 'x' in elm_update.property_name else (
            'y:set' if 'dy' in elm_update.property_name else elm_update.property_name)
        
        try:
            logger.info(f"Updating {elm_update.element_id}:{property_name} to {elm_update.value}")
            print(f" Updating {elm_update.element_id}:{property_name} to {elm_update.value}")
            
            device_name = f"{self.prefix}/PowerConverterDevice_VS3P2T8R"
            device = DeviceProxy(device_name)
            device.write_attribute(property_name, elm_update.value)
            
            logger.info(f"Successfully updated {elm_update.element_id}:{property_name}")
            print(f"Successfully updated {elm_update.element_id}:{property_name}")
            
        except Exception as e:
            logger.error(f"Failed to update {elm_update.element_id}:{property_name}: {e}")
            print(f" Failed to update {elm_update.element_id}:{property_name}: {e}")
```

##  Running the System

### Method 1: Manual Approach

#### 1.1 Start Tango Server
```bash
# Navigate to custom_tango directory
cd src/dt4acc/custom_tango

# Start clean Tango server
python tango_server.py test
```

**Expected Output:**
```
STARTING CLEAN TANGO SERVER (NO HEARTBEAT)...
 Initializing accelerator manager to connect view to updates...
 Accelerator manager initialized - view now connected to updates
 EXPORTING ALL DEVICES WITH COMPLETE DEVICE EXPORTER...
 COMPLETE DEVICE EXPORT SUMMARY:
  - Power converters: 150
  - Magnets: 300
  - TwissOrbit devices: 1
  - BPM devices: 100
  - Total exported: 551
 Calling tango.server.run()...
Ready to accept request
```

#### 1.2 Start Update Monitor Service
```bash
# In a new terminal
cd src/dt4acc/custom_tango

# Start update monitor service
python update_monitor_service.py
```

**Expected Output:**
```
Update Monitor Service (EPICS-style logging)
Initializing view for update monitor...
View initialized: ResultView
Update monitor service started successfully!
Starting update monitor...
Update monitor heartbeat at 2024-01-15 10:30:15
Update monitor iteration 10 (elapsed: 0:00:10)
Update monitor iteration 20 (elapsed: 0:00:20)
...
```


##  Troubleshooting

### Common Issues


#### 2. Device Export Fails
```bash
# Check device registration
python -c "
from tango import Database
db = Database()
print(db.get_device_exported('tango_server/test/TwissOrbitDevice_MAIN'))
"

# Re-register devices
python tango_server.py test
```

#### 3. Update Monitor Not Showing Logs
```bash


# Test view connection
python test_magnetic_updates.py
```

#### 4. Memory Issues
```bash
# Monitor memory usage
htop

# Increase Python memory limit
export PYTHONMALLOC=malloc
export PYTHONDEVMODE=1
```

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with verbose output
python tango_server.py test 
```


### Core Classes

#### TangoServer
```python
class TangoServer:
    def __init__(self, instance_name="test")
    def run_server(self)
```

#### UpdateMonitorService
```python
class UpdateMonitorService:
    def __init__(self, interval_seconds=1, log_interval=10)
    def initialize_view(self)
    def start(self)
    def stop(self)
```

#### ResultView
```python
class ResultView:
    def __init__(self, *, prefix)
    async def push_value(self, elm_update: ElementUpdate)
    async def push_orbit(self, orbit_result: Orbit)
    async def push_twiss(self, twiss_result: TwissWithAggregatedKValues)
    async def heart_beat(self)
```

### Key Methods

#### Device Management
- `register_server()`: Register Tango server
- `register_device_classes()`: Register device classes
- `export_all_devices()`: Export all devices

#### Update Monitoring
- `push_value()`: Handle magnetic updates
- `push_orbit()`: Handle orbit updates
- `push_twiss()`: Handle Twiss updates
- `heart_beat()`: Periodic heartbeat


