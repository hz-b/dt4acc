#!/usr/bin/env python3
"""
Check which properties are mapped in liaison manager for a device.
Usage: python check_mapped_properties.py <device_name>
"""

import sys
import os
sys.path.append('/Volumes/MyDrive/Bessy/version-may/dt4acc/src')

from dt4acc.custom_epics.ioc.liasion_translation_manager import build_managers
from bact_twin_architecture.data_model.identifiers import DevicePropertyID

def main():
    if len(sys.argv) != 2:
        print("Usage: python check_mapped_properties.py <device_name>")
        return
    
    device_name = sys.argv[1]
    
    # Extract the device name part (remove server/instance prefix)
    if '/' in device_name:
        parts = device_name.split('/')
        if len(parts) >= 3:
            actual_device_name = parts[2].replace('magnet_', '').replace('power_converter_', '')
        else:
            actual_device_name = device_name
    else:
        actual_device_name = device_name
    
    try:
        liaison_manager, translator_service = build_managers()
        
        print(f"Checking mapped properties for device: {actual_device_name}")
        print("-" * 50)
        
        # Check common properties
        properties_to_check = ["K", "x", "y", "powersupply_current", "set_current", "x_kick", "y_kick", "main_strength"]
        
        mapped_properties = []
        for prop in properties_to_check:
            device_property_id = DevicePropertyID(device_name=actual_device_name, property=prop)
            lattice_properties = liaison_manager.inverse(device_property_id)
            
            if lattice_properties:
                mapped_properties.append(prop)
                print(f"✓ {prop} -> {lattice_properties}")
            else:
                print(f"✗ {prop} -> Not mapped")
        
        print(f"\nMapped properties: {mapped_properties}")
        
        if not mapped_properties:
            print(f"\nNo properties are mapped for device '{actual_device_name}'")
            print("This device cannot be updated through the liaison manager.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
