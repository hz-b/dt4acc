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
            logger.info("Initializing view for heartbeat service...")
            
            os.environ["server"] = "tango"
            
            self.view = get_view_instance()
            logger.info(f" View initialized: {type(self.view).__name__}")
            
            if hasattr(self.view, 'heart_beat'):
                logger.info(f"View has heart_beat method")
                return True
            else:
                logger.error(f" View does not have heart_beat method")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize view: {e}")
            return False
    
    async def heartbeat_loop(self):
        """Main heartbeat loop."""
        logger.info("Starting heartbeat loop...")
        
        self.start_time = datetime.now()
        self.iteration = 0
        
        while self.running:
            try:
                await asyncio.sleep(self.interval_seconds)
                self.iteration += 1
                
                await self.view.heart_beat()
                
                if hasattr(self.view, 'monitor_updates'):
                    pass
                
                if self.iteration % self.log_interval == 0:
                    elapsed = datetime.now() - self.start_time
                    logger.info(f"Heartbeat iteration {self.iteration} (elapsed: {elapsed})")
                
            except asyncio.CancelledError:
                logger.warning("Heartbeat loop was cancelled")
                break
            except Exception as e:
                logger.error(f"Heartbeat error at iteration {self.iteration}: {e}")
                # Continue running even if there's an error
                await asyncio.sleep(self.interval_seconds)
        
        logger.info("Heartbeat loop stopped")
    
    def start(self):
        """Start the heartbeat service."""
        if self.running:
            return False
        
        logger.info("Starting Heartbeat Service...")
        
        if not self.initialize_view():
            print("❌ Failed to initialize view. Cannot start heartbeat.")
            return False
        
        self.running = True
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            logger.info(" Heartbeat service started successfully!")
            
            loop.run_until_complete(self.heartbeat_loop())
            
        except KeyboardInterrupt:
            logger.info(" Heartbeat service interrupted by user")
        except Exception as e:
            logger.error(f"Heartbeat service error: {e}")
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
        
        logger.info(" Stopping Heartbeat Service...")
        
        self.running = False
        
        if self.start_time:
            total_time = datetime.now() - self.start_time
            logger.info(f"Heartbeat service ran for {total_time} ({self.iteration} iterations)")
        
        logger.info("Heartbeat service stopped")

def signal_handler(signum, frame):
    """Handle interrupt signals."""
    if heartbeat_service:
        heartbeat_service.stop()
    sys.exit(0)

def main():
    """Main entry point for heartbeat service."""
    global heartbeat_service
    
    print("=" * 50)
    print("This service runs independently of the Tango server.")
    print("Make sure the Tango server is running before starting this service.")
    print("Press Ctrl+C to stop the service.")
    print("=" * 50)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    heartbeat_service = HeartbeatService(interval_seconds=1, log_interval=10)
    
    try:
        heartbeat_service.start()
    except KeyboardInterrupt:
    except Exception as e:
        logger.error(f" Service failed: {e}")

if __name__ == "__main__":
    heartbeat_service = None
    main() 