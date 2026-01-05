from tango import DevState, DevFailed
from tango.server import Device, attribute, command, device_property, AttrWriteType

import asyncio

from ....core.utils.logger import get_logger
from ....core.bl.handlers import get_update_manager, handle_device_update
from bact_twin_architecture.data_model.identifiers import LatticeElementPropertyID
from dt4acc.custom_tango.ioc.devices.shared_event_loop import get_shared_event_loop

logger = get_logger()


def split_name(name: str):
    """Split Soleil Tango device name 'AN10-AR/EM/SCF.11'."""
    parts = name.split("/")
    if len(parts) != 3:
        raise DevFailed(f"Invalid Soleil magnet name '{name}'")
    return parts[0], parts[1], parts[2]


class MagnetDevice(Device):
    """
    FINAL, SOLEIL-CORRECT VERSION.

    Tango device name IS the lattice name:
        AN10-AR/EM/SCF.11

    Server     = AN10-AR
    Instance   = EM
    Member     = SCF.11

    ALL magnet identity comes ONLY from the Tango name.
    No DB properties required.
    """

    # Optional properties, but we do not depend on them.
    # Tango DB may or may not contain them.
    pc_name = device_property(dtype=str, default_value="")
    type = device_property(dtype=str, default_value="")

    def init_device(self):
        super().init_device()

        # Extract magnet identity from Tango device name
        full_name = self.get_name()             # e.g. AN10-AR/EM/SCF.11
        domain, family, member = split_name(full_name)

        self.magnet_name = full_name
        self.domain = domain
        self.family = family
        self.member = member

        logger.info(f"Initializing MagnetDevice: {self.magnet_name}")

        # Use shared event loop to avoid exhausting file descriptors
        self._loop = get_shared_event_loop()

        # Attempt to read main_strength; if missing fallback to 0.0
        try:
            update_manager = get_update_manager()
            val = update_manager.peek_engine(
                LatticeElementPropertyID(self.magnet_name, "main_strength")
            )
            self._magnetic_strength = float(val)
        except Exception:
            self._magnetic_strength = 0.0

        self._magnetic_strength_readback = self._magnetic_strength
        self._current = 0.0
        self._x = 0.0
        self._y = 0.0

        self.set_state(DevState.ON)

    # ------------------------------------------------------------------
    # Async helpers
    # ------------------------------------------------------------------
    def _async(self, coro):
        try:
            fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
            return fut.result(timeout=10)
        except Exception as e:
            raise DevFailed(str(e))

    # ------------------------------------------------------------------
    # Tango attributes
    # ------------------------------------------------------------------
    @attribute(dtype=float, access=AttrWriteType.READ_WRITE)
    def magnetic_strength(self):
        return self._magnetic_strength

    @magnetic_strength.write
    def magnetic_strength(self, value):
        value = float(value)
        self._magnetic_strength = value
        pc = self.pc_name or f"{self.magnet_name}-pc"     # default Soleil rule
        self._async(handle_device_update(pc, "set_current", value))
        self._magnetic_strength_readback = value

    @attribute(dtype=float)
    def magnetic_strength_readback(self):
        return self._magnetic_strength_readback

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE)
    def current(self):
        return self._current

    @current.write
    def current(self, value):
        value = float(value)
        self._current = value
        pc = self.pc_name or f"{self.magnet_name}-pc"
        self._async(handle_device_update(pc, "set_current", value))

    # Horizontal steerer kick
    @attribute(dtype=float, access=AttrWriteType.READ_WRITE)
    def x_kick(self):
        return self._x

    @x_kick.write
    def x_kick(self, value):
        self._x = float(value)
        self._async(handle_device_update(self.magnet_name, "x_kick", value))

    # Vertical steerer kick
    @attribute(dtype=float, access=AttrWriteType.READ_WRITE)
    def y_kick(self):
        return self._y

    @y_kick.write
    def y_kick(self, value):
        self._y = float(value)
        self._async(handle_device_update(self.magnet_name, "y_kick", value))

    # Reset the device state
    @command
    def reset(self):
        self._magnetic_strength = 0.0
        self._magnetic_strength_readback = 0.0
        self._current = 0.0
        self._x = 0.0
        self._y = 0.0
        logger.info(f"{self.magnet_name}: reset")
        self.set_state(DevState.STANDBY)
