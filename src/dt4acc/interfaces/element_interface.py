from abc import abstractmethod, ABCMeta


class AlignmentInterface(metaclass=ABCMeta):
    @abstractmethod
    def get_name(self):
        pass

    @abstractmethod
    def get_x(self):
        pass

    @abstractmethod
    def get_y(self):
        pass

    @abstractmethod
    def get_roll(self):
        pass

    @abstractmethod
    def set_x(self, val):
        pass

    @abstractmethod
    def set_y(self, val):
        pass

    @abstractmethod
    def set_roll(self, val):
        pass


class ElementInterface(metaclass=ABCMeta):
    """
    Todo:
        * review if an method should be added that user is supposed
          to override and an other one that is the external
          interface?

        * should be the on_update_finished an event that has to
          be added here?

    Reason: after the element has been updated the proxy should
    trigger the on_update_finished.

    """
    @abstractmethod
    def update(self, property_id, value, element):
        pass


class MagneticElementInterface(ElementInterface):
    """
    Todo:
        alignment is not part of elementinterface by design
        it should be part of magnet
    """
    @abstractmethod
    def get_alignment(self) -> AlignmentInterface:
        pass

    @abstractmethod
    def get_main_field_value(self):
        pass

    @abstractmethod
    def set_main_field_value(self):
        pass
