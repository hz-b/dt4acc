"""
Tango AI Agent Package for dt4acc
Advanced AI-powered Tango control using LangChain and LLMs
"""

__version__ = "1.0.0"
__author__ = "dt4acc Team"

from .core.agent import TangoAIAgent
from .core.config import AgentConfig, LLMConfig
from .core.command_parser import CommandParser
from .core.executor import CommandExecutor
from .core.knowledge_base import TangoKnowledgeBase

__all__ = [
    "TangoAIAgent",
    "AgentConfig", 
    "LLMConfig",
    "CommandParser",
    "CommandExecutor",
    "TangoKnowledgeBase"
]
