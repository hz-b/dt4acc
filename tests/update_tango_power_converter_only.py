#!/usr/bin/env python3
"""
Update Only Power Converter Properties in Tango Power Converter Device

This file updates only the power converter properties defined in EPICS pv_setup.py:
- current_setpoint (pc_name:set in EPICS)
- current_readback (pc_name:rdbk in EPICS)
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dt4acc.custom_epics.data.querries import get_unique_power_converters
from tango import DeviceProxy, DevFailed

def update_power_converter_properties_only():
    """Update only the power converter properties in Tango power converter device."""
    
    print("⚡ Updating Only Power Converter Properties in Tango Power Converter Device")
    print("=" * 70)
    
    # Get power converter list from database
    power_converters = list(get_unique_power_converters())
    
    if not power_converters:
        print("❌ No power converters found in database")
        return
    
    test_power_converter = power_converters[0]
    print(f"✅ Testing with power converter: {test_power_converter}")
    
    # Get device name from database
    pc_device_name = f"SimpleTangoServer/test/power_converter_{test_power_converter}"
    print(f"📋 Device name: {pc_device_name}")
    
    try:
        # Connect to the device
        device = DeviceProxy(pc_device_name)
        
        # Check what attributes are available
        print("\n📋 Available attributes on the device:")
        for attr_name in device.get_attribute_list():
            print(f"  - {attr_name}")
        
        # Try to get device info
        print(f"\n📋 Device info:")
        print(f"  - Device name: {device.name()}")
        print(f"  - Device state: {device.state()}")
        
        # Read current values first
        print(f"\n📋 Reading current values:")
        try:
            current_setpoint = device.current_setpoint
            print(f"  - current_setpoint: {current_setpoint}")
        except Exception as e:
            print(f"  - current_setpoint read error: {e}")
            
        try:
            current_readback = device.current_readback
            print(f"  - current_readback: {current_readback}")
        except Exception as e:
            print(f"  - current_readback read error: {e}")
        
        # Update power converter properties (matching EPICS pv_setup.py exactly)
        print(f"\n📋 Updating power converter properties:")
        
        # 1. Update current_setpoint (pc_name:set in EPICS)
        print("  1. Updating current_setpoint (pc_name:set in EPICS)...")
        try:
            device.current_setpoint = 5.1
            print("     ✅ Successfully updated current_setpoint!")
            
            # Read the updated value
            updated_setpoint = device.current_setpoint
            print(f"     📊 Updated current_setpoint: {updated_setpoint}")
            
        except Exception as e:
            print(f"     ❌ current_setpoint update error: {e}")
        
        # 2. Read current_readback (pc_name:rdbk in EPICS) - READ ONLY
        print("  2. Reading current_readback (pc_name:rdbk in EPICS)...")
        try:
            # Note: current_readback is read-only in EPICS, automatically updated by system
            updated_readback = device.current_readback
            print(f"     📊 Current readback value: {updated_readback}")
            print("     ℹ️  Readback is read-only (automatically updated by system)")
            
        except Exception as e:
            print(f"     ❌ current_readback read error: {e}")
        
        # Final summary
        print(f"\n📊 FINAL SUMMARY:")
        print("=" * 40)
        try:
            final_setpoint = device.current_setpoint
            final_readback = device.current_readback
            
            print(f"  current_setpoint: {final_setpoint}")
            print(f"  current_readback: {final_readback}")
            
            print("\n✅ All power converter properties updated successfully!")
            
        except Exception as e:
            print(f"❌ Error reading final values: {e}")
        
        print("\n🎉 Power converter properties update completed!")
        print("=" * 70)
        
    except DevFailed as e:
        print(f"❌ Tango device error: {e}")
        print("Make sure the Tango server is running")
    except Exception as e:
        print(f"❌ Connection error: {e}")
        print("Make sure the Tango server is running")

if __name__ == "__main__":
    update_power_converter_properties_only() 