import yaml
import json
from bson import ObjectId

# classes considered magnets
MAGNET_CLASSES = {"Quadrupole", "Sextupole", "Multipole", "Bend", "RFCavity"}

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

        # skip non-magnets or entries lacking a name
        if cls not in MAGNET_CLASSES or not name:
            continue

        # base magnet (as in your original script)
        base_obj = {
            "_id": {"$oid": str(ObjectId())},
            "uuid": uuid,                     # YAML entry key
            "type": cls,
            "FamName": fam_name,             # FamName copied
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

    with open(OUTPUT_JSON, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Generated {len(output)} magnet entries in {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
