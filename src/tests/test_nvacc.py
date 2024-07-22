"""

Todo:
    need to implement a reset before each command is started
    so that each test starts with the same accelerator setup

    All used values must be close to the real machine: then the
    following Twiss calculation will proceed

    Need to ensure that all delayed calculations run synchronous

"""
import pytest

from dt4acc.command import update, acc

# Demand synchronous execution for testing
acc.set_delay(None)


def test_update_quad_strength():
    update(element_id='Q1M1D1R', property_name='K', value=34344)


def test_update_quad_offset_hor():
    update(element_id='Q1M1D1R', property_name='dx', value=1e-5)


def test_update_quad_offset_vert():
    update(element_id='Q1M1D1R', property_name='dy', value=1e-5)

def test_update_quad_offset_vert():
    update(element_id='Q1M1D8R', property_name='dx', value=0.5e-4)

def test_update_horizontal_steerer():
    update(element_id='HS4M2D1R', property_name='K', value=1e-4)


@pytest.mark.skip
def test_update_roll():
    """
    Todo:
        check why this test fails calculating Twiss
    """

    update(element_id='Q1M1D1R', property_name='roll', value=0e0)
