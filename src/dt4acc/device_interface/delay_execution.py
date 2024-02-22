import logging
import threading
import time
import datetime
from .event import Event
from queue import Queue

logger = logging.getLogger("dt4acc")

class DelayExecution:
    def __init__(self, *, callback, delay):
        self.callback = callback
        self.delay = float(delay)
        self.pending_queue = Queue()  # Queue for managing pending executions
        self.worker_thread = threading.Thread(target=self.worker)
        self.worker_thread.daemon = True  # Daemonize the worker thread
        self.worker_thread.start()

    def request_execution(self):
        self.pending_queue.put(datetime.datetime.now())

    def worker(self):
        while True:
            timestamp = self.pending_queue.get()
            time_diff = (datetime.datetime.now() - timestamp).total_seconds()
            if time_diff < self.delay:
                time.sleep(self.delay - time_diff)
            self.callback()
            self.pending_queue.task_done()