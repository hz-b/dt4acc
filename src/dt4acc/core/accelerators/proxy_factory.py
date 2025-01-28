from .element_proxies import ElementProxy, KickAngleCorrectorProxy
from ..interfaces.proxy_factory_interface import ProxyFactoryInterface


class PyATProxyFactory(ProxyFactoryInterface):
    """
    Factory class for creating proxies for accelerator elements.

    This class provides an interface for retrieving accelerator element proxies
    from a given lattice structure.

    Warning:
        Currently, this implementation uses an `at_lattice` directly, which should be
        revised when a proper lattice model becomes available.
    """

    def __init__(self, *, lattice_model, at_lattice):
        """
        Initialize the proxy factory.

        Args:
            lattice_model: The high-level model of the accelerator lattice (currently unused).
            at_lattice: The actual AT lattice used to retrieve elements.
        """
        self.acc = at_lattice

    def get(self, element_id):
        """
        Retrieve an element proxy based on the given element ID.

        Args:
            element_id (str): The ID of the element to retrieve.

        Returns:
            ElementProxy: The proxy object for the requested element.

        Raises:
            ValueError: If the element is not found in the lattice.
        """

        sub_lattice = self.acc[element_id]
        # single element expected in sub lattice
        try:
            (_,) = sub_lattice
            found_sub_lattice = True
        except ValueError:
            found_sub_lattice = False

        if found_sub_lattice and sub_lattice:
            return ElementProxy(sub_lattice, element_id=element_id)

        host_element_id = self.get_element_id_of_host(element_id)
        sub_lattice = self.acc[host_element_id]
        # single element expected in sublattice
        (_,) = sub_lattice
        if not sub_lattice:
            raise ValueError(f"Element with ID {element_id} not found")

        return self.instantiate_addon_proxy(
            sub_lattice, element_id=element_id, host_element_id=host_element_id
        )

    @staticmethod
    def get_element_id_of_host(element_id: str) -> str:
        """
        Derives the host element ID from the provided element ID.

        Args:
            element_id (str): The ID of the element.

        Returns:
            str: The ID of the host element.

        Raises:
            ValueError: If the element ID cannot be processed.
        """
        if element_id.startswith("H") or element_id.startswith("V"):
            return element_id[1:]

        raise ValueError(f"Unknown element ID format: {element_id}")

    def instantiate_addon_proxy(self, sub_lattice, *, element_id, host_element_id):
        """
        Instantiates the correct proxy for the given sub lattice and element ID.

        Args:
            sub_lattice: The AT sub lattice containing the element.
            element_id: The ID of the element.
            host_element_id: The ID of the host element.

        Returns:
            KickAngleCorrectorProxy: The proxy instance for the element.

        Raises:
            ValueError: If the element ID type is unsupported.
        """
        if not host_element_id.startswith("S"):
            raise ValueError(f"Unsupported host element ID: {host_element_id}")

        correction_plane = "horizontal" if element_id.startswith("H") else "vertical" if element_id.startswith(
            "V") else None

        if correction_plane is None:
            raise ValueError(f"Unknown correction plane for element ID: {element_id}")

        return KickAngleCorrectorProxy(
            sub_lattice,
            correction_plane=correction_plane,
            element_id=element_id,
            host_element_id=host_element_id,
        )
