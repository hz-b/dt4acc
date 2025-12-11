"""
Unified Tango devices for SOLEIL:
 - MasterClockDevice
 - CavityDevice
 - TuneDevice
 - OtherPVsDevice
 - register_all_devices() for ALL Tango devices

This file assumes MagnetDevice, PowerConverterDevice,
TwissOrbitDevice, BPMManagerDevice are already implemented.
"""

import asyncio
import threading
import numpy as np
from tango import DevState, DbDevInfo, Database, DevFailed
from tango.server import Device, attribute, device_property, AttrDataFormat, AttrWriteType

from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_epics.ioc.handlers import update_manager, handle_device_update
from dt4acc.custom_epics.data.querries import get_unique_power_converters, get_magnets_per_power_converters
from dt4acc.custom_epics.data.constants import cavity_names, ring_parameters, special_pvs
from bact_twin_architecture.data_model.identifiers import (
    DevicePropertyID,
    LatticeElementPropertyID
)

logger = get_logger()

# --------------------------------------------------------------------------------------
# 1. MASTER CLOCK DEVICE
# --------------------------------------------------------------------------------------

class MasterClockDevice(Device):
    """
    Tango wrapper around dt4acc master clock.
    Device name: SOLEIL/RF/MASTER_CLOCK
    """

    name = device_property(dtype=str, default_value="SOLEIL/RF/MASTER_CLOCK")

    def init_device(self):
        super().init_device()

        try:
            val = update_manager.device_value_from_peeking_engine(
                DevicePropertyID("master_clock", "reference_frequency")
            )
            self._frequency = float(val)
        except Exception:
            self._frequency = 0.0

        self.set_state(DevState.ON)
        logger.info("MasterClockDevice initialized.")

    @attribute(dtype=float, access=AttrWriteType.READ_WRITE)
    def frequency(self):
        return self._frequency

    @frequency.write
    def frequency(self, value):
        value = float(value)
        self._frequency = value
        handle_device_update("master_clock", "reference_frequency", value)

# --------------------------------------------------------------------------------------
# 2. CAVITY DEVICE
# --------------------------------------------------------------------------------------

class CavityDevice(Device):
    """
    Tango cavities, each mapped to dt4acc cavity model.
    Device names:
        SOLEIL/RF/<cavity_name>
    """

    name = device_property(dtype=str)
    cavity = device_property(dtype=str)

    def init_device(self):
        super().init_device()

        try:
            v = update_manager.device_value_from_peeking_engine(
                DevicePropertyID(self.cavity, "frequency")
            )
            self._frequency = float(v)
        except Exception:
            self._frequency = 0.0

        self._voltage = 0.0
        self._phase = 0.0

        logger.info(f"CavityDevice initialized for {self.cavity}")
        self.set_state(DevState.ON)

    # Frequency
    @attribute(dtype=float, access=AttrWriteType.READ_WRITE)
    def frequency(self):
        return self._frequency

    @frequency.write
    def frequency(self, value):
        value = float(value)
        self._frequency = value
        handle_device_update(self.cavity, "frequency", value)

    # Voltage
    @attribute(dtype=float, access=AttrWriteType.READ_WRITE)
    def voltage(self):
        return self._voltage

    @voltage.write
    def voltage(self, value):
        value = float(value)
        self._voltage = value
        handle_device_update(self.cavity, "voltage", value)

    # Phase
    @attribute(dtype=float, access=AttrWriteType.READ_WRITE)
    def phase(self):
        return self._phase

    @phase.write
    def phase(self, value):
        value = float(value)
        self._phase = value
        handle_device_update(self.cavity, "phase", value)

# --------------------------------------------------------------------------------------
# 3. TUNE DEVICE
# --------------------------------------------------------------------------------------

class TuneDevice(Device):
    """
    Provides horizontal & vertical tune values.
    Tango name: SOLEIL/PHYSICS/TUNE
    """

    name = device_property(dtype=str, default_value="SOLEIL/PHYSICS/TUNE")

    def init_device(self):
        super().init_device()
        self._update_values()
        self.set_state(DevState.ON)

    def _update_values(self):
        try:
            self.tune_x = float(update_manager.peek_engine(
                LatticeElementPropertyID("TUNE", "x")
            ))
            self.tune_y = float(update_manager.peek_engine(
                LatticeElementPropertyID("TUNE", "y")
            ))
        except Exception:
            self.tune_x = 0.0
            self.tune_y = 0.0

    @attribute(dtype=float)
    def tune_x_attr(self):
        return self.tune_x

    @attribute(dtype=float)
    def tune_y_attr(self):
        return self.tune_y


# --------------------------------------------------------------------------------------
# 4. OTHER PVS DEVICE
# --------------------------------------------------------------------------------------

class OtherPVsDevice(Device):
    """
    Virtual holder for global PVs (temperatures, states, etc.)
    Tango name: SOLEIL/PHYSICS/OTHER_PVS
    """

    name = device_property(dtype=str, default_value="SOLEIL/PHYSICS/OTHER_PVS")

    def init_device(self):
        super().init_device()
        self._values = {}
        self._load_initial_values()
        self.set_state(DevState.ON)

    def _load_initial_values(self):
        for gpv in special_pvs:
            try:
                val = update_manager.peek_engine(
                    LatticeElementPropertyID(gpv["element"], gpv["property"])
                )
                self._values[gpv["property"]] = float(val)
            except Exception:
                self._values[gpv["property"]] = 0

    @attribute(dtype=float)
    def temperature(self):
        return self._values.get("temperature", 0.0)

    @attribute(dtype=float)
    def vacuum(self):
        return self._values.get("vacuum", 0.0)
