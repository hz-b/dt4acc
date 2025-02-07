from abc import ABCMeta, abstractmethod

from .element_interface import ElementInterface


class AcceleratorInterface(metaclass=ABCMeta):
    """

    Todo:
        Derive from a list interface
    """

    @abstractmethod
    def get_element(self, element_id) -> ElementInterface:
        """
        Review if derived classes use async implementations
        """
        pass

    @abstractmethod
    def __init__(self, *args, **kwargs):
        pass
