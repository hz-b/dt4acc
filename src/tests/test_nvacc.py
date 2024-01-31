import pytest
import pydev

from src.dt4acc.command import update


def test_update_simple():
    update(element_id='q1m1d1r', property_name='dx', value=0.5e-3)
