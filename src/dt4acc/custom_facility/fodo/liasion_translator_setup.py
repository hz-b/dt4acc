import functools
from importlib.resources import files
from typing import Tuple

import jsons
import yaml

from dt4acc_lib.bl.liaison_manager import LiaisonManager
from dt4acc_lib.bl.translator_service import TranslatorService
from dt4acc_lib.bl.yellow_pages import YellowPages
from dt4acc_lib.interfaces.utils.liaison_manager import LiaisonManagerBase
from dt4acc_lib.interfaces.utils.translator_service import TranslatorServiceBase
from dt4acc_lib.interfaces.utils.yellow_pages import YellowPagesBase
from dt4acc_lib.model.utils.liaison_manager_lookup_table import (
    LiaisonManagerInverseLookupTable,
    LiaisonManagerForwardLookupTable,
)
from dt4acc_lib.model.utils.translator_manager_lookup_table import TranslatorLookupTable


@functools.lru_cache(maxsize=1)
def load_managers() -> (YellowPagesBase, LiaisonManagerBase, TranslatorServiceBase):
    return build_managers(("custom_facility", "fodo", "resources", "created"))


def build_managers(config_dir: Tuple[str]):
    obj = load_file(config_dir + ("fodo_yellow_pages_lookup_table.yml",))
    yp_lut = jsons.load(obj)
    yp = YellowPages(yp_lut)

    obj = load_file(config_dir + ("fodo_liaison_manager_forward_lookup_table.yml",))
    lm_fwd = jsons.load(obj, LiaisonManagerForwardLookupTable)
    obj = load_file(config_dir + ("fodo_liaison_manager_inverse_lookup_table.yml",))
    lm_inv = jsons.load(obj, LiaisonManagerInverseLookupTable)
    lm = LiaisonManager(forward_lut=lm_fwd, inverse_lut=lm_inv)

    obj = load_file(config_dir + ("fodo_translation_service_lookup_table.yml",))
    ts_lut = jsons.load(obj, TranslatorLookupTable)
    #: Todo: use correct brho for the FODO test lattice!
    ts = TranslatorService(lut=ts_lut, brho=5.4)
    return yp, lm, ts


def load_file(config_dir: Tuple[str]):
    t_file = files("dt4acc").joinpath(*(config_dir))
    with open(t_file, "rt") as fp:
        obj = yaml.load(fp, yaml.Loader)
    return obj
