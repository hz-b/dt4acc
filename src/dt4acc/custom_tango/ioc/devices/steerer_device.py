"""
steerer_device.py
==================
Tango devices for horizontal and vertical dipole correctors (steerers).

HorizontalSteererDevice exposes x_kick and magnetic_strength.
VerticalSteererDevice exposes y_kick and magnetic_strength.

Steerers can share the UUID of their host multipole in the AT lattice.
The public attribute names ("x_kick" / "y_kick") are kept for compatibility,
but the backend stores them through the host dipolar strength:
angle = atan(strength), strength = tan(angle), using PolynomB[0] for horizontal
and PolynomA[0] for vertical correctors when those arrays exist.
"""

import math

from tango.server import attribute, command
from tango import DevState, AttrWriteType

from dt4acc.custom_tango.ioc.devices.base_magnet_device import BaseMagnetDevice
from dt4acc.core.utils.logger import get_logger

logger = get_logger()


class HorizontalSteererDevice(BaseMagnetDevice):
    """
    Tango device for horizontal dipole correctors (CDLH, CDRH).
    """

    def init_device(self):
        super().init_device()
        self._x = 0.0

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE,
               label="Horizontal kick", unit="rad")
    def x_kick(self) -> float:
        return self._x

    @x_kick.write
    def x_kick(self, value: float) -> None:
        value = float(value)
        self._x = value
        self._send("x_kick", value)

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE,
               label="Magnetic strength")
    def magnetic_strength(self) -> float:
        return math.tan(self._x)

    @magnetic_strength.write
    def magnetic_strength(self, value: float) -> None:
        self._x = math.atan(float(value))
        self._send("x_kick", self._x)

    @command
    def reset(self) -> None:
        self._x = 0.0
        logger.info("%s: reset", self.trl.as_trl())
        self.set_state(DevState.STANDBY)

    @command
    def RefreshFromCache(self) -> None:
        try:
            from dt4acc.custom_tango.ioc.single_server import get_nominal_values
            vals = get_nominal_values(self.lattice_id)
            self._x = vals["x_kick"]
            logger.info("%s: RefreshFromCache done — x_kick=%.6f",
                        self.trl.as_trl(), self._x)
        except Exception as exc:
            logger.error("%s: RefreshFromCache failed: %s", self.trl.as_trl(), exc)


class VerticalSteererDevice(BaseMagnetDevice):
    """
    Tango device for vertical dipole correctors (CDLV, CDRV).
    """

    def init_device(self):
        super().init_device()
        self._y = 0.0

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE,
               label="Vertical kick", unit="rad")
    def y_kick(self) -> float:
        return self._y

    @y_kick.write
    def y_kick(self, value: float) -> None:
        value = float(value)
        self._y = value
        self._send("y_kick", value)

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE,
               label="Magnetic strength")
    def magnetic_strength(self) -> float:
        return math.tan(self._y)

    @magnetic_strength.write
    def magnetic_strength(self, value: float) -> None:
        self._y = math.atan(float(value))
        self._send("y_kick", self._y)

    @command
    def reset(self) -> None:
        self._y = 0.0
        logger.info("%s: reset", self.trl.as_trl())
        self.set_state(DevState.STANDBY)

    @command
    def RefreshFromCache(self) -> None:
        try:
            from dt4acc.custom_tango.ioc.single_server import get_nominal_values
            vals = get_nominal_values(self.lattice_id)
            self._y = vals["y_kick"]
            logger.info("%s: RefreshFromCache done — y_kick=%.6f",
                        self.trl.as_trl(), self._y)
        except Exception as exc:
            logger.error("%s: RefreshFromCache failed: %s", self.trl.as_trl(), exc)
