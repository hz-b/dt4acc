#!/usr/bin/env python3
"""
Update Monitor Service - monitors and logs updates like EPICS version.
Runs independently from Tango server.
"""

import os
import sys
import time
import asyncio
import threading
import signal
from datetime import datetime

# Add src to path (now we're in custom_tango folder)
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from dt4acc.core.utils.logger import get_logger
from dt4acc.core.views.shared_view import get_view_instance

logger = get_logger()

class UpdateMonitorService:
    """Service that monitors and logs updates like EPICS version."""
    
    def __init__(self, interval_seconds: int = 1, log_interval: int = 10):
        self.interval_seconds = interval_seconds
        self.log_interval = log_interval  # Log every N iterations
        self.running = False
        self.view = None
        self.iteration = 0
        self.start_time = None
        self.last_update_time = None
        
    def initialize_view(self):
        """Initialize the view instance."""
        try:
            print("🔧 Initializing view for update monitor...")
            logger.info("🔧 Initializing view for update monitor...")
            
            # Set environment variable for Tango view
            os.environ["server"] = "tango"
            
            # Get the view instance
            self.view = get_view_instance()
            print(f"✅ View initialized: {type(self.view).__name__}")
            logger.info(f"✅ View initialized: {type(self.view).__name__}")
            
            # Test if view has heart_beat method
            if hasattr(self.view, 'heart_beat'):
                print(f"✅ View has heart_beat method")
                logger.info(f"✅ View has heart_beat method")
                return True
            else:
                print(f"❌ View does not have heart_beat method")
                logger.error(f"❌ View does not have heart_beat method")
                return False
                
        except Exception as e:
            print(f"❌ Failed to initialize view: {e}")
            logger.error(f"❌ Failed to initialize view: {e}")
            return False
    
    async def monitor_heartbeat(self):
        """Monitor heartbeat and log updates like EPICS."""
        print("💓 Starting update monitor...")
        logger.info("💓 Starting update monitor...")
        
        self.start_time = datetime.now()
        self.iteration = 0
        
        while self.running:
            try:
                await asyncio.sleep(self.interval_seconds)
                self.iteration += 1
                
                # Call the heart_beat method (like EPICS)
                try:
                    await self.view.heart_beat()
                    
                    # Log like EPICS - show when updates happen
                    current_time = datetime.now()
                    if self.last_update_time is None or (current_time - self.last_update_time).seconds >= 5:
                        # Log periodic status (like EPICS heartbeat)
                        logger.info(f"Update monitor heartbeat at {current_time}")
                        print(f"💓 Update monitor heartbeat at {current_time}")
                        self.last_update_time = current_time
                    
                except Exception as e:
                    logger.error(f"💓 Heartbeat call failed: {e}")
                    print(f"❌ Heartbeat call failed: {e}")
                
                # Log progress every N iterations (like EPICS minimal logging)
                if self.iteration % self.log_interval == 0:
                    elapsed = datetime.now() - self.start_time
                    logger.info(f"Update monitor iteration {self.iteration} (elapsed: {elapsed})")
                    print(f"💓 Update monitor iteration {self.iteration} (elapsed: {elapsed})")
                
            except asyncio.CancelledError:
                print("💓 Update monitor was cancelled")
                logger.warning("💓 Update monitor was cancelled")
                break
            except Exception as e:
                print(f"❌ Update monitor error at iteration {self.iteration}: {e}")
                logger.error(f"❌ Update monitor error at iteration {self.iteration}: {e}")
                # Continue running even if there's an error
                await asyncio.sleep(self.interval_seconds)
        
        print("💓 Update monitor stopped")
        logger.info("💓 Update monitor stopped")
    
    def start(self):
        """Start the update monitor service."""
        if self.running:
            print("⚠️ Update monitor service is already running")
            return False
        
        print("🚀 Starting Update Monitor Service...")
        logger.info("🚀 Starting Update Monitor Service...")
        
        # Initialize view
        if not self.initialize_view():
            print("❌ Failed to initialize view. Cannot start update monitor.")
            return False
        
        # Start the monitor loop
        self.running = True
        
        try:
            # Create and run the event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            print("💓 Update monitor service started successfully!")
            logger.info("💓 Update monitor service started successfully!")
            
            # Run the monitor loop
            loop.run_until_complete(self.monitor_heartbeat())
            
        except KeyboardInterrupt:
            print("\n⏹️ Update monitor service interrupted by user")
            logger.info("💓 Update monitor service interrupted by user")
        except Exception as e:
            print(f"❌ Update monitor service error: {e}")
            logger.error(f"❌ Update monitor service error: {e}")
        finally:
            self.stop()
            try:
                loop.close()
            except:
                pass
    
    def stop(self):
        """Stop the update monitor service."""
        if not self.running:
            return
        
        print("🛑 Stopping Update Monitor Service...")
        logger.info("🛑 Stopping Update Monitor Service...")
        
        self.running = False
        
        if self.start_time:
            total_time = datetime.now() - self.start_time
            print(f"📊 Update monitor service ran for {total_time} ({self.iteration} iterations)")
            logger.info(f"📊 Update monitor service ran for {total_time} ({self.iteration} iterations)")
        
        print("✅ Update monitor service stopped")
        logger.info("✅ Update monitor service stopped")

def signal_handler(signum, frame):
    """Handle interrupt signals."""
    print(f"\n📡 Received signal {signum}. Stopping update monitor service...")
    if update_monitor_service:
        update_monitor_service.stop()
    sys.exit(0)

def main():
    """Main entry point for update monitor service."""
    global update_monitor_service
    
    print("💓 Update Monitor Service (EPICS-style logging)")
    print("=" * 60)
    print("This service monitors updates and logs them like the EPICS version.")
    print("Make sure the Tango server is running before starting this service.")
    print("Press Ctrl+C to stop the service.")
    print("=" * 60)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create update monitor service
    update_monitor_service = UpdateMonitorService(interval_seconds=1, log_interval=10)
    
    try:
        # Start the service
        update_monitor_service.start()
    except KeyboardInterrupt:
        print("\n⏹️ Service stopped by user")
    except Exception as e:
        print(f"❌ Service failed: {e}")
        logger.error(f"❌ Service failed: {e}")

if __name__ == "__main__":
    update_monitor_service = None
    main() 