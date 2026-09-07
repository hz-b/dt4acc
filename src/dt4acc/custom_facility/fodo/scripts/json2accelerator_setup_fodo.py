"""
json2accelerator_setup_fodo.py
===============================
Generate accelerator_setup.json for the FODO test facility.

Reads the AT-format lattice description in
  custom_facility/fodo/resources/fodo_lattice.json
and writes the magnet database consumed by custom_epics
(same schema as custom_epics/data/standard/accelerator_setup.json) to
  custom_epics/data/fodo/accelerator_setup.json

Output schema per entry (matches the "standard" facility):
  {
    "_id": {"$oid": "..."},
    "type": "Quadrupole" | "Sextupole" | "Steerer",
    "name": "<magnet name>",
    "magnetic_strength": <float>,
    "pc": "<power converter name>",
    "k": <float or null>,
  }

Only Quadrupole/Sextupole/Multipole lattice elements become magnet-DB
entries — Drift, Bend, RFCavity and Monitor elements are not driven by
a power converter in this schema and are skipped, mirroring the
"standard" accelerator_setup.json which also excludes them.

Each AT "Multipole" lattice element (a single combined-function thin
corrector magnet, one FamName such as "COR_001" carrying both a
horizontal and a vertical kick coefficient — PolynomB[0] and
PolynomA[0] of the *same* AT element) produces two Steerer entries,
the actual power-converter-driven correctors, one per plane:
  PolynomB[0] (normal, horizontal kick) -> Steerer "H<FamName>"
  PolynomA[0] (skew, vertical kick)     -> Steerer "V<FamName>"
There is no separate accelerator_setup.json entry for the Multipole
magnet itself — unlike a quadrupole or sextupole it has no power
converter of its own; it only exists as the host AT lattice element
that both steerers act on (see horizontal_steerers_host /
vertical_steerers_host in the yellow pages, and how the liaison
manager maps both planes' lattice property back to this same host
element name).
"""

import json
from pathlib import Path

from bson import ObjectId

LAT_FILE = Path(__file__).resolve().parent.parent / "resources" / "fodo_lattice.json"
OUTPUT_FILE = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "custom_epics"
    / "data"
    / "fodo"
    / "accelerator_setup.json"
)


def oid():
    return {"$oid": str(ObjectId())}


def make_entry(elem_type, name, magnetic_strength, pc, k):
    return {
        "_id": oid(),
        "type": elem_type,
        "name": name,
        "magnetic_strength": magnetic_strength,
        "pc": pc,
        "k": k,
    }


def generate(lattice):
    out = []

    for elem in lattice["elements"]:
        cls = elem.get("Class")
        fam_name = elem["FamName"]

        if cls == "Quadrupole":
            k = elem.get("K", elem["PolynomB"][1])
            out.append(make_entry("Quadrupole", fam_name, k, f"{fam_name}_PC", k))

        elif cls == "Sextupole":
            k = elem["PolynomB"][2]
            out.append(make_entry("Sextupole", fam_name, k, f"{fam_name}_PC", k))

        elif cls == "Multipole":
            h_name = f"H{fam_name}"
            v_name = f"V{fam_name}"
            h_strength = elem["PolynomB"][0]
            v_strength = elem["PolynomA"][0]
            out.append(make_entry("Steerer", h_name, h_strength, f"{h_name}_PC", None))
            out.append(make_entry("Steerer", v_name, v_strength, f"{v_name}_PC", None))

        # Drift, Bend, RFCavity, Monitor: no power converter -> skipped

    return out


def main():
    with LAT_FILE.open() as f:
        lattice = json.load(f)

    output = generate(lattice)

    by_type = {}
    for e in output:
        by_type[e["type"]] = by_type.get(e["type"], 0) + 1

    print(f"Loaded {len(lattice['elements'])} lattice elements from {LAT_FILE}")
    print(f"Generated {len(output)} magnet-DB entries:")
    for t, n in sorted(by_type.items()):
        print(f"  {t:12s}: {n}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w") as f:
        json.dump(output, f, indent=2)
    print(f"\nWritten to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
