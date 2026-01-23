import json
import jsons

from dt4acc.core.model.bpm_description import BPMDescriptionCollection


def load_bpm_configuration_data(fp) -> BPMDescriptionCollection:
    """load bpm configuration from a json file

    If loading from a database: just use jsons directly
    """
    data = json.load(fp)
    r = jsons.load(data, BPMDescriptionCollection)
    return r
