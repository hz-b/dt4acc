#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build bpm_config.json from ao_mls.json with MongoDB-style _id.

Each entry:
  {
    "_id": {"$oid": "<24-hex>"},
    "bpm_name": "BPMZ8T4R",
    "x_state": 0,
    "y_state": 0,
    "ds": 0,
    "idx": 64,
    "scale_x": 0,
    "scale_y": 0
  }
"""

import json
import secrets

def safe_get(d, *path, default=None):
    cur = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur

def gen_oid_hex() -> str:
    # Generate a 24-hex string (like MongoDB ObjectId)
    return secrets.token_hex(12)

def main():
    with open("ao_mls.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    bpmx = data.get("BPMx", {}) or {}
    bpmy = data.get("BPMy", {}) or {}

    names   = bpmx.get("CommonNames", []) or []
    x_state = bpmx.get("Status", []) or []
    y_state = bpmy.get("Status", []) or []

    atidx_x = safe_get(bpmx, "AT", "ATIndex", default=[]) or []
    atidx_y = safe_get(bpmy, "AT", "ATIndex", default=[]) or []

    def idx_for(i):
        if i < len(atidx_x):
            return atidx_x[i]
        if i < len(atidx_y):
            return atidx_y[i]
        return None

    # Iterate over aligned BPM lists; idx fallback handles ATIndex source
    n = min(len(names), len(x_state), len(y_state))

    results = []
    for i in range(n):
        idx = idx_for(i)
        if idx is None:
            continue
        results.append({
            "_id": {"$oid": gen_oid_hex()},
            "bpm_name": names[i],
            "x_state": x_state[i],
            "y_state": y_state[i],
            "ds": 0,
            "idx": idx,
            "scale_x": 0,
            "scale_y": 0
        })

    with open("bpm_config.json", "w", encoding="utf-8") as out:
        json.dump(results, out, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
