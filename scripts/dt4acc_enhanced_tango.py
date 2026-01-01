
import logging
import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

logging.basicConfig(level=logging.WARNING)

os.environ["server"] = "tango"

from dt4acc.custom_tango.ioc.devices.server_tango import main

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n Tango server stopped by user")
    except Exception as e:
        print(f"Tango server failed: {e}")
        raise 