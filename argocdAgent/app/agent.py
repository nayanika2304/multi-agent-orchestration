import os
import asyncio
from collections.abc import AsyncIterable
from typing import Any, Literal

from langchain_core.messages import AIMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel

from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

memory = MemorySaver()

class ResponseFormat(BaseModel):
    """Response format for the ArgoCD agent."""
    status: Literal['input_required', 'completed', 'error'] = 'input_required'
    message: str

class ArgoCDAgent:
    """
    ArgoCDAgent - a specialized assistant for ArgoCD management via MCP stdio.
    
    This agent connects to ArgoCD via the MCP stdio protocol and provides
    natural language interface to ArgoCD operations.
    """
    SYSTEM_INSTRUCTION = (
        'You are a specialized assistant for ArgoCD management. '
        'Your sole purpose is to use the ArgoCD MCP tools to help users manage their ArgoCD deployments. '
        'You can list applications, get application details, sync applications, and more. '
        'If the user asks about anything other than ArgoCD management, '
        'politely state that you cannot help with that topic and can only assist with ArgoCD-related queries. '
        'Do not attempt to answer unrelated questions or use tools for other purposes. '
        'Set response status to input_required if the user needs to provide more information. '
        'Set response status to error if there is an error while processing the request. '
        'Set response status to completed if the request is complete. '
        'Always provide clear, concise responses about the ArgoCD operations you perform.'
    )

    def __init__(self):
        self.model = ChatGoogleGenerativeAI(model='gemini-2.0-flash')
        os.environ["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"
        os.environ["ARGOCD_BASE_URL"] = os.getenv("ARGOCD_BASE_URL", "https://9.30.147.51:8080/")
        os.environ["ARGOCD_API_TOKEN"] = os.getenv("ARGOCD_API_TOKEN", "")
        self.tools = []
        self.mcp_session = None
        self.graph = create_react_agent(
            self.model,
            tools=self.tools,
            checkpointer=memory,
            prompt=self.SYSTEM_INSTRUCTION,
            response_format=ResponseFormat,
        )
    
    async def _init_mcp_tools(self):
        """Initialize MCP tools using stdio transport, with direct API fallback."""
        if self.tools:
            return self.tools
            
        # Set environment variables before creating the server parameters
        os.environ["ARGOCD_BASE_URL"] = os.getenv("ARGOCD_BASE_URL", "https://9.30.147.51:8080/")
        os.environ["ARGOCD_API_TOKEN"] = os.getenv("ARGOCD_API_TOKEN", "")
        os.environ["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"
        
        # First try MCP stdio transport
        mcp_command_str = os.getenv('ARGOCD_MCP_COMMAND', 'npx argocd-mcp@latest stdio')
        cmd_parts = mcp_command_str.split()
        command = cmd_parts[0]
        args = cmd_parts[1:] if len(cmd_parts) > 1 else []
        
        server_params = StdioServerParameters(command=command, args=args)
        
        try:
            # Use a shorter timeout to fail faster if there are issues
            async with asyncio.timeout(10):
                async with stdio_client(server_params) as (read_stream, write_stream):
                    self.mcp_session = ClientSession(read_stream, write_stream)
                    tools = await load_mcp_tools(self.mcp_session)
                    print("Successfully initialized MCP stdio transport")
                    return tools
                    
        except Exception as e:
            print(f"MCP stdio transport failed: {str(e)}")
            print("Falling back to direct ArgoCD API client...")
            
            # Fallback to direct ArgoCD API
            try:
                from .argocd_direct import create_direct_tools
                tools, self.direct_client = create_direct_tools()
                
                # Convert direct tools to langchain-compatible tools
                from langchain_core.tools import StructuredTool
                langchain_tools = []
                
                for tool_def in tools:
                    def create_tool_func(handler, tool_name):
                        async def tool_func(**kwargs):
                            try:
                                result = await handler(**kwargs)
                                return f"Success: {result}"
                            except Exception as e:
                                return f"Error: {str(e)}"
                        tool_func.__name__ = tool_name
                        return tool_func
                    
                    langchain_tool = StructuredTool.from_function(
                        func=create_tool_func(tool_def["handler"], tool_def["name"]),
                        name=tool_def["name"],
                        description=tool_def["description"],
                        args_schema=None  # We'll handle this manually
                    )
                    langchain_tools.append(langchain_tool)
                
                print(f"Successfully initialized direct ArgoCD client with {len(langchain_tools)} tools")
                return langchain_tools
                
            except Exception as fallback_error:
                self.mcp_session = None
                raise RuntimeError(f"Both MCP stdio and direct API failed. MCP error: {str(e)}, Direct API error: {str(fallback_error)}")