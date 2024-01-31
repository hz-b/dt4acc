import pydev

from src.dt4acc.model.orbit import Orbit
from src.dt4acc.model.twiss import Twiss


class ResultView:
    def __init__(self, *, prefix):
        self.prefix = prefix

    def push_orbit(self, orbit_result: Orbit):
        pydev.iointr(f"{self.prefix}:orbit:found", orbit_result.found)
        pydev.iointr(f"{self.prefix}:orbit:x", orbit_result.x)
        pydev.iointr(f"{self.prefix}:orbit:y", orbit_result.y)
        pydev.iointr(f"{self.prefix}:orbit:names", orbit_result.names)

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
