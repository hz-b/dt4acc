from bact_twin_architecture.data_model.identifiers import ConversionID, DevicePropertyID, LatticeElementPropertyID

from src.dt4acc.custom_epics.ioc.liasion_translation_manager import build_managers


def test_liasion_service():
    lm, _ = build_managers()

    device_name = "HS4P2D1R"
    r, = lm.inverse(DevicePropertyID(device_name=device_name, property="set_current"))
    assert r.property == "x_kick"
    assert r.element_name == device_name.replace("P", "M")

    device_name = "VS2P2D1R"
    r, = lm.inverse(DevicePropertyID(device_name=device_name, property="set_current"))
    assert r.property == "y_kick"
    assert r.element_name == device_name.replace("P", "M")


    device_name = "S4PD1R"
    # warning: no warrenty which one is first
    down_stream, up_stream = lm.inverse(DevicePropertyID(device_name=device_name, property="set_current"))
    r = up_stream
    assert r.property == "K"
    assert r.element_name == device_name[:2] + "M1" + device_name[3:]
    r = down_stream
    assert r.property == "K"
    assert r.element_name == device_name[:2] + "M2" + device_name[3:]
