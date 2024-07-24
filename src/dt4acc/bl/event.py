import asyncio


class Event:
    def __init__(self):
        self.callbacks = []

    def subscribe(self, callback):
        if not asyncio.iscoroutinefunction(callback):
            raise TypeError("Callback must be an async function")
        self.callbacks.append(callback)

    async def trigger(self, obj):
        for callback in self.callbacks:
            await callback(obj)

class StatusChange(Event):
    async def trigger(self, flag: bool):
        return await super().trigger(flag)