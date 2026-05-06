import yaml
import json
from bson import ObjectId

# classes considered magnets
MAGNET_CLASSES = {"Quadrupole", "Sextupole", "Multipole", "Bend", "RFCavity", "Octupole"}
BPM_CLASSES = {"Monitor"}  # covers both BPM and FBPM — FamName distinguished by uuid prefix

INPUT_YAML = "SOLEIL_II_V3635_STAB_SYM1_SB3_MULT7_4SX60_V001.yaml"
OUTPUT_JSON = "accelerator_setup.json"


def main():
    with open(INPUT_YAML, "r") as f:
        db = yaml.safe_load(f)

    output = []

    for uuid, entry in db.items():
        lattice = entry.get("Lattice", {})
        nomenclature = entry.get("Nomenclature", {})
        localisation = entry.get("Localisation", {})

        cls = lattice.get("Class")
        fam_name = lattice.get("FamName")
        name = nomenclature.get("TANGO")

        if not name:
            continue

        # --- BPMs ---
        if cls in BPM_CLASSES:
            output.append({
                "_id": {"$oid": str(ObjectId())},
                "uuid": uuid,
                "type": "BPM",
                "FamName": fam_name,
                "name": name,
                "s_pos": localisation.get("S_pos", 0.0),
            })
            continue

        # skip non-magnets
        if cls not in MAGNET_CLASSES:
            continue

        # base magnet (as in your original script)
        base_obj = {
            "_id": {"$oid": str(ObjectId())},
            "uuid": uuid,
            "type": cls,
            "FamName": fam_name,
            "name": name,
            "magnetic_strength": 1.0,
            "pc": f"{name}-pc",
            "k": 1.0
        }
        output.append(base_obj)

        # --- Extra steerers for Sextupoles with TANGO_2ND/3RD ---
        if cls == "Sextupole":
            tango_2nd = nomenclature.get("TANGO_2ND")
            tango_3rd = nomenclature.get("TANGO_3RD")

            # if TANGO_2ND exists -> create Steerer
            if tango_2nd:
                steerer_2nd = {
                    "_id": {"$oid": str(ObjectId())},
                    "uuid": uuid,             # same YAML entry
                    "type": "Steerer",
                    "FamName": fam_name,      # same FamName
                    "name": tango_2nd,
                    "magnetic_strength": 1.0,
                    "pc": f"{tango_2nd}-pc",
                                    "k": 1.0
                }
                output.append(steerer_2nd)

            # if TANGO_3RD exists -> create Steerer
            if tango_3rd:
                steerer_3rd = {
                    "_id": {"$oid": str(ObjectId())},
                    "uuid": uuid,             # same YAML entry
                    "type": "Steerer",
                    "FamName": fam_name,      # same FamName
                    "name": tango_3rd,
                    "magnetic_strength": 1.0,
                    "pc": f"{tango_3rd}-pc",
                                    "k": 1.0
                }
                output.append(steerer_3rd)

        # --- Skew quadrupole correctors for Octupoles with TANGO_2ND/3RD ---
        # CQLN → slow normal quadrupolar corrector → PolynomA[1] (skew quad)
        # CQLT → slow turned quadrupolar corrector → PolynomB[1] (normal quad)
        # Both share the same UUID as the host octupole (same AT element)
        if cls == "Octupole":
            for tango_key in ("TANGO_2ND", "TANGO_3RD"):
                corr_name = nomenclature.get(tango_key)
                if not corr_name:
                    continue

                # Determine corrector type from the device name suffix
                # e.g. OH.02-CQLN.02 → CQLN, OH.01-CQLT.01 → CQLT
                if "CQLN" in corr_name:
                    corr_type = "CQLN"
                elif "CQLT" in corr_name:
                    corr_type = "CQLT"
                else:
                    # Unknown corrector type — skip with a warning
                    import sys
                    print(f"WARNING: unknown corrector type in {corr_name!r} — skipping", file=sys.stderr)
                    continue

                corr_obj = {
                    "_id": {"$oid": str(ObjectId())},
                    "uuid": f"{corr_type}:{uuid}",  # e.g. "CQLN:OH2_QCORROCT_2_001"
                    "type": "SkewQuadrupole",
                    "corrector_type": corr_type,   # "CQLN" or "CQLT"
                    "FamName": fam_name,      # same FamName as host octupole
                    "name": corr_name,
                    "magnetic_strength": 0.0,
                    "pc": f"{corr_name}-pc",
                                    "k": 0.0
                }
                output.append(corr_obj)

    with open(OUTPUT_JSON, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Generated {len(output)} magnet entries in {OUTPUT_JSON}")


if __name__ == "__main__":
    main()