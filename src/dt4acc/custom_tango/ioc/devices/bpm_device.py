"""
bpm_device.py
=============

Read-only Tango device for a single Beam Position Monitor.

Subscribes to change events on RingSimulatorDevice.orbit_x / orbit_y
and caches its own x/y by index. No polling of the backend — one event
subscription per BPM, values updated on every heartbeat calculation.

Attributes (read-only, polled every 1s from local cache):
    x   — horizontal closed-orbit position at this BPM [m]
    y   — vertical closed-orbit position at this BPM [m]
"""

from tango import DevState, DevDouble, EventType
from tango.server import Device, attribute, device_property
from tango import DeviceProxy

from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_tango.ioc.devices.virtual_devices import RING_SIM_DEV

logger = get_logger()


class BPMDevice(Device):
    """Read-only Tango device for a single BPM.
    Subscribes to orbit change events from RingSimulatorDevice.
    """

    lattice_id  = device_property(dtype=str, default_value="")
    s_pos       = device_property(dtype=float, default_value=0.0)
    orbit_index = device_property(dtype=int, default_value=-1)

    def init_device(self):
        super().init_device()
        self._x = 0.0
        self._y = 0.0
        self._event_ids = []
        self._ringsim = None
        self._subscribed = False
        self.set_state(DevState.ON)
        logger.info("Initializing BPMDevice: %s lattice_id=%s orbit_index=%d",
                    self.get_name(), self.lattice_id, self.orbit_index)
        self._subscribe_orbit_events()

    def always_executed_hook(self):
        """Retry subscription if not yet connected — ringsimulator may not
        have been running when init_device was called."""
        if not self._subscribed:
            self._subscribe_orbit_events()

    def _subscribe_orbit_events(self):
        """Subscribe to orbit_x / orbit_y change events on RingSimulatorDevice.
        Called at init and retried via always_executed_hook until successful."""
        try:
            logger.info("BPMDevice %s: subscribing to %s orbit events (index=%d s_pos=%.3f)",
                        self.get_name(), RING_SIM_DEV, self.orbit_index, self.s_pos)
            ringsim = DeviceProxy(RING_SIM_DEV)
            ringsim.set_timeout_millis(3000)
            eid_x = ringsim.subscribe_event(
                "orbit_x", EventType.CHANGE_EVENT, self._on_orbit_x
            )
            eid_y = ringsim.subscribe_event(
                "orbit_y", EventType.CHANGE_EVENT, self._on_orbit_y
            )
            self._event_ids = [eid_x, eid_y]
            self._ringsim = ringsim  # keep reference alive
            self._subscribed = True
            logger.info("BPMDevice %s: subscribed OK (eid_x=%s eid_y=%s)",
                        self.get_name(), eid_x, eid_y)
        except Exception as exc:
            logger.debug("BPMDevice %s: subscription attempt failed (will retry): %s",
                         self.get_name(), exc)

    def _on_orbit_x(self, event):
        if event.err:
            logger.warning("BPMDevice %s: orbit_x event error: %s",
                           self.get_name(), event.errors)
            return
        if self.orbit_index < 0:
            logger.warning("BPMDevice %s: orbit_index=-1, cannot index orbit array",
                           self.get_name())
            return
        try:
            arr = event.attr_value.value
            if arr is None:
                logger.warning("BPMDevice %s: orbit_x event value is None", self.get_name())
                return
            logger.debug("BPMDevice %s: orbit_x event len=%d index=%d",
                         self.get_name(), len(arr), self.orbit_index)
            if self.orbit_index < len(arr):
                self._x = float(arr[self.orbit_index])
            else:
                logger.warning("BPMDevice %s: orbit_index=%d >= orbit_x len=%d",
                               self.get_name(), self.orbit_index, len(arr))
        except Exception as exc:
            logger.warning("BPMDevice %s: _on_orbit_x failed: %s", self.get_name(), exc)

    def _on_orbit_y(self, event):
        if event.err:
            return
        if self.orbit_index < 0:
            return
        try:
            arr = event.attr_value.value
            if arr is not None and self.orbit_index < len(arr):
                self._y = float(arr[self.orbit_index])
        except Exception as exc:
            logger.warning("BPMDevice %s: _on_orbit_y failed: %s", self.get_name(), exc)

    def delete_device(self):
        try:
            if hasattr(self, "_ringsim") and self._event_ids:
                for eid in self._event_ids:
                    self._ringsim.unsubscribe_event(eid)
        except Exception:
            pass

    @attribute(dtype=DevDouble, label="Horizontal position", unit="m",
               polling_period=1000)
    def x(self) -> float:
        return self._x

    @attribute(dtype=DevDouble, label="Vertical position", unit="m",
               polling_period=1000)
    def y(self) -> float:
        return self._y