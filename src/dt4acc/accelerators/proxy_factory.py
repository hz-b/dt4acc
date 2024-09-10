from ..accelerators.element_proxies import (
    ElementProxy,
    KickAngleCorrectorProxy,
)
from ..interfaces.proxy_factory_interface import ProxyFactoryInterface


class PyATProxyFactory(ProxyFactoryInterface):
    """

    Warning:
        Currently just a hack to show that the interface could be
        used. Needs to be reworked as soon as lattice_model is
        available.
    """

    def __init__(self, *, lattice_model, at_lattice):
        """

        Args:
            lattice_model:

        Warning:
             currently uses an at lattice to do the job
             but that its not what it should do
        """
        self.acc = at_lattice

    def get(self, element_id):
        pass

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

        return self.instaniate_addon_proxy(
            sub_lattice, element_id=element_id, host_element_id=host_element_id
        )

    def get_element_id_of_host(self, element_id):
        """
        Warning:
            Currently just a hack
        """
        if element_id[0] == "H":
            return element_id[1:]
        elif element_id[0] == "V":
            return element_id[1:]
        else:
            raise ValueError("Do not know how to handle element id %s", element_id)

    def instaniate_addon_proxy(self, sub_lattice, *, element_id, host_element_id):
        """currently only implementing for steerers on sextupoles"""
        assert host_element_id[0] == "S"
        if element_id[0] == "H":
            return KickAngleCorrectorProxy(
                sub_lattice,
                correction_plane="horizontal",
                element_id=element_id,
                host_element_id=host_element_id,
            )
        elif element_id[0] == "V":
            return KickAngleCorrectorProxy(
                sub_lattice,
                correction_plane="vertical",
                element_id=element_id,
                host_element_id=host_element_id,
            )
        else:
            raise ValueError("Do not know how to handle element id")
