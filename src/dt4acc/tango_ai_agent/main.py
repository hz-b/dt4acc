#!/usr/bin/env python3
"""
Main launcher for Tango AI Agent
Interactive command-line interface for controlling Tango devices
"""

import os
import sys
import json
import time
import logging
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(src_path))

from dt4acc.tango_ai_agent.core.agent import TangoAIAgent
from dt4acc.tango_ai_agent.core.config import load_config

def print_banner():
    """Print the agent banner"""
    print("🤖" + "=" * 60 + "🤖")
    print("🚀 TANGO AI AGENT - Advanced Particle Accelerator Control")
    print("🎯 Natural Language Commands for Tango Devices")
    print("🔒 Built-in Safety and Validation")
    print("🧠 Powered by LangChain and LLMs")
    print("🤖" + "=" * 60 + "🤖")
    print()

def print_help():
    """Print help information"""
    print("📚 AVAILABLE COMMANDS:")
    print("  Basic Operations:")
    print("    help                    - Show this help")
    print("    status                  - Show agent status")
    print("    test                    - Test Tango connection")
    print("    commands                - List available commands")
    print("    devices                 - List available devices")
    print("    safety                  - Show safety information")
    print("    history                 - Show command history")
    print("    clear                   - Clear history")
    print("    quit/exit               - Exit the agent")
    print()
    print("  Natural Language Commands:")
    print("    'set Q3P2T6R current to 5.1A'")
    print("    'get Q1M1T1R strength'")
    print("    'list all power converters'")
    print("    'show status of Q3P2T6R'")
    print("    'what is the current of Q2M1T1R?'")
    print()
    print("  Advanced Operations:")
    print("    'monitor Q3P2T6R'       - Start monitoring device")
    print("    'calculate beam optics' - Trigger calculations")
    print("    'validate command'      - Validate without execution")
    print()

def print_status(agent: TangoAIAgent):
    """Print agent status"""
    status = agent.get_agent_status()
    
    print("📊 AGENT STATUS:")
    print(f"  Name: {status['agent']['name']}")
    print(f"  Version: {status['agent']['version']}")
    print(f"  Uptime: {status['agent']['uptime']:.1f} seconds")
    print()
    
    print("📈 STATISTICS:")
    print(f"  Total Commands: {status['statistics']['total_commands']}")
    print(f"  Successful: {status['statistics']['successful_commands']}")
    print(f"  Failed: {status['statistics']['failed_commands']}")
    print(f"  Success Rate: {status['statistics']['success_rate']:.1%}")
    print()
    
    print("🔧 COMPONENTS:")
    print(f"  Knowledge Base: {status['components']['knowledge_base']['total_devices']} devices, {status['components']['knowledge_base']['total_commands']} commands")
    print(f"  Command Parser: LangChain {'✓' if status['components']['command_parser']['langchain_available'] else '✗'}")
    print(f"  Command Executor: {status['components']['command_executor']['success_rate']:.1%} success rate")
    print()
    
    print("⚙️  CONFIGURATION:")
    print(f"  LLM Provider: {status['configuration']['llm_provider']}")
    print(f"  LLM Model: {status['configuration']['llm_model']}")
    print(f"  Tango Server: {status['configuration']['tango_server']}")
    print(f"  Safety Enabled: {'✓' if status['configuration']['safety_enabled'] else '✗'}")

def print_test_results(agent: TangoAIAgent):
    """Print connection test results"""
    test_results = agent.test_connection()
    
    print("🔍 CONNECTION TEST RESULTS:")
    print(f"  Tango Available: {'✓' if test_results['tango_available'] else '✗'}")
    print(f"  dt4acc Available: {'✓' if test_results['dt4acc_available'] else '✗'}")
    print(f"  Device Connection: {'✓' if test_results['device_connection'] else '✗'}")
    print(f"  Knowledge Base: {'✓' if test_results['knowledge_base'] else '✗'}")
    print(f"  Overall Status: {test_results['overall_status']}")
    
    if 'error' in test_results:
        print(f"  Error: {test_results['error']}")
    print()

def print_commands(agent: TangoAIAgent):
    """Print available commands"""
    commands = agent.get_available_commands()
    
    print("📋 AVAILABLE COMMANDS:")
    for cmd in commands:
        print(f"\n  {cmd['name']}:")
        print(f"    Description: {cmd['description']}")
        print(f"    Examples: {', '.join(cmd['examples'])}")
        if cmd['safety_notes']:
            print(f"    Safety: {', '.join(cmd['safety_notes'])}")

def print_devices(agent: TangoAIAgent):
    """Print available devices"""
    devices = agent.get_available_devices()
    
    print("🔌 AVAILABLE DEVICES:")
    for device in devices:
        print(f"\n  {device['name']} ({device['type']}):")
        print(f"    Description: {device['description']}")
        print(f"    Attributes: {', '.join(device['attributes'])}")
        if device['safety_limits']:
            print(f"    Safety Limits: {device['safety_limits']}")

def print_safety_info(agent: TangoAIAgent):
    """Print safety information"""
    safety_info = agent.get_safety_info()
    
    print("🔒 SAFETY INFORMATION:")
    print(f"  Safety Checks: {'✓' if safety_info['safety_enabled'] else '✗'}")
    print(f"  Limits Enabled: {'✓' if safety_info['limits_enabled'] else '✗'}")
    print()
    
    print("📏 SAFETY LIMITS:")
    for limit_name, limit_value in safety_info['limits'].items():
        print(f"  {limit_name}: {limit_value}")
    print()
    
    print("⚠️  CONFIRMATION REQUIRED FOR:")
    for item in safety_info['confirmation_required']:
        print(f"  - {item}")

def print_history(agent: TangoAIAgent):
    """Print command history"""
    history = agent.get_command_history()
    
    if not history:
        print("📜 No commands executed yet.")
        return
    
    print("📜 COMMAND HISTORY:")
    for i, entry in enumerate(history[-10:], 1):  # Show last 10 commands
        timestamp = time.strftime('%H:%M:%S', time.localtime(entry['timestamp']))
        status = "✅" if entry['success'] else "❌"
        print(f"  {i:2d}. [{timestamp}] {status} {entry['command']}")
        if entry['error']:
            print(f"       Error: {entry['error']}")
        print(f"       Time: {entry['execution_time']:.3f}s")

def process_command(agent: TangoAIAgent, command: str):
    """Process a command and display results"""
    if not command.strip():
        return
    
    # Handle built-in commands
    if command.lower() in ['help', 'h', '?']:
        print_help()
        return
    
    if command.lower() in ['status', 's']:
        print_status(agent)
        return
    
    if command.lower() in ['test', 't']:
        print_test_results(agent)
        return
    
    if command.lower() in ['commands', 'cmd']:
        print_commands(agent)
        return
    
    if command.lower() in ['devices', 'dev']:
        print_devices(agent)
        return
    
    if command.lower() in ['safety', 'safe']:
        print_safety_info(agent)
        return
    
    if command.lower() in ['history', 'hist']:
        print_history(agent)
        return
    
    if command.lower() in ['clear', 'cls']:
        agent.clear_history()
        print("🧹 History cleared.")
        return
    
    if command.lower() in ['quit', 'exit', 'q']:
        print("👋 Goodbye!")
        return 'quit'
    
    # Process natural language command
    print(f"\n🤖 Processing: {command}")
    print("-" * 50)
    
    try:
        result = agent.process_command(command)
        
        if result['success']:
            print("✅ Command executed successfully!")
            
            # Display execution result
            exec_result = result['execution_result']
            if exec_result['result']:
                if 'message' in exec_result['result']:
                    print(f"📝 {exec_result['result']['message']}")
                elif 'value' in exec_result['result']:
                    print(f"📊 {exec_result['result']['device']}.{exec_result['result']['property']} = {exec_result['result']['value']} {exec_result['result'].get('unit', '')}")
                elif 'devices' in exec_result['result']:
                    print(f"📋 Found {exec_result['result']['count']} {exec_result['result']['device_type']} devices")
                    for device in exec_result['result']['devices'][:5]:  # Show first 5
                        print(f"    - {device}")
                    if exec_result['result']['count'] > 5:
                        print(f"    ... and {exec_result['result']['count'] - 5} more")
                else:
                    print(f"📊 Result: {exec_result['result']}")
            
            print(f"⏱️  Execution time: {exec_result['execution_time']:.3f}s")
            
        else:
            print(f"❌ Command failed: {exec_result['error']}")
            
            # Show parsed command for debugging
            if 'parsed_command' in result:
                parsed = result['parsed_command']
                print(f"🔍 Parsed as: {parsed['action']} {parsed['device_name']}.{parsed['property_name']}")
                print(f"   Confidence: {parsed['confidence']:.1%}")
        
        print(f"⏱️  Total processing time: {result['processing_time']:.3f}s")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        logging.error(f"Command processing error: {e}")

def main():
    """Main function"""
    print_banner()
    
    # Check if configuration file exists
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        print("⚠️  No configuration file found, using defaults.")
        print("   Create config.yaml for custom settings.")
        print()
    
    try:
        # Initialize the agent
        print("🚀 Initializing Tango AI Agent...")
        agent = TangoAIAgent(config_path if config_path.exists() else None)
        print("✅ Agent initialized successfully!")
        print()
        
        # Test connection
        print("🔍 Testing connections...")
        test_results = agent.test_connection()
        if test_results['overall_status'] == 'HEALTHY':
            print("✅ All systems operational!")
        elif test_results['overall_status'] == 'PARTIAL':
            print("⚠️  Partial functionality available")
        else:
            print("❌ System issues detected")
        print()
        
        # Show initial help
        print_help()
        
        # Main command loop
        while True:
            try:
                command = input("\n🤖 Enter command: ").strip()
                
                if not command:
                    continue
                
                result = process_command(agent, command)
                if result == 'quit':
                    break
                    
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except EOFError:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Unexpected error: {e}")
                logging.error(f"Main loop error: {e}")
        
        # Shutdown
        agent.shutdown()
        
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        logging.error(f"Initialization error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
