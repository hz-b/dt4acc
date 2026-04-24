import asyncio

import numpy as np
from dt4acc_lib.model.utils.command import ReadCommand, BehaviourOnError, Command
from tango import DevState, DevFailed
from tango.server import Device, attribute, device_property, AttrWriteType

from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_tango.ioc.devices.shared_event_loop import get_shared_event_loop
from dt4acc.custom_tango.ioc.controller_registry import get_controller

logger = get_logger()


def split_name(name: str):
    parts = name.split("/")
    if len(parts) != 3:
        raise DevFailed(f"Invalid Tango PC name '{name}'")
    return parts[0], parts[1], parts[2]


class PowerConverterDevice(Device):
    """
    Tango device representing a power converter.

    Device name IS the power converter identifier:
        AN10-AR/EM/SCF.11-pc

    All identity is derived from the Tango device name.
    No DB properties are required.

    Write handlers delegate to TangoController.update(), which:
      1. calls mexec.set([cmd]) to mutate the backend lattice
      2. queues delayed reads (track/pos, twiss/parameters, tune/x, tune/y)
         so orbit/twiss recalculation fires automatically after each set.
    """

    magnet_list = device_property(dtype=(str,), default_value=[])

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def init_device(self):
        super().init_device()
        self.set_state(DevState.INIT)

        full_name = self.get_name()
        domain, family, member = split_name(full_name)
        self.pc_name = full_name

        logger.info("Initializing PowerConverterDevice: %s", self.pc_name)

        self._loop = get_shared_event_loop()

        # Fetch initial current setpoint from the backend via the controller.
        # Falls back to 0.0 if the backend does not know this PC yet.
        self._current = self._peek_initial_current()
        self._current_rb = self._current
        self._voltage = 0.0

        self.set_state(DevState.ON)

    def _peek_initial_current(self) -> float:
        """Read set_current from the backend at startup."""
        try:
            result = self._async(
                get_controller().trigger_read(
                    [ReadCommand(id=self.pc_name, property="set_current")]
                )
            )
            readings = result.all_readings()
            if readings:
                val = readings[0].payload
                if isinstance(val, (list, np.ndarray)):
                    return float(np.mean(val))
                return float(val)
        except Exception as exc:
            logger.warning(
                "%s: could not read initial set_current: %s — defaulting to 0.0",
                self.pc_name, exc,
            )
        return 0.0

    # ------------------------------------------------------------------
    # Async helper
    # ------------------------------------------------------------------

    def _async(self, coro):
        try:
            fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
            return fut.result(timeout=10)
        except Exception as exc:
            raise DevFailed(str(exc))

    # ------------------------------------------------------------------
    # Tango attributes
    # ------------------------------------------------------------------

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE,
               label="Current setpoint", unit="A")
    def current_set(self) -> float:
        return self._current

    @current_set.write
    def current_set(self, value: float) -> None:
        value = float(value)
        self._current = value
        self._current_rb = value
        self._async(
            get_controller().update(
                cmd=Command(
                    id=self.pc_name,
                    property="set_current",
                    value=value,
                    behaviour_on_error=BehaviourOnError.stop,
                ),
                reads=[],
                delayed_reads=[],
            )
        )

    @attribute(dtype=float, label="Current readback", unit="A")
    def current_readback(self) -> float:
        return self._current_rb

    @attribute(dtype=float, label="Voltage readback", unit="V")
    def voltage(self) -> float:
        return self._voltage
