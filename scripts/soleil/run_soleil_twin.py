#!/usr/bin/env python3
"""
run_soleil_twin.py
==================

Launch script for the SOLEIL digital twin TANGO server.

Usage
-----
    python scripts/soleil/run_soleil_twin.py [--lattice PATH] [--port PORT]

All SOLEIL-specific configuration is set here before handing off to the
generic server_manager. The server_manager itself has no hardcoded paths.

Directory layout
----------------
    scripts/
        soleil/
            run_soleil_twin.py      ← this file
    src/
        dt4acc/
            custom_tango/
                ioc/
                    server_manager.py

Environment variables (all optional, CLI args take precedence)
--------------------------------------------------------------
    DT4ACC_LATTICE_FILE   Path to the SOLEIL AT lattice .m file
    DT4ACC_TANGO_HOST     Tango database host:port  (default: localhost:10000)
    DT4ACC_HEARTBEAT_DEV  Magnet device used for heartbeat writes
"""

import argparse
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve paths — script lives at scripts/soleil/, src is two levels up
# ---------------------------------------------------------------------------

SCRIPTS_DIR = Path(__file__).resolve().parent          # scripts/soleil/
ROOT_DIR    = SCRIPTS_DIR.parent.parent                 # project root
SRC_DIR     = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# ---------------------------------------------------------------------------
# SOLEIL defaults
# ---------------------------------------------------------------------------

DEFAULT_LATTICE_FILE = (
    Path.home()
    / "Documents"
    / "dt4acc_soleil_twin_data"
    / "SOLEIL_II_V3635_STAB_SYM1_SB3_MULT7_4SX60_V001_Nomenclature.m"
)

DEFAULT_HEARTBEAT_DEVICE = "AN01-AR/EM-QP/QF01.01"
DEFAULT_HEARTBEAT_ATTR   = "magnetic_strength"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Launch the SOLEIL digital twin TANGO server"
    )
    parser.add_argument(
        "--lattice",
        type=Path,
        default=Path(os.environ.get("DT4ACC_LATTICE_FILE", DEFAULT_LATTICE_FILE)),
        help="Path to the SOLEIL AT lattice .m file "
             f"(default: {DEFAULT_LATTICE_FILE})",
    )
    parser.add_argument(
        "--tango-host",
        default=os.environ.get("DT4ACC_TANGO_HOST", "localhost:10000"),
        help="Tango database host:port (default: localhost:10000)",
    )
    parser.add_argument(
        "--heartbeat-device",
        default=os.environ.get("DT4ACC_HEARTBEAT_DEV", DEFAULT_HEARTBEAT_DEVICE),
        help=f"Magnet device for heartbeat writes (default: {DEFAULT_HEARTBEAT_DEVICE})",
    )
    parser.add_argument(
        "--heartbeat-attr",
        default=DEFAULT_HEARTBEAT_ATTR,
        help=f"Attribute to write for heartbeat (default: {DEFAULT_HEARTBEAT_ATTR})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=50200,
        help="TCP port for the MexecService manager (default: 50200)",
    )
    parser.add_argument(
        "--view",
    type=str,
    default=os.environ.get("DT4ACC_VIEW", "design"),
    help="Design or Device view"
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# SOLEIL-specific load_managers
# ---------------------------------------------------------------------------

def _soleil_load_managers():
    """Load the SOLEIL liaison manager and translator service."""
    from dt4acc.custom_facility.bessyii.liasion_translator_setup import load_managers
    return load_managers()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    # Validate lattice file
    if not args.lattice.exists():
        print(f"ERROR: Lattice file not found: {args.lattice}", file=sys.stderr)
        sys.exit(1)

    print(f"SOLEIL twin server starting")
    print(f"  Lattice : {args.lattice}")
    print(f"  TANGO   : {args.tango_host}")
    print(f"  Heartbeat: {args.heartbeat_device}.{args.heartbeat_attr}")
    print(f"  MexecPort: {args.port}")

    # Set TANGO_HOST before importing anything that touches Tango
    os.environ["TANGO_HOST"] = args.tango_host

    # Import and configure server_manager
    from dt4acc.custom_tango.ioc import server_manager

    server_manager.LATTICE_FILE             = args.lattice
    server_manager.LOAD_MANAGERS_FN         = _soleil_load_managers
    server_manager.HEARTBEAT_DEVICE         = args.heartbeat_device
    server_manager.HEARTBEAT_ATTR           = args.heartbeat_attr
    server_manager._MANAGER_PORT            = args.port
    server_manager.EXPECTED_VIEW            = args.view

    # Launch
    server_manager.main()


if __name__ == "__main__":
    main()
