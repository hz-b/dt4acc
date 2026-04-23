"""
skew_quad_device.py
===================
Tango device for skew quadrupole correctors (CQLN, CQLT) mounted
as secondary coils on octupoles.

Exposes: skew_quad_strength only.
    CQLN → PolynomA[1] (skew quad, coupling corrector)
    CQLT → PolynomB[1] (turned normal quad corrector)

The UUID stored in the DB is "CQLN:<host_uuid>" or "CQLT:<host_uuid>",
which routes to SkewQuadCorrectorProxy in accelerator_simulator.get().
"""

from tango.server import attribute, command
from tango import DevState, AttrWriteType

from dt4acc.custom_tango.ioc.devices.base_magnet_device import BaseMagnetDevice
from dt4acc.core.utils.logger import get_logger

logger = get_logger()


class SkewQuadDevice(BaseMagnetDevice):
    """
    Tango device for CQLN/CQLT skew quadrupole correctors on octupoles.
    Only exposes skew_quad_strength.
    """

    def init_device(self):
        super().init_device()
        self._skew_quad_strength = 0.0

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE,
               label="Skew quadrupole strength", unit="1/m")
    def skew_quad_strength(self) -> float:
        return self._skew_quad_strength

    @skew_quad_strength.write
    def skew_quad_strength(self, value: float) -> None:
        value = float(value)
        self._skew_quad_strength = value
        self._send("skew_quad_strength", value)

    @command
    def reset(self) -> None:
        self._skew_quad_strength = 0.0
        logger.info("%s: reset", self.magnet_name)
        self.set_state(DevState.STANDBY)

    @command
    def RefreshFromCache(self) -> None:
        try:
            from dt4acc.custom_tango.ioc.single_server import get_nominal_values
            vals = get_nominal_values(self.lattice_id)
            self._skew_quad_strength = vals.get("skew_quad_strength", 0.0)
            logger.info("%s: RefreshFromCache done — skew_quad_strength=%.6f",
                        self.magnet_name, self._skew_quad_strength)
        except Exception as exc:
            logger.error("%s: RefreshFromCache failed: %s", self.magnet_name, exc)
