"""
Main Tango AI Agent Class
Pure LangChain-based agent with tools for dynamic execution
"""

import time
import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from .config import AgentConfig, load_config
from .knowledge_base import TangoKnowledgeBase
from .command_parser import CommandParser, ParsedCommand
from .executor import CommandExecutor, ExecutionResult

logger = logging.getLogger(__name__)

class TangoAIAgent:
    """Pure LangChain-based Tango AI Agent"""
    
    def __init__(self, config: Optional[Union[AgentConfig, str, Path]] = None):
        """Initialize the Tango AI Agent"""
        # Load configuration
        if isinstance(config, (str, Path)):
            self.config = load_config(config)
        elif isinstance(config, AgentConfig):
            self.config = config
        else:
            self.config = load_config()
        
        # Setup logging
        self._setup_logging()
        
        # Initialize components
        self.knowledge_base = TangoKnowledgeBase(self.config.knowledge_base_path)
        self.command_parser = CommandParser(self.knowledge_base, self._get_parser_config())
        self.command_executor = CommandExecutor(self.knowledge_base, self._get_executor_config())
        
        # Agent state
        self.session_start_time = time.time()
        self.total_commands_processed = 0
        self.successful_commands = 0
        self.failed_commands = 0
        
        logger.info(f"Tango AI Agent initialized: {self.config.name} v{self.config.version}")
        logger.info(f"Knowledge base: {self.knowledge_base.get_knowledge_summary()}")
    
    def _setup_logging(self):
        """Setup logging configuration"""
        log_level = getattr(logging, self.config.logging.level.upper(), logging.INFO)
        logging.basicConfig(level=log_level)
        
        # Setup file logging if specified
        if self.config.logging.file_path:
            from logging.handlers import RotatingFileHandler
            
            file_handler = RotatingFileHandler(
                self.config.logging.file_path,
                maxBytes=self.config.logging.max_file_size,
                backupCount=self.config.logging.backup_count
            )
            
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            
            # Add to root logger
            logging.getLogger().addHandler(file_handler)
    
    def _get_parser_config(self) -> Dict[str, Any]:
        """Get configuration for command parser"""
        return {
            "llm_provider": self.config.llm.provider,
            "llm_model": self.config.llm.model,
            "llm_temperature": self.config.llm.temperature,
            "llm_max_tokens": self.config.llm.max_tokens,
            "use_memory": self.config.langchain.use_memory,
            "memory_type": self.config.langchain.memory_type,
            "max_memory_size": self.config.langchain.max_memory_size,
            "verbose": self.config.langchain.verbose
        }
    
    def _get_executor_config(self) -> Dict[str, Any]:
        """Get configuration for command executor"""
        return {
            "tango": {
                "device_prefix": self.config.tango.device_prefix,
                "timeout": self.config.tango.timeout,
                "retry_attempts": self.config.tango.retry_attempts,
                "connection_pool_size": self.config.tango.connection_pool_size
            },
            "safety": {
                "enable_safety_checks": self.config.safety.enable_safety_checks,
                "enable_limits": self.config.safety.enable_limits,
                "max_current": self.config.safety.max_current,
                "max_voltage": self.config.safety.max_voltage,
                "max_strength": self.config.safety.max_strength
            }
        }
    
    def process_command(self, command: str) -> Dict[str, Any]:
        """Process any command using LangChain tools - no manual logic"""
        start_time = time.time()
        
        try:
            logger.info(f"Processing command with LangChain: {command}")
            
            # Everything goes through LangChain - no manual parsing or execution
            # The LangChain agent will decide how to handle the command
            result = self._process_with_langchain(command)
            
            # Update statistics
            self.total_commands_processed += 1
            if result.get('success', False):
                self.successful_commands += 1
            else:
                self.failed_commands += 1
            
            # Add timing information
            result['processing_time'] = time.time() - start_time
            result['timestamp'] = time.time()
            
            logger.info(f"LangChain command processed: {result.get('success', False)}")
            return result
            
        except Exception as e:
            logger.error(f"LangChain command processing failed: {e}")
            self.total_commands_processed += 1
            self.failed_commands += 1
            
            return {
                "success": False,
                "command": command,
                "error": str(e),
                "processing_time": time.time() - start_time,
                "timestamp": time.time()
            }
    
    def _process_with_langchain(self, command: str) -> Dict[str, Any]:
        """Process command using LangChain tools and agents"""
        try:
            # Use LangChain to process the command
            # This will automatically choose the right tools and execute them
            result = self.command_parser.process_with_langchain(command)
            
            # The result should contain everything needed
            return {
                "success": result.get('success', False),
                "command": command,
                "result": result.get('result'),
                "error": result.get('error'),
                "metadata": result.get('metadata', {}),
                "langchain_tools_used": result.get('tools_used', []),
                "execution_time": result.get('execution_time', 0.0)
            }
            
        except Exception as e:
            logger.error(f"LangChain processing error: {e}")
            return {
                "success": False,
                "error": f"LangChain processing failed: {str(e)}",
                "metadata": {"exception": str(e)}
            }
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get basic agent status"""
        return {
            "agent": {
                "name": self.config.name,
                "version": self.config.version,
                "description": self.config.description,
                "session_start_time": self.session_start_time,
                "uptime": time.time() - self.session_start_time
            },
            "statistics": {
                "total_commands": self.total_commands_processed,
                "successful_commands": self.successful_commands,
                "failed_commands": self.failed_commands,
                "success_rate": self.successful_commands / self.total_commands_processed if self.total_commands_processed > 0 else 0.0
            },
            "architecture": "Pure LangChain-based agent with tools"
        }
    
    def shutdown(self):
        """Shutdown the agent gracefully"""
        logger.info("Shutting down Tango AI Agent...")
        logger.info("Tango AI Agent shutdown complete")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.shutdown()
