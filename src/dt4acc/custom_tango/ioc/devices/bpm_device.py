"""
bpm_device.py
=============

Dedicated Tango device for one BPM.

The device name comes from accelerator_setup.json, for example:
    AN01-AR/DG-EPOS/BPM.02
The element_uuid property links it to the BPM UUID in the AT lattice, for
example BPM_002.
"""

import asyncio

from tango import DevFailed, DevState
from tango.server import AttrWriteType, Device, attribute, device_property

from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_tango.ioc.controller_registry import get_controller
from dt4acc.custom_tango.ioc.devices.shared_event_loop import get_shared_event_loop

logger = get_logger()

ASYNC_READ_TIMEOUT_S = 5.0


class BpmDevice(Device):
    """Read-only BPM position device backed by the shared MexecService cache."""

    element_uuid = device_property(dtype=str, default_value="")

    def init_device(self):
        super().init_device()
        self.set_state(DevState.INIT)
        self.lattice_id = self.element_uuid or self.get_name().split("/")[-1]
        self._loop = get_shared_event_loop()
        self._last_x = 0.0
        self._last_y = 0.0
        self.set_change_event("x", True, False)
        self.set_change_event("y", True, False)
        self.set_state(DevState.ON)
        logger.debug("Initialized BpmDevice %s lattice_id=%s", self.get_name(), self.lattice_id)

    def _async(self, coro):
        try:
            fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
            return fut.result(timeout=ASYNC_READ_TIMEOUT_S)
        except Exception as exc:
            raise DevFailed(str(exc))

    def _read_position(self):
        valid, x, y = self._async(get_controller().mexec.bpm_position(self.lattice_id))
        if valid:
            self._last_x = float(x)
            self._last_y = float(y)
            self.set_state(DevState.ON)
        else:
            self.set_state(DevState.UNKNOWN)
        return self._last_x, self._last_y

    @attribute(dtype=float, access=AttrWriteType.READ, label="Horizontal position")
    def x(self) -> float:
        x, _ = self._read_position()
        return x

    @attribute(dtype=float, access=AttrWriteType.READ, label="Vertical position")
    def y(self) -> float:
        _, y = self._read_position()
        return y
