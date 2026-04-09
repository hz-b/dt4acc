
import asyncio
import threading
from dt4acc.core.utils.logger import get_logger

logger = get_logger()

# Global shared event loop and thread
_shared_loop = None
_shared_thread = None
_loop_lock = threading.Lock()


def get_shared_event_loop():
  
    global _shared_loop, _shared_thread
    
    with _loop_lock:
        if _shared_loop is None or _shared_loop.is_closed():
            logger.info("Creating shared event loop for Tango devices")
            _shared_loop = asyncio.new_event_loop()
            
            def run_loop():
                asyncio.set_event_loop(_shared_loop)
                _shared_loop.run_forever()
            
            _shared_thread = threading.Thread(target=run_loop, daemon=True, name="SharedEventLoop")
            _shared_thread.start()
        
        return _shared_loop


def shutdown_shared_event_loop():
    global _shared_loop, _shared_thread
    
    with _loop_lock:
        if _shared_loop is not None and not _shared_loop.is_closed():
            _shared_loop.call_soon_threadsafe(_shared_loop.stop)
            if _shared_thread and _shared_thread.is_alive():
                _shared_thread.join(timeout=2.0)
            if not _shared_loop.is_closed():
                _shared_loop.close()
            _shared_loop = None
            _shared_thread = None

