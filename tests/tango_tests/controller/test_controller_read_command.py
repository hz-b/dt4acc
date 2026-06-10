"""Test bed for read commands on tango controller delegate

Without all the overhead of the tango control system

*NB* uses soleil setup
"""
import math
from pathlib import Path

import pytest

from dt4acc.core.bl.controller import Controller
from dt4acc.core.bl.translating_command_execution_engine import (
    TranslatingCommandExecutionEngine,
)
from dt4acc.custom_facility.soleil.liasion_translator_setup import load_managers
from dt4acc.custom_tango.ioc.handle_lattice import LatticeLoader
from dt4acc_lib.bl.command_rewritter import CommandRewriter
from dt4acc_lib.model.output.tune import Chromaticity
from dt4acc_lib.model.utils.command import ReadCommand
from dt4acc_lib.pyat_simulator.accelerator_simulator import PyATAcceleratorSimulator
from dt4acc_lib.pyat_simulator.simulator_backend import SimulatorBackend


@pytest.fixture(scope="module")
def backend():
    loader = LatticeLoader()
    # Todo: need here some test file
    #       * e.g. an outdated Soleil II file
    #       * a simple TME lattice file
    #       * a FODO File
    lattice_file = (
            Path.home() / "Documents"
                    / "dt4acc_config_data"
    / "SOLEIL_II_V3635_STAB_SYM1_SB3_MULT7_4SX60_V001_Nomenclature.m"
    )
    loader.set_lattice_file(lattice_file)
    acc = loader.load()
    r = SimulatorBackend(
        name="Facility specific PYAT",
        acc=PyATAcceleratorSimulator(at_lattice=acc),
    )
    return r


@pytest.fixture(scope="module")
def managers():
    return load_managers()


@pytest.fixture(scope="module")
def mexec(managers, backend):
    _, lm, ts = managers

    cmd_rewriter = CommandRewriter(liaison_manager=lm, translation_service=ts)
    r = TranslatingCommandExecutionEngine(
        backend=backend,
        cmd_rewriter=cmd_rewriter,
        expected_view_for_output="design",
        num_readings=1,
    )
    return r


@pytest.fixture(scope="function")
def controller(mexec):
    controller = Controller(
        name = "tango-test-controller",
        mexec = mexec,
        default_delayed_reads = [],
        # todo: find out which view is needed here
        view = None,
        )
    return controller


@pytest.mark.asyncio
async def test_read_track(controller):
    rcmds = [
        ReadCommand(id='track', property='pos'),
    ]
    r = await controller.trigger_read(rcmds)
    pass


@pytest.mark.asyncio
async def test_read_chromaticity(controller):
    rcmds = [
        ReadCommand(id='chromaticity', property='transversal')
    ]
    r = await controller.trigger_read(rcmds)
    chroma_pkg, = r.all_readings()
    chroma = chroma_pkg.payload
    assert isinstance(chroma, Chromaticity)
    assert not math.isnan(chroma.x)
    assert not math.isnan(chroma.y)


@pytest.mark.asyncio
async def test_read_twiss(controller):
    rcmds = [
        ReadCommand(id='twiss', property='parameters'),
    ]

    r = await controller.trigger_read(rcmds)

    pass
