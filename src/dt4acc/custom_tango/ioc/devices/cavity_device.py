"""
cavity_device.py
=================
Tango device for RF cavities.
Exposes RF frequency and voltage.
"""

from tango.server import attribute, command
from tango import DevState, AttrWriteType

from dt4acc.custom_tango.ioc.devices.base_magnet_device import BaseMagnetDevice
from dt4acc.core.utils.logger import get_logger

logger = get_logger()


class CavityDevice(BaseMagnetDevice):
    """
    Tango device for RFCavity elements.
    Exposes frequency and voltage.
    """

    def init_device(self):
        super().init_device()
        from dt4acc.custom_tango.ioc.single_server import get_initial_value
        self._frequency = get_initial_value(self.lattice_id, "frequency")
        self._voltage = get_initial_value(self.lattice_id, "voltage")
        for attr_name in ("frequency", "voltage"):
            self.set_change_event(attr_name, True, False)

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE,
               label="Frequency", unit="Hz")
    def frequency(self) -> float:
        return self._frequency

    @frequency.write
    def frequency(self, value: float) -> None:
        value = float(value)
        self._frequency = value
        self.push_change_event("frequency", self._frequency)
        self._send("frequency", value)

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE,
               label="Voltage", unit="V")
    def voltage(self) -> float:
        return self._voltage

    @voltage.write
    def voltage(self, value: float) -> None:
        value = float(value)
        self._voltage = value
        self.push_change_event("voltage", self._voltage)
        self._send("voltage", value)

    @command
    def reset(self) -> None:
        self._frequency = 0.0
        self._voltage = 0.0
        self.push_change_event("frequency", self._frequency)
        self.push_change_event("voltage", self._voltage)
        logger.info("%s: reset", self.trl.as_trl())
        self.set_state(DevState.STANDBY)

    @command
    def RefreshFromCache(self) -> None:
        try:
            from dt4acc.custom_tango.ioc.single_server import refresh_nominal_values
            vals = refresh_nominal_values(
                self.lattice_id,
                ("frequency", "voltage"),
            )
            self._frequency = vals.get("frequency", 0.0)
            self._voltage = vals.get("voltage", 0.0)
            self.push_change_event("frequency", self._frequency)
            self.push_change_event("voltage", self._voltage)
            logger.info("%s: RefreshFromCache done — frequency=%.3f voltage=%.3f",
                        self.trl.as_trl(), self._frequency, self._voltage)
        except Exception as exc:
            logger.error("%s: RefreshFromCache failed: %s", self.trl.as_trl(), exc)
