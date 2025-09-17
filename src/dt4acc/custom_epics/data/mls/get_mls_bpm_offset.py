#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Extract BPM offsets from ao_mls.json and write bpm_offset.json.

It combines BPMx and BPMy:
  - bpm_name from CommonNames (shared between BPMx and BPMy)
  - offset_x from BPMx.Monitor.Offset[i]
  - offset_y from BPMy.Monitor.Offset[i]
Each entry gets a MongoDB-style _id with an ObjectId-like hex string.
"""

import json
import secrets

def gen_oid_hex() -> str:
    # Generate a 24-character hex string (like MongoDB ObjectId)
    return secrets.token_hex(12)

def main():
    with open("ao_mls.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    bpmx = data.get("BPMx", {})
    bpmy = data.get("BPMy", {})

    names_x   = bpmx.get("CommonNames", [])
    offsets_x = (bpmx.get("Monitor") or {}).get("Offset", [])
    offsets_y = (bpmy.get("Monitor") or {}).get("Offset", [])

    results = []
    count = min(len(names_x), len(offsets_x), len(offsets_y))
    for i in range(count):
        results.append({
            "_id": {"$oid": gen_oid_hex()},
            "bpm_name": names_x[i],
            "offset_x": offsets_x[i],
            "offset_y": offsets_y[i]
        })

    with open("bpm_offset.json", "w", encoding="utf-8") as out:
        json.dump(results, out, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
