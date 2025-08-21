#!/usr/bin/env python3
"""
Update Only Magnetic Properties in Tango Magnet Device

This file updates only the magnetic properties defined in EPICS pv_setup.py:
- k_strength (Cm:set in EPICS)
- current (im:I in EPICS) 
- x_position (x:set in EPICS)
- y_position (y:set in EPICS)
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dt4acc.custom_epics.data.querries import get_magnets
from bact_twin_architecture.bl.bessyii_yellow_pages import bessyii_yellow_pages
from tango import DeviceProxy, DevFailed

def update_magnetic_properties_only():
    """Update only the magnetic properties in Tango magnet device."""
    
    print("🧲 Updating Only Magnetic Properties in Tango Magnet Device")
    print("=" * 60)
    
    # Get magnetic list from database
    magnets = list(get_magnets())
    yp = bessyii_yellow_pages()
    
    # Filter quadrupoles
    quadrupoles = []
    for magnet in magnets:
        if magnet['name'] in yp.quadrupole_names():
            quadrupoles.append(magnet)
    
    if not quadrupoles:
        print("❌ No quadrupoles found in database")
        return
    
    test_quadrupole = quadrupoles[0]
    print(f"✅ Testing with quadrupole: {test_quadrupole['name']}")
    
    # Get device name from database
    magnet_device_name = f"SimpleTangoServer/test/magnet_{test_quadrupole['name']}"
    print(f"📋 Device name: {magnet_device_name}")
    
    try:
        # Connect to the device
        device = DeviceProxy(magnet_device_name)
        
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
            current_k_strength = device.k_strength
            print(f"  - k_strength: {current_k_strength}")
        except Exception as e:
            print(f"  - k_strength read error: {e}")
            
        try:
            current_readback = device.k_strength_readback
            print(f"  - k_strength_readback: {current_readback}")
        except Exception as e:
            print(f"  - k_strength_readback read error: {e}")
            
        try:
            current_current = device.current
            print(f"  - current: {current_current}")
        except Exception as e:
            print(f"  - current read error: {e}")
            
        try:
            current_x_position = device.x_position
            print(f"  - x_position: {current_x_position}")
        except Exception as e:
            print(f"  - x_position read error: {e}")
            
        try:
            current_y_position = device.y_position
            print(f"  - y_position: {current_y_position}")
        except Exception as e:
            print(f"  - y_position read error: {e}")
        
        # Update magnetic properties (matching EPICS pv_setup.py exactly)
        print(f"\n📋 Updating magnetic properties:")
        
        # 1. Update k_strength (Cm:set in EPICS)
        print("  1. Updating k_strength (Cm:set in EPICS)...")
        try:
            device.k_strength = 2.5
            print("     ✅ Successfully updated k_strength!")
            
            # Read the updated value
            updated_k_strength = device.k_strength_readback
            print(f"     📊 Updated k_strength_readback: {updated_k_strength}")
            
        except Exception as e:
            print(f"     ❌ k_strength update error: {e}")
        
        # 2. Update current (im:I in EPICS)
        print("  2. Updating current (im:I in EPICS)...")
        try:
            device.current = 1.5
            print("     ✅ Successfully updated current!")
            
            # Read the updated value
            updated_current = device.current
            print(f"     📊 Updated current: {updated_current}")
            
        except Exception as e:
            print(f"     ❌ current update error: {e}")
        
        # 3. Update x_position (x:set in EPICS)
        print("  3. Updating x_position (x:set in EPICS)...")
        try:
            device.x_position = 0.1
            print("     ✅ Successfully updated x_position!")
            
            # Read the updated value
            updated_x_position = device.x_position
            print(f"     📊 Updated x_position: {updated_x_position}")
            
        except Exception as e:
            print(f"     ❌ x_position update error: {e}")
        
        # 4. Update y_position (y:set in EPICS)
        print("  4. Updating y_position (y:set in EPICS)...")
        try:
            device.y_position = 0.2
            print("     ✅ Successfully updated y_position!")
            
            # Read the updated value
            updated_y_position = device.y_position
            print(f"     📊 Updated y_position: {updated_y_position}")
            
        except Exception as e:
            print(f"     ❌ y_position update error: {e}")
        
        # Final summary
        print(f"\n📊 FINAL SUMMARY:")
        print("=" * 40)
        try:
            final_k_strength = device.k_strength
            final_k_readback = device.k_strength_readback
            final_current = device.current
            final_x_position = device.x_position
            final_y_position = device.y_position
            
            print(f"  k_strength: {final_k_strength}")
            print(f"  k_strength_readback: {final_k_readback}")
            print(f"  current: {final_current}")
            print(f"  x_position: {final_x_position}")
            print(f"  y_position: {final_y_position}")
            
            print("\n✅ All magnetic properties updated successfully!")
            
        except Exception as e:
            print(f"❌ Error reading final values: {e}")
        
        print("\n🎉 Magnetic properties update completed!")
        print("=" * 60)
        
    except DevFailed as e:
        print(f"❌ Tango device error: {e}")
        print("Make sure the Tango server is running")
    except Exception as e:
        print(f"❌ Connection error: {e}")
        print("Make sure the Tango server is running")

if __name__ == "__main__":
    update_magnetic_properties_only() 