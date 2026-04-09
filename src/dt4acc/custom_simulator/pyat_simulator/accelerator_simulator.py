

from .element_proxies import ElementProxy, KickAngleCorrectorProxy
from ...core.interfaces.simulator.accelerator_simulator import AcceleratorSimulatorInterface
import at

class PyATAcceleratorSimulator(AcceleratorSimulatorInterface):
    """
    Factory class for creating proxies for accelerator elements.

    This class provides an interface for retrieving accelerator element proxies
    from a given lattice structure.

    Warning:
        Currently, this implementation uses an `at_lattice` directly,
        which should be revised when a proper lattice model becomes available.

    Todo:
        Revisit name: still a proxy? The element proxy currently not necessary`?

        Leave addon element proxy e.g. for handling combined function magnets

        Do we only need to calculate optics? How much one needs to optimise
        calculation speed.


    """

    def __init__(self, *, at_lattice):
        """
        Initialize the proxy factory.

        Args:
            at_lattice: The actual AT lattice used to retrieve elements.
        """
        self.acc = at_lattice

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(at_lattice={self.acc})"

    def get_optics_parameters(self):
        x0, ring_pars, elem_data = self.acc.get_optics(at.All)
        return x0, ring_pars, elem_data

    # def get_twiss(self) -> Twiss:
    #     pass
    #
    # def get_track(self) -> CalculatedTrack:
    #     pass

    # def get_tune(self) -> Tune:
    #    """
    #    Todo:
    #        review who else needs these data
    #    """
    #    _, ring_pars, elem_data = self._get_optics_parameter()
    #
    #    tune = ring_pars["tune"]
    #    return Tune(x=tune[0], y=tune[1])

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

        raise ValueError(f"Unknown element id: {element_id}")

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

        Warning:
            this code should not be used any more
        """

        # raise AssertionError("Code should not be used any more")

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
            sub_lattice,
            element_id=element_id,
            host_element_id=host_element_id,
        )
