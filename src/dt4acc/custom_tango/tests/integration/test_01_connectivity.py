"""
test_01_connectivity.py
=======================
Verify all TANGO devices are registered, exported, and reachable.
These are the fastest tests — no writes, no waits.
"""

import pytest
import tango
from ..conftest import (
    TWISS_ORBIT_DEV, BPM_DEV, TUNE_DEV,
    TEST_QUAD, TEST_STEERER_H,
)

pytestmark = [pytest.mark.integration, pytest.mark.connectivity]


class TestDeviceConnectivity:
    """All virtual and magnet devices must be reachable before anything else."""

    @pytest.mark.parametrize("device_name", [
        TWISS_ORBIT_DEV,
        BPM_DEV,
        TUNE_DEV,
        TEST_QUAD,
        TEST_STEERER_H,
    ])
    def test_device_is_exported(self, device_name):
        """Device must be registered in the Tango DB and exported."""
        dp = tango.DeviceProxy(device_name)
        dp.ping()

    def test_twiss_orbit_state_is_on(self, dp_twiss_orbit):
        assert dp_twiss_orbit.state() == tango.DevState.ON

    def test_bpm_state_is_on(self, dp_bpm):
        assert dp_bpm.state() == tango.DevState.ON

    def test_tune_state_is_on(self, dp_tune):
        assert dp_tune.state() == tango.DevState.ON

    def test_quad_state_is_on(self, dp_quad):
        assert dp_quad.state() == tango.DevState.ON

    def test_steerer_state_is_on(self, dp_steerer_h):
        assert dp_steerer_h.state() == tango.DevState.ON

    def test_twiss_orbit_has_expected_attributes(self, dp_twiss_orbit):
        """TwissOrbitDevice must expose all expected spectrum attributes."""
        attr_names = [a.name for a in dp_twiss_orbit.attribute_list_query()]
        for expected in ("orbit_x", "orbit_y", "beta_x", "beta_y",
                         "alpha_x", "alpha_y", "nu_x", "nu_y"):
            assert expected in attr_names, \
                f"TwissOrbitDevice missing attribute: {expected}"

    def test_bpm_has_expected_attributes(self, dp_bpm):
        attr_names = [a.name for a in dp_bpm.attribute_list_query()]
        for expected in ("bpm_x_attr", "bpm_y_attr", "bpm_names_attr"):
            assert expected in attr_names, \
                f"BPMManagerDevice missing attribute: {expected}"

    def test_tune_has_expected_attributes(self, dp_tune):
        attr_names = [a.name for a in dp_tune.attribute_list_query()]
        for expected in ("hor", "vert"):
            assert expected in attr_names, \
                f"TuneDevice missing attribute: {expected}"

    def test_quad_has_magnetic_strength(self, dp_quad):
        attr_names = [a.name for a in dp_quad.attribute_list_query()]
        assert "magnetic_strength" in attr_names

    def test_steerer_has_x_kick(self, dp_steerer_h):
        attr_names = [a.name for a in dp_steerer_h.attribute_list_query()]
        assert "x_kick" in attr_names
