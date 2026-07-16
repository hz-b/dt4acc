from __future__ import annotations

from dt4acc_lib.bl.liaison_manager import LiaisonManager
from dt4acc_lib.bl.yellow_pages import YellowPages
from dt4acc_lib.bl.translator_service import TranslatorService
from dt4acc.custom_facility.als.read_lattice import als_get_lattice, default_energy
from dt4acc.custom_facility.als.readin_ao import als_ring_ao_data, load_ramp_data
from dt4acc_lib.bl.unit_conversion import calculate_brho

from .config import als_bootstrap_config
from .liaison_builder import create_liaison_lut
from .translator_builder import create_translator_luts
from .yellow_pages_builder import create_yellow_pages_input


def load_managers(lat=None):
    """Bootstrap the ALS managers used by dt4acc."""
    if lat is None:
        lat = als_get_lattice()
    ao_model = als_ring_ao_data()
    ramp_data = load_ramp_data(ao_model)
    config = als_bootstrap_config()

    yp = YellowPages(create_yellow_pages_input(ao_model, lat, config))
    fwd_lut, inv_lut, process_variable_views, mappings = create_liaison_lut(yp, ao_model, lat)
    lm = LiaisonManager(forward_lut=fwd_lut, inverse_lut=inv_lut)
    ts_lut = create_translator_luts(yp, lm, ao_model, ramp_data, lat, mappings=mappings, reference_energy=default_energy)
    ts = TranslatorService(lut=ts_lut, brho=calculate_brho(default_energy))
    return yp, lm, ts, process_variable_views
