#!/usr/bin/env python3
"""
DT4ACC Enhanced Tango Server Script - Equivalent to EPICS softioc script
Runs the enhanced Tango server with EPICS-aligned heartbeat monitoring.
"""
import argparse
import logging
import os
import sys
from pathlib import Path


# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Set up logging
logging.basicConfig(level=logging.WARNING)

# Set environment variable for Tango server type
os.environ["server"] = "tango"

from dt4acc.config.accelerator_config import accelerator_config

def parse_args() -> argparse.Namespace:
    default_dir = Path.home() / "Documents" / "dt4acc_soleil_twin_data"
    default_setup = default_dir / "accelerator_setup.json"
    default_lattice = default_dir / "SOLEIL_II_V3631_sym1_V001_database.m"
    parser = argparse.ArgumentParser(
        description=(
            "Digital twin for accelerator enhanced tango server"
        )
    )
    parser.add_argument(
        "--accelerator-setup-file",
        default = str(default_setup),
        help="Configuration file for the accelerator",
    )
    parser.add_argument(
        "--lattice-file",
        default = str(default_lattice),
        help="The lattice file",
    )
    return parser.parse_args()

if __name__ == "__main__":
    try:
        args = parse_args()

        accelerator_config.accelerator_setup_file = args.accelerator_setup_file
        accelerator_config.accelerator_lattice_file = args.lattice_file
        logging.log(logging.INFO, f"Accelerator setup file: {accelerator_config.accelerator_setup_file}")
        logging.log(logging.INFO, f"Lattice file = {accelerator_config.accelerator_lattice_file}")
        print(f"Accelerator setup file = {accelerator_config.accelerator_setup_file}")
        print(f"Lattice file = {accelerator_config.accelerator_lattice_file}")

        # Run the enhanced Tango server with heartbeat
        print("🚀 Starting DT4ACC Enhanced Tango Server...")
        print("🔧 Server type: Tango")
        from dt4acc.custom_tango.ioc.devices.server_manager import main
        main()
    except KeyboardInterrupt:
        print("\n🛑 Tango server stopped by user")
    except Exception as e:
        print(f"❌ Tango server failed: {e}")
        raise 