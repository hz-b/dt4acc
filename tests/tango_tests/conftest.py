"""
conftest.py
===========
Pytest configuration and shared fixtures for the dt4acc TANGO integration tests.
"""

import time
import pytest

try:
    import tango
    TANGO_AVAILABLE = True
except ImportError:
    TANGO_AVAILABLE = False


# ---------------------------------------------------------------------------
# Pytest markers
# ---------------------------------------------------------------------------

def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (require running TANGO server)"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests that write to magnets and wait for recalculation"
    )
    config.addinivalue_line(
        "markers", "connectivity: marks basic device reachability tests"
    )


# ---------------------------------------------------------------------------
# Device name constants (shared across test modules)
# ---------------------------------------------------------------------------

# Single virtual device — replaces old PHYSICS/SOLEIL/TWISS_ORBIT,
# PHYSICS/SOLEIL/BPM, and PHYSICS/SOLEIL/TUNE
RING_SIM_DEV     = "simulator/ringsimulator/ringsimulator"

# Aliases so test_01/02/03 can reference meaningful names
TWISS_ORBIT_DEV  = RING_SIM_DEV
BPM_DEV          = RING_SIM_DEV
TUNE_DEV         = RING_SIM_DEV

# Test magnet devices — a real quadrupole and horizontal steerer from the DB
TEST_QUAD        = "AN01-AR/EM-QP/QF01.01"          # MultipoleDevice (Quadrupole)
TEST_STEERER_H   = "AN01-AR/EM-COR/SHF.01-CDLH.01"  # HorizontalSteererDevice

# Skew quadrupole correctors on octupole OH.01
TEST_CQLN        = "an01-ar/em-cor/oc.01-cqln.03"   # SkewQuadDevice (CQLN → PolynomA[1], skew)
TEST_CQLT        = "an01-ar/em-cor/oc.01-cqlt.02"   # SkewQuadDevice (CQLT → PolynomB[1], normal)
TEST_OCT_HOST    = "AN01-AR/EM-OCT/OH.01"            # MultipoleDevice (host octupole)

# Steerer used for beam-loss / reset test — aggressive kick causes divergence
RESET_STEERER_H  = "AN05-AR/EM-COR/SCD.12-CDLV.07"  # VerticalSteererDevice

SETTLE_S       = 2.0    # seconds to wait after a write for delayed reads to propagate
RESET_SETTLE_S = 5.0    # longer wait after reset — lattice reload + full recalculation
STARTUP_SETTLE_S = 8.0  # wait at session start for heartbeat + first full calculation


# ---------------------------------------------------------------------------
# Session-scoped fixtures — connect once per test session
# ---------------------------------------------------------------------------

def _connect(device_name: str) -> "tango.DeviceProxy":
    if not TANGO_AVAILABLE:
        pytest.skip("PyTango not installed")
    try:
        dp = tango.DeviceProxy(device_name)
        dp.ping()
        return dp
    except Exception as exc:
        pytest.skip(f"Device {device_name} not reachable: {exc}")


def _backend_is_healthy(dp_ring_sim) -> bool:
    """
    Probe backend health by reading beta_x.
    Returns False if beta_x is placeholder (length 1) or contains non-positive values.
    """
    try:
        import numpy as np
        beta = np.asarray(dp_ring_sim.read_attribute("beta_x").value, dtype=np.float64)
        return len(beta) >= 10 and np.all(beta > 0)
    except Exception:
        return False


def _ensure_nominal(dp_ring_sim):
    """
    Ensure the backend is healthy before tests run.

    RingSimulatorDevice always reports DevState.ON even when the backend
    SimulatorBackend is in error state. We probe by reading beta_x — if it
    has only 1 element (placeholder) or is not positive, the backend hasn't
    calculated or is broken. Reset and wait for a full calculation cycle.
    """
    if not _backend_is_healthy(dp_ring_sim):
        try:
            dp_ring_sim.command_inout("Reset")
            time.sleep(RESET_SETTLE_S)
        except Exception:
            pass
    # Always wait for at least one full heartbeat calculation cycle
    time.sleep(STARTUP_SETTLE_S)


@pytest.fixture(scope="session")
def dp_ring_sim():
    """RingSimulatorDevice — single virtual device for all physics results."""
    return _connect(RING_SIM_DEV)


# Aliases — all point to the same device, kept separate for readability in tests
@pytest.fixture(scope="session")
def dp_twiss_orbit(dp_ring_sim):
    return dp_ring_sim


@pytest.fixture(scope="session")
def dp_bpm(dp_ring_sim):
    return dp_ring_sim


@pytest.fixture(scope="session")
def dp_tune(dp_ring_sim):
    return dp_ring_sim


@pytest.fixture(scope="session")
def dp_quad():
    return _connect(TEST_QUAD)


@pytest.fixture(scope="session")
def dp_steerer_h():
    return _connect(TEST_STEERER_H)


@pytest.fixture(scope="session")
def dp_reset_steerer():
    return _connect(RESET_STEERER_H)


@pytest.fixture(scope="session")
def dp_cqln():
    """CQLN skew quadrupole corrector — sets PolynomA[1] on host octupole."""
    return _connect(TEST_CQLN)


@pytest.fixture(scope="session")
def dp_cqlt():
    """CQLT turned quadrupole corrector — sets PolynomB[1] on host octupole."""
    return _connect(TEST_CQLT)


@pytest.fixture(scope="session")
def dp_oct_host():
    """Host octupole for the CQLN/CQLT correctors above."""
    return _connect(TEST_OCT_HOST)


@pytest.fixture(scope="session")
def settled(dp_ring_sim):
    """
    Session-scoped fixture that ensures the backend is healthy and
    calculations have been pushed before any test reads data.

    Resets if the backend is in error state (e.g. leftover from a previous
    test run), then waits long enough for the heartbeat to fire and push
    real twiss/orbit/tune values to RingSimulatorDevice.
    """
    _ensure_nominal(dp_ring_sim)
    return dp_ring_sim