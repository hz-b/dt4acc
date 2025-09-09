#!/usr/bin/env python3
"""
Show device attribute values.
Usage: python show_device_values.py <device_name>
"""

import sys
import os
from tango import DeviceProxy

def main():
    if len(sys.argv) != 2:
        print("Usage: python show_device_values.py <device_name>")
        return
    
    if not os.environ.get("TANGO_HOST"):
        print("TANGO_HOST not set")
        return
    
    device_name = sys.argv[1]
    
    try:
        dev = DeviceProxy(device_name)
        attributes = list(dev.get_attribute_list())
        
        print(f"Device: {device_name}")
        print(f"Attributes: {len(attributes)}")
        print("-" * 40)
        
        for attr in attributes:
            try:
                value = dev.read_attribute(attr).value
                if isinstance(value, float):
                    print(f"{attr:<20} = {value:.6f}")
                else:
                    print(f"{attr:<20} = {value}")
            except Exception as e:
                print(f"{attr:<20} = Error: {e}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
