#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Extract Q* (Quadrupole), S* (Sextupole), HCM (Steerer-H), VCM (Steerer-V)
from an AO JSON (e.g., ao_mls.json) into a flat JSON array.

For each element:
  - _id: {"$oid": "<24-hex>"}  (MongoDB-style id)
  - type: "Quadrupole" | "Sextupole" | "Steerer"
  - name: CommonNames[i]
  - pc:   Monitor.ChannelNames[i] with suffix after ':' stripped
  - k:    FIRST numeric parameter from the per-element Monitor.HW2PhysicsParams[i]

Output is saved to accelerator_setup.json.
"""

import json
import re
import secrets
from typing import Any, Dict, List, Optional, Union

Number = Union[int, float]
_suffix_re = re.compile(r":.*$")

def family_to_type(family_key: str) -> Optional[str]:
    if family_key.startswith("Q"):
        return "Quadrupole"
    if family_key.startswith("S"):
        return "Sextupole"
    if family_key in ("HCM", "VCM"):
        return "Steerer"
    return None

def strip_pc_suffix(ch_name: str) -> str:
    return _suffix_re.sub("", ch_name)

def normalize_hw2physicsparams(hw2: Any, n: int) -> List[Any]:
    if isinstance(hw2, list):
        if hw2 and isinstance(hw2[0], list) and len(hw2[0]) >= n:
            return hw2[0][:n]
        if len(hw2) >= n:
            return hw2[:n]
    return [hw2 for _ in range(n)]

def first_numeric_param(entry: Any) -> Optional[Number]:
    cur = entry
    max_depth = 3
    for _ in range(max_depth):
        if isinstance(cur, (list, tuple)) and len(cur) > 0:
            if isinstance(cur[0], (int, float)):
                return cur[0]
            cur = cur[0]
        else:
            break
    if isinstance(entry, (int, float)):
        return entry
    return None

def gen_oid_hex() -> str:
    return secrets.token_hex(12)  # 24-hex string like MongoDB ObjectId

def main():
    with open("ao_mls.json", "r", encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)

    results: List[Dict[str, Any]] = []

    for family_key, family_obj in data.items():
        if not isinstance(family_obj, dict):
            continue

        mtype = family_to_type(family_key)
        if not mtype:
            continue

        monitor = family_obj.get("Monitor") or {}
        channel_names = list(monitor.get("ChannelNames") or [])
        common_names  = list(family_obj.get("CommonNames") or [])
        hw2           = monitor.get("HW2PhysicsParams")

        if not channel_names or not common_names or hw2 is None:
            continue

        count = min(len(channel_names), len(common_names))
        per_element_entries = normalize_hw2physicsparams(hw2, count)
        count = min(count, len(per_element_entries))

        for i in range(count):
            pc_name = strip_pc_suffix(channel_names[i])
            k_val = first_numeric_param(per_element_entries[i])
            if k_val is None:
                continue
            results.append({
                "_id": {"$oid": gen_oid_hex()},
                "type": mtype,
                "name": common_names[i],
                "pc": pc_name,
                "magnetic_strength": k_val,
                "k": k_val
            })

    with open("accelerator_setup.json", "w", encoding="utf-8") as out:
        json.dump(results, out, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
