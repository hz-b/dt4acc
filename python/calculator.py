from thor_scsi.utils.linear_optics import compute_Twiss_along_lattice
import numpy as np
import logging
from thor_scsi.utils.closed_orbit import compute_closed_orbit
from thor_scsi.utils.accelerator import (
    extract_orbit_from_accelerator_with_standard_observers,
)
import gtpsa

# there are some memory management problems in thor scsi
desc = gtpsa.desc(6, 2)

logger = logging.getLogger("thor-scsi-lib")

class Calculator:
    def __init__(self, parent):
        # Check that the parent has the attributes required
        assert(parent.acc)
        assert(parent.conf)
        assert(parent.mapping)
        self.parent = parent
        self.result = None

class TwissCalculator(Calculator):
    def calculate(self):
        n_dof = 2
        self.result = compute_Twiss_along_lattice(n_dof, self.parent.acc, self.parent.conf, desc=desc,
                                                  mapping=self.parent.mapping)
        return self.result


class OrbitCalculator(Calculator):
    def __init__(self, delta=0.0, x0=None, eps=1e-8, max_iter=10, **kwargs):
        super().__init__(**kwargs)
        self.delta = delta
        self.x0 = x0
        self.eps = eps
        self.max_iter = max_iter

    def set_epsilon(self, eps):
        # Convert eps to float and check if it is greater than 0.0
        eps = float(eps)
        threshold = 1e-17
        if eps > threshold:
            pass
        else:
            raise ValueError(f"{eps=} must be > {threshold}")

        self.eps = eps

        self.eps = 1e-15
        logger.warning(f"got {eps=} forced to {self.eps} ")

    def get_epsilon(self):
        return self.eps

    def calculate(self, *, mapping, desc=None):
        # Determine whether delta and x0 need to be set
        logger.info(f"Before calculating: last stored result {self.result=} eps = {self.eps}")
        if self.result is None or not np.isfinite(self.result.x0.iloc).all():
            delta = 0.0
            x0 = None
        else:
            delta = None
            x0 = self.result.x0

        # start alw
        try:
            # Call compute_closed_orbit with the appropriate arguments
            self.result = compute_closed_orbit(
                self.parent.acc,
                self.parent.conf,
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
        self.orbit = extract_orbit_from_accelerator_with_standard_observers(self.parent.acc)
        logger.warning(f"Calculated Orbit x0 * 1000 = {self.result.x0 * 1000} for eps {self.eps}")

        return self.result
