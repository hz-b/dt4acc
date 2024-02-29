import logging
import queue
import threading
import time
import datetime
from typing import Union

from .event import Event
from queue import Queue

logger = logging.getLogger("dt4acc")


class DelayExecution:
    """

    Args:
        callback:
        delay: how much to delay execution. set it to None for
        synchronous execution
    """

    def __init__(self, *, callback, delay: Union[float, None]):
        self.callback = callback
        self.set_delay(delay)

        self.pending_queue = Queue()  # Queue for managing pending executions
        self.worker_thread = threading.Thread(target=self.worker)
        self.worker_thread.daemon = True  # Daemonize the worker thread
        self.worker_thread.start()
        self.calculation_requested = False

    def set_delay(self, delay: Union[float, None]):
        if delay is not None:
            delay = float(delay)

        self.delay = delay

    def request_execution(self):
        if self.delay is None:
            # In case there was still a pending calculation
            self.calculation_requested = False
            self.callback()
            return

        self.calculation_requested = True
        self.pending_queue.put(datetime.datetime.now())

    def worker(self):
        while True:
            try:
                timestamp = self.pending_queue.get(block=True, timeout=self.delay)
            except queue.Empty:
                if self.calculation_requested:
                    self.callback()
                    self.calculation_requested = False
            else:
                continue

                time_diff = (datetime.datetime.now() - timestamp).total_seconds()
                if time_diff < self.delay:
                    time.sleep(self.delay - time_diff)
                self.callback()
                self.pending_queue.task_done()
