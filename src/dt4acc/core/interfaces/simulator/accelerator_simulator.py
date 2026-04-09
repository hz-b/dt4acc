"""

Todo:
    review if required, or if it should rather follow
    the backend interface

"""
from abc import ABCMeta, abstractmethod

from .element import ElementInterface


class AcceleratorSimulatorInterface(metaclass=ABCMeta):
    """

    Todo:
        Derive from a list interface
    """

    @abstractmethod
    def get(self, element_id) -> ElementInterface:
        """
        Review if derived classes use async implementations
        """
        pass
