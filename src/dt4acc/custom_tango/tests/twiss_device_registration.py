import subprocess
import time
from tango import Database, DbDevInfo, DevFailed
from dt4acc.custom_tango.server_config import (
    SERVER_NAME,
    SERVER_CLASS,
    SERVER_INSTANCE
)

def start_tango_server():
    """Start the Tango server in a separate process"""
    print("\nStarting Tango server...")
    server_process = subprocess.Popen(
        ['python', '-m', 'dt4acc.custom_tango.tango_server'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    # Give the server time to start
    time.sleep(5)  # Increased wait time
    return server_process

def verify_server_status():
    """Verify that the Tango server is running and has the device class registered"""
    try:
        db = Database()
        server_list = db.get_server_list()
        print(f"\nRegistered servers: {server_list}")
        
        if SERVER_INSTANCE not in server_list:
            raise DevFailed(f"Server {SERVER_INSTANCE} not found in registered servers")
            
        # Get device class list
        class_list = db.get_class_list()
        print(f"Registered device classes: {class_list}")
        
        if "TwissOrbitDevice" not in class_list:
            raise DevFailed("TwissOrbitDevice class not found in registered classes")
            
        return True
    except Exception as e:
        print(f"Server verification failed: {str(e)}")
        return False

def register_twiss_device():
    """Register the TwissOrbitDevice in the Tango database"""
    try:
        # Create database connection
        db = Database()
        
        # Create device info with proper naming format
        device_name = "tango_server/test/TwissOrbitDevice_twiss_orbit"
        device_info = DbDevInfo()
        device_info._class = "TwissOrbitDevice"
        device_info.server = SERVER_INSTANCE
        device_info.name = device_name
        
        # Add device to database
        db.add_device(device_info)
        print("✓ Device registered in database successfully")
        
        # List all devices to verify registration
        device_list = db.get_device_name(SERVER_INSTANCE, "*")
        print(f"\nRegistered devices: {device_list}")
        
        return device_name
        
    except Exception as e:
        print(f"\nError registering device: {str(e)}")
        raise

def cleanup_twiss_device(device_name):
    """Remove the TwissOrbitDevice from the Tango database"""
    try:
        db = Database()
        db.delete_device(device_name)
        print("\n✓ Test device removed from database")
    except Exception as e:
        print(f"\nError removing device: {str(e)}")
        raise

if __name__ == '__main__':
    # Example usage
    server_process = start_tango_server()
    try:
        if verify_server_status():
            device_name = register_twiss_device()
            print(f"Device registered: {device_name}")
    finally:
        server_process.terminate()
        server_process.wait() 