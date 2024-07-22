import asyncio


class Event:
    def __init__(self):
        self.callbacks = []
        self.event_queue = asyncio.Queue()

    def subscribe(self, callback):
        self.callbacks.append(callback)

    async def trigger(self, obj):
        # Process each callback asynchronously but in sequence
        for callback in self.callbacks:
            await callback(obj)  # Ensure your callbacks are designed as coroutine functions

    async def process_events(self):
        while True:
            obj, callbacks = await self.event_queue.get()
            for callback in callbacks:
                await callback(obj)  # Ensure your callbacks are coroutine functions


class StatusChange(Event):
    async def trigger(self, flag: bool):
        return await super().trigger(flag)
