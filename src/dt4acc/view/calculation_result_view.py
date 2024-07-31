import logging
from datetime import datetime

from .create_or_update_pv import update_or_create_pv
from ..model.element_upate import ElementUpdate
from ..model.orbit import Orbit
from ..model.twiss import Twiss

# import pydev

logger = logging.getLogger("dt4acc")


class StatusFlagView:
    def __init__(self, *, prefix):
        self.prefix = prefix

    async def on_update(self, flag: bool):
        return
        if isinstance(flag, datetime):
            val = True  # or False, depending on your logic
        else:
            val = int(flag)
        await update_or_create_pv(self, self.prefix, val, 'bool', 'b')
        # pydev.iointr(self.prefix, val)
        logger.debug("sent label %s, val %s", self.prefix, val)


class ElementParameterView:
    def __init__(self, *, prefix):
        self.prefix = prefix

    async def push_value(self, elm_update: ElementUpdate):
        property_name = 'Cm:set' if 'K' in elm_update.property_name else (
            'x:set' if 'x' in elm_update.property_name else (
                'y:set' if 'dy' in elm_update.property_name else elm_update.property_name))
        label = f'{self.prefix}:{elm_update.element_id}:{property_name}'
        await update_or_create_pv(elm_update, label, elm_update.value, 'float', 'd')


class ResultView:
    def __init__(self, *, prefix):
        self.prefix = prefix

    async def push_orbit(self, orbit_result: Orbit):
        label = f"{self.prefix}:orbit:found"
        logger.warning('Orbit pushing view %s = %s type(%s)', label, orbit_result.found, type(orbit_result.found))
        await update_or_create_pv(orbit_result, label, orbit_result.found, 'bool', 'b')
        await update_or_create_pv(orbit_result, f"{self.prefix}:orbit:x", orbit_result.x, 'array', 'ad')
        await update_or_create_pv(orbit_result, f"{self.prefix}:orbit:y", orbit_result.y, 'array', 'ad')
        await update_or_create_pv(orbit_result, f"{self.prefix}:orbit:fixed_point", orbit_result.x0, 'array', 'ad')

    async def push_twiss(self, twiss_result: Twiss):
        # fmt:off
        logger.warning('Twiss pushing view')
        await update_or_create_pv(twiss_result, f"{self.prefix}:twiss:alpha:x", twiss_result.x.alpha, 'float', 'd')
        await update_or_create_pv(twiss_result, f"{self.prefix}:twiss:beta:x", twiss_result.x.beta, 'float', 'd')
        await update_or_create_pv(twiss_result, f"{self.prefix}:twiss:nu:x", twiss_result.x.nu, 'float', 'd')
        await update_or_create_pv(twiss_result, f"{self.prefix}:twiss:alpha:y", twiss_result.y.alpha, 'float', 'd')
        await update_or_create_pv(twiss_result, f"{self.prefix}:twiss:beta:y", twiss_result.y.beta, 'float', 'd')
        await update_or_create_pv(twiss_result, f"{self.prefix}:twiss:nu:y", twiss_result.y.nu, 'float', 'd')

        # pydev.iointr(f"{self.prefix}:twiss:alpha:x", twiss_result.x.alpha)
        # pydev.iointr(f"{self.prefix}:twiss:beta:x",  twiss_result.x.beta)
        # pydev.iointr(f"{self.prefix}:twiss:nu:x",    twiss_result.x.nu)

        # pydev.iointr(f"{self.prefix}:twiss:alpha:y", twiss_result.y.alpha)
        # pydev.iointr(f"{self.prefix}:twiss:beta:y",  twiss_result.y.beta)
        # pydev.iointr(f"{self.prefix}:twiss:nu:y",    twiss_result.y.nu)

        # names are not published: assuming these are identical
        # with the names that orbit publishes

        # fmt:on
        # pass

    async def push_bpms(self, bpm_result: Orbit):
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
        # pydev.iointr(f"{self.prefix}:bpm:bdata", list(bdata.ravel()))

        # pydev.iointr(f"{self.prefix}:bpm:dx", list(bpm_result.x))
        # pydev.iointr(f"{self.prefix}:bpm:dy", list(bpm_result.y))
        # pydev.iointr(f"{self.prefix}:bpm:names", [bytes(name.encode("utf8")) for name in bpm_result.names])
