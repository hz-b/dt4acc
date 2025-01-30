from bact_twin_architecture.data_model.identifiers import ConversionID, LatticeElementPropertyID, DevicePropertyID

from src.dt4acc.custom_epics.ioc.liasion_translation_manager import build_managers


def test_translation_service():
    _, tm = build_managers()
    r = tm.get(
        ConversionID(
            lattice_property_id=LatticeElementPropertyID(element_name="Q1M1D1R", property="K"),
            device_property_id=DevicePropertyID(device_name="Q1PDR", property="set_current")
        )
    )

def test_translation_service_as_issued_by_command_test():
    _, tm = build_managers()

    # make selection to simplify searching for the cause
    d = {
        key: item for key, item in tm.lut.items() if key.lattice_property_id.element_name in ["S4M1D1R", "HS4M1D1R"]
     }
    r = tm.get(
        ConversionID(
            lattice_property_id=LatticeElementPropertyID(element_name='S4M1D1R', property='x_kick'),
            device_property_id=DevicePropertyID(device_name='HS4P1D1R', property='set_current')
        )
    )

