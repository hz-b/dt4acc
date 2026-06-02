import json
import logging
import os
from pathlib import Path
from typing import Dict, Sequence, Tuple

import numpy as np
import pandas as pd
import scipy.io.matlab
import xarray as xr
from scipy.io import loadmat

from bact_mml_json_importer.data_model.mml_ao import load, FamilyInfoCollection

logger = logging.getLogger("dt4acc-custom-als")

def create_data_array(
    t_data: Dict[str, Sequence[float]],
    energies: Sequence[float],
    fam_name: str,
    device_indices: Sequence[Tuple[int, int]]
) -> xr.Dataset:

    dev_idx = pd.MultiIndex.from_tuples(device_indices, names=["sector", "child"])


    setp_da = xr.DataArray(
        data=t_data["Setpoint"], dims="reference_energy", coords=[energies],
    )

    ph_da = xr.DataArray(
        # What are these data: I guess some reference point data
        data=t_data["Physics"],
        dims=["device_list"],
        coords={
            "sector": ("device_list", [c[0] for c in device_indices]),
            "child": ("device_list", [c[1] for c in device_indices]),
        },
        attrs=dict(family=fam_name, reference_energy=dict(unit="GeV")),
    )
    pass

    r = xr.Dataset(
        dict(setpoint=setp_da, physics=ph_da,
             device_indices=xr.Coordinates.from_pandas_multiindex(dev_idx, dim="device_list")
        ),
        attrs=dict(family=fam_name),
    )
    return r


def create_ranges(*, family_name: str, upper_limit, lower_limit, field_name, ao_table) -> xr.DataArray:
    """
    Todo:
        need to simplify that returned data!
    """
    sel_ao = ao_table[family_name]
    # field_name can be used in a double manner only for field_name "Setpoint" or "Monitor"

    sel_up = upper_limit[field_name][family_name][field_name]
    sel_low = lower_limit[field_name][family_name][field_name]

    dev_list = ao_table[family_name].get_device_list()
    assert (sel_low["DeviceList"] == dev_list).all()
    assert (sel_up["DeviceList"] == dev_list).all()

    xr.DataArray(
        data=[sel_up["Data"], sel_low["Data"]],
        dims=["range", "device_list"],
        coords={
            "range": ["upper", "lower"],
            "sector": ("device_list", [c[0] for c in dev_list]),
            "child": ("device_list", [c[0] for c in dev_list]),
        },
    )
    r = xr.DataArray(
        data=[sel_up["Data"],sel_low["Data"]],
        dims=["range", "device_list"],
        coords={
            "range": ["upper", "lower"],
            "sector": ("device_list", [c[0] for c in dev_list]),
            "child": ("device_list", [c[1] for c in dev_list]),
        },
    )
    return r


def convert(obj):
    if isinstance(obj, scipy.io.matlab.MatlabFunction):
        return convert(obj.tolist())
    elif isinstance(obj, scipy.io.matlab.mat_struct):
        r = {name: convert(getattr(obj, name)) for name in obj._fieldnames}
        return r
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert(v) for v in obj]
    elif isinstance(obj, (str, int, float)):
        # for debugging remove this branch for production
        return obj
    else:
        return obj

default_data_dir = (
        Path(os.environ["HOME"])
        / "Devel/github/matlab-middle-layer/machine/ALS//StorageRingOpsData/"
    )

def load_loco_data(ao_model: Dict[str, FamilyInfoCollection])-> Dict[str, xr.Dataset]:
    data = loadmat(default_data_dir / "PseudoSingleBunch" / "LOCO_Production.mat", simplify_cells=True)
    data


def load_ramp_data(ao_model: Dict[str, FamilyInfoCollection]) -> Dict[str, xr.Dataset]:
    # filename = path / "Greg/alsrampup.mat"
    filename = os.environ.get("DT4ACC_ALS_RAMP_MAT_FILE", None)
    if filename is None:
        default_filename = default_data_dir / "PseudoSingleBunch" / "alsrampup.mat"
        logger.warning(
            f"No DT4ACC_ALS_RAMP_MAT_FILE environment variable defined using {default_filename}"
        )
        filename = default_filename


    data = loadmat(filename, simplify_cells=True)
    # data = loadmat(path / "Model" /"alsrampdown.mat", simplify_cells=True)
    # data = loadmat(path / "Model" /"alsrampup.mat", simplify_cells=True)
    ramp_data = data["RampTable"].copy()
    lower_limit = ramp_data.pop("UpperLattice")
    upper_limit = ramp_data.pop("LowerLattice")

    energies = ramp_data.pop("GeV")

    d = {
        family_name:
            create_data_array(
                t_data, energies = energies, fam_name=family_name,
                device_indices=ao_model[family_name].get_device_list()
            )
        for family_name, t_data in ramp_data.items()
    }

    ranges = {
        family_name: create_ranges(family_name=family_name, field_name="Setpoint", upper_limit=upper_limit, lower_limit=lower_limit, ao_table=ao_model)
        for family_name in ramp_data.keys()
    }

    def add_ranges(ds: xr.Dataset, ranges: xr.DataArray) -> xr.Dataset:
        nds = ds.copy()
        nds["range"] = ranges
        return nds

    d2 = {
        family_name: add_ranges(ds, ranges[family_name])
        for family_name, ds in d.items()
    }

    return d2


def als_ring_ao_data():
    t_dir =    filename = (
        Path(os.environ.get("HOME"))
        / "Documents"
        / "dt4acc_als_data"
    )

    filename = os.environ.get("DT4ACC_ALS_AO_MAT_FILE", None)
    if filename is None:
        default_filename = t_dir / "ao_as_loaded_from_mml.mat"
        logger.warning(
            f"No DT4ACC_ALS_AO_MAT_FILE environment variable defined using {default_filename}"
        )
        filename = default_filename
    data_from_mat = loadmat(filename, simplify_cells=True)
    tmp = convert(data_from_mat["AO"])
    model = load(tmp)
    return model
    pass

    # as received by Thorsten
    filename = t_dir / "MML_ao_SR_250410_raw.json"
    with open(filename, "r") as fp:
        data = json.load(fp)

    model = load(data["ao"])

    return model


def main():
    ao_model = als_ring_ao_data()
    loco_data = load_loco_data(ao_model)
    ramp_data = load_ramp_data(ao_model)
    pass


if __name__ == "__main__":
    main()

