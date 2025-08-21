#!/usr/bin/env python3
"""
Check Registered Devices - List all devices in the Tango database
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tango import Database, DevFailed

def check_registered_devices():
    """Check what devices are registered in the Tango database."""
    
    print("🔍 Checking Registered Devices in Tango Database")
    print("=" * 50)
    
    try:
        # Connect to the database
        db = Database()
        
        # Try different server/instance combinations
        server_instances = [
            ("SimpleTangoServer", "test"),
            ("SimpleTangoServer", "*"),
            ("*", "test"),
            ("*", "*"),
        ]
        
        all_devices = set()
        
        for server, instance in server_instances:
            try:
                device_list = db.get_device_name(server, instance)
                print(f"\n📋 Server '{server}' Instance '{instance}' found {len(device_list)} devices:")
                for device_name in device_list:
                    print(f"  - {device_name}")
                    all_devices.add(device_name)
            except Exception as e:
                print(f"  ❌ Server '{server}' Instance '{instance}' failed: {e}")
        
        print(f"\n📊 TOTAL UNIQUE DEVICES FOUND: {len(all_devices)}")
        print("=" * 50)
        
        # Check specifically for our devices
        other_pvs_devices = [d for d in all_devices if "other_pvs" in d.lower()]
        cavity_devices = [d for d in all_devices if "cavity" in d.lower()]
        master_clock_devices = [d for d in all_devices if "master_clock" in d.lower()]
        
        print(f"\n🔍 SPECIFIC DEVICE SEARCH:")
        if other_pvs_devices:
            print(f"✅ Found Other PVs devices: {other_pvs_devices}")
        else:
            print(f"❌ No Other PVs devices found!")
            
        if cavity_devices:
            print(f"✅ Found Cavity devices: {cavity_devices}")
        else:
            print(f"❌ No Cavity devices found!")
            
        if master_clock_devices:
            print(f"✅ Found Master Clock devices: {master_clock_devices}")
        else:
            print(f"❌ No Master Clock devices found!")
            
    except DevFailed as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    check_registered_devices() 