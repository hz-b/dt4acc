# data_access.py
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client.bessyii


def get_magnets():
    return db['accelerator.setup'].find({"type": {"$in": ["Quadrupole", "Sextupole", "Steerer"]}})


def get_magnets_per_power_converters(pc):
    return list(db['accelerator.setup'].find({"pc": pc}))


def get_unique_power_converters():
    """Fetch unique power converter names from magnets in the DB."""
    return db['accelerator.setup'].distinct("pc", {"type": {"$in": ["Quadrupole", "Sextupole", "Steerer"]}})


def get_unique_power_converters_type_specified(type_list):
    """Fetch unique power converter names from magnets in the DB."""
    return db['accelerator.setup'].distinct("pc", {"type": {"$in": type_list}})
