from typing import List, Optional, Sequence, Dict
import itertools

import numpy as np
from tango import AttrQuality, AttrWriteType, DevState, DeviceProxy
from tango.server import Device, attribute, command, device_property

from ....core.model.orbit import Orbit
from ....core.model.twiss import TwissWithAggregatedKValues
from ....core.utils.logger import get_logger
from ....custom_epics.data.constants import config, special_pvs

logger = get_logger()

class TwissOrbitDevice(Device):
    """Tango device for managing Twiss parameters and beam orbit measurements."""

    # Device properties
    Host = device_property(dtype=str, default_value="localhost")
    Port = device_property(dtype=int, default_value=10000)
    Prefix = device_property(dtype=str, default_value="beam")

    def init_device(self):
        """Initialize the device."""
        Device.init_device(self)
        self.set_state(DevState.ON)
        
        # Initialize orbit arrays
        self._orbit_x = np.zeros(config.n_elements, dtype=float)
        self._orbit_y = np.zeros(config.n_elements, dtype=float)
        self._orbit_x0 = np.zeros(config.n_elements, dtype=float)
        self._orbit_names = np.array([""] * config.n_elements, dtype=str)
        self._orbit_found = 0

        # Initialize Twiss parameters
        self._twiss_alpha_x = np.zeros(config.n_elements, dtype=float)
        self._twiss_beta_x = np.zeros(config.n_elements, dtype=float)
        self._twiss_nu_x = np.zeros(config.n_elements, dtype=float)
        self._twiss_alpha_y = np.zeros(config.n_elements, dtype=float)
        self._twiss_beta_y = np.zeros(config.n_elements, dtype=float)
        self._twiss_nu_y = np.zeros(config.n_elements, dtype=float)
        self._twiss_names = np.array([""] * config.n_elements, dtype=str)
        
        # Initialize BPM data
        self._bpm_data = np.empty([2048], np.int16)
        self._bpm_data.fill(-2 ** 15 + 1)
        self._bpm_counter = itertools.count()
        
        # Initialize magnet strengths
        self._magnet_strengths = {}
        
        logger.info("Device initialized successfully")

    def _validate_array_length(self, data: Sequence, name: str) -> None:
        """Validate that array length matches n_elements."""
        if len(data) != config.n_elements:
            raise ValueError(f"{name} must have length {config.n_elements}, got {len(data)}")

    # Orbit attributes
    @attribute(
        name="beam/orbit/x",
        dtype=('double',),
        access=AttrWriteType.READ_WRITE,
        label="X orbit",
        unit="mm",
        format="%6.3f",
        max_dim_x=config.n_elements,
    )
    def orbit_x(self) -> List[float]:
        return self._orbit_x.tolist()

    @orbit_x.write
    def orbit_x(self, value: List[float]):
        self._validate_array_length(value, "orbit_x")
        self._orbit_x = np.array(value, dtype=float)
        logger.info("Updated orbit_x")

    @attribute(
        name="beam/orbit/y",
        dtype=('double',),
        access=AttrWriteType.READ_WRITE,
        label="Y orbit",
        unit="mm",
        format="%6.3f",
        max_dim_x=config.n_elements,
    )
    def orbit_y(self) -> List[float]:
        return self._orbit_y.tolist()

    @orbit_y.write
    def orbit_y(self, value: List[float]):
        self._validate_array_length(value, "orbit_y")
        self._orbit_y = np.array(value, dtype=float)
        logger.info("Updated orbit_y")

    @attribute(
        name="beam/orbit/x0",
        dtype=('double',),
        access=AttrWriteType.READ_WRITE,
        label="X0 orbit",
        unit="mm",
        format="%6.3f",
        max_dim_x=config.n_elements,
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
        max_dim_x=config.n_elements,
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

    # Twiss attributes
    @attribute(
        name="beam/twiss/x/alpha",
        dtype=('double',),
        access=AttrWriteType.READ_WRITE,
        label="X alpha",
        format="%6.3f",
        max_dim_x=config.n_elements,
    )
    def twiss_alpha_x(self) -> List[float]:
        return self._twiss_alpha_x.tolist()

    @twiss_alpha_x.write
    def twiss_alpha_x(self, value: List[float]):
        self._validate_array_length(value, "twiss_alpha_x")
        self._twiss_alpha_x = np.array(value, dtype=float)
        logger.info("Updated twiss_alpha_x")

    @attribute(
        name="beam/twiss/x/beta",
        dtype=('double',),
        access=AttrWriteType.READ_WRITE,
        label="X beta",
        format="%6.3f",
        max_dim_x=config.n_elements,
    )
    def twiss_beta_x(self) -> List[float]:
        return self._twiss_beta_x.tolist()

    @twiss_beta_x.write
    def twiss_beta_x(self, value: List[float]):
        self._validate_array_length(value, "twiss_beta_x")
        self._twiss_beta_x = np.array(value, dtype=float)
        logger.info("Updated twiss_beta_x")

    @attribute(
        name="beam/twiss/x/nu",
        dtype=('double',),
        access=AttrWriteType.READ_WRITE,
        label="X nu",
        format="%6.3f",
        max_dim_x=config.n_elements,
    )
    def twiss_nu_x(self) -> List[float]:
        return self._twiss_nu_x.tolist()

    @twiss_nu_x.write
    def twiss_nu_x(self, value: List[float]):
        self._validate_array_length(value, "twiss_nu_x")
        self._twiss_nu_x = np.array(value, dtype=float)
        logger.info("Updated twiss_nu_x")

    @attribute(
        name="beam/twiss/y/alpha",
        dtype=('double',),
        access=AttrWriteType.READ_WRITE,
        label="Y alpha",
        format="%6.3f",
        max_dim_x=config.n_elements,
    )
    def twiss_alpha_y(self) -> List[float]:
        return self._twiss_alpha_y.tolist()

    @twiss_alpha_y.write
    def twiss_alpha_y(self, value: List[float]):
        self._validate_array_length(value, "twiss_alpha_y")
        self._twiss_alpha_y = np.array(value, dtype=float)
        logger.info("Updated twiss_alpha_y")

    @attribute(
        name="beam/twiss/y/beta",
        dtype=('double',),
        access=AttrWriteType.READ_WRITE,
        label="Y beta",
        format="%6.3f",
        max_dim_x=config.n_elements,
    )
    def twiss_beta_y(self) -> List[float]:
        return self._twiss_beta_y.tolist()

    @twiss_beta_y.write
    def twiss_beta_y(self, value: List[float]):
        self._validate_array_length(value, "twiss_beta_y")
        self._twiss_beta_y = np.array(value, dtype=float)
        logger.info("Updated twiss_beta_y")

    @attribute(
        name="beam/twiss/y/nu",
        dtype=('double',),
        access=AttrWriteType.READ_WRITE,
        label="Y nu",
        format="%6.3f",
        max_dim_x=config.n_elements,
    )
    def twiss_nu_y(self) -> List[float]:
        return self._twiss_nu_y.tolist()

    @twiss_nu_y.write
    def twiss_nu_y(self, value: List[float]):
        self._validate_array_length(value, "twiss_nu_y")
        self._twiss_nu_y = np.array(value, dtype=float)
        logger.info("Updated twiss_nu_y")

    @attribute(
        name="beam/twiss/names",
        dtype=('str',),
        access=AttrWriteType.READ_WRITE,
        label="Twiss names",
        max_dim_x=config.n_elements,
    )
    def twiss_names(self) -> List[str]:
        return self._twiss_names.tolist()

    @twiss_names.write
    def twiss_names(self, value: List[str]):
        self._validate_array_length(value, "twiss_names")
        self._twiss_names = np.array(value, dtype=str)
        logger.info("Updated twiss_names")

    # BPM attributes
    @attribute(
        name="beam/bpm/data",
        dtype=('int16',),
        access=AttrWriteType.READ_WRITE,
        label="BPM data",
        max_dim_x=2048,
    )
    def bpm_data(self) -> List[int]:
        return self._bpm_data.tolist()

    @bpm_data.write
    def bpm_data(self, value: List[int]):
        if len(value) != 2048:
            raise ValueError("BPM data must have length 2048")
        self._bpm_data = np.array(value, dtype=np.int16)
        logger.info("Updated BPM data")

    @attribute(
        name="beam/bpm/count",
        dtype=int,
        access=AttrWriteType.READ,
        label="BPM counter",
    )
    def bpm_count(self) -> int:
        return next(self._bpm_counter)

    @command
    def update_magnet_strengths(self, pv_names: List[str], values: List[float]):
        """Update magnet strengths for multiple magnets at once."""
        if len(pv_names) != len(values):
            raise ValueError("Number of PV names must match number of values")
        
        for pv_name, value in zip(pv_names, values):
            self._magnet_strengths[pv_name] = float(value)
            logger.info(f"Updated magnet strength {pv_name} to {value}")

    @command
    def reset(self):
        """Reset all attributes to their initial values."""
        self.init_device()
        logger.info("Device reset to initial values") 