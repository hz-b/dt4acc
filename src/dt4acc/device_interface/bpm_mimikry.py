import logging

import pandas as pd

from ..model.orbit import Orbit

logger = logging.getLogger("dt4acc")

#: todo: needs to be imported from database
from bact_device_models.filters.bpm_calibration import BPMCalibrationPlane

# one fits all ..
calib = BPMCalibrationPlane()


class BPMMimikry:
    """
    Combine data from individual BPMs as expected at the BESSY II machine.

    Mimics the bpm IOCs of the BESSSY II machine.
    """

    def __init__(self, *, prefix, bpm_names):
        """
        Initialize BPMMimikry object.

        Args:
            parent: The parent object.
            prefix (str): The prefix for the EPICS channel names.
        """
        self.prefix = prefix
        self.bpm_names = bpm_names

    def extract_bpm_data(self, orbit_result: Orbit):
        """
        Publish BPM data to EPICS.

        Args:
            orbit_result (OrbitResult): Result of the orbit calculation.

        Raises:
            AssertionError: If no orbit data is found.
        """
        if orbit_result is None:
            raise AssertionError("Orbit data not found.")

        if not orbit_result.found:
            logger.warning("No valid orbit!")
            return

        # find indices where the names are ..
        df = pd.DataFrame(index=["x", "y"], columns=orbit_result.names, data=[orbit_result.x, orbit_result.y]).T
        # todo: where shall one handle the conversion form etter to nano meters?
        df_bpm = df.loc[self.bpm_names, :]
        return Orbit(x=df_bpm.x.values, y=df_bpm.y.values, names=df_bpm.index.values, found=orbit_result.found, x0=orbit_result.x0)
