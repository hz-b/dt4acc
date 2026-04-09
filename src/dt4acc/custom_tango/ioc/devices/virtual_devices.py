"""
virtual_devices.py
==================

Virtual Tango devices used by dt4acc:

    ✔ TwissOrbitDevice   — receives pushed orbit/twiss arrays (unchanged)
    ✔ BPMManagerDevice   — receives pushed BPM data (unchanged)
    ✔ TuneDevice         — receives pushed tune scalars (unchanged)
    ✔ OtherPVsDevice     — read-only misc values (unchanged)
    ✔ MasterClockDevice  — writes reference_frequency via TangoController
    ✔ CavityDevice       — writes frequency/voltage/phase via TangoController

TwissOrbitDevice, BPMManagerDevice, TuneDevice, OtherPVsDevice do NOT call
the backend directly — they are passive stores that CalculationResultView
pushes data into via DeviceProxy commands/attributes. No changes needed there.

MasterClockDevice and CavityDevice write to the backend so they use
get_controller().update() instead of the old handle_device_update().
"""

import asyncio

import numpy as np
from dt4acc_lib.model.utils.command import ReadCommand, BehaviourOnError, Command
from tango import DevState, DevFailed, DevDouble
from tango.server import (
    Device, attribute, command,
    AttrDataFormat, device_property, AttrWriteType,
)

from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_tango.ioc.devices.shared_event_loop import get_shared_event_loop
from dt4acc.custom_tango.ioc.controller_registry import get_controller

logger = get_logger()


# ===============================================================
# Shared async helper mixin (unchanged)
# ===============================================================

class AsyncMixin:
    def _start_async(self):
        self._loop = get_shared_event_loop()

    def _async(self, coro):
        try:
            fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
            return fut.result(timeout=10)
        except Exception as exc:
            raise DevFailed(str(exc))


# ===============================================================
# 1. TwissOrbitDevice — UNCHANGED
#    Passive store: CalculationResultView pushes data in via commands.
#    No backend calls here.
# ===============================================================

class TwissOrbitDevice(Device, AsyncMixin):
    MAX_ELEMS = 6000

    def __init__(self, cl, name):
        super().__init__(cl, name)
        self._orbit_x = np.array([0.0], dtype=np.float64)
        self._orbit_y = np.array([0.0], dtype=np.float64)
        self._beta_x  = np.array([0.0], dtype=np.float64)
        self._alpha_x = np.array([0.0], dtype=np.float64)
        self._nu_x    = np.array([0.0], dtype=np.float64)
        self._beta_y  = np.array([0.0], dtype=np.float64)
        self._alpha_y = np.array([0.0], dtype=np.float64)
        self._nu_y    = np.array([0.0], dtype=np.float64)

    def init_device(self):
        super().init_device()
        self._orbit_x = np.array([0.0], dtype=np.float64)
        self._orbit_y = np.array([0.0], dtype=np.float64)
        self._beta_x  = np.array([0.0], dtype=np.float64)
        self._alpha_x = np.array([0.0], dtype=np.float64)
        self._nu_x    = np.array([0.0], dtype=np.float64)
        self._beta_y  = np.array([0.0], dtype=np.float64)
        self._alpha_y = np.array([0.0], dtype=np.float64)
        self._nu_y    = np.array([0.0], dtype=np.float64)
        for a in ("orbit_x", "orbit_y", "beta_x", "alpha_x", "nu_x",
                  "beta_y", "alpha_y", "nu_y"):
            self.set_change_event(a, True, False)
        self.set_state(DevState.ON)

    @attribute(dtype=DevDouble, dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_ELEMS)
    def orbit_x(self): return self._orbit_x

    @attribute(dtype=DevDouble, dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_ELEMS)
    def orbit_y(self): return self._orbit_y

    @attribute(dtype=DevDouble, dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_ELEMS)
    def beta_x(self): return self._beta_x

    @attribute(dtype=DevDouble, dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_ELEMS)
    def alpha_x(self): return self._alpha_x

    @attribute(dtype=DevDouble, dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_ELEMS)
    def nu_x(self): return self._nu_x

    @attribute(dtype=DevDouble, dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_ELEMS)
    def beta_y(self): return self._beta_y

    @attribute(dtype=DevDouble, dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_ELEMS)
    def alpha_y(self): return self._alpha_y

    @attribute(dtype=DevDouble, dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_ELEMS)
    def nu_y(self): return self._nu_y

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

    @command(dtype_in=(float,))
    def push_beta_x(self, values):
        arr = np.asarray(values, dtype=np.float64).ravel()
        self._beta_x = arr
        self.push_change_event("beta_x", arr)

    @command(dtype_in=(float,))
    def push_alpha_x(self, values):
        arr = np.asarray(values, dtype=np.float64).ravel()
        self._alpha_x = arr
        self.push_change_event("alpha_x", arr)

    @command(dtype_in=(float,))
    def push_nu_x(self, values):
        arr = np.asarray(values, dtype=np.float64).ravel()
        self._nu_x = arr
        self.push_change_event("nu_x", arr)

    @command(dtype_in=(float,))
    def push_beta_y(self, values):
        arr = np.asarray(values, dtype=np.float64).ravel()
        self._beta_y = arr
        self.push_change_event("beta_y", arr)

    @command(dtype_in=(float,))
    def push_alpha_y(self, values):
        arr = np.asarray(values, dtype=np.float64).ravel()
        self._alpha_y = arr
        self.push_change_event("alpha_y", arr)

    @command(dtype_in=(float,))
    def push_nu_y(self, values):
        arr = np.asarray(values, dtype=np.float64).ravel()
        self._nu_y = arr
        self.push_change_event("nu_y", arr)


# ===============================================================
# 2. BPMManagerDevice — UNCHANGED
#    Passive store: CalculationResultView writes attributes directly.
# ===============================================================

class BPMManagerDevice(Device, AsyncMixin):
    """Virtual BPM aggregator. Tango device: PHYSICS/SOLEIL/BPM"""

    MAX_BPMS = 4096

    def init_device(self):
        super().init_device()
        self._bpm_names = []
        self._bpm_x = np.array([], dtype=np.float64)
        self._bpm_y = np.array([], dtype=np.float64)
        for attr_name in ("bpm_names_attr", "bpm_x_attr", "bpm_y_attr"):
            self.set_change_event(attr_name, True, False)
        self.set_state(DevState.ON)

    @attribute(dtype=str, access=AttrWriteType.READ_WRITE,
               dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_BPMS)
    def bpm_names_attr(self): return self._bpm_names

    @bpm_names_attr.write
    def bpm_names_attr(self, values):
        self._bpm_names = [] if values is None else [str(v) for v in values]
        if self._bpm_names:
            self.push_change_event("bpm_names_attr", self._bpm_names)

    @attribute(dtype=DevDouble, access=AttrWriteType.READ_WRITE,
               dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_BPMS)
    def bpm_x_attr(self): return self._bpm_x

    @bpm_x_attr.write
    def bpm_x_attr(self, values):
        arr = np.asarray([] if values is None else values, dtype=np.float64).ravel()
        arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
        self._bpm_x = arr
        if arr.size:
            self.push_change_event("bpm_x_attr", arr.tolist())

    @attribute(dtype=DevDouble, access=AttrWriteType.READ_WRITE,
               dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_BPMS)
    def bpm_y_attr(self): return self._bpm_y

    @bpm_y_attr.write
    def bpm_y_attr(self, values):
        arr = np.asarray([] if values is None else values, dtype=np.float64).ravel()
        arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
        self._bpm_y = arr
        if arr.size:
            self.push_change_event("bpm_y_attr", arr.tolist())


# ===============================================================
# 3. TuneDevice — UNCHANGED
#    Passive store: TangoController pushes tune scalars here via
#    CalculationResultView. The write attributes allow external
#    clients to override if needed, but do not call the backend.
# ===============================================================

class TuneDevice(Device):
    """Virtual tune provider. Tango device: PHYSICS/SOLEIL/TUNE"""

    def init_device(self):
        super().init_device()
        self.tune_x = 0.0
        self.tune_y = 0.0
        self.set_state(DevState.ON)

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE)
    def hor(self) -> float:
        return self.tune_x

    @hor.write
    def hor(self, value: float) -> None:
        self.tune_x = float(value)

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE)
    def vert(self) -> float:
        return self.tune_y

    @vert.write
    def vert(self, value: float) -> None:
        self.tune_y = float(value)


# ===============================================================
# 4. OtherPVsDevice — UNCHANGED
#    Read-only misc values. No backend writes.
# ===============================================================

class OtherPVsDevice(Device):
    """Virtual provider for miscellaneous global values."""

    def init_device(self):
        super().init_device()
        self._temperature = 0.0
        self._vacuum = 0.0
        self.set_state(DevState.ON)

    @attribute(dtype=float)
    def temperature(self) -> float:
        return self._temperature

    @attribute(dtype=float)
    def vacuum(self) -> float:
        return self._vacuum


# ===============================================================
# 5. MasterClockDevice — REWRITTEN
#    Writes reference_frequency via TangoController.
# ===============================================================

class MasterClockDevice(Device):
    """
    Virtual RF master clock device. Tango device: PHYSICS/SOLEIL/MASTER_CLOCK

    Writing `frequency` triggers a backend update via TangoController, which
    queues the default delayed reads so orbit/twiss recalculate automatically.
    """

    def init_device(self):
        super().init_device()
        self.set_state(DevState.INIT)
        logger.info("Initializing MasterClockDevice")

        self._loop = get_shared_event_loop()

        self.frequency_value = self._peek_initial_frequency()
        self.set_state(DevState.ON)

    def _peek_initial_frequency(self) -> float:
        try:
            result = self._async(
                get_controller().trigger_read(
                    [ReadCommand(id="master_clock", property="reference_frequency")]
                )
            )
            readings = result.all_readings()
            if readings:
                return float(readings[0].payload)
        except Exception as exc:
            logger.warning("MasterClockDevice: could not read initial frequency: %s", exc)
        return 0.0

    def _async(self, coro):
        try:
            fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
            return fut.result(timeout=10)
        except Exception as exc:
            raise DevFailed(str(exc))

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE,
               label="Reference frequency", unit="kHz")
    def frequency(self) -> float:
        return self.frequency_value

    @frequency.write
    def frequency(self, value: float) -> None:
        value = float(value)
        self.frequency_value = value
        self._async(
            get_controller().update(
                cmd=Command(
                    id="master_clock",
                    property="reference_frequency",
                    value=value,
                    behaviour_on_error=BehaviourOnError.stop,
                ),
                reads=[],
                delayed_reads=[],
            )
        )


# ===============================================================
# 6. CavityDevice — REWRITTEN
#    Writes frequency/voltage/phase via TangoController.
# ===============================================================

class CavityDevice(Device):
    """
    Virtual cavity device. Tango name: SOLEIL/RF/<cavity_name>

    The cavity name is derived from the Tango device name (member part).
    Writing any attribute triggers a backend update via TangoController.
    """

    def init_device(self):
        super().init_device()
        self.set_state(DevState.INIT)

        # Cavity name is the member part of the Tango device name
        # e.g. SOLEIL/RF/CAVH1T8R -> cavity_id = CAVH1T8R
        full_name = self.get_name()
        parts = full_name.split("/")
        self.cavity_id = parts[-1] if len(parts) == 3 else full_name
        logger.info("Initializing CavityDevice: %s", self.cavity_id)

        self._loop = get_shared_event_loop()

        self.freq          = self._peek_initial_frequency()
        self.voltage_value = 0.0
        self.phase_value   = 0.0

        self.set_state(DevState.ON)

    def _peek_initial_frequency(self) -> float:
        try:
            result = self._async(
                get_controller().trigger_read(
                    [ReadCommand(id=self.cavity_id, property="frequency")]
                )
            )
            readings = result.all_readings()
            if readings:
                return float(readings[0].payload)
        except Exception as exc:
            logger.warning(
                "CavityDevice %s: could not read initial frequency: %s",
                self.cavity_id, exc,
            )
        return 0.0

    def _async(self, coro):
        try:
            fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
            return fut.result(timeout=10)
        except Exception as exc:
            raise DevFailed(str(exc))

    def _update(self, property_name: str, value: float) -> None:
        self._async(
            get_controller().update(
                cmd=Command(
                    id=self.cavity_id,
                    property=property_name,
                    value=value,
                    behaviour_on_error=BehaviourOnError.stop,
                ),
                reads=[],
                delayed_reads=[],
            )
        )

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE,
               label="Frequency", unit="kHz")
    def frequency(self) -> float:
        return self.freq

    @frequency.write
    def frequency(self, value: float) -> None:
        self.freq = float(value)
        self._update("frequency", self.freq)

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE,
               label="Voltage", unit="MV")
    def voltage(self) -> float:
        return self.voltage_value

    @voltage.write
    def voltage(self, value: float) -> None:
        self.voltage_value = float(value)
        self._update("voltage", self.voltage_value)

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE,
               label="Phase", unit="deg")
    def phase(self) -> float:
        return self.phase_value

    @phase.write
    def phase(self, value: float) -> None:
        self.phase_value = float(value)
        self._update("phase", self.phase_value)
