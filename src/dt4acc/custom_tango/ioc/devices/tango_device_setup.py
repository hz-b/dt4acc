# tango_device_setup.py

from tango import Database, DbDevInfo, DevFailed
from dt4acc.core.utils.logger import get_logger
from dt4acc.config.data.querries import (
    get_unique_power_converters,
    get_magnets_per_power_converters,
    get_unique_power_converters_type_specified,
    get_bpms,
)

from dt4acc.custom_tango.ioc.devices.multipole_device import MultipoleDevice
from dt4acc.custom_tango.ioc.devices.steerer_device import HorizontalSteererDevice, VerticalSteererDevice
from dt4acc.custom_tango.ioc.devices.skew_quad_device import SkewQuadDevice
from dt4acc.custom_tango.ioc.devices.cavity_device import CavityDevice
from dt4acc.custom_tango.ioc.devices.virtual_devices import RingSimulatorDevice, RING_SIM_DEV
from dt4acc.custom_tango.ioc.devices.power_converter_device import PowerConverterDevice
from dt4acc.custom_tango.ioc.devices.bpm_device import BPMDevice

logger = get_logger()

# Map JSON "type" field → Tango device class name
_TYPE_TO_CLASS = {
    "Quadrupole":    "MultipoleDevice",
    "Sextupole":     "MultipoleDevice",
    "Octupole":      "MultipoleDevice",
    "Multipole":     "MultipoleDevice",
    "Steerer":       None,   # determined by is_horizontal/is_vertical below
    "SkewQuadrupole": "SkewQuadDevice",
    "RFCavity":      "CavityDevice",
}

def _steerer_class(name: str, subtype: str = None) -> str:
    """
    Determine steerer class from device name or subtype field.
    subtype="H"/"V" is set by MAX IV JSON generator.
    SOLEIL uses name patterns (CDLH/CDLV).
    """
    if subtype == "H":
        return "HorizontalSteererDevice"
    if subtype == "V":
        return "VerticalSteererDevice"
    # SOLEIL fallback — name-based detection
    if "CDLH" in name or "CDRH" in name or "CRFCX" in name or "CRCOX" in name:
        return "HorizontalSteererDevice"
    if "CDLV" in name or "CDRV" in name or "CRFCY" in name or "CRCOY" in name:
        return "VerticalSteererDevice"
    return "HorizontalSteererDevice"


def _split_domain_family_member(device_name: str):
    """AN10-AR/EM/SCF.11 -> ('AN10-AR', 'EM', 'SCF.11')"""
    parts = device_name.split("/")
    if len(parts) != 3:
        raise ValueError(f"Invalid Soleil device name: {device_name}")
    return parts[0], parts[1], parts[2]


def _register_dservers(db: Database, servers: set[tuple[str, str]]):
    """
    Ensure a DServer device exists for each (server_name, instance_name).

    For (AN10-AR, EM) we create:
      name   = dserver/AN10-AR/EM
      server = AN10-AR/EM
      class  = DServer
    """
    for server_name, instance_name in sorted(servers):
        dserver_name = f"dserver/{server_name}/{instance_name}"
        server_str = f"{server_name}/{instance_name}"

        db_dev = DbDevInfo()
        db_dev._class = "DServer"
        db_dev.server = server_str
        db_dev.name = dserver_name

        try:
            db.add_device(db_dev)
            logger.info(f"🧱 Registered DServer device {dserver_name} (server={server_str})")
        except DevFailed as e:
            # Ignore 'already exists' style errors, log others
            msg = str(e)
            if "DB_DuplicateKey" in msg or "already" in msg or "Duplicate" in msg:
                logger.debug(f"DServer {dserver_name} already exists, skipping.")
            else:
                logger.error(f"❌ Failed to register DServer {dserver_name}: {e}")


def register_all_devices():
    """
    Register ALL Soleil devices in the Tango DB.

    - Device *names* are the Soleil-style names (AN10-AR/EM/SCF.11, ...).
    - For each device name:
        domain  -> server_name
        family  -> instance_name
        server  -> f"{server_name}/{instance_name}"
    - Also registers DServer devices for each (server_name, instance_name).

    Returns:
        list[(server_name, instance_name)] : all unique device servers to start.
    """
    db = Database()
    unique_servers: set[tuple[str, str]] = set()

    logger.info("📝 Registering ALL devices into Tango DB...")

    # ------------------------------------------------------------
    # 1) Magnets — registered by Tango name (magnet TRL)
    #    UUID/uuids stored as DB property for AT element lookup.
    # ------------------------------------------------------------
    for pc_name in get_unique_power_converters():
        magnets = get_magnets_per_power_converters(pc_name)
        for m in magnets:
            magnet_name = m["name"]
            magnet_uuid = m.get("uuid", "") or (m.get("uuids", [""])[0] if m.get("uuids") else "")
            magnet_type = m.get("type", "")
            magnet_subtype = m.get("subtype", "")
            try:
                domain, family, _ = _split_domain_family_member(magnet_name)
                server_name   = domain
                instance_name = family
                server_str    = f"{server_name}/{instance_name}"
                unique_servers.add((server_name, instance_name))

                # Pick the correct Tango class for this physical type
                if magnet_type == "Steerer":
                    class_name = _steerer_class(magnet_name, subtype=magnet_subtype)
                else:
                    class_name = _TYPE_TO_CLASS.get(magnet_type, "MultipoleDevice")

                db_dev        = DbDevInfo()
                db_dev._class = class_name
                db_dev.server = server_str
                db_dev.name   = magnet_name
                db.add_device(db_dev)

                # Store UUID so the device can uniquely identify its AT element
                if magnet_uuid:
                    try:
                        db.put_device_property(
                            magnet_name, {"element_uuid": [magnet_uuid]}
                        )
                    except Exception as e:
                        logger.warning("Could not set uuid property for %s: %s",
                                       magnet_name, e)

                logger.info("🧲 Registered magnet %s uuid=%s (server=%s)",
                            magnet_name, magnet_uuid, server_str)
            except Exception as e:
                logger.error("❌ Failed to register magnet %s: %s", magnet_name, e)

    # ------------------------------------------------------------
    # 2) Power converters — registered as PowerConverterDevice (device view)
    #    Each PC TRL becomes a Tango device so current can be written to it.
    #    Skipped if the PC name is not a valid 3-part TRL (e.g. cavity PCs).
    # ------------------------------------------------------------
    registered_pcs = set()
    for pc_name in get_unique_power_converters():
        if pc_name in registered_pcs:
            continue
        registered_pcs.add(pc_name)
        try:
            domain, family, _ = _split_domain_family_member(pc_name)
            server_name   = domain
            instance_name = family
            server_str    = f"{server_name}/{instance_name}"
            unique_servers.add((server_name, instance_name))

            db_dev        = DbDevInfo()
            db_dev._class = "PowerConverterDevice"
            db_dev.server = server_str
            db_dev.name   = pc_name
            db.add_device(db_dev)

            logger.info("⚡ Registered PC %s (server=%s)", pc_name, server_str)
        except Exception as e:
            logger.warning("Skipping PC %s (not a valid TRL?): %s", pc_name, e)

    # ------------------------------------------------------------
    # 2) Cavities and SkewQuadrupoles — registered as typed devices
    # ------------------------------------------------------------
    for pc_name in get_unique_power_converters_type_specified(["RFCavity", "SkewQuadrupole"]):
        for m in get_magnets_per_power_converters(pc_name):
            dev_name  = m["name"]
            dev_uuid  = m.get("uuid", "")
            dev_type  = m.get("type", "")
            class_name = _TYPE_TO_CLASS.get(dev_type, "MultipoleDevice")
            try:
                domain, family, _ = _split_domain_family_member(dev_name)
                server_name   = domain
                instance_name = family
                server_str    = f"{server_name}/{instance_name}"
                unique_servers.add((server_name, instance_name))

                db_dev        = DbDevInfo()
                db_dev._class = class_name
                db_dev.server = server_str
                db_dev.name   = dev_name
                db.add_device(db_dev)

                if dev_uuid:
                    try:
                        db.put_device_property(dev_name, {"element_uuid": [dev_uuid]})
                    except Exception as e:
                        logger.warning("Could not set uuid for %s: %s", dev_name, e)

                logger.info("📡 Registered %s %s uuid=%s (server=%s)",
                            class_name, dev_name, dev_uuid, server_str)
            except Exception as e:
                logger.error("❌ Failed to register %s %s: %s", dev_type, dev_name, e)

    # ------------------------------------------------------------
    # 3) Single RingSimulatorDevice — replaces all PHYSICS/SOLEIL/* devices
    # ------------------------------------------------------------
    try:
        domain, family, _ = _split_domain_family_member(RING_SIM_DEV)
        server_name   = domain
        instance_name = family
        server_str    = f"{server_name}/{instance_name}"
        unique_servers.add((server_name, instance_name))

        db_dev        = DbDevInfo()
        db_dev._class = "RingSimulatorDevice"
        db_dev.server = server_str
        db_dev.name   = RING_SIM_DEV
        db.add_device(db_dev)
        logger.info("🔭 Registered RingSimulatorDevice %s (server=%s)", RING_SIM_DEV, server_str)
    except Exception as e:
        logger.error("❌ Failed to register RingSimulatorDevice: %s", e)

    # ------------------------------------------------------------
    # 4) BPM devices — one per Monitor element, read-only
    # ------------------------------------------------------------
    # Build s_pos → AT element index map by loading the lattice directly.
    # AT element s positions are computed via at.get_s_pos() — not stored
    # on individual elements.
    bpm_index_map: dict = {}  # uuid → AT element index
    try:
        import at as _at
        from dt4acc.custom_tango.ioc.server_manager import LATTICE_FILE, _load_lattice
        if LATTICE_FILE is not None:
            lattice = _load_lattice(LATTICE_FILE)
            for i, elem in enumerate(lattice):
                if getattr(elem, "FamName", None) in ("BPM", "FBPM"):
                    uuid = getattr(elem, "UUID", None)
                    if uuid:
                        bpm_index_map[uuid] = i
            logger.info("BPM registration: resolved %d BPM orbit indices from lattice",
                        len(bpm_index_map))
            if bpm_index_map:
                sample = list(bpm_index_map.items())[:3]
                logger.info("BPM registration: sample uuid→index: %s", sample)
    except Exception as e:
        logger.warning("BPM registration: could not build orbit index map: %s", e)

    for bpm in get_bpms():
        bpm_name = bpm.get("name")
        bpm_uuid = bpm.get("uuid")
        bpm_spos = float(bpm.get("s_pos", 0.0))
        if not bpm_name:
            continue

        # Find orbit index by UUID match
        orbit_index = bpm_index_map.get(bpm_uuid, -1)
        if orbit_index == -1:
            logger.warning("BPM %s: uuid=%s not found in lattice BPM map", bpm_name, bpm_uuid)

        try:
            domain, family, member = _split_domain_family_member(bpm_name)
            server_name   = domain
            instance_name = family
            server_str    = f"{server_name}/{instance_name}"
            unique_servers.add((server_name, instance_name))

            db_dev        = DbDevInfo()
            db_dev._class = "BPMDevice"
            db_dev.server = server_str
            db_dev.name   = bpm_name
            db.add_device(db_dev)
            db.put_device_property(bpm_name, {
                "lattice_id":  [bpm_uuid],
                "s_pos":       [str(bpm_spos)],
                "orbit_index": [str(orbit_index)],
            })
            logger.info("📡 Registered BPMDevice %s uuid=%s s_pos=%.3f orbit_index=%d (server=%s)",
                        bpm_name, bpm_uuid, bpm_spos, orbit_index, server_str)
        except Exception as e:
            logger.error("❌ Failed to register BPMDevice %s: %s", bpm_name, e)

    logger.info("✔ Unique (server_name, instance_name) pairs: %s", unique_servers)
    logger.info("✔ Device registration DONE. We have %d servers to start.", len(unique_servers))

    # ------------------------------------------------------------
    # 5) Make sure dserver/<server_name>/<instance_name> exists
    # ------------------------------------------------------------
    _register_dservers(db, unique_servers)

    return sorted(unique_servers)


def get_all_device_classes():
    """Return all device classes used by the servers."""
    return [
        MultipoleDevice,
        HorizontalSteererDevice,
        VerticalSteererDevice,
        SkewQuadDevice,
        CavityDevice,
        # PowerConverterDevice,
        RingSimulatorDevice,
        BPMDevice,
    ]