"""
cavity_device.py
=================
Tango device for RF cavities.
Exposes: frequency only.
"""

from tango.server import attribute, command
from tango import DevState, AttrWriteType

from dt4acc.custom_tango.ioc.devices.base_magnet_device import BaseMagnetDevice
from dt4acc.core.utils.logger import get_logger

logger = get_logger()


class CavityDevice(BaseMagnetDevice):
    """
    Tango device for RFCavity elements.
    Only exposes frequency.
    """

    def init_device(self):
        super().init_device()
        self._frequency = 0.0

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE,
               label="Frequency", unit="Hz")
    def frequency(self) -> float:
        return self._frequency

    @frequency.write
    def frequency(self, value: float) -> None:
        value = float(value)
        self._frequency = value
        self._send("frequency", value)

    @command
    def reset(self) -> None:
        self._frequency = 0.0
        logger.info("%s: reset", self.trl.as_trl())
        self.set_state(DevState.STANDBY)

    @command
    def RefreshFromCache(self) -> None:
        try:
            from dt4acc.custom_tango.ioc.single_server import get_nominal_values
            vals = get_nominal_values(self.lattice_id)
            self._frequency = vals.get("frequency", 0.0)
            logger.info("%s: RefreshFromCache done — frequency=%.3f",
                        self.trl.as_trl(), self._frequency)
        except Exception as exc:
            logger.error("%s: RefreshFromCache failed: %s", self.trl.as_trl(), exc)
