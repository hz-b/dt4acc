import itertools
import logging

from p4p.client.asyncio import Context

logger = logging.getLogger(__name__)

ctx = Context("pva")


async def update_or_create_pv(element, pv_name, value, value_type, initial_type):
    try:
        await ctx.put(pv_name, value)
    except Exception as e:
        logger.error(f"Failed to update PV {pv_name}: {e}")


# Function to update Twiss PVs
async def update_twiss_pv(pv_name, twiss_result):
    try:
        await ctx.put(f"{pv_name}:x:alpha", twiss_result.x.alpha)
        await ctx.put(f"{pv_name}:x:beta", twiss_result.x.beta)
        await ctx.put(f"{pv_name}:x:nu", twiss_result.x.nu)
        await ctx.put(f"{pv_name}:y:alpha", twiss_result.y.alpha)
        await ctx.put(f"{pv_name}:y:beta", twiss_result.y.beta)
        await ctx.put(f"{pv_name}:y:nu", twiss_result.y.nu)
        # await ctx.put(f"{pv_name}:names", twiss_result.names)
    except Exception as e:
        logger.error(f"Failed to update or create PV {pv_name}: {e}")
    try:
        await ctx.put(twiss_result.all_k_pv_names, twiss_result.all_k_pv_values)
    except Exception as e:
        logger.error(f"Failed to update or create PV {pv_name}: {e}")


# Function to update Orbit PVs
async def update_orbit_pv(pv_name, orbit_result):
    try:
        await ctx.put(f"{pv_name}:x", orbit_result.x)
        await ctx.put(f"{pv_name}:y", orbit_result.y)
        await ctx.put(f"{pv_name}:names", orbit_result.names)
        await ctx.put(f"{pv_name}:found", orbit_result.found)
        await ctx.put(f"{pv_name}:x0", orbit_result.x0)
    except Exception as e:
        logger.error(f"Failed to update or create PV {pv_name}: {e}")


# Function to update BPM PVs
cnt = itertools.count()


async def update_bpm_pv(pv_name, bpm_result):
    try:
        await ctx.put(pv_name, bpm_result)
        await ctx.put('MDIZ2T5G:count', next(cnt))  # add the prefix
    except Exception as e:
        logger.error(f"Failed to update or create PV {pv_name}: {e}")
