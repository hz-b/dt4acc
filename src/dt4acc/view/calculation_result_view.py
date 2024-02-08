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
        pydev.iointr(label, orbit_result.found)
        pydev.iointr(f"{self.prefix}:orbit:x", orbit_result.x)
        pydev.iointr(f"{self.prefix}:orbit:y", orbit_result.y)
        label = f"{self.prefix}:names"
        logger.warning('label %s', label)
        names = [bytes(name, 'utf-8') for name in orbit_result.names]
        logger.debug('label %s = %s', label, names)
        pydev.iointr(label, names)

    def push_twiss(self, twiss_result: Twiss):
        # fmt:off
        pydev.iointr(f"{self.prefix}:twiss:x:alpha", twiss_result.x.alpha)
        pydev.iointr(f"{self.prefix}:twiss:x:beta", twiss_result.x.beta)
        pydev.iointr(f"{self.prefix}:twiss:x:nu", twiss_result.x.nu)

        pydev.iointr(f"{self.prefix}:twiss:y:alpha", twiss_result.y.alpha)
        pydev.iointr(f"{self.prefix}:twiss:y:beta", twiss_result.y.beta)
        pydev.iointr(f"{self.prefix}:twiss:y:nu", twiss_result.y.nu)

        pydev.iointr(f"{self.prefix}:twiss:names", twiss_result.names)
        # fmt:on

    def push_bpms(self, bpm_result: Orbit):
        pydev.iointr(f"{self.prefix}:bpm:x", list(bpm_result.x))
        pydev.iointr(f"{self.prefix}:bpm:y", list(bpm_result.y))
        pydev.iointr(f"{self.prefix}:bpm:names", list(bpm_result.names))
