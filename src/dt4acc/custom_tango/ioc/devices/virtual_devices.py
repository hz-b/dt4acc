"""
virtual_devices.py
==================

Single virtual Tango device for the digital twin:

    simulator/ringsimulator/ringsimulator  (RingSimulatorDevice)

"""

import asyncio
import numpy as np
from tango import DevState, DevFailed, DevDouble, DevString
from tango.server import Device, attribute, command, AttrDataFormat, device_property, AttrWriteType

from dt4acc.core.bl.shared_event_loop import get_shared_event_loop
from dt4acc_lib.model.utils.command import Command, BehaviourOnError, ReadCommand
from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_tango.ioc.controller_registry import get_controller

logger = get_logger()

RING_SIM_DEV = "simulator/ringsimulator/ringsimulator"
MAX_ELEMS = 6000
MAX_BPMS  = 4096

# ---------------------------------------------------------------------------
# Module-level orbit cache — updated by RingSimulatorDevice.push_orbit_x/y
# and read by BPMDevice without any cross-process calls.
# ---------------------------------------------------------------------------
_orbit_x_cache: np.ndarray = np.array([], dtype=np.float64)
_orbit_y_cache: np.ndarray = np.array([], dtype=np.float64)


def get_orbit_at_index(index: int):
    """Return (x, y) from the latest orbit cache at the given AT element index.
    Returns (0.0, 0.0) if the cache is empty or index is out of range.
    """
    if index < len(_orbit_x_cache) and index < len(_orbit_y_cache):
        return float(_orbit_x_cache[index]), float(_orbit_y_cache[index])
    return 0.0, 0.0


class AsyncMixin:
    def _start_async(self):
        self._loop = get_shared_event_loop()

    def _async(self, coro):
        try:
            fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
            return fut.result(timeout=10)
        except Exception as exc:
            raise DevFailed(str(exc))


class RingSimulatorDevice(Device, AsyncMixin):
    """
    Single Tango device exposing all digital twin physics results.
    Device name: simulator/ringsimulator/ringsimulator
    """

    def init_device(self):
        super().init_device()
        self._loop = get_shared_event_loop()
        self._orbit_x = np.array([0.0], dtype=np.float64)
        self._orbit_y = np.array([0.0], dtype=np.float64)
        self._beta_x  = np.array([0.0], dtype=np.float64)
        self._beta_y  = np.array([0.0], dtype=np.float64)
        self._alpha_x = np.array([0.0], dtype=np.float64)
        self._alpha_y = np.array([0.0], dtype=np.float64)
        self._nu_x    = np.array([0.0], dtype=np.float64)
        self._nu_y    = np.array([0.0], dtype=np.float64)
        self._bpm_names = []
        self._bpm_x     = np.array([], dtype=np.float64)
        self._bpm_y     = np.array([], dtype=np.float64)
        self._tune_hor  = 0.0
        self._tune_vert = 0.0
        self._xi_x      = 0.0
        self._xi_y      = 0.0
        self._reference_frequency = 0.0
        for attr_name in ("orbit_x", "orbit_y",
                          "beta_x", "beta_y", "alpha_x", "alpha_y", "nu_x", "nu_y",
                          "bpm_x_attr", "bpm_y_attr", "hor", "vert"):
            self.set_change_event(attr_name, True, False)
        self.set_state(DevState.ON)

    # Orbit
    @attribute(dtype=DevDouble, dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_ELEMS)
    def orbit_x(self): return self._orbit_x

    @attribute(dtype=DevDouble, dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_ELEMS)
    def orbit_y(self): return self._orbit_y

    # Twiss
    @attribute(dtype=DevDouble, dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_ELEMS)
    def beta_x(self): return self._beta_x

    @attribute(dtype=DevDouble, dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_ELEMS)
    def beta_y(self): return self._beta_y

    @attribute(dtype=DevDouble, dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_ELEMS)
    def alpha_x(self): return self._alpha_x

    @attribute(dtype=DevDouble, dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_ELEMS)
    def alpha_y(self): return self._alpha_y

    @attribute(dtype=DevDouble, dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_ELEMS)
    def nu_x(self): return self._nu_x

    @attribute(dtype=DevDouble, dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_ELEMS)
    def nu_y(self): return self._nu_y

    # BPM
    @attribute(dtype=DevString, dformat=AttrDataFormat.SPECTRUM,
               access=AttrWriteType.READ_WRITE, max_dim_x=MAX_BPMS)
    def bpm_names_attr(self): return self._bpm_names

    @bpm_names_attr.write
    def bpm_names_attr(self, values):
        self._bpm_names = [] if values is None else [str(v) for v in values]

    @attribute(dtype=DevDouble, dformat=AttrDataFormat.SPECTRUM,
               access=AttrWriteType.READ_WRITE, max_dim_x=MAX_BPMS)
    def bpm_x_attr(self): return self._bpm_x

    @bpm_x_attr.write
    def bpm_x_attr(self, values):
        self._bpm_x = np.asarray(values, dtype=np.float64)
        self.push_change_event("bpm_x_attr", self._bpm_x)

    @attribute(dtype=DevDouble, dformat=AttrDataFormat.SPECTRUM,
               access=AttrWriteType.READ_WRITE, max_dim_x=MAX_BPMS)
    def bpm_y_attr(self): return self._bpm_y

    @bpm_y_attr.write
    def bpm_y_attr(self, values):
        self._bpm_y = np.asarray(values, dtype=np.float64)
        self.push_change_event("bpm_y_attr", self._bpm_y)

    # Tune — READ ONLY. Tunes are computed by AT, not settable directly.
    @attribute(dtype=DevDouble, label="Horizontal tune")
    def hor(self): return self._tune_hor

    @attribute(dtype=DevDouble, label="Vertical tune")
    def vert(self): return self._tune_vert

    # Chromaticity — READ ONLY. Computed by AT alongside tune.
    @attribute(dtype=DevDouble, label="Horizontal chromaticity")
    def xi_x(self): return self._xi_x

    @attribute(dtype=DevDouble, label="Vertical chromaticity")
    def xi_y(self): return self._xi_y

    # Master clock
    @attribute(dtype=DevDouble, access=AttrWriteType.READ_WRITE,
               label="Reference frequency", unit="kHz")
    def reference_frequency(self): return self._reference_frequency

    @reference_frequency.write
    def reference_frequency(self, value: float):
        value = float(value)
        self._reference_frequency = value
        self._async(
            get_controller().update(
                cmd=Command(
                    id="master_clock",
                    property="reference_frequency",
                    value=value,
                    behaviour_on_error=BehaviourOnError.stop,
                ),
                reads=[], delayed_reads=[],
            )
        )

    # Orbit push commands
    @command(dtype_in=(float,))
    def push_orbit_x(self, values):
        global _orbit_x_cache
        arr = np.asarray(values, dtype=np.float64).ravel()
        self._orbit_x = arr
        _orbit_x_cache = arr
        self.push_change_event("orbit_x", arr)

    @command(dtype_in=(float,))
    def push_orbit_y(self, values):
        global _orbit_y_cache
        arr = np.asarray(values, dtype=np.float64).ravel()
        self._orbit_y = arr
        _orbit_y_cache = arr
        self.push_change_event("orbit_y", arr)

    # Twiss push commands
    @command(dtype_in=(float,))
    def push_beta_x(self, values):
        arr = np.asarray(values, dtype=np.float64).ravel()
        self._beta_x = arr
        self.push_change_event("beta_x", arr)

    @command(dtype_in=(float,))
    def push_beta_y(self, values):
        arr = np.asarray(values, dtype=np.float64).ravel()
        self._beta_y = arr
        self.push_change_event("beta_y", arr)

    @command(dtype_in=(float,))
    def push_alpha_x(self, values):
        arr = np.asarray(values, dtype=np.float64).ravel()
        self._alpha_x = arr
        self.push_change_event("alpha_x", arr)

    @command(dtype_in=(float,))
    def push_alpha_y(self, values):
        arr = np.asarray(values, dtype=np.float64).ravel()
        self._alpha_y = arr
        self.push_change_event("alpha_y", arr)

    @command(dtype_in=(float,))
    def push_nu_x(self, values):
        arr = np.asarray(values, dtype=np.float64).ravel()
        self._nu_x = arr
        self.push_change_event("nu_x", arr)

    @command(dtype_in=(float,))
    def push_nu_y(self, values):
        arr = np.asarray(values, dtype=np.float64).ravel()
        self._nu_y = arr
        self.push_change_event("nu_y", arr)

    @command(dtype_in=(float,))
    def push_tune(self, values):
        """Called by the heartbeat with [tune_x, tune_y] from AT."""
        if len(values) >= 2:
            self._tune_hor  = float(values[0])
            self._tune_vert = float(values[1])
            self.push_change_event("hor",  self._tune_hor)
            self.push_change_event("vert", self._tune_vert)

    @command(dtype_in=(float,))
    def push_chromaticity(self, values):
        """Called by the heartbeat with [xi_x, xi_y] from AT."""
        if len(values) >= 2:
            self._xi_x = float(values[0])
            self._xi_y = float(values[1])
            self.push_change_event("xi_x", self._xi_x)
            self.push_change_event("xi_y", self._xi_y)

    # Reset
    @command
    def Recalculate(self):
        """
        Trigger a fresh twiss+orbit+tune calculation on the CURRENT lattice
        state without changing anything.

        Called by the calculation heartbeat every second, and can also be
        called manually after a measurement to get an updated result.
        Does NOT perturb the lattice — zero noise.
        Sets State=FAULT if beam is lost (NaN/inf in AT optics), ON on recovery.
        """
        controller = get_controller()
        assert callable(controller.enqueue)
        delayed_reads = get_controller().get_default_delayed_reads()
        assert delayed_reads, "No delayed reads were provided"
        try:
            self._async(
                # Todo: provide a public method for it
                get_controller().enqueue(list(delayed_reads))
            )
            # Successful calculation — restore ON if we were in FAULT
            if self.get_state() == DevState.FAULT:
                self.set_state(DevState.ON)
        except Exception as exc:
            msg = str(exc)
            if "infs or NaN" in msg or "nan" in msg.lower() or "inf" in msg.lower():
                logger.warning("RingSimulatorDevice: beam lost — setting FAULT state")
                self.set_state(DevState.FAULT)
                self.set_status("Beam lost: lattice optics diverged (NaN/inf). "
                                "Reset magnets to nominal and call Reset.")
            else:
                logger.debug("RingSimulatorDevice.Recalculate: %s", exc)

    @command
    def Reset(self):
        """Reset the digital twin to nominal state after beam loss."""
        logger.warning("RingSimulatorDevice.Reset: initiating backend reset...")
        self.set_state(DevState.INIT)
        try:
            self._start_async()
            get_controller().reset()
            self.set_state(DevState.ON)
            logger.warning("RingSimulatorDevice.Reset: complete — nominal state restored")
        except Exception as exc:
            logger.error("RingSimulatorDevice.Reset failed: %s", exc)
            self.set_state(DevState.FAULT)
            raise DevFailed(str(exc))