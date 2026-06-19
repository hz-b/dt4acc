import argparse
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# SOLEIL defaults
# ---------------------------------------------------------------------------
DEFAULT_LATTICE_FILE = (
    Path.home()
    / "Documents"
    / "dt4acc_config_data"
    / "SOLEIL_II_V3635_STAB_SYM1_SB3_MULT7_4SX60_V001_Nomenclature.m"
)

# Calculation heartbeat: recalculates twiss+orbit+tune every N seconds
# WITHOUT changing the lattice — zero noise, reflects current state

DEFAULT_HEARTBEAT_PERIOD_S = 1.0

# ---------------------------------------------------------------------------
# CLI: standared arguments
# ---------------------------------------------------------------------------
def build_args_parser():
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
        "--heartbeat-period",
        type=float,
        default=DEFAULT_HEARTBEAT_PERIOD_S,
        help=f"Recalculation period in seconds, 0 to disable (default: {DEFAULT_HEARTBEAT_PERIOD_S})",
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
        help="Design or Device view (default: design)",
    )
    return parser


def parse_args():
    return build_args_parser().parse_args()


def standard_setup_from_environment():
    """
    Should be run at the very beginning of script or process
    """
    os.environ.setdefault("TANGO_HOST", "localhost:10000")


def display_setup_from_args(args):
    print("Arguments used")
    print(f"  Lattice          : {args.lattice}")
    print(f"  TANGO            : {args.tango_host}")
    print(f"  Recalc period    : {args.heartbeat_period}s (no lattice changes)")
    print(f"  MexecPort        : {args.port}")
    print(f"  View             : {args.view}")

