import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Dict

import itertools

from bact_mml_json_importer.data_model.mml_ao import load


@dataclass(frozen=True)
class FunctionHandlerInfo:
    func_name: str
    file_name: str
    type: str
    used_for: str



def handler(d: Dict[str, Dict[str, str]], used_for: str) -> FunctionHandlerInfo:
    if d is None:
        return None
    func_name = d["function_handle"]["function"]
    file_name = d["function_handle"]["file"]
    type=d["function_handle"]["type"]
    return FunctionHandlerInfo(
        func_name=func_name, file_name=file_name, type=type, used_for=used_for
    )


def extract_function_handler_functions_for_channel(
        data: Dict[
            str, Dict[
                str, Dict[str, str]
            ]
        ]
) -> Sequence[FunctionHandlerInfo]:
    if data is None:
        return []
    r1 = handler(data.get("HW2PhysicsFcn"), "H->P")
    r2 = handler(data.get("Physics2HWFcn"), "P->H")
    return [r1, r2]


def extract_function_handler_functions_for_device(
    data: Dict[
        str, Dict[
            str, Dict[
                str, Dict[str, str]
            ]
        ]
    ]
) -> Sequence[FunctionHandlerInfo]:
    return (
            extract_function_handler_functions_for_channel(data.get("Monitor")) +
            extract_function_handler_functions_for_channel(data.get("Setpoint"))
    )


def extract_function_handler_functions(data):
    r = {
        fam_name: extract_function_handler_functions_for_device(data[fam_name])
        for fam_name, family in data.items()
    }
    unique_converters = [
        t for t in
        set(itertools.chain.from_iterable(r.values())) if t is not None
    ]
    return r


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