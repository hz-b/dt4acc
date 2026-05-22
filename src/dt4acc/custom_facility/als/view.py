from typing import Dict, Tuple

from dt4acc.custom_epics.ioc.view import View
from dt4acc.custom_facility.maxiv.liasion_translator_setup import TranslatorService
from dt4acc_lib.interfaces.utils.liaison_manager import LiaisonManagerBase
from dt4acc_lib.interfaces.utils.state_conversion import StateConversion
from dt4acc_lib.model.utils.command import ReadCommand
from dt4acc_lib.model.utils.identifiers import DevicePropertyID, ConversionID


class ALSView(View):
    def __init__(self, *, lm: LiaisonManagerBase, ts: TranslatorService, **kwargs):
        super().__init__(**kwargs)
        self.lm = lm
        self.ts = ts

    def update_track(self, var: ReadCommand, pkg):
        super().update_track(var, pkg)
        self.update_bpms(pkg)

    # @functools.cached_property
    def bpm_converters(
        self,
    ) -> Dict[
        str,
        Tuple[
            Tuple[StateConversion, StateConversion],
            Tuple[StateConversion, StateConversion],
        ],
    ]:
        def get_converter(dev_id: str, prop: str) -> Tuple[str, StateConversion]:
            dev_prop = DevicePropertyID(dev_id, prop)
            (lat_prop,) = self.lm.inverse(dev_prop)
            to = self.ts.get(ConversionID(lat_prop, dev_prop))
            return lat_prop.element_name, to

        dict_for_x, dict_for_y = [
            {
                pv.id: get_converter(pv.id, prop)
                for pv in self.process_variables
                if hasattr(pv.id, "family") and pv.id.family == family
            }
            for family, prop in [("BPMx", "dx"), ("BPMy", "dy")]
        ]

        def check_and_extract(
            kvx, kvy
        ) -> Tuple[Tuple[str, StateConversion], Tuple[str, StateConversion]]:
            kx, tmpx = kvx
            ky, tmpy = kvy
            lat_elm_x, tx = tmpx
            lat_elm_y, ty = tmpy
            assert lat_elm_x == lat_elm_y
            assert kx.sector == ky.sector
            assert kx.child == ky.child
            return (kx, tx), (ky, ty)

        # keys must be the same
        r = {
            kvx[1][0]: check_and_extract(kvx, kvy)
            for kvx, kvy in zip(dict_for_x.items(), dict_for_y.items())
        }
        return r

    def update_bpms(self, pkg):
        converters = self.bpm_converters()

        (t_data,) = pkg.readings
        track = t_data.payload.track
        d = {pos.uid: pos for pos in track}
        for k, v in converters.items():
            pos = d[k]
            tmp_x, tmp_y = v
            id_x, to_x = tmp_x
            id_y, to_y = tmp_y
            rcmd_x = ReadCommand(id_x, "dx")
            rcmd_y = ReadCommand(id_y, "dy")
            rec_x = self.process_variables[rcmd_x]
            rec_y = self.process_variables[rcmd_y]
            vx = to_x.forward(pos.x)
            vy = to_y.forward(pos.x)
            rec_x.set(vx)
            rec_y.set(vy)
