# tango_device_setup.py

from tango import Database, DbDevInfo, DevFailed
from dt4acc.core.utils.logger import get_logger
from dt4acc.config.data.querries import (
    get_unique_power_converters,
    get_magnets_per_power_converters,
    get_unique_power_converters_type_specified,
)

from .magnet_device import MagnetDevice
from .virtual_devices import RingSimulatorDevice, RING_SIM_DEV

logger = get_logger()


def _split_domain_family_member(device_name: str):
    """AN10-AR/EM/SCF.11 -> ('AN10-AR', 'EM', 'SCF.11')"""
    parts = device_name.split("/")
    if len(parts) != 3:
        raise ValueError(f"Invalid device name: {device_name}")
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
    Register ALL devices in the Tango DB.

    - Device *names* are the names (AN10-AR/EM/SCF.11, ...).
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
    # 1) Magnets — registered by Tango name, UUID stored as DB property
    #    so init_device can look up the unique AT element.
    #    Power converters are NOT registered as Tango devices.
    # ------------------------------------------------------------
    for pc_name in get_unique_power_converters():
        magnets = get_magnets_per_power_converters(pc_name)
        for m in magnets:
            magnet_name = m["name"]       # e.g. AN10-AR/EM/SCF.11
            magnet_uuid = m.get("uuid", "")
            try:
                domain, family, _ = _split_domain_family_member(magnet_name)
                server_name   = domain
                instance_name = family
                server_str    = f"{server_name}/{instance_name}"
                unique_servers.add((server_name, instance_name))

                db_dev        = DbDevInfo()
                db_dev._class = "MagnetDevice"
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
    # 2) Cavities — registered as MagnetDevice (same as magnets)
    # ------------------------------------------------------------
    for pc_name in get_unique_power_converters_type_specified(["RFCavity"]):
        for m in get_magnets_per_power_converters(pc_name):
            cav_name = m["name"]       # e.g. AN02-SD/RF-CAV/CAV
            cav_uuid = m.get("uuid", "")
            try:
                domain, family, _ = _split_domain_family_member(cav_name)
                server_name   = domain
                instance_name = family
                server_str    = f"{server_name}/{instance_name}"
                unique_servers.add((server_name, instance_name))

                db_dev        = DbDevInfo()
                db_dev._class = "MagnetDevice"
                db_dev.server = server_str
                db_dev.name   = cav_name
                db.add_device(db_dev)

                if cav_uuid:
                    try:
                        db.put_device_property(
                            cav_name, {"element_uuid": [cav_uuid]}
                        )
                    except Exception as e:
                        logger.warning("Could not set uuid for cavity %s: %s", cav_name, e)

                logger.info("📡 Registered cavity %s uuid=%s (server=%s)",
                            cav_name, cav_uuid, server_str)
            except Exception as e:
                logger.error("❌ Failed to register cavity %s: %s", cav_name, e)

    # ------------------------------------------------------------
    # 3) Single RingSimulatorDevice
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

    logger.info("✔ Unique (server_name, instance_name) pairs: %s", unique_servers)
    logger.info("✔ Device registration DONE. We have %d servers to start.", len(unique_servers))

    # ------------------------------------------------------------
    # 4) Make sure dserver/<server_name>/<instance_name> exists
    # ------------------------------------------------------------
    _register_dservers(db, unique_servers)

    return sorted(unique_servers)


def get_all_device_classes():
    """Return all device classes used by the servers."""
    return [MagnetDevice, RingSimulatorDevice]