# tango_device_setup.py
from typing import Any

from tango import Database, DbDevInfo, DevFailed
from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_epics.data.querries import (
    get_unique_power_converters,
    get_magnets_per_power_converters,
)
from dt4acc.custom_epics.data.constants import cavity_names

from dt4acc.custom_tango.ioc.devices.magnet_device import MagnetDevice
from dt4acc.custom_tango.ioc.devices.power_converter_device import PowerConverterDevice
from dt4acc.custom_tango.ioc.devices.virtual_devices import CavityDevice, BPMManagerDevice, TuneDevice, TwissOrbitDevice, OtherPVsDevice, MasterClockDevice

logger = get_logger()


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
    logger.info(f"🧱 Registering DServer devices ({len(servers)})")
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


def register_all_devices(elements: list[dict[str, Any]] | None = None):
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

    logger.info("📝 Registering ALL Soleil devices into Tango DB...")

    # ------------------------------------------------------------
    # 1) Magnets & power converters
    # ------------------------------------------------------------
    for pc_name in get_unique_power_converters(elements):
        magnets = get_magnets_per_power_converters(pc_name)

        # Power converter name should already be Soleil-like, e.g. AN10-AR/EM/SCF.11-pc
        pc_device_name = pc_name

        # register PC first
        try:
            domain, family, _ = _split_domain_family_member(pc_device_name)
            server_name = domain
            instance_name = family
            server_str = f"{server_name}/{instance_name}"
            unique_servers.add((server_name, instance_name))

            db_dev = DbDevInfo()
            db_dev._class = "PowerConverterDevice"
            db_dev.server = server_str
            db_dev.name = pc_device_name

            db.add_device(db_dev)
            logger.debug(f"⚡ Registered PC device {db_dev.name} (class=PowerConverterDevice, server={server_str})")
        except Exception as e:
            logger.error(f"❌ Failed to register power converter {pc_device_name}: {e}")

        # register magnets driven by this PC
        for m in magnets:
            magnet_name = m["name"]  # AN10-AR/EM/SCF.11
            try:
                domain, family, _ = _split_domain_family_member(magnet_name)
                server_name = domain
                instance_name = family
                server_str = f"{server_name}/{instance_name}"
                unique_servers.add((server_name, instance_name))

                db_dev = DbDevInfo()
                db_dev._class = "MagnetDevice"
                db_dev.server = server_str
                db_dev.name = magnet_name

                db.add_device(db_dev)
                logger.debug(f"🧲 Registered magnet device {db_dev.name} (class=MagnetDevice, server={server_str})")
            except Exception as e:
                logger.error(f"❌ Failed to register magnet {magnet_name}: {e}")

    # ------------------------------------------------------------
    # 2) Virtual / physics devices
    # ------------------------------------------------------------

    # Twiss + orbit + BPM combined device
    twiss_name = "PHYSICS/SOLEIL/TWISS_ORBIT"
    try:
        domain, family, _ = _split_domain_family_member(twiss_name)
        server_name = domain
        instance_name = family
        server_str = f"{server_name}/{instance_name}"
        unique_servers.add((server_name, instance_name))

        db_dev = DbDevInfo()
        db_dev._class = "TwissOrbitDevice"
        db_dev.server = server_str
        db_dev.name = twiss_name
        db.add_device(db_dev)
        logger.debug(f"📈 Registered virtual device {twiss_name} (class=TwissOrbitDevice, server={server_str})")
    except Exception as e:
        logger.error(f"❌ Failed to register TwissOrbitDevice: {e}")

    # Master clock
    mc_name = "PHYSICS/SOLEIL/MASTER_CLOCK"
    try:
        domain, family, _ = _split_domain_family_member(mc_name)
        server_name = domain
        instance_name = family
        server_str = f"{server_name}/{instance_name}"
        unique_servers.add((server_name, instance_name))

        db_dev = DbDevInfo()
        db_dev._class = "MasterClockDevice"
        db_dev.server = server_str
        db_dev.name = mc_name
        db.add_device(db_dev)
        logger.debug(f"⏱ Registered virtual device {mc_name} (class=MasterClockDevice, server={server_str})")
    except Exception as e:
        logger.error(f"❌ Failed to register MasterClockDevice: {e}")

    # OtherPVs
    other_name = "PHYSICS/SOLEIL/OTHERS"
    try:
        domain, family, _ = _split_domain_family_member(other_name)
        server_name = domain
        instance_name = family
        server_str = f"{server_name}/{instance_name}"
        unique_servers.add((server_name, instance_name))

        db_dev = DbDevInfo()
        db_dev._class = "OtherPVsDevice"
        db_dev.server = server_str
        db_dev.name = other_name
        db.add_device(db_dev)
        logger.debug(f"📦 Registered virtual device {other_name} (class=OtherPVsDevice, server={server_str})")
    except Exception as e:
        logger.error(f"❌ Failed to register OtherPVsDevice: {e}")

    # Tune device
    tune_name = "PHYSICS/SOLEIL/TUNE"
    try:
        domain, family, _ = _split_domain_family_member(tune_name)
        server_name = domain
        instance_name = family
        server_str = f"{server_name}/{instance_name}"
        unique_servers.add((server_name, instance_name))

        db_dev = DbDevInfo()
        db_dev._class = "TuneDevice"
        db_dev.server = server_str
        db_dev.name = tune_name
        db.add_device(db_dev)
        logger.debug(f"🎯 Registered virtual device {tune_name} (class=TuneDevice, server={server_str})")
    except Exception as e:
        logger.error(f"❌ Failed to register TuneDevice: {e}")

    # BPM Manager device
    bpm_manager_name = "PHYSICS/SOLEIL/BPM"
    try:
        domain, family, _ = _split_domain_family_member(bpm_manager_name)
        server_name = domain
        instance_name = family
        server_str = f"{server_name}/{instance_name}"
        unique_servers.add((server_name, instance_name))

        db_dev = DbDevInfo()
        db_dev._class = "BPMManagerDevice"
        db_dev.server = server_str
        db_dev.name = bpm_manager_name
        db.add_device(db_dev)
        logger.debug(f" Registered virtual device {bpm_manager_name} (class=BPMManagerDevice, server={server_str})")
    except Exception as e:
        logger.error(f" Failed to register BPMManagerDevice: {e}")

    # Cavities: use the Soleil element name from input data directly.
    cavities = [elem["name"] for elem in elements if elem["type"] == "RFCavity"]
    if len(cavities) == 0:
        cavities = cavity_names

    for cav in cavities:
        cav_name = cav
        try:
            domain, family, _ = _split_domain_family_member(cav_name)
            server_name = domain
            instance_name = family
            server_str = f"{server_name}/{instance_name}"
            unique_servers.add((server_name, instance_name))

            db_dev = DbDevInfo()
            db_dev._class = "CavityDevice"
            db_dev.server = server_str
            db_dev.name = cav_name
            db.add_device(db_dev)
            logger.debug(f"📡 Registered virtual device {cav_name} (class=CavityDevice, server={server_str})")
        except Exception as e:
            logger.error(f"❌ Failed to register CavityDevice {cav_name}: {e}")

    logger.info(f"✔ Unique (server_name, instance_name) pairs: {unique_servers}")
    logger.info(f"✔ Device registration DONE. We have {len(unique_servers)} servers to start.")

    # ------------------------------------------------------------
    # 3) Make sure dserver/<server_name>/<instance_name> exists
    # ------------------------------------------------------------
    _register_dservers(db, unique_servers)

    return sorted(unique_servers)


def get_all_device_classes():
    """Return all device classes used by the servers."""
    return [
        MagnetDevice,
        PowerConverterDevice,
        TwissOrbitDevice,
        BPMManagerDevice,
        CavityDevice,
        MasterClockDevice,
        OtherPVsDevice,
        TuneDevice,
    ]
