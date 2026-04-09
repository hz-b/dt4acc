"""
SOLEIL-CORRECT VIRTUAL DEVICES
==============================

This file contains ALL virtual Tango devices used by dt4acc:

    ✔ TwissOrbitDevice
    ✔ BPMManagerDevice
    ✔ TuneDevice
    ✔ OtherdevDevice
    ✔ MasterClockDevice
    ✔ CavityDevice

These devices:

  • Do NOT use Tango DB properties.
  • Use only their Tango device name.
  • Are registered under fixed virtual servers (PHYSICS/SOLEIL, RF/SOLEIL).
  • Use dt4acc update_manager.peek_engine for all data.

"""

from bact_twin_architecture.data_model.identifiers import (
    LatticeElementPropertyID,
    DevicePropertyID,
)
from dt4acc.core.utils.logger import get_logger

logger = get_logger()

# ===============================================================
# Helper mixin for all async devices
# ===============================================================

import numpy as np
import asyncio
from tango import DevState, DevFailed, DevDouble, EventType  # <--- Added DevDouble
from tango.server import Device, attribute, command, AttrDataFormat, device_property, AttrWriteType

from dt4acc.core.bl.handlers import get_update_manager, handle_device_update
from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_tango.ioc.devices.shared_event_loop import get_shared_event_loop

logger = get_logger()


class AsyncMixin:
    def _start_async(self):
        self._loop = get_shared_event_loop()

    def _async(self, coro):
        try:
            fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
            return fut.result(timeout=10)
        except Exception as e:
            raise DevFailed(str(e))


class TwissOrbitDevice(Device, AsyncMixin):
    MAX_ELEMS = 6000

    def __init__(self, cl, name):
        super().__init__(cl, name)
        self._orbit_x = np.array([0.0], dtype=np.float64)
        self._orbit_y = np.array([0.0], dtype=np.float64)
        self._beta_x = np.array([0.0], dtype=np.float64)
        self._alpha_x = np.array([0.0], dtype=np.float64)
        self._nu_x = np.array([0.0], dtype=np.float64)
        self._beta_y = np.array([0.0], dtype=np.float64)
        self._alpha_y = np.array([0.0], dtype=np.float64)
        self._nu_y = np.array([0.0], dtype=np.float64)

    def init_device(self):
        super().init_device()
        self.set_state(DevState.ON)

        # Initialize as lists containing at least one float

        self._orbit_x = np.array([0.0], dtype=np.float64)
        self._orbit_y = np.array([0.0], dtype=np.float64)
        self._beta_x = np.array([0.0], dtype=np.float64)
        self._alpha_x = np.array([0.0], dtype=np.float64)
        self._nu_x = np.array([0.0], dtype=np.float64)
        self._beta_y = np.array([0.0], dtype=np.float64)
        self._alpha_y = np.array([0.0], dtype=np.float64)
        self._nu_y = np.array([0.0], dtype=np.float64)

        # Enable change events
        for a in ("orbit_x", "orbit_y", "beta_x", "alpha_x", "nu_x", "beta_y", "alpha_y", "nu_y"):
            self.set_change_event(a, True, False)

    @staticmethod
    def _to_float_array(v):
        """
        Always returns numpy array with dtype=np.float64
        """
        if v is None:
            return np.array([0.0], dtype=np.float64)

        if isinstance(v, np.ndarray):
            return v.astype(np.float64, copy=False).ravel()

        # list/tuple/scalar
        try:
            arr = np.array(v, dtype=np.float64)
            return arr.ravel() if arr.ndim > 1 else arr
        except:
            return np.array([float(v)], dtype=np.float64)

    # -------------------------
    # Attributes: Explicitly use DevDouble
    # -------------------------
    @attribute(dtype=DevDouble, dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_ELEMS)
    def orbit_x(self):
        return self._orbit_x

    @attribute(dtype=DevDouble, dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_ELEMS)
    def orbit_y(self):
        return self._orbit_y

    @attribute(dtype=DevDouble, dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_ELEMS)
    def beta_x(self):
        return self._beta_x

    @attribute(dtype=DevDouble, dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_ELEMS)
    def alpha_x(self):
        return self._alpha_x

    @attribute(dtype=DevDouble, dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_ELEMS)
    def nu_x(self):
        return self._nu_x

    @attribute(dtype=DevDouble, dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_ELEMS)
    def beta_y(self):
        return self._beta_y

    @attribute(dtype=DevDouble, dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_ELEMS)
    def alpha_y(self):
        return self._alpha_y

    @attribute(dtype=DevDouble, dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_ELEMS)
    def nu_y(self):
        return self._nu_y

    # -------------------------
    # Commands: STRICT Type Enforcement
    # -------------------------

    @command(dtype_in=(float,))
    def push_orbit_x(self, values):
        arr = np.asarray(values, dtype=np.float64).ravel()
        self._orbit_x = arr
        self.push_change_event("orbit_x", arr)  # numpy float64 is fine for DevVarDoubleArray

    @command(dtype_in=(float,))
    def push_orbit_y(self, values):
        arr = np.asarray(values, dtype=np.float64).ravel()
        self._orbit_y = arr
        self.push_change_event("orbit_y", arr)  # numpy float64 is fine for DevVarDoubleArray

    @command(dtype_in=(float,))
    def push_beta_x(self, values):
        arr = np.asarray(values, dtype=np.float64).ravel()
        self._beta_x = arr
        self.push_change_event("beta_x", arr)  # numpy float64 is fine for DevVarDoubleArray

    @command(dtype_in=(float,))
    def push_alpha_x(self, values):
        arr = np.asarray(values, dtype=np.float64).ravel()
        self._alpha_x = arr
        self.push_change_event("alpha_x", arr)  # numpy float64 is fine for DevVarDoubleArray

    @command(dtype_in=(float,))
    def push_nu_x(self, values):
        arr = np.asarray(values, dtype=np.float64).ravel()
        self._nu_x = arr
        self.push_change_event("nu_x", arr)  # numpy float64 is fine for DevVarDoubleArray

    @command(dtype_in=(float,))
    def push_beta_y(self, values):
        arr = np.asarray(values, dtype=np.float64).ravel()
        self._beta_y = arr
        self.push_change_event("beta_y", arr)  # numpy float64 is fine for DevVarDoubleArray

    @command(dtype_in=(float,))
    def push_alpha_y(self, values):
        arr = np.asarray(values, dtype=np.float64).ravel()
        self._alpha_y = arr
        self.push_change_event("alpha_y", arr)  # numpy float64 is fine for DevVarDoubleArray


    @command(dtype_in=(float,))
    def push_nu_y(self, values):
        arr = np.asarray(values, dtype=np.float64).ravel()
        self._nu_y = arr
        self.push_change_event("nu_y", arr)  # numpy float64 is fine for DevVarDoubleArray

# ===============================================================
# 2. BPM MANAGER DEVICE
# ===============================================================

class BPMManagerDevice(Device, AsyncMixin):
    """
    Virtual BPM aggregator.

    Tango device: PHYSICS/SOLEIL/BPM
    """

    MAX_BPMS = 4096

    def init_device(self):
        super().init_device()
        logger.debug("Initializing BPMManagerDevice")

        self._bpm_names = []
        self._bpm_x = np.array([], dtype=np.float64)
        self._bpm_y = np.array([], dtype=np.float64)

        for attr_name in ("bpm_names_attr", "bpm_x_attr", "bpm_y_attr"):
            self.set_change_event(attr_name, True, False)

        self.set_state(DevState.ON)

    @attribute(dtype=str, access=AttrWriteType.READ_WRITE, dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_BPMS)
    def bpm_names_attr(self):
        return self._bpm_names

    @bpm_names_attr.write
    def bpm_names_attr(self, values):
        self._bpm_names = [] if values is None else [str(v) for v in values]
        if self._bpm_names:
            self.push_change_event("bpm_names_attr", self._bpm_names)

    @attribute(dtype=DevDouble, access=AttrWriteType.READ_WRITE, dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_BPMS)
    def bpm_x_attr(self):
        return self._bpm_x

    @bpm_x_attr.write
    def bpm_x_attr(self, values):
        arr = np.asarray([] if values is None else values, dtype=np.float64).ravel()
        arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
        self._bpm_x = arr
        if arr.size:
            self.push_change_event("bpm_x_attr", arr.tolist())

    @attribute(dtype=DevDouble, access=AttrWriteType.READ_WRITE, dformat=AttrDataFormat.SPECTRUM, max_dim_x=MAX_BPMS)
    def bpm_y_attr(self):
        return self._bpm_y

    @bpm_y_attr.write
    def bpm_y_attr(self, values):
        arr = np.asarray([] if values is None else values, dtype=np.float64).ravel()
        arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
        self._bpm_y = arr
        if arr.size:
            self.push_change_event("bpm_y_attr", arr.tolist())

# ===============================================================
# 3. TUNE DEVICE
# ===============================================================

class TuneDevice(Device):
    """
    Virtual tune provider:

        SOLEIL/PHYSICS/TUNE
    """

    def init_device(self):
        super().init_device()
        logger.debug("Initializing TuneDevice")

        try:
            update_manager = get_update_manager()
            self.tune_x = float(
                update_manager.peek_engine(LatticeElementPropertyID("TUNE", "x"))
            )
            self.tune_y = float(
                update_manager.peek_engine(LatticeElementPropertyID("TUNE", "y"))
            )
        except Exception:
            self.tune_x = 0.0
            self.tune_y = 0.0

        self.set_state(DevState.ON)

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE)
    def hor(self):
        return self.tune_x

    @hor.write
    def hor(self, value):
        self.tune_x = float(value)

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE)
    def vert(self):
        return self.tune_y

    @vert.write
    def vert(self, value):
        self.tune_y = float(value)


# ===============================================================
# 4. OTHER dev DEVICE
# ===============================================================

class OtherPVsDevice(Device):
    """
    Virtual provider for miscellaneous global dev:

        SOLEIL/PHYSICS/OTHER_dev
    """

    def init_device(self):
        super().init_device()
        logger.debug("Initializing OtherdevDevice")

        self.values = {}
        self.values["temperature"] = 0.0
        self.values["vacuum"] = 0.0
        try:
            update_manager = get_update_manager()

            try:
                val = update_manager.peek_engine(
                    LatticeElementPropertyID("GLOBAL", "temperature")
                )
                self.values["temperature"] = float(val)
            except Exception:
                pass

            try:
                val = update_manager.peek_engine(
                    LatticeElementPropertyID("GLOBAL", "vacuum")
                )
                self.values["vacuum"] = float(val)
            except Exception:
                pass
        except Exception as e:
            logger.debug(f"Could not fetch values from update manager: {e}")

        self.set_state(DevState.ON)

    @attribute(dtype=float)
    def temperature(self):
        return self.values.get("temperature", 0.0)

    @attribute(dtype=float)
    def vacuum(self):
        return self.values.get("vacuum", 0.0)


# ===============================================================
# 5. MASTER CLOCK DEVICE
# ===============================================================

class MasterClockDevice(Device):
    """
    Virtual RF master clock device:

        SOLEIL/RF/MASTER_CLOCK
    """

    def init_device(self):
        super().init_device()
        logger.debug("Initializing MasterClockDevice")

        try:
            update_manager = get_update_manager()
            val = update_manager.device_value_from_peeking_engine(
                DevicePropertyID("master_clock", "reference_frequency")
            )
            self.frequency_value = float(val)
        except Exception:
            self.frequency_value = 0.0

        self.set_state(DevState.ON)

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE)
    def frequency(self):
        return self.frequency_value

    @frequency.write
    def frequency(self, value):
        value = float(value)
        self.frequency_value = value
        try:
            handle_device_update("master_clock", "reference_frequency", value)
        except Exception as e:
            raise DevFailed(str(e))


# ===============================================================
# 6. CAVITY DEVICES
# ===============================================================

class CavityDevice(Device):
    """
    Virtual cavity device template.

        Tango name: SOLEIL/RF/<cavity_name>
    """

    name = device_property(dtype=str, default_value="UNKNOWN")

    def init_device(self):
        super().init_device()
        logger.info(f"Initializing CavityDevice: {self.get_name()}")

        try:
            update_manager = get_update_manager()
            val = update_manager.device_value_from_peeking_engine(
                DevicePropertyID(self.get_name(), "frequency")
            )
            self.freq = float(val)
        except Exception:
            self.freq = 0.0

        self.voltage_value = 0.0
        self.phase_value = 0.0

        self.set_state(DevState.ON)

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE)
    def frequency(self):
        return self.freq

    @frequency.write
    def frequency(self, value):
        value = float(value)
        self.freq = value
        try:
            handle_device_update(self.name, "frequency", value)
        except Exception as e:
            raise DevFailed(str(e))

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE)
    def voltage(self):
        return self.voltage_value

    @voltage.write
    def voltage(self, value):
        value = float(value)
        self.voltage_value = value
        try:
            handle_device_update(self.name, "voltage", value)
        except Exception as e:
            raise DevFailed(str(e))

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE)
    def phase(self):
        return self.phase_value

    @phase.write
    def phase(self, value):
        value = float(value)
        self.phase_value = value
        try:
            handle_device_update(self.name, "phase", value)
        except Exception as e:
            raise DevFailed(str(e))
