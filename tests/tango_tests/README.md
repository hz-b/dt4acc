# dt4acc TANGO Integration Tests

## Prerequisites

- TANGO server running (`python server_manager.py`)
- `TANGO_HOST` set (e.g. `export TANGO_HOST=localhost:10000`)
- PyTango installed in your venv

## Structure

```
tests/
├── conftest.py               # fixtures, markers, device name constants
├── test_01_connectivity.py   # are all devices reachable?
├── test_02_calculation_output.py  # are twiss/orbit/tune being pushed?
└── test_03_end_to_end.py     # does a magnet write trigger recalculation?
```

## Running

```bash
# All tango_tests
pytest -v

# Only connectivity (fast, no writes)
pytest -v -m connectivity

# Only output checks (reads only, waits for heartbeat)
pytest -v tango_tests/test_02_calculation_output.py

# Full end-to-end (writes to magnets)
pytest -v -m slow

# Stop on first failure
pytest -v -x

# With live log output
pytest -v --log-cli-level=WARNING
```

## Test descriptions

### test_01_connectivity
Verifies all devices are registered, exported, and in ON state.
Checks that each device exposes its expected attributes.
**Fast — no writes, no waits.**

### test_02_calculation_output
Verifies the backend calculations are being pushed to virtual devices.
Reads orbit_x/y, beta_x/y, alpha_x/y, nu_x/y from TwissOrbitDevice.
Reads BPM data from BPMManagerDevice.
Reads tune from TuneDevice.
**Read-only — waits for heartbeat to fire (2s settle time).**

### test_03_end_to_end
Writes small perturbations to a quadrupole and steerer.
Verifies that orbit, twiss, and tune change as expected.
Verifies that restoring the magnet restores the orbit.
**Writes to magnets — uses autouse fixtures to always restore.**
