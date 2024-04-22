from dt4acc.setup_configuration.server import create_pv

from ..setup_configuration.pv_manager import PVManager

# Instantiate the PVManager
manager = PVManager()


def update_or_create_pv(element,pv_name, value, value_type,initial_type):
    # Check if the PV already exists
    pv = manager.get_pv(pv_name)
    if pv:
        # Update the existing PV
        manager.update_pv(pv_name, value)
    else:
        # Create a new PV and add it to the manager
        new_pv = create_pv(initial_value_type=value_type,initial_type=initial_type, element=element)
        manager.add_pv(pv_name, new_pv)

