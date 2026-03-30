import itertools
from typing import Sequence
from datetime import datetime

import numpy as np
from tango import DeviceProxy

from ...core.utils.logger import get_logger
from ...custom_epics.data.constants import special_dev
from ..config import SERVER_NAME, SERVER_INSTANCE, DEVICE_NAME_FORMAT

logger = get_logger()

class BeamPositionPVs:
    def __init__(self, *, prefix):
        self.prefix = prefix
        self.device = None
        self._initialized = False
        self.bdata_cache = None
        self.counter = itertools.count()
        self.device_name = "SimpleTangoServer/test/twiss_orbit_twiss_device"

    def set_data_sync(self, data):
        """Set BPM data synchronously."""
        try:
            if not self.device:
                self.device = DeviceProxy(self.device_name)

            data_array = np.asarray(data, dtype=np.float32)
            data_array = np.nan_to_num(data_array, nan=0.0, posinf=0.0, neginf=0.0)
            data_array = data_array.astype(np.int16)
            
            # Pad or truncate to required length (2048 elements)
            if len(data_array) < 2048:
                # Pad with zeros to reach target length
                padded = np.zeros(2048, dtype=np.int16)
                padded[:len(data_array)] = data_array
                data_array = padded
            elif len(data_array) > 2048:
                # Truncate to target length
                data_array = data_array[:2048]
            
            self.device.write_attribute("beam/bpm/data", data_array.tolist())
            self._initialized = True
            logger.info("BPM data set successfully")
        except Exception as e:
            logger.error(f"Failed to set BPM data: {e}")
            raise

    def heart_beat_sync(self):
        """Send heartbeat synchronously."""
        try:
            if not self.device:
                self.device = DeviceProxy(f"{self.prefix}/TwissOrbitDevice_MAIN")
            self.device.ping()
            logger.debug("BPM heartbeat sent successfully")
        except Exception as e:
            logger.error(f"Failed to send BPM heartbeat: {e}")
            raise

    def _get_device(self):
        """Get or create device proxy"""
        if self.device is None:
            try:
                self.device = DeviceProxy(self.device_name)
                logger.info(f"Created device proxy for {self.device_name}")
            except Exception as e:
                logger.error(f"Failed to create device proxy: {e}")
                raise
        return self.device

    async def update_values(self):
        if self.bdata_cache is None:
            logger.warning("No bpm data (yet)")
            return

        try:
            device = self._get_device()

            data_array = np.asarray(self.bdata_cache, dtype=np.float32)
            data_array = np.nan_to_num(data_array, nan=0.0, posinf=0.0, neginf=0.0)
            data_array = data_array.astype(np.int16)
            device.write_attribute("beam/bpm/data", data_array.tolist())
            next(self.counter)
            logger.debug(f"Updated BPM values at {datetime.now()}")
        except Exception as e:
            logger.error(f"Failed to update BPM values: {e}")
            raise

    async def heart_beat(self):
        """Periodic heartbeat function to update BPM data"""
        try:
            await self.update_values()
            logger.debug(f"BPM heartbeat at {datetime.now()}")
        except Exception as e:
            logger.error(f"BPM heartbeat failed: {e}")
            raise

    async def set_data(self, bdata: Sequence[np.int16]):
        """Set BPM data and update the device"""
        try:

            data_array = np.asarray(bdata, dtype=np.float32)
            data_array = np.nan_to_num(data_array, nan=0.0, posinf=0.0, neginf=0.0)
            self.bdata_cache = data_array.astype(np.int16)
            await self.update_values()
            logger.info(f"Set new BPM data at {datetime.now()}")
        except Exception as e:
            logger.error(f"Failed to set BPM data: {e}")
            raise 