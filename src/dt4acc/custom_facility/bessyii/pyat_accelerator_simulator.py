from dt4acc_lib.pyat_simulator.accelerator_simulator import PyATAcceleratorSimulator
from dt4acc_lib.pyat_simulator.element_proxies import (
    KickAngleCorrectorProxy,
    ElementProxy,
)
from dt4acc_lib.interfaces.simulator.element import ElementInterface
from dt4acc_lib.pyat_simulator.proxies.proxy_factory import ElementProxyFactory


class BESSYIIPyAtAcceleratorSimulator(PyATAcceleratorSimulator):
    def __init__(self, *, at_lattice, proxy_factory: ElementProxyFactory):
        super().__init__(at_lattice=at_lattice)
        self.proxy_factory = proxy_factory

    def get(self, element_id: str) -> ElementInterface:
        elements = self.acc.get_elements(element_id)
        # should be unique
        if len(elements) == 1:
            (element,) = elements
            return self.proxy_factory.get_proxy(element, element_id=element_id)
        elif len(elements) == 0:
            # Todo: should not be necessary any more,
            #       liaison manager needs to be updated here
            #       and if so it should cross check the name
            #       to yellow
            host_element_id = get_element_id_of_host(element_id)
            elements = self.acc.get_elements(host_element_id)
            (_,) = elements
            return instantiate_addon_proxy(
                elements, element_id=element_id, host_element_id=host_element_id
            )
        else:
            raise ValueError(f"Got too many elements for {element_id}")


def get_element_id_of_host(element_id: str) -> str:
    """
    Derives the host element ID from the provided element ID.
    Used by the EPICS path (H/V prefix convention).

    Args:
        element_id (str): The ID of the element.

    Returns:
        str: The ID of the host element.
    """
    if element_id.startswith("H") or element_id.startswith("V"):
        return element_id[1:]
    raise ValueError(f"Unknown element id: {element_id}")


def instantiate_addon_proxy(elements, *, element_id, host_element_id):
    """
    Instantiates the correct proxy for the given sub lattice and element ID.
    Used by the EPICS path (H/V prefix convention).

    Args:
        element: the element that AT knows of
        element_id: The ID of the element.
        host_element_id: The ID of the host element.

    Returns:
        KickAngleCorrectorProxy: The proxy instance for the element.

    """
    if not host_element_id.startswith("S"):
        raise ValueError(f"Unsupported host element ID: {host_element_id}")

    correction_plane = (
        "horizontal"
        if element_id.startswith("H")
        else "vertical"
        if element_id.startswith("V")
        else None
    )
    if correction_plane is None:
        raise ValueError(f"Unknown correction plane for element ID: {element_id}")

    return KickAngleCorrectorProxy(
        elements,
        element_id=element_id,
        host_element_id=host_element_id,
    )


__all__ = [BESSYIIPyAtAcceleratorSimulator]
