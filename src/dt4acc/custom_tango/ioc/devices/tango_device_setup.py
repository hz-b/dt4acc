# tango_device_setup.py

import os

from tango import Database, DbDevInfo, DevFailed
from dt4acc.core.utils.logger import get_logger
from dt4acc.config.data.querries import (
    get_unique_power_converters,
    get_devices_type_specified,
)

from dt4acc.custom_tango.ioc.devices.multipole_device import MultipoleDevice
from dt4acc.custom_tango.ioc.devices.steerer_device import HorizontalSteererDevice, VerticalSteererDevice
from dt4acc.custom_tango.ioc.devices.skew_quad_device import SkewQuadDevice
from dt4acc.custom_tango.ioc.devices.cavity_device import CavityDevice
from dt4acc.custom_tango.ioc.devices.bpm_device import BpmDevice
from dt4acc.custom_tango.ioc.devices.virtual_devices import RingSimulatorDevice, RING_SIM_DEV
from dt4acc.custom_tango.ioc.devices.power_converter_device import PowerConverterDevice

logger = get_logger()

DEFAULT_DB_TIMEOUT_MS = 60000
_MAGNET_TYPES = {
    "Quadrupole",
    "Sextupole",
    "Octupole",
    "Multipole",
    "Bend",
    "Steerer",
    "SkewQuadrupole",
    "RFCavity",
}

# Map JSON "type" field → Tango device class name
_TYPE_TO_CLASS = {
    "Quadrupole":    "MultipoleDevice",
    "Sextupole":     "MultipoleDevice",
    "Octupole":      "MultipoleDevice",
    "Multipole":     "MultipoleDevice",
    "Steerer":       None,   # determined by is_horizontal/is_vertical below
    "SkewQuadrupole": "SkewQuadDevice",
    "RFCavity":      "CavityDevice",
    "BPM":           "BpmDevice",
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


def _configure_db_timeout(db: Database, timeout_ms: int | None = None) -> int:
    configured = timeout_ms
    if configured is None:
        try:
            configured = int(os.environ.get("DT4ACC_TANGO_DB_TIMEOUT_MS", DEFAULT_DB_TIMEOUT_MS))
        except ValueError:
            configured = DEFAULT_DB_TIMEOUT_MS
    db.set_timeout_millis(configured)
    return configured


def _entry_uuid(entry: dict) -> str:
    uuid = entry.get("uuid", "")
    if uuid:
        return uuid
    uuids = entry.get("uuids")
    if uuids:
        return uuids[0]
    return ""


def _class_for_entry(entry: dict) -> str:
    device_type = entry.get("type", "")
    if device_type == "Steerer":
        return _steerer_class(entry.get("name", ""), subtype=entry.get("subtype", ""))
    return _TYPE_TO_CLASS.get(device_type, "MultipoleDevice")


def _add_device(
    db: Database,
    *,
    name: str,
    class_name: str,
    server_str: str,
    element_uuid: str = "",
) -> bool:
    db_dev = DbDevInfo()
    db_dev._class = class_name
    db_dev.server = server_str
    db_dev.name = name
    db.add_device(db_dev)
    if element_uuid:
        db.put_device_property(name, {"element_uuid": [element_uuid]})
    return True


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
            logger.debug(f"🧱 Registered DServer device {dserver_name} (server={server_str})")
        except DevFailed as e:
            # Ignore 'already exists' style errors, log others
            msg = str(e)
            if "DB_DuplicateKey" in msg or "already" in msg or "Duplicate" in msg:
                logger.debug(f"DServer {dserver_name} already exists, skipping.")
            else:
                logger.error(f"❌ Failed to register DServer {dserver_name}: {e}")


def register_all_devices(
    *,
    include_power_converters: bool | None = None,
    db_timeout_ms: int | None = None,
):
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
    configured_timeout = _configure_db_timeout(db, db_timeout_ms)
    unique_servers: set[tuple[str, str]] = set()

    if include_power_converters is None:
        include_power_converters = os.environ.get(
            "DT4ACC_REGISTER_POWER_CONVERTERS",
            "1",
        ).lower() not in {"0", "false", "no", "off"}

    logger.info(
        "📝 Registering Tango devices into DB (timeout=%d ms, power_converters=%s)...",
        configured_timeout,
        include_power_converters,
    )

    # ------------------------------------------------------------
    # 1) Physical devices — registered by Tango name (TRL).
    #    UUID/uuids is stored as DB property for AT element lookup.
    # ------------------------------------------------------------
    physical_entries = get_devices_type_specified(_MAGNET_TYPES)
    registered_devices: set[str] = set()
    for entry in physical_entries:
        dev_name = entry.get("name", "")
        if not dev_name or dev_name in registered_devices:
            continue
        try:
            domain, family, _ = _split_domain_family_member(dev_name)
            server_name = domain
            instance_name = family
            server_str = f"{server_name}/{instance_name}"
            unique_servers.add((server_name, instance_name))

            class_name = _class_for_entry(entry)
            dev_uuid = _entry_uuid(entry)
            _add_device(
                db,
                name=dev_name,
                class_name=class_name,
                server_str=server_str,
                element_uuid=dev_uuid,
            )
            registered_devices.add(dev_name)
            logger.debug(
                "Registered %s %s uuid=%s (server=%s)",
                class_name,
                dev_name,
                dev_uuid,
                server_str,
            )
        except Exception as e:
            logger.error("Failed to register device %s: %s", dev_name, e)

    # ------------------------------------------------------------
    # 2) Power converters — registered as PowerConverterDevice (device view)
    #    Each PC TRL becomes a Tango device so current can be written to it.
    #    Skipped if the PC name is not a valid 3-part TRL (e.g. cavity PCs).
    # ------------------------------------------------------------
    if include_power_converters:
        registered_pcs = set()
        for pc_name in get_unique_power_converters():
            if pc_name in registered_pcs:
                continue
            registered_pcs.add(pc_name)
            try:
                domain, family, _ = _split_domain_family_member(pc_name)
                server_name = domain
                instance_name = family
                server_str = f"{server_name}/{instance_name}"
                unique_servers.add((server_name, instance_name))

                _add_device(
                    db,
                    name=pc_name,
                    class_name="PowerConverterDevice",
                    server_str=server_str,
                )
                logger.debug("Registered PC %s (server=%s)", pc_name, server_str)
            except Exception as e:
                logger.warning("Skipping PC %s (not a valid TRL?): %s", pc_name, e)

    # ------------------------------------------------------------
    # 3) BPMs — registered from their real SOLEIL Tango names in the JSON.
    # ------------------------------------------------------------
    for bpm in get_devices_type_specified(["BPM"]):
        dev_name = bpm.get("name", "")
        dev_uuid = bpm.get("uuid", "") or (bpm.get("uuids", [""])[0] if bpm.get("uuids") else "")
        try:
            domain, family, _ = _split_domain_family_member(dev_name)
            server_name = domain
            instance_name = family
            server_str = f"{server_name}/{instance_name}"
            unique_servers.add((server_name, instance_name))

            _add_device(
                db,
                name=dev_name,
                class_name="BpmDevice",
                server_str=server_str,
                element_uuid=dev_uuid,
            )
            if not dev_uuid:
                logger.warning("BPM %s has no uuid/uuids in accelerator setup", dev_name)

            logger.debug("Registered BpmDevice %s uuid=%s (server=%s)",
                         dev_name, dev_uuid, server_str)
        except Exception as e:
            logger.error("Failed to register BPM %s: %s", dev_name, e)

    # ------------------------------------------------------------
    # 4) Single RingSimulatorDevice — replaces all PHYSICS/SOLEIL/* devices
    # ------------------------------------------------------------
    try:
        domain, family, _ = _split_domain_family_member(RING_SIM_DEV)
        server_name   = domain
        instance_name = family
        server_str    = f"{server_name}/{instance_name}"
        unique_servers.add((server_name, instance_name))

        _add_device(
            db,
            name=RING_SIM_DEV,
            class_name="RingSimulatorDevice",
            server_str=server_str,
        )
        logger.info("Registered RingSimulatorDevice %s (server=%s)", RING_SIM_DEV, server_str)
    except Exception as e:
        logger.error("Failed to register RingSimulatorDevice: %s", e)

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
        BpmDevice,
        PowerConverterDevice,
        RingSimulatorDevice,
    ]
