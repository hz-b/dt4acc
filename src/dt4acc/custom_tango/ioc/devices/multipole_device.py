"""
multipole_device.py
========================
Tango device for Quadrupoles, Sextupoles, and Octupoles.
Exposes: magnetic_strength (READ_WRITE) + magnetic_strength_readback (READ).
"""

from tango.server import attribute, command
from tango import DevState, AttrWriteType

from dt4acc.custom_tango.ioc.devices.base_magnet_device import BaseMagnetDevice
from dt4acc.core.utils.logger import get_logger

logger = get_logger()


class MultipoleDevice(BaseMagnetDevice):
    """
    Tango device for Quadrupoles, Sextupoles, and Octupoles.
    Only exposes magnetic_strength and its readback.
    """

    def init_device(self):
        super().init_device()
        from dt4acc.custom_tango.ioc.single_server import get_initial_strength
        self._magnetic_strength = get_initial_strength(self.lattice_id)
        self._magnetic_strength_readback = self._magnetic_strength

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE,
               label="Magnetic strength", unit="1/m")
    def magnetic_strength(self) -> float:
        return self._magnetic_strength

    @magnetic_strength.write
    def magnetic_strength(self, value: float) -> None:
        value = float(value)
        self._magnetic_strength = value
        self._send("main_strength", value)
        self._magnetic_strength_readback = value

    @attribute(dtype=float, label="Magnetic strength readback", unit="1/m")
    def magnetic_strength_readback(self) -> float:
        return self._magnetic_strength_readback

    @command
    def reset(self) -> None:
        self._magnetic_strength = 0.0
        self._magnetic_strength_readback = 0.0
        logger.info("%s: reset", self.trl.as_trl())
        self.set_state(DevState.STANDBY)

    @command
    def RefreshFromCache(self) -> None:
        """Read nominal values from process-local cache after system reset."""
        try:
            from dt4acc.custom_tango.ioc.single_server import get_nominal_values
            vals = get_nominal_values(self.lattice_id)
            self._magnetic_strength = vals["main_strength"]
            self._magnetic_strength_readback = vals["main_strength"]
            logger.info("%s: RefreshFromCache done — strength=%.6f",
                        self.trl.as_trl(), self._magnetic_strength)
        except Exception as exc:
            logger.error("%s: RefreshFromCache failed: %s", self.trl.as_trl(), exc)
