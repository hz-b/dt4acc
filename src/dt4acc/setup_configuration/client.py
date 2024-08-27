import asyncio

import aioca
from p4p.client.asyncio import Context

# Configuration for fanout relationships
fanout_config = {
    "Q1PDR:set": [
        "Q1M1D1R:im:I", "Q1M1D2R:im:I", "Q1M1D3R:im:I", "Q1M1D4R:im:I",
        "Q1M1D5R:im:I", "Q1M1D6R:im:I", "Q1M1D7R:im:I", "Q1M1D8R:im:I"
    ],
    "Q1PTR:set": [
        "Q1M1T1R:im:I", "Q1M1T2R:im:I", "Q1M1T3R:im:I", "Q1M1T4R:im:I",
        "Q1M1T5R:im:I", "Q1M1T6R:im:I", "Q1M1T7R:im:I", "Q1M1T8R:im:I"
    ]
}


async def update_fanout(fanout_items, prefix='Anonym:', use_machine=False):
    context = Context('pva')
    magnet_updates = []

    # Default values to use when not connecting to the machine
    default_values = [2.44045585 * 100, 2.440455 * 100]  # [1e49, 1e69]

    # Perform the first bulk update for power converter PVs
    pv_names = []
    pv_values = []
    for idx, (source_pv, target_pvs) in enumerate(fanout_items.items()):
        if use_machine:
            source_value = await aioca.caget(source_pv)
        else:
            # Use the default values instead of caget
            source_value = default_values[idx % len(default_values)]  # Alternate between 1e49 and 1e69

        for target_pv in target_pvs:
            twin_pv_name = prefix + target_pv
            pv_names.append(twin_pv_name)
            pv_values.append(source_value)
            magnet_name = twin_pv_name.replace("im:I", "Cm:set")
            magnet_value = source_value / 100
            magnet_updates.append((magnet_name, magnet_value))

    await context.put(pv_names, pv_values)
    print("Bulk update completed for all twin PVs")

    # Now perform the secondary bulk update for magnet PVs
    if magnet_updates:
        magnet_pv_names, magnet_pv_values = zip(*magnet_updates)
        await context.put(magnet_pv_names, magnet_pv_values)

    context.close()


async def main():
    await update_fanout(fanout_config)


if __name__ == "__main__":
    asyncio.run(main())
