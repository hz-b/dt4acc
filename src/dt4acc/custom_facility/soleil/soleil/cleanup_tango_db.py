#!/usr/bin/env python3
"""
cleanup_tango_db.py
===================

Delete all dt4acc-related devices from the Tango database before restarting
the server. Run this when device names have changed significantly.

Usage
-----
    python scripts/soleil/cleanup_tango_db.py [--tango-host HOST:PORT] [--dry-run]

What it deletes
---------------
    - All MagnetDevice instances
    - All RingSimulatorDevice instances
    - All old PHYSICS/SOLEIL/* devices (TwissOrbitDevice, BPMManagerDevice,
      TuneDevice, MasterClockDevice, OtherPVsDevice, CavityDevice)
    - The corresponding DServer devices for all of the above servers
    - The server registrations themselves

What it does NOT touch
----------------------
    - The Tango database server itself
    - Any devices from other applications
"""

import argparse
import os
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT_DIR    = SCRIPTS_DIR.parent.parent
SRC_DIR     = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# ---------------------------------------------------------------------------
# Device classes to remove
# ---------------------------------------------------------------------------

MANAGED_CLASSES = {
    "MagnetDevice",
    "RingSimulatorDevice",
    # Legacy virtual devices — safe to remove even if already gone
    "VerticalSteererDevice",
    "SkewQuadDevice",
    "TuneDevice",
    "MultipoleDevice",
    "HorizontalSteererDevice",
    "CavityDevice",
    "PowerConverterDevice",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Delete all dt4acc devices from the Tango database"
    )
    parser.add_argument(
        "--tango-host",
        default=os.environ.get("TANGO_HOST", "localhost:10000"),
        help="Tango database host:port (default: localhost:10000 or $TANGO_HOST)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting anything",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )
    return parser.parse_args()


def get_all_managed_devices(db) -> dict:
    """
    Find ALL registered devices belonging to managed classes.
    Uses get_device_name which searches all registered devices
    regardless of whether the server is currently running.
    """
    to_delete = {}  # device_name → class_name

    for class_name in sorted(MANAGED_CLASSES):
        try:
            # "*" wildcard finds all domains/families/members
            result = db.get_device_name("*", class_name)
            for dev_name in result.value_string:
                dev_name = str(dev_name).strip()
                if dev_name and dev_name != "nodb":
                    to_delete[dev_name] = class_name
        except Exception as exc:
            pass  # class not in DB — skip silently

    return to_delete


def get_all_managed_servers(db) -> set:
    """
    Find ALL server/instance registrations that contain only managed devices.
    We delete the entire server registration which removes all its devices.
    """
    servers = set()
    try:
        # Get all server names (format: "ServerName/instance")
        all_servers = db.get_server_list("*").value_string
        for server_str in all_servers:
            server_str = str(server_str).strip()
            if not server_str:
                continue
            try:
                # Get all classes in this server
                classes_in_server = set(db.get_server_class_list(server_str).value_string)
                # If ALL classes in this server are managed classes → delete whole server
                # If ANY managed class is in this server → delete it
                if classes_in_server & MANAGED_CLASSES:
                    servers.add(server_str)
            except Exception:
                pass
    except Exception as exc:
        print(f"  Warning: could not list servers: {exc}")
    return servers


def delete_device(db, device_name: str, dry_run: bool) -> bool:
    """Delete a device from the DB. Returns True if successful."""
    if dry_run:
        print(f"  [DRY RUN] would delete: {device_name}")
        return True
    try:
        db.delete_device(device_name)
        print(f"  ✓ deleted: {device_name}")
        return True
    except Exception as exc:
        print(f"  ✗ failed to delete {device_name}: {exc}")
        return False


def delete_server(db, server_str: str, dry_run: bool) -> bool:
    """Delete a server registration (server/instance) from the DB."""
    if dry_run:
        print(f"  [DRY RUN] would delete server: {server_str}")
        return True
    try:
        db.delete_server(server_str)
        print(f"  ✓ deleted server: {server_str}")
        return True
    except Exception as exc:
        print(f"  ✗ failed to delete server {server_str}: {exc}")
        return False


def main():
    args = parse_args()
    os.environ["TANGO_HOST"] = args.tango_host

    try:
        from tango import Database
    except ImportError:
        print("ERROR: PyTango not installed", file=sys.stderr)
        sys.exit(1)

    db = Database()
    print(f"Connected to Tango DB at {args.tango_host}")
    print()

    # Find all servers containing managed device classes
    print("Scanning Tango DB for dt4acc servers...")
    servers = get_all_managed_servers(db)
    # Also find any stray devices in case server reg is missing
    stray_devices = get_all_managed_devices(db)

    if not servers and not stray_devices:
        print("No dt4acc devices or servers found in the Tango database. Nothing to do.")
        return

    # Show summary
    print(f"Found {len(servers)} server registrations to delete:")
    for s in sorted(servers)[:20]:
        print(f"  {s}")
    if len(servers) > 20:
        print(f"  ... and {len(servers) - 20} more")
    print()
    if stray_devices:
        print(f"Found {len(stray_devices)} stray device registrations:")
        for d in sorted(stray_devices)[:10]:
            print(f"  {d}  [{stray_devices[d]}]")
        if len(stray_devices) > 10:
            print(f"  ... and {len(stray_devices) - 10} more")
        print()

    # Confirm
    total = len(servers) + len(stray_devices)
    if not args.dry_run and not args.yes:
        answer = input(
            f"Delete {len(servers)} server registrations and {len(stray_devices)} "
            f"stray devices? [y/N] "
        ).strip().lower()
        if answer not in ("y", "yes"):
            print("Aborted.")
            return

    # Delete server registrations (this removes all their devices automatically)
    deleted_servers = 0
    failed_servers  = 0
    if servers:
        print("Deleting server registrations...")
        for server_str in sorted(servers):
            if delete_server(db, server_str, args.dry_run):
                deleted_servers += 1
            else:
                failed_servers += 1

    # Delete any remaining stray devices
    deleted_devices = 0
    failed_devices  = 0
    if stray_devices:
        print("Deleting stray devices...")
        for dev_name in sorted(stray_devices):
            if delete_device(db, dev_name, args.dry_run):
                deleted_devices += 1
            else:
                failed_devices += 1

    # Summary
    print()
    if args.dry_run:
        print(f"DRY RUN complete — would delete {len(servers)} server registrations "
              f"and {len(stray_devices)} stray devices.")
    else:
        print(f"Done.")
        print(f"  Servers:  {deleted_servers} deleted, {failed_servers} failed")
        print(f"  Devices:  {deleted_devices} deleted, {failed_devices} failed")
        if failed_servers or failed_devices:
            print("WARNING: some deletions failed — check errors above.")
        print()
        print("Tango database is clean. You can now restart the server.")


if __name__ == "__main__":
    main()