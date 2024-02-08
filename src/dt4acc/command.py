import os

from .update_context_manager import UpdateContext

CALCULATION_ENGINE_default = os.environ["CALCULATION_ENGINE"]

if CALCULATION_ENGINE_default == 'thor_scsi':
    from .accelerators import thor_scsi_accelerator

    acc = thor_scsi_accelerator.set_accelerator()
else:
    from .accelerators import pyat_accelerator

    acc = pyat_accelerator.set_accelerator()

def publish(*, what):
    print(f"Need to implement publishing {what}?")

def update(*, element_id, property_name, value=None):
    """
    What to do here:
        find the element
        get the property
        set the value
        see if further processing is required

        Who takes care of the read back
        Is value=None a value user wants to set?
        If so get an other place holder..
    """
    with UpdateContext(element_id=element_id, property_name=property_name, value=value, kwargs=dict()):
        elem_proxy = acc.get_element(element_id)
        elem_proxy.update(property_name, value)
