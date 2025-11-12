from typing import Sequence, Optional

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
from .ai.oat_planner import OAKPlanner
from .update_context_manager import UpdateContext


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
            oak_planner: Optional[OAKPlanner] = None
    ):
        self.command_rewritter = command_rewritter
        self.liaison_manager = liaison_manager
        self.translator_service = translator_service
        self.acc_mgr = acc_mgr
        self.oak_planner = oak_planner

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
            # in UpdateManager.update(...) before the command rewriting step:
            if hasattr(self, "oak_planner") and self.oak_planner is not None:
                try:
                    oak_actions = self.oak_planner.plan_set_property(device_id, property_name, value)
                except Exception as exc:
                    raise  # or log and abort

                # Convert OAK actions into commands / calls. Keep execution explicit.
                for action in oak_actions:
                    if action.name == "set_master_clock_ref":
                        # translate to your device update flow, e.g. call update() recursively or build command
                        await self.update(device_id=action.params["device"], property_name="reference_frequency",
                                          value=action.params["reference_frequency"])
                    elif action.name == "set_property":
                        # proceed with normal inverse + send to accelerator
                        # you can inject action.params["value"] into command rewriting
                        value_to_apply = action.params["value"]
                        # existing code: build cmds = self.command_rewritter.inverse(...)
                        # process cmds as before, using value_to_apply
                        cmds = self.command_rewritter.inverse(
                            Command(
                                id=device_id,
                                property=property_name,
                                value=value_to_apply,
                                behaviour_on_error=BehaviourOnError.stop,
                            )
                        )
                        for cmd in cmds:
                            elem_proxy = await self.acc_mgr.accelerator.get_element(cmd.id)
                            await elem_proxy.update(cmd.property, cmd.value, None)
                return  # skip original flow if OAK handled it
            else:  # fall back to original behavior (no OAK)
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
