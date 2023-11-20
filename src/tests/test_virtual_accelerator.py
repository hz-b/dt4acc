import pytest
import accelerator
prefix = "Waheedullah:DT"


def test_set_multipoles_element():
    vacc = accelerator.build_virtual_accelerator(prefix=prefix)
    element_name = "q1m1d1r"
    vacc.set_property_and_readback( element_name=element_name,
        element_index=0,
        method_names=['set_dx'],
        value=2,
        readback_method='get_dx',
        readback_label=f'{prefix}:{element_name}-get_dx',
        twiss=True,
    )
if __name__ == "__main__":
  class pydev(object):
    @staticmethod
    def iointr(param, value=None):
      pass
  # rest of your code