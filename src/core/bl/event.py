import asyncio


class Event:
    """
    A generic event class to manage asynchronous event callbacks.
    """
    def __init__(self):
        # List to store callback functions
        self.callbacks = []

    def subscribe(self, callback):
        """
        Subscribe an asynchronous callback function to the event.

        Args:
            callback (coroutine function): The function to be called when the event is triggered.

        Raises:
            TypeError: If the provided callback is not an async function.
        """
        if not asyncio.iscoroutinefunction(callback):
            raise TypeError("Callback must be an async function")
        self.callbacks.append(callback)

    async def trigger(self, obj):
        """
        Trigger all subscribed callbacks asynchronously.

        Args:
            obj: The object/data to pass to the callback functions.
        """
        for callback in self.callbacks:
            await callback(obj)


class StatusChange(Event):
    """
    Specialized Event subclass to handle status changes.
    """
    async def trigger(self, flag: bool):
        """
        Trigger the event with a boolean flag indicating a status change.

        Args:
            flag (bool): The status flag to pass to the event callbacks.
        """
        return await super().trigger(flag)
