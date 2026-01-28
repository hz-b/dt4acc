import logging
from typing import Sequence

import pandas as pd

from ...core.model.orbit import Orbit

logger = logging.getLogger("dt4acc")


class OrbitAtBPMS:
    """Filter orbit data and extract the points for known bpm data"""

    def __init__(self, bpm_names: Sequence[str]):
        self.bpm_names = bpm_names
        # Why do I need a prefix here?
        # self.prefix = prefix

    # def set_orbit_at_bpms(self, orbit):
    #     raise NotImplementedError("need to implement set_orbit_at_bpms")

    def extract_bpms_at_orbit(self, orbit: Orbit) -> Orbit:
        df = pd.DataFrame(index=orbit.names, data=dict(x=orbit.x, y=orbit.y))
        # as in machine orbit object: all data which are not set are marked as nan
        r = pd.DataFrame(index=self.bpm_names, columns=["x", "y"])
        idx = df.index.intersection(r.index)

        # Todo: check if BPM's are marked active
        #       if not active no data will be needed
        not_copied = r.index.difference(df.index)
        if not_copied.any():
            logger.debug("Orbit object: no data for %s", not_copied)
        r.loc[idx, ["x", "y"]] = df.loc[idx, ["x", "y"]].values
        return r
