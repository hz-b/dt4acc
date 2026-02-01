import asyncio
import numpy as np

from tango import DeviceProxy

from ...core.interfaces.view_interface import ViewInterface
from ...core.model.orbit import Orbit
from ...core.model.twiss import TwissWithAggregatedKValues, TuneData
from ...core.utils.logger import get_logger
from ...core.utils.periodic_publisher import PeriodicPublisher

logger = get_logger()

# ---------------------------------------------------------------------
# Hard safety gate: only allow pushes to virtual devices from virtual_devices.py
# ---------------------------------------------------------------------
_ALLOWED_VIRTUAL_DEVICES = {
    "PHYSICS/SOLEIL/TWISS_ORBIT",
    "PHYSICS/SOLEIL/TUNE",
}


def _virtual_device_name(prefix: str | None, suffix: str) -> str:
    """
    Build a Tango device name for our virtual devices only.
    - If prefix contains "/", it is assumed to be a server prefix and we build "<prefix>/<suffix>"
    - Otherwise we fall back to fixed "PHYSICS/SOLEIL/<suffix>"
    """
    if prefix and "/" in prefix:
        dev = f"{prefix}/{suffix}"
    else:
        dev = f"PHYSICS/SOLEIL/{suffix}"

    if dev not in _ALLOWED_VIRTUAL_DEVICES:
        raise RuntimeError(f"Refusing to push to non-virtual device: {dev}")

    return dev


def _to_py_float_list(x) -> list[float]:
    """
    Convert array-like to a 1D list of *Python* floats (most compatible with PyTango).
    Also sanitizes NaN/inf -> 0.0.
    """
    arr = np.asarray(x, dtype=np.float64).ravel()
    arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
    return [float(v) for v in arr]


def _to_py_float(x) -> float:
    """
    Convert scalar-like to a Python float.
    """
    return float(np.asarray(x).item())


# ---------------------------------------------------------------------
# Views that ONLY push to virtual_devices.py devices
# ---------------------------------------------------------------------
class OrbitView(ViewInterface):
    """
    Pushes orbit arrays (x,y) to TwissOrbitDevice using commands:
      - push_orbit_x (DevDouble spectrum)
      - push_orbit_y (DevDouble spectrum)
    """

    def __init__(self, prefix: str | None):
        self.prefix = prefix

    async def push(self, data):
        # data is expected to be a dataframe-like with columns 'x' and 'y'
        if data is None or len(getattr(data, "index", [])) == 0:
            return

        x_payload = _to_py_float_list(data.loc[:, "x"].values)
        y_payload = _to_py_float_list(data.loc[:, "y"].values)

        dev_name = _virtual_device_name(self.prefix, "TWISS_ORBIT")
        dev = DeviceProxy(dev_name)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: dev.command_inout("push_orbit_x", x_payload))
        await loop.run_in_executor(None, lambda: dev.command_inout("push_orbit_y", y_payload))


class TwissView(ViewInterface):
    """
    Pushes twiss arrays (alpha,beta,nu for x/y) to TwissOrbitDevice using commands:
      - push_alpha_x, push_beta_x, push_nu_x
      - push_alpha_y, push_beta_y, push_nu_y
    """

    def __init__(self, prefix: str | None):
        self.prefix = prefix

    async def push(self, twiss_result: TwissWithAggregatedKValues):
        if twiss_result is None:
            return

        alpha_x = _to_py_float_list(twiss_result.x.alpha)
        beta_x = _to_py_float_list(twiss_result.x.beta)
        nu_x = _to_py_float_list(twiss_result.x.nu)

        alpha_y = _to_py_float_list(twiss_result.y.alpha)
        beta_y = _to_py_float_list(twiss_result.y.beta)
        nu_y = _to_py_float_list(twiss_result.y.nu)

        dev_name = _virtual_device_name(self.prefix, "TWISS_ORBIT")
        dev = DeviceProxy(dev_name)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: dev.command_inout("push_alpha_x", alpha_x))
        await loop.run_in_executor(None, lambda: dev.command_inout("push_beta_x", beta_x))
        await loop.run_in_executor(None, lambda: dev.command_inout("push_nu_x", nu_x))
        await loop.run_in_executor(None, lambda: dev.command_inout("push_alpha_y", alpha_y))
        await loop.run_in_executor(None, lambda: dev.command_inout("push_beta_y", beta_y))
        await loop.run_in_executor(None, lambda: dev.command_inout("push_nu_y", nu_y))


class TuneView(ViewInterface):
    """
    Pushes tune scalars to TuneDevice using attributes:
      - hor (READ_WRITE)
      - vert (READ_WRITE)
    """

    def __init__(self, prefix: str | None):
        self.prefix = prefix

    async def push(self, data: TuneData):
        if data is None:
            return

        tune_x = _to_py_float(data.x)
        tune_y = _to_py_float(data.y)

        tune_x += float(np.random.uniform(-1e-12, 1e-12))
        tune_y += float(np.random.uniform(-1e-12, 1e-12))
        dev_name = _virtual_device_name(self.prefix, "TUNE")
        dev = DeviceProxy(dev_name)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: dev.write_attribute("hor", tune_x))
        await loop.run_in_executor(None, lambda: dev.write_attribute("vert", tune_y))


# ---------------------------------------------------------------------
# RepeatedResultView: no fake data, only republish if real data exists
# ---------------------------------------------------------------------
class RepeatedResultView:
    """
    This class is responsible for publishing REAL results to the virtual Tango devices.
    It does not generate or push fake/sentinel data.
    """

    def __init__(self, *, prefix: str | None):
        self.prefix = prefix

        self.orbit_publisher = PeriodicPublisher(view=OrbitView(prefix=prefix), name="orbit")
        self.twiss_publisher = PeriodicPublisher(view=TwissView(prefix=prefix), name="twiss")
        self.tune_publisher = PeriodicPublisher(view=TuneView(prefix=prefix), name="tune")

        self._have_orbit = False
        self._have_twiss = False
        self._have_tune = False

    async def heart_beat(self):
        """
        Republishes the latest REAL values only (if they exist).
        No fake values are created here.
        """
        if self._have_orbit:
            await self.orbit_publisher.publish()
        if self._have_twiss:
            await self.twiss_publisher.publish()
        if self._have_tune:
            await self.tune_publisher.publish()

    async def push_twiss(self, twiss_result: TwissWithAggregatedKValues):
        """
        Publishes twiss arrays to TWISS_ORBIT, and also publishes tune scalars to TUNE.
        """
        if twiss_result is None:
            return

        # 1) push twiss arrays
        self.twiss_publisher.set_data(twiss_result)
        self._have_twiss = True
        await self.twiss_publisher.publish()

        # 2) push tune scalars (derived)
        try:
            tune_x = float(twiss_result.x.tune)
            tune_y = float(twiss_result.y.tune)
            tune_data = TuneData(x=tune_x, y=tune_y)
            self.tune_publisher.set_data(tune_data)
            self._have_tune = True
            await self.tune_publisher.publish()
        except Exception as e:
            logger.warning(f"Could not publish tune from twiss_result: {e}")

    async def push_orbit(self, orbit_result: Orbit):
        """
        If orbit_result is processed elsewhere into a dataframe-like object,
        pass that object into this method.
        """
        if orbit_result is None:
            return

        self.orbit_publisher.set_data(orbit_result)
        self._have_orbit = True
        await self.orbit_publisher.publish()
