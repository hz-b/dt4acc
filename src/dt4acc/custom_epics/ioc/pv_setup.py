from dataclasses import dataclass

import numpy as np
from bact_twin_architecture.data_model.identifiers import DevicePropertyID

from .handlers import handle_device_update, update_manager
from ..data.constants import config, special_pvs, cavity_names
from ..data.querries import (
    get_unique_power_converters,
    get_magnets_per_power_converters,
)
from ...core.utils.logger import get_logger

logger = get_logger()


def flag_not_handling(pv_name: str, val: object):
    logger.warning("Not handling update of pv %s to %s", pv_name, val)
@dataclass(frozen=True)
class LatticeElementPropertyID:
    element_name: str
    property: str
    uuid:str

def initialize_magnet_pvs(builder, magnet):
    """
    Initializes the process variables (PVs) for a given magnet.

    Args:
        builder: The SoftIOC PV builder instance.
        magnet (dict): Magnet properties including name, type, and magnetic strength.

    PVs Created:
        - `<magnet_name>:Cm:set`: Setpoint for magnetic field strength
        - `<magnet_name>:im:I`: Measured current of the magnet
        - `<magnet_name>:x:set`: Horizontal position setpoint
        - `<magnet_name>:y:set`: Vertical position setpoint
    """
    magnet_name = magnet["name"]
    # Create an element representing the magnet
    # Create PVs and link to update logic
    val = update_manager.peek_engine(
        LatticeElementPropertyID(element_name=magnet_name, property="main_strength",uuid=magnet["uuid"])
    )
    builder.aOut(
        f"{magnet_name}:Cm:set",
        initial_value=magnet["k"] or 0,
        on_update=lambda val: handle_device_update(magnet_name, "K", val),
    )
    rdbk = builder.aIn(f"{magnet_name}:Cm:rdbk", initial_value=val)

    async def handle_magnet_update(device_id: str, property_id: str, value: float):
        r = await handle_device_update(
            device_id=device_id, property_id=property_id, value=value
        )
        logger.info("%s:%s setting setpoint val=%s", device_id, property_id, value)
        rdbk.set(value)
        logger.info("%s:%s set readback  val=%s", device_id, property_id, value)
        return r

    builder.aOut(
        f"{magnet_name}:im:I",
        initial_value=0.0,
        # Todo: what to do if current is set, should be rather read only
        # on_update=lambda val: handle_device_update(f"{magnet_name}:im:I", val)
        on_update=lambda val: handle_magnet_update(
            magnet_name, "powersupply_current", val
        ),
    )
    builder.aOut(
        f"{magnet_name}:x:set",
        initial_value=0.0,
        on_update=lambda val: handle_device_update(magnet_name, "x", val),
    )
    builder.aOut(
        f"{magnet_name}:y:set",
        initial_value=0.0,
        on_update=lambda val: handle_device_update(magnet_name, "y", val),
    )


def initialize_power_converter_pvs(builder, prefix):
    """
    Initializes power converter PVs and associated magnets.

    Args:
        builder: The SoftIOC PV builder instance.
        prefix (str): The prefix used for PV naming.
    """
    for pc_name in get_unique_power_converters():
        add_pc_pvs(builder, pc_name, prefix)


def add_pc_pvs(builder, pc_name, prefix):
    """
    Adds PVs for a specific power converter and its associated magnets.

    Args:
        builder: The SoftIOC PV builder instance.
        pc_name (str): Power converter name.
        prefix (str): Prefix for PVs.
    """
    magnets = get_magnets_per_power_converters(pc_name)
    element = {"magnets": [item["name"] for item in magnets]}
    element_cache = {}  # Store magnet information for reference
    element_cache[pc_name] = element

    # Initialize PVs for each magnet connected to this (pc_name) power converter
    for magnet_data in magnets:
        initialize_magnet_pvs(builder, magnet_data)

    # Create power converter setpoint and readback PVs
    # Todo: put it to power converters directly
    vals = update_manager.device_value_from_peeking_engine(
        DevicePropertyID(device_name=pc_name, property="set_current")
    )
    start_val = np.asarray(vals).mean()
    rdbk = builder.aOut(f"{pc_name}:rdbk", initial_value=start_val, PREC=2)

    async def handle_pc_update(device_id: str, property_id: str, value: float):
        logger.warning("%s:%s updating setpoint val=%s", device_id, property_id, value)
        r = await handle_device_update(
            device_id=device_id, property_id=property_id, value=value
        )
        logger.debug("%s:%s updating rdbk val=%s", device_id, property_id, value)
        rdbk.set(value)
        return r

    builder.aOut(
        f"{pc_name}:set",
        initial_value=start_val,
        on_update=lambda val: handle_pc_update(pc_name, "set_current", val),
        PREC = 2,
    )


def initialize_orbit_pvs(builder):
    """
    Initializes PVs related to beam orbit measurements.

    Args:
        builder: The SoftIOC PV builder instance.
    """
    builder.WaveformOut(f"beam:orbit:x", initial_value=[0.0], length=config.n_elements)
    builder.WaveformOut(f"beam:orbit:y", initial_value=[0.0], length=config.n_elements)
    builder.WaveformOut(f"beam:orbit:x0", initial_value=[0.0], length=config.n_elements)
    builder.WaveformOut(
        f"beam:orbit:names", initial_value=[""], length=config.n_elements
    )
    builder.aOut(f"beam:orbit:found", initial_value=0)


def initialize_tune_pvs(builder):
    for axis in ["rdH", "rdV"]:
        builder.aOut(f"TUNEZR:flq:{axis}", initial_value=0.0, PREC=9)
        builder.aOut(f"TUNEZR:{axis}", initial_value=0.0, PREC=3, EGU="kHz")
    builder.longOut(f"TUNEZR:count", initial_value=0)


def initialize_twiss_pvs(builder):
    """
    Initializes PVs for Twiss parameters, which describe beam optics.

    Args:
        builder: The SoftIOC PV builder instance.
    """
    for axis in ["x", "y"]:
        builder.WaveformOut(
            f"beam:twiss:{axis}:alpha", initial_value=[0.0], length=config.n_elements
        )
        builder.WaveformOut(
            f"beam:twiss:{axis}:beta", initial_value=[0.0], length=config.n_elements
        )
        builder.WaveformOut(
            f"beam:twiss:{axis}:nu", initial_value=[0.0], length=config.n_elements
        )
        builder.aOut(f"beam:twiss:{axis}:tune", initial_value=0.0, PREC=8)
    builder.WaveformOut(
        f"beam:twiss:names", initial_value=[""], length=config.n_elements
    )


def initialize_machine_info_pvs(builder):
    """configuration of the machine: e.g. number of bunches
    """

    builder.longOut(f"beam:machine:info:n_rf_buckets", initial_value=400)
    builder.aOut(f"beam:rev_freq", initial_value=0.0, EGU="kHz")


def initialize_master_clock_pvs(builder):
    """initalise master clock pv

    Warning:
        note for running the twin as a shadow it will
        require precise frequency tuning

    Todo:
        Foresee dedicated variables for allowing only a difference shift
        Provide the frequency the code starts with
    """
    vals = update_manager.device_value_from_peeking_engine(
        DevicePropertyID(device_name="master_clock", property="reference_frequency")
    )
    start_val = np.asarray(vals).mean()
    builder.aOut(
        f"{special_pvs['master_clock']}:freq",
        initial_value=start_val,
        always_update=True,
        EGU="kHz",
        PREC=3,
        on_update=lambda val: handle_device_update(
            device_id="master_clock", property_id="reference_frequency", value=val
        ),
    )
    #: todo ... comment these values
    builder.aIn("lattice_info:ref_freq", initial_value=start_val, EGU="kHz", PREC=1)
    builder.longIn(
        "lattice_info:ref_freq:khz:up", initial_value=int(start_val), EGU="kHz"
    )
    frac = (start_val % 1) * 1e6
    builder.longIn("lattice_info:ref_freq:khz:frac", initial_value=int(frac), EGU="mHz")


def initialize_other_pvs(builder, prefix):
    """Initializes miscellaneous PVs (dummy values).

    Args:
        builder: The SoftIOC PV builder instance.
        prefix (str): Prefix for PV naming.
    """
    builder.aOut(f"dummy:x", initial_value=0)
    builder.aOut(f"dummy:y", initial_value=0)
    builder.aOut(f"{special_pvs['current']}:current", initial_value=0)


def initialize_bpm_pvs(builder):
    tmp = np.empty([2048], np.int16)
    tmp.fill(-(2 ** 15) + 1)
    # bpm pv names from default
    builder.WaveformOut(
        f"{special_pvs['bpm_pv']}:bdata", initial_value=tmp, length=len(tmp)
    )
    builder.longOut(f"{special_pvs['bpm_pv']}:count", initial_value=0)


def initialize_orbit_object_pvs(builder):
    n_bpms = 128
    tmp = np.ravel(np.empty([n_bpms, 2], float))
    tmp.fill(np.nan)
    builder.WaveformOut("ORBITCC:rdPos", initial_value=tmp, length=len(tmp))
    tmp = np.ravel(np.empty([n_bpms, 4], float))
    tmp.fill(np.nan)
    builder.WaveformOut("ORBITCC:rdButtons", initial_value=tmp, length=len(tmp))
    builder.WaveformOut("ORBITCC:rdBpmNames", initial_value=[""], length=n_bpms)
    builder.longOut("ORBITCC:count", initial_value=0)


def initialize_cavity_pvs(builder):
    """
    Initializes PVs for RF cavities.

    Args:
        builder: The SoftIOC PV builder instance.

    Todo:
        check that these are updated if the master clock changes
    """

    for cavity_name in cavity_names:
        vals = update_manager.device_value_from_peeking_engine(
            DevicePropertyID(device_name=cavity_name, property="frequency")
        )
        start_val = np.asarray(vals).mean()
        builder.aOut(f"{cavity_name}:freq", initial_value=start_val, EGU="kHz", PREC=3)
