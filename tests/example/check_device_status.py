#!/usr/bin/env python3
"""
Check device status and writability.
Usage: python check_device_status.py <device_name>
"""

import sys
import os
from tango import DeviceProxy

def main():
    if len(sys.argv) != 2:
        print("Usage: python check_device_status.py <device_name>")
        return
    
    if not os.environ.get("TANGO_HOST"):
        print("TANGO_HOST not set")
        return
    
    device_name = sys.argv[1]
    
    try:
        dev = DeviceProxy(device_name)
        
        # Check if device is responding
        print(f"Device: {device_name}")
        try:
            ping_time = dev.ping()
            print(f"Ping: {ping_time} ms - OK")
        except Exception as e:
            print(f"Ping failed: {e}")
            return
        
        # Check device state
        try:
            state = dev.state()
            status = dev.status()
            print(f"State: {state}")
            print(f"Status: {status}")
        except Exception as e:
            print(f"Could not get state/status: {e}")
        
        # Check attributes and their writability
        print("\nAttributes:")
        attributes = list(dev.get_attribute_list())
        for attr in attributes:
            try:
                attr_config = dev.get_attribute_config(attr)
                writable = "WRITABLE" if attr_config.writable != 0 else "READ-ONLY"
                
                try:
                    value = dev.read_attribute(attr).value
                    if isinstance(value, float):
                        print(f"  {attr:<20} = {value:.6f} ({writable})")
                    else:
                        print(f"  {attr:<20} = {value} ({writable})")
                except Exception as e:
                    print(f"  {attr:<20} = Read Error: {e} ({writable})")
                    
            except Exception as e:
                print(f"  {attr:<20} = Config Error: {e}")
                
    except Exception as e:
        print(f"Error connecting to device: {e}")

if __name__ == "__main__":
    main()
