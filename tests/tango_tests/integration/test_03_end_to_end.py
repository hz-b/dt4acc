"""
test_03_end_to_end.py
=====================
End-to-end tests: write to a magnet device, verify that the backend
recalculates optics and pushes updated results to virtual devices.

These are the most important tests — they verify the full data flow:

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
from ..conftest import SETTLE_S, RESET_SETTLE_S

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def _arr(dp, attr: str) -> np.ndarray:
    return np.asarray(dp.read_attribute(attr).value, dtype=np.float64)


def _read(dp, attr: str) -> float:
    return float(dp.read_attribute(attr).value)


def _write(dp, attr: str, value: float):
    dp.write_attribute(attr, value)
    time.sleep(SETTLE_S)


def _connect(device_name: str):
    import tango
    dp = tango.DeviceProxy(device_name)
    dp.ping()
    return dp


class TestQuadrupoleWriteTriggersRecalculation:
    """Writing to a quadrupole must trigger twiss and orbit recalculation."""

    @pytest.fixture
    def baseline(self, dp_quad, dp_twiss_orbit, settled):
        """Capture baseline twiss before perturbation."""
        time.sleep(SETTLE_S)
        return {
            "strength": _read(dp_quad, "magnetic_strength"),
            "beta_x":   _arr(dp_twiss_orbit, "beta_x").copy(),
            "beta_y":   _arr(dp_twiss_orbit, "beta_y").copy(),
        }

    @pytest.fixture(autouse=True)
    def restore_quad(self, dp_quad, baseline):
        """Always restore the quadrupole after each test."""
        yield
        dp_quad.write_attribute("magnetic_strength", baseline["strength"])
        time.sleep(SETTLE_S * 2)

    def test_beta_x_changes_after_quad_write(self, dp_quad, dp_twiss_orbit, baseline):
        """
        A quadrupole strength change affects beta functions, not closed orbit.
        Use 1% delta (not 0.1%) to ensure a detectable change.
        """
        delta = baseline["strength"] * 0.01 if baseline["strength"] != 0.0 else 1e-3
        _write(dp_quad, "magnetic_strength", baseline["strength"] + delta)
        time.sleep(SETTLE_S)  # extra settle for twiss propagation

        beta_after = _arr(dp_twiss_orbit, "beta_x")
        assert not np.allclose(baseline["beta_x"], beta_after, rtol=1e-6), \
            "beta_x unchanged after quad write — twiss not recalculated"

    def test_beta_y_changes_after_quad_write(self, dp_quad, dp_twiss_orbit, baseline):
        delta = baseline["strength"] * 0.01 if baseline["strength"] != 0.0 else 1e-3
        _write(dp_quad, "magnetic_strength", baseline["strength"] + delta)
        time.sleep(SETTLE_S)

        beta_after = _arr(dp_twiss_orbit, "beta_y")
        assert not np.allclose(baseline["beta_y"], beta_after, rtol=1e-6), \
            "beta_y unchanged after quad write — twiss not recalculated"

    def test_beta_restores_after_quad_restore(self, dp_quad, dp_twiss_orbit, baseline):
        """After restoring the quadrupole, beta must return to baseline."""
        delta = baseline["strength"] * 0.01 if baseline["strength"] != 0.0 else 1e-3

        _write(dp_quad, "magnetic_strength", baseline["strength"] + delta)
        time.sleep(SETTLE_S)
        _write(dp_quad, "magnetic_strength", baseline["strength"])
        time.sleep(SETTLE_S)

        beta_restored = _arr(dp_twiss_orbit, "beta_x")
        assert np.allclose(baseline["beta_x"], beta_restored, rtol=1e-6), \
            "beta_x did not return to baseline after quad restore"

    def test_multiple_writes_accumulate_correctly(self, dp_quad, dp_twiss_orbit, baseline):
        """Two successive writes should both propagate — verified via beta_x."""
        delta = baseline["strength"] * 0.01 if baseline["strength"] != 0.0 else 1e-3

        _write(dp_quad, "magnetic_strength", baseline["strength"] + delta)
        time.sleep(SETTLE_S)
        beta_after_first = _arr(dp_twiss_orbit, "beta_x").copy()

        _write(dp_quad, "magnetic_strength", baseline["strength"] + 2 * delta)
        time.sleep(SETTLE_S)
        beta_after_second = _arr(dp_twiss_orbit, "beta_x")

        assert not np.allclose(beta_after_first, beta_after_second, rtol=1e-6), \
            "Second quad write did not change beta_x — writes not accumulating"


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
            "strength":  _read(dp_quad, "magnetic_strength"),
            "tune_hor":  _read(dp_tune, "hor"),
            "tune_vert": _read(dp_tune, "vert"),
        }

    @pytest.fixture(autouse=True)
    def restore_quad(self, dp_quad, baseline):
        yield
        dp_quad.write_attribute("magnetic_strength", baseline["strength"])
        time.sleep(SETTLE_S * 2)

    def test_tune_hor_changes_after_quad_write(self, dp_quad, dp_tune, baseline):
        # Use 1% delta — 0.5% was too small to produce a detectable tune shift
        delta = baseline["strength"] * 0.01 if baseline["strength"] != 0.0 else 1e-3
        _write(dp_quad, "magnetic_strength", baseline["strength"] + delta)
        time.sleep(SETTLE_S)  # extra settle for tune propagation

        tune_after = _read(dp_tune, "hor")
        assert not np.isclose(tune_after, baseline["tune_hor"], rtol=1e-6), \
            f"tune.hor unchanged after quad write: {baseline['tune_hor']} → {tune_after}"

    def test_tune_vert_changes_after_quad_write(self, dp_quad, dp_tune, baseline):
        delta = baseline["strength"] * 0.01 if baseline["strength"] != 0.0 else 1e-3
        _write(dp_quad, "magnetic_strength", baseline["strength"] + delta)
        time.sleep(SETTLE_S)

        tune_after = _read(dp_tune, "vert")
        assert not np.isclose(tune_after, baseline["tune_vert"], rtol=1e-6), \
            f"tune.vert unchanged after quad write: {baseline['tune_vert']} → {tune_after}"


class TestResetFunctionality:
    """
    Verify TwissOrbitDevice.Reset recovers the digital twin after beam loss
    caused by an aggressive magnet change.

    Scenario:
      1. Capture nominal beta_x baseline (twin is healthy)
      2. Write a large kick (1e-2 rad) → orbit diverges → backend enters error state
      3. Call TwissOrbitDevice.Reset
      4. Verify the twin recovers: beta_x is finite, positive, close to nominal
      5. Verify the twin accepts further writes (queue loop is running)
    """

    SAFE_KICK   = 1e-6   # rad — small enough for valid optics
    LETHAL_KICK = 1e-2   # rad — large enough to cause divergence / beam loss

    @pytest.fixture
    def dp_reset_steerer(self):
        from ..conftest import RESET_STEERER_H
        return _connect(RESET_STEERER_H)

    @pytest.fixture
    def nominal_beta_x(self, dp_twiss_orbit, dp_reset_steerer, settled):
        """Set a safe kick, wait, record beta_x as reference."""
        dp_reset_steerer.write_attribute("x_kick", self.SAFE_KICK)
        time.sleep(SETTLE_S)
        beta = _arr(dp_twiss_orbit, "beta_x").copy()
        assert len(beta) >= 10, "beta_x not populated before reset test"
        assert np.all(beta > 0), "beta_x not valid before reset test"
        return beta

    def test_reset_restores_device_connectivity(
            self, dp_reset_steerer, dp_twiss_orbit, dp_bpm, dp_tune, nominal_beta_x):
        """After Reset, all virtual devices must be reachable and responsive."""
        import tango
        dp_reset_steerer.write_attribute("x_kick", self.LETHAL_KICK)
        time.sleep(SETTLE_S)

        dp_twiss_orbit.command_inout("Reset")
        time.sleep(RESET_SETTLE_S)

        assert dp_twiss_orbit.state() == tango.DevState.ON, \
            "TwissOrbitDevice not ON after reset"
        dp_bpm.ping()
        dp_tune.ping()

        dp_reset_steerer.write_attribute("x_kick", self.SAFE_KICK)
        time.sleep(SETTLE_S)

    def test_reset_restores_valid_beta_x(
            self, dp_reset_steerer, dp_twiss_orbit, nominal_beta_x):
        """After Reset, beta_x must be finite, positive, and close to nominal."""
        dp_reset_steerer.write_attribute("x_kick", self.LETHAL_KICK)
        time.sleep(SETTLE_S)

        dp_twiss_orbit.command_inout("Reset")
        time.sleep(RESET_SETTLE_S)

        beta = _arr(dp_twiss_orbit, "beta_x")
        assert len(beta) >= 10, "beta_x too short after reset"
        assert np.all(np.isfinite(beta)), "beta_x contains NaN/Inf after reset"
        assert np.all(beta > 0), "beta_x has non-positive values after reset"
        assert np.allclose(nominal_beta_x, beta, rtol=1e-4), \
            "beta_x after reset differs significantly from nominal — lattice not restored"

        dp_reset_steerer.write_attribute("x_kick", self.SAFE_KICK)
        time.sleep(SETTLE_S)

    def test_reset_restores_valid_tune(
            self, dp_reset_steerer, dp_twiss_orbit, dp_tune, nominal_beta_x):
        """After Reset, tune must be finite and in physically valid range."""
        dp_reset_steerer.write_attribute("x_kick", self.LETHAL_KICK)
        time.sleep(SETTLE_S)

        dp_twiss_orbit.command_inout("Reset")
        time.sleep(RESET_SETTLE_S)

        tune_hor  = _read(dp_tune, "hor")
        tune_vert = _read(dp_tune, "vert")

        assert np.isfinite(tune_hor),  f"tune.hor not finite after reset: {tune_hor}"
        assert np.isfinite(tune_vert), f"tune.vert not finite after reset: {tune_vert}"
        assert 0.0 < tune_hor  % 1.0 < 1.0, f"tune.hor out of range: {tune_hor}"
        assert 0.0 < tune_vert % 1.0 < 1.0, f"tune.vert out of range: {tune_vert}"

        dp_reset_steerer.write_attribute("x_kick", self.SAFE_KICK)
        time.sleep(SETTLE_S)

    def test_twin_usable_after_reset(
            self, dp_reset_steerer, dp_twiss_orbit, dp_quad, nominal_beta_x):
        """After Reset, the twin must accept further writes and produce new calculations."""
        dp_reset_steerer.write_attribute("x_kick", self.LETHAL_KICK)
        time.sleep(SETTLE_S)

        dp_twiss_orbit.command_inout("Reset")
        time.sleep(RESET_SETTLE_S)

        baseline_beta = _arr(dp_twiss_orbit, "beta_x").copy()
        current = _read(dp_quad, "magnetic_strength")
        delta = current * 0.01 if current != 0.0 else 1e-3

        _write(dp_quad, "magnetic_strength", current + delta)
        time.sleep(SETTLE_S)
        beta_after = _arr(dp_twiss_orbit, "beta_x")

        dp_quad.write_attribute("magnetic_strength", current)
        dp_reset_steerer.write_attribute("x_kick", self.SAFE_KICK)
        time.sleep(SETTLE_S)

        assert not np.allclose(baseline_beta, beta_after, rtol=1e-6), \
            "beta_x unchanged after quad write post-reset — queue loop not running"