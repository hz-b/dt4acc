import logging
import queue
import threading
import datetime
from typing import Union

from .context_manager_with_trigger import TriggerEnterExitContextManager

from .event import StatusChange
from queue import Queue


class DelayExecution:
    """

    Args:
        callback:
        delay: how much to delay execution. set it to None for
        synchronous execution
    """

    def __init__(self, *, callback, delay: Union[float, None]):
        self._callback = callback
        self.set_delay(delay)

        self.pending_queue = Queue()  # Queue for managing pending executions
        self.worker_thread = threading.Thread(target=self.worker)
        self.worker_thread.daemon = True  # Daemonize the worker thread
        self.worker_thread.start()
        self._calculation_requested = False
        self.on_calculation = StatusChange()
        self.on_calculation_requested = StatusChange()

    @property
    def calculation_requested(self):
        return self._calculation_requested

    @calculation_requested.setter
    def calculation_requested(self, flag: bool):
        flag = bool(flag)
        self.on_calculation_requested.trigger(flag)
        self._calculation_requested = flag

    def callback(self):
        with TriggerEnterExitContextManager(self.on_calculation):
            return self._callback()

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
        # The "busy" wait is favoured to its straightforward
        # implementation.
        # The alternative would be to block forever when
        # calculation_request is false, and to block with timeout
        # only when there is a calculation request. This,however,
        # would require a careful analysis of possible race
        # conditions. In its current form a missed request would
        # only result in some extra delay.
        # The load of this implementation was estimated to be less
        # than 1 percent on a standard cpu. Thus, this extra load
        # is deemed to be acceptable.
        while True:
            try:
                timestamp = self.pending_queue.get(block=True, timeout=self.delay)
            except queue.Empty:
                if self.calculation_requested:
                    self.callback()
                    self.calculation_requested = False
            else:
                continue