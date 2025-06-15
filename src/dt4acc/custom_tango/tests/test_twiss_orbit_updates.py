import numpy as np
from tango import DeviceProxy
from dt4acc.custom_tango.config import SERVER_NAME, SERVER_INSTANCE, DEVICE_NAME_FORMAT
from dt4acc.custom_epics.data.constants import config

def convert_to_list(data):
    """Convert sequence or numpy array to list with proper type handling"""
    if isinstance(data, np.ndarray):
        return data.tolist()
    return list(data)

def pad_array(arr, target_length=config.n_elements):
    """Pad array to match expected length"""
    if len(arr) < target_length:
        return np.pad(arr, (0, target_length - len(arr)), mode='constant', constant_values=0)
    return arr[:target_length]  # Truncate if longer

def print_array_comparison(name, original, new, max_display=5):
    """Print comparison of array values"""
    print(f"\n{name} comparison (showing first {max_display} values):")
    print("Original values:", original[:max_display])
    print("New values:     ", new[:max_display])
    print(f"Match: {np.allclose(original, new)}")

def test_twiss_orbit_updates():
    """Test Twiss-Orbit device updates."""
    # Create device proxy with correct device name
    device_name = f"{SERVER_NAME}/{SERVER_INSTANCE}/TwissOrbitDevice_MAIN"
    print(f"Connecting to device: {device_name}")
    device = DeviceProxy(device_name)
    
    print("\nTesting Twiss-Orbit Device Updates:")
    print("===================================")
    
    try:
        # Test 1: Update and verify orbit data

        # Read back and verify
        read_orbit_x = device.read_attribute("beam/orbit/x").value
        read_orbit_y = device.read_attribute("beam/orbit/y").value
        read_orbit_x0 = device.read_attribute("beam/orbit/x0").value
        read_names = device.read_attribute("beam/orbit/names").value
        read_found = device.read_attribute("beam/orbit/found").value

        read_twiss_alpha = device.read_attribute("beam/twiss/y/alpha").value
        read_twiss_beta = device.read_attribute("beam/twiss/y/beta").value

        print("readed the values of orbit_x",read_orbit_x)
        print("readed the values of orbit_y", read_orbit_y)
        print("readed the values of orbit_xo", read_orbit_x0)
        print("readed the values of orbit_name", read_names)
        print("readed the values of orbit_found", read_found)

        print("readed the values of twiss alpha", read_twiss_alpha)
        print("readed the values of  twiss beta", read_twiss_beta)





        print("\nAll tests completed successfully!")
        
    except Exception as e:
        print(f"\nError during testing: {str(e)}")
        raise

if __name__ == '__main__':
    test_twiss_orbit_updates() 