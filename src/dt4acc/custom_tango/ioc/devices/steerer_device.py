"""
steerer_device.py
==================
Tango devices for horizontal and vertical dipole correctors (steerers).

HorizontalSteererDevice → x_kick only
VerticalSteererDevice   → y_kick only

Steerers share the UUID of their host sextupole in the AT lattice.
The property name ("x_kick" / "y_kick") routes to the correct
KickAngle index in ElementProxy._update().
"""

from tango.server import attribute, command
from tango import DevState, AttrWriteType

from dt4acc.custom_tango.ioc.devices.base_magnet_device import BaseMagnetDevice
from dt4acc.core.utils.logger import get_logger

logger = get_logger()


class HorizontalSteererDevice(BaseMagnetDevice):
    """
    Tango device for horizontal dipole correctors (CDLH, CDRH).
    Only exposes x_kick.
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

    @command
    def reset(self) -> None:
        self._x = 0.0
        logger.info("%s: reset", self.magnet_name)
        self.set_state(DevState.STANDBY)

    @command
    def RefreshFromCache(self) -> None:
        try:
            from dt4acc.custom_tango.ioc.single_server import get_nominal_values
            vals = get_nominal_values(self.lattice_id)
            self._x = vals["x_kick"]
            logger.info("%s: RefreshFromCache done — x_kick=%.6f",
                        self.magnet_name, self._x)
        except Exception as exc:
            logger.error("%s: RefreshFromCache failed: %s", self.magnet_name, exc)


class VerticalSteererDevice(BaseMagnetDevice):
    """
    Tango device for vertical dipole correctors (CDLV, CDRV).
    Only exposes y_kick.
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

    @command
    def reset(self) -> None:
        self._y = 0.0
        logger.info("%s: reset", self.magnet_name)
        self.set_state(DevState.STANDBY)

    @command
    def RefreshFromCache(self) -> None:
        try:
            from dt4acc.custom_tango.ioc.single_server import get_nominal_values
            vals = get_nominal_values(self.lattice_id)
            self._y = vals["y_kick"]
            logger.info("%s: RefreshFromCache done — y_kick=%.6f",
                        self.magnet_name, self._y)
        except Exception as exc:
            logger.error("%s: RefreshFromCache failed: %s", self.magnet_name, exc)
