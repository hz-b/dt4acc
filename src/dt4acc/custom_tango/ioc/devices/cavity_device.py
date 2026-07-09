"""
cavity_device.py
=================
Tango device for RF cavities.
Exposes: frequency and voltage.
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
        self._frequency = 0.0
        self._voltage = 0.0
        self._refresh_from_cache()

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE,
               label="Frequency", unit="Hz")
    def frequency(self) -> float:
        return self._frequency

    @frequency.write
    def frequency(self, value: float) -> None:
        value = float(value)
        self._frequency = value
        self._send("frequency", value)

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE,
               label="Voltage", unit="V")
    def voltage(self) -> float:
        return self._voltage

    @voltage.write
    def voltage(self, value: float) -> None:
        value = float(value)
        self._voltage = value
        self._send("voltage", value)

    @command
    def reset(self) -> None:
        self._frequency = 0.0
        self._voltage = 0.0
        logger.info("%s: reset", self.magnet_name)
        self.set_state(DevState.STANDBY)

    @command
    def RefreshFromCache(self) -> None:
        self._refresh_from_cache()

    def _refresh_from_cache(self) -> None:
        try:
            from dt4acc.custom_tango.ioc.mexec_server_for_physics_engine import _connect_to_mexec_service
            from dt4acc.custom_tango.ioc.single_server import get_nominal_values

            vals = get_nominal_values(self.lattice_id)
            self._frequency = vals.get("frequency", 0.0)
            self._voltage = vals.get("voltage", 0.0)

            sync_proxy, _, _ = _connect_to_mexec_service()
            raw = sync_proxy.sync_trigger_read(
                [self.lattice_id, self.lattice_id],
                ["frequency", "voltage"],
            )
            for _rcmd_id, rcmd_prop, payload in raw:
                if payload is None:
                    continue
                if rcmd_prop == "frequency":
                    self._frequency = float(payload)
                elif rcmd_prop == "voltage":
                    self._voltage = float(payload)

            logger.info("%s: RefreshFromCache done — frequency=%.3f voltage=%.3f",
                        self.magnet_name, self._frequency, self._voltage)
        except Exception as exc:
            logger.error("%s: RefreshFromCache failed: %s", self.magnet_name, exc)
