"""
json2accelerator_setup_maxiv_r1.py
===================================
Generate accelerator_setup.json for MAX IV R1.

Output schema per entry:
  {
    "_id": {"$oid": "..."},
    "name": "<magnet TRL>",          # from CommonNames or curves keys
    "pc":   "<PC TRL>",              # from DeviceName
    "type": "Multipole|Steerer|SkewQuadrupole|RFCavity",
    "subtype": "Quad|Sext|Bend|H|V",
    "uuids": ["sqfi73", "sqfi74", ...],  # FamNames of AT elements
    "magnetic_strength": <float>,
    "curves": [{"curve":[...],"harmonic":{"number":N}},...],
  }

UUID = FamName of each AT element (the trailing number in FamName == ElemIndex).
For single-element devices uuids has one entry; for multi-element groups it has N.

Curve matching rules (CommonName → curves key):
  Direct match       : SQFI, HCM(CRCOX), VCM(CRCOY), SXCI(CRSXCI), SXCO(CRSXCO)
  Strip CR prefix    : CRSXCI→SXCI, CRSXCO→SXCO (already direct in curves)
  Strip CRC + suffix : CRDIPC→DIP  (BEND)
  From curves keys   : SQFO, SXDI, SXDO (names come directly from sorted curves keys)
"""

import json, re, uuid as _uuid
from pathlib import Path
from collections import defaultdict

LAT_FILE    = Path("R1_lat_indexed.json")
AO_FILE     = Path("ao_R1_with_lattice_index.json")
CURVES_FILE = Path("maxiv_r1_excitation_curves.json")
OUTPUT_FILE = Path("accelerator_setup_maxiv_r1.json")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def oid():
    return {"$oid": _uuid.uuid4().hex[:24]}

def as_list(v):
    return [v] if isinstance(v, str) else (v if isinstance(v, list) else [])

def build_famnum_index(elements):
    """trailing int in FamName → element. Prefer Multipole/Corrector over Drift."""
    priority = {"Multipole":3,"Corrector":2,"RFCavity":2,"Drift":0,"Marker":0}
    result = {}
    for e in elements:
        m = re.search(r'(\d+)$', e["FamName"])
        if not m: continue
        num = int(m.group(1))
        existing = result.get(num)
        if existing is None or priority.get(e.get("Class"),0) > priority.get(existing.get("Class"),0):
            result[num] = e
    return result

def unique_elem_indices(ao_family):
    """Unique ElemIndex values from ATParameterGroup in appearance order."""
    grp = ao_family.get("AT",{}).get("ATParameterGroup",[])
    if not grp: return []
    flat = [g for sub in grp for g in sub] if isinstance(grp[0],list) else grp
    seen, result = set(), []
    for g in flat:
        if isinstance(g,dict):
            idx = g.get("ElemIndex")
            if idx is not None and idx not in seen:
                seen.add(idx); result.append(idx)
    return result

def group_per_device(ao_family):
    """List of ElemIndex-lists, one per device."""
    grp = ao_family.get("AT",{}).get("ATParameterGroup",[])
    if not grp: return []
    if isinstance(grp[0],list):
        groups = []
        for sub in grp:
            idxs = sorted({g["ElemIndex"] for g in sub if isinstance(g,dict)})
            if idxs: groups.append(idxs)
        return groups
    idxs = sorted({g["ElemIndex"] for g in grp if isinstance(g,dict)})
    return [idxs] if idxs else []

def get_saved_value(ao_family, elem_index, field_index=1):
    """PolynomB[field_index] SavedValue from ATParameterGroup."""
    grp = ao_family.get("AT",{}).get("ATParameterGroup",[])
    if not grp: return 1.0
    flat = [g for sub in grp for g in sub] if isinstance(grp[0],list) else grp
    for g in flat:
        if not isinstance(g,dict): continue
        if g.get("ElemIndex")==elem_index and g.get("FieldIndex")==[field_index]:
            sv = g.get("SavedValue")
            if isinstance(sv,list) and len(sv)>field_index: return sv[field_index]
            if isinstance(sv,(int,float)): return sv
    return 1.0

def find_curves(mag_name, curves_db):
    """
    Find curves list for a magnet by its TRL name.
    Tries direct match, then strips CR prefix from the type token.
    Returns [] if no match found.
    """
    if mag_name in curves_db:
        return curves_db[mag_name].get("curves", [])
    # Strip CR prefix: /MAG/CRSXCI-01 → /MAG/SXCI-01
    stripped = re.sub(r'/MAG/CR([A-Z]+)-', r'/MAG/\1-', mag_name)
    if stripped in curves_db:
        return curves_db[stripped].get("curves", [])
    # Strip CR + trailing C: /MAG/CRDIPC-01 → /MAG/DIP-01
    stripped2 = re.sub(r'/MAG/CR([A-Z]+)C-', r'/MAG/\1-', mag_name)
    if stripped2 in curves_db:
        return curves_db[stripped2].get("curves", [])
    return []

def famnames_from_indices(elem_indices, famnum):
    """Convert list of ElemIndex ints to list of FamName strings."""
    return [famnum.get(i, {}).get("FamName", str(i)) for i in elem_indices]

def curves_keys_matching(curves_db, pattern):
    """Sorted curve keys containing pattern."""
    return sorted(k for k in curves_db if pattern in k)

def total_length(uuids, famnum):
    """Sum of AT element lengths for a list of FamName UUIDs."""
    total = 0.0
    for uuid in uuids:
        m = re.search(r'(\d+)$', uuid)
        if m:
            total += famnum.get(int(m.group(1)), {}).get("Length", 0.0)
    return round(total, 6)

def make_entry(mag_name, pc_name, elem_type, subtype, uuids, ms, curves_list, famnum=None):
    entry = {
        "_id": oid(),
        "name": mag_name,
        "pc": pc_name,
        "type": elem_type,
        "subtype": subtype,
        "uuids": uuids,
        "magnetic_strength": ms,
        "curves": curves_list,
    }
    if famnum is not None:
        entry["length"] = total_length(uuids, famnum)
    return entry


# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------

def generate(lat, ao, curves_db):
    ao_family_common = {k: as_list(ao[k].get("CommonNames",[])) for k in ao}
    famnum = build_famnum_index(lat["elements"])
    out = []

    # ------------------------------------------------------------------
    # 1. SQFI — 12 magnets (one per sector), each driving 4 AT elements
    #    Single PC for all. Individual names from curves: R1-1xx/MAG/SQFI-01
    # ------------------------------------------------------------------
    fam = ao["SQFI"]
    pc = as_list(fam["DeviceName"])[0]
    all_idx = unique_elem_indices(fam)    # 108 total (27 devices × 4 elem)
    per_dev = 4
    sqfi_mag_names = curves_keys_matching(curves_db, "/MAG/SQFI")  # 12 entries

    for i, mag in enumerate(sqfi_mag_names):
        chunk = all_idx[i*per_dev:(i+1)*per_dev]
        if not chunk: continue
        uuids = famnames_from_indices(chunk, famnum)
        ms = get_saved_value(fam, chunk[0], 1)
        out.append(make_entry(mag, pc, "Multipole", "Quad", uuids, ms,
                              find_curves(mag, curves_db), famnum))

    # ------------------------------------------------------------------
    # 2. SQFO — 6 PCs, each driving 3 AT elements (2 per sector × 12 sectors = 24 curves)
    #    curves has 24 SQFO entries (2 per sector), ao has 6 devices.
    #    Each ao device covers 2 sectors (4 curves each) via DeviceList grouping.
    #    Simplest: pair each device with the 4 curve entries for its sectors.
    #    DeviceList: [[1,1],[7,1],[8,1],[10,1],[11,1],[12,1]] → sector numbers
    # ------------------------------------------------------------------
    fam = ao["SQFO"]
    pc_names = as_list(fam["DeviceName"])
    device_list = fam.get("DeviceList", [])
    all_idx = unique_elem_indices(fam)      # 18 total (6 devices × 3 elem)
    sqfo_curves_keys = curves_keys_matching(curves_db, "/MAG/SQFO")  # 24 entries

    per_dev = 3
    for i, (pc, cn, dl) in enumerate(zip(pc_names, ao_family_common["SQFO"], device_list)):
        chunk = all_idx[i*per_dev:(i+1)*per_dev]
        if not chunk: continue
        uuids = famnames_from_indices(chunk, famnum)
        ms = get_saved_value(fam, chunk[0], 1)
        # Derive sector number from CommonName: "R1-1/..." → 101, "R1-107S/..." → 107
        m = re.search(r'R1-(\d+)', cn)
        sector = int(m.group(1)) if m else 0
        if sector < 100: sector = sector * 100 + 1  # "R1-1" → sector 101
        sector_str = f"R1-{sector:d}/MAG/SQFO"
        sector_curve_keys = [k for k in sqfo_curves_keys if sector_str in k]
        # Each SQFO device drives 2 magnets per sector (SQFO-01, SQFO-02)
        # Name it after the first curve key in the sector, or CommonName as fallback
        mag_name = sector_curve_keys[0] if sector_curve_keys else cn
        combined_curves = []
        for ck in sector_curve_keys:
            combined_curves += curves_db[ck].get("curves", [])
        out.append(make_entry(mag_name, pc, "Multipole", "Quad", uuids, ms,
                              combined_curves))

    # ------------------------------------------------------------------
    # 3. SXDI / SXDO — single PC, 2 magnets per sector × 12 sectors = 24 each
    #    Individual names come directly from curves keys
    # ------------------------------------------------------------------
    for fam_key, curve_pat in [("SXDI", "/MAG/SXDI"), ("SXDO", "/MAG/SXDO")]:
        fam = ao[fam_key]
        pc = as_list(fam["DeviceName"])[0]
        groups = group_per_device(fam)      # one group per magnet
        mag_names = curves_keys_matching(curves_db, curve_pat)

        for idxs, mag in zip(groups, mag_names):
            uuids = famnames_from_indices(idxs, famnum)
            ms = get_saved_value(fam, idxs[0], 2)
            out.append(make_entry(mag, pc, "Multipole", "Sext", uuids, ms,
                                  find_curves(mag, curves_db), famnum))

    # ------------------------------------------------------------------
    # 4. SXCI / SXCO — multiple PCs, CommonNames = magnet TRLs (with CR prefix)
    #    Curve keys use both CR and non-CR variants — try both
    # ------------------------------------------------------------------
    for fam_key in ["SXCI", "SXCO"]:
        fam = ao[fam_key]
        pc_names = as_list(fam["DeviceName"])
        mag_names = as_list(fam["CommonNames"])
        groups = group_per_device(fam)

        for idxs, pc, mag in zip(groups, pc_names, mag_names):
            uuids = famnames_from_indices(idxs, famnum)
            ms = get_saved_value(fam, idxs[0], 2)
            out.append(make_entry(mag, pc, "Multipole", "Sext", uuids, ms,
                                  find_curves(mag, curves_db), famnum))

    # ------------------------------------------------------------------
    # 5. BEND — dipole magnets, CommonNames = magnet TRLs (CRDIPC → DIP in curves)
    # ------------------------------------------------------------------
    fam = ao["BEND"]
    pc_names = as_list(fam["DeviceName"])
    mag_names = as_list(fam["CommonNames"])
    groups = group_per_device(fam)

    for idxs, pc, mag in zip(groups, pc_names, mag_names):
        uuids = famnames_from_indices(idxs, famnum)
        ms = get_saved_value(fam, idxs[0], 0)
        out.append(make_entry(mag, pc, "Multipole", "Bend", uuids, ms,
                              find_curves(mag, curves_db), famnum))

    # ------------------------------------------------------------------
    # 6. HCM / COFX — horizontal steerers (single-element, uuid is one FamName)
    # ------------------------------------------------------------------
    for fam_key in ["HCM", "COFX"]:
        fam = ao[fam_key]
        pc_names = as_list(fam["DeviceName"])
        mag_names = as_list(fam["CommonNames"])
        at_list = fam.get("AT",{}).get("ATIndex",[])
        if isinstance(at_list, int): at_list = [at_list]

        for pc, mag, eidx in zip(pc_names, mag_names, at_list):
            e = famnum.get(eidx, {})
            fam_name = e.get("FamName", f"hcm{eidx}")
            out.append(make_entry(mag, pc, "Steerer", "H", [fam_name], 0.0,
                                  find_curves(mag, curves_db), famnum))

    # ------------------------------------------------------------------
    # 7. VCM / COFY — vertical steerers
    # ------------------------------------------------------------------
    for fam_key in ["VCM", "COFY"]:
        fam = ao[fam_key]
        pc_names = as_list(fam["DeviceName"])
        mag_names = as_list(fam["CommonNames"])
        at_list = fam.get("AT",{}).get("ATIndex",[])
        if isinstance(at_list, int): at_list = [at_list]

        for pc, mag, eidx in zip(pc_names, mag_names, at_list):
            e = famnum.get(eidx, {})
            fam_name = e.get("FamName", f"vcm{eidx}")
            out.append(make_entry(mag, pc, "Steerer", "V", [fam_name], 0.0,
                                  find_curves(mag, curves_db), famnum))

    # ------------------------------------------------------------------
    # 8. SXCISKW — skew sextupoles on SXCI elements (PolynomA[2])
    #    Single PC for all 12 inner skew quads.
    #    Individual names derived as CRSXCI-01 → CRSKWI-01 to avoid
    #    collision with the SXCI magnet names.
    # ------------------------------------------------------------------
    fam = ao.get("SXCISKW", {})
    pc = as_list(fam.get("DeviceName", []))[0] if fam.get("DeviceName") else "unknown"
    sxci_groups = group_per_device(ao.get("SXCI", {}))
    sxci_mags = as_list(ao.get("SXCI", {}).get("CommonNames", []))

    for sxci_idxs, sxci_mag in zip(sxci_groups, sxci_mags):
        uuids = famnames_from_indices(sxci_idxs, famnum)
        # Derive unique name: "R1-101/MAG/CRSXCI-01" → "R1-101/MAG/CRSKWI-01"
        skw_mag = sxci_mag.replace("CRSXCI", "CRSKWI")
        out.append(make_entry(skw_mag, pc, "SkewQuadrupole", "SkewSext",
                              uuids, 0.0, [], famnum))

    # ------------------------------------------------------------------
    # 9. SXCOSKW — skew sextupoles on SXCO (PolynomA[2])
    # ------------------------------------------------------------------
    fam = ao.get("SXCOSKW", {})
    pc_names = as_list(fam.get("DeviceName", []))
    mag_names = as_list(fam.get("CommonNames", []))
    groups = group_per_device(fam)

    for idxs, pc, mag in zip(groups, pc_names, mag_names):
        uuids = famnames_from_indices(idxs, famnum)
        out.append(make_entry(mag, pc, "SkewQuadrupole", "SkewSext",
                              uuids, 0.0, [], famnum))

    # ------------------------------------------------------------------
    # 10. CAVITY — RF cavities
    # ------------------------------------------------------------------
    fam = ao.get("CAVITY", {})
    pc_names = as_list(fam.get("DeviceName", []))
    mag_names = as_list(fam.get("CommonNames", []))
    at_idx = fam.get("AT", {}).get("ATIndex")
    if isinstance(at_idx, int): at_idx = [at_idx] * len(pc_names)
    elif at_idx is None: at_idx = [None] * len(pc_names)

    seen = set()
    for pc, mag, eidx in zip(pc_names, mag_names, at_idx):
        if pc in seen: continue
        seen.add(pc)
        e = famnum.get(eidx, {}) if eidx else {}
        fam_name = e.get("FamName", f"cav{eidx}" if eidx else "RF")
        out.append(make_entry(mag, pc, "RFCavity", "", [fam_name], 1.0, [], famnum))

    return out


def main():
    print("Loading...")
    with LAT_FILE.open() as f: lat = json.load(f)
    with AO_FILE.open() as f: ao = json.load(f)
    with CURVES_FILE.open() as f: curves_db = json.load(f)

    output = generate(lat, ao, curves_db)

    by_type = defaultdict(int)
    for e in output: by_type[e["type"]] += 1
    print(f"\nGenerated {len(output)} entries:")
    for t, n in sorted(by_type.items()):
        print(f"  {t:20s}: {n}")

    # Check curves coverage
    with_curves = sum(1 for e in output if e.get("curves"))
    print(f"\nEntries with curves: {with_curves}/{len(output)}")

    # Spot check first SQFI
    sqfi = next(e for e in output if e["type"]=="Multipole" and e["subtype"]=="Quad" and "sqfi" in e["uuids"][0])
    print(f"\nFirst SQFI:")
    print(f"  name   = {sqfi['name']}")
    print(f"  pc     = {sqfi['pc']}")
    print(f"  uuids  = {sqfi['uuids']}")
    print(f"  ms     = {sqfi['magnetic_strength']}")
    print(f"  curves = {len(sqfi['curves'])} harmonics")

    with OUTPUT_FILE.open("w") as f:
        json.dump(output, f, indent=2)
    print(f"\nWritten to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()