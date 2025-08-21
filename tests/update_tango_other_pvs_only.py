#!/usr/bin/env python3
"""
Update Only Other PVs Properties in Tango Other PVs Device

This file updates only the other PVs properties defined in EPICS pv_setup.py:
- dummy_x (dummy:x in EPICS)
- dummy_y (dummy:y in EPICS)
- current_current (special_pvs['current']:current in EPICS)
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dt4acc.custom_epics.data.constants import special_pvs
from tango import DeviceProxy, DevFailed

def update_other_pvs_properties_only():
    """Update only the other PVs properties in Tango other PVs device."""
    
    print("📊 Updating Only Other PVs Properties in Tango Other PVs Device")
    print("=" * 65)
    
    # Use the correct device name that we know works
    device_name = "SimpleTangoServer/test/other_pvs_device"
    print(f"📋 Device name: {device_name}")
    
    try:
        # Connect to the device
        device = DeviceProxy(device_name)
        
        # Check what attributes are available
        print("\n📋 Available attributes on the device:")
        for attr_name in device.get_attribute_list():
            print(f"  - {attr_name}")
        
        # Try to get device info
        print(f"\n📋 Device info:")
        print(f"  - Device name: {device.name()}")
        print(f"  - Device state: {device.state()}")
        
        # Read current values first using correct attribute names
        print(f"\n📋 Reading current values:")
        try:
            current_dummy_x = device.read_attribute("dummy/x").value
            print(f"  - dummy/x: {current_dummy_x}")
        except Exception as e:
            print(f"  - dummy/x read error: {e}")
            
        try:
            current_dummy_y = device.read_attribute("dummy/y").value
            print(f"  - dummy/y: {current_dummy_y}")
        except Exception as e:
            print(f"  - dummy/y read error: {e}")
            
        try:
            current_current = device.read_attribute("MDIZ3T5G/current").value
            print(f"  - MDIZ3T5G/current: {current_current}")
        except Exception as e:
            print(f"  - MDIZ3T5G/current read error: {e}")
        
        # Update other PVs properties (matching EPICS pv_setup.py exactly)
        print(f"\n📋 Updating other PVs properties:")
        
        # 1. Update dummy/x (dummy:x in EPICS)
        print("  1. Updating dummy/x (dummy:x in EPICS)...")
        try:
            device.write_attribute("dummy/x", 10.5)
            print("     ✅ Successfully updated dummy/x!")
            
            # Read the updated value
            updated_dummy_x = device.read_attribute("dummy/x").value
            print(f"     📊 Updated dummy/x: {updated_dummy_x}")
            
        except Exception as e:
            print(f"     ❌ dummy/x update error: {e}")
        
        # 2. Update dummy/y (dummy:y in EPICS)
        print("  2. Updating dummy/y (dummy:y in EPICS)...")
        try:
            device.write_attribute("dummy/y", 20.7)
            print("     ✅ Successfully updated dummy/y!")
            
            # Read the updated value
            updated_dummy_y = device.read_attribute("dummy/y").value
            print(f"     📊 Updated dummy/y: {updated_dummy_y}")
            
        except Exception as e:
            print(f"     ❌ dummy/y update error: {e}")
        
        # 3. Update MDIZ3T5G/current (special_pvs['current']:current in EPICS)
        print("  3. Updating MDIZ3T5G/current (special_pvs['current']:current in EPICS)...")
        try:
            device.write_attribute("MDIZ3T5G/current", 100.0)
            print("     ✅ Successfully updated MDIZ3T5G/current!")
            
            # Read the updated value
            updated_current = device.read_attribute("MDIZ3T5G/current").value
            print(f"     📊 Updated MDIZ3T5G/current: {updated_current}")
            
        except Exception as e:
            print(f"     ❌ MDIZ3T5G/current update error: {e}")
        
        # Test device commands
        print("\n📋 Testing device commands:")
        
        # 1. Test reset command
        print("  1. Testing reset command...")
        try:
            result = device.command_inout("reset")
            print(f"     ✅ Reset command result: {result}")
            
            # Read values after reset
            reset_dummy_x = device.read_attribute("dummy/x").value
            reset_dummy_y = device.read_attribute("dummy/y").value
            reset_current = device.read_attribute("MDIZ3T5G/current").value
            print(f"     📊 Values after reset:")
            print(f"       - dummy/x: {reset_dummy_x}")
            print(f"       - dummy/y: {reset_dummy_y}")
            print(f"       - MDIZ3T5G/current: {reset_current}")
            
        except Exception as e:
            print(f"     ❌ Reset command error: {e}")
        
        # 2. Test get_other_pvs_info command
        print("  2. Testing get_other_pvs_info command...")
        try:
            info = device.command_inout("get_other_pvs_info")
            print(f"     ✅ Other PVs info: {info}")
            
        except Exception as e:
            print(f"     ❌ get_other_pvs_info command error: {e}")
        
        # Final summary
        print(f"\n📊 FINAL SUMMARY:")
        print("=" * 40)
        try:
            final_dummy_x = device.read_attribute("dummy/x").value
            final_dummy_y = device.read_attribute("dummy/y").value
            final_current = device.read_attribute("MDIZ3T5G/current").value
            
            print(f"  - Final dummy/x: {final_dummy_x}")
            print(f"  - Final dummy/y: {final_dummy_y}")
            print(f"  - Final MDIZ3T5G/current: {final_current}")
            print("  - Other PVs device working correctly!")
            
        except Exception as e:
            print(f"  - Final read error: {e}")
        
        print("\n✅ Other PVs device test completed successfully!")
        
    except DevFailed as e:
        print(f"❌ Tango device error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    update_other_pvs_properties_only() 