
# # List devices
# python3 tests/test_device_properties_Soleil.py

# # Get device info
# python3 tests/test_device_properties_Soleil.py AN01-AR/EM/CQLN.03

# # Update a property
# python3 tests/test_device_properties_Soleil.py AN01-AR/EM/CQLN.03 magnetic_strength 2.0


import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from tango import Database, DeviceProxy
import time


def get_device_info(device_name):
    """Get information about a device."""
    try:
        dev = DeviceProxy(device_name)
        
        print(f'Device: {device_name}')
        print(f'State: {dev.state()}')
        print(f'Status: {dev.status()}')
        
        # Get attributes
        attrs = list(dev.get_attribute_list())
        print(f'\nAttributes ({len(attrs)}):')
        for attr in attrs[:10]:
            try:
                attr_info = dev.get_attribute_config(attr)
                value = dev.read_attribute(attr)
                writable = "WR" if attr_info.writable != 0 else "R"
                print(f'  {attr}: {value.value} [{writable}]')
            except Exception as e:
                print(f'  {attr}: Error')
        if len(attrs) > 10:
            print(f'  ... {len(attrs) - 10} more')
        
        return dev
        
    except Exception as e:
        print(f'Error: {e}')
        return None


def update_device_property(device_name, attribute_name, new_value):
    """Update a device property."""
    try:
        dev = DeviceProxy(device_name)
        
        attr_info = dev.get_attribute_config(attribute_name)
        
        if attr_info.writable == 0:
            print(f'Error: Attribute "{attribute_name}" is read-only')
            return False
        
        old_value = dev.read_attribute(attribute_name).value
        print(f'Attribute: {attribute_name}')
        print(f'Current: {old_value} -> New: {new_value}')
        
        dev.write_attribute(attribute_name, new_value)
        
        time.sleep(0.1)
        updated_value = dev.read_attribute(attribute_name).value
        print(f'Updated: {updated_value}')
        
        return True
        
    except Exception as e:
        print(f'Error: {e}')
        return False


def list_available_devices():
    """List all available devices."""
    try:
        time.sleep(1)
        db = Database()
        exported = [str(d) for d in db.get_device_exported('*')]
        app_devices = [d for d in exported if not d.startswith('dserver/') and not d.startswith('sys/')]
        
        print(f'Found {len(app_devices)} devices')
        
        if app_devices:
            from collections import defaultdict
            by_server = defaultdict(list)
            for d in app_devices:
                parts = d.split('/')
                if len(parts) >= 2:
                    server = f'{parts[0]}/{parts[1]}'
                    by_server[server].append(d)
            
            for server in sorted(by_server.keys())[:10]:
                devices = by_server[server]
                print(f'\n{server} ({len(devices)} devices):')
                for dev in devices[:5]:
                    print(f'  {dev}')
                if len(devices) > 5:
                    print(f'  ... {len(devices) - 5} more')
            
            if len(by_server) > 10:
                print(f'\n... {len(by_server) - 10} more servers')
            
            if app_devices:
                print(f'\nExample: python3 tests/test_device_properties_Soleil.py {app_devices[0]}')
        else:
            print('No devices exported yet')
        
    except Exception as e:
        print(f'Error: {e}')


def main():
    """Main function."""
    if len(sys.argv) < 2:
        # No device specified, list available devices
        list_available_devices()
        return
    
    device_name = sys.argv[1]
    
    # Get device info first
    dev = get_device_info(device_name)
    
    if dev is None:
        return
    
    # If attribute and value are provided, update it
    if len(sys.argv) >= 4:
        attribute_name = sys.argv[2]
        try:
            new_value = float(sys.argv[3])
        except ValueError:
            print(f'Error: Invalid value "{sys.argv[3]}". Must be a number.')
            return
        
        update_device_property(device_name, attribute_name, new_value)
    elif len(sys.argv) == 3:
        # Just attribute name provided, show info about it
        attribute_name = sys.argv[2]
        try:
            attr_info = dev.get_attribute_config(attribute_name)
            value = dev.read_attribute(attribute_name)
            print(f'\nAttribute: {attribute_name}')
            print(f'Value: {value.value}')
            print(f'Type: {attr_info.data_type}')
            print(f'Writable: {"Yes" if attr_info.writable != 0 else "No"}')
        except Exception as e:
            print(f'Error: {e}')


if __name__ == "__main__":
    main()

