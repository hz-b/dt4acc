import asyncio

import numpy as np
from tango import DeviceProxy

from ...core.model.element_upate import ElementUpdate
from ...core.model.orbit import Orbit
from ...core.model.twiss import TwissWithAggregatedKValues
from ...core.utils.logger import get_logger

logger = get_logger()


def to_float_list(x) -> list[float]:
    """
    Convert anything array-like to a 1D Python list of Python floats.
    Also sanitizes NaN/inf to 0.0.
    """
    arr = np.asarray(x, dtype=np.float64).ravel()
    arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
    # Ensure Python core floats (not numpy.float64) for maximum PyTango compatibility
    return [float(v) for v in arr]


async def update_orbit_pv(pv_name, orbit_result):
    device = DeviceProxy(pv_name)

    x_payload = to_float_list(orbit_result.x)
    y_payload = to_float_list(orbit_result.y)

    logger.info(f"orbit_x payload len={len(x_payload)} first3={x_payload[:3]}")
    logger.info(f"orbit_y payload len={len(y_payload)} first3={y_payload[:3]}")

    loop = asyncio.get_running_loop()

    try:
        await loop.run_in_executor(None, lambda: device.command_inout("push_orbit_x", x_payload))
        logger.info("push_orbit_x SUCCESS")
    except Exception as e:
        logger.error(f"push_orbit_x FAILED: {e}")
        raise

    try:
        await loop.run_in_executor(None, lambda: device.command_inout("push_orbit_y", y_payload))
        logger.info("push_orbit_y SUCCESS")
    except Exception as e:
        logger.error(f"push_orbit_y FAILED: {e}")
        raise


async def update_twiss_pv(pv_name, twiss_result):
    device = DeviceProxy(pv_name)

    alpha_x_payload = to_float_list(twiss_result.x.alpha)
    beta_x_payload = to_float_list(twiss_result.x.beta)
    nu_x_payload = to_float_list(twiss_result.x.nu)

    alpha_y_payload = to_float_list(twiss_result.y.alpha)
    beta_y_payload = to_float_list(twiss_result.y.beta)
    nu_y_payload = to_float_list(twiss_result.y.nu)

    logger.info(f"alpha_x_payload payload len={len(alpha_x_payload)} first3={alpha_x_payload[:3]}")
    logger.info(f"beta_x payload len={len(beta_x_payload)} first3={beta_x_payload[:3]}")
    logger.info(f"nu_x_payload payload len={len(nu_x_payload)} first3={nu_x_payload[:3]}")
    logger.info(f"alpha_y_payload payload len={len(alpha_y_payload)} first3={alpha_y_payload[:3]}")
    logger.info(f"beta_y_payload payload len={len(beta_y_payload)} first3={beta_y_payload[:3]}")
    logger.info(f"nu_y_payload payload len={len(nu_y_payload)} first3={nu_y_payload[:3]}")
    loop = asyncio.get_running_loop()

    await loop.run_in_executor(None, lambda: device.command_inout("push_alpha_x", alpha_x_payload))
    await loop.run_in_executor(None, lambda: device.command_inout("push_beta_x", beta_x_payload))
    await loop.run_in_executor(None, lambda: device.command_inout("push_nu_x", nu_x_payload))
    await loop.run_in_executor(None, lambda: device.command_inout("push_alpha_y", alpha_y_payload))
    await loop.run_in_executor(None, lambda: device.command_inout("push_beta_y", beta_y_payload))
    await loop.run_in_executor(None, lambda: device.command_inout("push_nu_y", nu_y_payload))


class CalculationResultView:
    def __init__(self, *, prefix):
        self.prefix = prefix

    async def push_value(self, elm_update: ElementUpdate):
        pass

    async def push_orbit(self, orbit_result: Orbit):
        # If prefix is PHYSICS/SOLEIL, use it directly, otherwise use the registered name
        if self.prefix and "/" in self.prefix:
            # Prefix is like "PHYSICS/SOLEIL", construct device name
            device_name = f"{self.prefix}/TWISS_ORBIT"
        else:
            # Use the standard registered device name
            device_name = "PHYSICS/SOLEIL/TWISS_ORBIT"

        try:
            await update_orbit_pv(device_name, orbit_result)
        except Exception as exc:
            logger.warning('Orbit view pushing failed: %s', exc)
            raise exc
        else:
            logger.info('Orbit pushed view')

    async def push_twiss(self, twiss_result: TwissWithAggregatedKValues):
        if self.prefix and "/" in self.prefix:
            device_name = f"{self.prefix}/TWISS_ORBIT"
        else:
            device_name = "PHYSICS/SOLEIL/TWISS_ORBIT"

        if twiss_result is None:
            return

        await update_twiss_pv(device_name, twiss_result)
