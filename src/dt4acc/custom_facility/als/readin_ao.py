import json
import os
from pathlib import Path
from typing import Dict, Sequence, Tuple

import numpy as np
import pandas as pd
import xarray as xr
from scipy.io import loadmat

from bact_mml_json_importer.data_model.mml_ao import load, FamilyInfoCollection


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


def convert(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert(v) for v in obj]
    else:
        return obj

def load_ramp_data(ao_model: Dict[str, FamilyInfoCollection]) -> Dict[str, xr.Dataset]:
    path = (
        Path(os.environ["HOME"])
        / "Devel/github/matlab-middle-layer/machine/ALS//StorageRingOpsData/"
    )
    # filename = path / "Greg/alsrampup.mat"

    data = loadmat(path / "Model" /"alsrampup.mat", simplify_cells=True)
    ramp_data = data["RampTable"].copy()
    lower_lattice = ramp_data.pop("UpperLattice")
    upper_lattice = ramp_data.pop("LowerLattice")

    energies = ramp_data.pop("GeV")

    d = {
        family_name:
            create_data_array(
                t_data, energies = energies, fam_name=family_name,
                device_indices=ao_model[family_name].get_device_list()
            )
        for family_name, t_data in ramp_data.items()
    }

    return d


def als_ring_ao_data():
    filename = (
        Path(os.environ.get("HOME"))
        / "Documents"
        / "dt4acc_als_data"
        / "MML_ao_SR_250410_raw.json"
    )
    with open(filename, "r") as fp:
        data = json.load(fp)

    model = load(data["ao"])
    return model


def main():
    ao_model = als_ring_ao_data()
    ramp_data = load_ramp_data(ao_model)
    pass


if __name__ == "__main__":
    main()

