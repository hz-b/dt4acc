from pathlib import Path
from typing import Any, List, Optional

import at


_lattice_file: Optional[Path] = None
_uuid_by_index: Optional[List[Any]] = None


def configure_lattice_file(lattice_file) -> None:
    global _lattice_file, _uuid_by_index
    _lattice_file = Path(lattice_file)
    _uuid_by_index = None


def _load_uuid_by_index() -> list:
    global _uuid_by_index
    if _uuid_by_index is not None:
        return _uuid_by_index
    if _lattice_file is None:
        raise RuntimeError("SOLEIL orbit name resolver has no lattice file configured")

    suffix = _lattice_file.suffix.lower()
    if suffix == ".json":
        lattice = at.load_json(str(_lattice_file))
    elif suffix == ".m":
        lattice = at.load_m(_lattice_file)
    else:
        raise ValueError(f"Unsupported SOLEIL lattice file format: {suffix!r}")

    _uuid_by_index = [_value(element, "UUID") for element in lattice]
    return _uuid_by_index


def _value(obj: Any, key: str):
    if hasattr(obj, key):
        value = getattr(obj, key)
        if value:
            return value
    get = getattr(obj, "get", None)
    if get is not None:
        value = get(key, None)
        if value:
            return value
    try:
        value = obj[key]
    except Exception:
        return None
    return value or None


_DEDICATED_BPM_FAMILIES = {"BPM", "FBPM"}


def soleil_position_name(position, index: int) -> str:
    name = str(position.name)
    if name.upper() not in _DEDICATED_BPM_FAMILIES:
        return name

    payload_uuid = _value(position, "UUID") or _value(position, "uuid")
    if payload_uuid:
        return str(payload_uuid)

    uuid_by_index = _load_uuid_by_index()
    if index >= len(uuid_by_index):
        raise RuntimeError(
            f"SOLEIL {name} at orbit index {index} has no matching lattice element"
        )

    lattice_uuid = uuid_by_index[index]
    if not lattice_uuid:
        raise RuntimeError(
            f"SOLEIL {name} at orbit index {index} has no UUID in the AT lattice"
        )
    return str(lattice_uuid)
