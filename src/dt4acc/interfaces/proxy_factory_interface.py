from abc import abstractmethod, ABCMeta
from .element_interface import ElementInterface


class ProxyFactoryInterface(metaclass=ABCMeta):
    @abstractmethod
    def get(self, element_id) -> ElementInterface:
        raise NotImplementedError
