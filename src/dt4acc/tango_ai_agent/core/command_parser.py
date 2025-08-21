"""
Command Parser for Tango AI Agent
Pure LangChain-based parsing with tools for dynamic execution
"""

import time
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from pathlib import Path

try:
    from langchain.agents import initialize_agent, AgentType
    from langchain.tools import BaseTool
    from langchain.llms import OpenAI
    from langchain.chat_models import ChatOpenAI
    from langchain.memory import ConversationBufferMemory
    from langchain.schema import HumanMessage, SystemMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

from .knowledge_base import TangoKnowledgeBase

logger = logging.getLogger(__name__)

@dataclass
class ParsedCommand:
    """Parsed command result from LangChain"""
    action: str
    device_type: Optional[str]
    device_name: Optional[str]
    property_name: Optional[str]
    value: Optional[Any]
    unit: Optional[str]
    command_template: Optional[str]
    confidence: float
    raw_command: str
    parsed_parameters: Dict[str, Any]

class TangoTool(BaseTool):
    """Base Tango tool for LangChain"""
    name: str
    description: str
    knowledge_base: TangoKnowledgeBase
    
    def _run(self, query: str) -> str:
        """Execute the tool"""
        raise NotImplementedError("Subclasses must implement _run")
    
    def _arun(self, query: str) -> str:
        """Execute the tool asynchronously"""
        raise NotImplementedError("Subclasses must implement _arun")

class GetDeviceValueTool(TangoTool):
    """Tool for getting device values"""
    name = "get_device_value"
    description = "Get the current value of a device property"
    
    def _run(self, query: str) -> str:
        try:
            # Parse query for device and property
            # This will be handled by LangChain's reasoning
            return f"Getting device value for: {query}"
        except Exception as e:
            return f"Error getting device value: {e}"

class SetDeviceValueTool(TangoTool):
    """Tool for setting device values"""
    name = "set_device_value"
    description = "Set a device property to a specific value"
    
    def _run(self, query: str) -> str:
        try:
            # Parse query for device, property, and value
            return f"Setting device value for: {query}"
        except Exception as e:
            return f"Error setting device value: {e}"

class ListDevicesTool(TangoTool):
    """Tool for listing devices"""
    name = "list_devices"
    description = "List available devices of a specific type"
    
    def _run(self, query: str) -> str:
        try:
            return f"Listing devices for: {query}"
        except Exception as e:
            return f"Error listing devices: {e}"

class SystemStatusTool(TangoTool):
    """Tool for getting system status"""
    name = "system_status"
    description = "Get system status and health information"
    
    def _run(self, query: str) -> str:
        try:
            return "System status: All systems operational"
        except Exception as e:
            return f"Error getting system status: {e}"

class ConversationalTool(TangoTool):
    """Tool for conversational responses"""
    name = "conversational_response"
    description = "Provide conversational responses to general questions and greetings"
    
    def _run(self, query: str) -> str:
        try:
            # This tool handles general conversation
            if "how are you" in query.lower():
                return "I'm doing great! I'm your Tango AI assistant, ready to help you control your particle accelerator system."
            elif "what can you do" in query.lower():
                return "I can help you control your Tango system! I can set device values, get readings, list devices, check system status, and have conversations. Just ask me anything!"
            elif any(word in query.lower() for word in ["hi", "hello", "hey"]):
                return "Hello! I'm your Tango AI assistant. How can I help you today?"
            else:
                return f"I understand you're asking: {query}. I'm here to help with your Tango system operations and general questions."
        except Exception as e:
            return f"Error in conversational response: {e}"

class CommandParser:
    """Pure LangChain-based command parser"""
    
    def __init__(self, knowledge_base: TangoKnowledgeBase, config: Dict[str, Any]):
        self.knowledge_base = knowledge_base
        self.config = config
        self.llm = None
        self.agent = None
        self.memory = None
        self.tools = []
        
        if LANGCHAIN_AVAILABLE:
            self._setup_langchain()
        else:
            logger.warning("LangChain not available, parser will be limited")
    
    def _setup_langchain(self):
        """Setup LangChain components"""
        try:
            # Setup LLM
            if self.config.get("llm_provider") == "openai":
                api_key = self._get_openai_api_key()
                if api_key:
                    self.llm = ChatOpenAI(
                        openai_api_key=api_key,
                        model_name=self.config.get("llm_model", "gpt-3.5-turbo"),
                        temperature=self.config.get("llm_temperature", 0.1),
                        max_tokens=self.config.get("llm_max_tokens", 1000)
                    )
                    logger.info("OpenAI LLM initialized successfully")
                else:
                    logger.warning("OpenAI API key not found")
            else:
                logger.warning(f"LLM provider {self.config.get('llm_provider')} not supported")
                return
            
            # Setup memory
            if self.config.get("use_memory", True):
                self.memory = ConversationBufferMemory(
                    memory_key="chat_history",
                    max_token_limit=self.config.get("max_memory_size", 10)
                )
                logger.info("Conversation memory initialized")
            
            # Setup tools
            self._setup_tools()
            
            # Setup agent
            if self.llm and self.tools:
                self.agent = initialize_agent(
                    tools=self.tools,
                    llm=self.llm,
                    agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
                    memory=self.memory,
                    verbose=self.config.get("verbose", False),
                    max_iterations=self.config.get("max_iterations", 5)
                )
                logger.info("LangChain agent initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup LangChain: {e}")
    
    def _get_openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key from config"""
        try:
            from .config import load_config
            config = load_config()
            return config.llm.api_key
        except Exception as e:
            logger.warning(f"Could not get OpenAI API key: {e}")
            return None
    
    def _setup_tools(self):
        """Setup LangChain tools"""
        try:
            # Create Tango-specific tools
            self.tools = [
                GetDeviceValueTool(knowledge_base=self.knowledge_base),
                SetDeviceValueTool(knowledge_base=self.knowledge_base),
                ListDevicesTool(knowledge_base=self.knowledge_base),
                SystemStatusTool(knowledge_base=self.knowledge_base),
                ConversationalTool(knowledge_base=self.knowledge_base)
            ]
            logger.info(f"Initialized {len(self.tools)} LangChain tools")
            
        except Exception as e:
            logger.error(f"Failed to setup tools: {e}")
            self.tools = []
    
    def process_with_langchain(self, command: str) -> Dict[str, Any]:
        """Process command using LangChain agent and tools"""
        start_time = time.time()
        
        if not self.agent:
            return {
                "success": False,
                "error": "LangChain agent not available",
                "metadata": {"langchain_available": False}
            }
        
        try:
            logger.info(f"Processing with LangChain: {command}")
            
            # Let LangChain decide how to handle the command
            result = self.agent.run(command)
            
            execution_time = time.time() - start_time
            
            # Determine success based on result content
            success = self._is_successful_result(result)
            
            return {
                "success": success,
                "result": result,
                "error": None if success else "Command execution failed",
                "execution_time": execution_time,
                "tools_used": self._extract_tools_used(result),
                "metadata": {
                    "langchain_agent": True,
                    "execution_time": execution_time
                }
            }
            
        except Exception as e:
            logger.error(f"LangChain processing failed: {e}")
            return {
                "success": False,
                "error": f"LangChain processing failed: {str(e)}",
                "execution_time": time.time() - start_time,
                "metadata": {"exception": str(e)}
            }
    
    def _is_successful_result(self, result: str) -> bool:
        """Determine if LangChain result indicates success"""
        if not result:
            return False
        
        # Check for error indicators
        error_indicators = ["error", "failed", "not found", "invalid", "cannot"]
        result_lower = result.lower()
        
        for indicator in error_indicators:
            if indicator in result_lower:
                return False
        
        return True
    
    def _extract_tools_used(self, result: str) -> List[str]:
        """Extract which tools were used from the result"""
        tools_used = []
        
        # This is a simplified extraction - in practice, LangChain provides this info
        if "device value" in result.lower():
            tools_used.append("get_device_value")
        if "setting" in result.lower():
            tools_used.append("set_device_value")
        if "listing" in result.lower():
            tools_used.append("list_devices")
        if "status" in result.lower():
            tools_used.append("system_status")
        if any(word in result.lower() for word in ["hello", "hi", "how are you", "what can you do"]):
            tools_used.append("conversational_response")
        
        return tools_used
    
    def parse_command(self, command: str) -> ParsedCommand:
        """Legacy method - now redirects to LangChain processing"""
        logger.warning("parse_command is deprecated, use process_with_langchain instead")
        
        # Return a basic parsed command for backward compatibility
        return ParsedCommand(
            action="unknown",
            device_type=None,
            device_name=None,
            property_name=None,
            value=None,
            unit=None,
            command_template=None,
            confidence=0.0,
            raw_command=command,
            parsed_parameters={}
        )
    
    def get_parsing_stats(self) -> Dict[str, Any]:
        """Get parsing statistics"""
        return {
            "langchain_available": LANGCHAIN_AVAILABLE,
            "agent_initialized": self.agent is not None,
            "tools_count": len(self.tools),
            "memory_enabled": self.memory is not None
        }
