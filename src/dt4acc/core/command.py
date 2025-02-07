from typing import Sequence

from bact_twin_architecture.data_model.command import Command, BehaviourOnError
from bact_twin_architecture.data_model.identifiers import (
    LatticeElementPropertyID,
    DevicePropertyID,
    ConversionID,
)
from bact_twin_architecture.interfaces.command_rewritter import CommandRewriterBase
from bact_twin_architecture.interfaces.liaison_manager import LiaisonManagerBase
from bact_twin_architecture.interfaces.translator_service import TranslatorServiceBase

from .accelerators.accelerator_manager import AcceleratorManager
from .update_context_manager import UpdateContext
from ..custom_epics.ioc.liasion_translation_manager import TranslatorService


class UpdateManager:
    """Handle update requests from the device view

    Treats the incoming requests as commands to be rewritten and delivered to the
    machine

    Supports peeking into the engine
    """

    def __init__(
        self,
        *,
        command_rewritter: CommandRewriterBase,
        liaison_manager: LiaisonManagerBase,
        translator_service: TranslatorServiceBase,
        acc_mgr: AcceleratorManager,
    ):
        self.command_rewritter = command_rewritter
        self.liaison_manager = liaison_manager
        self.translator_service = translator_service
        self.acc_mgr = acc_mgr

    def device_value_from_peeking_engine(
        self, dev_prop: DevicePropertyID
    ) -> Sequence[float]:
        """
        Todo:
            review interface
            place it in correct layer

            How to handle that many values can be returned
        """
        if dev_prop.device_name[:3].upper() == "CAV":
            pass
        lat_props = self.liaison_manager.inverse(dev_prop)
        if lat_props is None:
            raise AssertionError(
                f"{self.liaison_manager.__class__.__name__} does not know {dev_prop}"
            )

        def convert(lat_prop):
            translator = self.translator_service.get(
                ConversionID(lattice_property_id=lat_prop, device_property_id=dev_prop)
            )
            val = self.peek_engine(lat_prop)
            return translator.forward(val)

        values = [convert(lat_prop) for lat_prop in lat_props]
        return values

    def peek_engine(self, lat_elem_prop: LatticeElementPropertyID) -> object:
        """peek into underlaying engine to get value

        Todo:
            resolve layring violation
        """
        proxy = self.acc_mgr.accelerator.proxy_factory.get(lat_elem_prop.element_name)
        val = proxy.peek(property_id=lat_elem_prop.property)
        return val

    async def update(self, *, device_id, property_name, value=None, element=None):
        """Update an device property using element knowledge


        Todo:
            element should not need to be passed on beyond this point
        """

        # this argument shall be removed
        assert element is None
        # update context manager: currently here as the async io comm stops at first exception
        with UpdateContext(
            element_id=device_id,
            property_name=property_name,
            value=value,
            element=element,
            kwargs=dict(),
        ):
            cmds = self.command_rewritter.inverse(
                Command(
                    id=device_id,
                    property=property_name,
                    value=value,
                    behaviour_on_error=BehaviourOnError.stop,
                )
            )
            cmds
            for cmd in cmds:
                # Todo: simplify the code down here ...
                # does one still need the proxy factory of the accelerator
                #
                # Todo: revisit if a transactional update should be applied here

                elem_proxy = await self.acc_mgr.accelerator.get_element(cmd.id)
                await elem_proxy.update(cmd.property, cmd.value, element)
