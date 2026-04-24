"""
test_01_connectivity.py
=======================
Verify all TANGO devices are registered, exported, and reachable.
These are the fastest tests — no writes, no waits.
"""

import pytest
import tango
from ..conftest import (
    RING_SIM_DEV,
    TEST_QUAD, TEST_STEERER_H,
)

pytestmark = [pytest.mark.integration, pytest.mark.connectivity]


class TestDeviceConnectivity:
    """All virtual and magnet devices must be reachable before anything else."""

    @pytest.mark.parametrize("device_name", [
        RING_SIM_DEV,
        TEST_QUAD,
        TEST_STEERER_H,
    ])
    def test_device_is_exported(self, device_name):
        """Device must be registered in the Tango DB and exported."""
        dp = tango.DeviceProxy(device_name)
        dp.ping()

    def test_ring_sim_state_is_on(self, dp_ring_sim):
        assert dp_ring_sim.state() == tango.DevState.ON

    def test_quad_state_is_on(self, dp_quad):
        assert dp_quad.state() == tango.DevState.ON

    def test_steerer_state_is_on(self, dp_steerer_h):
        assert dp_steerer_h.state() == tango.DevState.ON

    def test_ring_sim_has_twiss_attributes(self, dp_ring_sim):
        """RingSimulatorDevice must expose all twiss attributes."""
        attr_names = [a.name for a in dp_ring_sim.attribute_list_query()]
        for expected in ("orbit_x", "orbit_y",
                         "beta_x", "beta_y",
                         "alpha_x", "alpha_y",
                         "nu_x", "nu_y"):
            assert expected in attr_names, \
                f"RingSimulatorDevice missing attribute: {expected}"

    def test_ring_sim_has_bpm_attributes(self, dp_ring_sim):
        attr_names = [a.name for a in dp_ring_sim.attribute_list_query()]
        for expected in ("bpm_x_attr", "bpm_y_attr", "bpm_names_attr"):
            assert expected in attr_names, \
                f"RingSimulatorDevice missing attribute: {expected}"

    def test_ring_sim_has_tune_attributes(self, dp_ring_sim):
        attr_names = [a.name for a in dp_ring_sim.attribute_list_query()]
        for expected in ("hor", "vert"):
            assert expected in attr_names, \
                f"RingSimulatorDevice missing attribute: {expected}"

    def test_ring_sim_has_reset_and_recalculate_commands(self, dp_ring_sim):
        cmd_names = [c.cmd_name for c in dp_ring_sim.command_list_query()]
        assert "Reset" in cmd_names, "RingSimulatorDevice missing Reset command"
        assert "Recalculate" in cmd_names, \
            "RingSimulatorDevice missing Recalculate command"

    def test_quad_has_magnetic_strength(self, dp_quad):
        attr_names = [a.name for a in dp_quad.attribute_list_query()]
        assert "magnetic_strength" in attr_names
        assert "magnetic_strength_readback" in attr_names

    def test_steerer_has_x_kick_only(self, dp_steerer_h):
        """HorizontalSteererDevice must have x_kick but not y_kick."""
        attr_names = [a.name for a in dp_steerer_h.attribute_list_query()]
        assert "x_kick" in attr_names, "HorizontalSteererDevice missing x_kick"
        assert "y_kick" not in attr_names, \
            "HorizontalSteererDevice should not have y_kick"