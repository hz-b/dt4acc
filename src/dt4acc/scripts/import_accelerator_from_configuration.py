import pandas as pd
import pymongo

from ..resources.power_converters import quad_power_supplies, sext_power_supplies, steerer_power_supplies

# MongoDB connection details
MONGO_URI = "mongodb://localhost:27017"
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


def insert_data(data, magnet_type):
    """Insert data into the database with magnet_type: Quadrupole, Sextupole, Steerer."""
    for magnet_name, magnetic_strength in zip(data['Magnet'], data['Magnetic Strength']):
        magnet_name = magnet_name.strip("'\\")
        # Find corresponding power converters
        for pc, magnets in pc_mapping[magnet_type].items():
            if magnet_name in magnets:
                record = {
                    "type": magnet_type,
                    "name": magnet_name,
                    "magnetic_strength": magnetic_strength,
                    "pc": pc
                }
                print(f"Inserting: {record}")
                collection.insert_one(record)


# Load data from Excel
excel_file = "../resources/conversion-factors-simplified-table.xlsx"
sheets = {
    "Quadrupole": "Quadrupoles",
    "Sextupole": "Sextupoles",
    "Steerer": "Steerers"
}

for magnet_type, sheet_name in sheets.items():
    df = pd.read_excel(excel_file, sheet_name=sheet_name)
    df = df.iloc[:, [0, 1]]  # Select only the first two columns
    df.columns = ['Magnet', 'Magnetic Strength']  # Rename columns for clarity
    df.dropna(subset=['Magnet', 'Magnetic Strength'], inplace=True)
    df = df[df['Magnet'].str.strip().astype(bool)]

    insert_data(df, magnet_type)

print("Data insertion completed.")
