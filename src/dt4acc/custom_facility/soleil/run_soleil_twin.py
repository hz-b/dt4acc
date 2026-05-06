#!/usr/bin/env python3
"""
run_maxiv_twin.py
==================

Launch script for the SOLEIL digital twin TANGO server.

Usage
-----
    python scripts/soleil/run_maxiv_twin.py [--lattice PATH] [--port PORT]

All SOLEIL-specific configuration is set here before handing off to the
generic server_manager. The server_manager itself has no hardcoded paths.

Directory layout
----------------
    scripts/
        soleil/
            run_maxiv_twin.py      ← this file
    src/
        dt4acc/
            custom_tango/
                ioc/
                    server_manager.py

Environment variables (all optional, CLI args take precedence)
--------------------------------------------------------------
    DT4ACC_LATTICE_FILE   Path to the SOLEIL AT lattice .m file
    DT4ACC_TANGO_HOST     Tango database host:port  (default: localhost:10000)
    DT4ACC_VIEW           Design or Device view (default: design)
"""

import argparse
import os
import socket
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve paths — script lives at scripts/soleil/, src is two levels up
# ---------------------------------------------------------------------------

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT_DIR    = SCRIPTS_DIR.parent.parent
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

DEFAULT_ACCELERATOR_SETUP_FILE = (
    Path.home()
    / "Documents"
    / "dt4acc_config_data"
    / "accelerator_setup.json"
)

# Calculation heartbeat: recalculates twiss+orbit+tune every N seconds
# WITHOUT changing the lattice — zero noise, reflects current state
DEFAULT_HEARTBEAT_PERIOD_S = 1.0


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
        help=f"Path to the SOLEIL AT lattice .m file (default: {DEFAULT_LATTICE_FILE})",
    )
    parser.add_argument(
        "--tango-host",
        default=os.environ.get("DT4ACC_TANGO_HOST", "localhost:10000"),
        help="Tango database host:port (default: localhost:10000)",
    )
    parser.add_argument(
        "--accelerator-setup-file",
        type=Path,
        default=Path(
            os.environ.get(
                "DT4ACC_ACCELERATOR_SETUP_FILE",
                DEFAULT_ACCELERATOR_SETUP_FILE,
            )
        ),
        help=(
            "Path to accelerator_setup.json "
            f"(default: {DEFAULT_ACCELERATOR_SETUP_FILE})"
        ),
    )
    parser.add_argument(
        "--heartbeat-period",
        type=float,
        default=DEFAULT_HEARTBEAT_PERIOD_S,
        help=f"Recalculation period in seconds, 0 to disable (default: {DEFAULT_HEARTBEAT_PERIOD_S})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="TCP port for the MexecService manager, 0 chooses a free local port (default: 0)",
    )
    parser.add_argument(
        "--view",
        type=str,
        default=os.environ.get("DT4ACC_VIEW", "design"),
        help="Design or Device view (default: design)",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# SOLEIL-specific load_managers
# ---------------------------------------------------------------------------

def _soleil_load_managers():
    """Load the SOLEIL liaison manager and translator service."""
    from dt4acc.custom_facility.soleil.liasion_translator_setup import load_managers
    return load_managers()


def _pick_free_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    args = parse_args()
    mexec_port = args.port or _pick_free_local_port()

    if not args.lattice.exists():
        print(f"ERROR: Lattice file not found: {args.lattice}", file=sys.stderr)
        sys.exit(1)
    if not args.accelerator_setup_file.exists():
        print(
            f"ERROR: accelerator setup file not found: {args.accelerator_setup_file}",
            file=sys.stderr,
        )
        sys.exit(1)

    print("SOLEIL twin server starting")
    print(f"  Lattice          : {args.lattice}")
    print(f"  Accelerator setup: {args.accelerator_setup_file}")
    print(f"  TANGO            : {args.tango_host}")
    print(f"  Recalc period    : {args.heartbeat_period}s (no lattice changes)")
    print(f"  MexecPort        : {mexec_port}")
    print(f"  View             : {args.view}")

    os.environ["TANGO_HOST"] = args.tango_host

    from dt4acc.custom_tango.ioc import server_manager

    server_manager.LATTICE_FILE      = args.lattice
    server_manager.LOAD_MANAGERS_FN  = _soleil_load_managers
    server_manager.HEARTBEAT_PERIOD  = args.heartbeat_period
    server_manager._MANAGER_PORT     = mexec_port
    server_manager.EXPECTED_VIEW     = args.view

    server_manager.main(
        lattice_file=args.lattice,
        load_managers=(
            "dt4acc.custom_facility.soleil.liasion_translator_setup:load_managers"
        ),
        heartbeat_period=args.heartbeat_period,
        manager_port=mexec_port,
        expected_view=args.view,
        accelerator_setup_file=args.accelerator_setup_file,
        position_name_resolver=(
            "dt4acc.custom_facility.soleil.orbit_names:soleil_position_name"
        ),
    )


if __name__ == "__main__":
    main()
