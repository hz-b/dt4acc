"""
test_03_end_to_end.py
=====================
End-to-end tango_tests: write to a magnet device, verify that the backend
recalculates optics and pushes updated results to virtual devices.

These are the most important tango_tests — they verify the full data flow:

    MagnetDevice.write
      → SyncMexecProxy.sync_set (cross-process)
        → SimulatorBackend.set (pyAT lattice update)
          → TangoController delayed queue
            → mexec.trigger_read (twiss + orbit + tune)
              → TangoView.dispatch
                → TwissOrbitDevice / BPMManagerDevice / TuneDevice updated
"""

import time
import pytest
import numpy as np
from ..conftest import SETTLE_S

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def _arr(dp, attr: str) -> np.ndarray:
    return np.asarray(dp.read_attribute(attr).value, dtype=np.float64)


def _read(dp, attr: str) -> float:
    return float(dp.read_attribute(attr).value)


def _write(dp, attr: str, value: float):
    dp.write_attribute(attr, value)
    time.sleep(SETTLE_S)


class TestQuadrupoleWriteTriggersRecalculation:
    """Writing to a quadrupole must trigger twiss and orbit recalculation."""

    @pytest.fixture
    def baseline(self, dp_quad, dp_twiss_orbit, settled):
        """Capture baseline orbit and twiss before perturbation."""
        time.sleep(SETTLE_S)
        return {
            "strength": _read(dp_quad, "magnetic_strength"),
            "orbit_x":  _arr(dp_twiss_orbit, "orbit_x").copy(),
            "beta_x":   _arr(dp_twiss_orbit, "beta_x").copy(),
        }

    @pytest.fixture(autouse=True)
    def restore_quad(self, dp_quad, baseline):
        """Always restore the quadrupole after each test."""
        yield
        dp_quad.write_attribute("magnetic_strength", baseline["strength"])
        time.sleep(SETTLE_S)

    def test_orbit_x_changes_after_quad_write(self, dp_quad, dp_twiss_orbit, baseline):
        delta = baseline["strength"] * 0.001 if baseline["strength"] != 0.0 else 1e-4
        _write(dp_quad, "magnetic_strength", baseline["strength"] + delta)

        orbit_after = _arr(dp_twiss_orbit, "orbit_x")
        assert not np.allclose(baseline["orbit_x"], orbit_after, atol=1e-12), \
            "orbit_x unchanged after quad write — delayed read not triggered"

    def test_beta_x_changes_after_quad_write(self, dp_quad, dp_twiss_orbit, baseline):
        delta = baseline["strength"] * 0.001 if baseline["strength"] != 0.0 else 1e-4
        _write(dp_quad, "magnetic_strength", baseline["strength"] + delta)

        beta_after = _arr(dp_twiss_orbit, "beta_x")
        assert not np.allclose(baseline["beta_x"], beta_after, atol=1e-12), \
            "beta_x unchanged after quad write — twiss not recalculated"

    def test_orbit_restores_after_quad_restore(self, dp_quad, dp_twiss_orbit, baseline):
        """After restoring the magnet, orbit must return to baseline."""
        delta = baseline["strength"] * 0.01 if baseline["strength"] != 0.0 else 1e-3

        _write(dp_quad, "magnetic_strength", baseline["strength"] + delta)
        _write(dp_quad, "magnetic_strength", baseline["strength"])

        orbit_restored = _arr(dp_twiss_orbit, "orbit_x")
        assert np.allclose(baseline["orbit_x"], orbit_restored, atol=1e-10), \
            "orbit_x did not return to baseline after quad restore"

    def test_multiple_writes_accumulate_correctly(self, dp_quad, dp_twiss_orbit, baseline):
        """Two successive writes should both propagate."""
        delta = baseline["strength"] * 0.001 if baseline["strength"] != 0.0 else 1e-4

        _write(dp_quad, "magnetic_strength", baseline["strength"] + delta)
        orbit_after_first = _arr(dp_twiss_orbit, "orbit_x").copy()

        _write(dp_quad, "magnetic_strength", baseline["strength"] + 2 * delta)
        orbit_after_second = _arr(dp_twiss_orbit, "orbit_x")

        assert not np.allclose(orbit_after_first, orbit_after_second, atol=1e-12), \
            "Second quad write did not change orbit — writes not accumulating"


class TestSteererWriteTriggersRecalculation:
    """Writing a horizontal kick must change the orbit."""

    @pytest.fixture
    def baseline(self, dp_steerer_h, dp_twiss_orbit, settled):
        time.sleep(SETTLE_S)
        return {
            "x_kick":  _read(dp_steerer_h, "x_kick"),
            "orbit_x": _arr(dp_twiss_orbit, "orbit_x").copy(),
            "orbit_y": _arr(dp_twiss_orbit, "orbit_y").copy(),
        }

    @pytest.fixture(autouse=True)
    def restore_steerer(self, dp_steerer_h, baseline):
        yield
        dp_steerer_h.write_attribute("x_kick", baseline["x_kick"])
        time.sleep(SETTLE_S)

    def test_orbit_x_changes_after_h_kick(self, dp_steerer_h, dp_twiss_orbit, baseline):
        _write(dp_steerer_h, "x_kick", baseline["x_kick"] + 1e-5)

        orbit_after = _arr(dp_twiss_orbit, "orbit_x")
        assert not np.allclose(baseline["orbit_x"], orbit_after, atol=1e-12), \
            "orbit_x unchanged after horizontal kick"

    def test_orbit_y_unaffected_by_h_kick(self, dp_steerer_h, dp_twiss_orbit, baseline):
        """A pure horizontal kick should not change orbit_y significantly."""
        _write(dp_steerer_h, "x_kick", baseline["x_kick"] + 1e-5)

        orbit_y_after = _arr(dp_twiss_orbit, "orbit_y")
        # Allow small coupling effects but not large changes
        max_change = np.max(np.abs(orbit_y_after - baseline["orbit_y"]))
        orbit_y_scale = np.max(np.abs(baseline["orbit_y"])) or 1.0
        assert max_change / orbit_y_scale < 0.1, \
            f"orbit_y changed too much after h_kick: max_change={max_change:.2e}"

    def test_kick_zero_restores_orbit(self, dp_steerer_h, dp_twiss_orbit, baseline):
        _write(dp_steerer_h, "x_kick", baseline["x_kick"] + 1e-4)
        _write(dp_steerer_h, "x_kick", baseline["x_kick"])

        orbit_restored = _arr(dp_twiss_orbit, "orbit_x")
        assert np.allclose(baseline["orbit_x"], orbit_restored, atol=1e-10), \
            "orbit_x did not restore after setting kick back to baseline"


class TestTuneUpdateOnMagnetWrite:
    """Tune must update after a quadrupole write."""

    @pytest.fixture
    def baseline(self, dp_quad, dp_tune, settled):
        time.sleep(SETTLE_S)
        return {
            "strength": _read(dp_quad, "magnetic_strength"),
            "tune_hor":  _read(dp_tune, "hor"),
            "tune_vert": _read(dp_tune, "vert"),
        }

    @pytest.fixture(autouse=True)
    def restore_quad(self, dp_quad, baseline):
        yield
        dp_quad.write_attribute("magnetic_strength", baseline["strength"])
        time.sleep(SETTLE_S)

    def test_tune_hor_changes_after_quad_write(self, dp_quad, dp_tune, baseline):
        delta = baseline["strength"] * 0.005 if baseline["strength"] != 0.0 else 1e-3
        _write(dp_quad, "magnetic_strength", baseline["strength"] + delta)

        tune_after = _read(dp_tune, "hor")
        assert tune_after != baseline["tune_hor"], \
            "tune.hor unchanged after quad write — tune not recalculated"

    def test_tune_vert_changes_after_quad_write(self, dp_quad, dp_tune, baseline):
        delta = baseline["strength"] * 0.005 if baseline["strength"] != 0.0 else 1e-3
        _write(dp_quad, "magnetic_strength", baseline["strength"] + delta)

        tune_after = _read(dp_tune, "vert")
        assert tune_after != baseline["tune_vert"], \
            "tune.vert unchanged after quad write — tune not recalculated"
