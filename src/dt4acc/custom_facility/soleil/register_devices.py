import json
import pprint
from typing import Sequence, Tuple

from dt4acc.custom_facility.soleil.utils.command_line_interface import parse_args, display_setup_from_args, \
    build_args_parser
from dt4acc.custom_tango.ioc import handle_lattice
from dt4acc.custom_tango.ioc.devices.tango_device_setup import register_all_devices, check_devices
from dt4acc_lib.model.utils.tango_resource_locator import TangoResourceLocator


def display_server_report(server_report):
    if len(server_report.errors):
        print("ERRORS :")
        pprint.pprint(server_report.errors, compact=True)

    if len(server_report.missing):
        print("missing:")
        pprint.pprint(server_report.errors, compact=True)

    txt=f"""Server summary report
     
    numbers: errors {len(server_report.errors)} missing {len(server_report.missing)} found {len(server_report.present)}
    """
    print(txt)


def trl_to_single_server_arguments(trl: Sequence[str]) -> Tuple[str, str]:
    t = TangoResourceLocator.from_trl(trl)
    return t.domain, t.family


def export_present_devices(trls: Sequence[str], filename: str) -> None :
    data = [trl_to_single_server_arguments(t) for t in trls]
    with open(filename, "wt") as fp:
        json.dump(data, fp, indent=4)


def main():
    arg_parser = build_args_parser()
    arg_parser.add_argument("--register-devices", default=False)
    arg_parser.add_argument("--export-present-devices", default="")
    args = arg_parser.parse_args()
    display_setup_from_args(args)
    handle_lattice.lattice_loader.set_lattice_file(args.lattice)

    if args.register_devices:
        servers = register_all_devices()
        print("Registered %d servers", len(servers))
        pprint.pprint(servers, compact=True)
    else:
        server_report = check_devices()
        display_server_report(server_report)
        if args.export_present_devices:
            export_present_devices(server_report.present, args.export_present_devices)


if __name__ == "__main__":
    main()
