import functools
import logging
from typing import Sequence

import numpy as np
import pandas as pd
from bact_device_models.devices.bpm_elem_libera import BPMElement, BPMElementPosition, BPMElementList
from bact_device_models.filters.bpm_calibration import BPMCalibrationPlane

from . import bpm_config
from ..model.orbit import Orbit

logger = logging.getLogger("dt4acc")

#: todo: needs to be imported from database

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
        return BPMElementList([
            BPMElement(name=name,
                       pos=BPMElementPosition(x=df.loc[name, "x"], y=df.loc[name, "y"]),
                       sig=None)
            for name in self.bpm_names
        ])

    def extract_bpm_legacy_data(self, orbit_result: Orbit):
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
        bpm_config = create_bpm_config()

        # find indices where the names are ..
        df = pd.DataFrame(index=["x", "y"], columns=orbit_result.names, data=[orbit_result.x, orbit_result.y]).T
        bpm_names_as_index = pd.Series([f"empty_{cnt:03d}" for cnt in np.arange(128)])
        bpm_names_as_index.iloc[bpm_config["idx"]] = bpm_config["name"]
        df_bpm = pd.DataFrame(columns=["x", "y", "intensity_z", "intensity_s", "status", "x_rms", "y_rms"],
                              index=bpm_names_as_index)

        # Waring: order is lost!!!
        known_bpm_names = list(set(bpm_config["name"]).intersection(orbit_result.names))
        assert len(known_bpm_names) > 1
        assert df_bpm.shape[0] == 128

        # default values
        fill_value = 2**15
        df_bpm.loc[:, "x"] = fill_value
        df_bpm.loc[:, "y"] = fill_value
        df_bpm.loc[:, "y_rms"] = 0
        df_bpm.loc[:, "x_rms"] = 0
        df_bpm.loc[:, "status"] = 0

        # flipping coordinate system to get the dispersion on the correct side
        # todo: check at which state this should be done
        # fmt:off
        m2mm = 1e3
        sel = df.loc[known_bpm_names, :]
        df_bpm.loc[known_bpm_names, "x"] = sel.x * m2mm
        df_bpm.loc[known_bpm_names, "y"] = sel.y * m2mm
        df_bpm.loc[:, "status"] = 0
        df_bpm.loc[known_bpm_names, "status"] = 3

        # needs to be at least a bit in 16 ...
        df_bpm.loc[known_bpm_names, "x_rms"] = 1
        df_bpm.loc[known_bpm_names, "y_rms"] = 1


        tmp = np.empty([len(df_bpm), 8], dtype=np.int16)
        tmp.fill(0)
        mm2cnts = 2 ** 15 / 10

        # todo : clip the values
        def convert(vec):
            r = np.clip(-2 ** 15, 2 ** 15, vec * mm2cnts)
            return r.astype(np.int16)

        tmp[:, 0] = convert(df_bpm.x)
        tmp[:, 1] = convert(df_bpm.y)
        tmp[:, 4] = df_bpm.status
        tmp[:, 6] = convert(df_bpm.x_rms)
        tmp[:, 7] = convert(df_bpm.y_rms)
        bpm_legacy_data_vector = np.zeros([2048], np.int16)
        bpm_legacy_data_vector[:1024] = tmp.transpose().ravel()

        return bpm_legacy_data_vector


@functools.lru_cache(maxsize=1)
def create_bpm_config():
    '''Beam position monitor as an array of records

    The calculation from BPM readings to physical data is handled by
    :class:`ophyd.devices.utils.derived_signal.DerivedSignalLinearBPM`

    Returns:
         a structured numpy array

    The returned array contains the following entries:
        * `name`: name of the beam position monitor
        * `x_state`: scale in x axis
        * `y_state`: scale in y axis
        * `ds`:      s position in the ring
        * `x_scale`: scale in x axis
        * `y_scale`: scale in y axis
        * `x_offset`: offset in x axis
        * `y_offset`: offset in y axis

    Todo:
       Discuss how x_scale and y_scale should be handled.

       Rationale: bluesky/ophyd considers the transformation from raw data to
                  physics data as an inverse operation. Thus standard operation
                  would be for the forward operation:

                  ..math::

                       raw_value = scale $\cdot$ physics_value + offset

                  BESSY II standard approach is to use the equation above as
                  a mapping from raw_value to physics_value.
    '''

    # fmt: off
    t_names = ['name', 'x_state', 'y_state',  's',   'idx']
    formats = ['U20',   np.bool_,  np.bool_,  float,  int]
    t_names += ['x_scale', 'y_scale', 'x_offset', 'y_offset']
    formats += [float,      float,     float,      float]
    # fmt: on
    dtypes = np.dtype({'names':  t_names, 'formats': formats})

    n_bpms = len(bpm_config.bpm_conf)
    data = np.zeros((n_bpms,), dtype=dtypes)
    for i in range(n_bpms):
        entry = bpm_config.bpm_conf[i]
        no_offset = (0, 0)
        data[i] = entry + no_offset

    del entry, i, n_bpms

    # The scale factors are stored as multipliers ...
    # The BPM class expects them as deviders
    data['x_scale'] = 1 / data['x_scale']
    data['y_scale'] = 1 / data['y_scale']

    for name in bpm_config.bpm_offset.keys():
        x_offset, y_offset = bpm_config.bpm_offset[name]

        idx = data['name'] == name
        line = data[idx]
        assert(name == line['name'])

        line['x_offset'] = x_offset
        line['y_offset'] = y_offset
        data[idx] = line

    del idx, x_offset, y_offset, line, name
    # deselect deactivated bpms
    valid_bpms = data['x_state'] & data['y_state']
    reduced_bpms = data[valid_bpms]
    del data

    # only valid bpms beyond this point
    assert(sum(reduced_bpms['x_state']) == reduced_bpms.shape[0])
    assert(sum(reduced_bpms['x_state']) == reduced_bpms.shape[0])

    s_sort = np.argsort(reduced_bpms['s'])
    sorted_bpms = np.take(reduced_bpms, s_sort)
    del s_sort
    del reduced_bpms

    # data start counting at one ... need to use count at zero
    # compatible with python
    sorted_bpms['idx'] -= 1
    return sorted_bpms