from datetime import datetime
from typing import Sequence, List, Union, Optional
import itertools
import pandas as pd
import asyncio

import numpy as np
from tango import DeviceProxy, DevFailed, Database, DevState

from ...core.model.element_upate import ElementUpdate
from ...core.model.orbit import Orbit
from ...core.model.twiss import TwissWithAggregatedKValues, TwissForPlane
from ...core.utils.logger import get_logger
from ..config import SERVER_NAME, SERVER_INSTANCE, DEVICE_NAME_FORMAT
from ...custom_epics.data.constants import special_pvs, config
from ...custom_epics.utils.bpm_mimicry import BPMMimicry
from .bpm_data import BeamPositionPVs
from .create_or_update_pv import update_twiss_pv, update_orbit_pv, update_bpm_pv

logger = get_logger()

counter = itertools.count()


def clean_data_for_tango(data: Union[Sequence, np.ndarray, pd.Series], name: str = "data") -> np.ndarray:
    """
    Clean data by replacing NaN and INF values with safe defaults for Tango.

    Args:
        data: Input data that may contain NaN/INF values
        name: Name of the data for logging purposes

    Returns:
        Cleaned numpy array with NaN/INF replaced by safe values
    """
    if data is None:
        logger.warning(f"{name}: Data is None, returning empty array")
        return np.array([])

    # Convert to numpy array if it isn't already
    if isinstance(data, pd.Series):
        # Handle pandas Series more effectively
        data = data.fillna(0.0).values  # Replace NaN with 0.0 first
    elif not isinstance(data, np.ndarray):
        data = np.array(data)

    # Check for NaN and INF values
    nan_count = np.isnan(data).sum()
    inf_count = np.isinf(data).sum()

    if nan_count > 0 or inf_count > 0:
        logger.warning(f"{name}: Found {nan_count} NaN and {inf_count} INF values, cleaning data")

        # Replace NaN with 0.0
        data = np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)

        # Additional safety check
        if np.isnan(data).any() or np.isinf(data).any():
            logger.error(f"{name}: Still contains NaN/INF after cleaning, using zeros")
            data = np.zeros_like(data)

    logger.info(f"{name}: Data cleaned successfully, shape: {data.shape}, dtype: {data.dtype}")
    return data


def convert_to_list(data: Union[Sequence, np.ndarray]) -> List:
    """Convert sequence or numpy array to list with proper type handling"""
    if isinstance(data, np.ndarray):
        data = np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)
        return data.tolist()
    return list(data)


class CalculationResultView:
    def __init__(self, *, prefix):
        """Initialize the ResultView with a prefix."""
        self.prefix = prefix
        self.bpm_pvs = BeamPositionPVs(prefix=f"{self.prefix}:{special_pvs['bpm_pv']}")
        tmp = np.empty([2048], np.int16)
        tmp.fill(-2 ** 15 + 1)
        self.default_bpm_legacy_data = tmp
        self.orbit_object_data = None
        self.default_twiss = None
        self.bpm_mimicry = None

        # Device name templates using correct Tango format: server_name/instance_name/device_name
        # These are base device types, not specific instances
        self.twiss_orbit_device = "SimpleTangoServer/test/twiss_orbit_device"
        self.bpm_device = "SimpleTangoServer/test/bpm_device"

    def _get_device_name(self, element_id: str, device_type: str) -> str:
        """
        Generate device name based on element ID and device type.
        This allows for dynamic device naming instead of hardcoded values.
        Uses correct Tango format: server_name/instance_name/device_name
        """
        # Map element types to device naming patterns
        if device_type == "power_converter":
            return f"SimpleTangoServer/test/power_converter_{element_id}"
        elif device_type == "magnet":
            return f"SimpleTangoServer/test/magnet_{element_id}"
        elif device_type == "cavity":
            return f"SimpleTangoServer/test/cavity_{element_id}"
        elif device_type == "bpm":
            return f"SimpleTangoServer/test/bpm_{element_id}"
        else:
            # Default pattern for unknown device types
            return f"SimpleTangoServer/test/{device_type}_{element_id}"

    def _determine_device_type(self, element_id: str, property_name: str) -> str:
        """
        Determine device type based on element ID and property name.
        This is a heuristic that can be improved based on your naming conventions.
        """
        element_lower = element_id.lower()
        prop_lower = property_name.lower()

        # Check for power converter indicators - be more specific
        if any(indicator in element_lower for indicator in ['vs3p2t5r', 'vs', 'power', 'converter', 'pc']):
            return "power_converter"
        # Check for magnet indicators - be more specific
        elif any(indicator in element_lower for indicator in ['hs1md', 'magnet', 'quad', 'dipole', 'sext']):
            return "magnet"
        # Check for cavity indicators - be more specific
        elif any(indicator in element_lower for indicator in ['cavh', 'cavity']):
            return "cavity"
        # Check for BPM indicators - be more specific
        elif any(indicator in element_lower for indicator in ['bpm', 'position', 'mdiz']):
            return "bpm"
        # Check property name for clues
        elif 'set' in prop_lower or 'current' in prop_lower:
            return "power_converter"
        elif 'k' in prop_lower or 'strength' in prop_lower:
            return "magnet"
        else:
            # Default to power converter if uncertain
            return "power_converter"

    # dependency injection (push bpm mimicry when it is available
    def set_bpm_mimicry(self, bpm_mimicry):
        """Set BPM mimicry for legacy data handling."""
        if bpm_mimicry is None:
            logger.warning("BPM Mimicry is None, BPM data updates will be disabled")
        self.bpm_mimicry = bpm_mimicry

    async def push_value(self, elm_update: ElementUpdate):
        """Push a single value update to the device (like EPICS) - simplified without complex synchronization."""
        logger.info("*********in the push value*************************************** 0")
        print(f"[DEBUG] ResultView.push_value called with: {elm_update}")

        try:
            print(f"Pushing value from view: {elm_update}")
            # Handle main_strength property updates (maps to k_strength for both quadrupoles and sextupoles)
            if elm_update.property_name == "main_strength":
                logger.info(f"Updating {elm_update.element_id}:k_strength to {elm_update.value}")

                # For main_strength property, always use magnet device type
                device_type = "magnet"
                device_name = self._get_device_name(elm_update.element_id, device_type)

                logger.debug(f"Using device: {device_name} (type: {device_type})")

                # Simplified: direct device update without complex queuing
                try:
                    device = DeviceProxy(device_name)
                    device.write_attribute("k_strength", elm_update.value)
                    logger.info(
                        f"Successfully updated main_strength from push values {elm_update.element_id}:k_strength")
                except Exception as e:
                    logger.error(f"Failed to update {elm_update.element_id}:k_strength: {e}")
                    raise

            # Handle K property updates (quadrupole strength)
            elif elm_update.property_name == "K":
                logger.info(f"Updating {elm_update.element_id}:k_strength to {elm_update.value}")

                # For K property, always use magnet device type
                device_type = "magnet"
                device_name = self._get_device_name(elm_update.element_id, device_type)

                logger.debug(f"Using device: {device_name} (type: {device_type})")

                # Simplified: direct device update
                try:
                    device = DeviceProxy(device_name)
                    device.write_attribute("k_strength", elm_update.value)
                    logger.info(f"Successfully updated K strength from push values {elm_update.element_id}:k_strength")
                except Exception as e:
                    logger.error(f"Failed to update {elm_update.element_id}:k_strength: {e}")
                    raise

            # Handle H property updates (sextupole strength)
            elif elm_update.property_name == "H":
                logger.info(f"Updating {elm_update.element_id}:k_strength to {elm_update.value}")

                # For H property, always use magnet device type
                device_type = "magnet"
                device_name = self._get_device_name(elm_update.element_id, device_type)

                logger.debug(f"Using device: {device_name} (type: {device_type})")

                # Simplified: direct device update
                try:
                    device = DeviceProxy(device_name)
                    device.write_attribute("k_strength", elm_update.value)
                    logger.info(f"Successfully updated H strength from push values {elm_update.element_id}:k_strength")
                except Exception as e:
                    logger.error(f"Failed to update {elm_update.element_id}:k_strength: {e}")
                    raise

            else:
                # Handle other properties (x, y positions, etc.)
                # Map EPICS property names to Tango attribute names
                # EPICS uses 'x:set'/'y:set' but Tango devices have 'x_position'/'y_position' attributes
                property_name = 'x_position' if 'x' in elm_update.property_name else (
                    'y_position' if 'dy' in elm_update.property_name else elm_update.property_name)

                logger.info(f"Updating {elm_update.element_id}:{property_name} to {elm_update.value}")

                # Determine device type and generate device name dynamically
                device_type = self._determine_device_type(elm_update.element_id, elm_update.property_name)
                device_name = self._get_device_name(elm_update.element_id, device_type)

                logger.debug(f"Using device: {device_name} (type: {device_type})")

                # Simplified: direct device update
                try:
                    device = DeviceProxy(device_name)
                    device.write_attribute(property_name, elm_update.value)
                    logger.info(f"Successfully updated from push values {elm_update.element_id}:{property_name}")
                except Exception as e:
                    logger.error(f"Failed to update {elm_update.element_id}:{property_name}: {e}")
                    raise

        except Exception as e:
            logger.error(f"Failed to update {elm_update.element_id}:{elm_update.property_name}: {e}")
            raise

    async def push_orbit(self, orbit_result: Orbit):
        """Push orbit data to the device using create_or_update_pv function."""
        print(f"[DEBUG] ResultView.push_orbit called with: {type(orbit_result)}")

        try:
            logger.info('Orbit pushing view')

            # Validate and log orbit data before pushing
            if len(orbit_result.x) > 0:
                logger.info(f"Orbit X range: [{orbit_result.x.min():.6f}, {orbit_result.x.max():.6f}]")
            if len(orbit_result.y) > 0:
                logger.info(f"Orbit Y range: [{orbit_result.y.min():.6f}, {orbit_result.y.max():.6f}]")

            # Add detailed value logging for debugging
            print(f"🔍 ORBIT VALUES:")
            print(f"  X coordinates: min={orbit_result.x.min():.6f}, max={orbit_result.x.max():.6f}")
            print(f"  Y coordinates: min={orbit_result.y.min():.6f}, max={orbit_result.y.max():.6f}")
            if hasattr(orbit_result, 'x0') and len(orbit_result.x0) > 0:
                print(f"  X0 coordinates: min={orbit_result.x0.min():.6f}, max={orbit_result.x0.max():.6f}")

            # Show first few values
            if len(orbit_result.x) > 0:
                print(f"  First 5 X values: {orbit_result.x[:5]}")
                print(f"  First 5 Y values: {orbit_result.y[:5]}")

            # Show element names if available
            if hasattr(orbit_result, 'names') and len(orbit_result.names) > 0:
                print(f"  First 5 element names: {orbit_result.names[:5]}")
                print(f"  Last 5 element names: {orbit_result.names[-5:]}")

            # Check for NaN/INF values
            x_nan_count = np.isnan(orbit_result.x).sum() if hasattr(orbit_result.x, '__iter__') else 0
            y_nan_count = np.isnan(orbit_result.y).sum() if hasattr(orbit_result.y, '__iter__') else 0

            if x_nan_count > 0 or y_nan_count > 0:
                logger.warning(f"Found {x_nan_count} NaN in X, {y_nan_count} NaN in Y")

                # Clean the data by replacing NaN with 0.0
                if hasattr(orbit_result.x, '__iter__'):
                    orbit_result.x = np.nan_to_num(orbit_result.x, nan=0.0, posinf=0.0, neginf=0.0)
                if hasattr(orbit_result.y, '__iter__'):
                    orbit_result.y = np.nan_to_num(orbit_result.y, nan=0.0, posinf=0.0, neginf=0.0)
                if hasattr(orbit_result.x0, '__iter__'):
                    orbit_result.x0 = np.nan_to_num(orbit_result.x0, nan=0.0, posinf=0.0, neginf=0.0)

                logger.info("NaN values cleaned in orbit data")

            update_orbit_pv(self.twiss_orbit_device, orbit_result)

            logger.info('Orbit pushed view using create_or_update_pv')
        except Exception as exc:
            logger.warning('Orbit view pushing failed: %s', exc)
            raise exc

    async def push_twiss(self, twiss_result: TwissWithAggregatedKValues):
        """Push Twiss data to the device using create_or_update_pv function."""
        print(f"[DEBUG] ResultView.push_twiss called with: {type(twiss_result)}")

        if twiss_result is None:
            logger.warning("push_twiss called with None data")
            return

        try:
            # Validate and clean Twiss data before processing

            # Check for NaN/INF values in all Twiss parameters
            x_alpha_nan = np.isnan(twiss_result.x.alpha).sum() if hasattr(twiss_result.x.alpha, '__iter__') else 0
            x_beta_nan = np.isnan(twiss_result.x.beta).sum() if hasattr(twiss_result.x.beta, '__iter__') else 0
            x_nu_nan = np.isnan(twiss_result.x.nu).sum() if hasattr(twiss_result.x.nu, '__iter__') else 0

            y_alpha_nan = np.isnan(twiss_result.y.alpha).sum() if hasattr(twiss_result.y.alpha, '__iter__') else 0
            y_beta_nan = np.isnan(twiss_result.y.beta).sum() if hasattr(twiss_result.y.beta, '__iter__') else 0
            y_nu_nan = np.isnan(twiss_result.y.nu).sum() if hasattr(twiss_result.y.nu, '__iter__') else 0

            total_nan = x_alpha_nan + x_beta_nan + x_nu_nan + y_alpha_nan + y_beta_nan + y_nu_nan

            if total_nan > 0:
                logger.warning(f"Found {total_nan} NaN values in Twiss data")

                # Clean the data by replacing NaN with 0.0

                # Clean X-plane data
                if hasattr(twiss_result.x.alpha, '__iter__'):
                    twiss_result.x.alpha = np.nan_to_num(twiss_result.x.alpha, nan=0.0, posinf=0.0, neginf=0.0)
                if hasattr(twiss_result.x.beta, '__iter__'):
                    twiss_result.x.beta = np.nan_to_num(twiss_result.x.beta, nan=0.0, posinf=0.0, neginf=0.0)
                if hasattr(twiss_result.x.nu, '__iter__'):
                    twiss_result.x.nu = np.nan_to_num(twiss_result.x.nu, nan=0.0, posinf=0.0, neginf=0.0)

                # Clean Y-plane data
                if hasattr(twiss_result.y.alpha, '__iter__'):
                    twiss_result.y.alpha = np.nan_to_num(twiss_result.y.alpha, nan=0.0, posinf=0.0, neginf=0.0)
                if hasattr(twiss_result.y.beta, '__iter__'):
                    twiss_result.y.beta = np.nan_to_num(twiss_result.y.beta, nan=0.0, posinf=0.0, neginf=0.0)
                if hasattr(twiss_result.y.nu, '__iter__'):
                    twiss_result.y.nu = np.nan_to_num(twiss_result.y.nu, nan=0.0, posinf=0.0, neginf=0.0)

                logger.info("NaN values cleaned in Twiss data")

            # Log the information
            logger.info("📊 Pushing Twiss data with detailed information:")
            logger.info(f"X-Plane: {len(twiss_result.x.alpha)} elements, tune={twiss_result.x.tune}")
            logger.info(f"Y-Plane: {len(twiss_result.y.alpha)} elements, tune={twiss_result.y.tune}")
            logger.info(f"Total elements: {len(twiss_result.names)}")

            # Add detailed value logging for debugging
            print(f"🔍 TWISS VALUES - X-Plane:")
            print(f"  Alpha X: min={twiss_result.x.alpha.min():.6f}, max={twiss_result.x.alpha.max():.6f}")
            print(f"  Beta X: min={twiss_result.x.beta.min():.6f}, max={twiss_result.x.beta.max():.6f}")
            print(f"  Nu X: min={twiss_result.x.nu.min():.6f}, max={twiss_result.x.nu.max():.6f}")
            print(f"  Tune X: {twiss_result.x.tune:.6f}")

            print(f"🔍 TWISS VALUES - Y-Plane:")
            print(f"  Alpha Y: min={twiss_result.y.alpha.min():.6f}, max={twiss_result.y.alpha.max():.6f}")
            print(f"  Beta Y: min={twiss_result.y.beta.min():.6f}, max={twiss_result.y.beta.max():.6f}")
            print(f"  Nu Y: min={twiss_result.y.nu.min():.6f}, max={twiss_result.y.nu.max():.6f}")
            print(f"  Tune Y: {twiss_result.y.tune:.6f}")

            # Show first few element names
            if len(twiss_result.names) > 0:
                print(f"🔍 First 5 element names: {twiss_result.names[:5]}")
                print(f"🔍 Last 5 element names: {twiss_result.names[-5:]}")

            self.default_twiss = twiss_result

            # Push the data to the device
            update_twiss_pv(self.twiss_orbit_device, twiss_result)

            logger.info('Twiss pushed view using create_or_update_pv')
        except Exception as exc:
            logger.error(f"Twiss view pushing failed: {exc}")
            raise exc

    async def push_bpms(self, orbit_data):
        """
        BESSY specific way of setting BPM and pushing it.
        Matches EPICS implementation behavior.
        """
        print(f"[DEBUG] ResultView.push_bpms called with: {type(orbit_data)}")

        if not self.bpm_mimicry:
            raise ValueError("BPM Mimicry not set in ResultView")
        try:
            logger.info(f"pushing legacy bpm data")

            df_bpm = self.bpm_mimicry.extract_bpm_legacy_data_to_df(orbit_data)
            logger.info(f"BPM DataFrame created: {df_bpm.shape}")

            # Check for NaN values in the BPM data
            x_nan_count = df_bpm['x'].isna().sum()
            y_nan_count = df_bpm['y'].isna().sum()

            if x_nan_count > 0 or y_nan_count > 0:
                logger.warning(f"BPM data contains {x_nan_count} NaN in X, {y_nan_count} NaN in Y")

                # Fill NaN values with 0.0 before processing
                df_bpm['x'] = df_bpm['x'].fillna(0.0)
                df_bpm['y'] = df_bpm['y'].fillna(0.0)
                logger.info("NaN values replaced with 0.0")

            bpm_legacy_data = self.bpm_mimicry.bpm_legacy_data_df_to_array(df_bpm)
            logger.info(f"BPM legacy data array: {bpm_legacy_data.shape}, dtype: {bpm_legacy_data.dtype}")

            self.default_bpm_legacy_data = bpm_legacy_data
            await self.push_legacy_bpm_data(bpm_legacy_data)

            orbit_object_data = df_bpm.copy()
            mm2nm = 1e6
            orbit_object_data.x = df_bpm.x * mm2nm
            orbit_object_data.y = df_bpm.y * mm2nm

            logger.info(f"Orbit object data prepared: {len(orbit_object_data)} BPMs")

            self.orbit_object_data = orbit_object_data
            await self.push_orbit_object(self.orbit_object_data)

            logger.info("BPM data processing completed successfully")

        except Exception as e:
            logger.error(f"Error processing orbit data: {e}")
            raise

    async def push_legacy_bpm_data(self, bpm_legacy_data: Sequence[np.int16] = None):
        """
        Push BPM data to Tango using create_or_update_pv function.
        If no data is provided, push the default data.
        Matches EPICS implementation behavior.
        """
        if bpm_legacy_data is None:
            logger.info(f"Pushing legacy BPM data at {datetime.now()}")
            bpm_legacy_data = self.default_bpm_legacy_data

        try:
            # Ensure data is in the correct format
            if not isinstance(bpm_legacy_data, np.ndarray):
                bpm_legacy_data = np.asarray(bpm_legacy_data, dtype=np.int16)
            elif bpm_legacy_data.dtype != np.int16:
                bpm_legacy_data = bpm_legacy_data.astype(np.int16)

            # Ensure data has the correct shape (2048 elements)
            if bpm_legacy_data.shape != (2048,):
                logger.warning(f"Reshaping BPM data from {bpm_legacy_data.shape} to (2048,)")
                if len(bpm_legacy_data) > 2048:
                    bpm_legacy_data = bpm_legacy_data[:2048]
                else:
                    padded_data = np.zeros(2048, dtype=np.int16)
                    padded_data[:len(bpm_legacy_data)] = bpm_legacy_data
                    bpm_legacy_data = padded_data

            logger.debug(f"Pushing BPM data: shape={bpm_legacy_data.shape}, dtype={bpm_legacy_data.dtype}")

            update_bpm_pv(self.bpm_device, bpm_legacy_data)

            # If orbit object data exists, push it as well
            if hasattr(self, 'orbit_object_data') and self.orbit_object_data is not None:
                logger.info(f"Pushing orbit object data at {datetime.now()}")
                await self.push_orbit_object(self.orbit_object_data)

            logger.info(f"Successfully pushed BPM data: {len(bpm_legacy_data)} elements")

        except Exception as e:
            logger.error(f"Failed to push BPM data: {e}")
            logger.warning("Continuing heartbeat despite BPM data error")

    async def push_orbit_object(self, bpm_data: pd.DataFrame):
        """
        Push orbit object data to Tango device.
        Matches EPICS implementation for ORBITCC data.
        """
        try:
            device = DeviceProxy(self.twiss_orbit_device)

            # Clean the data before pushing to Tango
            logger.info("🧹 Cleaning orbit data before pushing to Tango...")

            # Extract and clean x, y positions - handle NaN values more aggressively
            x_positions = bpm_data.loc[:, "x"].fillna(0.0)  # Replace NaN with 0.0
            y_positions = bpm_data.loc[:, "y"].fillna(0.0)  # Replace NaN with 0.0

            # Convert to numpy arrays and ensure they're clean
            x_positions = clean_data_for_tango(x_positions, "orbit_x")
            y_positions = clean_data_for_tango(y_positions, "orbit_y")

            # Combine x and y positions
            pos = np.concatenate([x_positions, y_positions])

            # Clean BPM names (remove any None or empty values)
            bpm_names = []
            for val in bpm_data.index:
                if pd.isna(val) or val == '':
                    bpm_names.append(f"BPM_{len(bpm_names)}")
                else:
                    bpm_names.append(str(val))

            # Log the cleaned data
            logger.debug(f"📊 Cleaned orbit data:")
            logger.debug(
                f"   X positions: {len(x_positions)} elements, range: [{x_positions.min():.6f}, {x_positions.max():.6f}]")
            logger.debug(
                f"   Y positions: {len(y_positions)} elements, range: [{y_positions.min():.6f}, {y_positions.max():.6f}]")
            logger.debug(f"   Combined positions: {len(pos)} elements")
            logger.debug(f"   BPM names: {len(bpm_names)} elements")
            logger.debug(f"   Sample names: {bpm_names[:5]}")

            # Only write writable attributes - remove ORBITCC/count as it's not writable
            device.write_attribute("ORBITCC/rdPos", pos.tolist())
            device.write_attribute("ORBITCC/rdBpmNames", bpm_names)
            # Note: ORBITCC/count is not writable, so we skip it

            logger.info(f"Orbit object data pushed successfully")

        except Exception as e:
            logger.error(f"Error processing orbit object data: {e}")
            raise

    async def heart_beat(self):
        """
        Periodic heartbeat function to push default BPM data.
        Matches EPICS implementation behavior.
        """
        logger.info("💓 ResultView.heart_beat() called")

        try:
            logger.debug("💓 Pushing legacy BPM data...")

            await self.push_legacy_bpm_data(self.default_bpm_legacy_data)

            logger.debug("💓 Legacy BPM data pushed successfully")

            if self.default_twiss is not None:
                logger.debug("💓 Pushing Twiss data...")

                try:
                    await self.push_twiss(self.default_twiss)
                    logger.debug("💓 Twiss data pushed successfully")
                except Exception as twiss_error:
                    logger.warning(f"Twiss data push failed: {twiss_error}")
                    # Don't let Twiss errors crash the heartbeat
            else:
                logger.debug("💓 No Twiss data to push")

            logger.info("💓 Heartbeat completed successfully")

        except Exception as e:
            logger.error(f"Heartbeat check failed: {e}")
            logger.warning("Continuing heartbeat despite errors")