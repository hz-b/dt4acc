import json
from pydantic.dataclasses import dataclass
from pymongo import MongoClient
from importlib.resources import files


@dataclass
class AcceleratorSetup:
    type: str
    name: str
    hw2phys: float
    pc: str  # Field to store the power converter (setpoint)


MONGO_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "bessyii"
COLLECTION_NAME = "accelerator.setup"

# Type mapping based on family names
type_mapping = {
    "QUAD": "Quadrupole",
    "SEXT": "Sextupole",
    "STEER": "Steerers"
}


def get_config_filename(module_name: str, filename: str):
    '''Get the configuration filename using importlib.resources.'''
    path = files(module_name) / 'resources' / filename
    return path


def insert_data_into_mongodb(data):
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = db[COLLECTION_NAME]

    for name, hw2phys_value in data['hw2phys'].items():
        family = data['family'].get(name, "Unknown")
        magnet_type = type_mapping.get(family.upper(), "Unknown")
        pc = data['setpoint'].get(name, "Unknown")  # Get the power converter (setpoint)

        magnet = AcceleratorSetup(
            type=magnet_type,
            name=name,
            hw2phys=hw2phys_value,
            pc=pc
        )

        # Insert the magnet data into MongoDB
        collection.insert_one(magnet.__dict__)
    print("Data insertion complete.")


def main():
    file_name = "bessy2_quad_loco_current_hw2phys.json"
    path = get_config_filename("dt4acc", file_name)

    try:
        with open(path, 'r') as file:
            data = json.load(file)
    except FileNotFoundError as exc:
        print(f'Could not find package data file {file_name} using path {path}')
        raise exc

    insert_data_into_mongodb(data)


if __name__ == "__main__":
    main()
