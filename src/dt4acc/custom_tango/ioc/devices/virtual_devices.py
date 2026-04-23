"""
virtual_devices.py
==================

Single virtual Tango device for the SOLEIL digital twin:

    simulator/ringsimulator/ringsimulator  (RingSimulatorDevice)

Replaces the previous separate devices:
    PHYSICS/SOLEIL/TWISS_ORBIT
    PHYSICS/SOLEIL/BPM
    PHYSICS/SOLEIL/TUNE
    PHYSICS/SOLEIL/MASTER_CLOCK
    PHYSICS/SOLEIL/OTHERS
"""

import asyncio
import numpy as np
from tango import DevState, DevFailed, DevDouble, DevString
from tango.server import Device, attribute, command, AttrDataFormat, device_property, AttrWriteType

from dt4acc_lib.model.utils.command import Command, BehaviourOnError, ReadCommand
from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_tango.ioc.devices.shared_event_loop import get_shared_event_loop
from dt4acc.custom_tango.ioc.controller_registry import get_controller

logger = get_logger()

RING_SIM_DEV = "simulator/ringsimulator/ringsimulator"
MAX_ELEMS = 6000
MAX_BPMS  = 4096


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

    # Tune
    @attribute(dtype=DevDouble, access=AttrWriteType.READ_WRITE, label="Horizontal tune")
    def hor(self): return self._tune_hor

    @hor.write
    def hor(self, value):
        self._tune_hor = float(value)
        self.push_change_event("hor", self._tune_hor)

    @attribute(dtype=DevDouble, access=AttrWriteType.READ_WRITE, label="Vertical tune")
    def vert(self): return self._tune_vert

    @vert.write
    def vert(self, value):
        self._tune_vert = float(value)
        self.push_change_event("vert", self._tune_vert)

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
        arr = np.asarray(values, dtype=np.float64).ravel()
        self._orbit_x = arr
        self.push_change_event("orbit_x", arr)

    @command(dtype_in=(float,))
    def push_orbit_y(self, values):
        arr = np.asarray(values, dtype=np.float64).ravel()
        self._orbit_y = arr
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

    # Reset
    @command
    def Recalculate(self):
        """
        Trigger a fresh twiss+orbit+tune calculation on the CURRENT lattice
        state without changing anything.

        Called by the calculation heartbeat every second, and can also be
        called manually after a measurement to get an updated result.
        Does NOT perturb the lattice — zero noise.
        """
        try:
            self._async(
                get_controller()._enqueue(
                    list(get_controller().default_delayed_reads)
                )
            )
        except Exception as exc:
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
