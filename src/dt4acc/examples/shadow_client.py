import asyncio

import aioca
from p4p.client.asyncio import Context
from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client.bessyii
collection = db['accelerator.setup']


async def generate_fanout_config(pc_list):
    fanout_config = {}
    # get all unique setpoints or power converted from db.
    # we can also use one or more specific pcs
    # pcs = collection.distinct('pc')

    magnets = collection.find({"pc": {"$in": pc_list}})

    # Generate the list of target PVs for this PC
    target_pvs = []
    for magnet in magnets:
        name = magnet['name']
        target_pv = f"{name}:im:I"
        target_pvs.append(target_pv)

    # Add the list of target PVs to the fanout configuration
    fanout_config[f"{magnet['pc']}:set"] = target_pvs

    return fanout_config


async def update_fanout(fanout_items, prefix='Anonym:', use_machine=True):
    context = Context('pva')

    # Default values to use when not connecting to the machine
    default_values = [216.0197917196, 215.82754328]  # [1e49, 1e69]

    # Perform the first bulk update for power converter PVs
    pv_names = []
    pv_values = []
    for idx, (source_pv, target_pvs) in enumerate(fanout_items.items()):
        if use_machine:
            source_value = await aioca.caget(source_pv)
        else:
            source_value = default_values[idx % len(default_values)]  # Alternate between values

        for target_pv in target_pvs:
            twin_pv_name = prefix + target_pv
            pv_names.append(twin_pv_name)
            pv_values.append(source_value)

    await context.put(pv_names, pv_values)
    print("Bulk update completed for all twin PVs")

    context.close()


async def main():
    # Generate the fanout configuration dynamically
    fanout_config = await generate_fanout_config(["S1PR"])

    # Update the PVs based on the fanout configuration
    await update_fanout(fanout_config)


if __name__ == "__main__":
    asyncio.run(main())
