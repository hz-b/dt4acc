import pytest
from pathlib import Path
import os.path
import sys

class pydev(object):
    """Make pydev testable with no functionallity
    """
    @staticmethod
    def iointr(param, value=None):
      pass
sys.modules["pydev"]= pydev

from python import accelerator

prefix = "Waheedullah:DT"

def test_set_multipoles_element():
    path = Path(os.path.dirname(__file__))
    filename = path /".."/ ".."/"lattices"/ "b2_stduser_beamports_blm_tracy_corr.lat"
    vacc = accelerator.build_virtual_accelerator(prefix=prefix, lattice_file_name=filename)
    element_name = "q1m1d1r"
    vacc.set_property_and_readback( element_name=element_name,
        element_index=0,
        method_names=['set_dx'],
        value=2,
        readback_method='get_dx',
        readback_label=f'{prefix}:{element_name}-get-multipole',
        twiss=False,
        orbit=False
    )


if __name__ == "__main__":
    test_set_multipoles_element()