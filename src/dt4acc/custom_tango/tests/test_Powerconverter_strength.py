#!/usr/bin/env python3
import sys
import time
from tango import DeviceProxy, DevFailed
from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_epics.ioc.liasion_translation_manager import element_method
from bact_twin_architecture.bl.bessyii_yellow_pages import bessyii_yellow_pages

logger = get_logger()

def test_cm_set(magnet_name: str = "PQIPT6R"):
    """
    Test function
    """
    try:
        print(f"\n[TEST] Testing Cm:set property for magnet: {magnet_name}")
        
        device = DeviceProxy(f"tango_server/test/PowerConverterDevice_{magnet_name}")
        device.set_timeout_millis(10000)
        print(f"  - Connected to device: {device.dev_name()}")
        
        initial_strength = device.magnetic_strength
        initial_readback = device.magnetic_strength_readback
        print(f"\nInitial state:")
        print(f"  - Cm:set = {initial_strength}")
        print(f"  - Cm:rdbk = {initial_readback}")
        
        test_values = [1.5, 2.0, 1.0, initial_strength]
        
        for value in test_values:
            print(f"\nSetting Cm:set to {value}")
            try:
                device.magnetic_strength = value
                
                time.sleep(1.0)
                
                current_strength = device.magnetic_strength
                current_readback = device.magnetic_strength_readback
                
                if abs(current_strength - value) > 1e-6:
                    print(f"  - WARNING: Cm:set value mismatch. Expected {value}, got {current_strength}")
                if abs(current_readback - value) > 1e-6:
                    print(f"  - WARNING: Cm:rdbk value mismatch. Expected {value}, got {current_readback}")
                
            except Exception as e:
                print(f"  - ERROR: Failed to set value {value}: {str(e)}")
        
        print("\n[TEST] Cm:set property test completed")
        
    except DevFailed as e:
        print(f"\n[ERROR] Device error: {str(e)}")
    except Exception as e:
        print(f"\n[ERROR] Test failed: {str(e)}")

if __name__ == "__main__":
    magnet_name = sys.argv[1] if len(sys.argv) > 1 else "PQIPT6R"
    test_cm_set(magnet_name) 