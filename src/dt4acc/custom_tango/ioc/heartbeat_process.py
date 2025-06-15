import asyncio
import time
import signal
import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from tango import DeviceProxy, DevFailed
from dt4acc.custom_tango.views.calculation_result_view import ResultView
from dt4acc.core.utils.logger import get_logger
from dt4acc.custom_tango.config import SERVER_NAME, SERVER_INSTANCE, DEVICE_NAME_FORMAT
from dt4acc.custom_epics.data.constants import special_pvs

logger = get_logger()

# Global state
view = ResultView(prefix=f"{SERVER_NAME}/{SERVER_INSTANCE}")
stop_event = asyncio.Event()


def try_device_proxy(device_name, timeout=5):
    """Try creating a DeviceProxy with a timeout to avoid hangs."""
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(DeviceProxy, device_name)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeoutError:
            logger.error(f"[Timeout] Could not connect to device: {device_name}")
            return None
        except DevFailed as e:
            logger.error(f"[DevFailed] Failed to connect to {device_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"[Error] Connecting to {device_name}: {e}")
            return None


def cleanup():
    """Cleanup function to properly close Tango devices."""
    try:
        view.bpm_pvs.device = None
    except Exception:
        pass
    print("Cleanup completed and heartbeat stopped")


def signal_handler(signum, frame):
    print(f"Received signal {signum}, initiating cleanup...")
    cleanup()
    try:
        stop_event.set()
    except Exception:
        pass
    sys.exit(0)



signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


async def initialize_view():
    """Safely initialize the BPM device."""
    try:

        device_name = f"{SERVER_NAME}/{SERVER_INSTANCE}/{DEVICE_NAME_FORMAT.format(device_type='BPMDevice', name=special_pvs['bpm_pv'])}"
        print(f"Attempting to connect to device: {device_name}")
        device = try_device_proxy(device_name)
        if not device:
            print(f"[INIT ERROR] BPM device {device_name} unavailable.")
            return False

        view.bpm_pvs.device = device
        view.bpm_pvs.device.write_attribute("bdata", view.default_bpm_legacy_data)
        print(f"[INIT] BPM device initialized: {device_name}")
        return True
    except Exception as e:
        print(f"[WRITE ERROR] Failed to initialize device: {e}")
        return False


async def heartbeat_loop():
    """Ping the BPM device periodically."""
    logger.info("Heartbeat loop started")
    while not stop_event.is_set():
        if not view.bpm_pvs.device:
            success = await initialize_view()
            if not success:
                logger.warning("[HEARTBEAT] Waiting 5s before retry...")
                await asyncio.sleep(5)
                continue

        try:
            view.bpm_pvs.device.ping()
            print("[HEARTBEAT] Ping successful")
        except Exception as exc:
            print(f"[HEARTBEAT FAIL] {exc}. Resetting device and waiting...")
            view.bpm_pvs.device = None
        await asyncio.sleep(2)  # Maintain at least 2s delay between pings

    logger.info("Heartbeat loop stopped")


async def main():
    logger.info("Starting heartbeat monitor process...")
    try:
        await heartbeat_loop()
    except asyncio.CancelledError:
        logger.info("Heartbeat monitor cancelled")
    finally:
        cleanup()


if __name__ == "__main__":
    asyncio.run(main())
