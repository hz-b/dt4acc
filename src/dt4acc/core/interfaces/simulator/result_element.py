from abc import ABCMeta, abstractmethod


class ResultElement(metaclass=ABCMeta):
    """
    Todo:
        just for pyat or for all?

    Currently just a convenience for pyAT backend
    """

    @abstractmethod
    def get(self, prop_id: str) -> object:
        raise NotImplementedError("use derived class instead")
