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


async def update_fanout(fanout_items, prefix='Anonym:'):
    context = Context('pva')

    # Iterate over each fanout group, read source PV, update all target PVs
    for source_pv, target_pvs in fanout_items.items():
        # Read the source PV value from the EPICS 3 machine
        source_value = await aioca.caget(source_pv)

        # Asynchronously update each target PV in the EPICS 7 twin
        tasks = []
        for target_pv in target_pvs:
            twin_pv_name = prefix + target_pv
            tasks.append(context.put(twin_pv_name, source_value))

        # Execute all updates concurrently
        await asyncio.gather(*tasks)
        print(f"Updated all twin PVs based on {source_pv}")

    context.close()


# Example of calling the update function, using the machine prefix where your source PVs are located
async def main():
    await update_fanout(fanout_config)


if __name__ == "__main__":
    asyncio.run(main())
