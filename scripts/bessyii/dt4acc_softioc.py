import getpass
import json
import logging
import os
import at
from importlib import resources

from softioc import builder, softioc

from dt4acc.custom_simulator.pyat_simulator.simulator_backend import SimulatorBackend
from dt4acc_lib.core.bl.command_rewritter import CommandRewriter
from dt4acc_lib.core.model.utils.command import ReadCommand
from dt4acc.core.bl.translating_command_execution_engine import TranslatingCommandExecutionEngine
from dt4acc.custom_epics.ioc.orbit_pva import OrbitTwinServer
from dt4acc.custom_epics.ioc.server import View, Controller, dispatcher
from dt4acc.custom_facility.bessyii.liasion_translator_setup import load_managers
from dt4acc.custom_simulator.pyat_simulator.accelerator_simulator import PyATAcceleratorSimulator


logging.basicConfig(level=logging.WARNING)

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
        "custom_facility/bessyii/resources/storage_ring/input/bessy2_storage_ring_reflat.json"
    )
    acc = bessyii_pyat_lattice(filename=filename)
    backend=SimulatorBackend(
        name="BESSYII_on_PyAT",
        acc=PyATAcceleratorSimulator(at_lattice=acc),
    )

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



def bessyii_pyat_lattice_from_dics(seq, energy: float = 1.7185e9):
    r = at.Lattice(seq, name="BESSY II storage ring", energy=energy)
    r.enable_6d()
    r.cavpts = "CAV*"
    r.set_cavity_phase(cavpts=r.cavpts)
    return r


def bessyii_pyat_lattice(filename: str, energy: float = 1.7185e9) -> at.Lattice:
    from lat2db.tools.factories.pyat import factory

    with open(filename, "rt") as fp:
        d = json.load(fp)
    seq = factory(d, energy=energy)
    return bessyii_pyat_lattice_from_dics(seq, energy=energy)


if __name__ == "__main__":
    main()
