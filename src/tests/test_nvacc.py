import pytest

from dt4acc.command import update


def test_update_simple():
    update(element_id='Q1M1D1R', property_name='dx', value=0.5e-3)


def test_update_quad_strength():
    update(element_id='Q1M1D1R', property_name='K', value=2.445)

@pytest.mark.skip
def test_update_horizontal_steerer():
    update(element_id='Q1M1D1R', property_name='K', value=1.2)

def test_update_roll():
    update(element_id='Q1M1D1R', property_name='roll', value=0e0)