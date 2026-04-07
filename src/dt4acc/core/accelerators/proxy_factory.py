from typing import Any

from ...config.accelerator_config import accelerator_config

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

    Todo:
        Revisit name: still a proxy? The element proxy currently not necessary`?

        Leave addon element proxy e.g. for handling combined function magnets
    """

    def __init__(self, *, lattice_model, at_lattice, elements: list[dict[str, Any]] | None = None):
        """
        Initialize the proxy factory.

        Args:
            lattice_model: The high-level model of the accelerator lattice (currently unused).
            at_lattice: The actual AT lattice used to retrieve elements.
        """
        self.acc = at_lattice
        self.elements = elements
        self._uuid_by_name = None

    def _get_elements(self) -> list[dict[str, Any]]:
        if self.elements is not None:
            return self.elements

        elements = accelerator_config.get_accelerator_setup()
        if elements is None:
            raise RuntimeError(
                "Accelerator setup is not loaded. "
                "Provide `elements` explicitly or initialize accelerator_config first."
            )
        return elements

    def _get_uuid_by_name(self) -> dict[str, str]:
        if self._uuid_by_name is None:
            self._uuid_by_name = {
                entry["name"]: entry["uuid"]
                for entry in self._get_elements()
                if "name" in entry and "uuid" in entry
            }
        return self._uuid_by_name

    def get_element_by_uuid(self, uuid):
        for elem in self.acc:
            if getattr(elem, "UUID", None) == uuid:
                return elem
        return None

    def get_uuid(self, element_id):
        return self._get_uuid_by_name().get(element_id)

    def get(self, element_id,uuid=None):
        """
        Retrieve an element proxy based on the given element ID.

        Args:
            element_id (str): The ID of the element to retrieve.

        Returns:
            ElementProxy: The proxy object for the requested element.

        Raises:
            ValueError: If the element is not found in the lattice.
        """
        if uuid is not None:
            sub_lattice = (self.get_element_by_uuid(uuid),)
        else:
            sub_lattice = self.acc[element_id]
        # single element expected in sub lattice
        try:
            (_,) = sub_lattice
            found_sub_lattice = True
        except ValueError:
            found_sub_lattice = False

        if found_sub_lattice and sub_lattice:
            return ElementProxy(sub_lattice, element_id=element_id)
        uuid_ = self.get_uuid(element_id)
        host_element_id = uuid_ #self.get_element_id_of_host(element_id)
        sub_lattice = (self.get_element_by_uuid(uuid_),)
        # sub_lattice = self.acc[host_element_id]
        # single element expected in sublattice
        (_,) = sub_lattice
        return ElementProxy(sub_lattice, element_id=element_id)
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
        return (element_id,)
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
