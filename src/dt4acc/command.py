import os

from dt4acc.update_context_manager import UpdateContext
from .bl.event import Event
from .view.calculation_result_view import StatusFlagView

CALCULATION_ENGINE_default = 'AT'  # os.environ["CALCULATION_ENGINE"]

if CALCULATION_ENGINE_default == 'thor_scsi':
    from .accelerators import thor_scsi_accelerator

    acc = thor_scsi_accelerator.set_accelerator()
else:
    from .accelerators import pyat_accelerator

    acc = pyat_accelerator.set_accelerator()


def publish(*, what):
    print(f"Need to implement publishing {what}?")


# Signals to EPICS:
#      that an update is in progress
prefix = os.environ.get("DT4ACC_PREFIX", "Anonym")   # os.environ["DT4ACC_PREFIX"]
view = StatusFlagView(prefix=f"{prefix}:dt:im:updates")
on_update_event = Event()
on_update_event.subscribe(view.on_update)

# signal if orbit or twiss calculations are requested
view = StatusFlagView(prefix=f"{prefix}:im:calc:orbit:exc")
acc.on_orbit_calculation.subscribe(view.on_update)
view = StatusFlagView(prefix=f"{prefix}:im:calc:orbit:req")
acc.on_orbit_calculation_request.subscribe(view.on_update)

view = StatusFlagView(prefix=f"{prefix}:im:calc:twiss:exc")
acc.on_twiss_calculation_request.subscribe(view.on_update)
view = StatusFlagView(prefix=f"{prefix}:im:calc:twiss:req")
acc.on_twiss_calculation_request.subscribe(view.on_update)


async def update(*, element_id, property_name, value=None, element):
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
    # with TriggerEnterExitContextManager(on_update_event):
    with UpdateContext(element_id=element_id, property_name=property_name, value=value,element= element, kwargs=dict()):
        elem_proxy = await acc.get_element(element_id)
        await elem_proxy.update(property_name, value, element)
