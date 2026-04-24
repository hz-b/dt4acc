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


def _reset_if_needed(dp_ring_sim):
    """
    Reset if the backend SimulatorBackend is in error state.
    RingSimulatorDevice always reports DevState.ON even in error state.
    We probe by reading beta_x — if it's a placeholder or invalid, reset.
    """
    import numpy as np
    try:
        beta = np.asarray(dp_ring_sim.read_attribute("beta_x").value, dtype=np.float64)
        healthy = len(beta) >= 10 and np.all(beta > 0)
    except Exception:
        healthy = False

    if not healthy:
        try:
            dp_ring_sim.command_inout("Reset")
            time.sleep(RESET_SETTLE_S)
        except Exception:
            pass


class TestQuadrupoleWriteTriggersRecalculation:
    """
    Writing to a quadrupole must trigger twiss recalculation.

    NOTE: QF01.01 has K=0 in the nominal lattice. Writing a non-zero K
    perturbs the optics enough to cause AT tracking to diverge if the delta
    is too large. We use a single small-delta test and reset after.
    If beta_x responds, the full pipeline (set → recalc → push) is verified.
    """

    QUAD_DELTA = 1e-4

    @pytest.fixture
    def baseline(self, dp_quad, dp_ring_sim, settled):
        _reset_if_needed(dp_ring_sim)
        time.sleep(SETTLE_S)
        return {
            "strength": _read(dp_quad, "magnetic_strength"),
            "beta_x":   _arr(dp_ring_sim, "beta_x").copy(),
        }

    @pytest.fixture(autouse=True)
    def restore_quad(self, dp_quad, dp_ring_sim, baseline):
        yield
        _reset_if_needed(dp_ring_sim)
        try:
            dp_quad.write_attribute("magnetic_strength", baseline["strength"])
            time.sleep(SETTLE_S * 2)
        except Exception:
            pass

    def test_beta_x_changes_after_quad_write(self, dp_quad, dp_ring_sim, baseline):
        """A quadrupole strength change must trigger twiss recalculation."""
        _write(dp_quad, "magnetic_strength", baseline["strength"] + self.QUAD_DELTA)
        beta_after = _arr(dp_ring_sim, "beta_x")
        assert not np.allclose(baseline["beta_x"], beta_after, rtol=1e-6), \
            "beta_x unchanged after quad write — twiss not recalculated"


class TestSteererWriteTriggersRecalculation:
    """Writing a horizontal kick must change the orbit."""

    @pytest.fixture
    def baseline(self, dp_steerer_h, dp_ring_sim, settled):
        _reset_if_needed(dp_ring_sim)
        time.sleep(SETTLE_S)
        return {
            "x_kick":  _read(dp_steerer_h, "x_kick"),
            "orbit_x": _arr(dp_ring_sim, "orbit_x").copy(),
            "orbit_y": _arr(dp_ring_sim, "orbit_y").copy(),
        }

    @pytest.fixture(autouse=True)
    def restore_steerer(self, dp_steerer_h, dp_ring_sim, baseline):
        yield
        _reset_if_needed(dp_ring_sim)
        try:
            dp_steerer_h.write_attribute("x_kick", baseline["x_kick"])
            time.sleep(SETTLE_S)
        except Exception:
            pass

    def test_orbit_x_changes_after_h_kick(self, dp_steerer_h, dp_ring_sim, baseline):
        """
        A horizontal kick must change the closed orbit somewhere in the ring.
        We check orbit_x RMS changes rather than pointwise — the effect may
        be small at the steerer location but visible globally.
        """
        _write(dp_steerer_h, "x_kick", baseline["x_kick"] + 1e-5)

        orbit_after = _arr(dp_ring_sim, "orbit_x")
        rms_before = np.sqrt(np.mean(baseline["orbit_x"] ** 2))
        rms_after  = np.sqrt(np.mean(orbit_after ** 2))
        # RMS must change by at least 1% — not zero effect
        assert not np.isclose(rms_before, rms_after, rtol=0.01), \
            f"orbit_x RMS unchanged after horizontal kick: before={rms_before:.2e} after={rms_after:.2e}"

    def test_orbit_y_unaffected_by_h_kick(self, dp_steerer_h, dp_ring_sim, baseline):
        """A pure horizontal kick should not change orbit_y significantly."""
        _write(dp_steerer_h, "x_kick", baseline["x_kick"] + 1e-5)

        orbit_y_after = _arr(dp_ring_sim, "orbit_y")
        # Allow small coupling effects but not large changes
        max_change = np.max(np.abs(orbit_y_after - baseline["orbit_y"]))
        orbit_y_scale = np.max(np.abs(baseline["orbit_y"])) or 1.0
        assert max_change / orbit_y_scale < 0.1, \
            f"orbit_y changed too much after h_kick: max_change={max_change:.2e}"

    def test_kick_zero_restores_orbit(self, dp_steerer_h, dp_ring_sim, baseline):
        _write(dp_steerer_h, "x_kick", baseline["x_kick"] + 1e-4)
        _write(dp_steerer_h, "x_kick", baseline["x_kick"])

        orbit_restored = _arr(dp_ring_sim, "orbit_x")
        assert np.allclose(baseline["orbit_x"], orbit_restored, atol=1e-10), \
            "orbit_x did not restore after setting kick back to baseline"


class TestTuneUpdateOnMagnetWrite:
    """
    Tune must update after a quadrupole write.
    QF01.01 with K=0 may only affect one tune plane — we check that
    at least one of hor/vert changes.
    """

    QUAD_DELTA = 1e-4

    @pytest.fixture
    def baseline(self, dp_quad, dp_ring_sim, settled):
        _reset_if_needed(dp_ring_sim)
        time.sleep(SETTLE_S)
        return {
            "strength":  _read(dp_quad, "magnetic_strength"),
            "tune_hor":  _read(dp_ring_sim, "hor"),
            "tune_vert": _read(dp_ring_sim, "vert"),
        }

    @pytest.fixture(autouse=True)
    def restore_quad(self, dp_quad, dp_ring_sim, baseline):
        yield
        _reset_if_needed(dp_ring_sim)
        try:
            dp_quad.write_attribute("magnetic_strength", baseline["strength"])
            time.sleep(SETTLE_S * 2)
        except Exception:
            pass

    def test_tune_changes_after_quad_write(self, dp_quad, dp_ring_sim, baseline):
        """At least one tune plane must respond to a quad write."""
        _write(dp_quad, "magnetic_strength", baseline["strength"] + self.QUAD_DELTA)
        time.sleep(SETTLE_S)

        hor_after  = _read(dp_ring_sim, "hor")
        vert_after = _read(dp_ring_sim, "vert")

        hor_changed  = not np.isclose(hor_after,  baseline["tune_hor"],  rtol=1e-6)
        vert_changed = not np.isclose(vert_after, baseline["tune_vert"], rtol=1e-6)

        assert hor_changed or vert_changed, \
            f"Neither tune changed: hor {baseline['tune_hor']}→{hor_after}, " \
            f"vert {baseline['tune_vert']}→{vert_after}"


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
    def nominal_beta_x(self, dp_ring_sim, dp_reset_steerer, settled):
        """Reset to nominal, set a safe kick, record beta_x as reference."""
        # Always reset unconditionally — previous tests may have left
        # the backend in error state regardless of beta_x health probe
        dp_ring_sim.command_inout("Reset")
        time.sleep(RESET_SETTLE_S)
        dp_reset_steerer.write_attribute("y_kick", self.SAFE_KICK)
        time.sleep(SETTLE_S)
        beta = _arr(dp_ring_sim, "beta_x").copy()
        assert len(beta) >= 10, "beta_x not populated before reset test"
        assert np.all(beta > 0), "beta_x not valid before reset test"
        return beta

    def test_reset_restores_device_connectivity(
            self, dp_reset_steerer, dp_ring_sim, dp_bpm, dp_tune, nominal_beta_x):
        """After Reset, all virtual devices must be reachable and responsive."""
        import tango
        dp_reset_steerer.write_attribute("y_kick", self.LETHAL_KICK)
        time.sleep(SETTLE_S)

        dp_ring_sim.command_inout("Reset")
        time.sleep(RESET_SETTLE_S)

        assert dp_ring_sim.state() == tango.DevState.ON, \
            "TwissOrbitDevice not ON after reset"
        dp_ring_sim.ping()
        dp_ring_sim.ping()

        dp_reset_steerer.write_attribute("y_kick", self.SAFE_KICK)
        time.sleep(SETTLE_S)

    def test_reset_restores_valid_beta_x(
            self, dp_reset_steerer, dp_ring_sim, nominal_beta_x):
        """After Reset, beta_x must be finite, positive, and close to nominal."""
        dp_reset_steerer.write_attribute("y_kick", self.LETHAL_KICK)
        time.sleep(SETTLE_S)

        dp_ring_sim.command_inout("Reset")
        time.sleep(RESET_SETTLE_S)

        beta = _arr(dp_ring_sim, "beta_x")
        assert len(beta) >= 10, "beta_x too short after reset"
        assert np.all(np.isfinite(beta)), "beta_x contains NaN/Inf after reset"
        assert np.all(beta > 0), "beta_x has non-positive values after reset"
        assert np.allclose(nominal_beta_x, beta, rtol=1e-4), \
            "beta_x after reset differs significantly from nominal — lattice not restored"

        dp_reset_steerer.write_attribute("y_kick", self.SAFE_KICK)
        time.sleep(SETTLE_S)

    def test_reset_restores_valid_tune(
            self, dp_reset_steerer, dp_ring_sim, dp_tune, nominal_beta_x):
        """After Reset, tune must be finite and in physically valid range."""
        dp_reset_steerer.write_attribute("y_kick", self.LETHAL_KICK)
        time.sleep(SETTLE_S)

        dp_ring_sim.command_inout("Reset")
        time.sleep(RESET_SETTLE_S)

        tune_hor  = _read(dp_tune, "hor")
        tune_vert = _read(dp_tune, "vert")

        assert np.isfinite(tune_hor),  f"tune.hor not finite after reset: {tune_hor}"
        assert np.isfinite(tune_vert), f"tune.vert not finite after reset: {tune_vert}"
        assert 0.0 < tune_hor  % 1.0 < 1.0, f"tune.hor out of range: {tune_hor}"
        assert 0.0 < tune_vert % 1.0 < 1.0, f"tune.vert out of range: {tune_vert}"

        dp_reset_steerer.write_attribute("y_kick", self.SAFE_KICK)
        time.sleep(SETTLE_S)

    def test_twin_usable_after_reset(
            self, dp_reset_steerer, dp_ring_sim, dp_quad, nominal_beta_x):
        """After Reset, the twin must accept further writes and produce new calculations."""
        dp_reset_steerer.write_attribute("y_kick", self.LETHAL_KICK)
        time.sleep(SETTLE_S)

        dp_ring_sim.command_inout("Reset")
        time.sleep(RESET_SETTLE_S)

        baseline_beta = _arr(dp_ring_sim, "beta_x").copy()
        current = _read(dp_quad, "magnetic_strength")
        delta = 1e-4  # safe small absolute delta

        _write(dp_quad, "magnetic_strength", current + delta)
        time.sleep(SETTLE_S)
        beta_after = _arr(dp_ring_sim, "beta_x")

        # Restore — reset first in case the write caused beam loss
        _reset_if_needed(dp_ring_sim)
        try:
            dp_quad.write_attribute("magnetic_strength", current)
        except Exception:
            pass
        dp_reset_steerer.write_attribute("y_kick", self.SAFE_KICK)
        time.sleep(SETTLE_S)

        assert not np.allclose(baseline_beta, beta_after, rtol=1e-6), \
            "beta_x unchanged after quad write post-reset — queue loop not running"

class TestSkewQuadWriteTriggersRecalculation:
    """
    Writing to a CQLN or CQLT corrector must trigger optics recalculation.

    Physics:
      CQLN → PolynomA[1] = Ks (skew quadrupole) → introduces betatron coupling
      CQLT → PolynomB[1] = K  (normal quad component on turned octupole)

    Important: at the nominal zero-orbit state, a skew quad has no visible
    effect on uncoupled beta_x/beta_y. A non-zero closed orbit must first
    be established (via a small steerer kick) so that the coupling produces
    a measurable cross-plane orbit response in bpm_x/y and beta_x/y.

    Setup: kick AN01-AR/EM-COR/SHD.05-CDLV.13 y_kick = 1e-6 to create
    a small orbit, then write to CQLN/CQLT and observe the change.
    """

    SKEW_DELTA   = 1e-3    # 1/m — skew quad strength delta
    ORBIT_KICK   = 1e-6    # rad — small vertical kick to seed a closed orbit
    ORBIT_STEERER = "AN01-AR/EM-COR/SHD.05-CDLV.13"

    @pytest.fixture
    def dp_orbit_steerer(self):
        import tango
        dp = tango.DeviceProxy(self.ORBIT_STEERER)
        dp.ping()
        return dp

    @pytest.fixture
    def baseline(self, dp_cqln, dp_cqlt, dp_ring_sim, dp_orbit_steerer, settled):
        """
        Establish a small closed orbit via a steerer kick, then capture baseline.
        The orbit perturbation makes skew quad coupling effects visible.
        """
        _reset_if_needed(dp_ring_sim)
        # Introduce a small vertical orbit — needed for coupling to be observable
        dp_orbit_steerer.write_attribute("y_kick", self.ORBIT_KICK)
        time.sleep(SETTLE_S)
        return {
            "cqln_strength": _read(dp_cqln, "skew_quad_strength"),
            "cqlt_strength": _read(dp_cqlt, "skew_quad_strength"),
            "orbit_steerer_kick": self.ORBIT_KICK,
            "beta_x":   _arr(dp_ring_sim, "beta_x").copy(),
            "beta_y":   _arr(dp_ring_sim, "beta_y").copy(),
            "bpm_x":    _arr(dp_ring_sim, "bpm_x_attr").copy(),
            "bpm_y":    _arr(dp_ring_sim, "bpm_y_attr").copy(),
        }

    @pytest.fixture(autouse=True)
    def restore_skew_quads(self, dp_cqln, dp_cqlt, dp_ring_sim, dp_orbit_steerer, baseline):
        """Restore both correctors and the orbit steerer after each test."""
        yield
        _reset_if_needed(dp_ring_sim)
        try:
            dp_cqln.write_attribute("skew_quad_strength", baseline["cqln_strength"])
            dp_cqlt.write_attribute("skew_quad_strength", baseline["cqlt_strength"])
            dp_orbit_steerer.write_attribute("y_kick", 0.0)
            time.sleep(SETTLE_S)
        except Exception:
            pass

    def test_cqln_write_changes_optics(self, dp_cqln, dp_ring_sim, baseline):
        """
        With a non-zero closed orbit, CQLN introduces coupling visible in
        beta_x, beta_y, bpm_x_attr, or bpm_y_attr.
        """
        _write(dp_cqln, "skew_quad_strength", baseline["cqln_strength"] + self.SKEW_DELTA)

        changed = (
            not np.allclose(baseline["beta_x"], _arr(dp_ring_sim, "beta_x"), rtol=1e-6)
            or not np.allclose(baseline["beta_y"], _arr(dp_ring_sim, "beta_y"), rtol=1e-6)
            or not np.allclose(baseline["bpm_x"],  _arr(dp_ring_sim, "bpm_x_attr"), atol=1e-12)
            or not np.allclose(baseline["bpm_y"],  _arr(dp_ring_sim, "bpm_y_attr"), atol=1e-12)
        )
        assert changed, \
            "No optics changed after CQLN write — " \
            "ensure a non-zero closed orbit exists before testing skew quad coupling"

    def test_cqlt_write_changes_optics(self, dp_cqlt, dp_ring_sim, baseline):
        """
        With a non-zero closed orbit, CQLT (PolynomB[1]) acts as a normal
        quad perturbation — beta_x or beta_y must change.
        """
        _write(dp_cqlt, "skew_quad_strength", baseline["cqlt_strength"] + self.SKEW_DELTA)

        changed = (
            not np.allclose(baseline["beta_x"], _arr(dp_ring_sim, "beta_x"), rtol=1e-6)
            or not np.allclose(baseline["beta_y"], _arr(dp_ring_sim, "beta_y"), rtol=1e-6)
            or not np.allclose(baseline["bpm_x"],  _arr(dp_ring_sim, "bpm_x_attr"), atol=1e-12)
            or not np.allclose(baseline["bpm_y"],  _arr(dp_ring_sim, "bpm_y_attr"), atol=1e-12)
        )
        assert changed, \
            "No optics changed after CQLT write — " \
            "ensure a non-zero closed orbit exists before testing skew quad coupling"

    def test_cqln_independent_of_cqlt(self, dp_cqln, dp_cqlt, dp_ring_sim, baseline):
        """
        CQLN and CQLT are independent coils on the same physical octupole element.
        Writing CQLN must not change CQLT readback, and vice versa.
        """
        _write(dp_cqln, "skew_quad_strength", baseline["cqln_strength"] + self.SKEW_DELTA)

        cqlt_after = _read(dp_cqlt, "skew_quad_strength")
        assert np.isclose(cqlt_after, baseline["cqlt_strength"], atol=1e-10), \
            f"CQLT strength changed after writing CQLN: " \
            f"{baseline['cqlt_strength']} → {cqlt_after}"