# 🤖 Tango AI Agent - Advanced Particle Accelerator Control

A sophisticated AI-powered agent that understands **natural language commands** and executes them in your Tango-based particle accelerator control system using **LangChain** and **LLMs**.

## 🎯 **What This Agent Does:**

### **Natural Language → Tango Execution Pipeline:**
1. **Human Input**: "set power converter Q3P2T6R current to 5.1A"
2. **AI Parsing**: LangChain + LLM parses command into structured data
3. **Knowledge Validation**: Checks against comprehensive Tango knowledge base
4. **Safety Validation**: Ensures commands are within safety limits
5. **Execution**: Runs actual Tango commands using your existing infrastructure
6. **Result**: Returns detailed success/failure information

## 🏗️ **Architecture Overview:**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Natural       │    │   LangChain      │    │   Tango         │
│   Language      │───▶│   + LLM          │───▶│   Execution     │
│   Commands      │    │   Parser         │    │   Engine        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │   Knowledge      │    │   Safety        │
                       │   Base           │    │   Validation    │
                       └──────────────────┘    └─────────────────┘
```

## 🚀 **Quick Start:**

### **1. Install Dependencies:**
```bash
cd src/dt4acc/tango_ai_agent
pip install -r requirements.txt
```

### **2. Set Environment Variables (Optional):**
```bash
export OPENAI_API_KEY="your-openai-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

### **3. Run the Agent:**
```bash
python main.py
```

### **4. Start Using Natural Language:**
```bash
🤖 Enter command: set power converter Q3P2T6R current to 5.1A
✅ Command executed successfully!
📝 Successfully set Q3P2T6R.current_setpoint = 5.1
```

## 🎮 **Example Commands:**

### **Power Converter Operations:**
```bash
# Set current
"set power converter Q3P2T6R current to 5.1A"
"change Q3P2T6R current setpoint to 10.5 amperes"
"update power converter Q3P2T6R to 15.2A"

# Get current values
"get power converter Q3P2T6R current"
"what is the current of Q3P2T6R?"
"show me Q3P2T6R current setpoint"

# List devices
"list all power converters"
"show power converters"
"display available power converters"
```

### **Magnet Operations:**
```bash
# Set strength
"set quadrupole Q1M1T1R strength to 2.5"
"adjust Q2M1T1R k_strength to -1.8"
"change magnet Q3M2T6R strength to 5.0 tesla"

# Get status
"get status of Q1M1T1R"
"what is the strength of Q2M1T1R?"
"show me Q3M2T6R current"
```

### **System Operations:**
```bash
# Status checks
"show system status"
"what is the health of the accelerator?"
"check status of all devices"
"monitor system health"
```

## 🔧 **Built-in Commands:**

### **System Commands:**
- `help` - Show available commands
- `status` - Show agent status and statistics
- `test` - Test Tango connections
- `commands` - List available command templates
- `devices` - List available device types
- `safety` - Show safety configuration
- `history` - Show command execution history
- `clear` - Clear command history
- `quit/exit` - Exit the agent

## 🏗️ **Core Components:**

### **1. Configuration Management (`config.py`)**
- **LLM Configuration**: OpenAI, Anthropic, and local models
- **LangChain Settings**: Memory, tools, agents, and chains
- **Tango Integration**: Server settings, timeouts, connection pools
- **Safety Configuration**: Limits, validation rules, confirmation requirements
- **Logging Configuration**: File rotation, audit trails, log levels

### **2. Knowledge Base (`knowledge_base.py`)**
- **Device Schemas**: Complete information about Tango devices
- **Command Templates**: Natural language patterns and Tango equivalents
- **Safety Rules**: Configurable limits and validation rules
- **Operation Modes**: Normal, maintenance, and emergency modes
- **Export/Import**: YAML-based knowledge base management

### **3. Command Parser (`command_parser.py`)**
- **LangChain Integration**: LLM-powered natural language understanding
- **Fallback Parsing**: Rule-based parsing when LLM unavailable
- **Memory Management**: Conversation history and context
- **Confidence Scoring**: Parsing quality assessment
- **Template Matching**: Command-to-template mapping

### **4. Command Executor (`executor.py`)**
- **Tango Integration**: Direct device communication
- **Safety Validation**: Pre-execution safety checks
- **Connection Pooling**: Efficient device proxy management
- **Error Handling**: Graceful failure and detailed error reporting
- **Execution History**: Complete audit trail

### **5. Main Agent (`agent.py`)**
- **Component Orchestration**: Coordinates all subsystems
- **Command Processing**: End-to-end command execution
- **Status Monitoring**: Real-time agent health and statistics
- **Context Management**: Session state and history
- **Graceful Shutdown**: Clean resource cleanup

## 🔮 **Advanced Features:**

### **1. LangChain Integration:**
- **LLM Chains**: Structured command parsing pipelines
- **Memory Systems**: Conversation buffer and summary memory
- **Tool Integration**: Extensible command execution tools
- **Agent Frameworks**: Multi-step reasoning and execution

### **2. Safety Framework:**
- **Configurable Limits**: Min/max values for all properties
- **Operation Modes**: Different safety levels for different scenarios
- **Confirmation Requirements**: High-risk operations require confirmation
- **Audit Trails**: Complete command execution history

### **3. Knowledge Management:**
- **Extensible Schemas**: Easy addition of new device types
- **Template System**: Natural language command patterns
- **Safety Rules**: Device-specific safety configurations
- **Export/Import**: YAML-based knowledge base management

### **4. Performance Features:**
- **Connection Pooling**: Efficient Tango device management
- **Caching**: Device and command template caching
- **Async Support**: Non-blocking command execution
- **Statistics**: Real-time performance monitoring

## 🎯 **Integration with Your Tango App:**

### **1. Uses Your Existing Commands:**
```python
# Your existing function
from dt4acc.custom_epics.data.querries import get_unique_power_converters
power_converters = list(get_unique_power_converters())

# Agent uses this to list devices
def _execute_list(self, parsed_command):
    if parsed_command.device_type == DeviceType.POWER_CONVERTER:
        devices = list(get_unique_power_converters())  # Your working code!
        return {"success": True, "devices": devices, "count": len(devices)}
```

### **2. Executes Your Tango Commands:**
```python
# Your working Tango command
from tango import DeviceProxy
dev = DeviceProxy("SimpleTangoServer/test/power_converter_Q3P2T6R")
dev.current_setpoint = 5.1

# Agent wraps this in natural language
"set power converter Q3P2T6R current to 5.1A" → dev.current_setpoint = 5.1
```

### **3. Extends Your Functionality:**
- **Same Tango Server**: Connects to your existing `SimpleTangoServer`
- **Same Device Names**: Uses your device naming convention
- **Same Properties**: Accesses the same Tango attributes
- **Same Safety**: Respects your existing safety mechanisms

## 🔧 **Configuration:**

### **Default Configuration:**
The agent works out-of-the-box with sensible defaults, but you can customize:

### **Environment Variables:**
```bash
export OPENAI_API_KEY="your-openai-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export OPENAI_BASE_URL="your-openai-base-url"  # Optional
export ANTHROPIC_BASE_URL="your-anthropic-base-url"  # Optional
```

### **Configuration File (`config.yaml`):**
```yaml
name: "Tango AI Agent"
version: "1.0.0"
description: "Advanced AI-powered Tango control system"

llm:
  provider: "openai"  # openai, anthropic, local
  model: "gpt-4"
  temperature: 0.1
  max_tokens: 1000

langchain:
  use_memory: true
  memory_type: "conversation_buffer"
  max_memory_size: 10
  use_tools: true
  use_agents: true

tango:
  server_name: "SimpleTangoServer"
  server_instance: "test"
  device_prefix: "SimpleTangoServer/test"
  timeout: 5000
  retry_attempts: 3

safety:
  enable_safety_checks: true
  enable_limits: true
  max_current: 1000.0
  max_voltage: 100.0
  max_strength: 50.0
```

## 🚀 **Usage Examples:**

### **Basic Usage:**
```python
from dt4acc.tango_ai_agent.core.agent import TangoAIAgent

# Initialize agent
agent = TangoAIAgent()

# Process natural language command
result = agent.process_command("set Q3P2T6R current to 5.1A")
print(f"Success: {result['success']}")

# Get agent status
status = agent.get_agent_status()
print(f"Commands processed: {status['statistics']['total_commands']}")
```

### **Advanced Usage:**
```python
# Validate command without execution
validation = agent.validate_command("set Q3P2T6R current to 1500A")
if not validation['valid']:
    print(f"Validation errors: {validation['errors']}")

# Get device information
device_info = agent.get_device_info("Q3P2T6R")
print(f"Device status: {device_info['status']}")

# Export knowledge base
agent.export_knowledge_base("exported_kb")
```

### **Context Manager:**
```python
with TangoAIAgent() as agent:
    result = agent.process_command("get Q3P2T6R current")
    print(f"Current: {result['execution_result']['result']['value']}A")
# Agent automatically shuts down
```

## 🔒 **Safety Features:**

### **1. Input Validation:**
- **Device Names**: Regex validation for device identifiers
- **Values**: Type checking and range validation
- **Commands**: Action and property validation

### **2. Safety Limits:**
- **Configurable Ranges**: Min/max values for each property
- **Unit Conversion**: Automatic unit handling
- **Boundary Checking**: Prevents unsafe values

### **3. Operation Modes:**
- **Normal Mode**: Standard safety checks
- **Maintenance Mode**: Relaxed safety for maintenance
- **Emergency Mode**: Strict safety, read-only operations

### **4. Audit Trail:**
- **Command History**: Complete execution log
- **Timing Information**: Execution and processing times
- **Error Details**: Comprehensive error reporting

## 📊 **Monitoring and Statistics:**

### **1. Real-time Statistics:**
- **Command Success Rate**: Track execution success/failure
- **Processing Times**: Monitor performance
- **Error Patterns**: Identify common failure modes

### **2. Component Health:**
- **Knowledge Base**: Device and command coverage
- **Parser Performance**: LangChain and fallback usage
- **Executor Status**: Tango connection health

### **3. System Status:**
- **Tango Availability**: Connection status
- **dt4acc Integration**: Function availability
- **Overall Health**: System operational status

## 🛠️ **Customization and Extension:**

### **1. Add New Device Types:**
```python
# In knowledge_base.py
self.devices["new_device"] = DeviceSchema(
    name="new_device",
    type="new_device",
    class_name="NewDeviceClass",
    description="Description of new device",
    attributes={
        "new_property": {
            "type": "float",
            "unit": "units",
            "description": "New device property",
            "readable": True,
            "writable": True
        }
    },
    safety_limits={
        "new_property": {"min": 0.0, "max": 100.0, "unit": "units"}
    }
)
```

### **2. Add New Commands:**
```python
# In knowledge_base.py
self.commands["new_command"] = CommandTemplate(
    name="new_command",
    description="Description of new command",
    natural_language=[
        "do {action} with {device}",
        "perform {action} on {device}"
    ],
    tango_command="dev.new_property = {value}",
    parameters={
        "action": {"type": "string", "description": "Action to perform"},
        "device": {"type": "string", "description": "Device name"}
    },
    examples=["do something with Q1M1T1R"],
    safety_notes=["Safety considerations"]
)
```

### **3. Custom Safety Rules:**
```python
# In config.yaml
safety:
  custom_rules:
    - name: "high_power_operation"
      condition: "current > 500A or voltage > 50V"
      action: "require_confirmation"
      message: "High power operation requires confirmation"
```

## 🔮 **Future Enhancements:**

### **1. Advanced LLM Features:**
- **Multi-step Reasoning**: Complex command decomposition
- **Context Learning**: Learn from user patterns
- **Natural Language Generation**: Explain operations in plain English

### **2. Enhanced Safety:**
- **Predictive Safety**: Anticipate dangerous operations
- **Machine Learning**: Learn from historical safety data
- **Real-time Monitoring**: Continuous safety assessment

### **3. Integration Features:**
- **Web Interface**: Browser-based control panel
- **API Endpoints**: RESTful API for external integration
- **Event Streaming**: Real-time status updates

### **4. Advanced Analytics:**
- **Usage Patterns**: Understand operator behavior
- **Performance Optimization**: Identify bottlenecks
- **Predictive Maintenance**: Anticipate device issues

## 🎉 **Benefits:**

### **1. For Operators:**
- **Natural Language**: No need to remember exact Tango syntax
- **Safety**: Built-in validation prevents dangerous operations
- **Efficiency**: Faster command execution
- **Learning**: Understand what commands are available

### **2. For Developers:**
- **Extensible**: Easy to add new devices and properties
- **Maintainable**: Clean separation of concerns
- **Testable**: Each component can be tested independently
- **Documented**: Self-documenting code structure

### **3. For System Administrators:**
- **Audit Trail**: Complete command history
- **Safety**: Configurable safety limits
- **Monitoring**: Real-time system health
- **Integration**: Works with existing Tango infrastructure

## 🚀 **Ready to Use!**

Your Tango AI Agent is now ready to:
1. **Understand** human commands in natural language using LangChain and LLMs
2. **Validate** commands for safety and correctness
3. **Execute** them using your existing working Tango commands
4. **Provide** detailed feedback and results
5. **Maintain** a complete audit trail

**Start controlling your accelerator with natural language today!** 🎯

---

**Example Session:**
```bash
🤖 Enter command: set power converter Q3P2T6R current to 5.1A
✅ Command executed successfully!
📝 Successfully set Q3P2T6R.current_setpoint = 5.1

🤖 Enter command: get Q3P2T6R current
✅ Command executed successfully!
📊 Q3P2T6R.current = 5.1 A

🤖 Enter command: list all power converters
✅ Command executed successfully!
📋 Found 15 power_converter devices
    - Q1M1T1R, Q2M1T1R, Q3P2T6R, Q4M1T1R, Q5M2T6R
    ... and 10 more
```
