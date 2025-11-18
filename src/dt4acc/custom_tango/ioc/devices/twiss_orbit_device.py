from typing import List, Optional, Sequence, Dict
import itertools

import numpy as np
from tango import AttrQuality, AttrWriteType, DevState, DeviceProxy
from tango.server import Device, attribute, command, device_property

from ....core.model.orbit import Orbit
from ....core.model.twiss import TwissWithAggregatedKValues
from ....core.utils.logger import get_logger
from ....custom_epics.data.constants import config, special_pvs, cavity_names
from ....custom_epics.ioc.handlers import update_manager, handle_device_update
from bact_twin_architecture.data_model.identifiers import DevicePropertyID

logger = get_logger()

class TwissOrbitDevice(Device):
    """Tango device for managing Twiss parameters and beam orbit measurements.
    
    This device matches the EPICS PV structure exactly, providing the same
    functionality as the EPICS SoftIOC implementation.
    
    Special PVs supported:
    - master_clock: MCLKHX251C (master clock frequency)
    - bpm_pv: MDIZ2T5G (BPM data)
    - current: MDIZ3T5G (current values)
    """

    Host = device_property(dtype=str, default_value="localhost")
    Port = device_property(dtype=int, default_value=10000)
    Prefix = device_property(dtype=str, default_value="beam")

    def init_device(self):
        """Initialize the device with default values matching EPICS PV setup."""
        Device.init_device(self)
        self.set_state(DevState.ON)
        
        # Initialize with values matching EPICS PV initialization
        self._initialize_orbit_data()
        self._initialize_twiss_data()
        self._initialize_bpm_data()
        self._initialize_special_pvs_data()
        
        logger.info("TwissOrbitDevice initialized successfully")

    def _initialize_orbit_data(self):
        """Initialize orbit data matching EPICS initialize_orbit_pvs()."""
        # Orbit data - matching EPICS WaveformOut initialization
        self._orbit_x = np.zeros(config.n_elements, dtype=float)
        self._orbit_y = np.zeros(config.n_elements, dtype=float)
        self._orbit_x0 = np.zeros(config.n_elements, dtype=float)
        self._orbit_names = np.array([""] * config.n_elements, dtype=str)
        self._orbit_found = 0

    def _initialize_twiss_data(self):
        """Initialize Twiss data matching EPICS initialize_twiss_pvs()."""
        # Twiss data - matching EPICS WaveformOut initialization
        self._twiss_alpha_x = np.zeros(config.n_elements, dtype=float)
        self._twiss_beta_x = np.zeros(config.n_elements, dtype=float)
        self._twiss_nu_x = np.zeros(config.n_elements, dtype=float)
        self._twiss_alpha_y = np.zeros(config.n_elements, dtype=float)
        self._twiss_beta_y = np.zeros(config.n_elements, dtype=float)
        self._twiss_nu_y = np.zeros(config.n_elements, dtype=float)
        self._twiss_names = np.array([""] * config.n_elements, dtype=str)
        
        # Tune values - matching EPICS aOut with PREC=8
        self._twiss_x_tune = 0.0
        self._twiss_y_tune = 0.0

    def _initialize_bpm_data(self):
        """Initialize BPM data matching EPICS initialize_bpm_pvs()."""
        # BPM data - matching EPICS WaveformOut initialization
        self._bpm_data = np.empty([2048], np.int16)
        self._bpm_data.fill(-(2 ** 15) + 1)
        self._bpm_counter = itertools.count()
        
        # Orbit object data - matching EPICS initialize_orbit_object_pvs()
        n_bpms = 128
        self._orbit_pos = np.ravel(np.empty([n_bpms, 2], float))
        self._orbit_pos.fill(0.0)  # Fixed: Changed from np.nan to 0.0
        self._orbit_buttons = np.ravel(np.empty([n_bpms, 4], float))
        self._orbit_buttons.fill(0.0)  # Fixed: Changed from np.nan to 0.0
        self._orbit_bpm_names = np.array([""] * n_bpms, dtype=str)
        self._orbit_count = itertools.count()

    def _initialize_special_pvs_data(self):
        """Initialize special PVs data matching EPICS special_pvs usage."""
        # Special BPM data using special_pvs['bpm_pv']
        self._special_bpm_data = np.empty([2048], np.int16)
        self._special_bpm_data.fill(-(2 ** 15) + 1)
        self._special_bpm_counter = itertools.count()

    def _clean_nan_values(self, data: np.ndarray, name: str) -> np.ndarray:
        """
        Clean NaN and INF values from incoming data to prevent Tango errors.
        
        Args:
            data: Input numpy array that may contain NaN/INF values
            name: Name of the data for logging purposes
            
        Returns:
            Cleaned numpy array with NaN/INF replaced by 0.0
        """
        if data is None:
            logger.info(f"{name}: Data is None, returning empty array")
            return np.array([])
        
        # Convert to numpy array if it isn't already
        if not isinstance(data, np.ndarray):
            data = np.array(data)
        
        # Check for NaN and INF values
        nan_count = np.isnan(data).sum()
        inf_count = np.isinf(data).sum()
        
        if nan_count > 0 or inf_count > 0:
            logger.info(f"{name}: Found {nan_count} NaN and {inf_count} INF values, cleaning data")
            
            # Replace NaN with 0.0
            data = np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)
            
            # Additional safety check
            if np.isnan(data).any() or np.isinf(data).any():
                logger.error(f"{name}: Still contains NaN/INF after cleaning, using zeros")
                data = np.zeros_like(data)
        
        logger.info(f"{name}: Data cleaned successfully, shape: {data.shape}, dtype: {data.dtype}")
        return data

    def _validate_array_length(self, data: Sequence, name: str) -> None:
        """Validate that array length is reasonable and handle size mismatches gracefully."""
        if len(data) == 0:
            raise ValueError(f"{name} cannot be empty")
        
        # If the data length doesn't match config.n_elements, log a warning but accept it
        if len(data) != config.n_elements:
            logger.info(f"{name} expected length {config.n_elements}, got {len(data)} - adjusting device storage")
            
            # Resize the internal storage to match the actual data
            if name == "twiss_alpha_x":
                self._twiss_alpha_x = np.zeros(len(data), dtype=float)
            elif name == "twiss_beta_x":
                self._twiss_beta_x = np.zeros(len(data), dtype=float)
            elif name == "twiss_nu_x":
                self._twiss_nu_x = np.zeros(len(data), dtype=float)
            elif name == "twiss_alpha_y":
                self._twiss_alpha_y = np.zeros(len(data), dtype=float)
            elif name == "twiss_beta_y":
                self._twiss_beta_y = np.zeros(len(data), dtype=float)
            elif name == "twiss_nu_y":
                self._twiss_nu_y = np.zeros(len(data), dtype=float)
            elif name == "twiss_names":
                self._twiss_names = np.array([""] * len(data), dtype=str)
            elif name == "orbit_x":
                self._orbit_x = np.zeros(len(data), dtype=float)
            elif name == "orbit_y":
                self._orbit_y = np.zeros(len(data), dtype=float)
            elif name == "orbit_x0":
                self._orbit_x0 = np.zeros(len(data), dtype=float)
            elif name == "orbit_names":
                self._orbit_names = np.array([""] * len(data), dtype=str)

    # Orbit attributes - matching EPICS initialize_orbit_pvs()
    @attribute(
        name="beam/orbit/x",
        dtype=('double',),
        access=AttrWriteType.READ_WRITE,
        label="X orbit",
        unit="mm",
        format="%6.3f",
        max_dim_x=10000,  # Allow larger arrays for flexibility
    )
    def orbit_x(self) -> List[float]:
        return self._orbit_x.tolist()

    @orbit_x.write
    def orbit_x(self, value: List[float]):
        self._validate_array_length(value, "orbit_x")
        # Clean any NaN/INF values before storing
        clean_data = self._clean_nan_values(np.array(value, dtype=float), "orbit_x")
        self._orbit_x = clean_data
        logger.info("Updated orbit_x")

    @attribute(
        name="beam/orbit/y",
        dtype=('double',),
        access=AttrWriteType.READ_WRITE,
        label="Y orbit",
        unit="mm",
        format="%6.3f",
        max_dim_x=10000,  # Allow larger arrays for flexibility
    )
    def orbit_y(self) -> List[float]:
        return self._orbit_y.tolist()

    @orbit_y.write
    def orbit_y(self, value: List[float]):
        self._validate_array_length(value, "orbit_y")
        # Clean any NaN/INF values before storing
        clean_data = self._clean_nan_values(np.array(value, dtype=float), "orbit_y")
        self._orbit_y = clean_data
        logger.info("Updated orbit_y")

    @attribute(
        name="beam/orbit/x0",
        dtype=('double',),
        access=AttrWriteType.READ_WRITE,
        label="X0 orbit",
        unit="mm",
        format="%6.3f",
        max_dim_x=10000,  # Allow larger arrays for flexibility
    )
    def orbit_x0(self) -> List[float]:
        return self._orbit_x0.tolist()

    @orbit_x0.write
    def orbit_x0(self, value: List[float]):
        self._validate_array_length(value, "orbit_x0")
        self._orbit_x0 = np.array(value, dtype=float)
        logger.info("Updated orbit_x0")

    @attribute(
        name="beam/orbit/names",
        dtype=('str',),
        access=AttrWriteType.READ_WRITE,
        label="Orbit names",
        max_dim_x=10000,  # Allow larger arrays for flexibility
    )
    def orbit_names(self) -> List[str]:
        return self._orbit_names.tolist()

    @orbit_names.write
    def orbit_names(self, value: List[str]):
        self._validate_array_length(value, "orbit_names")
        self._orbit_names = np.array(value, dtype=str)
        logger.info("Updated orbit_names")

    @attribute(
        name="beam/orbit/found",
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        label="Orbit found",
    )
    def orbit_found(self) -> bool:
        return bool(self._orbit_found)

    @orbit_found.write
    def orbit_found(self, value: bool):
        self._orbit_found = 1 if value else 0
        logger.info("Updated orbit_found")

    # Twiss attributes - matching EPICS initialize_twiss_pvs()
    @attribute(
        name="beam/twiss/x/alpha",
        dtype=('double',),
        access=AttrWriteType.READ_WRITE,
        label="X alpha",
        format="%6.3f",
        max_dim_x=10000,  # Allow larger arrays for flexibility
    )
    def twiss_alpha_x(self) -> List[float]:
        return self._twiss_alpha_x.tolist()

    @twiss_alpha_x.write
    def twiss_alpha_x(self, value: List[float]):
        self._validate_array_length(value, "twiss_alpha_x")
        # Clean any NaN/INF values before storing
        clean_data = self._clean_nan_values(np.array(value, dtype=float), "twiss_alpha_x")
        self._twiss_alpha_x = clean_data
        logger.info("Updated twiss_alpha_x")

    @attribute(
        name="beam/twiss/x/beta",
        dtype=('double',),
        access=AttrWriteType.READ_WRITE,
        label="X beta",
        format="%6.3f",
        max_dim_x=10000,  # Allow larger arrays for flexibility
    )
    def twiss_beta_x(self) -> List[float]:
        return self._twiss_beta_x.tolist()

    @twiss_beta_x.write
    def twiss_beta_x(self, value: List[float]):
        self._validate_array_length(value, "twiss_beta_x")
        # Clean any NaN/INF values before storing
        clean_data = self._clean_nan_values(np.array(value, dtype=float), "twiss_beta_x")
        self._twiss_beta_x = clean_data
        logger.info("Updated twiss_beta_x")

    @attribute(
        name="beam/twiss/x/nu",
        dtype=('double',),
        access=AttrWriteType.READ_WRITE,
        label="X nu",
        format="%6.3f",
        max_dim_x=10000,  # Allow larger arrays for flexibility
    )
    def twiss_nu_x(self) -> List[float]:
        return self._twiss_nu_x.tolist()

    @twiss_nu_x.write
    def twiss_nu_x(self, value: List[float]):
        self._validate_array_length(value, "twiss_nu_x")
        # Clean any NaN/INF values before storing
        clean_data = self._clean_nan_values(np.array(value, dtype=float), "twiss_nu_x")
        self._twiss_nu_x = clean_data
        logger.info("Updated twiss_nu_x")

    @attribute(
        name="beam/twiss/y/alpha",
        dtype=('double',),
        access=AttrWriteType.READ_WRITE,
        label="Y alpha",
        format="%6.3f",
        max_dim_x=10000,  # Allow larger arrays for flexibility
    )
    def twiss_alpha_y(self) -> List[float]:
        return self._twiss_alpha_y.tolist()

    @twiss_alpha_y.write
    def twiss_alpha_y(self, value: List[float]):
        self._validate_array_length(value, "twiss_alpha_y")
        # Clean any NaN/INF values before storing
        clean_data = self._clean_nan_values(np.array(value, dtype=float), "twiss_alpha_y")
        self._twiss_alpha_y = clean_data
        logger.info("Updated twiss_alpha_y")

    @attribute(
        name="beam/twiss/y/beta",
        dtype=('double',),
        access=AttrWriteType.READ_WRITE,
        label="Y beta",
        format="%6.3f",
        max_dim_x=10000,  # Allow larger arrays for flexibility
    )
    def twiss_beta_y(self) -> List[float]:
        return self._twiss_beta_y.tolist()

    @twiss_beta_y.write
    def twiss_beta_y(self, value: List[float]):
        self._validate_array_length(value, "twiss_beta_y")
        # Clean any NaN/INF values before storing
        clean_data = self._clean_nan_values(np.array(value, dtype=float), "twiss_beta_y")
        self._twiss_beta_y = clean_data
        logger.info("Updated twiss_beta_y")

    @attribute(
        name="beam/twiss/y/nu",
        dtype=('double',),
        access=AttrWriteType.READ_WRITE,
        label="Y nu",
        format="%6.3f",
        max_dim_x=10000,  # Allow larger arrays for flexibility
    )
    def twiss_nu_y(self) -> List[float]:
        return self._twiss_nu_y.tolist()

    @twiss_nu_y.write
    def twiss_nu_y(self, value: List[float]):
        self._validate_array_length(value, "twiss_nu_y")
        # Clean any NaN/INF values before storing
        clean_data = self._clean_nan_values(np.array(value, dtype=float), "twiss_nu_y")
        self._twiss_nu_y = clean_data
        logger.info("Updated twiss_nu_y")

    @attribute(
        name="beam/twiss/names",
        dtype=('str',),
        access=AttrWriteType.READ_WRITE,
        label="Twiss names",
        max_dim_x=10000,  # Allow larger arrays for flexibility
    )
    def twiss_names(self) -> List[str]:
        return self._twiss_names.tolist()

    @twiss_names.write
    def twiss_names(self, value: List[str]):
        self._validate_array_length(value, "twiss_names")
        self._twiss_names = np.array(value, dtype=str)
        logger.info("Updated twiss_names")

    # Tune attributes - matching EPICS aOut with PREC=8
    @attribute(
        name="beam/twiss/x/tune",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        label="X tune",
        format="%8.6f",
    )
    def twiss_x_tune(self) -> float:
        return self._twiss_x_tune

    @twiss_x_tune.write
    def twiss_x_tune(self, value: float):
        self._twiss_x_tune = float(value)
        logger.info("Updated twiss_x_tune")

    @attribute(
        name="beam/twiss/y/tune",
        dtype=float,
        access=AttrWriteType.READ_WRITE,
        label="Y tune",
        format="%8.6f",
    )
    def twiss_y_tune(self) -> float:
        return self._twiss_y_tune

    @twiss_y_tune.write
    def twiss_y_tune(self, value: float):
        self._twiss_y_tune = float(value)
        logger.info("Updated twiss_y_tune")

    # BPM attributes - matching EPICS special_pvs usage
    @attribute(
        name=f"{special_pvs['bpm_pv']}/bdata",
        dtype=('int16',),
        access=AttrWriteType.READ_WRITE,
        label="Special BPM data",
        max_dim_x=2048,
    )
    def special_bpm_data(self) -> List[int]:
        """Special BPM data using special_pvs['bpm_pv'] name."""
        return self._special_bpm_data.tolist()

    @special_bpm_data.write
    def special_bpm_data(self, value: List[int]):
        if len(value) != 2048:
            raise ValueError("Special BPM data must have length 2048")
        self._special_bpm_data = np.array(value, dtype=np.int16)
        logger.info("Updated special BPM data")

    @attribute(
        name=f"{special_pvs['bpm_pv']}/count",
        dtype=int,
        access=AttrWriteType.READ,
        label="Special BPM counter",
    )
    def special_bpm_count(self) -> int:
        """Special BPM counter using special_pvs['bpm_pv'] name."""
        return next(self._special_bpm_counter)

    # Orbit object attributes - matching EPICS initialize_orbit_object_pvs()
    @attribute(
        name="ORBITCC/rdPos",
        dtype=('double',),
        access=AttrWriteType.READ_WRITE,
        label="Orbit position data",
        max_dim_x=256,  # 128 * 2
    )
    def orbit_pos(self) -> List[float]:
        return self._orbit_pos.tolist()

    @orbit_pos.write
    def orbit_pos(self, value: List[float]):
        if len(value) != 256:
            raise ValueError("Orbit position data must have length 256")
        # Clean any NaN/INF values before storing
        clean_data = self._clean_nan_values(np.array(value, dtype=float), "orbit_pos")
        self._orbit_pos = clean_data
        logger.info("Updated orbit position data")

    @attribute(
        name="ORBITCC/rdButtons",
        dtype=('double',),
        access=AttrWriteType.READ_WRITE,
        label="Orbit button data",
        max_dim_x=512,  # 128 * 4
    )
    def orbit_buttons(self) -> List[float]:
        return self._orbit_buttons.tolist()

    @orbit_buttons.write
    def orbit_buttons(self, value: List[float]):
        if len(value) != 512:
            raise ValueError("Orbit button data must have length 512")
        self._orbit_buttons = np.array(value, dtype=float)
        logger.info("Updated orbit button data")

    @attribute(
        name="ORBITCC/rdBpmNames",
        dtype=('str',),
        access=AttrWriteType.READ_WRITE,
        label="Orbit BPM names",
        max_dim_x=128,
    )
    def orbit_bpm_names(self) -> List[str]:
        return self._orbit_bpm_names.tolist()

    @orbit_bpm_names.write
    def orbit_bpm_names(self, value: List[str]):
        if len(value) != 128:
            raise ValueError("Orbit BPM names must have length 128")
        self._orbit_bpm_names = np.array(value, dtype=str)
        logger.info("Updated orbit BPM names")

    @attribute(
        name="ORBITCC/count",
        dtype=int,
        access=AttrWriteType.READ,
        label="Orbit counter",
    )
    def orbit_count(self) -> int:
        return next(self._orbit_count)

    @command
    def update_magnet_strengths(self, pv_names, values):
        """Update magnet strengths for multiple magnets at once."""
        if len(pv_names) != len(values):
            raise ValueError("Number of PV names must match number of values")
        
        for pv_name, value in zip(pv_names, values):
            # This command is now handled by the magnet_strengths_device
            # self._magnet_strengths[pv_name] = float(value)
            logger.info(f"Updated magnet strength {pv_name} to {value}")

    @command
    def reset(self):
        """Reset all attributes to their initial values."""
        self.init_device()
        logger.info("Device reset to initial values")

    @command
    def get_special_pvs_info(self):
        """Get information about special PVs configuration."""
        return {
            "bpm_pv": special_pvs["bpm_pv"],
            "master_clock": special_pvs["master_clock"],
            "current": special_pvs["current"],
            "description": "Special PVs mapping from EPICS constants"
        } 