
import sys
import os


sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from tango.server import run
from dt4acc.custom_tango.ioc.devices.tango_device_setup import get_all_device_classes

def main():
    if len(sys.argv) != 3:
        logger.error("start_tango_server.py should use <server_name> <instance_name>")
        sys.exit(1)
    
    server_name = sys.argv[1]
    instance_name = sys.argv[2]
    
    device_classes = get_all_device_classes()
    
    try:
        run(device_classes, args=[server_name, instance_name])
    except KeyboardInterrupt:
        print("\n Server stopped by user")
    except Exception as e:
        print(f" Server failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
