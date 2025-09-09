#!/usr/bin/env python3
"""
Update device attribute value.
Usage: python update_device_value.py <device_name> <attribute> <value>
"""

import sys
import os
from tango import DeviceProxy

def main():
    if len(sys.argv) != 4:
        print("Usage: python update_device_value.py <device_name> <attribute> <value>")
        return
    
    if not os.environ.get("TANGO_HOST"):
        print("TANGO_HOST not set")
        return
    
    device_name = sys.argv[1]
    attribute = sys.argv[2]
    value = sys.argv[3]
    
    try:
        dev = DeviceProxy(device_name)
        
        # Try to convert value to appropriate type
        try:
            if '.' in value:
                value = float(value)
            else:
                value = int(value)
        except:
            pass  # Keep as string
        
        # Read current value
        try:
            current = dev.read_attribute(attribute).value
            print(f"Current {attribute}: {current}")
        except:
            print(f"Could not read current {attribute}")
        
        # Set new value using write_attribute
        dev.write_attribute(attribute, value)
        print(f"Set {attribute} to: {value}")
        
        # Read back to verify
        try:
            new_value = dev.read_attribute(attribute).value
            print(f"Readback {attribute}: {new_value}")
        except:
            print("Could not read back value")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
