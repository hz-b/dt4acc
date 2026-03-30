#!/usr/bin/env python3
import os
import sys
import asyncio
from tango.server import run

from dt4acc.custom_tango.ioc.devices.tango_device_setup import get_all_device_classes
from dt4acc.core.utils.logger import get_logger

logger = get_logger()

global_event_loop = None


def _inject_shared_update_manager():
    """
    Pre-populate handlers._update_manager_instance with an async-compatible
    adapter over the shared service proxy — before any device's init_device()
    runs. handlers.py is not modified.
    """
    from dt4acc.custom_tango.ioc.devices.server_manager import _connect_to_update_manager_service
    import dt4acc.core.bl.handlers as handlers

    raw_proxy = _connect_to_update_manager_service()

    class AsyncAdapterProxy:
        """
        Makes the synchronous multiprocessing proxy look like the real
        UpdateManager to handlers.py. The async update() interface is
        restored here so magnet_device._async() and handle_device_update()
        work exactly as before — unaware of the process boundary.
        """
        def peek_engine(self, lat_elem_prop):
            return raw_proxy.peek_engine(lat_elem_prop)

        def device_value_from_peeking_engine(self, dev_prop):
            return raw_proxy.device_value_from_peeking_engine(dev_prop)

        async def update(self, *, device_id, property_name, value=None, element=None):
            # sync_update() runs the coroutine in the service process
            # and returns a plain result — safe to cross the process boundary.
            return raw_proxy.sync_update(device_id, property_name, value)

    handlers._update_manager_instance = AsyncAdapterProxy()
    logger.info("Injected shared UpdateManager proxy into handlers.")


def main_loop(server_name: str, instance_name: str, event=None):
    os.nice(4)

    # Inject BEFORE Tango initialises any device
    _inject_shared_update_manager()

    if event is None:
        def cb():
            logger.warning(f"Server {sys.argv} instantiated")
    else:
        def cb():
            logger.warning(f"Server {server_name}, {instance_name} instantiated... setting event")
            event.set()
            logger.warning(f"Server {server_name}, {instance_name} event is set")

    global global_event_loop
    try:
        global_event_loop = asyncio.get_event_loop()
        if global_event_loop.is_closed():
            global_event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(global_event_loop)
    except RuntimeError:
        global_event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(global_event_loop)

    try:
        device_classes = get_all_device_classes()
        logger.warning(
            "Starting server %s instance %s for %d device classes",
            server_name, instance_name, len(device_classes)
        )
        run(
            device_classes,
            args=[server_name, instance_name],
            post_init_callback=cb,
            raises=True,
            verbose=True,
        )
        sys.stderr.write(f"Tango server {server_name}/{instance_name} finished\n")
        sys.stderr.flush()
        logger.warning(f"Tango server {server_name}/{instance_name} finished")
    except Exception as e:
        sys.stderr.write(f"Tango server {server_name}/{instance_name} failed: {e}\n")
        sys.stderr.flush()
        logger.error(f"Tango server {server_name}/{instance_name} failed: {e}")
        raise
    finally:
        if global_event_loop and not global_event_loop.is_closed():
            try:
                global_event_loop.close()
            except Exception:
                pass


def main():
    if len(sys.argv) != 3:
        print("Usage: single_server.py <server_name> <instance_name>")
        sys.exit(1)
    main_loop(server_name=sys.argv[1], instance_name=sys.argv[2])


if __name__ == "__main__":
    main()