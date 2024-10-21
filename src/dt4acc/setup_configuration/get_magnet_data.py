# get_magnet_data.py
import os

import pymongo

MONGO_URI = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("MONGODB_DB", "bessyii")
COLLECTION_NAME = "accelerator.setup"
client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

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
