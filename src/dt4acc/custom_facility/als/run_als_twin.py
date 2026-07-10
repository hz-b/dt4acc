import asyncio
import logging
# logging.basicConfig(level=logging.WARNING)


import getpass
import os
from typing import Any, Dict, Sequence, Union

from softioc import builder, softioc

from dt4acc.core.bl.controller import Controller, read_and_dispatch
from dt4acc.core.bl.translating_command_execution_engine import (
    TranslatingCommandExecutionEngine,
)
from dt4acc.core.interfaces.controller_interface import ControllerInterface
from dt4acc.core.model.view import Monitor, Setpoint
from dt4acc.custom_epics.ioc.controller import dispatcher
from dt4acc.custom_epics.ioc.pv_setup import initialize_master_clock_pvs, initialize_machine_info_pvs, \
    initialize_orbit_pvs, initialize_twiss_pvs, initialize_tune_pvs, initialize_calculation_state_pvs, \
    initialize_turn_by_turn_p0
from dt4acc.custom_epics.ioc.pv_setup_from_model import initialize_pvs_from_model
from dt4acc.custom_facility.als.liaison_translator_setup import load_managers
from dt4acc.custom_facility.als.read_lattice import als_get_lattice, default_filename
from dt4acc.custom_facility.als.view import ALSView
from dt4acc_lib.model.utils.command import ReadCommand, Command
from dt4acc_lib.pyat_simulator.accelerator_simulator import PyATAcceleratorSimulator
from dt4acc_lib.pyat_simulator.simulator_backend import SimulatorBackend
from dt4acc_lib.bl.command_rewritter import CommandRewriter
from dt4acc_lib.model.output.track import ParticleState

# dt4acc lib etc only warning level info only for dt4acc
logging.getLogger("transitions").setLevel(logging.WARNING)
logging.getLogger("dt4acc_lib").setLevel(logging.WARNING)
logging.getLogger("dt4acc").setLevel(logging.INFO)

async def main():

    lat = als_get_lattice(default_filename)
    backend = SimulatorBackend(
        name="ALS_on_PyAT",
        acc=PyATAcceleratorSimulator(at_lattice=lat),
    )

    yp, lm, ts, process_variable_views = load_managers()
    command_rewriter = CommandRewriter(liaison_manager=lm, translation_service=ts)

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
    controller = Controller(
        name="epics-controller",
        mexec=mexec,
        view=view,
        default_delayed_reads=[
            ReadCommand("track", "pos"),
            ReadCommand("twiss", "parameters"),
            # will calculate any time something changes on the twin
            ReadCommand("turn_by_turn", "pos"),
            # ReadCommand("tune", "x"),
            # ReadCommand("tune", "y"),
        ],
    )
    # controller.start()
    if prefix:
        builder.SetDeviceName(prefix)

    # by default: set all beam position monitors as
    # I assume that the names of the BPM match lattice element
    # markers
    await controller.update(
        cmd=Command(
            "turn_by_turn_start",
            "data_needed_at",
            [mml_id.as_abbreviation() for mml_id in yp.get("BPM")],
            None
        ),
        reads=[]
    )

    # Todo: re evaluate if turn by turn data should default to tracking reference particle
    await controller.update(
        cmd=Command("turn_by_turn_start", "p0", [ParticleState.from_sequence([0] * 6)] * 3, None), reads=[]
    )
    # Todo: re evaluate if turn by turn data should default to tracking one turn
    await controller.update(
        cmd=Command("turn_by_turn_start", "n_turns", 1, None), reads=[]
    )
    r = await controller.trigger_read([ReadCommand("turn_by_turn_start", "p0")])
    view.update_process_variables(
        await initialise_pvs(
            builder=builder,
            models=process_variable_views,
            controller=controller
        )
    )
    # Only start controller: at this stage the delayed queue will
    # start to work
    controller.start()

    # Extra reads at startup
    await read_and_dispatch(
        controller=controller,
        view=view,
        rcmds=list(controller.default_delayed_reads),
    )
    builder.LoadDatabase()
    softioc.iocInit(dispatcher)
    softioc.interactive_ioc(globals())


async def initialise_pvs(
    builder,
    models: Sequence[Union[Monitor, Setpoint]],
    controller: ControllerInterface
) -> Dict[ReadCommand, Any]:

    return {
        **await initialize_pvs_from_model(builder, models, controller),
        **await initialize_turn_by_turn_p0(builder, controller),
        **initialize_machine_info_pvs(builder, n_ref_buckets=328),
        **initialize_orbit_pvs(builder),
        **initialize_twiss_pvs(builder),
        **initialize_tune_pvs(builder),
        **initialize_calculation_state_pvs(builder, controller),
    }


if __name__ == "__main__":
    asyncio.run(main())
