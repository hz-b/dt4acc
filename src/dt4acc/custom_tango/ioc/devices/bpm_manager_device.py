# bpm_manager_device.py

import asyncio
import threading
import numpy as np
from tango.server import Device, attribute, device_property, AttrDataFormat
from tango import DevState

from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_epics.ioc.handlers import update_manager
from bact_twin_architecture.data_model.identifiers import LatticeElementPropertyID

logger = get_logger()


class BPMManagerDevice(Device):
    """
    Virtual aggregate BPM device for SOLEIL.

    Tango name: SOLEIL/BPM/MANAGER

    Exposes:
        - bpm_names[]: list of BPM names
        - orbit_x[]: horizontal BPM readings
        - orbit_y[]: vertical BPM readings
    """

    name = device_property(
        dtype=str, default_value="SOLEIL/BPM/MANAGER",
        doc="Tango name of the BPM manager"
    )

    def init_device(self):
        super().init_device()
        logger.info(f"Initializing BPM Manager: {self.name}")

        # async loop for dt4acc calls
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        self.bpm_names = []
        self.orbit_x = np.zeros(1)
        self.orbit_y = np.zeros(1)

        self._update_all()
        self.set_state(DevState.ON)

    # ------------------ Async support ------------------
    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _run_async(self, coro):
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result()

    # ------------------ Data Updates -------------------
    def _update_all(self):
        try:
            # Get BPM names
            self.bpm_names = update_manager.peek_engine(
                LatticeElementPropertyID("BPM", "names")
            )

            # Get BPM horizontal orbit
            self.orbit_x = np.asarray(
                update_manager.peek_engine(
                    LatticeElementPropertyID("BPM", "x")
                )
            )

            # Get BPM vertical orbit
            self.orbit_y = np.asarray(
                update_manager.peek_engine(
                    LatticeElementPropertyID("BPM", "y")
                )
            )

        except Exception as exc:
            logger.error(f"BPMManagerDevice update failed: {exc}")

    # ------------------ Tango Attributes ------------------

    @attribute(dtype=str, max_dim_x=4096, format=AttrDataFormat.SPECTRUM)
    def bpm_names_attr(self):
        """List of BPM names."""
        return self.bpm_names

    @attribute(dtype=float, max_dim_x=4096, format=AttrDataFormat.SPECTRUM)
    def orbit_x_attr(self):
        return self.orbit_x

    @attribute(dtype=float, max_dim_x=4096, format=AttrDataFormat.SPECTRUM)
    def orbit_y_attr(self):
        return self.orbit_y
