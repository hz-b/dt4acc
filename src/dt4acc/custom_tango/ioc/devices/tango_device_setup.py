# tango_device_setup.py  (SOLEIL-style Tango registration)
#
# REAL DEVICES:
#   domain  = ANxx-AR
#   family  = EM, SD, etc.
#   member  = e.g. SHF.11, SHF.11-CDLH.03, SHF.11-pc
#
# Tango device = "AN10-AR/EM/SHF.11"
# Tango server = "AN10-AR/EM"
#
# VIRTUAL DEVICES (Twiss, Orbit, BPM, Tune, OtherPVs, MasterClock)
# are placed under a synthetic fixed server, e.g.:
#   PHYSICS/SOLEIL/TWISS
#   PHYSICS/SOLEIL/ORBIT
#   RF/SOLEIL/MASTER_CLOCK

from tango import Database, DbDevInfo, DevFailed
from dt4acc.core.utils.logger import get_logger

from dt4acc.custom_epics.data.querries import (
    get_unique_power_converters,
    get_magnets_per_power_converters,
)
from dt4acc.custom_epics.data.constants import cavity_names

# Import device classes (your existing files)
from .magnet_device import MagnetDevice
from .power_converter_device import PowerConverterDevice
from .virtual_devices import (
    MasterClockDevice,
    CavityDevice,
    TuneDevice,
    OtherPVsDevice,
    TwissOrbitDevice,
    BPMManagerDevice
)

logger = get_logger()


# ----------------------------------------------------------------------
# Helper: extract Tango server & instance from Soleil device name
# Soleil naming format: "AN10-AR/EM/SCF.11"
# → domain  = "AN10-AR"
# → family  = "EM"
# → member  = "SCF.11"
# → device full name = "AN10-AR/EM/SCF.11"
# → server descriptor = "AN10-AR/EM"
# ----------------------------------------------------------------------
def split_tango_name(name: str):
    """Return (domain, family, member)."""
    parts = name.split("/")
    if len(parts) != 3:
        raise ValueError(f"Invalid Soleil Tango name: {name}")
    return parts[0], parts[1], parts[2]


# ----------------------------------------------------------------------
# Register a REAL device (magnet or power converter)
# ----------------------------------------------------------------------
def register_real_device(db: Database, full_name: str, class_name: str):
    """
    Create a real Tango device with the correct Soleil naming:
        server = "domain/family"
        name   = "domain/family/member"
    """
    domain, family, member = split_tango_name(full_name)
    server_desc = f"{domain}/{family}"
    device_name = f"{domain}/{family}/{member}"

    dev = DbDevInfo()
    dev._class = class_name
    dev.name = device_name
    dev.server = server_desc

    try:
        db.add_device(dev)
        logger.info(f"Registered device: {device_name} (class={class_name})")
    except DevFailed as e:
        logger.warning(f"Device {device_name} exists or failed to register: {e}")

    return device_name


# ----------------------------------------------------------------------
# Register a virtual device using a constant server
# ----------------------------------------------------------------------
def register_virtual_device(db: Database, device_name: str, class_name: str, server="PHYSICS/SOLEIL"):
    dev = DbDevInfo()
    dev._class = class_name
    dev.name = device_name
    dev.server = server

    try:
        db.add_device(dev)
        logger.info(f"Registered virtual device: {device_name}")
    except DevFailed as e:
        logger.warning(f"Virtual device {device_name} exists or failed: {e}")


# ----------------------------------------------------------------------
# Write Tango device properties
# ----------------------------------------------------------------------
def set_properties(db: Database, device_name: str, props: dict):
    try:
        db.put_device_property(device_name, props)
        logger.info(f"Set properties for {device_name}: {props}")
    except DevFailed as e:
        logger.error(f"Failed to write properties for {device_name}: {e}")


# ----------------------------------------------------------------------
# MAIN REGISTRATION FUNCTION
# ----------------------------------------------------------------------
def register_all_devices():
    """
    Register all Soleil devices correctly according to Soleil Tango naming.
    No global server!! Each ANxx-AR/EM has its own Tango server instance.
    """
    db = Database()

    # -----------------------------
    # REAL MAGNETS + POWER SUPPLIES
    # -----------------------------
    for pc_name in get_unique_power_converters():
        magnets = get_magnets_per_power_converters(pc_name)
        magnet_names = [m["name"] for m in magnets]

        # Register power converter device
        pc_device_name = register_real_device(db, pc_name, "PowerConverterDevice")
        set_properties(db, pc_device_name, {
            "name": [pc_name],
            "magnet_list": magnet_names,
        })

        # Register each magnet device
        for m in magnets:
            magnet_name = m["name"]
            magnet_type = m.get("type", "unknown")

            magnet_device_name = register_real_device(db, magnet_name, magnet_type)
            set_properties(db, magnet_device_name, {
                "name":       [magnet_name],
                "pc_name":    [pc_name],
                "type":       [magnet_type],
            })

    # -----------------------------
    # VIRTUAL DEVICES (one server)
    # -----------------------------
    register_virtual_device(db, "SOLEIL/PHYSICS/TWISS_ORBIT", "TwissOrbitDevice")
    register_virtual_device(db, "SOLEIL/MONITOR/BPM", "BPMManagerDevice")
    register_virtual_device(db, "SOLEIL/PHYSICS/OTHER_PVS", "OtherPVsDevice")
    register_virtual_device(db, "SOLEIL/PHYSICS/TUNE", "TuneDevice")
    register_virtual_device(db, "SOLEIL/RF/MASTER_CLOCK", "MasterClockDevice", server="RF/SOLEIL")

    # Cavity devices
    for cav in cavity_names:
        cav_name = f"SOLEIL/RF/{cav}"
        register_virtual_device(db, cav_name, "CavityDevice", server="RF/SOLEIL")
        set_properties(db, cav_name, {"name": [cav]})

    logger.info("✔ All Soleil devices registered successfully.")


# ----------------------------------------------------------------------
# SERVER MUST KNOW WHICH CLASSES CAN BE RUN
# ----------------------------------------------------------------------
def get_all_device_classes():
    return [
        MagnetDevice,
        PowerConverterDevice,
        TwissOrbitDevice,
        BPMManagerDevice,
        MasterClockDevice,
        CavityDevice,
        TuneDevice,
        OtherPVsDevice,
    ]
