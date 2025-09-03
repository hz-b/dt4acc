# 🤖 Beautiful Tango Agent

A stunning, natural-language Tango device operator powered by LangChain and Groq.

## ✨ Features

- 🗣️ **Natural Language**: Just chat - no commands to memorize
- 🎯 **Smart Planning**: Automatically plans and executes complex operations
- 🔧 **Rich Toolset**: Comprehensive Tango device operations
- 🚀 **Groq Powered**: Lightning-fast responses
- 💎 **Beautiful Output**: Clean, formatted summaries
- 🎮 **Interactive Mode**: Chat interface for ongoing operations

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables
```bash
export GROQ_API_KEY=your-groq-api-key-here
export TANGO_HOST=127.0.0.1:10000  # Optional: your Tango database host
```

### 3. Run the Agent

#### Command Line Mode
```bash
# List all devices
python tango_exec_agent.py "list all devices and summarize"

# Find specific devices
python tango_exec_agent.py "show devices with magnet_ in the name and explain"

# Device operations
python tango_exec_agent.py "set x=0.5 y=0.5 k=1.0 on SimpleTangoServer/test/magnet_Q3P2T6R, read them back, get status"

# System commands
python tango_exec_agent.py "run 'docker ps' and explain the output"
```

#### Interactive Chat Mode
```bash
python tango_exec_agent.py --interactive
```

Then just chat naturally:
```
💬 You: What Tango devices are available?
🤖 Agent: I found 5 devices running in your system...

💬 You: Is the magnet device responding?
🤖 Agent: Let me check that for you...

💬 You: Set the position to 1.5 on the magnet device
🤖 Agent: I'll set that value for you...
```

## 🛠️ Available Operations

### Device Discovery
- **List devices**: "What devices are available?"
- **Filter devices**: "Show me all magnet devices"
- **Check system**: "Is the Tango system healthy?"

### Device Operations
- **Ping devices**: "Is device X responding?"
- **Read attributes**: "What attributes does device X have?"
- **Write values**: "Set attribute Y to value Z on device X"
- **Get status**: "What's the status of device X?"

### Magnet Operations
- **Set magnet values**: "Set x=0.5 y=0.5 k=1.0 on magnet device"
- **Read magnet values**: "What are the current magnet settings?"

### System Operations
- **Shell commands**: "Run ls -l and show me the results"
- **System health**: "Check if the Tango system is working"

## 🎯 Example Output

```
🎯 BEAUTIFUL SUMMARY
============================================================

✅ What was executed:
• Listed all exported Tango devices from the database
• Filtered devices containing 'magnet' in the name
• Pinged 3 magnet devices to check responsiveness

📊 Key results:
• Found 5 total devices in the system
• 3 devices contain 'magnet' in their names:
  - SimpleTangoServer/test/magnet_Q3P2T6R ✅ (2ms response)
  - SimpleTangoServer/test/magnet_Q4P2T7R ✅ (1ms response)
  - SimpleTangoServer/test/magnet_Q5P3T8R ❌ (not responding)

⚠️  Warnings:
• Device magnet_Q5P3T8R is not responding - may need attention

🚀 Suggested next steps:
• Check the status of magnet_Q5P3T8R
• Consider restarting the device server if needed
• You can now read/write attributes on the responding devices
```

## 🔧 Advanced Usage

### Custom Models
```bash
python tango_exec_agent.py --model llama-3.3-70b-versatile "complex operation"
```

### Interactive with Custom Model
```bash
python tango_exec_agent.py --interactive --model mixtral-8x7b-32768
```

## 🏗️ Architecture

```
Natural Language Input
         ↓
    LangChain Agent
         ↓
   Tool Selection
         ↓
  Tango/Shell Tools
         ↓
   JSON Responses
         ↓
  Beautiful Summary
```

## 🎨 Key Benefits

1. **No Hardcoding**: All device patterns discovered dynamically
2. **Structured Data**: JSON responses ensure reliability
3. **Error Handling**: Comprehensive error reporting
4. **Extensible**: Easy to add new tools with `@tool` decorator
5. **Fast**: Groq provides quick responses
6. **Beautiful**: Clean, formatted output with emojis and structure

## 🚨 Troubleshooting

### Common Issues

**"PyTango import failed"**
- Install PyTango: `pip install pytango`
- Ensure system libraries match

**"GROQ_API_KEY not set"**
- Get API key from: https://console.groq.com/
- Set: `export GROQ_API_KEY=your-key`

**"TANGO_HOST not set"**
- Set: `export TANGO_HOST=127.0.0.1:10000`
- Or leave unset for local database

**"No devices found"**
- Check if Tango servers are running
- Verify database connection

## 🎉 That's It!

Just chat naturally and the Beautiful Tango Agent will handle the rest! 🚀
