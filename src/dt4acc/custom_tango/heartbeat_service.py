#!/usr/bin/env python3
"""
Separate Heartbeat Service - runs independently of Tango server.
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

class HeartbeatService:
    """Separate heartbeat service that runs independently."""
    
    def __init__(self, interval_seconds: int = 1, log_interval: int = 10):
        self.interval_seconds = interval_seconds
        self.log_interval = log_interval  # Log every N iterations
        self.running = False
        self.view = None
        self.iteration = 0
        self.start_time = None
        
    def initialize_view(self):
        """Initialize the view instance."""
        try:
            print("🔧 Initializing view for heartbeat service...")
            logger.info("🔧 Initializing view for heartbeat service...")
            
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
    
    async def heartbeat_loop(self):
        """Main heartbeat loop."""
        print("💓 Starting heartbeat loop...")
        logger.info("💓 Starting heartbeat loop...")
        
        self.start_time = datetime.now()
        self.iteration = 0
        
        while self.running:
            try:
                await asyncio.sleep(self.interval_seconds)
                self.iteration += 1
                
                # Call the heart_beat method to catch updates
                await self.view.heart_beat()
                
                # Also check for any pending updates in the view
                if hasattr(self.view, 'monitor_updates'):
                    # This will trigger any pending calculations
                    pass
                
                # Log progress every N iterations
                if self.iteration % self.log_interval == 0:
                    elapsed = datetime.now() - self.start_time
                    print(f"💓 Heartbeat iteration {self.iteration} (elapsed: {elapsed})")
                    logger.info(f"💓 Heartbeat iteration {self.iteration} (elapsed: {elapsed})")
                
            except asyncio.CancelledError:
                print("💓 Heartbeat loop was cancelled")
                logger.warning("💓 Heartbeat loop was cancelled")
                break
            except Exception as e:
                print(f"❌ Heartbeat error at iteration {self.iteration}: {e}")
                logger.error(f"❌ Heartbeat error at iteration {self.iteration}: {e}")
                # Continue running even if there's an error
                await asyncio.sleep(self.interval_seconds)
        
        print("💓 Heartbeat loop stopped")
        logger.info("💓 Heartbeat loop stopped")
    
    def start(self):
        """Start the heartbeat service."""
        if self.running:
            print("⚠️ Heartbeat service is already running")
            return False
        
        print("🚀 Starting Heartbeat Service...")
        logger.info("🚀 Starting Heartbeat Service...")
        
        # Initialize view
        if not self.initialize_view():
            print("❌ Failed to initialize view. Cannot start heartbeat.")
            return False
        
        # Start the heartbeat loop
        self.running = True
        
        try:
            # Create and run the event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            print("💓 Heartbeat service started successfully!")
            logger.info("💓 Heartbeat service started successfully!")
            
            # Run the heartbeat loop
            loop.run_until_complete(self.heartbeat_loop())
            
        except KeyboardInterrupt:
            print("\n⏹️ Heartbeat service interrupted by user")
            logger.info("💓 Heartbeat service interrupted by user")
        except Exception as e:
            print(f"❌ Heartbeat service error: {e}")
            logger.error(f"❌ Heartbeat service error: {e}")
        finally:
            self.stop()
            try:
                loop.close()
            except:
                pass
    
    def stop(self):
        """Stop the heartbeat service."""
        if not self.running:
            return
        
        print("🛑 Stopping Heartbeat Service...")
        logger.info("🛑 Stopping Heartbeat Service...")
        
        self.running = False
        
        if self.start_time:
            total_time = datetime.now() - self.start_time
            print(f"📊 Heartbeat service ran for {total_time} ({self.iteration} iterations)")
            logger.info(f"📊 Heartbeat service ran for {total_time} ({self.iteration} iterations)")
        
        print("✅ Heartbeat service stopped")
        logger.info("✅ Heartbeat service stopped")

def signal_handler(signum, frame):
    """Handle interrupt signals."""
    print(f"\n📡 Received signal {signum}. Stopping heartbeat service...")
    if heartbeat_service:
        heartbeat_service.stop()
    sys.exit(0)

def main():
    """Main entry point for heartbeat service."""
    global heartbeat_service
    
    print("💓 Standalone Heartbeat Service")
    print("=" * 50)
    print("This service runs independently of the Tango server.")
    print("Make sure the Tango server is running before starting this service.")
    print("Press Ctrl+C to stop the service.")
    print("=" * 50)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create heartbeat service
    heartbeat_service = HeartbeatService(interval_seconds=1, log_interval=10)
    
    try:
        # Start the service
        heartbeat_service.start()
    except KeyboardInterrupt:
        print("\n⏹️ Service stopped by user")
    except Exception as e:
        print(f"❌ Service failed: {e}")
        logger.error(f"❌ Service failed: {e}")

if __name__ == "__main__":
    heartbeat_service = None
    main() 