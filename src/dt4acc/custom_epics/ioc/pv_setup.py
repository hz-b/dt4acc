import numpy as np

from .handlers import handle_device_update
from ..data.constants import DEFAULTS, CAVITY_NAMES
from ..data.querries import get_unique_power_converters, get_magnets_per_power_converters
from ...core.model.elementmodel import MagnetElementSetup


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
    magnet_name = magnet['name']
    # Create an element representing the magnet
    # Create PVs and link to update logic
    builder.aOut(f"{magnet_name}:Cm:set", initial_value=magnet["k"] or 0.0,
                 on_update=lambda val: handle_device_update(magnet_name, "K", val))
    builder.aOut(f"{magnet_name}:im:I", initial_value=0.0,
                 # Todo: what to do if current is set, should be rather read only
                 # on_update=lambda val: handle_device_update(f"{magnet_name}:im:I", val)
    )
    builder.aOut(f"{magnet_name}:x:set", initial_value=0.0,
                 on_update=lambda val: handle_device_update(magnet_name, "x", val))
    builder.aOut(f"{magnet_name}:y:set", initial_value=0.0,
                 on_update=lambda val: handle_device_update(magnet_name, "y", val))


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
    element = {'magnets': [item['name'] for item in magnets]}
    element_cache = {}  # Store magnet information for reference
    element_cache[pc_name] = element

    # Initialize PVs for each magnet connected to this (pc_name) power converter
    for magnet_data in magnets:
        initialize_magnet_pvs(builder, magnet_data)

    # Create power converter setpoint and readback PVs
    builder.aOut(f"{pc_name}:set", initial_value=0.0,
                 on_update=lambda val: handle_device_update(pc_name, "set_current", val))
    builder.aOut(f"{pc_name}:rdbk", initial_value=0.0)


def initialize_orbit_pvs(builder):
    """
    Initializes PVs related to beam orbit measurements.

    Args:
        builder: The SoftIOC PV builder instance.
    """
    builder.WaveformOut(f"beam:orbit:x", initial_value=[0.0], length=DEFAULTS['n_element'])
    builder.WaveformOut(f"beam:orbit:y", initial_value=[0.0], length=DEFAULTS['n_element'])
    builder.WaveformOut(f"beam:orbit:x0", initial_value=[0.0], length=DEFAULTS['n_element'])
    builder.WaveformOut(f"beam:orbit:names", initial_value=[""], length=DEFAULTS['n_element'])
    builder.aOut(f"beam:orbit:found", initial_value=0)


def initialize_twiss_pvs(builder):
    """
    Initializes PVs for Twiss parameters, which describe beam optics.

    Args:
        builder: The SoftIOC PV builder instance.
    """
    for axis in ['x', 'y']:
        builder.WaveformOut(f"beam:twiss:{axis}:alpha", initial_value=[0.0], length=DEFAULTS['n_element'])
        builder.WaveformOut(f"beam:twiss:{axis}:beta", initial_value=[0.0], length=DEFAULTS['n_element'])
        builder.WaveformOut(f"beam:twiss:{axis}:nu", initial_value=[0.0], length=DEFAULTS['n_element'])
    builder.WaveformOut(f"beam:twiss:names", initial_value=[""], length=DEFAULTS['n_element'])


def initialize_other_pvs(builder, prefix):
    """
    Initializes miscellaneous PVs including master clock and dummy values.

    Args:
        builder: The SoftIOC PV builder instance.
        prefix (str): Prefix for PV naming.
    """
    builder.aOut(f"{DEFAULTS['master_clock']}:freq", initial_value=0,
                 on_update=lambda val: handle_device_update(device_id="master_clock", property_id="reference_frequency", value=val))
    builder.aOut(f"dummy:x", initial_value=0)
    builder.aOut(f"dummy:y", initial_value=0)
    builder.aOut(f"{DEFAULTS['current']}:current", initial_value=0)


def initialize_bpm_pvs(builder):
    tmp = np.empty([2048], np.int16)
    tmp.fill(-2 ** 15 + 1)
    # bpm pv names from default
    builder.WaveformOut(f"{DEFAULTS['bpm_pv']}:bdata", initial_value=tmp, length=len(tmp))
    builder.longOut(f"{DEFAULTS['bpm_pv']}:count", initial_value=0)


def initialize_cavity_pvs(builder):
    """
    Initializes PVs for RF cavities.

    Args:
        builder: The SoftIOC PV builder instance.
    """
    for cavity_name in CAVITY_NAMES:
        builder.aOut(f"{cavity_name}:freq", initial_value=0.0)
