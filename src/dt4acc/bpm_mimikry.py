import logging

import numpy as np
import pydev
import pandas as pd

logger = logging.getLogger("dt4acc")

#: todo: needs to be imported from database
from bact_bessyii_ophyd.devices.pp import bpm_parameters
from bact_device_models.filters.bpm_calibration import BPMCalibrationPlane

# one fits all ...
calib = BPMCalibrationPlane()

class BPMMimikry:
    """
    Combine data from individual BPMs as expected at the BESSY II machine.

    Mimics the bpm IOCs of the BESSSY II machine.
    """

    def __init__(self, parent, prefix):
        """
        Initialize BPMMimikry object.

        Args:
            parent: The parent object.
            prefix (str): The prefix for the EPICS channel names.
        """
        self.prefix = prefix
        self.parent = parent
        # bpm_offsets= self.parent.accelerator_facade.get_bpm_data()
        self.bpm_config = bpm_parameters.create_bpm_config()
        indices = self.bpm_config['idx']
        n_channels = 128
        df =pd.DataFrame(
            columns=["name", "idx",  "x", "y", "intensity_z", "intensity_s", "stat", "gain_raw", "x_rms", "y_rms"],
            index=np.arange(n_channels)
            )

        # a few lions all over Africa but none as the other
        df.idx = np.arange(n_channels) * -1000 - 1
        df.name = [f"not_set_value_{cnt}_XXX" for cnt in range(n_channels)]
        df.name[indices] = self.bpm_config['name']
        # todo: check if the indices I assume currently are correct
        df.idx[indices] = indices
        df = df.set_index("name")
        self.bpm_prep = df



    def publish_bpm_data(self, orbit_result):
        """
        Publish BPM data to EPICS.

        Args:
            orbit_result (OrbitResult): Result of the orbit calculation.

        Raises:
            AssertionError: If no orbit data is found.
        """
        if orbit_result is None:
            raise AssertionError("Orbit data not found.")

        if not orbit_result.found_closed_orbit:
            logger.warning("No valid orbit!")
            return

        bpm_offsets = self.parent.accelerator_facade.get_bpm_data()
        logger.debug("BPM data shape: %s, %s", bpm_offsets.shape, bpm_offsets.index)

        # Publish BPM names
        label = f"{self.prefix}-bpm-names"
        names_as_bytes = [name.encode() for name in bpm_offsets.index.values]
        pydev.iointr(label, names_as_bytes)

        # Publish BPM data for each plane
        for data, plane in zip(bpm_offsets.T, ["x", "y"]):
            label = f"{self.prefix}-bpm.d{plane}"
            logger.debug("BPM data for plane %s: %s", plane, list(data))
            pydev.iointr(label, list(data))

        # Build BPM data together
        n_used, _ = bpm_offsets.shape

        df = self.bpm_prep.copy()

        # select only the ones that are marked as valid ... so there must be an index
        # set to them
        machine_bpm_not_in_model = set(df.index[df.idx>=0]).difference(bpm_offsets.index)
        if len(machine_bpm_not_in_model):
            logger.warning("Bpms in machine but not in model: %s", machine_bpm_not_in_model)
        else:
            logger.debug("All bpm's of machine are also in model")
        # todo:  check that name sorting is not making an issue
        common_names = set(bpm_offsets.index).intersection(df.index)
        common_names = list(common_names)
        common_names.sort()

        # pd.DataFrame.apply()
        # recalculate BPM values to bits, use same scale for all
        bpm_o_phys = bpm_offsets.loc[common_names, ["x", "y"]]
        bpm_o_eng = bpm_o_phys.copy()
        if False:
             bpm_o_eng.loc[:,  ["x", "y"]] = bpm_o_phys.loc[:, ["x", "y"]].apply(
                 lambda v: calib.to_bits(v)
             )
             df.loc[:, ["x", "y"]] += bpm_o_eng
        else:
            # df.loc[:, ["x", "y"]] = bpm_o_eng
            pass
        df.x_rms = .6
        df.y_rms = .7
        df.stat = 0
        df.loc[df.idx > 0, "stat"] = 1.0
        df.loc[:, "gain_raw"] = .5
        # todo: find good default values for intensity (z, s) stat and gain raw
        df.loc[:, "intensity_z"] = .2
        df.loc[:, "intensity_s"] = .3


        bdata_prepare = df.loc[:,  df.columns[1:]].values
        bdata_prepare = np.array(bdata_prepare, dtype=float)

        # prepare the data to be compatible in vector to what
        # the control system exports
        bdata = bdata_prepare.transpose().ravel()
        bdata_all = np.zeros((2048,), dtype=float)
        bdata_all[:len(bdata)] = bdata

        # Publish BPM data
        label = f"{self.prefix}-bpm-bdata"
        pydev.iointr(label, list(bdata_all))
