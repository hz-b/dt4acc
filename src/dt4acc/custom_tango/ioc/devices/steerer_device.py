"""
steerer_device.py
==================
Tango devices for horizontal and vertical dipole correctors (steerers).

HorizontalSteererDevice → x_kick only
VerticalSteererDevice   → y_kick only

Steerers can share a UUID in the AT lattice. The lattice_property DB property
routes horizontal devices to B1/PolynomB[0] and vertical devices to
A1/PolynomA[0].
"""

from tango.server import attribute, command, device_property
from tango import DevState, AttrWriteType

from dt4acc.custom_tango.ioc.devices.base_magnet_device import BaseMagnetDevice
from dt4acc.core.utils.logger import get_logger

logger = get_logger()


class HorizontalSteererDevice(BaseMagnetDevice):
    """
    Tango device for horizontal dipole correctors (CDLH, CDRH).
    Only exposes x_kick.
    """
    lattice_property = device_property(dtype=str, default_value="B1")

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
        self._send(self.lattice_property, value)

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
            self._x = vals.get(self.lattice_property, 0.0)
            logger.info("%s: RefreshFromCache done — x_kick=%.6f",
                        self.trl.as_trl(), self._x)
        except Exception as exc:
            logger.error("%s: RefreshFromCache failed: %s", self.trl.as_trl(), exc)


class VerticalSteererDevice(BaseMagnetDevice):
    """
    Tango device for vertical dipole correctors (CDLV, CDRV).
    Only exposes y_kick.
    """
    lattice_property = device_property(dtype=str, default_value="A1")

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
        self._send(self.lattice_property, value)

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
            self._y = vals.get(self.lattice_property, 0.0)
            logger.info("%s: RefreshFromCache done — y_kick=%.6f",
                        self.trl.as_trl(), self._y)
        except Exception as exc:
            logger.error("%s: RefreshFromCache failed: %s", self.trl.as_trl(), exc)
