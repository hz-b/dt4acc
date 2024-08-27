import asyncio
import datetime

from dt4acc.bl.event import Event

class DelayExecution:
    def __init__(self, callback, delay=0.1):
        self.callback = callback
        self.delay = delay
        self.pending_task = None
        self.last_execution_time = None
        self.on_calculation_requested = Event()
        self.on_calculation = Event()
        # self.callback = callback
        # self.delay = delay
        # self.pending_queue = asyncio.Queue()
        # self.processing_task = None

    async def request_execution(self):
        # Trigger the on_calculation_requested event whenever a request is made
        await self.on_calculation_requested.trigger(datetime.datetime.now())
        """Queue an execution request, resetting the timer with each call."""
        if self.pending_task is not None:
            # Cancel the pending task if it's still running
            self.pending_task.cancel()

        # Schedule a new task with the delay
        self.pending_task = asyncio.create_task(self._delayed_execution())

    async def _delayed_execution(self):
        """Wait for the delay period before executing the callback."""
        try:
            await asyncio.sleep(self.delay)
            await self.callback()  # Trigger the calculation after the delay
            # Trigger the on_calculation event after the calculation is completed
            await self.on_calculation.trigger(datetime.datetime.now())
        except asyncio.CancelledError:
            # Task was cancelled, do nothing
            pass

    # async def request_execution(self):
    #     """Queue an execution request, ensuring only one execution request is processed at a time."""
    #     await self.pending_queue.put(datetime.datetime.now())
    #     await self.on_calculation_requested.trigger(datetime.datetime.now())
    #     if self.processing_task is None or self.processing_task.done():
    #         self.processing_task = asyncio.create_task(self.process_requests())

    async def process_requests(self):
        """Process queued execution requests with a delay."""
        while not self.pending_queue.empty():
            await self.pending_queue.get()
            await asyncio.sleep(self.delay)
            await self.callback()  # Execute the callback after the delay
            await self.on_calculation.trigger(datetime.datetime.now())

    def set_delay(self, new_delay):
        """Set a new delay for calculations."""
        self.delay = new_delay
