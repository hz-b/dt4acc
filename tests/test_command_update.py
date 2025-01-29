import asyncio
import pytest

from src.dt4acc.core.accelerators.element_proxies import estimate_shift
from src.dt4acc.core.command import update_manager, acc


# pytest_plugins = ('pytest_asyncio',)


@pytest.mark.asyncio(scope="session")
async def test_update_quadrupole_x():
    device_id = "Q5M2T5R"
    for val in [-1e-4, 2e-4, 0]:
        await update_manager.update(device_id=device_id, property_name="x", value=val)
        # check that the result arrived
        # todo: reading  interaction should be improved
        proxy = await acc.acc_mgr.get_element(device_id)
        element, = proxy._obj
        shift =  estimate_shift(element)
        assert shift[0] == pytest.approx(-val, abs=1e-6)
        assert shift[2] == pytest.approx(0.0, abs=1e-6)

@pytest.mark.asyncio(scope="session")
async def test_update_quadrupole_y():

    device_id = "Q1M1D1R"
    for val in [-1e-4, 2e-4, 0]:
        await update_manager.update(device_id=device_id, property_name="y", value=val)
        # check that the result arrived
        # todo: reading  interaction should be improved
        proxy = await acc.acc_mgr.get_element(device_id)
        element, = proxy._obj
        shift =  estimate_shift(element)
        assert shift[0] == pytest.approx(0.0, abs=1e-6)
        assert shift[2] == pytest.approx(-val, abs=1e-6)


@pytest.mark.asyncio(scope="session")
async def test_update_steerer_pc_current():
    acc
    device_id = "HS4P1D1R"
    lattice_id = device_id[1:].replace("P", "M")

    for val in [5e-3, -7e-3, 0]:
        await update_manager.update(device_id=device_id, property_name="set_current", value=val)

        # check that the result arrived
        # todo: reading  interaction should be improved
        lattice_id = device_id[1:].replace("P", "M")
        proxy = await acc.acc_mgr.get_element(lattice_id)
        element, = proxy._obj
        x_kick, y_kick = element.KickAngle
        
        if val != pytest.approx(0, abs=1e-3):
            assert x_kick != pytest.approx(0, abs=1e-3)
        else:
            assert x_kick == pytest.approx(0, abs=1e-3)
        assert y_kick == pytest.approx(0, abs=1e-6)


@pytest.mark.asyncio(scope="session")
async def test_update_master_clock():
    device_id = "MCLKHX251C"
    frequency = 500e6
    with pytest.raises(AssertionError):
        await update_manager.update(device_id=device_id, property_name="reference_frequency", value=frequency)
