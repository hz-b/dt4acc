import logging

import numpy as np
import pydev

logger = logging.getLogger("thor-scsi-lib")

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

        bpm_data, names = self.parent.accelerator_facade.get_bpm_data()
        logger.warning("BPM data shape: %s", bpm_data.shape)

        # Publish BPM names
        label = f"{self.prefix}-bpm-names"
        names_as_bytes = [name.encode() for name in names]
        pydev.iointr(label, names_as_bytes)

        # Publish BPM data for each plane
        for data, plane in zip(bpm_data.T, ["x", "y"]):
            label = f"{self.prefix}-bpm.d{plane}"
            logger.debug("BPM data for plane %s: %s", plane, list(data))
            pydev.iointr(label, list(data))

        # Build BPM data together
        n_channels = 128
        n_used, _ = bpm_data.shape
        bdata_prepare = np.zeros((8, n_channels), dtype=np.float)
        # x plane .. simulated position
        bdata_prepare[0, :n_used] = bpm_data[:, 0]
        # y plane .. simulated position
        bdata_prepare[1, :n_used] = bpm_data[:, 1]
        # x rms ... next vector ?
        # todo: what is a reasonable value
        bdata_prepare[6, :n_used] = 1
        # y rms ... next vector ?
        # todo: what is a reasonable value
        bdata_prepare[7, :n_used] = 1
        # todo: find good default values for intensity (z, s) stat and gain raw
        bdata = bdata_prepare.reshape(-1)

        bdata_all = np.zeros((2048,), dtype=np.float)
        bdata_all[:len(bdata)] = bdata

        # Publish BPM data
        label = f"{self.prefix}-bpm-bdata"
        pydev.iointr(label, list(bdata_all))
