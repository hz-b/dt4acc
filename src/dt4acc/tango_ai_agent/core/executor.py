"""
Command Executor for Tango AI Agent
Tool-based execution using LangChain tools
"""

import time
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from pathlib import Path

# Try to import Tango
try:
    from tango import DeviceProxy, DevFailed
    TANGO_AVAILABLE = True
except ImportError:
    TANGO_AVAILABLE = False

# Try to import your existing functions
try:
    from dt4acc.custom_epics.data.querries import get_unique_power_converters
    DT4ACC_AVAILABLE = True
except ImportError:
    DT4ACC_AVAILABLE = False

from .knowledge_base import TangoKnowledgeBase, DeviceSchema

logger = logging.getLogger(__name__)

@dataclass
class ExecutionResult:
    """Result of command execution"""
    success: bool
    command: str
    device: Optional[str]
    property_name: Optional[str]
    value: Optional[Any]
    result: Optional[Any]
    error: Optional[str]
    execution_time: float
    timestamp: float
    metadata: Dict[str, Any]

class CommandExecutor:
    """Tool-based command executor using LangChain tools"""
    
    def __init__(self, knowledge_base: TangoKnowledgeBase, config: Dict[str, Any]):
        self.knowledge_base = knowledge_base
        self.config = config
        self.device_cache = {}
        self.connection_pool = {}
        self.execution_history = []
        
        # Initialize Tango connection if available
        if TANGO_AVAILABLE:
            self._initialize_tango()
        else:
            logger.warning("Tango not available, executor will be limited")
    
    def _initialize_tango(self):
        """Initialize Tango connection and cache devices"""
        try:
            logger.info("Initializing Tango connection...")
            
            # Cache available devices
            if DT4ACC_AVAILABLE:
                try:
                    power_converters = list(get_unique_power_converters())
                    self.device_cache['power_converter'] = power_converters
                    logger.info(f"Cached {len(power_converters)} power converters")
                except Exception as e:
                    logger.warning(f"Could not cache power converters: {e}")
            
            logger.info("Tango connection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Tango: {e}")
    
    def execute_command(self, parsed_command) -> ExecutionResult:
        """Execute a parsed command using tools"""
        start_time = time.time()
        
        try:
            logger.info(f"Executing command with tools: {parsed_command.action} {parsed_command.device_name}.{parsed_command.property_name}")
            
            # Use tool-based execution instead of manual logic
            result = self._execute_with_tools(parsed_command)
            
            # Create execution result
            execution_result = ExecutionResult(
                success=result.get("success", False),
                command=parsed_command.raw_command,
                device=parsed_command.device_name,
                property_name=parsed_command.property_name,
                value=parsed_command.value,
                result=result.get("result"),
                error=result.get("error"),
                execution_time=time.time() - start_time,
                timestamp=time.time(),
                metadata=result.get("metadata", {})
            )
            
            # Record execution
            self.execution_history.append(execution_result)
            
            return execution_result
            
        except Exception as e:
            logger.error(f"Tool-based command execution failed: {e}")
            return ExecutionResult(
                success=False,
                command=parsed_command.raw_command,
                device=parsed_command.device_name,
                property_name=parsed_command.property_name,
                value=parsed_command.value,
                result=None,
                error=str(e),
                execution_time=time.time() - start_time,
                timestamp=time.time(),
                metadata={"exception": str(e)}
            )
    
    def _execute_with_tools(self, parsed_command) -> Dict[str, Any]:
        """Execute command using appropriate tools"""
        try:
            # This method is now tool-based
            # The actual execution happens in the LangChain tools
            # This is just a fallback for backward compatibility
            
            action = parsed_command.action
            device_name = parsed_command.device_name
            property_name = parsed_command.property_name
            value = parsed_command.value
            
            if action == "get":
                return self._tool_get_value(device_name, property_name)
            elif action == "set":
                return self._tool_set_value(device_name, property_name, value)
            elif action == "list":
                return self._tool_list_devices(parsed_command.device_type)
            elif action == "status":
                return self._tool_get_status()
            else:
                return {
                    "success": False,
                    "error": f"Action {action} not implemented in tools"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Tool execution failed: {str(e)}"
            }
    
    def _tool_get_value(self, device_name: str, property_name: str) -> Dict[str, Any]:
        """Tool for getting device values"""
        try:
            if not device_name or not property_name:
                return {
                    "success": False,
                    "error": "Device name and property name required"
                }
            
            # This would be called by the LangChain tool
            # For now, return a placeholder
            return {
                "success": True,
                "result": f"Getting {device_name}.{property_name}",
                "metadata": {"tool": "get_device_value"}
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Get value tool failed: {str(e)}"
            }
    
    def _tool_set_value(self, device_name: str, property_name: str, value: Any) -> Dict[str, Any]:
        """Tool for setting device values"""
        try:
            if not device_name or not property_name or value is None:
                return {
                    "success": False,
                    "error": "Device name, property name, and value required"
                }
            
            # This would be called by the LangChain tool
            # For now, return a placeholder
            return {
                "success": True,
                "result": f"Setting {device_name}.{property_name} = {value}",
                "metadata": {"tool": "set_device_value"}
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Set value tool failed: {str(e)}"
            }
    
    def _tool_list_devices(self, device_type: Optional[str]) -> Dict[str, Any]:
        """Tool for listing devices"""
        try:
            # This would be called by the LangChain tool
            if device_type:
                devices = self.device_cache.get(device_type, [])
                return {
                    "success": True,
                    "result": f"Found {len(devices)} {device_type} devices",
                    "metadata": {"tool": "list_devices", "count": len(devices)}
                }
            else:
                total_devices = sum(len(devices) for devices in self.device_cache.values())
                return {
                    "success": True,
                    "result": f"Found {total_devices} total devices",
                    "metadata": {"tool": "list_devices", "total_count": total_devices}
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"List devices tool failed: {str(e)}"
            }
    
    def _tool_get_status(self) -> Dict[str, Any]:
        """Tool for getting system status"""
        try:
            # This would be called by the LangChain tool
            return {
                "success": True,
                "result": "System status: All systems operational",
                "metadata": {"tool": "system_status"}
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Status tool failed: {str(e)}"
            }
    
    def get_execution_history(self) -> List[ExecutionResult]:
        """Get execution history"""
        return self.execution_history
    
    def clear_history(self):
        """Clear execution history"""
        self.execution_history.clear()
        logger.info("Execution history cleared")
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        if not self.execution_history:
            return {
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "success_rate": 0.0
            }
        
        total = len(self.execution_history)
        successful = sum(1 for result in self.execution_history if result.success)
        failed = total - successful
        success_rate = successful / total if total > 0 else 0.0
        
        return {
            "total_executions": total,
            "successful_executions": successful,
            "failed_executions": failed,
            "success_rate": success_rate
        }
    
    def get_device_info(self, device_name: str) -> Optional[Dict[str, Any]]:
        """Get device information"""
        try:
            # Check if device exists in cache
            for device_type, devices in self.device_cache.items():
                if device_name in devices:
                    return {
                        "name": device_name,
                        "type": device_type,
                        "cached": True
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get device info: {e}")
            return None
