# import os
#
# import pymongo

# from dt4acc import mongodb_
#
# client = pymongo.MongoClient(mongodb_)
# DB_NAME = os.environ.get("MONGODB_DB", "bessyii")
# db = client[DB_NAME]
# collection = db['accelerator.setup']
# TODO
# this is a temporary solution to avoid the MongoDB dependency
# rework this to use the file repository along with mongodb

import json
from pathlib import Path
from typing import Iterable, List, Dict, Any

from dt4acc.config.accelerator_config import accelerator_config



# -----------------------------------------------------------------
# helper: Mongo-style $in filtering for the tiny use-cases we need
# -----------------------------------------------------------------
def _match(doc: Dict[str, Any], field: str, allowed: Iterable[str]) -> bool:
    return doc.get(field) in allowed


def _get_elements(elements: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    if elements is None:
        elements = accelerator_config.get_accelerator_setup()

    if elements is None:
        raise RuntimeError(
            "Accelerator setup is not loaded. "
            "Provide `elements` explicitly or initialize accelerator_config first."
        )

    return elements


def get_magnets(elements: list[dict[str, Any]] | None = None):
    """Return all Quadrupole/Sextupole/Steerer magnets as an iterator."""
    wanted = {"Quadrupole", "Sextupole", "Steerer"}
    elements = _get_elements(elements)
    return (d for d in elements if _match(d, "type", wanted))


def get_magnets_per_power_converters(
    pc: str,
    elements: list[dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    """Return all magnets driven by the given power-converter name."""
    elements = _get_elements(elements)
    return [d for d in elements if d.get("pc") == pc]


def get_unique_power_converters(
    elements: list[dict[str, Any]] | None = None,
) -> List[str]:
    """Distinct list of power-converter names for Quad/Sext/Steerer magnets."""
    wanted = {"Quadrupole", "Sextupole", "Steerer"}
    elements = _get_elements(elements)
    return sorted(
        {
            d["pc"]
            for d in elements
            if _match(d, "type", wanted) and "pc" in d
        }
    )


def get_unique_power_converters_type_specified(
    type_list: Iterable[str],
    elements: list[dict[str, Any]] | None = None,
) -> List[str]:
    """Distinct list of power-converter names for the supplied magnet types."""
    wanted = set(type_list)
    elements = _get_elements(elements)
    return sorted(
        {
            d["pc"]
            for d in elements
            if _match(d, "type", wanted) and "pc" in d
        }
    )

#
# def get_magnets():
#     return collection.find({"type": {"$in": ["Quadrupole", "Sextupole", "Steerer"]}})
#
#
# def get_magnets_per_power_converters(pc):
#     return list(collection.find({"pc": pc}))
#
#
# def get_unique_power_converters():
#     """Fetch unique power converter names from magnets in the DB."""
#     return collection.distinct("pc", {"type": {"$in": ["Quadrupole", "Sextupole", "Steerer"]}})
#
#
# def get_unique_power_converters_type_specified(type_list):
#     """Fetch unique power converter names from magnets in the DB."""
#     return collection.distinct("pc", {"type": {"$in": type_list}})
