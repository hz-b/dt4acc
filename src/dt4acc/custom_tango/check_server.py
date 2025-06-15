import os
from tango import Database, DeviceProxy
from dt4acc.custom_tango.server_config import SERVER_NAME, SERVER_INSTANCE

os.environ["TANGO_HOST"] = "localhost:10000"

def check_server_status():
    try:
        admin = DeviceProxy('dserver/tango_server/test')
        print("\nServer Status:")
        print("-" * 50)
        print(f"Server: {SERVER_NAME}")
        print(f"Server name: {admin.name()}")
        print(f"Server state: {admin.state()}")
        print(f"Server status: {admin.status()}")
        print("-" * 50)
        
        # List all devices
        print("\nRegistered Devices:")
        print("-" * 50)
        db = Database()
        devices = db.get_device_name('tango_server/test', '*')
        for device in devices:
            print(f"Device: {device}")
        print("-" * 50)
        
    except Exception as e:
        print(f"Error checking server status: {e}")

if __name__ == "__main__":
    check_server_status() 