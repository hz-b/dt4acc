import itertools
import logging
import os
import sys

print(sys.version)
print(sys.executable)

import gtpsa
print(gtpsa)
import thor_scsi
print(thor_scsi)

from thor_scsi.factory import accelerator_from_config

from .accelerator_facade import AcceleratorFacade
from .virtual_accelerator import VirtualAccelerator

logger = logging.getLogger("thor-scsi-lib")

t_dir = os.path.join(os.environ["HOME"], "Nextcloud", "thor_scsi")
t_file = os.path.join(t_dir, "b3_tst.lat")

desc = gtpsa.desc(6, 2)
try:
    lattice_filename_default = os.environ["THOR_SCSI_LATTICE"]
except KeyError:
    lattice_filename_default = None

def build_virtual_accelerator(*, prefix, lattice_file_name=lattice_filename_default, cmd=None):
    """
    cmd: setup of commands to be run accelerator facade after setup is finished,
    but before startup calculations are run
    """
    if not lattice_file_name:
        if lattice_filename_default is None:
            raise ValueError("No filename was given nor a default is known")

    # build the thor scsi accelerator model.
    # i.e. the machinery doing the actual beam dynamics calculation
    print(f"Reading lattice file {lattice_file_name}")
    acc = accelerator_from_config(lattice_file_name)
    assert(acc is not None)
    #
    af = AcceleratorFacade(acc)
    # watches which commands / changes to the accelerator come in
    # if required executes additional calculations
    # e.g. if a steerer is changed closed orbit and
    # Twiss parameters are recalculated
    vacc = VirtualAccelerator(af, prefix=prefix)
    # some calculations to do at start up
    #
    cmd(acc)
    vacc.execute_calculations_at_startup()
    return vacc

def move_quad_compensate(acc):
    """
    Todo:
        find out where to put the function below
    """
    def compensate_quadrupole_offset_with_dipole_kick(quad):
        dy = quad.get_dy()
        assert quad.get_main_multipole_number() == 2
        muls = quad.get_multipoles()
        k = muls.get_multipole(2)
        b = k * dy * 1j
        bref = muls.get_multipole(1)
        new_b = bref + b
        muls.set_multipole(1, new_b)

        check = quad.get_multipoles().get_multipole(1).imag
        diff = abs(check - new_b.imag)
        if diff > 1e-12:
            raise AssertionError("Compensated dipole is not matching expectations"
                                 f"expecting {new_b.imag} found {check}: difference {diff}"
                                 )

    quad_name = "q3m2t8r"
    quad = acc.find(quad_name, 0)
    dy = 3e-4
    quad.set_dy(dy)
    compensate_quadrupole_offset_with_dipole_kick(quad)
