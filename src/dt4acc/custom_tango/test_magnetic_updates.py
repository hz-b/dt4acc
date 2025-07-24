#!/usr/bin/env python3
"""
Test script to verify magnetic updates are working and being logged properly.
This simulates the magnetic updates that should trigger the push_value method.
"""

import os
import sys
import asyncio
import time

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from dt4acc.core.utils.logger import get_logger
from dt4acc.core.model.element_upate import ElementUpdate
from dt4acc.core.views.shared_view import get_view_instance

logger = get_logger()

async def test_magnetic_updates():
    """Test magnetic updates to verify they're being logged."""
    
    print("🧪 Testing Magnetic Updates")
    print("=" * 50)
    
    # Set environment for Tango view
    os.environ["server"] = "tango"
    
    try:
        # Get the view instance
        print("🔧 Getting view instance...")
        view = get_view_instance()
        print(f"✅ View instance: {type(view).__name__}")
        
        # Test push_value method directly
        print("\n🧪 Testing push_value method directly...")
        
        # Create test element updates
        test_updates = [
            ElementUpdate(element_id="VS3M2T6R", property_name="K", value=2.4),
            ElementUpdate(element_id="VS3M2T8R", property_name="K", value=1.8),
            ElementUpdate(element_id="VS3M2T10R", property_name="K", value=3.2),
        ]
        
        for update in test_updates:
            print(f"📤 Testing update: {update.element_id}:{update.property_name} = {update.value}")
            try:
                await view.push_value(update)
                print(f"✅ Update successful: {update.element_id}:{update.property_name}")
            except Exception as e:
                print(f"❌ Update failed: {update.element_id}:{update.property_name} - {e}")
        
        # Test orbit push
        print("\n🧪 Testing orbit push...")
        try:
            # Create a simple orbit result (you might need to import the actual Orbit class)
            from dt4acc.core.model.orbit import Orbit
            import numpy as np
            
            # Create a simple orbit result
            orbit_result = Orbit(
                x=np.array([0.1, 0.2, 0.3]),
                y=np.array([0.01, 0.02, 0.03]),
                x0=np.array([0.0, 0.0, 0.0]),
                names=np.array(["BPM1", "BPM2", "BPM3"]),
                found=True
            )
            
            await view.push_orbit(orbit_result)
            print("✅ Orbit push successful")
        except Exception as e:
            print(f"❌ Orbit push failed: {e}")
        
        print("\n✅ Magnetic update test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.error(f"Test failed: {e}")

def main():
    """Main function to run the test."""
    print("🧪 Magnetic Update Test Script")
    print("This script tests if magnetic updates are being logged properly.")
    print("=" * 60)
    
    try:
        asyncio.run(test_magnetic_updates())
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"❌ Test error: {e}")

if __name__ == "__main__":
    main() 