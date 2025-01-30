from bact_twin_architecture.data_model.command import Command, BehaviourOnError
from bact_twin_architecture.interfaces.command_rewritter import CommandRewriterBase

from .accelerators.accelerator_manager import AcceleratorManager
from .update_context_manager import UpdateContext


class UpdateManager:
    """Handle update requests from the device view

    Treats the incoming requests as commands to be rewritten and delivered to the
    machine
    """
    def __init__(self, command_rewritter: CommandRewriterBase, acc_mgr: AcceleratorManager):
        self.command_rewritter = command_rewritter
        self.acc_mgr = acc_mgr

    async def update(self, *, device_id, property_name, value=None, element=None):
        """Update an device property using element knowledge


        Todo:
            element should not need to be passed on beyond this point
        """

        # this argument shall be removed
        assert element is None
        # update context manager: currently here as the async io comm stops at first exception
        with UpdateContext(element_id=device_id, property_name=property_name, value=value, element=element,
                           kwargs=dict()):
            cmds = self.command_rewritter.inverse(
                Command(id=device_id, property=property_name, value=value, behaviour_on_error=BehaviourOnError.stop
            ))

            for cmd in cmds:
                # Todo: simplify the code down here ...
                # does one still need the proxy factory of the accelerator
                #
                # Todo: revisit if a transactional update should be applied here

                elem_proxy = await self.acc_mgr.accelerator.get_element(cmd.id)
                await elem_proxy.update(cmd.property, cmd.value, element)
