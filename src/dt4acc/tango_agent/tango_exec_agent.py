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

@tool("tango_list_devices")
def tango_list_devices(pattern: str = "*") -> str:
    """
    List exported Tango devices by DB wildcard pattern.
    Examples: '*', 'SimpleTangoServer/test/*', 'beam_server/test/*'
    Returns JSON: {"ok": bool, "pattern": str, "devices": [..], "count": int, "error"?: str}
    """
    err = _need_pytango_error() or _need_tango_host_error()
    if err:
        return json.dumps({"ok": False, "pattern": pattern, "error": err})
    try:
        db = Database()
        devices = db.get_device_exported(pattern)
        # Convert to strings to ensure JSON serialization
        device_list = [str(device) for device in devices] if devices else []
        return json.dumps({
            "ok": True, 
            "pattern": pattern, 
            "devices": device_list,
            "count": len(device_list)
        })
    except Exception as e:
        return json.dumps({"ok": False, "pattern": pattern, "error": str(e)})


@tool("tango_list_registered_devices")
def tango_list_registered_devices() -> str:
    """
    List all registered devices (including non-running ones) from the database.
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


@tool("tango_filter_devices")
def tango_filter_devices(devices_json: str, substring: str) -> str:
    """
    Filter devices (JSON from tango_list_devices) by case-insensitive substring.
    Returns JSON: {"ok": bool, "substring": str, "devices": [..], "count": int, "error"?: str}
    """
    try:
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


@tool("tango_ping_device")
def tango_ping_device(device_name: str) -> str:
    """
    Ping a Tango device to check if it's responding.
    Returns JSON: {"ok": bool, "device": str, "responding": bool, "response_time_ms": float, "error"?: str}
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


@tool("tango_get_device_attributes")
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
        attributes = dev.get_attribute_list()
        return json.dumps({
            "ok": True, 
            "device": device_name, 
            "attributes": attributes,
            "count": len(attributes)
        })
    except Exception as e:
        return json.dumps({"ok": False, "device": device_name, "error": str(e)})


@tool("tango_read_attribute")
def tango_read_attribute(device_name: str, attribute_name: str) -> str:
    """
    Read a specific attribute value from a Tango device.
    Returns JSON: {"ok": bool, "device": str, "attribute": str, "value": str, "error"?: str}
    """
    err = _need_pytango_error() or _need_tango_host_error()
    if err:
        return json.dumps({"ok": False, "device": device_name, "error": err})
    try:
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
            "device": device_name, 
            "attribute": attribute_name,
            "error": str(e)
        })


@tool("tango_write_attribute")
def tango_write_attribute(device_name: str, attribute_name: str, value: str) -> str:
    """
    Write a value to a specific attribute on a Tango device.
    Returns JSON: {"ok": bool, "device": str, "attribute": str, "value": str, "error"?: str}
    """
    err = _need_pytango_error() or _need_tango_host_error()
    if err:
        return json.dumps({"ok": False, "device": device_name, "error": err})
    try:
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
            "device": device_name, 
            "attribute": attribute_name,
            "error": str(e)
        })


@tool("tango_set_magnet_values")
def tango_set_magnet_values(device_name: str, x: float, y: float, k: float) -> str:
    """
    Set magnet attributes on a device: x_position, y_position, k_strength.
    Returns JSON: {"ok": bool, "device": str, "set": {...}, "error"?: str}
    """
    err = _need_pytango_error() or _need_tango_host_error()
    if err:
        return json.dumps({"ok": False, "device": device_name, "error": err})
    try:
        dev = DeviceProxy(device_name)
        dev.x_position = float(x)
        dev.y_position = float(y)
        dev.k_strength = float(k)
        return json.dumps({
            "ok": True, 
            "device": device_name,
            "set": {"x_position": x, "y_position": y, "k_strength": k}
        })
    except Exception as e:
        return json.dumps({"ok": False, "device": device_name, "error": str(e)})


@tool("tango_read_magnet_values")
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


@tool("tango_get_status")
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


@tool("tango_check_system_health")
def tango_check_system_health() -> str:
    """
    Check the overall health of the Tango system.
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


@tool("tango_read_power_converter_setpoint")
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


@tool("tango_set_power_converter_setpoint")
def tango_set_power_converter_setpoint(device_name: str, setpoint_value: float) -> str:
    """
    Set power converter current_setpoint attribute.
    Returns JSON: {"ok": bool, "device": str, "setpoint": float, "error"?: str}
    """
    err = _need_pytango_error() or _need_tango_host_error()
    if err:
        return json.dumps({"ok": False, "device": device_name, "error": err})
    try:
        dev = DeviceProxy(device_name)
        dev.current_setpoint = float(setpoint_value)
        return json.dumps({
            "ok": True,
            "device": device_name,
            "setpoint": float(setpoint_value)
        })
    except Exception as e:
        return json.dumps({"ok": False, "device": device_name, "error": str(e)})


# A generic shell tool for when you say things like: "run `docker ps`"
shell_tool = ShellTool()


def build_agent(model: str = "llama-3.1-8b-instant") -> Any:
    """Create a beautiful agent that:
    - Interprets human text naturally
    - Decides which tools to call and in what order
    - Produces polished human summaries
    """
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        print("❌ GROQ_API_KEY environment variable is required")
        print("Get your API key from: https://console.groq.com/")
        sys.exit(1)

    llm = ChatGroq(
        groq_api_key=groq_api_key,
        model_name=model,
        temperature=0.2
    )

    tools = [
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
    ]

    # Use ZERO_SHOT_REACT_DESCRIPTION with simplified tools (more reliable with Groq)
    from langchain.tools import Tool
    
    simplified_tools = [
        shell_tool,
        Tool(
            name="list_devices",
            func=lambda pattern: tango_list_devices(pattern.strip("'\"") if pattern else "*"),
            description="List Tango devices by pattern. Input: pattern string (default: '*')"
        ),
        Tool(
            name="list_registered_devices", 
            func=lambda: tango_list_registered_devices(),
            description="List all registered Tango devices. No input needed."
        ),
        Tool(
            name="filter_devices",
            func=lambda input_str: tango_filter_devices(*input_str.split(',', 1)),
            description="Filter devices by substring. Input: 'devices_json,substring'"
        ),
        Tool(
            name="ping_device",
            func=lambda device_name: tango_ping_device(device_name),
            description="Ping a Tango device. Input: device_name string"
        ),
        Tool(
            name="get_device_attributes",
            func=lambda device_name: tango_get_device_attributes(device_name),
            description="Get device attributes. Input: device_name string"
        ),
        Tool(
            name="read_attribute",
            func=lambda input_str: tango_read_attribute(*input_str.split(',', 1)),
            description="Read device attribute. Input: 'device_name,attribute_name'"
        ),
        Tool(
            name="write_attribute",
            func=lambda input_str: tango_write_attribute(*input_str.split(',', 2)),
            description="Write device attribute. Input: 'device_name,attribute_name,value'"
        ),
        Tool(
            name="set_magnet_values",
            func=lambda input_str: tango_set_magnet_values(*input_str.split(',', 3)),
            description="Set magnet values. Input: 'device_name,x,y,k'"
        ),
        Tool(
            name="read_magnet_values",
            func=lambda device_name: tango_read_magnet_values(device_name),
            description="Read magnet values. Input: device_name string"
        ),
        Tool(
            name="get_status",
            func=lambda device_name: tango_get_status(device_name),
            description="Get device status. Input: device_name string"
        ),
        Tool(
            name="check_system_health",
            func=lambda: tango_check_system_health(),
            description="Check Tango system health. No input needed."
        ),
        Tool(
            name="read_power_converter_setpoint",
            func=lambda device_name: tango_read_power_converter_setpoint(device_name),
            description="Read power converter current_setpoint. Input: device_name string"
        ),
        Tool(
            name="set_power_converter_setpoint",
            func=lambda input_str: tango_set_power_converter_setpoint(*input_str.split(',', 1)),
            description="Set power converter current_setpoint. Input: 'device_name,setpoint_value'"
        ),
    ]
    
    agent = initialize_agent(
        tools=simplified_tools,
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=3,
        early_stopping_method="generate",
    )
    print(f"✅ Using ZERO_SHOT_REACT_DESCRIPTION agent with {len(simplified_tools)} tools")
    return agent


SYSTEM_HINT = """You are a helpful Tango device operator. You MUST use tools to get information and then provide a beautiful, human-readable summary.

CRITICAL RULES:
1. After getting the answer from a tool, provide a summary and STOP
2. Do NOT call additional tools unless the user specifically asks for more information
3. Always end with "Final Answer:" followed by your summary

When user asks to read power converter setpoint:
1. Use "read_power_converter_setpoint" tool
2. Interpret the JSON response
3. Provide a clear summary with the value
4. End with "Final Answer:" and STOP

When user asks to "list devices" or "list all devices":
1. Use the "list_devices" tool with pattern "*"
2. Interpret the JSON response
3. Provide a beautiful summary like: "I found 565 devices in your Tango system including magnets, power converters, cavities, and more..."
4. End with "Final Answer:" and STOP

When user asks about device status or health:
1. Use the "check_system_health" tool
2. Interpret the JSON response
3. Report system status clearly
4. End with "Final Answer:" and STOP

Always end with "Final Answer:" followed by a clear, helpful summary that humans can easily understand.
"""


def run_interactive_mode():
    """Run the agent in interactive chat mode."""
    print("🤖 Beautiful Tango Agent - Interactive Mode")
    print("=" * 50)
    print("Just chat naturally! I'll help with Tango devices and system operations.")
    print("Type 'quit' to exit.\n")
    
    agent = build_agent()
    
    while True:
        try:
            user_input = input("💬 You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("👋 Goodbye! Happy Tango operations!")
                break
            
            if not user_input:
                continue
            
            print("\n🔄 Processing your request...")
            response = agent.invoke({"input": f"{SYSTEM_HINT}\n\nUser request: {user_input}"})
            print(f"\n🤖 Agent: {response['output']}\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


def main():
    parser = argparse.ArgumentParser(description="Beautiful Tango Agent")
    parser.add_argument("query", nargs="?", help="Natural language query about Tango operations")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")
    parser.add_argument("--model", "-m", default="llama-3.1-8b-instant", help="Groq model to use")
    
    args = parser.parse_args()
    
    if args.interactive:
        run_interactive_mode()
    elif args.query:
        agent = build_agent(args.model)
        response = agent.invoke({"input": f"{SYSTEM_HINT}\n\nUser request: {args.query}"})
        print("\n" + "="*60)
        print("🎯 BEAUTIFUL SUMMARY")
        print("="*60)
        print(response['output'])
    else:
        print(__doc__)
        print("\n💡 Examples:")
        print("  python tango_exec_agent.py 'list all devices and summarize'")
        print("  python tango_exec_agent.py 'show devices with magnet_ in the name'")
        print("  python tango_exec_agent.py --interactive")


if __name__ == "__main__":
    main()
