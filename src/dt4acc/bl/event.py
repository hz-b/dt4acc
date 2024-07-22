import asyncio


class Event:
    def __init__(self):
        self.callbacks = []

    def subscribe(self, callback):
        self.callbacks.append(callback)

    def trigger(self, obj):
        async def execute():
            # todo: use asyncio,gather
            for cb in self.callbacks:
                await cb(obj)

        loop = asyncio.get_running_loop()
        loop.run_until_complete(execute())


class StatusChange(Event):
    async def trigger(self, flag: bool):
        return await super().trigger(flag)
