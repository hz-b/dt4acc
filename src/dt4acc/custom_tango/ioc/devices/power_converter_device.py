from tango import DevState, DevFailed
from tango.server import Device, attribute, device_property, AttrWriteType
import numpy as np
import asyncio

from dt4acc.core.utils.logger import get_logger
from dt4acc.core.bl.handlers import get_update_manager, handle_device_update
from bact_twin_architecture.data_model.identifiers import DevicePropertyID
from dt4acc.custom_tango.ioc.devices.shared_event_loop import get_shared_event_loop

logger = get_logger()


def split_name(name: str):
    parts = name.split("/")
    if len(parts) != 3:
        raise DevFailed(f"Invalid Soleil Tango PC name '{name}'")
    return parts[0], parts[1], parts[2]


class PowerConverterDevice(Device):
    """
    FINAL, SOLEIL-CORRECT VERSION.

    Tango name e.g.:
        AN10-AR/EM/SCF.11-pc

    ALL identity derived from device name.
    Tango properties optional.
    """

    magnet_list = device_property(dtype=(str,), default_value=[])

    def init_device(self):
        super().init_device()

        full_name = self.get_name()
        domain, family, member = split_name(full_name)
        self.pc_name = full_name

        logger.info(f"Initializing PowerConverterDevice: {self.pc_name}")

        # Use shared event loop to avoid exhausting file descriptors
        self._loop = get_shared_event_loop()

    
        try:
            update_manager = get_update_manager()
            val = update_manager.device_value_from_peeking_engine(
                DevicePropertyID(self.pc_name, "set_current")
            )
            if isinstance(val, (list, np.ndarray)):
                self._current = float(np.mean(val))
            else:
                self._current = float(val)
        except Exception:
            self._current = 0.0

        self._current_rb = self._current
        self._voltage = 0.0

        self.set_state(DevState.ON)

    # ------------------------- Attributes -------------------------

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE)
    def current_set(self):
        return self._current

    @current_set.write
    def current_set(self, value):
        value = float(value)
        self._current = value
        self._current_rb = value
        self._async_update("set_current", value)

    @attribute(dtype=float)
    def current_readback(self):
        return self._current_rb

    @attribute(dtype=float)
    def voltage(self):
        return self._voltage

    # ------------------------------------------------------------------
    # Async helpers
    # ------------------------------------------------------------------
    def _async(self, coro):
        try:
            fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
            return fut.result(timeout=10)
        except Exception as e:
            raise DevFailed(str(e))

    # ------------------------- Helpers -------------------------

    def _async_update(self, prop, value):
        try:
            self._async(handle_device_update(self.pc_name, prop, value))
        except Exception as e:
            raise DevFailed(str(e))
