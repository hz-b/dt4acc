#!/usr/bin/env python3
"""
Beautiful Tango Agent: Natural-language → (plan) → execute Tango/shell → human summary.

Install:
  pip install langchain langchain-community langchain-groq pydantic
  pip install PyTango

Env:
  export GROQ_API_KEY=your-groq-api-key
  export TANGO_HOST=127.0.0.1:10000   # or your host:port

Run:
  python tango_exec_agent.py "list all devices and summarize"
  python tango_exec_agent.py "show devices with magnet_ in the name and explain"
  python tango_exec_agent.py "set x=0.5 y=0.5 k=1.0 on SimpleTangoServer/test/magnet_Q3P2T6R, read them back, get status"
  python tango_exec_agent.py "run 'docker ps' and explain the output"
  python tango_exec_agent.py --interactive
"""

import os
import sys
import json
import traceback
import argparse
from typing import List, Dict, Any, Optional

# LangChain
from langchain.agents import AgentType, initialize_agent
from langchain_groq import ChatGroq
from langchain_community.tools import ShellTool
from langchain.tools import tool

# ---- Tango (PyTango) ---------------------------------------------------------
try:
    from tango import Database, DeviceProxy
except Exception as e:
    Database = None
    DeviceProxy = None
    _IMPORT_ERROR = e
else:
    _IMPORT_ERROR = None


def _need_pytango_error() -> str | None:
    if _IMPORT_ERROR:
        return (
            "PyTango import failed. Install PyTango and ensure system libs match. Error:\n"
            + "".join(traceback.format_exception_only(type(_IMPORT_ERROR), _IMPORT_ERROR))
        )
    return None


def _need_tango_host_error() -> str | None:
    if not os.environ.get("TANGO_HOST"):
        return "TANGO_HOST is not set (e.g., export TANGO_HOST=127.0.0.1:10000)."
    return None


# -------------------------- Beautiful Tango Tools ----------------------------
@tool
def tango_list_devices(pattern: str = "*") -> str:
    """
    List exported Tango devices by DB wildcard pattern.
    """
    err = _need_pytango_error() or _need_tango_host_error()
    if err:
        return json.dumps({"ok": False, "pattern": pattern, "error": err})
    try:
        db = Database()
        devices = db.get_device_exported(pattern)
        device_list = [str(device) for device in devices] if devices else []
        return json.dumps({
            "ok": True, 
            "pattern": pattern, 
            "devices": device_list,
            "count": len(device_list)
        })
    except Exception as e:
        return json.dumps({"ok": False, "pattern": pattern, "error": str(e)})


@tool
def tango_list_registered_devices(input: str = "") -> str:
    """
    List all registered devices (including non-running ones) from the database.
    Input: ignored (can be empty string)
    Returns JSON: {"ok": bool, "devices": [..], "count": int, "error"?: str}
    """
    err = _need_pytango_error() or _need_tango_host_error()
    if err:
        return json.dumps({"ok": False, "error": err})
    try:
        db = Database()
        devices = db.get_device_name("*", "*")
        # Convert to strings to ensure JSON serialization
        device_list = [str(device) for device in devices] if devices else []
        return json.dumps({
            "ok": True, 
            "devices": device_list,
            "count": len(device_list)
        })
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})


@tool  
def tango_filter_devices(input_str: str) -> str:
    """
    Filter devices by case-insensitive substring.
    Input: 'devices_json,substring' (comma-separated)
    Returns JSON: {"ok": bool, "substring": str, "devices": [..], "count": int, "error"?: str}
    """
    try:
        parts = input_str.split(',', 1)
        if len(parts) != 2:
            return json.dumps({"ok": False, "error": "Input must be 'devices_json,substring'"})
        devices_json, substring = parts
        
        payload = json.loads(devices_json)
        devices = payload.get("devices", [])
        sub = substring.lower()
        filtered = [d for d in devices if sub in d.lower()]
        return json.dumps({
            "ok": True, 
            "substring": substring, 
            "devices": filtered,
            "count": len(filtered)
        })
    except Exception as e:
        return json.dumps({"ok": False, "substring": substring, "error": str(e)})


@tool
def tango_ping_device(device_name: str) -> str:
    """
    Ping a Tango device to check if it's responding.
    
    Args:
        device_name (str): The full name of the Tango device to ping
            Example: "SimpleTangoServer/test/magnet_HS1MD1"
    
    Returns:
        str: JSON response with ping results
    """
    err = _need_pytango_error() or _need_tango_host_error()
    if err:
        return json.dumps({"ok": False, "device": device_name, "error": err})
    try:
        dev = DeviceProxy(device_name)
        response_time = dev.ping()
        return json.dumps({
            "ok": True, 
            "device": device_name, 
            "responding": True,
            "response_time_ms": response_time
        })
    except Exception as e:
        return json.dumps({
            "ok": False, 
            "device": device_name, 
            "responding": False,
            "error": str(e)
        })


@tool
def tango_get_device_attributes(device_name: str) -> str:
    """
    Get all available attributes for a Tango device.
    Returns JSON: {"ok": bool, "device": str, "attributes": [..], "count": int, "error"?: str}
    """
    err = _need_pytango_error() or _need_tango_host_error()
    if err:
        return json.dumps({"ok": False, "device": device_name, "error": err})
    try:
        dev = DeviceProxy(device_name)
        attributes_vector = dev.get_attribute_list()
        # Convert StdStringVector to Python list for JSON serialization
        attributes = list(attributes_vector)
        return json.dumps({
            "ok": True, 
            "device": device_name, 
            "attributes": attributes,
            "count": len(attributes)
        })
    except Exception as e:
        return json.dumps({"ok": False, "device": device_name, "error": str(e)})


@tool
def tango_read_attribute(input_str: str) -> str:
    """
    Read a specific attribute value from a Tango device.
    Input: 'device_name,attribute_name' (comma-separated)
    Returns JSON: {"ok": bool, "device": str, "attribute": str, "value": str, "error"?: str}
    """
    try:
        parts = input_str.split(',', 1)
        if len(parts) != 2:
            return json.dumps({"ok": False, "error": "Input must be 'device_name,attribute_name'"})
        device_name, attribute_name = parts
        
        err = _need_pytango_error() or _need_tango_host_error()
        if err:
            return json.dumps({"ok": False, "device": device_name, "error": err})
                
        dev = DeviceProxy(device_name)
        value = getattr(dev, attribute_name)
        return json.dumps({
            "ok": True, 
            "device": device_name, 
            "attribute": attribute_name,
            "value": str(value)
        })
    except Exception as e:
        return json.dumps({
            "ok": False, 
            "device": device_name if 'device_name' in locals() else "unknown", 
            "attribute": attribute_name if 'attribute_name' in locals() else "unknown",
            "error": str(e)
        })


@tool
def tango_write_attribute(input_str: str) -> str:
    """
    Write a value to a specific attribute on a Tango device.
    Input: 'device_name,attribute_name,value' (comma-separated)
    Returns JSON: {"ok": bool, "device": str, "attribute": str, "value": str, "error"?: str}
    """
    try:
        parts = input_str.split(',', 2)
        if len(parts) != 3:
            return json.dumps({"ok": False, "error": "Input must be 'device_name,attribute_name,value'"})
        device_name, attribute_name, value = parts
        
        err = _need_pytango_error() or _need_tango_host_error()
        if err:
            return json.dumps({"ok": False, "device": device_name, "error": err})
                    
        dev = DeviceProxy(device_name)
        setattr(dev, attribute_name, value)
        return json.dumps({
            "ok": True, 
            "device": device_name, 
            "attribute": attribute_name,
            "value": value
        })
    except Exception as e:
        return json.dumps({
            "ok": False, 
            "device": device_name if 'device_name' in locals() else "unknown", 
            "attribute": attribute_name if 'attribute_name' in locals() else "unknown",
            "error": str(e)
        })


@tool
def tango_set_magnet_values(input_str: str) -> str:
    """
    Set magnet attributes on a device: x_position, y_position, k_strength.
    Input: 'device_name,x,y,k' (comma-separated)
    Returns JSON: {"ok": bool, "device": str, "set": {...}, "error"?: str}
    """
    try:
        parts = input_str.split(',', 3)
        if len(parts) != 4:
            return json.dumps({"ok": False, "error": "Input must be 'device_name,x,y,k'"})
        device_name, x, y, k = parts
        
        err = _need_pytango_error() or _need_tango_host_error()
        if err:
            return json.dumps({"ok": False, "device": device_name, "error": err})
                
        dev = DeviceProxy(device_name)
        dev.x_position = float(x)
        dev.y_position = float(y)
        dev.k_strength = float(k)
        return json.dumps({
            "ok": True, 
            "device": device_name,
            "set": {"x_position": float(x), "y_position": float(y), "k_strength": float(k)}
        })
    except Exception as e:
        return json.dumps({
            "ok": False, 
            "device": device_name if 'device_name' in locals() else "unknown", 
            "error": str(e)
        })


@tool
def tango_read_magnet_values(device_name: str) -> str:
    """
    Read magnet attributes: x_position, y_position, k_strength.
    Returns JSON: {"ok": bool, "device": str, "values": {...}, "error"?: str}
    """
    err = _need_pytango_error() or _need_tango_host_error()
    if err:
        return json.dumps({"ok": False, "device": device_name, "error": err})
    try:
        dev = DeviceProxy(device_name)
        vals = {
            "x_position": float(dev.x_position),
            "y_position": float(dev.y_position),
            "k_strength": float(dev.k_strength),
        }
        return json.dumps({"ok": True, "device": device_name, "values": vals})
    except Exception as e:
        return json.dumps({"ok": False, "device": device_name, "error": str(e)})


@tool
def tango_get_status(device_name: str) -> str:
    """
    Get device state and status information.
    Returns JSON: {"ok": bool, "device": str, "state": str, "status": str, "error"?: str}
    """
    err = _need_pytango_error() or _need_tango_host_error()
    if err:
        return json.dumps({"ok": False, "device": device_name, "error": err})
    try:
        dev = DeviceProxy(device_name)
        state = dev.state()
        status = dev.status()
        return json.dumps({
            "ok": True, 
            "device": device_name, 
            "state": str(state),
            "status": str(status)
        })
    except Exception as e:
        return json.dumps({"ok": False, "device": device_name, "error": str(e)})


@tool
def tango_check_system_health(input: str = "") -> str:
    """
    Check the overall health of the Tango system.
    Input: ignored (can be empty string)
    Returns JSON: {"ok": bool, "database_connected": bool, "running_devices": int, "total_registered": int, "error"?: str}
    """
    err = _need_pytango_error() or _need_tango_host_error()
    if err:
        return json.dumps({"ok": False, "error": err})
    try:
        db = Database()
        running_devices = db.get_device_exported("*")
        all_devices = db.get_device_name("*", "*")
        return json.dumps({
            "ok": True,
            "database_connected": True,
            "running_devices": len(running_devices),
            "total_registered": len(all_devices),
            "system_healthy": len(running_devices) > 0
        })
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e), "database_connected": False})


@tool
def tango_read_power_converter_setpoint(device_name: str) -> str:
    """
    Read power converter current_setpoint attribute.
    Returns JSON: {"ok": bool, "device": str, "current_setpoint": float, "error"?: str}
    """
    err = _need_pytango_error() or _need_tango_host_error()
    if err:
        return json.dumps({"ok": False, "device": device_name, "error": err})
    try:
        dev = DeviceProxy(device_name)
        current_setpoint = dev.current_setpoint
        return json.dumps({
            "ok": True,
            "device": device_name,
            "current_setpoint": float(current_setpoint)
        })
    except Exception as e:
        return json.dumps({"ok": False, "device": device_name, "error": str(e)})


@tool
def tango_set_power_converter_setpoint(input_str: str) -> str:
    """
    Set power converter current_setpoint attribute.
    Input: 'device_name,setpoint_value' (comma-separated)
    Returns JSON: {"ok": bool, "device": str, "setpoint": float, "error"?: str}
    """
    try:
        parts = input_str.split(',', 1)
        if len(parts) != 2:
            return json.dumps({"ok": False, "error": "Input must be 'device_name,setpoint_value'"})
        device_name, setpoint_value = parts
        
        err = _need_pytango_error() or _need_tango_host_error()
        if err:
            return json.dumps({"ok": False, "device": device_name, "error": err})
                
        dev = DeviceProxy(device_name)
        dev.current_setpoint = float(setpoint_value)
        return json.dumps({
            "ok": True,
            "device": device_name,
            "setpoint": float(setpoint_value)
        })
    except Exception as e:
        return json.dumps({
            "ok": False, 
            "device": device_name if 'device_name' in locals() else "unknown", 
            "error": str(e)
        })


# A generic shell tool for when you say things like: "run `docker ps`"
shell_tool = ShellTool()


@tool
def tango_check_database_connection(input: str = "") -> str:
    """
    Check Tango database connection and environment setup.
    
    Args:
        input: ignored (can be empty string)
    
    Returns:
        JSON with connection status, TANGO_HOST, and database info
    """
    try:
        err = _need_pytango_error() or _need_tango_host_error()
        if err:
            return json.dumps({
                "ok": False, 
                "error": err,
                "tango_host": os.environ.get("TANGO_HOST", "Not set")
            })
        
        db = Database()
        
        # Try to get database info
        try:
            info = db.get_info()
            db_info = str(info) if info else "No info available"
        except:
            db_info = "Could not get database info"
        
        return json.dumps({
            "ok": True,
            "tango_host": os.environ.get("TANGO_HOST", "Not set"),
            "database_info": db_info,
            "message": "Database connection successful"
        })
        
    except Exception as e:
        return json.dumps({
            "ok": False, 
            "error": str(e),
            "tango_host": os.environ.get("TANGO_HOST", "Not set")
        })


@tool
def tango_get_magnet_power_converter_relationships(input: str = "") -> str:
    """
    Get relationships between magnets and power converters from EPICS data.
    
    Args:
        input: ignored (can be empty string)
    
    Returns:
        JSON with power converter -> magnets mapping
    """
    try:
        # Add the source path to import EPICS data functions
        import sys
        sys.path.append('/Volumes/MyDrive/Bessy/version-may/dt4acc/src')
        
        from dt4acc.custom_epics.data.querries import get_unique_power_converters, get_magnets_per_power_converters
        
        power_converters = list(get_unique_power_converters())
        relationships = {}
        
        for pc_name in power_converters:
            magnets = get_magnets_per_power_converters(pc_name)
            relationships[pc_name] = {
                "count": len(magnets),
                "magnets": [
                    {
                        "name": magnet.get('name', 'Unknown'),
                        "type": magnet.get('type', 'Unknown'),
                        "k_value": magnet.get('k', 0.0)
                    }
                    for magnet in magnets
                ]
            }
        
        return json.dumps({
            "ok": True,
            "power_converter_count": len(power_converters),
            "relationships": relationships,
            "message": f"Found {len(power_converters)} power converters with magnet relationships"
        })
        
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})


@tool
def tango_list_all_servers(input: str = "") -> str:
    """
    List all registered Tango servers.
    
    Args:
        input: ignored (can be empty string)
    
    Returns:
        JSON with list of all registered servers
    """
    try:
        err = _need_pytango_error() or _need_tango_host_error()
        if err:
            return json.dumps({"ok": False, "error": err})
        
        db = Database()
        servers = db.get_server_list('*')
        
        # Filter out empty entries
        server_list = [str(server) for server in servers if str(server).strip()]
        
        return json.dumps({
            "ok": True,
            "servers": server_list,
            "count": len(server_list),
            "message": f"Found {len(server_list)} registered servers"
        })
        
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})


@tool
def tango_get_running_devices_categorized(server_pattern: str = "SimpleTangoServer/test/*") -> str:
    """
    Get running devices with categorization by device type.
    
    Args:
        server_pattern: Pattern to match devices (default: SimpleTangoServer/test/*)
    
    Returns:
        JSON with categorized device counts and examples
    """
    try:
        err = _need_pytango_error() or _need_tango_host_error()
        if err:
            return json.dumps({"ok": False, "error": err})
        
        db = Database()
        devices = db.get_device_exported(server_pattern)
        device_list = [str(device) for device in devices] if devices else []
        
        # Categorize devices
        categories = {
            'Magnets': [],
            'Power Converters': [],
            'Twiss/Orbit': [],
            'BPM': [],
            'Cavities': [],
            'Master Clock': [],
            'Other PVs': [],
            'Unknown': []
        }
        
        for device in device_list:
            device_name = device.lower()
            if 'magnet_' in device_name:
                categories['Magnets'].append(device)
            elif 'power_converter_' in device_name:
                categories['Power Converters'].append(device)
            elif 'twiss_orbit' in device_name:
                categories['Twiss/Orbit'].append(device)
            elif 'bpm' in device_name:
                categories['BPM'].append(device)
            elif 'cavity' in device_name:
                categories['Cavities'].append(device)
            elif 'master_clock' in device_name:
                categories['Master Clock'].append(device)
            elif 'other_pvs' in device_name:
                categories['Other PVs'].append(device)
            else:
                categories['Unknown'].append(device)
        
        # Create summary with examples
        summary = {}
        for category, devices_in_cat in categories.items():
            if devices_in_cat:
                summary[category] = {
                    "count": len(devices_in_cat),
                    "examples": devices_in_cat[:3],  # First 3 as examples
                    "has_more": len(devices_in_cat) > 3
                }
        
        return json.dumps({
            "ok": True,
            "server_pattern": server_pattern,
            "total_devices": len(device_list),
            "categories": summary,
            "message": f"Found {len(device_list)} running devices in {len(summary)} categories"
        })
        
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})


@tool
def tango_register_server_with_device(input_str: str) -> str:
    """
    Register a new Tango server with a device.
    
    Args:
        input_str: JSON string with "server_name", "instance", "device_name", "device_class"
        Example: '{"server_name": "MyServer", "instance": "test", "device_name": "my_device", "device_class": "TestDevice"}'
    
    Returns:
        JSON result indicating success or error
    """
    try:
        from tango import DbDevInfo
        
        err = _need_pytango_error() or _need_tango_host_error()
        if err:
            return json.dumps({"ok": False, "error": err})
        
        data = json.loads(input_str)
        server_name = data["server_name"]
        instance = data["instance"]
        device_name = data["device_name"]
        device_class = data["device_class"]
        
        db = Database()
        
        # Create device registration info
        device_info = DbDevInfo()
        device_info._class = device_class
        device_info.server = f"{server_name}/{instance}"
        device_info.name = f"{server_name}/{instance}/{device_name}"
        
        try:
            db.add_device(device_info)
            
            # Verify registration
            servers = db.get_server_list('*')
            server_full_name = f"{server_name}/{instance}"
            is_registered = server_full_name in servers
            
            return json.dumps({
                "ok": True,
                "server": server_full_name,
                "device": device_name,
                "device_class": device_class,
                "full_device_name": device_info.name,
                "registered_in_db": is_registered,
                "message": f"Registered server {server_full_name} with device {device_name}"
            })
            
        except Exception as e:
            return json.dumps({
                "ok": False, 
                "error": f"Registration failed: {e}",
                "attempted_server": f"{server_name}/{instance}"
            })
        
    except json.JSONDecodeError as e:
        return json.dumps({"ok": False, "error": f"Invalid JSON: {e}"})
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})


@tool
def tango_set_magnet_property(input_str: str) -> str:
    """
    Set individual magnet property (x_position, y_position, k_strength).
    
    Args:
        input_str: JSON string with "device_name", "property", "value"
        Example: '{"device_name": "SimpleTangoServer/test/magnet_Q3P2T6R", "property": "x_position", "value": 0.5}'
    
    Returns:
        JSON with success status and readback value
    """
    try:
        err = _need_pytango_error() or _need_tango_host_error()
        if err:
            return json.dumps({"ok": False, "error": err})
        
        data = json.loads(input_str)
        device_name = data["device_name"]
        property_name = data["property"]
        value = float(data["value"])
        
        # Validate property name
        valid_properties = ["x_position", "y_position", "k_strength"]
        if property_name not in valid_properties:
            return json.dumps({
                "ok": False, 
                "error": f"Invalid property '{property_name}'. Valid: {valid_properties}"
            })
        
        dev = DeviceProxy(device_name)
        
        # Set the property
        setattr(dev, property_name, value)
        
        # Read back to verify
        readback_value = getattr(dev, property_name)
        
        return json.dumps({
            "ok": True,
            "device": device_name,
            "property": property_name,
            "value_set": value,
            "value_readback": float(readback_value),
            "message": f"Set {property_name} = {value}, readback = {readback_value}"
        })
        
    except json.JSONDecodeError as e:
        return json.dumps({"ok": False, "error": f"Invalid JSON: {e}"})
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})


@tool
def tango_set_power_converter_current(input_str: str) -> str:
    """
    Set power converter current_setpoint and verify the value.
    
    Args:
        input_str: JSON string with "device_name" and "current_setpoint"
        Example: '{"device_name": "SimpleTangoServer/test/power_converter_Q3P2T6R", "current_setpoint": 5.1}'
    
    Returns:
        JSON with success status and readback value
    """
    try:
        err = _need_pytango_error() or _need_tango_host_error()
        if err:
            return json.dumps({"ok": False, "error": err})
        
        data = json.loads(input_str)
        device_name = data["device_name"]
        setpoint = float(data["current_setpoint"])
        
        dev = DeviceProxy(device_name)
        
        # Set the current setpoint
        dev.current_setpoint = setpoint
        
        # Read back to verify
        readback_setpoint = dev.current_setpoint
        
        return json.dumps({
            "ok": True,
            "device": device_name,
            "current_setpoint_set": setpoint,
            "current_setpoint_readback": float(readback_setpoint),
            "message": f"Set current_setpoint = {setpoint}, readback = {readback_setpoint}"
        })
        
    except json.JSONDecodeError as e:
        return json.dumps({"ok": False, "error": f"Invalid JSON: {e}"})
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})


@tool
def tango_verify_device_properties(device_name: str) -> str:
    """
    Read all key properties of a device to verify current values.
    
    Args:
        device_name: Full Tango device name
    
    Returns:
        JSON with all readable properties and their current values
    """
    try:
        err = _need_pytango_error() or _need_tango_host_error()
        if err:
            return json.dumps({"ok": False, "error": err})
        
        dev = DeviceProxy(device_name)
        
        # Determine device type and read appropriate properties
        properties = {}
        
        if "magnet_" in device_name.lower():
            # Magnet device properties
            try:
                properties["x_position"] = float(dev.x_position)
            except:
                properties["x_position"] = "N/A"
            try:
                properties["y_position"] = float(dev.y_position)
            except:
                properties["y_position"] = "N/A"
            try:
                properties["k_strength"] = float(dev.k_strength)
            except:
                properties["k_strength"] = "N/A"
            try:
                properties["current"] = float(dev.current)
            except:
                properties["current"] = "N/A"
                
        elif "power_converter_" in device_name.lower():
            # Power converter properties
            try:
                properties["current_setpoint"] = float(dev.current_setpoint)
            except:
                properties["current_setpoint"] = "N/A"
            try:
                properties["current_readback"] = float(dev.current_readback)
            except:
                properties["current_readback"] = "N/A"
        
        # Try to get status
        try:
            status = dev.command_inout("Status")
            properties["status"] = str(status)[:100]  # Truncate long status
        except:
            properties["status"] = "Status command not available"
        
        # Get device state
        try:
            state = dev.state()
            properties["state"] = str(state)
        except:
            properties["state"] = "Unknown"
        
        return json.dumps({
            "ok": True,
            "device": device_name,
            "properties": properties,
            "message": f"Read {len(properties)} properties from {device_name}"
        })
        
    except Exception as e:
        return json.dumps({"ok": False, "device": device_name, "error": str(e)})


@tool
def tango_set_multiple_magnet_properties(input_str: str) -> str:
    """
    Set multiple magnet properties at once (like your example).
    
    Args:
        input_str: JSON string with device_name and properties to set
        Example: '{"device_name": "SimpleTangoServer/test/magnet_Q3P2T6R", "x_position": 0.5, "y_position": 0.5, "k_strength": 1.0}'
    
    Returns:
        JSON with all set values and their readbacks
    """
    try:
        err = _need_pytango_error() or _need_tango_host_error()
        if err:
            return json.dumps({"ok": False, "error": err})
        
        data = json.loads(input_str)
        device_name = data.pop("device_name")  # Remove device_name, rest are properties
        
        dev = DeviceProxy(device_name)
        
        results = {}
        valid_properties = ["x_position", "y_position", "k_strength"]
        
        # Set each property
        for prop_name, prop_value in data.items():
            if prop_name in valid_properties:
                try:
                    # Set the property
                    setattr(dev, prop_name, float(prop_value))
                    # Read back
                    readback = getattr(dev, prop_name)
                    results[prop_name] = {
                        "set": float(prop_value),
                        "readback": float(readback)
                    }
                except Exception as e:
                    results[prop_name] = {
                        "set": float(prop_value),
                        "error": str(e)
                    }
            else:
                results[prop_name] = {
                    "error": f"Invalid property (valid: {valid_properties})"
                }
        
        return json.dumps({
            "ok": True,
            "device": device_name,
            "results": results,
            "message": f"Set {len(results)} properties on {device_name}"
        })
        
    except json.JSONDecodeError as e:
        return json.dumps({"ok": False, "error": f"Invalid JSON: {e}"})
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})


@tool
def tango_get_device_attributes_with_values(device_name: str) -> str:
    """
    Get complete attribute list with current values for a device.
    
    Args:
        device_name: Full Tango device name (e.g., "SimpleTangoServer/test/magnet_HS1MD1")
    
    Returns:
        JSON with all attributes and their current values
    """
    try:
        err = _need_pytango_error() or _need_tango_host_error()
        if err:
            return json.dumps({"ok": False, "error": err})
        
        dev = DeviceProxy(device_name)
        
        # Get all attributes
        all_attributes = list(dev.get_attribute_list())
        
        attributes_with_values = {}
        errors = {}
        
        for attr_name in all_attributes:
            try:
                # Get attribute info
                attr_info = dev.get_attribute_config(attr_name)
                attr_value = dev.read_attribute(attr_name)
                
                # Format value based on type
                value = attr_value.value
                if isinstance(value, float):
                    value_str = f"{value:.6f}"
                elif hasattr(value, '__iter__') and not isinstance(value, str):
                    # Handle arrays/lists
                    value_str = str(list(value))
                else:
                    value_str = str(value)
                
                attributes_with_values[attr_name] = {
                    "value": value_str,
                    "data_type": str(attr_info.data_type),
                    "writable": attr_info.writable != 0
                }
                
            except Exception as e:
                errors[attr_name] = str(e)
        
        return json.dumps({
            "ok": True,
            "device": device_name,
            "total_attributes": len(all_attributes),
            "successful_reads": len(attributes_with_values),
            "failed_reads": len(errors),
            "attributes": attributes_with_values,
            "errors": errors if errors else None,
            "message": f"Read {len(attributes_with_values)}/{len(all_attributes)} attributes successfully"
        })
        
    except Exception as e:
        return json.dumps({"ok": False, "device": device_name, "error": str(e)})


# Global tools registry for consistent access
ALL_TOOLS = [
    shell_tool,
    tango_list_devices,
    tango_list_registered_devices,
    tango_filter_devices,
    tango_ping_device,
    tango_get_device_attributes,
    tango_read_attribute,
    tango_write_attribute,
    tango_set_magnet_values,
    tango_read_magnet_values,
    tango_get_status,
    tango_check_system_health,
    tango_read_power_converter_setpoint,
    tango_set_power_converter_setpoint,
    tango_check_database_connection,
    tango_get_magnet_power_converter_relationships,
    tango_list_all_servers,
    tango_get_running_devices_categorized,
    tango_register_server_with_device,
    tango_get_device_attributes_with_values,
    tango_set_magnet_property,
    tango_set_power_converter_current,
    tango_verify_device_properties,
    tango_set_multiple_magnet_properties,
]

# Create tools lookup dictionary for efficient access
TOOLS_BY_NAME = {tool.name: tool for tool in ALL_TOOLS}


def validate_tool_result(result: str, tool_name: str) -> Dict[str, Any]:
    """Validate and parse tool results."""
    try:
        # Try to parse as JSON first
        parsed = json.loads(result)
        if isinstance(parsed, dict) and 'ok' in parsed:
            return parsed
        else:
            # Wrap non-standard results
            return {"ok": True, "tool": tool_name, "result": parsed}
    except json.JSONDecodeError:
        # Handle plain text results
        return {"ok": True, "tool": tool_name, "result": result}
    except Exception as e:
        return {"ok": False, "tool": tool_name, "error": str(e)}


def get_tool_usage_hints() -> str:
    """Get usage hints for available tools."""
    hints = []
    
    # Categorize tools for better understanding
    discovery_tools = [name for name in TOOLS_BY_NAME.keys() if 'list' in name or 'check' in name or 'ping' in name]
    info_tools = [name for name in TOOLS_BY_NAME.keys() if 'get' in name or 'read' in name or 'verify' in name]
    control_tools = [name for name in TOOLS_BY_NAME.keys() if 'set' in name or 'write' in name]
    
    hints.append(f"📡 Discovery ({len(discovery_tools)}): {', '.join(discovery_tools[:3])}...")
    hints.append(f"📊 Information ({len(info_tools)}): {', '.join(info_tools[:3])}...")
    hints.append(f"🎛️  Control ({len(control_tools)}): {', '.join(control_tools[:3])}...")
    
    return "\n".join(hints)


def build_agent(model: str = "llama-3.3-70b-versatile") -> Any:
    """Create an improved agent with better tool binding and error handling."""
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        # Fallback to hardcoded key for testing
        groq_api_key = "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"
        

    llm = ChatGroq(
        groq_api_key=groq_api_key,
        model_name=model,
        temperature=0.1,  # Slightly more creative but still controlled
        max_tokens=2048,  # Increased for better responses
        request_timeout=60  # Longer timeout for complex operations
    )

    # Use the global tools registry
    llm_with_tools = llm.bind_tools(ALL_TOOLS)
    
    print(f"✅ Using improved tool binding with {len(ALL_TOOLS)} tools")
    print(f"📋 Available tools: {', '.join([tool.name for tool in ALL_TOOLS[:5]])}... (+{len(ALL_TOOLS)-5} more)")
    return llm_with_tools


ENHANCED_SYSTEM_PROMPT = """You are an expert Tango Control System operator and assistant. Your role is to help users interact with Tango devices effectively and safely.

## TOOL USAGE GUIDELINES:

### Device Discovery & Status:
- `tango_check_database_connection`: Always start here if unsure about system status
- `tango_list_devices`: List currently running/exported devices  
- `tango_list_registered_devices`: List all devices registered in database
- `tango_get_running_devices_categorized`: Get organized view by device type
- `tango_ping_device`: Check if specific device is responding

### Device Information:
- `tango_get_device_attributes`: Get list of available attributes
- `tango_get_device_attributes_with_values`: Get attributes with current values
- `tango_verify_device_properties`: Read all key properties of a device
- `tango_get_status`: Get device state and status

### Device Control:
- `tango_read_attribute`: Read single attribute (format: "device,attribute")
- `tango_write_attribute`: Write single attribute (format: "device,attribute,value")
- `tango_set_multiple_magnet_properties`: Set multiple magnet properties at once
- `tango_set_magnet_property`: Set individual magnet property
- `tango_set_power_converter_current`: Set power converter current

### Parameter Formats:
- Single device name: Just the device name string
- Comma-separated: "device_name,attribute_name" or "device_name,attribute,value"  
- JSON format: Use for complex operations with multiple parameters

## RESPONSE GUIDELINES:
1. Always validate tool results before summarizing
2. Provide clear, actionable feedback to users
3. Report errors in plain language with suggested solutions
4. Include relevant technical details for operators
5. Structure responses with clear sections when appropriate
6. Always verify operations by reading back values after writes

## SAFETY:
- Confirm destructive operations before executing
- Always read current values before making changes
- Provide clear feedback about what changed
- Warn about potential issues or conflicts

You are helpful, precise, and safety-conscious in all operations.
"""


def run_interactive_mode():
    """Run the agent in interactive mode with improved tool execution."""
    from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
    
    print("=" * 60)
    print(" 🚀 Enhanced Tango Agent - Interactive Mode")
    print("=" * 60)
    print("I'm your intelligent Tango Control System assistant!")
    print("I can help with device discovery, monitoring, and control.")
    print("Type 'quit', 'exit', or 'bye' to exit.")
    print("Type 'help' to see available tool categories.\n")
    
    llm_with_tools = build_agent()
    
    # Initialize conversation with enhanced system message
    messages = [
        SystemMessage(content=ENHANCED_SYSTEM_PROMPT)
    ]
    
    while True:
        try:
            user_input = input("💬 You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("👋 Goodbye! Happy Tango operations!")
                break
            
            if user_input.lower() == 'help':
                print("\n📚 Available Tool Categories:")
                print(get_tool_usage_hints())
                print("\nExample commands:")
                print("• 'list all devices'")
                print("• 'check system health'") 
                print("• 'ping SimpleTangoServer/test/magnet_HS1MD1'")
                print("• 'read x_position from SimpleTangoServer/test/magnet_Q3P2T6R'")
                print("• 'set magnet properties x=0.5 y=0.5 k=1.0 on SimpleTangoServer/test/magnet_Q3P2T6R'\n")
                continue
            
            if not user_input:
                continue
            
            print("\n🔄 Processing your request...")
            
            # Add user message to conversation
            messages.append(HumanMessage(content=user_input))
            
            try:
                # Execute the conversation with tool support
                response = execute_with_tools(llm_with_tools, messages)
                print(f"\n🤖 Agent: {response}\n")
                
            except Exception as e:
                error_msg = str(e)
                if "tool_use_failed" in error_msg or "JSON" in error_msg:
                    print(f"\n❌ Tool Execution Error: {error_msg}")
                    print("💡 This might be due to invalid tool parameters or network issues.")
                    print("🔄 Try rephrasing your request or try again.")
                elif "BadRequestError" in error_msg or "API" in error_msg:
                    print(f"\n❌ API Error: {error_msg}")
                    print("💡 Check your API key and internet connection.")
                else:
                    print(f"\n❌ Unexpected Error: {e}")
                    print("🔧 Please try a simpler request or restart the agent.")
                    import traceback
                    traceback.print_exc()
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ System Error: {e}")


def execute_with_tools(llm_with_tools, messages: List[Any]) -> str:
    """Execute conversation with proper tool handling."""
    from langchain_core.messages import ToolMessage
    
    max_iterations = 5  # Prevent infinite loops
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        
        # Get AI response
        ai_message = llm_with_tools.invoke(messages)
        messages.append(ai_message)
        
        # Check if AI wants to call tools
        if not ai_message.tool_calls:
            # No tools needed, return the response
            return ai_message.content
        
        print(f"🔧 Executing {len(ai_message.tool_calls)} tool(s)...")
        
        # Execute each tool call
        for tool_call in ai_message.tool_calls:
            tool_name = tool_call['name']
            tool_args = tool_call['args']
            tool_id = tool_call.get('id', f"call_{iteration}_{tool_name}")
            
            print(f"  → {tool_name}({tool_args})")
            
            try:
                # Find and execute the tool using our registry
                if tool_name in TOOLS_BY_NAME:
                    tool = TOOLS_BY_NAME[tool_name]
                    
                    # Execute the tool
                    raw_result = tool.invoke(tool_args)
                    
                    # Handle result format
                    if hasattr(raw_result, 'content'):
                        result_content = raw_result.content
                    else:
                        result_content = str(raw_result)
                    
                    # Validate and format result
                    validated_result = validate_tool_result(result_content, tool_name)
                    
                    # Create tool message
                    tool_msg = ToolMessage(
                        content=json.dumps(validated_result, indent=2),
                        tool_call_id=tool_id
                    )
                    messages.append(tool_msg)
                    
                    # Show result summary
                    if validated_result.get('ok'):
                        print(f"    ✅ Success")
                    else:
                        print(f"    ❌ Error: {validated_result.get('error', 'Unknown error')}")
                        
                else:
                    # Tool not found
                    error_msg = ToolMessage(
                        content=json.dumps({
                            "ok": False, 
                            "error": f"Tool '{tool_name}' not found. Available: {list(TOOLS_BY_NAME.keys())[:5]}...",
                            "tool": tool_name
                        }),
                        tool_call_id=tool_id
                    )
                    messages.append(error_msg)
                    print(f"    ❌ Tool '{tool_name}' not found")
                    
            except Exception as e:
                # Tool execution failed
                error_msg = ToolMessage(
                    content=json.dumps({
                        "ok": False,
                        "error": str(e),
                        "tool": tool_name,
                        "args": tool_args
                    }),
                    tool_call_id=tool_id
                )
                messages.append(error_msg)
                print(f"    ❌ Execution failed: {str(e)[:100]}...")
        
        # Continue the loop to get final response
    
    # If we've hit max iterations, return what we have
    return "⚠️  Maximum tool iterations reached. Please try a simpler request."


def main():
    parser = argparse.ArgumentParser(description="Beautiful Tango Agent")
    parser.add_argument("query", nargs="?", help="Natural language query about Tango operations")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")
    parser.add_argument("--model", "-m", default="llama3-70b-8192", help="Groq model to use")
    
    args = parser.parse_args()
    
    if args.interactive:
        run_interactive_mode()
    elif args.query:
        from langchain_core.messages import HumanMessage, SystemMessage
        
        llm_with_tools = build_agent(args.model)
        
        # Create messages for single query with enhanced system prompt
        messages = [
            SystemMessage(content=ENHANCED_SYSTEM_PROMPT),
            HumanMessage(content=args.query)
        ]
        
        try:
            # Execute with improved tool handling
            result = execute_with_tools(llm_with_tools, messages)
            
            print("\n" + "="*60)
            print("🎯 ENHANCED TANGO AGENT RESPONSE")
            print("="*60)
            print(result)
            print("="*60)
            
        except Exception as e:
            print("\n" + "="*60)
            print("❌ EXECUTION ERROR")
            print("="*60)
            print(f"Error: {e}")
            print("💡 Try a simpler query or check your Tango environment setup.")
            print("="*60)
    else:
        print(__doc__)
        print("\n💡 Examples:")
        print("  python tango_exec_agent.py 'list all devices and summarize'")
        print("  python tango_exec_agent.py 'show devices with magnet_ in the name'")
        print("  python tango_exec_agent.py --interactive")


if __name__ == "__main__":
    main()
