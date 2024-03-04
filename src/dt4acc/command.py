from .bl.context_manager_with_trigger import TriggerEnterExitContextManager
from .bl.event import Event
from .update_context_manager import UpdateContext
from .view.calculation_progress_view import CalculationProgressView
import os

CALCULATION_ENGINE_default = os.environ["CALCULATION_ENGINE"]

if CALCULATION_ENGINE_default == 'thor_scsi':
    from .accelerators import thor_scsi_accelerator

    acc = thor_scsi_accelerator.set_accelerator()
else:
    from .accelerators import pyat_accelerator

    acc = pyat_accelerator.set_accelerator()

def publish(*, what):
    print(f"Need to implement publishing {what}?")

prefix = "Pierre:DT"
view = CalculationProgressView(prefix=f"{prefix}:dt:im:updates")
on_update_event = Event()
on_update_event.append(view.on_update)


def update(*, element_id, property_name, value=None):
    """
    What to do here:
        find the element
        get the property
        set the value
        see if further processing is required

        Who takes care of the read back
        Is value=None a value user wants to set?
        If so get another placeholder..
    """
    with TriggerEnterExitContextManager(on_update_event):
        with UpdateContext(element_id=element_id, property_name=property_name, value=value, kwargs=dict()):
            elem_proxy = acc.get_element(element_id)
            elem_proxy.update(property_name, value)
