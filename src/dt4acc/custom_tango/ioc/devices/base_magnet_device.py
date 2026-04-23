"""
base_magnet_device.py
=====================
Shared base class for all accelerator magnet Tango devices.
Contains only lifecycle logic — no attributes or commands.
Each subclass exposes only the attributes relevant to its physical type.
"""

import asyncio

from dt4acc_lib.model.utils import tango_resource_locator
from tango import DevState, DevFailed
from tango.server import Device, device_property

from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_tango.ioc.controller_registry import get_controller
from dt4acc.custom_tango.ioc.devices.shared_event_loop import get_shared_event_loop

logger = get_logger()


def split_name(name: str):
    """Split Tango device name 'AN10-AR/EM/SCF.11'."""
    parts = name.split("/")
    if len(parts) != 3:
        raise DevFailed(f"Invalid magnet name '{name}'")
    return parts[0], parts[1], parts[2]


class BaseMagnetDevice(Device):
    """
    Shared base for all magnet device types.

    Subclasses add only the attributes that make physical sense:
        QuadSextOctDevice  → magnetic_strength + readback
        HorizontalSteererDevice → x_kick
        VerticalSteererDevice   → y_kick
        SkewQuadDevice     → skew_quad_strength
        CavityDevice       → frequency
    """

    element_uuid = device_property(dtype=str, default_value="")

    def init_device(self):
        super().init_device()
        self.set_state(DevState.INIT)

        full_name = self.get_name()
        self.trl = tango_resource_locator.TangoResourceLocator.from_trl(full_name)

        # UUID is the unique key into the pyAT lattice.
        # Falls back to member name if not set (shouldn't happen after registration).
        self.lattice_id = self.element_uuid if self.element_uuid else self.trl.member

        logger.info("Initializing %s: %s lattice_id=%s",
                    self.__class__.__name__, self.trl.as_trl(), self.lattice_id)

        self._loop = get_shared_event_loop()
        self.set_state(DevState.ON)

    def _async(self, coro):
        """Submit coroutine to shared loop, block until done, raise DevFailed on error."""
        try:
            fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
            return fut.result(timeout=10)
        except Exception as exc:
            raise DevFailed(str(exc))

    def _send(self, property_name: str, value: float) -> None:
        """Send a set command to the backend via TangoController."""
        from dt4acc_lib.model.utils.command import Command, BehaviourOnError
        self._async(
            get_controller().update(
                cmd=Command(
                    id=self.lattice_id,
                    property=property_name,
                    value=value,
                    behaviour_on_error=BehaviourOnError.stop,
                ),
                reads=[],
                delayed_reads=[],
            )
        )
