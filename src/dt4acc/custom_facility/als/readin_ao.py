import json
import os
from pathlib import Path

from bact_mml_json_importer.data_model.mml_ao import load


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
    als_ring_ao_data()


if __name__ == "__main__":
    main()
