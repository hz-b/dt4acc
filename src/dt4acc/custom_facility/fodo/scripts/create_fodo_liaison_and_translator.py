"""
create_fodo_liaison_and_translator.py
=======================================
Generate the liaison-manager (forward/inverse) and translation-service
lookup tables for the FODO test facility.

Mirrors build_liaison_manager_lut() / build_translator_manager_lut() in
  scripts/bessyii/create_managers_input.py
but simplified for FODO:
  * one power converter drives exactly one magnet (no grouping needed),
  * each corrector ("Multipole" lattice element) hosts its own H/V
    steerer pair directly (no co-wound-on-sextupole indirection),
  * there is no calibration-curve input (magnets.yaml / power_converters.yaml
    equivalent) for FODO, so every PC <-> magnet conversion is a plain
    identity mapping (coeffs [0.0, 1.0]). Replace with real curves once
    FODO gets actual calibration data.

Run after create_fodo_yellow_pages.py (this script loads the yellow
pages lookup table it produced) and after
json2accelerator_setup_fodo.py (this script loads the magnet DB it
produced).

Writes, next to fodo_yellow_pages_lookup_table.yml:
  fodo_liaison_manager_forward_lookup_table.yml
  fodo_liaison_manager_inverse_lookup_table.yml
  fodo_translation_service_lookup_table.yml
"""

import datetime
import json
import pprint
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

import jsons
import yaml

from dt4acc_lib.bl.yellow_pages import YellowPages
from dt4acc_lib.model.utils.identifiers import (
    ConversionID,
    DevicePropertyID,
    LatticeElementPropertyID,
)
from dt4acc_lib.model.utils.liaison_manager_lookup_table import (
    LiaisonManagerForwardLookupElement,
    LiaisonManagerForwardLookupTable,
    LiaisonManagerInverseLookupElement,
    LiaisonManagerInverseLookupTable,
)
from dt4acc_lib.model.utils.translator_manager_lookup_table import (
    IdentityMapper,
    PolynomCoefficients,
    TranslatorLookupTable,
    TranslatorLookupTableElement,
    TuneConversionCoefficients,
)

FODO_DIR = Path(__file__).resolve().parent.parent
ACCELERATOR_SETUP_FILE = (
    FODO_DIR.parent.parent / "custom_epics" / "data" / "fodo" / "accelerator_setup.json"
)
YP_FILE = FODO_DIR / "resources" / "created" / "fodo_yellow_pages_lookup_table.yml"
LM_FWD_FILE = FODO_DIR / "resources" / "created" / "fodo_liaison_manager_forward_lookup_table.yml"
LM_INV_FILE = FODO_DIR / "resources" / "created" / "fodo_liaison_manager_inverse_lookup_table.yml"
TS_FILE = FODO_DIR / "resources" / "created" / "fodo_translation_service_lookup_table.yml"


class CompressedSequenceDumper(yaml.SafeDumper):
    def represent_sequence(self, tag, seq, flow_style=None):
        flow = len(seq) <= 12
        return super().represent_sequence(tag, seq, flow_style=flow)


def build_liaison_manager_lut(magnets, yp: YellowPages):
    pc_of = {m["name"]: m["pc"] for m in magnets}

    inv_d = defaultdict(list)
    fwd_d = defaultdict(list)

    # --- quadrupoles / sextupoles: main_strength <-> PC set_current -----
    for family_name in ("quadrupoles", "sextupoles"):
        for name in yp.get(family_name):
            dev_name = pc_of[name]
            lat_p = LatticeElementPropertyID(element_name=name, property="main_strength")
            pc_dev_p = DevicePropertyID(device_name=dev_name, property="set_current")
            mag_dev_p = DevicePropertyID(device_name=name, property="main_strength")
            fwd_d[lat_p].append(pc_dev_p)
            inv_d[pc_dev_p].append(lat_p)
            inv_d[mag_dev_p].append(lat_p)
            inv_d[DevicePropertyID(device_name=dev_name, property="rdbk_current")].append(lat_p)
            inv_d[DevicePropertyID(device_name=name, property="main_strength_rdbk")].append(lat_p)

    lut_fwd = []
    lut_inv = []

    # --- steerers: B1 / A1 (PolynomB[0] / PolynomA[0]) <-> PC set_current -
    # host = the corrector lattice element the steerer's kick acts on.
    # AT's ThinMultipole uses the European multipole convention (dipole=1,
    # quadrupole=2, sextupole=3, ...), so the dipole/kick term at Python
    # index PolynomB[0]/PolynomA[0] is addressed as "B1"/"A1", not "B0"/"A0"
    # (index 0 isn't a valid European order at all) and not "x_kick"/
    # "y_kick" (which would instead go through the element's KickAngle
    # attribute, which our Multipole-class correctors don't carry).
    # dt4acc_lib's ElementProxyFactory now resolves B1/A1 straight onto
    # PolynomB[0]/PolynomA[0] (proxy_factory.py's multipole range was
    # widened from range(2, 20) to range(1, 20) to enable this).
    for family_name, host_family, lattice_property, co_wound_prefix in (
        ("horizontal_steerers", "horizontal_steerers_host", "B1", "H"),
        ("vertical_steerers", "vertical_steerers_host", "A1", "V"),
    ):
        for name, host in zip(yp.get(family_name), yp.get(host_family)):
            assert name[0] == co_wound_prefix
            assert name[1:] == host
            dev_name = pc_of[name]
            lat_p = LatticeElementPropertyID(element_name=host, property=lattice_property)
            pc_dev_p = DevicePropertyID(device_name=dev_name, property="set_current")
            mag_dev_p = DevicePropertyID(device_name=name, property="main_strength")
            fwd_d[lat_p].append(pc_dev_p)
            inv_d[pc_dev_p].append(lat_p)
            inv_d[mag_dev_p].append(lat_p)
            inv_d[DevicePropertyID(device_name=dev_name, property="rdbk_current")].append(lat_p)
            # Steerers also need main_strength_rdbk (pv_setup.py builds a
            # readback PV for every magnet type, quad/sext/steerer alike —
            # this was missing here even though quad/sext have it below).
            inv_d[DevicePropertyID(device_name=name, property="main_strength_rdbk")].append(lat_p)

    lut_fwd += [LiaisonManagerForwardLookupElement(lat_id=k, dev_ids=v) for k, v in fwd_d.items()]
    lut_inv += [LiaisonManagerInverseLookupElement(dev_id=k, lat_ids=v) for k, v in inv_d.items()]
    del fwd_d, inv_d

    # --- identity x/y bookkeeping on quadrupoles & sextupoles -----------
    for family in ("quadrupoles", "sextupoles"):
        for prop in ("x", "y"):
            lut_inv += [
                LiaisonManagerInverseLookupElement(
                    dev_id=DevicePropertyID(device_name=name, property=prop),
                    lat_ids=[LatticeElementPropertyID(element_name=name, property=prop)],
                )
                for name in yp.get(family)
            ]

    # --- cavities <-> master clock ---------------------------------------
    lut_inv.append(
        LiaisonManagerInverseLookupElement(
            dev_id=DevicePropertyID(device_name="master_clock", property="reference_frequency"),
            lat_ids=[
                LatticeElementPropertyID(element_name=cav, property="frequency")
                for cav in yp.get("cavities")
            ],
        )
    )
    lut_fwd += [
        LiaisonManagerForwardLookupElement(
            lat_id=LatticeElementPropertyID(element_name=cav, property="frequency"),
            dev_ids=[DevicePropertyID(device_name="master_clock", property="reference_frequency")],
        )
        for cav in yp.get("cavities")
    ]

    # --- generic virtual quantities (facility independent) ---------------
    lut_fwd.append(
        LiaisonManagerForwardLookupElement(
            lat_id=LatticeElementPropertyID(element_name="tune", property="transversal"),
            dev_ids=[
                DevicePropertyID(device_name="tune", property=prop)
                for prop in ("x", "y", "flq_x", "flq_y", "transversal", "transversal_frequency")
            ],
        )
    )
    lut_inv += [
        LiaisonManagerInverseLookupElement(
            dev_id=DevicePropertyID(device_name="tune", property=prop),
            lat_ids=[LatticeElementPropertyID(element_name="tune", property="transversal")],
        )
        for prop in ("x", "y", "flq_x", "flq_y", "transversal", "transversal_frequency")
    ]
    lut_inv.append(
        LiaisonManagerInverseLookupElement(
            dev_id=DevicePropertyID(device_name="orbit", property="pos"),
            lat_ids=[LatticeElementPropertyID(element_name="orbit", property="pos")],
        )
    )
    for name, prop in (("twiss", "parameters"), ("track", "pos"), ("survey", "s")):
        lut_inv.append(
            LiaisonManagerInverseLookupElement(
                dev_id=DevicePropertyID(device_name=name, property=prop),
                lat_ids=[LatticeElementPropertyID(element_name=name, property=prop)],
            )
        )
        lut_fwd.append(
            LiaisonManagerForwardLookupElement(
                lat_id=LatticeElementPropertyID(element_name=name, property=prop),
                dev_ids=[DevicePropertyID(device_name=name, property=prop)],
            )
        )

    return lut_fwd, lut_inv


def build_translator_manager_lut(magnets, yp: YellowPages, lm_inv: LiaisonManagerInverseLookupTable):
    lut = []

    for cavity_name in yp.get("cavities"):
        lut.append(
            TranslatorLookupTableElement(
                ConversionID(
                    lattice_property_id=LatticeElementPropertyID(element_name=cavity_name, property="frequency"),
                    device_property_id=DevicePropertyID(device_name="master_clock", property="reference_frequency"),
                ),
                PolynomCoefficients([0.0, 1.0], energy_dependent=False),
            )
        )

    pc_of = {m["name"]: m["pc"] for m in magnets}
    steerers = set(yp.get("steerers"))
    quadrupoles = set(yp.get("quadrupoles"))
    sextupoles = set(yp.get("sextupoles"))
    quad_sext_names = quadrupoles | sextupoles
    steerer_pcs = {pc_of[name] for name in steerers}
    quad_sext_pcs = {pc_of[name] for name in quad_sext_names}

    all_keys = list(lm_inv.keys())
    unhandled = []

    # No calibration curve for FODO yet -> identity, but flagged energy
    # dependent since a real PC-current-to-strength conversion would be.
    for dev_p in all_keys:
        if dev_p.device_name in steerer_pcs and dev_p.property in ("set_current", "rdbk_current"):
            for lat_p in lm_inv.get(dev_p):
                lut.append(
                    TranslatorLookupTableElement(
                        ConversionID(lat_p, dev_p),
                        PolynomCoefficients([0.0, 1.0], energy_dependent=True),
                    )
                )
        else:
            unhandled.append(dev_p)

    all_keys, unhandled = unhandled, []
    for dev_p in all_keys:
        if dev_p.device_name in quad_sext_pcs and dev_p.property in ("set_current", "rdbk_current"):
            for lat_p in lm_inv.get(dev_p):
                lut.append(
                    TranslatorLookupTableElement(
                        ConversionID(lat_p, dev_p),
                        PolynomCoefficients([0.0, 1.0], energy_dependent=True),
                    )
                )
        else:
            unhandled.append(dev_p)

    all_keys, unhandled = unhandled, []
    for dev_p in all_keys:
        if dev_p.property in ("x", "y") and dev_p.device_name in quad_sext_names:
            (lat_p,) = lm_inv.get(dev_p)
            lut.append(
                TranslatorLookupTableElement(
                    ConversionID(lat_p, dev_p),
                    PolynomCoefficients([0.0, 1.0], energy_dependent=False),
                )
            )
        else:
            unhandled.append(dev_p)

    all_keys, unhandled = unhandled, []
    for dev_p in all_keys:
        if dev_p.device_name in steerers and dev_p.property in ("main_strength", "main_strength_rdbk"):
            (lat_p,) = lm_inv.get(dev_p)
            assert lat_p.property in ("B1", "A1")
            lut.append(
                TranslatorLookupTableElement(
                    ConversionID(lat_p, dev_p),
                    PolynomCoefficients([0.0, 1.0], energy_dependent=False),
                )
            )
        else:
            unhandled.append(dev_p)

    all_keys, unhandled = unhandled, []
    for dev_p in all_keys:
        if dev_p.property in ("main_strength", "main_strength_rdbk") and dev_p.device_name in quad_sext_names:
            (lat_p,) = lm_inv.get(dev_p)
            lut.append(
                TranslatorLookupTableElement(
                    ConversionID(lat_p, dev_p),
                    PolynomCoefficients([0.0, 1.0], energy_dependent=False),
                )
            )
        else:
            unhandled.append(dev_p)

    # --- generic virtual quantities (facility independent) ---------------
    lat_p = LatticeElementPropertyID(element_name="tune", property="transversal")
    lut.extend(
        TranslatorLookupTableElement(
            ConversionID(lat_p, DevicePropertyID(device_name="tune", property=prop)),
            IdentityMapper(),
        )
        for prop in ("flq_x", "flq_y", "transversal")
    )
    floquet_to_frequency = 500e3 / 400.0
    lut.extend(
        TranslatorLookupTableElement(
            ConversionID(lat_p, DevicePropertyID(device_name="tune", property=prop)),
            TuneConversionCoefficients(PolynomCoefficients([0.0, floquet_to_frequency], energy_dependent=False)),
        )
        for prop in ("x", "y", "transversal_frequency")
    )
    lut.extend(
        TranslatorLookupTableElement(
            ConversionID(
                LatticeElementPropertyID(element_name=name, property=prop),
                DevicePropertyID(device_name=name, property=prop),
            ),
            IdentityMapper(),
        )
        for name, prop in (("twiss", "parameters"), ("track", "pos"), ("survey", "s"))
    )

    print("No translation objects for (expected: orbit, tune sub-properties already added directly):")
    pprint.pprint(unhandled)
    return lut


def dump_yaml(fname: Path, data_type: str, now, payload):
    header = (
        "# \n"
        f"# FODO {data_type}: {now}\n"
        "# WARNING: automatically generated data\n"
        "#          please check when it is updated if you edit it by hand!\n"
    )
    fname.parent.mkdir(parents=True, exist_ok=True)
    with fname.open("wt") as fp:
        fp.write(header)
        yaml.dump(payload, fp, Dumper=CompressedSequenceDumper)
        fp.write("# EOF\n")


def main():
    with ACCELERATOR_SETUP_FILE.open() as f:
        magnets = json.load(f)
    with YP_FILE.open() as f:
        yp_lut = yaml.safe_load(f)
    yp = YellowPages(yp_lut)

    lut_fwd_, lut_inv_ = build_liaison_manager_lut(magnets, yp)
    lut_fwd = LiaisonManagerForwardLookupTable(lut_fwd_)
    lut_inv = LiaisonManagerInverseLookupTable(lut_inv_)

    mismatched = lut_inv.non_unique_entries()
    if mismatched:
        print("Following inverse lut items look up can be misleading!")
        pprint.pprint(mismatched)
    mismatched = lut_fwd.non_unique_entries()
    if mismatched:
        print("Following forward lut items look up can be misleading!")
        pprint.pprint(mismatched)

    lut_fwd.verify()
    lut_inv.verify()

    now = datetime.datetime.now()
    dump_yaml(LM_INV_FILE, "Liaison manager inverse table", now, asdict(lut_inv))
    dump_yaml(LM_FWD_FILE, "Liaison manager forward table", now, asdict(lut_fwd))

    # reload to make sure what we wrote is actually consumable
    with LM_INV_FILE.open() as f:
        lmt_inv = jsons.load(yaml.safe_load(f), LiaisonManagerInverseLookupTable)
    lmt_inv.verify()
    with LM_FWD_FILE.open() as f:
        lmt_fwd = jsons.load(yaml.safe_load(f), LiaisonManagerForwardLookupTable)
    lmt_fwd.verify()

    tlut = TranslatorLookupTable(lut=build_translator_manager_lut(magnets, yp, lmt_inv))
    dump_yaml(TS_FILE, "Translation service table", now, asdict(tlut))

    with TS_FILE.open() as f:
        tlut_loaded = jsons.load(yaml.safe_load(f), TranslatorLookupTable)
    assert tlut == tlut_loaded
    tlut_loaded.verify()

    print(f"\nliaison manager forward entries : {len(lut_fwd.lut)}")
    print(f"liaison manager inverse entries : {len(lut_inv.lut)}")
    print(f"translator entries              : {len(tlut.lut)}")
    print(f"\nWritten to {LM_FWD_FILE}")
    print(f"Written to {LM_INV_FILE}")
    print(f"Written to {TS_FILE}")


if __name__ == "__main__":
    main()
