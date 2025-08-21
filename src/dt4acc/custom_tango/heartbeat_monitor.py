#!/usr/bin/env python3
"""
Heartbeat Monitor - Runs heartbeat monitoring independently from Tango server
"""

import os
import sys
import asyncio
import signal
import time

# Add the parent directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from dt4acc.custom_tango.ioc.tasks import monitor_heartbeat
from dt4acc.core.utils.logger import get_logger

logger = get_logger()

# Global variables
shutdown_event = asyncio.Event()

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    print(f"🛑 Received signal {signum}, shutting down heartbeat...")
    shutdown_event.set()

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def wait_for_tango_server():
    """Wait for Tango server to be available before starting heartbeat."""
    print("⏳ Waiting for Tango server to be available...")
    logger.info("⏳ Waiting for Tango server to be available...")
    
    max_attempts = 60  # 60 seconds max wait
    attempt = 0
    
    while attempt < max_attempts:
        try:
            from tango import Database
            db = Database()
            db.get_device_info("SimpleTangoServer/test/twiss_orbit_twiss_device")
            print("✅ Tango server is available!")
            logger.info("✅ Tango server is available!")
            return True
            
        except Exception as e:
            attempt += 1
            print(f"⏳ Waiting for Tango server... (attempt {attempt}/{max_attempts})")
            time.sleep(1)
    
    print("❌ Tango server not available within timeout")
    logger.error("❌ Tango server not available within timeout")
    return False

async def monitor_heartbeat_with_shutdown():
    """Heartbeat monitoring with shutdown responsiveness."""
    print("💓 Starting heartbeat monitoring with shutdown responsiveness...")
    logger.info("💓 Starting heartbeat monitoring with shutdown responsiveness...")
    
    iteration = 0
    while not shutdown_event.is_set():  # Check shutdown signal
        iteration += 1
        try:
            print(f"💓 Heartbeat iteration {iteration}")
            logger.debug(f"💓 Heartbeat iteration {iteration}")
            
            # Check shutdown signal BEFORE any long operation
            if shutdown_event.is_set():
                print("🛑 Shutdown signal received, stopping heartbeat...")
                logger.info("🛑 Shutdown signal received, stopping heartbeat...")
                break
            
            # Run the actual heartbeat with timeout protection
            try:
                # Use asyncio.wait_for to prevent blocking operations
                await asyncio.wait_for(
                    monitor_heartbeat(), 
                    timeout=10.0  # 10 second timeout for heartbeat operation
                )
            except asyncio.TimeoutError:
                print("⏰ Heartbeat operation timed out, checking shutdown...")
                if shutdown_event.is_set():
                    print("🛑 Shutdown signal received during timeout, stopping...")
                    break
                continue
            
            # Check shutdown signal AFTER heartbeat operation
            if shutdown_event.is_set():
                print("🛑 Shutdown signal received, stopping heartbeat...")
                logger.info("🛑 Shutdown signal received, stopping heartbeat...")
                break
            
            # Very short sleep to be extremely responsive to shutdown
            await asyncio.sleep(1)  # Check every 1 second instead of 5
            
        except asyncio.CancelledError:
            logger.warning("Heartbeat was cancelled.")
            print("💓 Heartbeat was cancelled.")
            break
        except Exception as exc:
            logger.error(f"Heartbeat encountered an error: {exc}")
            print(f"❌ Heartbeat encountered an error: {exc}")
            
            # Check shutdown signal on error
            if shutdown_event.is_set():
                print("🛑 Shutdown signal received, stopping heartbeat...")
                logger.info("🛑 Shutdown signal received, stopping heartbeat...")
                break
            
            # Brief pause on error, but still check shutdown
            await asyncio.sleep(0.5)
    
    print("💓 Heartbeat monitoring stopped")
    logger.info("💓 Heartbeat monitoring stopped")

def main():
    """Main function to run heartbeat monitoring independently."""
    try:
        # Ensure server type is set for shared view system
        os.environ["server"] = "tango"
        
        # Set DT4ACC_PREFIX for PV naming - use a sensible default if not set
        if "DT4ACC_PREFIX" not in os.environ:
            default_prefix = "BESSY"  # Default prefix for BESSY
            os.environ["DT4ACC_PREFIX"] = default_prefix
            print(f"🔧 Setting DT4ACC_PREFIX to default: {default_prefix}")
            logger.info(f"Setting DT4ACC_PREFIX to default: {default_prefix}")
        else:
            print(f"🔧 Using existing DT4ACC_PREFIX: {os.environ['DT4ACC_PREFIX']}")
            logger.info(f"Using existing DT4ACC_PREFIX: {os.environ['DT4ACC_PREFIX']}")
        
        print("💓 Starting DT4ACC Heartbeat Monitor (Independent)...")
        logger.info("💓 Starting DT4ACC Heartbeat Monitor (Independent)...")
        
        # Wait for Tango server to be available
        print("=" * 50)
        print("Waiting for Tango Server")
        print("=" * 50)
        if not wait_for_tango_server():
            print("❌ Cannot start heartbeat - Tango server not available")
            os._exit(1)
        
        # Start heartbeat monitoring
        print("=" * 50)
        print("Starting Heartbeat Monitoring")
        print("=" * 50)
        
        try:
            # Run the heartbeat monitoring
            asyncio.run(monitor_heartbeat_with_shutdown())
        except KeyboardInterrupt:
            print("🛑 Keyboard interrupt received...")
            print("🛑 Shutting down heartbeat...")
        except Exception as e:
            print(f"❌ Heartbeat failed: {e}")
            logger.error(f"❌ Heartbeat failed: {e}")
            os._exit(1)
        
    except Exception as e:
        print(f"❌ Heartbeat monitor failed: {e}")
        logger.error(f"❌ Heartbeat monitor failed: {e}")
        os._exit(1)

if __name__ == "__main__":
    main()
