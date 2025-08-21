#!/usr/bin/env python3
"""
Enhanced Tango Server (Complete) - Full EPICS alignment with heartbeat monitoring
Mirrors EPICS server.py structure exactly.
"""

import os
import getpass
import asyncio
import sys
import threading
import time
import signal

# Add the parent directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from tango.server import run

from dt4acc.custom_tango.tango_device_setup import register_all_devices, get_all_device_classes
from dt4acc.custom_tango.ioc.tasks import monitor_heartbeat
from dt4acc.core.utils.logger import get_logger

logger = get_logger()

# Global variables
tango_server_thread = None
shutdown_event = threading.Event()
global_event_loop = None  # Global reference to the event loop for DelayExecution

def force_exit(signum, frame):
    """Force exit immediately without cleanup."""
    print(f"🛑 Force exit signal {signum} received!")
    print("🚀 Exiting immediately...")
    os._exit(1)

def force_shutdown():
    """Force shutdown immediately without waiting."""
    print("🚀 Force shutdown initiated...")
    logger.info("🚀 Force shutdown initiated...")
    
    # Set shutdown event
    shutdown_event.set()
    
    # Force exit immediately
    print("🚀 Force exiting...")
    os._exit(1)

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    print(f"🛑 Received signal {signum}, shutting down gracefully...")
    
    # Set a timeout for graceful shutdown
    import threading
    def timeout_shutdown():
        time.sleep(3)  # Wait 3 seconds for graceful shutdown
        print("⏰ Graceful shutdown timeout - forcing exit...")
        force_shutdown()
    
    # Start timeout thread
    timeout_thread = threading.Thread(target=timeout_shutdown, daemon=True)
    timeout_thread.start()
    
    # Try graceful shutdown
    cleanup_and_exit()

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGUSR1, force_exit)  # Force exit signal
signal.signal(signal.SIGUSR2, force_exit)  # Force exit signal

# Handle SIGALRM for timeout-based shutdown
def alarm_handler(signum, frame):
    """Handle alarm signal for timeout-based shutdown."""
    print("⏰ Alarm timeout - forcing exit...")
    os._exit(1)

signal.signal(signal.SIGALRM, alarm_handler)

def cleanup_and_exit():
    """Cleanup function to properly shut down all threads."""
    print("🛑 Shutting down gracefully...")
    logger.info("🛑 Shutting down gracefully...")
    
    # Signal shutdown to all threads
    shutdown_event.set()
    
    # Wait for threads to finish (with shorter timeout)
    if tango_server_thread and tango_server_thread.is_alive():
        print("⏳ Waiting for Tango server thread to finish...")
        tango_server_thread.join(timeout=2)  # Reduced timeout
        
        # Force kill if still alive
        if tango_server_thread.is_alive():
            print("⚠️ Tango server thread still alive, forcing termination...")
            # Note: Python threads can't be forcefully killed, but we can mark them as daemon
    
    print("✅ Cleanup completed")
    logger.info("✅ Cleanup completed")
    
    # Restore original asyncio.create_task
    global original_create_task
    if 'original_create_task' in globals():
        asyncio.create_task = original_create_task
        print("✅ Restored original asyncio.create_task")
        logger.info("✅ Restored original asyncio.create_task")
    
    # Stop global event loop if running
    global global_event_loop
    if global_event_loop and global_event_loop.is_running():
        print("⏳ Stopping global event loop...")
        logger.info("⏳ Stopping global event loop...")
        global_event_loop.stop()
        global_event_loop.close()
        print("✅ Global event loop stopped")
        logger.info("✅ Global event loop stopped")
    
    # Force exit immediately to prevent blocking
    print("🚀 Force exiting to prevent blocking...")
    os._exit(0)

def start_tango_server():
    """Start the Tango server in a separate thread."""
    def server_worker():
        """Worker function that runs the Tango server."""
        print("🚀 Tango server worker thread started")
        logger.info("🚀 Tango server worker thread started")
        
        try:
            print("🔧 Registering Tango devices...")
            logger.info("🔧 Registering Tango devices...")
            register_all_devices("SimpleTangoServer", "test")
            
            print("🚀 Tango server initialized and ready!")
            logger.info("🚀 Tango server initialized and ready!")
            
            print("🚀 Starting Tango server...")
            logger.info("🚀 Starting Tango server...")
            
            # Get device classes and start the Tango server
            device_classes = get_all_device_classes()
            run(device_classes, args=["SimpleTangoServer", "test"])
            
        except Exception as e:
            print(f"❌ Tango server worker thread failed: {e}")
            logger.error(f"❌ Tango server worker thread failed: {e}")
        finally:
            print("🚀 Tango server worker thread ending")
            logger.info("🚀 Tango server worker thread ending")
    
    # Start Tango server in background thread
    thread = threading.Thread(target=server_worker, daemon=True)
    thread.start()
    
    print(f"🚀 Tango server thread created: {thread.name}")
    logger.info(f"🚀 Tango server thread created: {thread.name}")
    
    return thread

def wait_for_tango_server_ready():
    """Wait for Tango server to be fully ready and responding."""
    print("⏳ Waiting for Tango server to be ready...")
    logger.info("⏳ Waiting for Tango server to be ready...")
    
    max_attempts = 20  # 30 seconds max wait
    attempt = 0
    
    while attempt < max_attempts:
        try:
            from tango import Database
            db = Database()
            db.get_device_info("SimpleTangoServer/test/twiss_orbit_twiss_device")
            print("✅ Tango server is ready and responding!")
            logger.info("✅ Tango server is ready and responding!")
            return True
            
        except Exception as e:
            attempt += 1
            print(f"⏳ Waiting for Tango server... (attempt {attempt}/{max_attempts})")
            time.sleep(1)
    
    print("❌ Tango server failed to become ready within timeout")
    logger.error("❌ Tango server failed to become ready within timeout")
    return False

def wait_for_devices_ready():
    """Wait for specific devices to be accessible before starting heartbeat."""
    print("⏳ Waiting for specific devices to be accessible...")
    logger.info("⏳ Waiting for specific devices to be accessible...")
    
    # List of critical devices that heartbeat needs
    critical_devices = [
        "SimpleTangoServer/test/power_converter_VS3P2T5R",
        "SimpleTangoServer/test/twiss_orbit_device",
        "SimpleTangoServer/test/bpm_device"
    ]
    
    max_attempts = 50  # 60 seconds max wait
    attempt = 0
    
    while attempt < max_attempts:
        try:
            from tango import DeviceProxy
            
            # Test each critical device
            all_devices_ready = True
            for device_name in critical_devices:
                try:
                    device = DeviceProxy(device_name)
                    # Try to read a simple attribute to verify device is working
                    device.ping()
                    print(f"✅ Device {device_name} is accessible")
                except Exception as e:
                    print(f"⏳ Device {device_name} not ready yet: {e}")
                    all_devices_ready = False
                    break
            
            if all_devices_ready:
                print("✅ All critical devices are accessible!")
                logger.info("✅ All critical devices are accessible!")
                return True
                
        except Exception as e:
            pass
        
        attempt += 1
        print(f"⏳ Waiting for devices... (attempt {attempt}/{max_attempts})")
        time.sleep(1)
    
    print("❌ Critical devices failed to become accessible within timeout")
    logger.error("❌ Critical devices failed to become accessible within timeout")
    return False

def shutdown_helper():
    """Helper function to shutdown the server from command line."""
    import os
    import signal
    
    # Find the main process
    try:
        # Try to send SIGTERM to the main process
        main_pid = os.getpid()
        print(f"🛑 Sending shutdown signal to process {main_pid}")
        os.kill(main_pid, signal.SIGTERM)
        
        # Wait a moment, then force kill if needed
        time.sleep(2)
        print("🚀 Force killing process...")
        os.kill(main_pid, signal.SIGKILL)
        
    except Exception as e:
        print(f"❌ Failed to shutdown: {e}")
        os._exit(1)

def main():
    """Main function to start services sequentially."""
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
        
        print("🚀 Starting DT4ACC Enhanced Tango Server...")
        logger.info("🚀 Starting DT4ACC Enhanced Tango Server...")
        
        # Set up alarm for auto-shutdown after 8 hours (prevent hanging)
        signal.alarm(8 * 60 * 60)  # 8 hours
        
        # Initialize accelerator manager for Twiss data
        #accelerator_manager = initialize_accelerator_manager()
        
        # STEP 1: Start Tango server first
        print("=" * 50)
        print("STEP 1: Starting Tango Server")
        print("=" * 50)
        global tango_server_thread
        tango_server_thread = start_tango_server()
        
        # STEP 2: Wait for Tango server to be ready
        print("=" * 50)
        print("STEP 2: Waiting for Tango Server to be Ready")
        print("=" * 50)
        if not wait_for_tango_server_ready():
            print("❌ Cannot continue - Tango server not ready")
            cleanup_and_exit()
            return
        
        # STEP 2.5: Wait additional 25 seconds for server to be completely stable
        print("=" * 50)
        print("STEP 2.5: Waiting 25 Seconds for Server Stability")
        print("=" * 50)
        print("⏳ Waiting 25 seconds for Tango server to be completely stable...")
        logger.info("⏳ Waiting 25 seconds for Tango server to be completely stable...")
        
        for i in range(25, 0, -1):
            print(f"⏳ Server stability countdown: {i} seconds remaining...")
            time.sleep(1)
        
        print("✅ Server stability wait completed!")
        logger.info("✅ Server stability wait completed!")
        
        # STEP 2.6: Wait for critical devices to be accessible
        print("=" * 50)
        print("STEP 2.6: Waiting for Critical Devices to be Accessible")
        print("=" * 50)
        if not wait_for_devices_ready():
            print("❌ Cannot continue - Critical devices not accessible")
            cleanup_and_exit()
            return
        
        # STEP 3: Heartbeat monitoring is now in separate file
        print("=" * 50)
        print("STEP 3: Heartbeat Monitoring (Disabled - Use Separate File)")
        print("=" * 50)
        print("💓 Heartbeat monitoring is now in separate file: heartbeat_monitor.py")
        print("💓 Run heartbeat_monitor.py in a separate terminal after server is ready")
        logger.info("💓 Heartbeat monitoring is now in separate file: heartbeat_monitor.py")
        
        # STEP 4: Start Global Event Loop for DelayExecution Tasks (EPICS-style)
        print("=" * 50)
        print("STEP 4: Starting Global Event Loop (EPICS-style)")
        print("=" * 50)
        print("✅ Tango server started successfully!")
        print("🔄 Starting global event loop for DelayExecution tasks...")
        logger.info("✅ Tango server started successfully!")
        logger.info("🔄 Starting global event loop for DelayExecution tasks...")
        
        # Set environment variable for Tango mode
        os.environ["server"] = "tango"
        
        # Create global event loop (similar to EPICS asyncio_dispatcher)
        global global_event_loop
        global_event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(global_event_loop)
        
        # Start the global event loop in a separate thread (EPICS-style)
        def run_global_event_loop():
            """Run the global event loop for DelayExecution tasks (EPICS-style)."""
            try:
                asyncio.set_event_loop(global_event_loop)
                print("🔄 Global event loop started in background thread")
                logger.info("🔄 Global event loop started in background thread")
                
                # Run the event loop forever (like EPICS dispatcher)
                global_event_loop.run_forever()
                
            except Exception as e:
                print(f"❌ Global event loop failed: {e}")
                logger.error(f"❌ Global event loop failed: {e}")
        
        # Start global event loop thread
        global_loop_thread = threading.Thread(target=run_global_event_loop, daemon=True)
        global_loop_thread.start()
        print("✅ Global event loop thread started")
        logger.info("✅ Global event loop thread started")
        
        # Wait a moment for the event loop to be ready
        time.sleep(1)
        
        # Verify event loop is running
        if global_event_loop.is_running():
            print("✅ Global event loop is running and ready")
            logger.info("✅ Global event loop is running and ready")
        else:
            print("⚠️ Global event loop not running yet, waiting...")
            logger.warning("⚠️ Global event loop not running yet, waiting...")
            time.sleep(2)
        
        # Monkey-patch asyncio.create_task to use our global event loop in Tango mode
        # This ensures DelayExecution.asyncio.create_task() works properly
        original_create_task = asyncio.create_task
        
        def tango_create_task(coro, *, name=None):
            """Tango-compatible create_task that uses global event loop."""
            global global_event_loop
            if global_event_loop and global_event_loop.is_running():
                # Use global event loop for Tango mode
                future = asyncio.run_coroutine_threadsafe(coro, global_event_loop)
                print(f"🔄 Task scheduled in global event loop: {future}")
                logger.info(f"🔄 Task scheduled in global event loop: {future}")
                return future
            else:
                # Fall back to original behavior
                return original_create_task(coro, name=name)
        
        # Apply the monkey patch
        asyncio.create_task = tango_create_task
        print("✅ Monkey-patched asyncio.create_task for Tango compatibility")
        logger.info("✅ Monkey-patched asyncio.create_task for Tango compatibility")
        
        # Test the global event loop with a simple task
        async def test_global_event_loop():
            """Test function to verify global event loop is working."""
            print("🧪 Test task started in global event loop")
            await asyncio.sleep(0.1)
            print("🧪 Test task completed successfully")
            return "test_success"
        
        try:
            # Test scheduling a task in the global event loop
            test_future = asyncio.create_task(test_global_event_loop())
            print(f"🧪 Test task scheduled: {test_future}")
            logger.info(f"🧪 Test task scheduled: {test_future}")
            
            # Wait a moment for the task to complete
            time.sleep(0.2)
            
            if test_future.done():
                result = test_future.result()
                print(f"🧪 Test task result: {result}")
                logger.info(f"🧪 Test task result: {result}")
            else:
                print("⚠️ Test task did not complete within timeout")
                logger.warning("⚠️ Test task did not complete within timeout")
                
        except Exception as e:
            print(f"⚠️ Test task failed: {e}")
            logger.warning(f"⚠️ Test task failed: {e}")
        
        # STEP 5: Monitor Tango server and global event loop
        print("=" * 50)
        print("STEP 5: Monitoring Tango Server and Global Event Loop")
        print("=" * 50)
        print("👀 Main thread monitoring Tango server and global event loop...")
        logger.info("👀 Main thread monitoring Tango server and global event loop...")
        
        try:
            # Keep main thread alive and monitor both threads
            while True:
                # Check if Tango server thread is still alive
                if not tango_server_thread.is_alive():
                    print("❌ Tango server thread died!")
                    logger.error("❌ Tango server thread died!")
                    break
                
                # Check if global event loop thread is still alive
                if not global_loop_thread.is_alive():
                    print("❌ Global event loop thread died!")
                    logger.error("❌ Global event loop thread died!")
                    break
                
                # Check if global event loop is still running
                if not global_event_loop.is_running():
                    print("❌ Global event loop stopped!")
                    logger.error("❌ Global event loop stopped!")
                    break
                
                time.sleep(10)  # Check every 10 seconds
                
        except KeyboardInterrupt:
            print("🛑 Keyboard interrupt received...")
            cleanup_and_exit()
        except Exception as e:
            print(f"❌ Server monitoring failed: {e}")
            logger.error(f"❌ Server monitoring failed: {e}")
            cleanup_and_exit()
        finally:
            # Ensure cleanup happens even on normal exit
            print("🔄 Final cleanup...")
            cleanup_and_exit()
        
    except Exception as e:
        print(f"❌ Enhanced Tango server failed: {e}")
        logger.error(f"❌ Enhanced Tango server failed: {e}")
        cleanup_and_exit()

if __name__ == "__main__":
    main() 