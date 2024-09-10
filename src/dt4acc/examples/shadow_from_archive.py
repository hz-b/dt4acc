import asyncio
import datetime
from urllib.error import HTTPError

from bact_archiver_bessyii import BESSY as archiver_bessy
from p4p.client.asyncio import Context
from pymongo import MongoClient

from dt4acc.setup_configuration.data_access import get_unique_power_converters_type_specified

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client.bessyii
collection = db['accelerator.setup']


async def get_archiver_data(pvname, t0, t1):
    try:
        # Use the archiver to get data
        archiver_data = archiver_bessy.getData(pvname, t0=t0, t1=t1, time_format='datetime')
        return archiver_data
    except HTTPError as e:
        if e.code == 404:
            print(f"PV {pvname} not found in archiver.")
        else:
            print(f"Error fetching data for {pvname}: {e}")
        return None  # Return None if data is not available or error occurs
    except Exception as e:
        print(f"Unexpected error fetching data for {pvname}: {e}")
        return None


async def generate_fanout_config(pc_list):
    """Generate the fanout configuration from power converters."""
    fanout_config = {}

    # Query MongoDB for all magnets related to power converters
    magnets = collection.find({"pc": {"$in": pc_list}})

    # Build the fanout structure (map source PVs to target PVs)
    for magnet in magnets:
        pc_name = magnet['pc']
        target_pv = f"{magnet['name']}:im:I"
        if f"{pc_name}:set" not in fanout_config:
            fanout_config[f"{pc_name}:set"] = []
        fanout_config[f"{pc_name}:set"].append(target_pv)

    return fanout_config


async def update_fanout(fanout_items, t0, t1, prefix='Anonym:'):
    context = Context('pva')
    combined_pv_list = []

    # Iterate over fanout configuration and update PVs
    pv_names = []
    pv_values = []
    for source_pv, target_pvs in fanout_items.items():
        # Fetch the archiver data for the source PV
        archiver_data = await get_archiver_data(source_pv, t0, t1)
        if archiver_data is not None and not archiver_data.empty:
            source_value = archiver_data['val'].iloc[-1]  # Use the latest value
            combined_pv_list.append((source_pv, source_value))
        else:
            source_value = 0.0

        # Create the list of twin PVs to update
        for target_pv in target_pvs:
            twin_pv_name = prefix + target_pv
            pv_names.append(twin_pv_name)
            pv_values.append(source_value)

    # Bulk update to the twin
    for pv_name, value in combined_pv_list:
        print(f"PV: {pv_name}, Value: {value}")
    await context.put(pv_names, pv_values)
    print("Bulk update completed for all twin PVs")
    context.close()


async def main():
    # Define the time window for the data retrieval
    t0 = datetime.datetime(2024, 3, 21, 11, 40)
    t1 = datetime.datetime(2024, 3, 21, 11, 41)
    fanout_config = await generate_fanout_config(
        get_unique_power_converters_type_specified(["Quadrupole", "Sextupole", "Steerer"]))

    await update_fanout(fanout_config, t0, t1)


if __name__ == "__main__":
    asyncio.run(main())
