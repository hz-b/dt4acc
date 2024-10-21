import os

import pymongo

from dt4acc.resources import bpm_config

# MongoDB connection details
MONGO_URI = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("MONGODB_DB", "bessyii")
COLLECTION_NAME = "bpm.config"
client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# Read the content from the file
bpm_conf = bpm_config.bpm_conf
bpm_offset = bpm_config.bpm_offset




# Insert the bpm_conf data into bpm.config collection
for entry in bpm_conf:
    doc = {
        'bpm_name': entry[0],
        'x_state': entry[1],
        'y_state': entry[2],
        'ds': entry[3],
        'idx': entry[4],
        'scale_x': entry[5],
        'scale_y': entry[6]
    }
    collection.insert_one(doc)

collection = db['bpm.offset']
# Insert the bpm_offset data into bpm.offset collection
for bpm_name, offsets in bpm_offset.items():
    doc = {
        'bpm_name': bpm_name,
        'offset_x': offsets[0],
        'offset_y': offsets[1]
    }
    collection.insert_one(doc)

print("Data insertion completed.")
