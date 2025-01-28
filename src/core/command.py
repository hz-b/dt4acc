from .accelerators.pyat_accelerator import setup_accelerator
from .update_context_manager import UpdateContext

acc = setup_accelerator()


async def update(*, element_id, property_name, value=None, element):
    """
    Update an element's property and trigger necessary calculations or readbacks.
    """
    with UpdateContext(element_id=element_id, property_name=property_name, value=value, element=element, kwargs=dict()):
        elem_proxy = await acc.accelerator.get_element(element_id)
        await elem_proxy.update(property_name, value, element)
