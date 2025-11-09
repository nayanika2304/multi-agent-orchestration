# Time/Date Agent - Time & Date Operations

Time and date operations agent using **OpenAI GPT-4o**, **MCP (Model Context Protocol)**, and **A2A SDK**. The agent integrates seamlessly with the [intelligent orchestrator system](../orchestrator/README.md) for automatic routing.

## 🕐 Features

- **Current Time**: Get real-time time in any timezone
- **Timezone Conversion**: Convert time between different timezones
- **Date Calculations**: Calculate differences between dates (days, hours, minutes, seconds)
- **Date Arithmetic**: Add or subtract time from dates
- **Date Formatting**: Format dates in various formats (ISO, readable, short, long, timestamp)
- **Timezone Search**: List and search available timezones
- **MCP Integration**: Uses MCP protocol for tool management
- **Orchestrator Integration**: Automatically routed by the intelligent orchestrator
- **No API Keys Required**: Uses Python's built-in datetime and timezone libraries

## 🚀 Quick Start

### Prerequisites

1. **OpenAI API Key**:
   - Already configured in your `.env` file

2. **Python 3.11+** with zoneinfo support (included in Python 3.9+)

### Installation

```bash
cd timeDateAgent
uv sync
```

### Running the Agent

```bash
python -m app --port 8001
```

The agent will start on `http://localhost:8001`

## 📋 Example Queries

- "What time is it in New York?"
- "Convert 3:00 PM EST to London time"
- "How many days until Christmas?"
- "What's the current time in Tokyo?"
- "What date is 30 days from now?"
- "How many hours between now and tomorrow at 5 PM?"
- "Format today's date as ISO 8601"
- "List all timezones in America"

## 🏗️ Architecture

The Time/Date Agent uses an MCP-based architecture:

```
User Query → Time/Date Agent → MCP Client → Time/Date MCP Server → Python datetime/pytz
```

### Components

1. **Time/Date Agent** (`app/agent.py`): Main agent logic with LangGraph
2. **Time/Date MCP Server** (`time_mcp_server.py`): MCP server providing time/date tools
3. **Agent Executor** (`app/agent_executor.py`): A2A SDK integration
4. **Entry Point** (`app/__main__.py`): Server startup and configuration

## 🔧 Configuration

### Environment Variables

Add to your `.env` file:

```env
# Required
OPENAI_API_KEY=your_openai_key

# LangSmith (optional)
LANGSMITH_API_KEY=your_langsmith_key
LANGSMITH_PROJECT=your_project_name
```

### MCP Tools

The Time/Date MCP Server provides:

1. **get_current_time**: Get current time in any timezone
2. **convert_timezone**: Convert time between timezones
3. **calculate_date_difference**: Calculate difference between two dates
4. **add_subtract_time**: Add or subtract time from a date
5. **format_date**: Format dates in various formats
6. **list_timezones**: List and search available timezones

## 🎯 Orchestrator Integration

The agent is automatically discovered by the orchestrator with skills:
- Current Time
- Timezone Conversion
- Date Calculation
- Date Formatting

Example routing:
- "What time is it?" → Time/Date Agent (high confidence)
- "Convert EST to PST" → Time/Date Agent (high confidence)
- "How many days until..." → Time/Date Agent (high confidence)

## 📦 Dependencies

- `a2a-sdk`: Agent-to-agent communication
- `langchain-openai`: OpenAI integration
- `langchain-mcp-adapters`: MCP tool integration
- `langgraph`: Agent workflow
- `mcp`: MCP protocol
- `pytz`: Timezone support (fallback for older timezones)
- `zoneinfo`: Built-in timezone support (Python 3.9+)

## 🧪 Testing

Test the agent directly:

```bash
python -m app.agent
```

Or use the orchestrator to route queries automatically.

## 📝 Notes

- Uses Python's built-in `datetime` and `zoneinfo` modules
- Falls back to `pytz` for older timezone definitions
- Supports all IANA timezone database timezones
- No external API calls required - all operations are local
- Handles daylight saving time automatically

## 🌍 Supported Timezones

The agent supports all timezones from the IANA Time Zone Database, including:
- America/New_York (EST/EDT)
- America/Los_Angeles (PST/PDT)
- Europe/London (GMT/BST)
- Asia/Tokyo (JST)
- UTC
- And many more...

Use the `list_timezones` tool to search for specific timezones.

