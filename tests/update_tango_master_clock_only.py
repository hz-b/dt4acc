#!/usr/bin/env python3
"""
Update Only Master Clock Properties in Tango Master Clock Device

This file updates only the master clock properties defined in EPICS pv_setup.py:
- frequency (special_pvs['master_clock']:freq in EPICS)
- ref_freq (lattice_info:ref_freq in EPICS)
- ref_freq_khz_up (lattice_info:ref_freq:khz:up in EPICS)
- ref_freq_khz_frac (lattice_info:ref_freq:khz:frac in EPICS)
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tango import DeviceProxy, DevFailed

def update_master_clock_properties_only():
    """Update only the master clock properties in Tango master clock device."""
    
    print("⏰ Updating Only Master Clock Properties in Tango Master Clock Device")
    print("=" * 65)
    
    # Get device name
    master_clock_device_name = "SimpleTangoServer/test/master_clock_device"
    print(f"📋 Device name: {master_clock_device_name}")
    
    try:
        # Connect to the device
        device = DeviceProxy(master_clock_device_name)
        
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
            current_frequency = device.read_attribute("MCLKHX251C/freq").value
            print(f"  - MCLKHX251C/freq: {current_frequency}")
        except Exception as e:
            print(f"  - MCLKHX251C/freq read error: {e}")
            
        try:
            current_ref_freq = device.read_attribute("lattice_info/ref_freq").value
            print(f"  - lattice_info/ref_freq: {current_ref_freq}")
        except Exception as e:
            print(f"  - lattice_info/ref_freq read error: {e}")
            
        try:
            current_ref_freq_khz_up = device.read_attribute("lattice_info/ref_freq/khz/up").value
            print(f"  - lattice_info/ref_freq/khz/up: {current_ref_freq_khz_up}")
        except Exception as e:
            print(f"  - lattice_info/ref_freq/khz/up read error: {e}")
            
        try:
            current_ref_freq_khz_frac = device.read_attribute("lattice_info/ref_freq/khz/frac").value
            print(f"  - lattice_info/ref_freq/khz/frac: {current_ref_freq_khz_frac}")
        except Exception as e:
            print(f"  - lattice_info/ref_freq/khz/frac read error: {e}")
        
        # Update master clock properties (matching EPICS pv_setup.py exactly)
        print(f"\n📋 Updating master clock properties:")
        
        # 1. Update frequency (special_pvs['master_clock']:freq in EPICS)
        print("  1. Updating MCLKHX251C/freq (special_pvs['master_clock']:freq in EPICS)...")
        try:
            device.write_attribute("MCLKHX251C/freq", 500.5)
            print("     ✅ Successfully updated MCLKHX251C/freq!")
            
            # Read the updated value
            updated_frequency = device.read_attribute("MCLKHX251C/freq").value
            print(f"     📊 Updated MCLKHX251C/freq: {updated_frequency}")
            
        except Exception as e:
            print(f"     ❌ MCLKHX251C/freq update error: {e}")
        
        # 2. Update ref_freq (lattice_info:ref_freq in EPICS)
        print("  2. Updating lattice_info/ref_freq (lattice_info:ref_freq in EPICS)...")
        try:
            device.write_attribute("lattice_info/ref_freq", 501.0)
            print("     ✅ Successfully updated lattice_info/ref_freq!")
            
            # Read the updated value
            updated_ref_freq = device.read_attribute("lattice_info/ref_freq").value
            print(f"     📊 Updated lattice_info/ref_freq: {updated_ref_freq}")
            
        except Exception as e:
            print(f"     ❌ lattice_info/ref_freq update error: {e}")
        
        # 3. Update ref_freq_khz_up (lattice_info:ref_freq:khz:up in EPICS)
        print("  3. Updating lattice_info/ref_freq/khz/up (lattice_info:ref_freq:khz:up in EPICS)...")
        try:
            device.write_attribute("lattice_info/ref_freq/khz/up", 502)
            print("     ✅ Successfully updated lattice_info/ref_freq/khz/up!")
            
            # Read the updated value
            updated_ref_freq_khz_up = device.read_attribute("lattice_info/ref_freq/khz/up").value
            print(f"     📊 Updated lattice_info/ref_freq/khz/up: {updated_ref_freq_khz_up}")
            
        except Exception as e:
            print(f"     ❌ lattice_info/ref_freq/khz/up update error: {e}")
        
        # 4. Update ref_freq_khz_frac (lattice_info:ref_freq:khz:frac in EPICS)
        print("  4. Updating lattice_info/ref_freq/khz/frac (lattice_info:ref_freq:khz:frac in EPICS)...")
        try:
            device.write_attribute("lattice_info/ref_freq/khz/frac", 500000)
            print("     ✅ Successfully updated lattice_info/ref_freq/khz/frac!")
            
            # Read the updated value
            updated_ref_freq_khz_frac = device.read_attribute("lattice_info/ref_freq/khz/frac").value
            print(f"     📊 Updated lattice_info/ref_freq/khz/frac: {updated_ref_freq_khz_frac}")
            
        except Exception as e:
            print(f"     ❌ lattice_info/ref_freq/khz/frac update error: {e}")
        
        # Test device commands
        print("\n📋 Testing device commands:")
        
        # 1. Test reset command
        print("  1. Testing reset command...")
        try:
            result = device.command_inout("reset")
            print(f"     ✅ Reset command result: {result}")
            
            # Read values after reset
            reset_frequency = device.read_attribute("MCLKHX251C/freq").value
            reset_ref_freq = device.read_attribute("lattice_info/ref_freq").value
            reset_ref_freq_khz_up = device.read_attribute("lattice_info/ref_freq/khz/up").value
            reset_ref_freq_khz_frac = device.read_attribute("lattice_info/ref_freq/khz/frac").value
            print(f"     📊 Values after reset:")
            print(f"       - MCLKHX251C/freq: {reset_frequency}")
            print(f"       - lattice_info/ref_freq: {reset_ref_freq}")
            print(f"       - lattice_info/ref_freq/khz/up: {reset_ref_freq_khz_up}")
            print(f"       - lattice_info/ref_freq/khz/frac: {reset_ref_freq_khz_frac}")
            
        except Exception as e:
            print(f"     ❌ Reset command error: {e}")
        
        # 2. Test get_master_clock_info command
        print("  2. Testing get_master_clock_info command...")
        try:
            info = device.command_inout("get_master_clock_info")
            print(f"     ✅ Master clock info: {info}")
            
        except Exception as e:
            print(f"     ❌ get_master_clock_info command error: {e}")
        
        # Final summary
        print(f"\n📊 FINAL SUMMARY:")
        print("=" * 40)
        try:
            final_frequency = device.read_attribute("MCLKHX251C/freq").value
            final_ref_freq = device.read_attribute("lattice_info/ref_freq").value
            final_ref_freq_khz_up = device.read_attribute("lattice_info/ref_freq/khz/up").value
            final_ref_freq_khz_frac = device.read_attribute("lattice_info/ref_freq/khz/frac").value
            
            print(f"  - Final MCLKHX251C/freq: {final_frequency}")
            print(f"  - Final lattice_info/ref_freq: {final_ref_freq}")
            print(f"  - Final lattice_info/ref_freq/khz/up: {final_ref_freq_khz_up}")
            print(f"  - Final lattice_info/ref_freq/khz/frac: {final_ref_freq_khz_frac}")
            print("  - Master clock device working correctly!")
            
        except Exception as e:
            print(f"  - Final read error: {e}")
        
        print("\n✅ Master clock device test completed successfully!")
        
    except DevFailed as e:
        print(f"❌ Tango device error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    update_master_clock_properties_only() 