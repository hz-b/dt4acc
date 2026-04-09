import getpass
import logging
import os
from importlib import resources

from dt4acc.core.bl.translating_command_execution_engine import TranslatingCommandExecutionEngine
from dt4acc.custom_epics.ioc.orbit_pva import OrbitTwinServer

logging.basicConfig(level=logging.WARNING)

from softioc import builder, softioc

from accml_lib.core.bl.command_rewritter import CommandRewriter
from accml_lib.core.model.utils.command import ReadCommand
from accml_lib.custom.bessyii.liasion_translator_setup import load_managers
from accml_lib.custom.bessyii.pyat_simulator_backend import simulator_backend


from dt4acc.custom_epics.ioc.server import View, Controller, dispatcher

def main():
    """Handle all startups

    * load liasion manager and translation service
      and build command rewriter from them
    * use a basic measurement execution engine should be
      (should be rather called "command execution engine).
      This currently uses an pyat based backend.

    * view is a key-value storage to access the proces variables
    * controller takes care to
        * build up all variables of the view (needed due to EPICS builder)
        * pass them to the view
        * handle delayed execution

    """
    filename = resources.files("dt4acc").joinpath(
        "custom_epics/data/standard/bessy2_storage_ring_reflat.json"
    )

    backend = simulator_backend(filename)
    _, lm, ts = load_managers()

    command_rewriter=CommandRewriter(
        liaison_manager=lm,
        translation_service=ts
    )

    # Todo: review if a dedicated execution engine
    #       View gets an engine to execute
    #       each trigger calls to the engine. When something happens
    mexec = TranslatingCommandExecutionEngine(
        backend=backend,
        cmd_rewriter=command_rewriter,
        storage=None,
        expected_view_for_output="device",
        num_readings=1,
    )
    prefix = os.environ.get("DT4ACC_PREFIX", getpass.getuser())
    orbit_server = OrbitTwinServer(prefix + ":ORBITCC:rdBpm")
    orbit_server.start()
    view = View(orbit_server=orbit_server)
    controller = Controller(
        view=view,
        mexec=mexec,
        builder=builder,
        default_delayed_reads=[
            ReadCommand("track", "pos"),
            ReadCommand("twiss", "parameters"),
            ReadCommand("tune", "x"),
            ReadCommand("tune", "y"),
        ]
    )
    dispatcher(controller.startup)
    softioc.interactive_ioc(globals())


if __name__ == "__main__":
    main()
