import asyncio


class Event:
    def __init__(self):
        self.callbacks = []
        self.event_queue = asyncio.Queue()

    async def subscribe(self, callback):
        status = self.callbacks.append(callback)
        if status is None:
            print(callback)
        await status

    async def trigger(self, obj):
        # Process each callback asynchronously but in sequence
        if len(self.callbacks) == 0:
            print(self)
            return
        for callback in self.callbacks:
            await callback(obj)  # Ensure your callbacks are designed as coroutine functions


    async def process_events(self):
        while True:
            obj, callbacks = await self.event_queue.get()
            for callback in callbacks:
                callback(obj)  # Ensure your callbacks are coroutine functions


class StatusChange(Event):
    async def trigger(self, flag: bool):
        return await super().trigger(flag)
