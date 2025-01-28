import os

import pymongo

from src.dt4acc import mongodb_

client = pymongo.MongoClient(mongodb_)
DB_NAME = os.environ.get("MONGODB_DB", "bessyii")
db = client[DB_NAME]
collection = db['accelerator.setup']


def get_magnets():
    return collection.find({"type": {"$in": ["Quadrupole", "Sextupole", "Steerer"]}})


def get_magnets_per_power_converters(pc):
    return list(collection.find({"pc": pc}))


def get_unique_power_converters():
    """Fetch unique power converter names from magnets in the DB."""
    return collection.distinct("pc", {"type": {"$in": ["Quadrupole", "Sextupole", "Steerer"]}})


def get_unique_power_converters_type_specified(type_list):
    """Fetch unique power converter names from magnets in the DB."""
    return collection.distinct("pc", {"type": {"$in": type_list}})
