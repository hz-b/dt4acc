# tango_device_setup.py

from tango import Database, DbDevInfo, DevFailed

from dataclasses import dataclass, field
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
from dt4acc_lib.model.utils.tango_resource_locator import TangoResourceLocator

logger = get_logger()


@dataclass
class DeviceCheckReport:
    present: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def check_devices() -> DeviceCheckReport:
    """
    Read-only validation entry point.

    Patch 2:
    - no registration
    - no behaviour change to existing registration path
    - foundation for check vs ensure mode
    """
    db = Database()
    report = DeviceCheckReport()

    # TODO: implement device inventory checks in patch 3
    return report


# Map JSON "type" field → Tango device class name
_TYPE_TO_CLASS = {
    "Quadrupole":              "MultipoleDevice",
    "Sextupole":               "MultipoleDevice",
    "Octupole":                "MultipoleDevice",
    "Multipole":               "MultipoleDevice",
    "Steerer":                 None,
    "QuadrupoleCorrector":     "SkewQuadDevice",
    "SkewQuadrupoleCorrector": "SkewQuadDevice",
    "RFCavity":                "CavityDevice",
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



def _register_magnets(db: Database, unique_servers: set[tuple[str, str]]):
    """Register magnet devices and properties."""
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
                trl = TangoResourceLocator.from_trl(magnet_name)
                domain, family = trl.domain, trl.family
                server_name   = domain
                instance_name = family
                server_str    = f"{server_name}/{instance_name}"
                unique_servers.add((server_name, instance_name))

                # Pick the correct Tango class for this physical type
                if magnet_type == "Steerer":
                    class_name = _steerer_class(magnet_name, subtype=magnet_subtype)
                else:
                    class_name = _TYPE_TO_CLASS.get(magnet_type, "MultipoleDevice")

                _SUBTYPE_TO_LATTICE_PROP = {
                    "Quad":     "B2",
                    "Sext":     "B3",
                    "SkewSext": "B3",
                    "Oct":      "B4",
                }
                # For corrector types, use the magnet type directly
                if magnet_type == "QuadrupoleCorrector":
                    lattice_prop = "B2"
                elif magnet_type == "SkewQuadrupoleCorrector":
                    lattice_prop = "A2"
                else:
                    lattice_prop = _SUBTYPE_TO_LATTICE_PROP.get(magnet_subtype, "main_strength")

                db_dev        = DbDevInfo()
                db_dev._class = class_name
                db_dev.server = server_str
                db_dev.name   = magnet_name
                try:
                    db.add_device(db_dev)
                except DevFailed as e:
                    msg = str(e)
                    if "DB_DuplicateKey" not in msg and "already" not in msg:
                        raise

                # Always set properties — even if device already existed
                props = {}
                if magnet_uuid:
                    props["element_uuid"] = [magnet_uuid]
                if pc_name:
                    props["power_supply"] = [pc_name]
                props["lattice_property"] = [lattice_prop]
                db.put_device_property(magnet_name, props)

                logger.info("🧲 Registered magnet %s uuid=%s lattice_property=%s (server=%s)",
                            magnet_name, magnet_uuid, lattice_prop, server_str)
            except Exception as e:
                logger.error("❌ Failed to register magnet %s: %s", magnet_name, e)

def _register_power_converters(db: Database, unique_servers: set[tuple[str, str]]):
    """Register power converter devices and properties."""
    # ------------------------------------------------------------
    # 2) Power converters — device view only.
    #    In design view the magnet device is the control source — no PC devices.
    # ------------------------------------------------------------
    from dt4acc.custom_tango.ioc.server_manager import EXPECTED_VIEW
    if EXPECTED_VIEW == "device":
        registered_pcs = set()
        for pc_name in get_unique_power_converters():
            if pc_name in registered_pcs:
                continue
            registered_pcs.add(pc_name)
            try:
                trl = TangoResourceLocator.from_trl(pc_name)
                domain, family = trl.domain, trl.family
                server_name   = domain
                instance_name = family
                server_str    = f"{server_name}/{instance_name}"
                unique_servers.add((server_name, instance_name))

                db_dev        = DbDevInfo()
                db_dev._class = "PowerConverterDevice"
                db_dev.server = server_str
                db_dev.name   = pc_name
                try:
                    db.add_device(db_dev)
                except DevFailed as e:
                    msg = str(e)
                    if "DB_DuplicateKey" not in msg and "already" not in msg:
                        raise

                # Always set properties
                pc_magnet_names = [m["name"] for m in get_magnets_per_power_converters(pc_name)]
                if pc_magnet_names:
                    db.put_device_property(pc_name, {"magnets": pc_magnet_names})

                logger.info("⚡ Registered PC %s (server=%s)", pc_name, server_str)
            except Exception as e:
                logger.warning("Skipping PC %s (not a valid TRL?): %s", pc_name, e)

def _register_cavities(db: Database, unique_servers: set[tuple[str, str]]):
    """Register cavity devices."""
    # 2) Cavities — registered as typed devices
    # ------------------------------------------------------------
    for pc_name in get_unique_power_converters_type_specified(["RFCavity"]):
        for m in get_magnets_per_power_converters(pc_name):
            dev_name  = m["name"]
            dev_uuid  = m.get("uuid", "")
            dev_type  = m.get("type", "")
            class_name = _TYPE_TO_CLASS.get(dev_type, "MultipoleDevice")
            try:
                trl = TangoResourceLocator.from_trl(dev_name)
                domain, family = trl.domain, trl.family
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

def _register_ring_simulator(db: Database, unique_servers: set[tuple[str, str]]):
    """Register the RingSimulatorDevice."""
    # 3) Single RingSimulatorDevice — replaces all PHYSICS/SOLEIL/* devices
    # ------------------------------------------------------------
    try:
        trl = TangoResourceLocator.from_trl(RING_SIM_DEV)
        domain, family = trl.domain, trl.family
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

def _register_bpms(db: Database, unique_servers: set[tuple[str, str]]):
    """Register BPM devices and properties."""
    # 4) BPM devices — one per Monitor element, read-only
    # ------------------------------------------------------------
    # Build s_pos → AT element index map by loading the lattice directly.
    # AT element s positions are computed via at.get_s_pos() — not stored
    # on individual elements.
    bpm_index_map: dict = {}  # uuid → AT element index
    try:
        import at as _at
        from dt4acc.custom_tango.ioc.handle_lattice import lattice_loader

        lattice = lattice_loader.load()
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
            trl = TangoResourceLocator.from_trl(bpm_name)
            domain, family, member = trl.domain, trl.family, trl.member
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

    _register_magnets(db, unique_servers)
    _register_power_converters(db, unique_servers)
    _register_cavities(db, unique_servers)
    _register_ring_simulator(db, unique_servers)
    _register_bpms(db, unique_servers)

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
        PowerConverterDevice,
        RingSimulatorDevice,
        BPMDevice,
    ]
