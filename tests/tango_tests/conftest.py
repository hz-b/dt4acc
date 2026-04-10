"""
conftest.py
===========
Pytest configuration and shared fixtures for the dt4acc TANGO integration tango_tests.
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
        "markers", "integration: marks tango_tests as integration tango_tests (require running TANGO server)"
    )
    config.addinivalue_line(
        "markers", "slow: marks tango_tests that write to magnets and wait for recalculation"
    )
    config.addinivalue_line(
        "markers", "connectivity: marks basic device reachability tango_tests"
    )


# ---------------------------------------------------------------------------
# Device name constants (shared across test modules)
# ---------------------------------------------------------------------------

TWISS_ORBIT_DEV  = "PHYSICS/SOLEIL/TWISS_ORBIT"
BPM_DEV          = "PHYSICS/SOLEIL/BPM"
TUNE_DEV         = "PHYSICS/SOLEIL/TUNE"
MASTER_CLOCK_DEV = "PHYSICS/SOLEIL/MASTER_CLOCK"
TEST_QUAD        = "an01-ar/em/cqln.03"
TEST_STEERER_H   = "an20-ar/em/shf.06-cdlh.10"

SETTLE_S = 2.0   # seconds to wait after a write for delayed reads to propagate


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


@pytest.fixture(scope="session")
def dp_twiss_orbit():
    return _connect(TWISS_ORBIT_DEV)


@pytest.fixture(scope="session")
def dp_bpm():
    return _connect(BPM_DEV)


@pytest.fixture(scope="session")
def dp_tune():
    return _connect(TUNE_DEV)


@pytest.fixture(scope="session")
def dp_quad():
    return _connect(TEST_QUAD)


@pytest.fixture(scope="session")
def dp_steerer_h():
    return _connect(TEST_STEERER_H)


@pytest.fixture(scope="session")
def settled(dp_twiss_orbit):
    """Wait for the heartbeat to fire and push initial calculations."""
    time.sleep(SETTLE_S)
    return dp_twiss_orbit
