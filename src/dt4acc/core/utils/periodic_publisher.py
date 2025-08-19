import asyncio
import itertools

from .logger import get_logger
from ..interfaces.view_interface import ViewInterface

#: use a "singleton", even if the name is not unique it should still work
counter = itertools.count()
logger = get_logger()

class PeriodicPublisher:
    """

    Todo:
        find a better name for it?
        Its rather a periodic publisher proxy

        It is expected to be triggered from outside
    """
    def __init__(self, view: ViewInterface, name: str):
        """

        Todo:
            view should cohere to a protocol or interface
        """
        self.view = view
        self.data = None
        self.name = name

    def set_data(self, data):
        self.data = data

    async def publish(self):
        """
        Expect that publish is called in parallel, thus just return stat object
        """
        #  name=f"publish-data-{self.name}-{next(counter)}"
        if self.data is None:
            logger.warning(f"{self.__class__.__name__}(name={self.name}), self.data is None, thus not publishing data")
            return
        return await self.view.push(self.data)