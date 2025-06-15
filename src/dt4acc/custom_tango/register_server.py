from tango import Database, DbDevInfo
from dt4acc.custom_tango.ioc.devices.bpm_device import BPMDevice
from dt4acc.custom_tango.ioc.devices.twiss_orbit_device import TwissOrbitDevice

SERVER_INSTANCE = "tango_server/test"


print(f"[INIT] Registering server and devices in Tango DB...")
db = Database()

# Register BPMDevice
dev1 = DbDevInfo()
dev1.name = "tango_server/test/BPMDevice_MDIZ2T5G"
dev1._class = "BPMDevice"
dev1.server = SERVER_INSTANCE
db.add_device(dev1)

# Register TwissOrbitDevice
dev2 = DbDevInfo()
dev2.name = "tango_server/test/TwissOrbitDevice_MAIN"
dev2._class = "TwissOrbitDevice"
dev2.server = SERVER_INSTANCE
db.add_device(dev2)

print("✅ Server and devices registered in Tango DB.")
