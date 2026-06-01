import logging
logging.basicConfig(level=logging.WARNING)

import getpass
import os

from softioc import builder, softioc

from dt4acc.core.bl.controller import Controller
from dt4acc.core.bl.translating_command_execution_engine import TranslatingCommandExecutionEngine
from dt4acc.custom_epics.ioc.controller import dispatcher
from dt4acc.custom_facility.als.controller import ALSEpicsController
from dt4acc.custom_facility.als.liaison_translator_setup import load_managers
from dt4acc.custom_facility.als.read_lattice import als_get_lattice, default_filename
from dt4acc.custom_facility.als.view import ALSView
from dt4acc_lib.model.utils.command import ReadCommand
from dt4acc_lib.pyat_simulator.simulator_backend import SimulatorBackend
from dt4acc_lib.bl.command_rewritter import CommandRewriter
from dt4acc_lib.pyat_simulator.accelerator_simulator_proxy_factory import PyATAcceleratorSimulator

def main():

    lat = als_get_lattice(default_filename)
    backend=SimulatorBackend(
        name="ALS_on_PyAT",
        acc=PyATAcceleratorSimulator(at_lattice=lat),
    )

    _, lm, ts, process_variable_views = load_managers()
    command_rewriter = CommandRewriter(
        liaison_manager=lm,
        translation_service=ts
    )

    mexec = TranslatingCommandExecutionEngine(
        backend=backend,
        cmd_rewriter=command_rewriter,
        # Todo: Cross check with Thorsten,
        #       als-mml ao indicates power converters are working in AMps
        expected_view_for_output="device",
        num_readings=1,
    )
    prefix = os.environ.get("DT4ACC_PREFIX", getpass.getuser())
    view = ALSView(lm=lm, ts=ts)
    common_controller = Controller(
        name="epics-delegate-ctrller",
        mexec=mexec,
        view=view,
        default_delayed_reads=[
            ReadCommand("track", "pos"),
            ReadCommand("twiss", "parameters"),
            # ReadCommand("tune", "x"),
            # ReadCommand("tune", "y"),
        ]
    )
    controller =  ALSEpicsController(
        name = "epics_controller",
        controller_delegate=common_controller,
        builder=builder,
        process_variable_views=process_variable_views
    )
    dispatcher(controller.startup)
    # dispatcher(controller.trigger_read_all_values)
    common_controller.start()
    softioc.interactive_ioc(globals())


if __name__ == "__main__":
    main()