import itertools

import numpy as np
import pandas as pd
import thor_scsi.lib as tslib
from thor_scsi.factory import accelerator_from_config
from pathlib import Path
import os.path

t_dir = Path(os.path.dirname(__file__))
t_file = t_dir / "b2_transferline_thor_scsi.lat"


def main():
    acc = accelerator_from_config(t_file)
    madx_table = pd.read_csv("transfer.outx", comment="@", delimiter="\s+")
    # only elements of non zero length
    if False:
        ts_elems = [elem for elem in acc if elem.get_length() != 0e0]
        madx_elems = [row for _, row in madx_table.iterrows() if row.L != 0e0]
    else:
        ts_elems = [elem for elem in acc]
        madx_elems = [row for _, row in madx_table.iterrows()]

    # Well one to many Q6 seems to be without markers
    not_added_markers = ["SEK1S12B_ENTRY"] + list(
        itertools.chain(*[(f"Q{i}MT_ENTRY", f"Q{i}MT_EXIT") for i in range(1, 13)])
    )
    eps = 1e-6
    ts_elems_iter = iter(ts_elems)
    for madx_elem in madx_elems:
        if madx_elem.NAME in not_added_markers:
            print("Ignoring element marker ", madx_elem.NAME)
            continue

        try:
            ts_elem = next(ts_elems_iter)
        except Exception as exc:
            raise exc

        if ts_elem.name != madx_elem.NAME:
            if ts_elem.name == "START":
                assert madx_elem.NAME == "TL$START"
            elif ts_elem.name == "END":
                assert madx_elem.NAME == "TL$END"
            else:
                raise AssertionError(
                    f"Not matching element names: thor scsi '{ts_elem.name}' != mad_x '{madx_elem.NAME}'"
                )

        dl = madx_elem.L - ts_elem.get_length()
        if abs(dl) > eps:
            print(ts_elem.name, ts_elem.get_length(), madx_elem.NAME, madx_elem.L)
            raise AssertionError(
                f"Not matching elements thor scsi {ts_elem}  mad_x {madx_elem}"
            )

        if isinstance(ts_elem, tslib.Quadrupole):
            # check quadrupole sign
            k1l_ts = ts_elem.get_main_multipole_strength() * ts_elem.get_length()
            k1l_madx = madx_elem.K1L
            dK = k1l_madx - k1l_ts
            if abs(dK) > eps:
                print("integrated gradient: k madx / k ts ", k1l_madx / k1l_ts)
                raise AssertionError(
                    f"Not matching elements thor scsi {repr(ts_elem)}  mad_x {madx_elem}"
                )

    # Check the bending magnets by hand
    bend_magnets = ["SEK1S12B", "SEK2S12B", "B1M1T", "B1M2T", "B2MT", "SEK1D1R", "SEK2D1R"]
    deg2rad = np.pi / 180
    for name in bend_magnets:
        bend_ts = acc.find(name, 0)
        bend_madx = madx_table.loc[madx_table.NAME == name, :]
        angles = np.array(
            [
                bend_ts.get_entrance_angle(),
                bend_ts.get_bending_angle(),
                bend_ts.get_exit_angle(),
            ]
        )
        print(bend_ts.name, bend_madx.NAME)
        print("angles thor scsi degree", angles)
        print("angles thor scsi mrad", angles * deg2rad * 1000)
        print("angle madx  mrad", bend_madx.ANGLE * 1000)
        print(repr(bend_ts))
        print(bend_madx)
        print()


if __name__ == "__main__":
    main()
