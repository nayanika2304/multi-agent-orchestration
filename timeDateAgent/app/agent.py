#!/usr/bin/env python3
"""
Time/Date Agent using MCP (Model Context Protocol) Server
"""
import asyncio
import os
import sys
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools

# Load environment variables from .env file in project root
project_root = Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=project_root / ".env")

# LangSmith tracing
os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
os.environ.setdefault("LANGCHAIN_ENDPOINT", os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"))
os.environ.setdefault("LANGCHAIN_API_KEY", os.getenv("LANGSMITH_API_KEY", ""))
os.environ.setdefault("LANGCHAIN_PROJECT", os.getenv("LANGSMITH_PROJECT", "03892bba-bf1e-4c69-82d9-1058208e56ae"))

class TimeDateAgent:
    """Time/Date Agent using MCP server for time and date operations"""
    
    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']
    
    def __init__(self):
        self.agent = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the OpenAI GPT-4o model"""
        self.model = ChatOpenAI(
            model="gpt-4o",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            temperature=1,  # Use default temperature
        )
    
    async def process_request(self, request: str) -> str:
        """Process a time/date request using MCP tools"""
        try:
            # Create agent with MCP tools for each request
            # This ensures fresh connection each time
            current_dir = Path(__file__).parent.parent
            time_server_path = current_dir / "time_mcp_server.py"
            
            if not time_server_path.exists():
                return f"Error: Time/Date MCP server not found at {time_server_path}"
            
            server_params = StdioServerParameters(
                command="python",
                args=[str(time_server_path)],
            )
            
            try:
                async with stdio_client(server_params) as (read, write):
                    try:
                        async with ClientSession(read, write) as session:
                            try:
                                await session.initialize()
                                
                                # Use load_mcp_tools to get LangChain-compatible tools
                                tools = await load_mcp_tools(session)
                                
                                if not tools:
                                    return "Error: No tools loaded from MCP server"
                                
                                # Create agent with MCP tools (they're already LangChain-compatible)
                                agent = create_react_agent(self.model, tools)
                                
                                # Process the request - format as list of HumanMessage objects
                                response = await agent.ainvoke({"messages": [HumanMessage(content=request)]})
                                
                                # Extract the final message content
                                if "messages" in response:
                                    messages = response["messages"]
                                    if messages and hasattr(messages[-1], 'content'):
                                        return messages[-1].content
                                    elif messages:
                                        return str(messages[-1])
                                
                                return str(response)
                            except Exception as session_error:
                                import traceback
                                error_details = traceback.format_exc()
                                print(f"ERROR in MCP session: {session_error}\n{error_details}", file=sys.stderr)
                                return f"Error in MCP session: {str(session_error)}"
                    except Exception as client_error:
                        import traceback
                        error_details = traceback.format_exc()
                        print(f"ERROR in MCP client: {client_error}\n{error_details}", file=sys.stderr)
                        return f"Error connecting to MCP server: {str(client_error)}"
            except Exception as stdio_error:
                import traceback
                error_details = traceback.format_exc()
                print(f"ERROR starting MCP server: {stdio_error}\n{error_details}", file=sys.stderr)
                return f"Error starting MCP server: {str(stdio_error)}. Make sure Python can execute the time_mcp_server.py file."
                    
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"ERROR processing time/date request: {e}\n{error_details}", file=sys.stderr)
            return f"Error processing time/date request: {str(e)}"
    
    def get_capabilities(self) -> List[str]:
        """Return list of time/date capabilities"""
        return [
            "Get current time in any timezone",
            "Convert time between timezones",
            "Calculate date differences (days, hours, minutes, seconds)",
            "Add or subtract time from dates",
            "Format dates in various formats (ISO, readable, short, long, timestamp)",
            "List and search available timezones",
            "Support for all major timezones worldwide"
        ]

# Global agent instance
time_date_agent = TimeDateAgent()

async def process_time_date_request(request: str) -> str:
    """Process a time/date request"""
    return await time_date_agent.process_request(request)

def get_time_date_capabilities() -> List[str]:
    """Get time/date capabilities"""
    return time_date_agent.get_capabilities()

# Test function
async def test_agent():
    """Test the time/date agent"""
    test_requests = [
        "What time is it in New York?",
        "Convert 3:00 PM EST to London time",
        "How many days until Christmas?",
        "What's the current time in Tokyo?",
    ]
    
    for request in test_requests:
        print(f"\nRequest: {request}")
        response = await process_time_date_request(request)
        print(f"Response: {response}")

if __name__ == "__main__":
    asyncio.run(test_agent())

