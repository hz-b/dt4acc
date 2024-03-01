import logging

import pydev


from ..model.element_upate import ElementUpdate
from ..model.orbit import Orbit
from ..model.twiss import Twiss

logger = logging.getLogger("dt4acc")


class ElementParameterView:
    def __init__(self, *, prefix):
        self.prefix = prefix

    def push_value(self, elm_update: ElementUpdate):
        label = f'{self.prefix}:{elm_update.element_id}:{elm_update.property_name}'
        logger.debug('label: %s = %s', label, elm_update.value)
        pydev.iointr(label, elm_update.value)


class ResultView:
    def __init__(self, *, prefix):
        self.prefix = prefix

    def push_orbit(self, orbit_result: Orbit):
        label = f"{self.prefix}:orbit:found"
        logger.warning('label %s = %s type(%s)', label, orbit_result.found, type(orbit_result.found))
        pydev.iointr(label, bool(orbit_result.found))
        pydev.iointr(f"{self.prefix}:orbit:x", orbit_result.x)
        pydev.iointr(f"{self.prefix}:orbit:y", orbit_result.y)
        label = f"{self.prefix}:names"
        logger.warning('label %s', label)
        names = [bytes(name, 'utf-8') for name in orbit_result.names]
        logger.debug('label %s = %s', label, names)
        pydev.iointr(label, names)

    def push_twiss(self, twiss_result: Twiss):
        # fmt:off
        pydev.iointr(f"{self.prefix}:twiss:alpha:x", twiss_result.x.alpha)
        pydev.iointr(f"{self.prefix}:twiss:beta:x",  twiss_result.x.beta)
        pydev.iointr(f"{self.prefix}:twiss:nu:x",    twiss_result.x.nu)

        pydev.iointr(f"{self.prefix}:twiss:alpha:y", twiss_result.y.alpha)
        pydev.iointr(f"{self.prefix}:twiss:beta:y",  twiss_result.y.beta)
        pydev.iointr(f"{self.prefix}:twiss:nu:y",    twiss_result.y.nu)

        # names are not published: assuming these are identical
        # with the names that orbit publishes

        # fmt:on

    def push_bpms(self, bpm_result: Orbit):
        """
        Todo:
            implement that data is pushed to bdata
            or make it unnecssary ...

        Warning:
            Current implementation is broken
        """
        import numpy as np

        n_entries = 128
        n_found = len(bpm_result.x)
        bdata = np.zeros([8, n_entries], dtype=float)
        bdata[0, :n_found] = bpm_result.x
        bdata[1, :n_found] = bpm_result.y
        label = f"{self.prefix}:bpm:bdata"
        data = list(bdata.ravel())
        pydev.iointr(label, data)
        logger.warning("Published bdata using label %s, n data %s, data[:10] %s",
                       label, len(data), data[:10])

        return

        pydev.iointr(f"{self.prefix}:bpm:x", list(bpm_result.x))
        pydev.iointr(f"{self.prefix}:bpm:y", list(bpm_result.y))
        pydev.iointr(f"{self.prefix}:bpm:names", list(bpm_result.names))

