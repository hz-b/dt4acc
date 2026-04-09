from tango import DevState, DevFailed
from tango.server import Device, attribute, command, device_property, AttrWriteType

import asyncio

from accml_lib.core.model.utils.command import Command, BehaviourOnError, ReadCommand
from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_tango.ioc.devices.shared_event_loop import get_shared_event_loop
from dt4acc.custom_tango.ioc.controller_registry import get_controller

logger = get_logger()


def split_name(name: str):
    """Split Soleil Tango device name 'AN10-AR/EM/SCF.11'."""
    parts = name.split("/")
    if len(parts) != 3:
        raise DevFailed(f"Invalid Soleil magnet name '{name}'")
    return parts[0], parts[1], parts[2]


class MagnetDevice(Device):
    """
    Tango device representing a single accelerator magnet.

    Device name IS the lattice element name:
        AN10-AR/EM/SCF.11

    Domain   = server name  (AN10-AR)
    Family   = instance name (EM)
    Member   = element name  (SCF.11)

    All magnet identity comes only from the Tango device name.
    No DB properties are required.

    Write handlers delegate to TangoController.update(), which:
      1. calls mexec.set([cmd]) to mutate the backend lattice
      2. queues delayed reads (track/pos, twiss/parameters, tune/x, tune/y)
         which trigger orbit/twiss/tune recalculation and push results
         to TwissOrbitDevice, BPMManagerDevice, TuneDevice.
    """

    # Optional — set in DB if power converter name differs from the default rule.
    # Default rule: pc_name = "{magnet_name}-pc"
    pc_name = device_property(dtype=str, default_value="")
    type    = device_property(dtype=str, default_value="")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def init_device(self):
        super().init_device()
        self.set_state(DevState.INIT)

        full_name = self.get_name()   # e.g. AN10-AR/EM/SCF.11
        domain, family, member = split_name(full_name)

        self.magnet_name = full_name
        self.domain = domain
        self.family = family
        self.member = member

        logger.info("Initializing MagnetDevice: %s", self.magnet_name)

        self._loop = get_shared_event_loop()

        # Fetch initial main_strength from the backend via the controller.
        # Falls back to 0.0 if the backend does not yet know this element.
        self._magnetic_strength = self._peek_initial_strength()
        self._magnetic_strength_readback = self._magnetic_strength
        self._current = 0.0
        self._x = 0.0
        self._y = 0.0

        self.set_state(DevState.ON)

    def _peek_initial_strength(self) -> float:
        """Read main_strength from the backend at startup."""
        try:
            result = self._async(
                get_controller().trigger_read(
                    [ReadCommand(id=self.magnet_name, property="main_strength")]
                )
            )
            readings = result.all_readings()
            if readings:
                return float(readings[0].payload)
        except Exception as exc:
            logger.warning(
                "%s: could not read initial main_strength: %s — defaulting to 0.0",
                self.magnet_name, exc,
            )
        return 0.0

    # ------------------------------------------------------------------
    # Async helper — submits a coroutine to the shared event loop and
    # blocks until it completes. Converts exceptions to DevFailed so
    # Tango clients receive a proper error.
    # ------------------------------------------------------------------

    def _async(self, coro):
        try:
            fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
            return fut.result(timeout=10)
        except Exception as exc:
            raise DevFailed(str(exc))

    # ------------------------------------------------------------------
    # Helper: resolve the power converter name for this magnet
    # ------------------------------------------------------------------

    def _pc(self) -> str:
        """Return the power converter name for this magnet."""
        return self.pc_name if self.pc_name else f"{self.magnet_name}-pc"

    # ------------------------------------------------------------------
    # Tango attributes
    # ------------------------------------------------------------------

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE,
               label="Magnetic strength", unit="1/m")
    def magnetic_strength(self) -> float:
        return self._magnetic_strength

    @magnetic_strength.write
    def magnetic_strength(self, value: float) -> None:
        value = float(value)
        self._magnetic_strength = value
        self._async(
            get_controller().update(
                cmd=Command(
                    id=self._pc(),
                    property="set_current",
                    value=value,
                    behaviour_on_error=BehaviourOnError.stop,
                ),
                reads=[],
                # default_delayed_reads in controller handles twiss/orbit/tune
                delayed_reads=[],
            )
        )
        self._magnetic_strength_readback = value

    @attribute(dtype=float, label="Magnetic strength readback", unit="1/m")
    def magnetic_strength_readback(self) -> float:
        return self._magnetic_strength_readback

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE,
               label="Current setpoint", unit="A")
    def current(self) -> float:
        return self._current

    @current.write
    def current(self, value: float) -> None:
        value = float(value)
        self._current = value
        self._async(
            get_controller().update(
                cmd=Command(
                    id=self._pc(),
                    property="set_current",
                    value=value,
                    behaviour_on_error=BehaviourOnError.stop,
                ),
                reads=[],
                delayed_reads=[],
            )
        )

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE,
               label="Horizontal kick", unit="rad")
    def x_kick(self) -> float:
        return self._x

    @x_kick.write
    def x_kick(self, value: float) -> None:
        value = float(value)
        self._x = value
        self._async(
            get_controller().update(
                cmd=Command(
                    id=self.magnet_name,
                    property="x_kick",
                    value=value,
                    behaviour_on_error=BehaviourOnError.stop,
                ),
                reads=[],
                delayed_reads=[],
            )
        )

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE,
               label="Vertical kick", unit="rad")
    def y_kick(self) -> float:
        return self._y

    @y_kick.write
    def y_kick(self, value: float) -> None:
        value = float(value)
        self._y = value
        self._async(
            get_controller().update(
                cmd=Command(
                    id=self.magnet_name,
                    property="y_kick",
                    value=value,
                    behaviour_on_error=BehaviourOnError.stop,
                ),
                reads=[],
                delayed_reads=[],
            )
        )

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    @command
    def reset(self) -> None:
        """Reset all setpoints to zero and go to STANDBY."""
        self._magnetic_strength = 0.0
        self._magnetic_strength_readback = 0.0
        self._current = 0.0
        self._x = 0.0
        self._y = 0.0
        logger.info("%s: reset", self.magnet_name)
        self.set_state(DevState.STANDBY)
