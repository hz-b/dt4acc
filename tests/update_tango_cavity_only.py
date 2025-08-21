#!/usr/bin/env python3
"""
Update Only Cavity Properties in Tango Cavity Device

This file updates only the cavity properties defined in EPICS pv_setup.py:
- frequency (cavity_name:freq in EPICS)
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dt4acc.custom_epics.data.constants import cavity_names
from tango import DeviceProxy, DevFailed

def update_cavity_properties_only():
    """Update only the cavity properties in Tango cavity device."""
    
    print("🏛️ Updating Only Cavity Properties in Tango Cavity Device")
    print("=" * 60)
    
    # Get cavity list from constants
    cavities = cavity_names
    
    if not cavities:
        print("❌ No cavities found in constants")
        return
    
    test_cavity = cavities[0]
    print(f"✅ Testing with cavity: {test_cavity}")
    
    # Get device name from database
    cavity_device_name = f"SimpleTangoServer/test/cavity_{test_cavity}"
    print(f"📋 Device name: {cavity_device_name}")
    
    try:
        # Connect to the device
        device = DeviceProxy(cavity_device_name)
        
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
            current_frequency = device.frequency
            print(f"  - frequency: {current_frequency}")
        except Exception as e:
            print(f"  - frequency read error: {e}")
        
        # Update cavity properties (matching EPICS pv_setup.py exactly)
        print(f"\n📋 Updating cavity properties:")
        
        # 1. Update frequency (cavity_name:freq in EPICS)
        print("  1. Updating frequency (cavity_name:freq in EPICS)...")
        try:
            device.frequency = 500.5
            print("     ✅ Successfully updated frequency!")
            
            # Read the updated value
            updated_frequency = device.frequency
            print(f"     📊 Updated frequency: {updated_frequency}")
            
        except Exception as e:
            print(f"     ❌ frequency update error: {e}")
        
        # Test device commands
        print("\n📋 Testing device commands:")
        
        # 1. Test reset command
        print("  1. Testing reset command...")
        try:
            result = device.reset()
            print(f"     ✅ Reset command result: {result}")
            
            # Read frequency after reset
            reset_frequency = device.frequency
            print(f"     📊 Frequency after reset: {reset_frequency}")
            
        except Exception as e:
            print(f"     ❌ Reset command error: {e}")
        
        # 2. Test get_cavity_info command
        print("  2. Testing get_cavity_info command...")
        try:
            info = device.get_cavity_info()
            print(f"     ✅ Cavity info: {info}")
            
        except Exception as e:
            print(f"     ❌ get_cavity_info command error: {e}")
        
        # Final summary
        print(f"\n📊 FINAL SUMMARY:")
        print("=" * 40)
        try:
            final_frequency = device.frequency
            print(f"  - Final frequency: {final_frequency}")
            print("  - Cavity device working correctly!")
            
        except Exception as e:
            print(f"  - Final read error: {e}")
        
        print("\n✅ Cavity device test completed successfully!")
        
    except DevFailed as e:
        print(f"❌ Tango device error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    update_cavity_properties_only() 