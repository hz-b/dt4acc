"""Helpers for synchronising Tango write-side setpoints."""

from tango.server import Device

from dt4acc.core.utils.logger import get_logger

logger = get_logger()


def sync_write_value(device: Device, attr_name: str, value) -> None:
    """Mirror an internally refreshed value into Tango's write cache."""
    try:
        device.get_device_attr().get_w_attr_by_name(attr_name).set_write_value(value)
    except Exception as exc:
        logger.debug(
            "%s: could not sync write value for %s: %s",
            device.get_name(),
            attr_name,
            exc,
        )
