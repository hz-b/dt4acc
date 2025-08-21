"""
Async wrapper for device updates to handle the coroutine issue.
This provides a clean way to call async functions from sync methods.
"""

import asyncio
import threading
from functools import wraps
from dt4acc.core.utils.logger import get_logger

logger = get_logger()

def run_async_in_background(func):
    """
    Decorator to run async functions in the background without blocking.
    This is used for device update methods that need to call async functions.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Try to get the current event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Loop is running, create a task
                    loop.create_task(func(*args, **kwargs))
                else:
                    # Loop exists but not running, run the function
                    loop.run_until_complete(func(*args, **kwargs))
            except RuntimeError:
                # No event loop, create a new one
                asyncio.run(func(*args, **kwargs))
        except Exception as e:
            logger.error(f"Error running async function {func.__name__}: {e}")
            # Don't raise here, just log the error
    return wrapper

def run_async_calls_in_background(func):
    """
    Decorator that makes a sync method async and handles async calls within it.
    This allows the method to use await internally.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            # Call the original function (which now uses await)
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in async method {func.__name__}: {e}")
            raise
    
    # Return the async wrapper
    return wrapper

def run_async_sync(func):
    """
    Decorator to run async functions synchronously.
    This blocks until the async function completes.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Try to get the current event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Loop is running, we need to run in a new thread
                    result = None
                    exception = None
                    
                    def run_in_thread():
                        nonlocal result, exception
                        try:
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            result = new_loop.run_until_complete(func(*args, **kwargs))
                        except Exception as e:
                            exception = e
                        finally:
                            new_loop.close()
                    
                    thread = threading.Thread(target=run_in_thread)
                    thread.start()
                    thread.join()
                    
                    if exception:
                        raise exception
                    return result
                else:
                    # Loop exists but not running, run the function
                    return loop.run_until_complete(func(*args, **kwargs))
            except RuntimeError:
                # No event loop, create a new one
                return asyncio.run(func(*args, **kwargs))
        except Exception as e:
            logger.error(f"Error running async function {func.__name__}: {e}")
            raise
    return wrapper
