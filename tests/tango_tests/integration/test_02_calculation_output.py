"""
test_02_calculation_output.py
==============================
Verify that the backend calculations (twiss, orbit, tune) are computed
and pushed to the virtual TANGO devices after the heartbeat fires.

These tests only READ — they do not write to any magnet.
They depend on the heartbeat being active and having fired at least once.
"""

import time
import pytest
import numpy as np

pytestmark = pytest.mark.integration


def _arr(dp, attr: str) -> np.ndarray:
    return np.asarray(dp.read_attribute(attr).value, dtype=np.float64)


class TestOrbitData:
    """TwissOrbitDevice must publish a valid orbit after heartbeat fires."""

    @pytest.fixture(autouse=True)
    def wait_for_heartbeat(self, settled, dp_ring_sim):
        """Ensure heartbeat has fired before reading."""
        pass

    def test_orbit_x_is_not_all_zeros(self, dp_ring_sim):
        arr = _arr(dp_ring_sim, "orbit_x")
        assert len(arr) >= 10, "orbit_x array too short"
        assert not np.all(arr == 0.0), \
            "orbit_x is all zeros — calculation not pushed to TwissOrbitDevice"

    def test_orbit_y_is_finite_and_correct_length(self, dp_ring_sim):
        """
        orbit_y is legitimately all-zeros at nominal operating point
        (no vertical errors or kicks). Just verify it's finite and the right length.
        """
        arr = _arr(dp_ring_sim, "orbit_y")
        assert len(arr) >= 10, "orbit_y array too short"
        assert np.all(np.isfinite(arr)), "orbit_y contains NaN or Inf"

    def test_orbit_x_is_finite(self, dp_ring_sim):
        arr = _arr(dp_ring_sim, "orbit_x")
        assert np.all(np.isfinite(arr)), "orbit_x contains NaN or Inf"

    def test_orbit_y_is_finite(self, dp_ring_sim):
        arr = _arr(dp_ring_sim, "orbit_y")
        assert np.all(np.isfinite(arr)), "orbit_y contains NaN or Inf"

    def test_orbit_x_y_same_length(self, dp_ring_sim):
        x = _arr(dp_ring_sim, "orbit_x")
        y = _arr(dp_ring_sim, "orbit_y")
        assert len(x) == len(y), \
            f"orbit_x length {len(x)} != orbit_y length {len(y)}"


class TestTwissData:
    """TwissOrbitDevice must publish valid Twiss parameters."""

    @pytest.fixture(autouse=True)
    def wait_for_heartbeat(self, settled, dp_ring_sim):
        pass

    def test_beta_x_is_positive(self, dp_ring_sim):
        arr = _arr(dp_ring_sim, "beta_x")
        assert len(arr) >= 10, "beta_x array too short"
        assert np.all(arr > 0), \
            f"beta_x has non-positive values (min={arr.min():.4f})"

    def test_beta_y_is_positive(self, dp_ring_sim):
        arr = _arr(dp_ring_sim, "beta_y")
        assert len(arr) >= 10, "beta_y array too short"
        assert np.all(arr > 0), \
            f"beta_y has non-positive values (min={arr.min():.4f})"

    def test_alpha_x_is_finite(self, dp_ring_sim):
        arr = _arr(dp_ring_sim, "alpha_x")
        assert np.all(np.isfinite(arr)), "alpha_x contains NaN or Inf"

    def test_alpha_y_is_finite(self, dp_ring_sim):
        arr = _arr(dp_ring_sim, "alpha_y")
        assert np.all(np.isfinite(arr)), "alpha_y contains NaN or Inf"

    def test_nu_x_is_monotonically_increasing(self, dp_ring_sim):
        arr = _arr(dp_ring_sim, "nu_x")
        assert len(arr) >= 10
        diffs = np.diff(arr)
        assert np.all(diffs >= 0), \
            f"nu_x not monotonically increasing — max decrease: {diffs.min():.6f}"

    def test_nu_y_is_monotonically_increasing(self, dp_ring_sim):
        arr = _arr(dp_ring_sim, "nu_y")
        assert len(arr) >= 10
        diffs = np.diff(arr)
        assert np.all(diffs >= 0), \
            f"nu_y not monotonically increasing — max decrease: {diffs.min():.6f}"

    def test_all_twiss_arrays_same_length(self, dp_ring_sim):
        lengths = {
            attr: len(_arr(dp_ring_sim, attr))
            for attr in ("beta_x", "beta_y", "alpha_x", "alpha_y", "nu_x", "nu_y")
        }
        unique = set(lengths.values())
        assert len(unique) == 1, f"Twiss array length mismatch: {lengths}"

    def test_twiss_and_orbit_same_length(self, dp_ring_sim):
        orbit_len = len(_arr(dp_ring_sim, "orbit_x"))
        twiss_len = len(_arr(dp_ring_sim, "beta_x"))
        assert orbit_len == twiss_len, \
            f"orbit_x length {orbit_len} != beta_x length {twiss_len}"


class TestBPMData:
    """BPMManagerDevice must publish BPM readings derived from orbit."""

    @pytest.fixture(autouse=True)
    def wait_for_heartbeat(self, settled, dp_ring_sim):
        pass

    def test_bpm_names_not_empty(self, dp_ring_sim):
        names = dp_ring_sim.read_attribute("bpm_names_attr").value
        assert names is not None and len(names) > 0, \
            "bpm_names_attr is empty — orbit not pushed to BPMManagerDevice"

    def test_bpm_names_are_bpm_elements(self, dp_ring_sim):
        names = dp_ring_sim.read_attribute("bpm_names_attr").value
        non_bpm = [n for n in names if not n.upper().startswith("BPM")]
        assert len(non_bpm) == 0, \
            f"Non-BPM element names in bpm_names_attr: {non_bpm[:5]}"

    def test_bpm_x_is_finite(self, dp_ring_sim):
        arr = _arr(dp_ring_sim, "bpm_x_attr")
        assert len(arr) > 0, "bpm_x_attr is empty"
        assert np.all(np.isfinite(arr)), "bpm_x_attr contains NaN or Inf"

    def test_bpm_y_is_finite(self, dp_ring_sim):
        arr = _arr(dp_ring_sim, "bpm_y_attr")
        assert len(arr) > 0, "bpm_y_attr is empty"
        assert np.all(np.isfinite(arr)), "bpm_y_attr contains NaN or Inf"

    def test_bpm_arrays_consistent_length(self, dp_ring_sim):
        x     = _arr(dp_ring_sim, "bpm_x_attr")
        y     = _arr(dp_ring_sim, "bpm_y_attr")
        names = dp_ring_sim.read_attribute("bpm_names_attr").value
        assert len(x) == len(y) == len(names), \
            f"BPM length mismatch: x={len(x)}, y={len(y)}, names={len(names)}"


class TestTuneData:
    """TuneDevice must publish non-zero fractional tune values."""

    @pytest.fixture(autouse=True)
    def wait_for_heartbeat(self, settled, dp_ring_sim):
        pass

    def test_tune_hor_is_nonzero(self, dp_ring_sim):
        val = float(dp_ring_sim.read_attribute("hor").value)
        assert val != 0.0, "tune.hor is zero — tune not pushed to TuneDevice"

    def test_tune_vert_is_nonzero(self, dp_ring_sim):
        val = float(dp_ring_sim.read_attribute("vert").value)
        assert val != 0.0, "tune.vert is zero — tune not pushed to TuneDevice"

    def test_tune_hor_is_finite(self, dp_ring_sim):
        val = float(dp_ring_sim.read_attribute("hor").value)
        assert np.isfinite(val), f"tune.hor is not finite: {val}"

    def test_tune_vert_is_finite(self, dp_ring_sim):
        val = float(dp_ring_sim.read_attribute("vert").value)
        assert np.isfinite(val), f"tune.vert is not finite: {val}"

    def test_tune_fractional_part_in_range(self, dp_ring_sim):
        """Fractional part of tune must be in (0, 1)."""
        hor  = float(dp_ring_sim.read_attribute("hor").value) % 1.0
        vert = float(dp_ring_sim.read_attribute("vert").value) % 1.0
        assert 0.0 < hor  < 1.0, f"tune.hor fractional part out of (0,1): {hor}"
        assert 0.0 < vert < 1.0, f"tune.vert fractional part out of (0,1): {vert}"