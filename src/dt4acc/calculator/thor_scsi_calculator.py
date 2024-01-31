import logging
from abc import ABCMeta

import gtpsa
import numpy as np
from thor_scsi.utils.accelerator import extract_orbit_from_accelerator_with_standard_observers
from thor_scsi.utils.closed_orbit import compute_closed_orbit
from thor_scsi.utils.linear_optics import compute_Twiss_along_lattice

logger = logging.getLogger("thor-scsi-lib")
from ..interfaces.calculation_interface import TwissCalculator, OrbitCalculator
from ..model.orbit import Orbit
from ..model.twiss import Twiss, TwissForPlane


class ThorScsiTwissCalculator(TwissCalculator, metaclass=ABCMeta):
    def __init__(self, conf, mapping, acc):
        self.conf = conf
        self.acc = acc
        self.mapping = mapping

    def calculate(self) -> Twiss:
        # Implement calculation using Thor_scsi
        desc = gtpsa.desc(6, 1)
        r = compute_Twiss_along_lattice(2, self.acc, self.conf, desc=desc,
                                        mapping=self.mapping)
        nu_x = np.add.accumulate(r.twiss.sel(plane="x", par="dnu").values)
        nu_y = np.add.accumulate(r.twiss.sel(plane="y", par="dnu").values)
        return Twiss(
            x=TwissForPlane(alpha=r.twiss.sel(plane="x", par="alpha").values, beta=r.twiss.sel(plane="x", par="beta").values, nu=nu_x),
            y=TwissForPlane(alpha=r.twiss.sel(plane="y", par="alpha").values, beta=r.twiss.sel(plane="y", par="beta").values, nu=nu_y),
            names=r.names.values
        )


class ThorScsiOrbitCalculator(OrbitCalculator, metaclass=ABCMeta):
    def __init__(self, conf, mapping, acc):
        self.delta = 0.0
        self.x0 = None
        self.eps = 1e-8
        self.max_iter = 10
        self.result = None
        self.acc = acc
        self.mapping = mapping
        self.conf = conf

    def calculate(self) -> Orbit:
        # Implement calculation using Thor_scsi
        # Determine whether delta and x0 need to be set
        desc = gtpsa.desc(6, 1)
        logger.debug("Before calculating: last stored result %s eps = %s", self.result, self.eps)
        if self.result is None or not np.isfinite(self.result.x0.iloc).all():
            delta = 0.0
            x0 = None
        else:
            delta = None
            x0 = self.result.x0

        # start with last settings
        px0 = None
        if x0 is not None:
            px0 = x0 * 1000
        logger.warning("Calculating orbit with x0 * 1000 = %s for eps %s", px0, self.eps)
        del px0

        try:
            # Call compute_closed_orbit with the appropriate arguments
            self.result = compute_closed_orbit(
                self.acc,
                self.conf,
                x0=x0,
                delta=delta,
                max_iter=self.max_iter,
                eps=self.eps,
                # mapping=mapping,
                desc=desc,
            )
        except Exception as e:
            # Log a warning message and re-raise the exception
            logger.warning(f"eps {self.eps}")
            raise e

        # Check whether a closed orbit was found
        if not self.result.found_closed_orbit:
            raise ValueError("No closed orbit was found")

        # Calculate the orbit using the updated result object
        self.orbit = extract_orbit_from_accelerator_with_standard_observers(self.acc)
        logger.warning(f"Calculated Orbit x0 * 1000 = %s for eps %s", self.result.x0 * 1000, self.eps)

        # return self.result
        return Orbit(
            x=self.orbit.ps.sel(phase_coordinate="x").values,
            y=self.orbit.ps.sel(phase_coordinate="y").values,
            names=self.orbit.names.values,
            found=self.result.found_closed_orbit,
            x0= self.result.x0
        )
