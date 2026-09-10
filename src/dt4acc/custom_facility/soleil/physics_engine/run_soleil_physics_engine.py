"""Physics engine as tango device

Starts the mexec service and the tango device
"""
import os

from dt4acc.custom_facility.soleil.run_soleil_twin import _soleil_load_managers
from dt4acc.custom_facility.soleil.utils.command_line_interface import display_setup_from_args, parse_args
from dt4acc.core.bl import handle_lattice
from dt4acc.custom_tango.ioc import mexec_server_for_physics_engine
from dt4acc.custom_tango.ioc.mexec_server_for_physics_engine import _run_mexec_service


def main():
    args = parse_args()
    print("Starting SOLEIL twin physics mexec engine")
    display_setup_from_args(args)
    os.environ["TANGO_HOST"] = args.tango_host

    # Todo: need to improve handling configurations for load managers etc
    mexec_server_for_physics_engine.LOAD_MANAGERS_FN = _soleil_load_managers

    handle_lattice.lattice_loader.set_lattice_file(args.lattice)
    print(handle_lattice.lattice_loader)
    _run_mexec_service()


if __name__ == "__main__":
    main()