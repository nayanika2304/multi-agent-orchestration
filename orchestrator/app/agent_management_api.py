#!/usr/bin/env python3
"""
FastAPI endpoints for agent management operations
"""
import logging
import json
from typing import Dict, List, Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.orchestrator import SmartOrchestrator

logger = logging.getLogger(__name__)

# Pydantic models for request/response
class RegisterAgentRequest(BaseModel):
    endpoint: str = Field(..., description="The endpoint URL of the agent to register")

class RegisterAgentResponse(BaseModel):
    success: bool
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    endpoint: Optional[str] = None
    message: str
    error: Optional[str] = None

class UnregisterAgentRequest(BaseModel):
    agent_identifier: str = Field(..., description="Agent ID, name, or endpoint to unregister")

class UnregisterAgentResponse(BaseModel):
    success: bool
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    endpoint: Optional[str] = None
    message: str
    error: Optional[str] = None

class AgentInfo(BaseModel):
    agent_id: str
    name: str
    description: str
    endpoint: str
    skills: List[Dict]
    keywords: List[str]
    capabilities: List[str]

class ListAgentsResponse(BaseModel):
    success: bool = True
    agents: List[AgentInfo]
    total_count: int
    message: str

class QueryRequest(BaseModel):
    query: str = Field(..., description="The user query to process")
    session_id: Optional[str] = Field(None, description="Optional session ID for conversation context")

class QueryResponse(BaseModel):
    success: bool
    response: str
    selected_agent_id: Optional[str] = None
    selected_agent_name: Optional[str] = None
    confidence: Optional[float] = None
    reasoning: Optional[str] = None
    session_id: Optional[str] = None
    error: Optional[str] = None

# Global orchestrator instance (will be injected)
_orchestrator_instance: Optional[SmartOrchestrator] = None

def get_orchestrator() -> SmartOrchestrator:
    """Dependency to get the orchestrator instance"""
    if _orchestrator_instance is None:
        logger.error("Orchestrator instance is None - not initialized")
        raise HTTPException(status_code=500, detail="Orchestrator not initialized. Please check server logs.")
    return _orchestrator_instance

def set_orchestrator(orchestrator: SmartOrchestrator):
    """Set the orchestrator instance"""
    global _orchestrator_instance
    _orchestrator_instance = orchestrator

# Create FastAPI router
router = APIRouter(prefix="/api/v1/agents", tags=["Agent Management"])

@router.post("/register", response_model=RegisterAgentResponse)
async def register_agent(
    request: RegisterAgentRequest,
    orchestrator: SmartOrchestrator = Depends(get_orchestrator)
):
    """
    Register a new agent by providing its endpoint URL.
    The orchestrator will fetch the agent's card and add it to the registry.
    """
    try:
        logger.info(f"Registering agent from endpoint: {request.endpoint}")
        
        result = await orchestrator.register_agent(request.endpoint)
        
        if result["success"]:
            logger.info(f"Successfully registered agent: {result.get('agent_name', 'Unknown')}")
            return RegisterAgentResponse(
                success=True,
                agent_id=result.get("agent_id"),
                agent_name=result.get("agent_name"),
                endpoint=result.get("endpoint"),
                message=result.get("message", "Agent registered successfully")
            )
        else:
            logger.warning(f"Failed to register agent from {request.endpoint}: {result.get('error')}")
            return RegisterAgentResponse(
                success=False,
                message="Failed to register agent",
                error=result.get("error")
            )
            
    except Exception as e:
        logger.error(f"Error registering agent from {request.endpoint}: {e}")
        return RegisterAgentResponse(
            success=False,
            message="Internal server error during agent registration",
            error=str(e)
        )

@router.post("/unregister", response_model=UnregisterAgentResponse)
async def unregister_agent(
    request: UnregisterAgentRequest,
    orchestrator: SmartOrchestrator = Depends(get_orchestrator)
):
    """
    Unregister an agent by providing its identifier (agent ID, name, or endpoint).
    The agent will be removed from the registry.
    """
    try:
        logger.info(f"Unregistering agent: {request.agent_identifier}")
        
        result = await orchestrator.unregister_agent(request.agent_identifier)
        
        if result["success"]:
            logger.info(f"Successfully unregistered agent: {result.get('agent_name', 'Unknown')}")
            return UnregisterAgentResponse(
                success=True,
                agent_id=result.get("agent_id"),
                agent_name=result.get("agent_name"),
                endpoint=result.get("endpoint"),
                message=result.get("message", "Agent unregistered successfully")
            )
        else:
            logger.warning(f"Failed to unregister agent {request.agent_identifier}: {result.get('error')}")
            return UnregisterAgentResponse(
                success=False,
                message="Failed to unregister agent",
                error=result.get("error")
            )
            
    except Exception as e:
        logger.error(f"Error unregistering agent {request.agent_identifier}: {e}")
        return UnregisterAgentResponse(
            success=False,
            message="Internal server error during agent unregistration",
            error=str(e)
        )

@router.get("/list", response_model=ListAgentsResponse)
async def list_agents(
    orchestrator: SmartOrchestrator = Depends(get_orchestrator)
):
    """
    List all registered agents with their details including skills and capabilities.
    """
    try:
        logger.info("Listing all registered agents")
        
        agents_data = orchestrator.get_available_agents()
        
        agents = [
            AgentInfo(
                agent_id=agent["agent_id"],
                name=agent["name"],
                description=agent["description"],
                endpoint=agent["endpoint"],
                skills=agent["skills"],
                keywords=agent["keywords"],
                capabilities=agent["capabilities"]
            )
            for agent in agents_data
        ]
        
        logger.info(f"Found {len(agents)} registered agents")
        
        return ListAgentsResponse(
            success=True,
            agents=agents,
            total_count=len(agents),
            message=f"Found {len(agents)} registered agents"
        )
        
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during agent listing: {str(e)}"
        )

# Alternative simpler endpoints if you prefer GET requests for register/unregister
@router.get("/register_agent")
async def register_agent_get(
    endpoint: str,
    orchestrator: SmartOrchestrator = Depends(get_orchestrator)
):
    """
    Alternative GET endpoint for registering an agent.
    Usage: GET /api/v1/agents/register_agent?endpoint=http://localhost:8001
    """
    request = RegisterAgentRequest(endpoint=endpoint)
    return await register_agent(request, orchestrator)

@router.get("/unregister_agent")
async def unregister_agent_get(
    agent_identifier: str,
    orchestrator: SmartOrchestrator = Depends(get_orchestrator)
):
    """
    Alternative GET endpoint for unregistering an agent.
    Usage: GET /api/v1/agents/unregister_agent?agent_identifier=MathAgent
    """
    request = UnregisterAgentRequest(agent_identifier=agent_identifier)
    return await unregister_agent(request, orchestrator)

@router.get("/list_agents")
async def list_agents_get(
    orchestrator: SmartOrchestrator = Depends(get_orchestrator)
):
    """
    Alternative GET endpoint for listing agents.
    Usage: GET /api/v1/agents/list_agents
    """
    return await list_agents(orchestrator)

@router.post("/query", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    orchestrator: SmartOrchestrator = Depends(get_orchestrator)
):
    """
    Process a user query through the orchestrator.
    The orchestrator will route the query to the most appropriate agent.
    """
    print(f"\n{'='*80}")
    print(f"📥 QUERY REQUEST RECEIVED")
    print(f"{'='*80}")
    print(f"Query: {request.query}")
    print(f"Session ID: {request.session_id}")
    print(f"Orchestrator agents: {list(orchestrator.agents.keys())}")
    print(f"{'='*80}\n")
    
    try:
        logger.info(f"Processing query: {request.query[:100]}...")
        print(f"Starting query processing...")
        
        # Validate request
        if not request.query or not request.query.strip():
            return QueryResponse(
                success=False,
                response="",
                selected_agent_id=None,
                selected_agent_name=None,
                confidence=None,
                reasoning=None,
                session_id=request.session_id,
                error="Query cannot be empty"
            )
        
        print(f"Calling orchestrator.process_request...")
        result = await orchestrator.process_request(
            request.query.strip(),
            session_id=request.session_id
        )
        print(f"Received result from orchestrator: {type(result)}")
        print(f"Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        
        # Ensure result is a dict
        if not isinstance(result, dict):
            error_msg = f"Unexpected result type: {type(result)}, value: {result}"
            logger.error(error_msg)
            print(f"ERROR: {error_msg}")
            return QueryResponse(
                success=False,
                response="",
                selected_agent_id=None,
                selected_agent_name=None,
                confidence=None,
                reasoning=None,
                session_id=request.session_id,
                error=error_msg
            )
        
        if result.get("success", False):
            return QueryResponse(
                success=True,
                response=result.get("response", ""),
                selected_agent_id=result.get("selected_agent_id"),
                selected_agent_name=result.get("selected_agent_name"),
                confidence=result.get("confidence"),
                reasoning=result.get("reasoning"),
                session_id=result.get("session_id")
            )
        else:
            return QueryResponse(
                success=False,
                response="",
                selected_agent_id=None,
                selected_agent_name=None,
                confidence=None,
                reasoning=None,
                session_id=request.session_id,
                error=result.get("error", "Unknown error occurred")
            )
            
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        
        # Print to console (will definitely show up)
        print(f"\n{'='*80}")
        print(f"ERROR: EXCEPTION IN QUERY ENDPOINT")
        print(f"{'='*80}")
        print(f"Error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"\nFull traceback:")
        print(error_trace)
        print(f"{'='*80}\n")
        
        logger.error(f"Error processing query: {e}", exc_info=True)
        logger.error(f"Full traceback: {error_trace}")
        
        # Return proper error response
        try:
            return QueryResponse(
                success=False,
                response="",
                selected_agent_id=None,
                selected_agent_name=None,
                confidence=None,
                reasoning=None,
                session_id=getattr(request, 'session_id', None),
                error=f"Internal server error: {str(e)}"
            )
        except Exception as response_error:
            # If even creating the response fails, log and raise
            print(f"CRITICAL ERROR: Failed to create error response: {response_error}")
            logger.error(f"Failed to create error response: {response_error}")
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error: {str(e)}"
            )

@router.post("/query/stream")
async def process_query_stream(
    request: QueryRequest,
    orchestrator: SmartOrchestrator = Depends(get_orchestrator)
):
    """
    Process a user query through the orchestrator with streaming response.
    """
    async def generate_stream() -> AsyncGenerator[str, None]:
        try:
            # Validate request
            if not request.query or not request.query.strip():
                yield f"data: {json.dumps({'type': 'error', 'error': 'Query cannot be empty'})}\n\n"
                return
            
            # Send initial status
            yield f"data: {json.dumps({'type': 'status', 'message': 'Processing query...'})}\n\n"
            
            # Process request
            result = await orchestrator.process_request(
                request.query.strip(),
                session_id=request.session_id
            )
            
            # Stream the result
            if isinstance(result, dict):
                if result.get("success", False):
                    # Stream metadata first
                    if result.get("selected_agent_name"):
                        yield f"data: {json.dumps({'type': 'metadata', 'agent': result.get('selected_agent_name'), 'confidence': result.get('confidence'), 'reasoning': result.get('reasoning')})}\n\n"
                    
                    # Stream response text in chunks
                    response_text = result.get("response", "")
                    if response_text:
                        # Stream in chunks for better UX
                        chunk_size = 50
                        for i in range(0, len(response_text), chunk_size):
                            chunk = response_text[i:i + chunk_size]
                            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                    
                    # Send completion
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'error', 'error': result.get('error', 'Unknown error occurred')})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'error': f'Unexpected result type: {type(result)}'})}\n\n"
                
        except Exception as e:
            logger.error(f"Error in streaming query: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'error': f'Internal server error: {str(e)}'})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    ) 