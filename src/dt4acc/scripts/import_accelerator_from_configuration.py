import pandas as pd
import pymongo
import os

from ..resources import conversion_factors_file
from ..resources.power_converters import quad_power_supplies, sext_power_supplies, steerer_power_supplies

from lat2db.model.accelerator import Accelerator

# MongoDB connection details
MONGO_URI = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = "bessyii"
COLLECTION_NAME = "accelerator.setup"

# Mapping of power converters from the power_converters.py
pc_mapping = {
    "Quadrupole": quad_power_supplies(),
    "Sextupole": sext_power_supplies(),
    "Steerer": steerer_power_supplies()
}

# Load MongoDB client
client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]


def insert_data(data, magnet_type, machine):
    """Insert data into the database with magnet_type: Quadrupole, Sextupole, Steerer."""
    for magnet_name, magnetic_strength in zip(data['Magnet'], data['Magnetic Strength']):
        magnet_name = magnet_name.strip("'\\")

        # Find the correct magnet based on its type and name
        target_magnet = None
        if magnet_type == "Quadrupole":
            target_magnet = next(
                (q for q in machine.quadrupoles if q.name == magnet_name), None
            )
        else:
            target_magnet = next(
                (s for s in machine.sextupoles if s.name == magnet_name), None
            )
        # Add similar checks for other magnet types as needed

        # Extract the 'k' value if the magnet is found
        k = None
        if target_magnet:
            if magnet_type == "Quadrupole":
                k = target_magnet.element_configuration.magnetic_element.coeffs.normal_coefficients[1]
            else:
                k = target_magnet.element_configuration.magnetic_element.coeffs.normal_coefficients[2]

        # Find corresponding power converters
        for pc, magnets in pc_mapping[magnet_type].items():
            if magnet_name in magnets:
                record = {
                    "type": magnet_type,
                    "name": magnet_name,
                    "magnetic_strength": magnetic_strength,
                    "pc": pc,
                    "k": k
                }
                print(f"Inserting: {record}")
                collection.insert_one(record)


# Load data from Excel

sheets = {
    "Quadrupole": "Quadrupoles",
    "Sextupole": "Sextupoles",
    "Steerer": "Steerers"
}

machine = Accelerator().machine
for magnet_type, sheet_name in sheets.items():
    df = pd.read_excel(conversion_factors_file, sheet_name=sheet_name)
    df = df.iloc[:, [0, 1]]  # Select only the first two columns
    df.columns = ['Magnet', 'Magnetic Strength']  # Rename columns for clarity
    df.dropna(subset=['Magnet', 'Magnetic Strength'], inplace=True)
    df = df[df['Magnet'].str.strip().astype(bool)]

    insert_data(df, magnet_type,machine)

print("Data insertion completed.")
