import asyncio
import datetime

from .event import Event


class DelayExecution:
    """
    Class to manage delayed execution of a given callback function.
    """

    def __init__(self, callback, delay=0.1):
        """
        Initialize DelayExecution with a callback and delay time.

        Args:
            callback (coroutine function): The function to execute after the delay.
            delay (float): The delay in seconds before executing the callback.
        """
        self.callback = callback  # Function to execute after delay
        self.delay = delay  # Delay duration in seconds
        self.pending_task = None  # Reference to the currently pending execution task
        self.last_execution_time = None  # Timestamp of the last execution
        self.on_calculation_requested = Event()  # Event triggered when calculation is requested
        self.on_calculation = Event()  # Event triggered when calculation completes

    async def request_execution(self):
        """
        Queue an execution request, resetting the timer with each call.

        This method triggers the `on_calculation_requested` event and schedules
        the callback after the specified delay.
        """
        # Notify that a calculation request has been made
        await self.on_calculation_requested.trigger(datetime.datetime.now())

        # Cancel any pending task to reset the delay timer
        if self.pending_task is not None:
            self.pending_task.cancel()

        # Schedule a new execution task after the delay
        self.pending_task = asyncio.create_task(self._delayed_execution())

    async def _delayed_execution(self):
        """
        Private method to handle the delayed execution logic.

        Waits for the specified delay, then executes the callback and triggers
        the `on_calculation` event.
        """
        try:
            await asyncio.sleep(self.delay)  # Wait for the specified delay
            await self.callback()  # Execute the callback function
            self.last_execution_time = datetime.datetime.now()  # Record execution time
            await self.on_calculation.trigger(self.last_execution_time)
        except asyncio.CancelledError:
            # Task was cancelled, do nothing
            pass

    async def process_requests(self):
        """
        Process queued execution requests with a delay.

        Iterates over the queue of pending requests, executing them one by one
        with the specified delay.
        """
        while not self.pending_queue.empty():
            await self.pending_queue.get()
            await asyncio.sleep(self.delay)
            await self.callback()  # Execute the callback after the delay
            await self.on_calculation.trigger(datetime.datetime.now())

    def set_delay(self, new_delay):
        """
        Set a new delay for the execution timer.

        Args:
            new_delay (float): New delay in seconds.
        """
        self.delay = new_delay
