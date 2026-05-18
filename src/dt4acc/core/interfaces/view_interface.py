from abc import ABCMeta, abstractmethod

from dt4acc_lib.model.output.result import TranslatedReading
from dt4acc_lib.model.utils.command import ReadCommand


class ViewInterface(metaclass=ABCMeta):
    @abstractmethod
    async def dispatch(self, rcmd: ReadCommand, result: TranslatedReading) -> None:
        """dispatch updated data to view
        """
        raise NotImplementedError("use derived class instead")

    @abstractmethod
    async def push_invalid(self) -> None:
        """Announce that data should be invalidated

        Typically, sent if calculation backend fails
        """
        raise NotImplementedError("use derived class instead")
