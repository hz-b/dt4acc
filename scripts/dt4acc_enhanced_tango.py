#!/usr/bin/env python3
"""
DT4ACC Enhanced Tango Server Script - Equivalent to EPICS softioc script
Runs the enhanced Tango server with EPICS-aligned heartbeat monitoring.
"""

import logging
import os
import sys
import time

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Set up logging
logging.basicConfig(level=logging.WARNING)

# Set environment variable for Tango server type
os.environ["server"] = "tango"

from dt4acc.custom_tango.ioc.devices.server_manager import main

if __name__ == "__main__":
    try:
        # Run the enhanced Tango server with heartbeat
        print("🚀 Starting DT4ACC Enhanced Tango Server...")
        print("🔧 Server type: Tango")
        main()
    except KeyboardInterrupt:
        print("\n🛑 Tango server stopped by user")
    except Exception as e:
        print(f"❌ Tango server failed: {e}")
        raise 