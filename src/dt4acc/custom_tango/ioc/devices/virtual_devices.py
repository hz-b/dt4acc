"""
SOLEIL-CORRECT VIRTUAL DEVICES
==============================

This file contains ALL virtual Tango devices used by dt4acc:

    ✔ TwissOrbitDevice
    ✔ BPMManagerDevice
    ✔ TuneDevice
    ✔ OtherPVsDevice
    ✔ MasterClockDevice
    ✔ CavityDevice

These devices:

  • Do NOT use Tango DB properties.
  • Use only their Tango device name.
  • Are registered under fixed virtual servers (PHYSICS/SOLEIL, RF/SOLEIL).
  • Use dt4acc update_manager.peek_engine for all data.

"""

import asyncio
import threading
import numpy as np

from tango.server import (
    Device,
    attribute,
    device_property,
    AttrDataFormat,
    AttrWriteType,
)
from tango import DevState, DevFailed

from dt4acc.core.utils.logger import get_logger
from dt4acc.core.bl.handlers import get_update_manager, handle_device_update
from bact_twin_architecture.data_model.identifiers import (
    LatticeElementPropertyID,
    DevicePropertyID,
)
from dt4acc.custom_epics.data.constants import global_settings
from dt4acc.custom_tango.ioc.devices.shared_event_loop import get_shared_event_loop

logger = get_logger()

# ===============================================================
# Helper mixin for all async devices
# ===============================================================

class AsyncMixin:
    """
    Shared async loop helper for virtual devices.
    Uses a shared event loop to avoid exhausting file descriptors.
    """

    def _start_async(self):
        # Use shared event loop instead of creating a new one per device
        self._loop = get_shared_event_loop()

    def _async(self, coro):
        try:
            fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
            return fut.result(timeout=10)
        except Exception as e:
            raise DevFailed(str(e))


# ===============================================================
# 1. TWISS + ORBIT DEVICE
# ===============================================================

class TwissOrbitDevice(Device, AsyncMixin):
    """
    Virtual device for Twiss and Orbit:

        Tango device: SOLEIL/PHYSICS/TWISS_ORBIT
        Server:       PHYSICS/SOLEIL

    Provides:
        orbit_x[], orbit_y[]
        twiss_beta_x[], twiss_alpha_x[]
        twiss_beta_y[], twiss_alpha_y[]
    """

    def init_device(self):
        super().init_device()
        self._start_async()

        logger.info("Initializing TwissOrbitDevice")

        # Initialize empty arrays 
        self.orbit_x = np.zeros(1)
        self.orbit_y = np.zeros(1)
        self.beta_x  = np.zeros(1)
        self.alpha_x = np.zeros(1)
        self.beta_y  = np.zeros(1)
        self.alpha_y = np.zeros(1)

        # Initialize writable attributes 
        self.beam_orbit_x = np.zeros(1)
        self.beam_orbit_y = np.zeros(1)
        self.beam_orbit_names = []
        self.beam_orbit_found = 0
        self.beam_orbit_x0 = np.zeros(1)
        
        self.beam_twiss_x_tune = 0.0
        self.beam_twiss_x_alpha = np.zeros(1)
        self.beam_twiss_x_beta = np.zeros(1)
        self.beam_twiss_x_nu = np.zeros(1)
        self.beam_twiss_y_tune = 0.0
        self.beam_twiss_y_alpha = np.zeros(1)
        self.beam_twiss_y_beta = np.zeros(1)
        self.beam_twiss_y_nu = np.zeros(1)
        self.beam_twiss_names = []

        self._refresh()
        self.set_state(DevState.ON)

    def _refresh(self):
        """
        Fetch twiss + orbit from dt4acc.
        """
        try:
            update_manager = get_update_manager()
            self.orbit_x = np.asarray(
                update_manager.peek_engine(
                    LatticeElementPropertyID("ORBIT", "x")
                )
            )
            self.orbit_y = np.asarray(
                update_manager.peek_engine(
                    LatticeElementPropertyID("ORBIT", "y")
                )
            )

            self.beta_x = np.asarray(
                update_manager.peek_engine(
                    LatticeElementPropertyID("TWISS", "beta_x")
                )
            )
            self.alpha_x = np.asarray(
                update_manager.peek_engine(
                    LatticeElementPropertyID("TWISS", "alpha_x")
                )
            )

            self.beta_y = np.asarray(
                update_manager.peek_engine(
                    LatticeElementPropertyID("TWISS", "beta_y")
                )
            )
            self.alpha_y = np.asarray(
                update_manager.peek_engine(
                    LatticeElementPropertyID("TWISS", "alpha_y")
                )
            )

        except Exception as e:
            logger.error(f"TwissOrbitDevice refresh failed: {e}")

    # ------- Tango Attributes -------
    
    # Read-only attributes (from engine)
    @attribute(dtype=float, max_dim_x=4096, format=AttrDataFormat.SPECTRUM)
    def orbit_x_attr(self):
        return self.orbit_x

    @attribute(dtype=float, max_dim_x=4096, format=AttrDataFormat.SPECTRUM)
    def orbit_y_attr(self):
        return self.orbit_y

    @attribute(dtype=float, max_dim_x=4096, format=AttrDataFormat.SPECTRUM)
    def beta_x_attr(self):
        return self.beta_x

    @attribute(dtype=float, max_dim_x=4096, format=AttrDataFormat.SPECTRUM)
    def alpha_x_attr(self):
        return self.alpha_x

    @attribute(dtype=float, max_dim_x=4096, format=AttrDataFormat.SPECTRUM)
    def beta_y_attr(self):
        return self.beta_y

    @attribute(dtype=float, max_dim_x=4096, format=AttrDataFormat.SPECTRUM)
    def alpha_y_attr(self):
        return self.alpha_y

    # Writable attributes  Orbit
    @attribute(name="beam/orbit/x", dtype=float, max_dim_x=4096, format=AttrDataFormat.SPECTRUM, access=AttrWriteType.READ_WRITE)
    def beam_orbit_x_attr(self):
        if isinstance(self.beam_orbit_x, np.ndarray):
            return [float(x) for x in self.beam_orbit_x.astype(float).tolist()]
        else:
            return [float(x) for x in list(self.beam_orbit_x)]
    
    @beam_orbit_x_attr.write
    def beam_orbit_x_attr(self, value):
        # Tango passes lists of Python floats for SPECTRUM attributes
        if isinstance(value, np.ndarray):
            self.beam_orbit_x = value.astype(np.float64)
        elif isinstance(value, (list, tuple)):
            self.beam_orbit_x = np.asarray([float(v) for v in value], dtype=np.float64)
        else:
            self.beam_orbit_x = np.asarray([float(value)], dtype=np.float64)

    @attribute(name="beam/orbit/y", dtype=float, max_dim_x=4096, format=AttrDataFormat.SPECTRUM, access=AttrWriteType.READ_WRITE)
    def beam_orbit_y_attr(self):
        # Ensure pure Python floats not numpy types
        if isinstance(self.beam_orbit_y, np.ndarray):
            return [float(x) for x in self.beam_orbit_y.astype(float).tolist()]
        else:
            return [float(x) for x in list(self.beam_orbit_y)]
    
    @beam_orbit_y_attr.write
    def beam_orbit_y_attr(self, value):
        # Tango passes lists of Python floats for SPECTRUM attributes
        if isinstance(value, np.ndarray):
            self.beam_orbit_y = value.astype(np.float64)
        elif isinstance(value, (list, tuple)):
            self.beam_orbit_y = np.asarray([float(v) for v in value], dtype=np.float64)
        else:
            self.beam_orbit_y = np.asarray([float(value)], dtype=np.float64)

    @attribute(name="beam/orbit/names", dtype=str, max_dim_x=4096, format=AttrDataFormat.SPECTRUM, access=AttrWriteType.READ_WRITE)
    def beam_orbit_names_attr(self):
        return self.beam_orbit_names
    
    @beam_orbit_names_attr.write
    def beam_orbit_names_attr(self, value):
        # Tango passes string arrays as list of strings
        if isinstance(value, (list, tuple)):
            self.beam_orbit_names = [str(v) for v in value]
        else:
            self.beam_orbit_names = [str(value)]

    @attribute(name="beam/orbit/found", dtype=int, access=AttrWriteType.READ_WRITE)
    def beam_orbit_found_attr(self):
        return self.beam_orbit_found
    
    @beam_orbit_found_attr.write
    def beam_orbit_found_attr(self, value):
        self.beam_orbit_found = int(value)
    
    @attribute(name="beam/orbit/x0", dtype=float, max_dim_x=4096, format=AttrDataFormat.SPECTRUM, access=AttrWriteType.READ_WRITE)
    def beam_orbit_x0_attr(self):
        # Ensure pure Python floats, not numpy types
        if isinstance(self.beam_orbit_x0, np.ndarray):
            return [float(x) for x in self.beam_orbit_x0.astype(float).tolist()]
        else:
            return [float(x) for x in list(self.beam_orbit_x0)]
    
    @beam_orbit_x0_attr.write
    def beam_orbit_x0_attr(self, value):
        # Tango passes lists of Python floats for SPECTRUM attributes
        if isinstance(value, np.ndarray):
            self.beam_orbit_x0 = value.astype(np.float64)
        elif isinstance(value, (list, tuple)):
            self.beam_orbit_x0 = np.asarray([float(v) for v in value], dtype=np.float64)
        else:
            self.beam_orbit_x0 = np.asarray([float(value)], dtype=np.float64)

    # Writable attributes  - Twiss
    @attribute(name="beam/twiss/x/tune", dtype=float, access=AttrWriteType.READ_WRITE)
    def beam_twiss_x_tune_attr(self):
        return self.beam_twiss_x_tune
    
    @beam_twiss_x_tune_attr.write
    def beam_twiss_x_tune_attr(self, value):
        self.beam_twiss_x_tune = float(value)
    
    @attribute(name="beam/twiss/x/alpha", dtype=float, max_dim_x=4096, format=AttrDataFormat.SPECTRUM, access=AttrWriteType.READ_WRITE)
    def beam_twiss_x_alpha_attr(self):
        # Ensure pure Python floats, not numpy types
        if isinstance(self.beam_twiss_x_alpha, np.ndarray):
            return [float(x) for x in self.beam_twiss_x_alpha.astype(float).tolist()]
        else:
            return [float(x) for x in list(self.beam_twiss_x_alpha)]
    
    @beam_twiss_x_alpha_attr.write
    def beam_twiss_x_alpha_attr(self, value):
        # Tango passes lists of Python floats for SPECTRUM attributes
        if isinstance(value, np.ndarray):
            self.beam_twiss_x_alpha = value.astype(np.float64)
        elif isinstance(value, (list, tuple)):
            self.beam_twiss_x_alpha = np.asarray([float(v) for v in value], dtype=np.float64)
        else:
            self.beam_twiss_x_alpha = np.asarray([float(value)], dtype=np.float64)
    
    @attribute(name="beam/twiss/x/beta", dtype=float, max_dim_x=4096, format=AttrDataFormat.SPECTRUM, access=AttrWriteType.READ_WRITE)
    def beam_twiss_x_beta_attr(self):
        # Ensure pure Python floats, not numpy types
        if isinstance(self.beam_twiss_x_beta, np.ndarray):
            return [float(x) for x in self.beam_twiss_x_beta.astype(float).tolist()]
        else:
            return [float(x) for x in list(self.beam_twiss_x_beta)]
    
    @beam_twiss_x_beta_attr.write
    def beam_twiss_x_beta_attr(self, value):
        # Tango passes lists of Python floats for SPECTRUM attributes
        if isinstance(value, np.ndarray):
            self.beam_twiss_x_beta = value.astype(np.float64)
        elif isinstance(value, (list, tuple)):
            self.beam_twiss_x_beta = np.asarray([float(v) for v in value], dtype=np.float64)
        else:
            self.beam_twiss_x_beta = np.asarray([float(value)], dtype=np.float64)
    
    @attribute(name="beam/twiss/x/nu", dtype=float, max_dim_x=4096, format=AttrDataFormat.SPECTRUM, access=AttrWriteType.READ_WRITE)
    def beam_twiss_x_nu_attr(self):
        # Ensure pure Python floats, not numpy types
        if isinstance(self.beam_twiss_x_nu, np.ndarray):
            return [float(x) for x in self.beam_twiss_x_nu.astype(float).tolist()]
        else:
            return [float(x) for x in list(self.beam_twiss_x_nu)]
    
    @beam_twiss_x_nu_attr.write
    def beam_twiss_x_nu_attr(self, value):
        # Tango passes lists of Python floats for SPECTRUM attributes
        if isinstance(value, np.ndarray):
            self.beam_twiss_x_nu = value.astype(np.float64)
        elif isinstance(value, (list, tuple)):
            self.beam_twiss_x_nu = np.asarray([float(v) for v in value], dtype=np.float64)
        else:
            self.beam_twiss_x_nu = np.asarray([float(value)], dtype=np.float64)
    
    @attribute(name="beam/twiss/y/tune", dtype=float, access=AttrWriteType.READ_WRITE)
    def beam_twiss_y_tune_attr(self):
        return self.beam_twiss_y_tune
    
    @beam_twiss_y_tune_attr.write
    def beam_twiss_y_tune_attr(self, value):
        self.beam_twiss_y_tune = float(value)
    
    @attribute(name="beam/twiss/y/alpha", dtype=float, max_dim_x=4096, format=AttrDataFormat.SPECTRUM, access=AttrWriteType.READ_WRITE)
    def beam_twiss_y_alpha_attr(self):
        # Ensure pure Python floats, not numpy types
        if isinstance(self.beam_twiss_y_alpha, np.ndarray):
            return [float(x) for x in self.beam_twiss_y_alpha.astype(float).tolist()]
        else:
            return [float(x) for x in list(self.beam_twiss_y_alpha)]
    
    @beam_twiss_y_alpha_attr.write
    def beam_twiss_y_alpha_attr(self, value):
        # Tango passes lists of Python floats for SPECTRUM attributes
        if isinstance(value, np.ndarray):
            self.beam_twiss_y_alpha = value.astype(np.float64)
        elif isinstance(value, (list, tuple)):
            self.beam_twiss_y_alpha = np.asarray([float(v) for v in value], dtype=np.float64)
        else:
            self.beam_twiss_y_alpha = np.asarray([float(value)], dtype=np.float64)
    
    @attribute(name="beam/twiss/y/beta", dtype=float, max_dim_x=4096, format=AttrDataFormat.SPECTRUM, access=AttrWriteType.READ_WRITE)
    def beam_twiss_y_beta_attr(self):
        # Ensure pure Python floats, not numpy types
        if isinstance(self.beam_twiss_y_beta, np.ndarray):
            return [float(x) for x in self.beam_twiss_y_beta.astype(float).tolist()]
        else:
            return [float(x) for x in list(self.beam_twiss_y_beta)]
    
    @beam_twiss_y_beta_attr.write
    def beam_twiss_y_beta_attr(self, value):
        # Tango passes lists of Python floats for SPECTRUM attributes
        if isinstance(value, np.ndarray):
            self.beam_twiss_y_beta = value.astype(np.float64)
        elif isinstance(value, (list, tuple)):
            self.beam_twiss_y_beta = np.asarray([float(v) for v in value], dtype=np.float64)
        else:
            self.beam_twiss_y_beta = np.asarray([float(value)], dtype=np.float64)
    
    @attribute(name="beam/twiss/y/nu", dtype=float, max_dim_x=4096, format=AttrDataFormat.SPECTRUM, access=AttrWriteType.READ_WRITE)
    def beam_twiss_y_nu_attr(self):
        # Ensure pure Python floats, not numpy types
        if isinstance(self.beam_twiss_y_nu, np.ndarray):
            return [float(x) for x in self.beam_twiss_y_nu.astype(float).tolist()]
        else:
            return [float(x) for x in list(self.beam_twiss_y_nu)]
    
    @beam_twiss_y_nu_attr.write
    def beam_twiss_y_nu_attr(self, value):
        # Tango passes lists of Python floats for SPECTRUM attributes
        if isinstance(value, np.ndarray):
            self.beam_twiss_y_nu = value.astype(np.float64)
        elif isinstance(value, (list, tuple)):
            self.beam_twiss_y_nu = np.asarray([float(v) for v in value], dtype=np.float64)
        else:
            self.beam_twiss_y_nu = np.asarray([float(value)], dtype=np.float64)
    
    @attribute(name="beam/twiss/names", dtype=str, max_dim_x=4096, format=AttrDataFormat.SPECTRUM, access=AttrWriteType.READ_WRITE)
    def beam_twiss_names_attr(self):
        return self.beam_twiss_names
    
    @beam_twiss_names_attr.write
    def beam_twiss_names_attr(self, value):
        # Tango passes string arrays as list of strings
        if isinstance(value, (list, tuple)):
            self.beam_twiss_names = [str(v) for v in value]
        else:
            self.beam_twiss_names = [str(value)]



# ===============================================================
# 2. BPM MANAGER DEVICE
# ===============================================================

class BPMManagerDevice(Device, AsyncMixin):
    """
    Virtual BPM aggregator:

        Tango device: SOLEIL/BPM/MANAGER
        Server:       PHYSICS/SOLEIL

    Provides:
        bpm_names[]
        bpm_x[]
        bpm_y[]
    """

    def init_device(self):
        super().init_device()
        self._start_async()

        logger.info("Initializing BPMManagerDevice")

        self.bpm_names = []
        self.bpm_x = np.zeros(1)
        self.bpm_y = np.zeros(1)

        self._refresh()
        self.set_state(DevState.ON)

    def _refresh(self):
        try:
            update_manager = get_update_manager()
            self.bpm_names = update_manager.peek_engine(
                LatticeElementPropertyID("BPM", "names")
            )
            self.bpm_x = np.asarray(
                update_manager.peek_engine(
                    LatticeElementPropertyID("BPM", "x")
                )
            )
            self.bpm_y = np.asarray(
                update_manager.peek_engine(
                    LatticeElementPropertyID("BPM", "y")
                )
            )
        except Exception as e:
            logger.error(f"BPMManagerDevice refresh failed: {e}")

    @attribute(dtype=str,  max_dim_x=4096, format=AttrDataFormat.SPECTRUM)
    def bpm_names_attr(self):
        return self.bpm_names

    @attribute(dtype=float, max_dim_x=4096, format=AttrDataFormat.SPECTRUM)
    def bpm_x_attr(self):
        return self.bpm_x

    @attribute(dtype=float, max_dim_x=4096, format=AttrDataFormat.SPECTRUM)
    def bpm_y_attr(self):
        return self.bpm_y


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
        logger.info("Initializing TuneDevice")

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
    def tune_x_attr(self):
        return self.tune_x
    
    @tune_x_attr.write
    def tune_x_attr(self, value):
        self.tune_x = float(value)

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE)
    def tune_y_attr(self):
        return self.tune_y
    
    @tune_y_attr.write
    def tune_y_attr(self, value):
        self.tune_y = float(value)


# ===============================================================
# 4. OTHER PVs DEVICE
# ===============================================================

class OtherPVsDevice(Device):
    """
    Virtual provider for miscellaneous global PVs:

        SOLEIL/PHYSICS/OTHER_PVS
    """

    def init_device(self):
        super().init_device()
        logger.info("Initializing OtherPVsDevice")

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
        logger.info("Initializing MasterClockDevice")

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
                DevicePropertyID(self.name, "frequency")
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
