#!/usr/bin/env python3
"""
Chatbox Interface for Tango AI Agent
Uses LangChain tools and agents for dynamic command execution
"""

import sys
import time
import logging
from pathlib import Path
from typing import Dict, Any

# Add the src directory to Python path
src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(src_path))

from dt4acc.tango_ai_agent.core.agent import TangoAIAgent

class ChatboxInterface:
    """Chatbox interface using LangChain tools and agents"""
    
    def __init__(self):
        self.agent = None
        self.chat_history = []
        self.setup_agent()
    
    def setup_agent(self):
        """Initialize the Tango AI Agent with LangChain tools"""
        try:
            print("🤖 Initializing Tango AI Agent with LangChain...")
            self.agent = TangoAIAgent()
            print("✅ Agent ready! Start chatting...")
            print("💡 The AI can now execute any command using LangChain tools")
            print("🔍 Example: 'set Q3P2T6R current to 5.1A' or 'how are you'")
            print("=" * 60)
        except Exception as e:
            print(f"❌ Failed to initialize agent: {e}")
            sys.exit(1)
    
    def process_chat_message(self, message: str) -> Dict[str, Any]:
        """Process a chat message using LangChain agent"""
        if not message.strip():
            return {"type": "error", "content": "Please enter a message"}
        
        print(f"\n🔍 Processing message: '{message}'")
        
        # Add to chat history
        self.chat_history.append({
            "timestamp": time.time(),
            "user": message,
            "type": "user"
        })
        
        # Process with LangChain agent (no hardcoded logic)
        try:
            print("🤖 Agent: Processing with LangChain...")
            result = self.agent.process_command(message)
            
            # Create response based on agent result
            if result['success']:
                response = self._format_agent_response(result)
            else:
                response = self._format_agent_error(result)
            
            # Add response to chat history
            self.chat_history.append({
                "timestamp": time.time(),
                "user": response,
                "type": "agent"
            })
            
            return response
            
        except Exception as e:
            error_response = {
                "type": "error",
                "content": f"❌ Error processing message: {str(e)}"
            }
            self.chat_history.append({
                "timestamp": time.time(),
                "user": error_response,
                "type": "agent"
            })
            return error_response
    
    def _format_agent_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format successful agent response"""
        exec_result = result.get('execution_result', {})
        
        if exec_result.get('result'):
            content = f"✅ {exec_result['result']}"
        else:
            content = "✅ Command executed successfully!"
        
        # Add timing information
        if 'execution_time' in exec_result:
            content += f"\n⏱️ Execution time: {exec_result['execution_time']:.3f}s"
        if 'processing_time' in result:
            content += f"\n⏱️ Total processing time: {result['processing_time']:.3f}s"
        
        return {
            "type": "success",
            "content": content,
            "metadata": result
        }
    
    def _format_agent_error(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format agent error response"""
        exec_result = result.get('execution_result', {})
        error_msg = exec_result.get('error', 'Unknown error')
        
        content = f"❌ Command failed: {error_msg}"
        
        # Add parsed command info for debugging
        if 'parsed_command' in result:
            parsed = result['parsed_command']
            content += f"\n🔍 Parsed as: {parsed.get('action', 'unknown')} {parsed.get('device_name', 'unknown')}.{parsed.get('property_name', 'unknown')}"
            if 'confidence' in parsed:
                content += f"\n   Confidence: {parsed['confidence']:.1%}"
        
        if 'processing_time' in result:
            content += f"\n⏱️ Processing time: {result['processing_time']:.3f}s"
        
        return {
            "type": "error",
            "content": content,
            "metadata": result
        }
    
    def get_chat_history(self) -> list:
        """Get chat history"""
        return self.chat_history
    
    def clear_chat_history(self):
        """Clear chat history"""
        self.chat_history.clear()
        return {"type": "info", "content": "🧹 Chat history cleared"}

def main():
    """Main chatbox interface"""
    print("🤖 Tango AI Agent - LangChain Chatbox Interface")
    print("=" * 50)
    
    # Initialize chatbox
    chatbox = ChatboxInterface()
    
    print("\n💬 Start chatting with your Tango system!")
    print("💡 The AI can execute any command using LangChain tools:")
    print("   • 'set Q3P2T6R current to 5.1A'")
    print("   • 'get Q1M1T1R strength'")
    print("   • 'list all power converters'")
    print("   • 'how are you'")
    print("   • 'what can you do'")
    print("   • 'clear history'")
    print("   • 'quit' to exit")
    print("\n🚀 No hardcoded commands - everything is dynamic!")
    print("=" * 50)
    
    # Chat loop
    while True:
        try:
            # Get user input
            user_message = input("\n👤 You: ").strip()
            
            if not user_message:
                continue
            
            # Handle special commands
            if user_message.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if user_message.lower() in ['clear', 'cls']:
                response = chatbox.clear_chat_history()
                print(f"🤖 Agent: {response['content']}")
                continue
            
            # Process the message with LangChain agent
            response = chatbox.process_chat_message(user_message)
            
            # Display response
            print(f"🤖 Agent: {response['content']}")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            logging.error(f"Chatbox error: {e}")

if __name__ == "__main__":
    main()
