# twiss_orbit_device_new.py

import asyncio
import threading
import numpy as np
from tango.server import Device, attribute, device_property, AttrDataFormat
from tango import DevState
from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_epics.ioc.handlers import update_manager
from bact_twin_architecture.data_model.identifiers import LatticeElementPropertyID

logger = get_logger()


class TwissOrbitDevice(Device):
    """
    Virtual Tango device providing:
      - orbit x[], y[]
      - twiss alpha/beta at BPMs
    Device name: SOLEIL/PHYSICS/TWISS_ORBIT
    """

    name = device_property(dtype=str, default_value="SOLEIL/PHYSICS/TWISS_ORBIT")

    def init_device(self):
        super().init_device()
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        self.orbit_x = np.zeros(1)
        self.orbit_y = np.zeros(1)
        self.twiss_alpha_x = np.zeros(1)
        self.twiss_beta_x = np.zeros(1)
        self.twiss_alpha_y = np.zeros(1)
        self.twiss_beta_y = np.zeros(1)

        self.set_state(DevState.ON)
        self._update_all()

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _run_async(self, coro):
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result()

    def _update_all(self):
        """Fetch orbit and Twiss values from dt4acc."""
        try:
            # Orbit
            self.orbit_x = np.array(update_manager.peek_engine(
                LatticeElementPropertyID("ORBIT", "x")
            ))
            self.orbit_y = np.array(update_manager.peek_engine(
                LatticeElementPropertyID("ORBIT", "y")
            ))

            # Twiss
            self.twiss_alpha_x = np.array(update_manager.peek_engine(
                LatticeElementPropertyID("TWISS", "alpha_x")
            ))
            self.twiss_beta_x = np.array(update_manager.peek_engine(
                LatticeElementPropertyID("TWISS", "beta_x")
            ))
            self.twiss_alpha_y = np.array(update_manager.peek_engine(
                LatticeElementPropertyID("TWISS", "alpha_y")
            ))
            self.twiss_beta_y = np.array(update_manager.peek_engine(
                LatticeElementPropertyID("TWISS", "beta_y")
            ))

        except Exception as exc:
            logger.error(f"TwissOrbitDevice update failed: {exc}")

    @attribute(dtype=float, max_dim_x=4096, format=AttrDataFormat.SPECTRUM)
    def orbit_x_attr(self):
        return self.orbit_x

    @attribute(dtype=float, max_dim_x=4096, format=AttrDataFormat.SPECTRUM)
    def orbit_y_attr(self):
        return self.orbit_y

    @attribute(dtype=float, max_dim_x=4096, format=AttrDataFormat.SPECTRUM)
    def twiss_alpha_x_attr(self):
        return self.twiss_alpha_x

    @attribute(dtype=float, max_dim_x=4096, format=AttrDataFormat.SPECTRUM)
    def twiss_beta_x_attr(self):
        return self.twiss_beta_x

    @attribute(dtype=float, max_dim_x=4096, format=AttrDataFormat.SPECTRUM)
    def twiss_alpha_y_attr(self):
        return self.twiss_alpha_y

    @attribute(dtype=float, max_dim_x=4096, format=AttrDataFormat.SPECTRUM)
    def twiss_beta_y_attr(self):
        return self.twiss_beta_y
