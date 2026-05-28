"""

Check that the managers are built for the same configuration
that the data have been exported for

Todo:
    add the mode to the data
"""
from __future__ import annotations

import logging
from pathlib import Path
import pytest

from dt4acc.custom_facility.als.liaison_translator_setup import load_managers
from dt4acc.custom_facility.als.mml_exported_data_model import ReferenceCurvesForFamily
from dt4acc_lib.model.utils.identifiers import DevicePropertyID

logger = logging.getLogger("dt4acc-als-test")

yp, lm, ts, pvs = load_managers()

data_dir = Path(__file__).parent / "data" / "reference_curves"

# Optional: keep this if you want to assert specific families should exist.
# If you do not want that behaviour, leave it as None.
expected_families =  ["HCM", "VCM", "QF", "QD", "QFA",  "QDA"]


def _family_file(family_name: str) -> Path:
    func_name = "amp2k"
    channel_name = "Setpoint"
    return data_dir / f"reference_test_data_{family_name}_{func_name}_{channel_name}.json"


def _available_family_files() -> list[Path]:
    return sorted(data_dir.glob("*.json"))


@pytest.fixture(scope="module")
def reference_data(request) -> ReferenceCurvesForFamily:
    data_file: Path = request.param

    if not data_file.exists():
        pytest.skip(f"Missing reference data file: {data_file}")

    return ReferenceCurvesForFamily.model_validate_json(
        data_file.read_text(encoding="utf-8")
    )


def pytest_generate_tests(metafunc):
    if "reference_data" not in metafunc.fixturenames:
        return

    if expected_families is None:
        files = _available_family_files()
    else:
        files = [_family_file(fam) for fam in expected_families]

    if not files:
        pytest.skip(f"No reference curve files found in {data_dir}")

    metafunc.parametrize("reference_data", files, indirect=True)


def test_reference_file_schema(reference_data: ReferenceCurvesForFamily):
    assert len(reference_data.curves) > 0

    for reference_curve in reference_data.curves:
        assert reference_curve.channel_name
        assert reference_curve.reference_function_name
        assert reference_curve.device_id.family
        assert len(reference_curve.curve) > 0


def test_amp2k_matches_matlab_reference(reference_data: ReferenceCurvesForFamily):
    for reference_curve in reference_data.curves:
        # Todo: track down the correct translation object
        device = reference_curve.device_id
        dev_index = [device.sector, device.child]

        dev_prop = DevicePropertyID(reference_curve.channel_name, "set_current")
        convs = ts.objects_for_device(reference_curve.pv_name.strip())
        conv_id, = convs.keys()
        to = ts.get(conv_id)
        for point in reference_curve.curve:
            actual = float(to.inverse(point.indep))
            pass
            try:
                assert actual == pytest.approx(point.dep, rel=1e-7, abs=1e-7)
                # That is perhaps to harsh for extrapolation
                # assert actual == pytest.approx(point.dep, rel=1e-12, abs=1e-12)
            except:
                logger.error(f"Test failed for {reference_curve.device_id} {reference_curve.channel_name} {reference_curve.pv_name}")
                raise
