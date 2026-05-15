
import asyncio
import threading
from ..utils.logger import get_logger

logger = get_logger()

class SharedEventLoop:
    """
    Todo:
        is this functionality not provided by asyncio

    """
    def __init__(self, lock = None):
        if lock is None:
            lock = threading.Lock()
        self.lock = lock
        self.thread = None
        self.loop = None

    def get(self):
        with self.lock:
            if self.loop is None or self.loop.is_closed():
                logger.info("Creating shared asyncio event loop")
                self.loop = asyncio.new_event_loop()

                def run_loop():
                    asyncio.set_event_loop(self.loop)
                    self.loop.run_forever()

                self.thread = threading.Thread(target=run_loop, daemon=True, name="SharedEventLoop")
                self.thread.start()

        assert self.thread is not None
        assert self.loop is not None
        return self.loop

    def shutdown(self):
        with self.lock:
            if self.loop is not None and not self.loop.is_closed():
                self.loop.call_soon_threadsafe(self.loop.stop)
                if self.thread and self.thread.is_alive():
                    self.thread.join(timeout=2.0)
                if not self.loop.is_closed():
                    self.loop.close()
                self.loop = None
                self.thread = None

    def __del__(self):
        if self.loop is not None or self.thread is not None:
            self.shutdown()


_shared_event_loop = SharedEventLoop()


def get_shared_event_loop():
    return _shared_event_loop.get()


def shutdown_shared_event_loop():
    _shared_event_loop.shutdown()


__all__ = ["get_shared_event_loop", "shutdown_shared_event_loop"]
