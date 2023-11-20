import numpy as np
import logging
logger = logging.getLogger("dt4acc")

from python import accelerator

def move_quad_compensate_kick(vacc):
    element_name = "q1m1d1r"
    element = vacc.accelerator_facade.find_element(element_name, 0)

    # 0.1 mm
    dx = 0.1e-3

    idx = element.get_main_multipole_number()
    assert idx == 2
    muls = element.get_multipoles()
    # quadrupole strength
    k = muls.get_multipole(idx)
    b = k * dx
    new_b = muls.get_multipole(1) + b
    muls.set_multipole(1, new_b)

    chk_b = muls.get_multipole(1)
    eps = 1e-6
    if abs(chk_b - new_b) > eps:
        raise AssertionError(f"set dipole component {chk_b} does not match expected {new_b} within eps {eps}")

    element.set_dx(dx)

def init_acc_for_bba_test(*args, **kwargs):
    vacc = accelerator.build_virtual_accelerator(*args, **kwargs)
    move_quad_compensate_kick(vacc)
    return vacc
