#!/usr/bin/env python3
"""
Simple script to list all devices in the Tango database.

This script shows:
1. All registered devices in the database
2. All currently running devices
3. Devices categorized by type (power converters, magnets, etc.)

Usage:
    python list_all_devices.py
    
Requirements:
    - PyTango installed
    - TANGO_HOST environment variable set
    - Running Tango database
"""

import os
import sys
from typing import List, Dict

try:
    from tango import Database
    TANGO_AVAILABLE = True
except ImportError:
    print("❌ PyTango not available. Please install it: pip install PyTango")
    TANGO_AVAILABLE = False


def check_tango_environment():
    """Check if Tango environment is properly set up."""
    if not TANGO_AVAILABLE:
        return False
    
    tango_host = os.environ.get("TANGO_HOST")
    if not tango_host:
        print("❌ TANGO_HOST environment variable is not set.")
        print("   Set it like: export TANGO_HOST=127.0.0.1:10000")
        return False
    
    try:
        db = Database()
        db.get_info()
        print(f" Connected to Tango database at {tango_host}")
        return True
    except Exception as e:
        print(f"❌ Cannot connect to Tango database: {e}")
        return False


def get_all_registered_devices() -> List[str]:
    """Get all devices registered in the database."""
    try:
        db = Database()
        devices = db.get_device_name("*", "*")
        return [str(device) for device in devices] if devices else []
    except Exception as e:
        print(f"❌ Error getting registered devices: {e}")
        return []


def get_all_running_devices() -> List[str]:
    """Get all currently running/exported devices."""
    try:
        db = Database()
        devices = db.get_device_exported("*")
        return [str(device) for device in devices] if devices else []
    except Exception as e:
        print(f"❌ Error getting running devices: {e}")
        return []


def categorize_devices(devices: List[str]) -> Dict[str, List[str]]:
    """Categorize devices by type based on their names."""
    categories = {
        'Power Converters': [],
        'Magnets': [],
        'BPM': [],
        'Cavities': [],
        'Twiss/Orbit': [],
        'Master Clock': [],
        'Other PVs': [],
        'Unknown': []
    }
    
    for device in devices:
        device_name = device.lower()
        if 'power_converter_' in device_name:
            categories['Power Converters'].append(device)
        elif 'magnet_' in device_name:
            categories['Magnets'].append(device)
        elif 'bpm' in device_name:
            categories['BPM'].append(device)
        elif 'cavity' in device_name:
            categories['Cavities'].append(device)
        elif 'twiss_orbit' in device_name:
            categories['Twiss/Orbit'].append(device)
        elif 'master_clock' in device_name:
            categories['Master Clock'].append(device)
        elif 'other_pvs' in device_name:
            categories['Other PVs'].append(device)
        else:
            categories['Unknown'].append(device)
    
    return categories


def print_device_list(title: str, devices: List[str], show_all: bool = False):
    """Print a formatted list of devices."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")
    print(f"Total devices: {len(devices)}")
    
    if not devices:
        print("   No devices found")
        return
    
    # Show devices
    devices_to_show = devices if show_all or len(devices) <= 20 else devices[:20]
    
    for i, device in enumerate(devices_to_show, 1):
        print(f"   {i:2d}. {device}")
    
    if not show_all and len(devices) > 20:
        print(f"   ... and {len(devices) - 20} more devices")
        print(f"   (Use show_all=True to see all devices)")


def print_categorized_devices(categories: Dict[str, List[str]]):
    """Print devices organized by category."""
    print(f"\n{'='*60}")
    print(" DEVICES BY CATEGORY")
    print(f"{'='*60}")
    
    total_devices = sum(len(devices) for devices in categories.values())
    print(f"Total devices: {total_devices}")
    
    for category, devices in categories.items():
        if devices:
            print(f"\n {category}: {len(devices)} devices")
            # Show first few examples
            for i, device in enumerate(devices[:5], 1):
                print(f"   {i}. {device}")
            if len(devices) > 5:
                print(f"   ... and {len(devices) - 5} more")


def main():
    """Main function to list all devices."""

    
    # Check Tango environment
    if not check_tango_environment():
        return
    
 
    
    # Get all registered devices
    registered_devices = get_all_registered_devices()
    print_device_list("ALL REGISTERED DEVICES", registered_devices)
    
    # Get all running devices
    running_devices = get_all_running_devices()
    print_device_list("CURRENTLY RUNNING DEVICES", running_devices)
    
    # Show categorized view of running devices
    if running_devices:
        categories = categorize_devices(running_devices)
        print_categorized_devices(categories)
    
    # Summary
    print(f"\n{'='*60}")
    print(" SUMMARY")
    print(f"{'='*60}")
    print(f"• Total registered devices: {len(registered_devices)}")
    print(f"• Currently running devices: {len(running_devices)}")
    
    if registered_devices:
        running_percentage = (len(running_devices) / len(registered_devices)) * 100
        print(f"• Devices currently running: {running_percentage:.1f}%")
    
    # Show power converters and magnets specifically
    if running_devices:
        categories = categorize_devices(running_devices)
        power_converters = categories.get('Power Converters', [])
        magnets = categories.get('Magnets', [])
        
        print(f"\n Power Converters found: {len(power_converters)}")
        for pc in power_converters:
            print(f"   • {pc}")
            
        print(f"\n Magnets found: {len(magnets)}")
        for magnet in magnets:
            print(f"   • {magnet}")
    
    print(f"\n{'='*60}")
    print(" Device listing completed")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
