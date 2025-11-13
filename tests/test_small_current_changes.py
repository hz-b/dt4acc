#!/usr/bin/env python3
"""
Test script with SMALL, realistic current changes.

This tests whether small current adjustments (±1%, ±5%, ±10%)
produce corresponding small tune changes, which would be expected
in normal accelerator operation.
"""

import time
import sys
from tango import DeviceProxy

def test_small_changes():
    """Test tune response to small current changes."""
    
    print("=" * 80)
    print("SMALL CURRENT CHANGES TEST - Realistic operational adjustments")
    print("=" * 80)
    
    try:
        # Connect to devices
        tune_device_name = "SimpleTangoServer/test/tune_device"
        pc_device_name = "SimpleTangoServer/test/power_converter_Q3P2T6R"
        
        print(f"\nConnecting to devices...")
        tune_device = DeviceProxy(tune_device_name)
        pc_device = DeviceProxy(pc_device_name)
        print(f"  ✓ Tune device: {tune_device_name}")
        print(f"  ✓ Power converter: {pc_device_name}")
        
        # Get initial values
        initial_current = pc_device.read_attribute("current_setpoint").value
        initial_tune_x = tune_device.read_attribute("x").value
        initial_tune_y = tune_device.read_attribute("y").value
        
        print(f"\n Initial State:")
        print(f"  Current:  {initial_current:.6f} A")
        print(f"  Tune X:   {initial_tune_x:.10f}")
        print(f"  Tune Y:   {initial_tune_y:.10f}")
        
        print("\n" + "=" * 80)
        print("TEST SEQUENCE: Small incremental changes")
        print("=" * 80)
        
        # Test sequence with small changes
        # Format: (percentage, description)
        test_changes = [
            (1.01, "+1% (very small)"),
            (1.02, "+2%"),
            (1.05, "+5%"),
            (1.10, "+10%"),
            (1.15, "+15%"),
            (1.00, "Back to initial"),
            (0.99, "-1%"),
            (0.98, "-2%"),
            (0.95, "-5%"),
            (0.90, "-10%"),
            (0.85, "-15%"),
            (1.00, "Restore initial"),
        ]
        
        results = []
        tune_changed_count = 0
        
        for i, (factor, description) in enumerate(test_changes, 1):
            test_current = initial_current * factor
            
            print(f"\n--- Test {i}/{len(test_changes)}: {description} → {test_current:.4f} A ---")
            
            # Set the new current
            pc_device.write_attribute("current_setpoint", test_current)
            
            # Wait for calculations (longer wait to ensure completion)
            wait_time = 2.0
            time.sleep(wait_time)
            
            # Read values
            readback_current = pc_device.read_attribute("current_readback").value
            new_tune_x = tune_device.read_attribute("x").value
            new_tune_y = tune_device.read_attribute("y").value
            
            
        
        return tune_changed_count > 0
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Restore initial current
        try:
            if pc_device and initial_current is not None:
                print(f"\n Restoring initial current: {initial_current:.6f} A")
                pc_device.write_attribute("current_setpoint", initial_current)
                time.sleep(2.0)
                print("✓ Current restored")
        except:
            pass


if __name__ == "__main__":
    print("\n" + "" * 40)
    print("SMALL CURRENT CHANGES → TUNE RESPONSE TEST")
    print("" * 40 + "\n")
    
    success = test_small_changes()
    
  

