from abc import ABCMeta, abstractmethod


class ViewInterface(metaclass=ABCMeta):
    @abstractmethod
    async def push(self, data):
        """
        """
        raise NotImplementedError("use base class instead")