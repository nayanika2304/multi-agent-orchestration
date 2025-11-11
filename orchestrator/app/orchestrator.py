#!/usr/bin/env python3
"""
Smart Orchestrator Agent with A2A SDK integration and Context Management
"""
import asyncio
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, TypedDict, Tuple, Any
from a2a.client import A2AClient, A2ACardResolver

import httpx
from dotenv import load_dotenv
from langgraph.graph import StateGraph
from a2a.types import AgentCard, AgentSkill, AgentCapabilities
from app.context_manager import OrchestratorContextManager

# Load environment variables from .env file in project root
project_root = Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=project_root / ".env")

# LangSmith tracing configuration
os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
os.environ.setdefault("LANGCHAIN_ENDPOINT", os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"))
os.environ.setdefault("LANGCHAIN_API_KEY", os.getenv("LANGSMITH_API_KEY", ""))
os.environ.setdefault("LANGCHAIN_PROJECT", os.getenv("LANGSMITH_PROJECT", "03892bba-bf1e-4c69-82d9-1058208e56ae"))

class RouterState(TypedDict):
    request: str
    original_request: str
    session_id: str
    selected_agent: str
    confidence: float
    reasoning: str
    response: str
    error: str
    metadata: dict


class SmartOrchestrator:
    """Intelligent orchestrator using A2A SDK types and LangGraph workflow with Context Management"""
    
    def __init__(self):
        self.agents: Dict[str, AgentCard] = {}
        self.skill_keywords: Dict[str, List[str]] = {}
        self.agent_capabilities: Dict[str, Dict[str, Any]] = {}
        self.context_manager = OrchestratorContextManager()
        self.workflow = self._create_workflow()
        self._initialize_default_agents()
    
    def _initialize_default_agents(self):
        """Initialize default agents by fetching their agent cards using A2A client"""
        
        # Default agent endpoints
        default_agents = [
            "http://localhost:8001",  # Time/Date Agent
            "http://localhost:8002",  # Math Agent
            "http://localhost:8003",  # Currency Agent
            "http://localhost:8004",  # RAG Agent
            "http://localhost:8005",  # Report Agent
        ]
        
        # Fetch agent cards using A2A client - run async initialization
        asyncio.run(self._fetch_all_agent_cards(default_agents))
    
    async def _fetch_all_agent_cards(self, default_agents: List[str]):
        """Async method to fetch all agent cards"""
        async with httpx.AsyncClient(timeout=5.0) as httpx_client:
            for endpoint in default_agents:
                try:
                    agent_card = await self._fetch_agent_card_with_a2a(httpx_client, endpoint)
                    if agent_card:
                        self.agents[agent_card.name] = agent_card
                        print(f"Loaded {agent_card.name} from {endpoint}")
                    else:
                        print(f"WARNING: Failed to load agent card from {endpoint}")
                except Exception as e:
                    print(f"ERROR: Error loading agent from {endpoint}: {e}")
        
        # Update skill keywords and agent capabilities after loading all default agents
        self._update_skill_keywords()
        self._extract_agent_capabilities()
    
    async def _fetch_agent_card_with_a2a(self, httpx_client: httpx.AsyncClient, endpoint: str) -> Optional[AgentCard]:
        """Fetch agent card using A2A client"""
        try:
            # Create A2A card resolver
            resolver = A2ACardResolver(
                httpx_client=httpx_client,
                base_url=endpoint
            )
            
            # Fetch agent card using the resolver
            agent_card = await resolver.get_agent_card()
            return agent_card
                
        except Exception as e:
            print(f"Error fetching agent card from {endpoint} using A2A client: {e}")
            return None
    
    def add_agent(self, agent_id: str, agent_card: AgentCard):
        """Add a new agent using A2A SDK AgentCard"""
        self.agents[agent_id] = agent_card
        self._update_skill_keywords()
        self._extract_agent_capabilities()
    
    def _update_skill_keywords(self):
        """Update skill keywords based on currently available agents"""
        self.skill_keywords = {}
        
        for agent_id, agent_card in self.agents.items():
            for skill in agent_card.skills:
                skill_name = skill.name
                
                # Initialize skill keywords list if not exists
                if skill_name not in self.skill_keywords:
                    self.skill_keywords[skill_name] = []
                
                # Add tags from this skill as keywords
                if skill.tags:
                    for tag in skill.tags:
                        if tag.lower() not in [kw.lower() for kw in self.skill_keywords[skill_name]]:
                            self.skill_keywords[skill_name].append(tag.lower())
                
                # Add skill name itself as a keyword
                skill_name_lower = skill_name.lower().replace("_", " ")
                if skill_name_lower not in [kw.lower() for kw in self.skill_keywords[skill_name]]:
                    self.skill_keywords[skill_name].append(skill_name_lower)
                
                # Add description words as keywords (first 3 words)
                if skill.description:
                    desc_words = skill.description.lower().split()[:3]
                    for word in desc_words:
                        # Only add meaningful words (length > 2)
                        if len(word) > 2 and word not in [kw.lower() for kw in self.skill_keywords[skill_name]]:
                            self.skill_keywords[skill_name].append(word)
        
        print(f"Updated skill keywords for {len(self.skill_keywords)} skills from {len(self.agents)} agents")
    
    def _extract_agent_capabilities(self):
        """Extract and organize agent capabilities for better routing decisions"""
        self.agent_capabilities = {}
        
        for agent_id, agent_card in self.agents.items():
            # Initialize capabilities dictionary for this agent
            self.agent_capabilities[agent_id] = {
                "name": agent_card.name,
                "description": agent_card.description,
                "url": agent_card.url,
                "skills": {},
                "domains": set(),
                "keywords": set(),
                "examples": []
            }
            
            # Extract capabilities from skills
            for skill in agent_card.skills:
                skill_id = skill.id if hasattr(skill, 'id') else skill.name.lower().replace(" ", "_")
                
                # Add skill details
                self.agent_capabilities[agent_id]["skills"][skill_id] = {
                    "name": skill.name,
                    "description": skill.description,
                    "tags": skill.tags if hasattr(skill, 'tags') and skill.tags else []
                }
                
                # Add examples if available
                if hasattr(skill, 'examples') and skill.examples:
                    self.agent_capabilities[agent_id]["examples"].extend(skill.examples)
                
                # Extract domains from skill names and descriptions
                if skill.name:
                    domain_words = [word.lower() for word in skill.name.split() if len(word) > 3]
                    self.agent_capabilities[agent_id]["domains"].update(domain_words)
                
                if skill.description:
                    domain_words = [word.lower() for word in skill.description.split() if len(word) > 3]
                    self.agent_capabilities[agent_id]["domains"].update(domain_words)
                
                # Add all tags as keywords
                if hasattr(skill, 'tags') and skill.tags:
                    self.agent_capabilities[agent_id]["keywords"].update([tag.lower() for tag in skill.tags])
            
            # Convert sets to lists for JSON serialization
            self.agent_capabilities[agent_id]["domains"] = list(self.agent_capabilities[agent_id]["domains"])
            self.agent_capabilities[agent_id]["keywords"] = list(self.agent_capabilities[agent_id]["keywords"])
        
        print(f"Extracted capabilities for {len(self.agent_capabilities)} agents")
    
    async def register_agent(self, endpoint: str) -> Dict:
        """Register a new agent by fetching its agent card from the endpoint"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as httpx_client:
                agent_card = await self._fetch_agent_card_with_a2a(httpx_client, endpoint)
                if agent_card:
                    # Generate agent_id from the endpoint
                    agent_id = agent_card.name
                    
                    # Add the agent to our registry
                    self.agents[agent_id] = agent_card
                    self._update_skill_keywords()
                    self._extract_agent_capabilities()
                    
                    return {
                        "success": True,
                        "agent_id": agent_id,
                        "agent_name": agent_card.name,
                        "endpoint": endpoint,
                        "message": f"Successfully registered {agent_card.name} from {endpoint}"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to fetch agent card from {endpoint}"
                    }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error registering agent from {endpoint}: {str(e)}"
            }
    
    def get_conversation_context(self, session_id: str) -> Dict[str, Any]:
        """Get conversation context for a session"""
        return self.context_manager.get_conversation_context(session_id)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about active sessions"""
        return self.context_manager.get_session_stats()
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        return self.context_manager.cleanup_expired_sessions()
    
    async def unregister_agent(self, agent_identifier: str) -> Dict:
        """Unregister an agent by agent_id, endpoint, or name"""
        try:
            agent_to_remove = None
            agent_id_to_remove = None
            
            # Try to find the agent by different identifiers
            for agent_id, agent_card in self.agents.items():
                # Match by agent_id
                if agent_id == agent_identifier:
                    agent_to_remove = agent_card
                    agent_id_to_remove = agent_id
                    break
                # Match by endpoint/URL
                elif agent_card.url == agent_identifier:
                    agent_to_remove = agent_card
                    agent_id_to_remove = agent_id
                    break
                # Match by name
                elif agent_card.name.lower() == agent_identifier.lower():
                    agent_to_remove = agent_card
                    agent_id_to_remove = agent_id
                    break
                # Match by partial endpoint (e.g., localhost:8080)
                elif agent_identifier in agent_card.url:
                    agent_to_remove = agent_card
                    agent_id_to_remove = agent_id
                    break
            
            if agent_to_remove and agent_id_to_remove:
                # Remove the agent from registry
                del self.agents[agent_id_to_remove]
                
                # Also remove from capabilities
                if agent_id_to_remove in self.agent_capabilities:
                    del self.agent_capabilities[agent_id_to_remove]
                
                self._update_skill_keywords()
                
                return {
                    "success": True,
                    "agent_id": agent_id_to_remove,
                    "agent_name": agent_to_remove.name,
                    "endpoint": agent_to_remove.url,
                    "message": f"Successfully unregistered {agent_to_remove.name} (ID: {agent_id_to_remove})"
                }
            else:
                return {
                    "success": False,
                    "error": f"Agent not found: {agent_identifier}. Available agents: {list(self.agents.keys())}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error unregistering agent {agent_identifier}: {str(e)}"
            }
    
    def get_available_agents(self) -> List[Dict]:
        """Get available agents in a format compatible with existing code"""
        agents = []
        for agent_id, agent_card in self.agents.items():
            agents.append({
                "agent_id": agent_id,
                "name": agent_card.name,
                "description": agent_card.description,
                "endpoint": agent_card.url,
                "skills": [{"name": skill.name, "description": skill.description} for skill in agent_card.skills],
                "keywords": [tag for skill in agent_card.skills for tag in (skill.tags or [])],
                "capabilities": [cap for cap, enabled in [
                    ("streaming", agent_card.capabilities.streaming),
                    ("state_transition_history", getattr(agent_card.capabilities, 'state_transition_history', False))
                ] if enabled]
            })
        return agents
    
    def _create_workflow(self):
        """Create LangGraph workflow for request routing"""
        workflow = StateGraph(RouterState)
        
        workflow.add_node("analyze", self._analyze_request)
        workflow.add_node("route", self._route_to_agent)
        
        workflow.add_edge("analyze", "route")
        workflow.set_entry_point("analyze")
        workflow.set_finish_point("route")
        
        return workflow.compile()
    
    async def _analyze_request(self, state: RouterState) -> RouterState:
        """Analyze the request and select the best agent using intelligent routing"""
        request = state["request"]
        
        # Log the start of agent selection
        print(f"\nAGENT SELECTION STARTED")
        print(f"Request: '{request}'")
        print(f"Available agents: {list(self.agents.keys())}")
        print(f"Analyzing {len(self.agents)} agents for best match...")
        
        # Get scores for all agents based on request content
        agent_scores = {}
        skill_matches = {}
        semantic_matches = {}
        
        for agent_id, agent_card in self.agents.items():
            # Calculate score using multiple methods for better accuracy
            keyword_score, matched_skills = self._calculate_keyword_score(request, agent_card)
            semantic_score, semantic_reasons = self._calculate_semantic_score(request, agent_id)
            
            # Combine scores with appropriate weights
            # Keyword matching is more precise but limited, semantic matching is broader
            combined_score = (keyword_score * 0.6) + (semantic_score * 0.4)
            
            agent_scores[agent_id] = combined_score
            skill_matches[agent_id] = matched_skills
            semantic_matches[agent_id] = semantic_reasons
            
            # Log detailed scoring for each agent
            print(f"\nAgent: {agent_card.name} (ID: {agent_id})")
            print(f"   Keyword Score: {keyword_score:.2f} (matched skills: {matched_skills})")
            print(f"   Semantic Score: {semantic_score:.2f} (reasons: {semantic_reasons})")
            print(f"   Combined Score: {combined_score:.2f}")
        
        # Find the best agent based on combined score
        best_agent = None
        best_score = 0.0
        
        for agent_id, score in agent_scores.items():
            if score > best_score:
                best_score = score
                best_agent = agent_id
        
        # Get number of agents for normalization
        num_agents = len(agent_scores)
        
        print(f"\nSCORING RESULTS:")
        print(f"   Best Agent: {best_agent}")
        print(f"   Best Score: {best_score:.2f}")
        print(f"   Number of Agents: {num_agents}")
        print(f"   All Scores: {[(aid, f'{score:.2f}') for aid, score in sorted(agent_scores.items(), key=lambda x: x[1], reverse=True)]}")
        
        # If no agent has a good score, don't default to any specific agent
        # This makes the orchestrator more flexible and not biased toward any agent
        if best_score < 0.2:  # Minimum threshold for confidence
            print(f"ERROR: No agent meets minimum threshold (0.2), best score was {best_score:.2f}")
            best_agent = None
            best_score = 0.0
            reasoning = "No agent has sufficient capability to handle this request"
        else:
            # Calculate confidence (0.0 to 1.0)
            # Normalize by number of agents to account for competition level
            # More agents = more competition, so same score gives lower confidence
            confidence = min(best_score / num_agents, 1.0) if num_agents > 0 else 0.0
            
            # Generate reasoning based on matched skills and semantic analysis
            if best_agent is not None:
                reasoning = self._generate_reasoning(
                    request, 
                    best_agent, 
                    agent_scores, 
                    skill_matches, 
                    semantic_matches
                )
            else:
                reasoning = "No suitable agent found"
        
        print(f"\nFINAL SELECTION:")
        print(f"   Selected Agent: {self.agents[best_agent].name if best_agent else 'None'}")
        print(f"   Confidence: {confidence if best_agent else 0.0:.2f}")
        print(f"   Reasoning: {reasoning}")
        print(f"AGENT SELECTION COMPLETED\n")
        
        # Update state with routing decision
        state.update({
            "selected_agent": best_agent if best_agent else "",
            "confidence": confidence if best_agent else 0.0,
            "reasoning": reasoning,
            "metadata": {
                "request_id": str(uuid.uuid4()),
                "start_timestamp": datetime.now().isoformat(),
                "agent_scores": agent_scores,
                "skill_matches": skill_matches,
                "semantic_matches": semantic_matches,
                "analysis_timestamp": datetime.now().isoformat()
            }
        })
        
        return state
    
    def _calculate_keyword_score(self, request: str, agent_card: AgentCard) -> Tuple[float, List[str]]:
        """
        Calculate score for an agent based on keywords and skills matching.
        
        Scoring mechanism:
        - Keyword matching from skill tags: +1.0 points per match
        - Skill matching via _skill_matches_request: +1.5 points per match
        
        Returns:
            tuple[float, List[str]]: (total_score, list_of_matched_skill_names)
        """
        score = 0.0
        matched_skills = []
        
        request_lower = request.lower()
        
        # Keyword matching from skill tags (weight: 1.0)
        keywords = [tag for skill in agent_card.skills for tag in (skill.tags or [])]
        for keyword in keywords:
            if keyword.lower() in request_lower:
                score += 1.0

        # Skill matching (weight: 1.5)
        for skill in agent_card.skills:
            if self._skill_matches_request(skill.name, request):
                score += 1.5
                matched_skills.append(skill.name)
        
        return score, matched_skills
    
    def _calculate_semantic_score(self, request: str, agent_id: str) -> Tuple[float, List[str]]:
        """
        Calculate semantic similarity score between request and agent capabilities.
        This provides a more nuanced understanding beyond simple keyword matching.
        
        Returns:
            tuple[float, List[str]]: (semantic_score, list_of_reasons)
        """
        score = 0.0
        reasons = []
        
        # Skip if agent not in capabilities
        if agent_id not in self.agent_capabilities:
            return 0.0, []
        
        agent_cap = self.agent_capabilities[agent_id]
        request_lower = request.lower()
        
        # Check for domain matches
        for domain in agent_cap["domains"]:
            if domain in request_lower:
                score += 0.5
                reasons.append(f"Request mentions domain: {domain}")
        
        # Check for keyword matches
        for keyword in agent_cap["keywords"]:
            if keyword in request_lower:
                score += 0.7
                reasons.append(f"Request contains keyword: {keyword}")
        
        # Check for example similarity
        for example in agent_cap["examples"]:
            # Simple similarity check - can be enhanced with embeddings
            if any(word in example.lower() for word in request_lower.split()):
                score += 0.3
                reasons.append(f"Request similar to example: {example}")
        
        # Check skill descriptions for relevance
        for skill_id, skill_info in agent_cap["skills"].items():
            description = skill_info["description"].lower()
            # Check if any significant words from request appear in description
            significant_words = [w for w in request_lower.split() if len(w) > 3]
            for word in significant_words:
                if word in description:
                    score += 0.4
                    reasons.append(f"Request term '{word}' matches skill: {skill_info['name']}")
        
        return score, reasons[:3]  # Return top 3 reasons only
    
    def _skill_matches_request(self, skill_name: str, request: str) -> bool:
        """Check if a skill matches the request content using dynamic keywords from available agents"""
        # Get keywords for this skill from the dynamically built skill_keywords
        keywords = self.skill_keywords.get(skill_name, [])
        request_lower = request.lower()
        
        return any(keyword in request_lower for keyword in keywords)
    
    def _generate_reasoning(
        self, 
        request: str, 
        selected_agent: str, 
        agent_scores: Dict, 
        skill_matches: Dict,
        semantic_matches: Dict
    ) -> str:
        """Generate human-readable reasoning for the routing decision"""
        if not selected_agent:
            return "No suitable agent found for this request"
            
        agent_card = self.agents[selected_agent]
        
        # Find matched keywords from skill tags
        matched_keywords = []
        request_lower = request.lower()
        keywords = [tag for skill in agent_card.skills for tag in (skill.tags or [])]

        for keyword in keywords:
            if keyword.lower() in request_lower:
                matched_keywords.append(keyword)
        
        # Get matched skills and semantic reasons
        matched_skills = skill_matches.get(selected_agent, [])
        semantic_reasons = semantic_matches.get(selected_agent, [])
        
        reasoning_parts = [f"Selected {agent_card.name}"]
        
        if matched_keywords:
            reasoning_parts.append(f"based on keywords: {', '.join(matched_keywords)}")
        
        if matched_skills:
            if matched_keywords:
                reasoning_parts.append(f"and skills: {', '.join(matched_skills)}")
            else:
                reasoning_parts.append(f"based on skills: {', '.join(matched_skills)}")
        
        if semantic_reasons:
            reasoning_parts.append(f"with additional context: {'; '.join(semantic_reasons)}")
        
        if not matched_keywords and not matched_skills and not semantic_reasons:
            reasoning_parts.append("based on best overall capability match")
        
        return " ".join(reasoning_parts)
    
    async def _route_to_agent(self, state: RouterState) -> RouterState:
        """Route the request to the selected agent"""
        selected_agent = state["selected_agent"]
        request = state["request"]
        
        # Handle case where no suitable agent was found
        if not selected_agent:
            print(f"WARNING: No agent selected - returning error message")
            state["response"] = "No suitable agent found for this request. Please try a different query or register additional agents."
            state["metadata"]["status"] = "no_agent_found"
            state["metadata"]["response_timestamp"] = datetime.now().isoformat()
            return state
        
        agent_card = self.agents[selected_agent]
        endpoint = agent_card.url
        
        print(f"\nROUTING REQUEST TO AGENT")
        print(f"   Agent: {agent_card.name} (ID: {selected_agent})")
        print(f"   Endpoint: {endpoint}")
        print(f"   Request: '{request}'")
        
        state["metadata"]["agent_endpoint"] = endpoint
        
        try:
            # Get conversation context - always include recent turns for better context awareness
            context_data = None
            request_lower = request.lower()
            is_report_request = any(
                keyword in request_lower 
                for keyword in ['report', 'generate', 'create', 'make']
            )
            
            # Get conversation history
            context = self.context_manager.get_conversation_context(
                state["session_id"], 
                last_n_turns=3  # Include last 3 turns for better context
            )
            
            if context.get("turns") and len(context["turns"]) >= 1:
                # Format conversation turns for context (used for both report and non-report requests)
                conversation_history = []
                for turn in context["turns"]:
                    conversation_history.append({
                        "user_query": turn.get("user_query", ""),
                        "agent_name": turn.get("agent_name", ""),
                        "agent_response": turn.get("agent_response", "")[:500]  # Limit response length
                    })
                
                # Get previous turn information
                previous_turn = context["turns"][-1]
                
                # For report requests: also include full previous data if from data source agent
                previous_data = None
                if is_report_request:
                    data_agents = ['RAG Agent', 'rag', 'search', 'query', 'weather']
                    is_data_source = any(
                        agent.lower() in previous_turn.get("agent_name", "").lower() 
                        for agent in data_agents
                    )
                    if is_data_source:
                        previous_data = previous_turn.get("agent_response", "")
                        print(
                            f"   Found data context from previous {previous_turn.get('agent_name', 'Unknown')} "
                            f"response for report generation"
                        )
                
                # Create context data (same structure for both report and non-report requests)
                context_data = {
                    "conversation_turns": conversation_history,
                    "previous_agent": previous_turn.get("agent_name", "Unknown"),
                    "previous_query": previous_turn.get("user_query", ""),
                    "previous_data": previous_data
                }
                
                request_type = "report generation" if is_report_request else "request"
                print(
                    f"   Including conversation context ({len(conversation_history)} previous turns) "
                    f"for {request_type}"
                )
            
            print(f"   Forwarding request to agent...")
            # Forward the request to the selected agent and get the actual response
            actual_response = await self._forward_request_to_agent(endpoint, request, state["session_id"], context_data)
            print(f"   Received response from agent: '{actual_response[:100]}{'...' if len(actual_response) > 100 else ''}'")
            state["response"] = f"Routed to {agent_card.name}: {actual_response}"
            state["metadata"]["status"] = "completed"
        except Exception as e:
            error_msg = str(e)
            print(f"   ERROR: Failed to forward request: {error_msg}")
            import traceback
            print(f"   Full traceback: {traceback.format_exc()}")
            # Fallback to routing information if forwarding fails
            state["response"] = f"Smart Routing Decision\n\n"
            state["response"] += f"Selected Agent: {agent_card.name}\n"
            state["response"] += f"Endpoint: {endpoint}\n"
            state["response"] += f"Confidence: {state.get('confidence', 0):.2f}\n"
            state["response"] += f"Reasoning: {state.get('reasoning', 'No reasoning provided')}\n\n"
            state["response"] += f"WARNING: Could not forward request: {error_msg}\n"
            state["response"] += f"Connect directly to {agent_card.name} at {endpoint}"
            state["metadata"]["status"] = "routing_only"
            state["metadata"]["error"] = error_msg
        
        print(f"REQUEST ROUTING COMPLETED\n")
        
        state["metadata"]["response_timestamp"] = datetime.now().isoformat()
        
        return state
    
    async def _forward_request_to_agent(self, endpoint: str, request: str, session_id: str, context_data: Optional[Dict] = None) -> str:
        """Forward request to agent using A2A protocol with consistent session ID"""
        import json
        from uuid import uuid4, UUID
        
        # Validate session_id is a valid UUID
        try:
            # Ensure session_id is a valid UUID string
            validated_uuid = UUID(session_id)
            context_id = str(validated_uuid)
        except (ValueError, TypeError, AttributeError):
            # If invalid, get a valid session from context manager
            print(f"WARNING: Invalid session_id '{session_id}' - getting valid session from context manager")
            context_id = self.context_manager.get_or_create_session(session_id)
        
        # Enhance request with context data if provided
        enhanced_request = request
        if context_data:
            request_lower = request.lower()
            is_report_request = any(
                keyword in request_lower 
                for keyword in ['report', 'generate', 'create', 'make']
            )
            
            # For report requests: include both conversation history AND previous data
            if is_report_request:
                context_parts = []
                
                # Add conversation history if available
                if context_data.get("conversation_turns"):
                    history_text = "Previous conversation:\n"
                    for i, turn in enumerate(context_data["conversation_turns"], 1):
                        history_text += (
                            f"\n[{i}] User: {turn['user_query']}\n"
                            f"    {turn['agent_name']}: {turn['agent_response'][:200]}...\n"
                        )
                    context_parts.append(history_text)
                
                # Add full previous data if available (from data source agents)
                if context_data.get("previous_data"):
                    context_parts.append(
                        f"Detailed data from most recent query:\n"
                        f"{context_data['previous_data']}\n"
                    )
                
                # Combine all context parts
                if context_parts:
                    if "report" in request_lower or "generate" in request_lower or "create" in request_lower:
                        instruction = "Please use the above conversation context and data to generate a comprehensive report."
                    elif "analyze" in request_lower or "analysis" in request_lower:
                        instruction = "Please analyze the above conversation context and data."
                    elif "summarize" in request_lower or "summarise" in request_lower:
                        instruction = "Please summarize the above conversation context and data."
                    else:
                        instruction = "Please use the above conversation context and data as needed."
                    
                    enhanced_request = (
                        f"{request}\n\n"
                        f"{''.join(context_parts)}\n"
                        f"{instruction}"
                    )
                    print(
                        f"   Enhanced report request with conversation context "
                        f"({len(context_data.get('conversation_turns', []))} turns) "
                        f"and previous data"
                    )
            
            # For non-report requests: include conversation history
            elif context_data.get("conversation_turns"):
                # Format conversation history
                history_text = "Previous conversation:\n"
                for i, turn in enumerate(context_data["conversation_turns"], 1):
                    history_text += (
                        f"\n[{i}] User: {turn['user_query']}\n"
                        f"    {turn['agent_name']}: {turn['agent_response'][:200]}...\n"
                    )
                
                enhanced_request = (
                    f"{request}\n\n"
                    f"{history_text}\n"
                    f"Please use the above conversation context to answer the current request."
                )
                print(
                    f"   Enhanced request with conversation context "
                    f"({len(context_data['conversation_turns'])} turns)"
                )
        
        # Create A2A JSON-RPC request payload using message/send method
        task_id = str(uuid4())
        message_id = str(uuid4())
        
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid4()),
            "method": "message/send",
            "params": {
                "id": task_id,
                "message": {
                    "role": "user",
                    "messageId": message_id,
                    "contextId": context_id,
                    "parts": [
                        {
                            "type": "text",
                            "text": enhanced_request
                        }
                    ]
                },
                "configuration": {
                    "acceptedOutputModes": ["text"]
                }
            }
        }
        
        try:
            # Ensure endpoint doesn't have trailing slash for POST requests (A2A protocol expects root)
            endpoint_clean = endpoint.rstrip('/')
            print(f"   Sending A2A request to {endpoint_clean}")
            print(f"   Payload method: {payload.get('method')}")
            print(f"   Payload params keys: {list(payload.get('params', {}).keys())}")
            
            # Increased timeout for RAG agent which may take longer to process
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Send task to agent - A2A protocol expects POST to root endpoint
                print(f"   POST request to {endpoint_clean}...")
                try:
                    response = await client.post(
                        endpoint_clean,
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    )
                    print(f"   Response status: {response.status_code}")
                    print(f"   Response headers: {dict(response.headers)}")
                    print(f"   Response text (first 500 chars): {response.text[:500]}")
                except httpx.ConnectError as conn_err:
                    print(f"   CONNECTION ERROR DETAILS: {conn_err}")
                    print(f"   Error type: {type(conn_err)}")
                    raise
                except httpx.HTTPStatusError as http_err:
                    print(f"   HTTP ERROR DETAILS: Status {http_err.response.status_code}")
                    print(f"   Response text: {http_err.response.text[:500]}")
                    raise
                response.raise_for_status()
                
                result = response.json()
                print(f"   Response JSON keys: {list(result.keys())}")
                
                # Check for JSON-RPC error
                if "error" in result:
                    error_details = result['error']
                    print(f"   JSON-RPC error: {error_details}")
                    raise Exception(f"Agent returned JSON-RPC error: {error_details}")
                
                # Get the response from message/send
                if "result" not in result:
                    raise Exception("No result in agent response")
                
                message_result = result["result"]
                
                # For message/send, the response might be a Task or Message
                if isinstance(message_result, dict):
                    # If it's a Task, we need to poll for completion
                    if "id" in message_result and "status" in message_result:
                        task_id = message_result["id"]
                        
                        # Poll for task completion - RAG agent may need more time for processing
                        max_attempts = 120  # Poll for up to 120 seconds (2 minutes)
                        poll_interval = 1  # Check every second
                        
                        print(f"   Polling for task completion (task_id: {task_id})...")
                        for attempt in range(max_attempts):
                            if attempt > 0:  # Don't sleep on first attempt
                                await asyncio.sleep(poll_interval)
                            
                            if attempt % 10 == 0:  # Log every 10 seconds
                                print(f"   Polling attempt {attempt + 1}/{max_attempts}...")
                            
                            get_payload = {
                                "jsonrpc": "2.0",
                                "id": str(uuid4()),
                                "method": "tasks/get",
                                "params": {
                                    "id": task_id
                                }
                            }
                            
                            try:
                                get_response = await client.post(
                                    endpoint_clean,
                                    json=get_payload,
                                    headers={"Content-Type": "application/json"},
                                    timeout=5.0  # Individual request timeout
                                )
                                get_response.raise_for_status()
                                
                                get_result = get_response.json()
                                
                                if "result" in get_result and get_result["result"]:
                                    task_data = get_result["result"]
                                    
                                    # Check task state
                                    task_state = task_data.get("status", {}).get("state")
                                    print(f"   Task state: {task_state} (attempt {attempt + 1})")
                                    
                                    if task_state == "completed":
                                        # Extract response from artifacts
                                        artifacts = task_data.get("artifacts", [])
                                        if artifacts:
                                            for artifact in artifacts:
                                                parts = artifact.get("parts", [])
                                                for part in parts:
                                                    if part.get("kind") == "text":
                                                        return part.get("text", "No text in response")
                                        
                                        return "Task completed but no response text found"
                                    elif task_state == "failed":
                                        error_msg = task_data.get("status", {}).get("message", {})
                                        if error_msg and isinstance(error_msg, dict):
                                            parts = error_msg.get("parts", [])
                                            for part in parts:
                                                if part.get("kind") == "text":
                                                    return f"Agent task failed: {part.get('text', 'Unknown error')}"
                                        return "Agent task failed"
                                    elif task_state == "input-required":
                                        # Extract response from status message for input-required state
                                        status_message = task_data.get("status", {}).get("message", {})
                                        if status_message:
                                            parts = status_message.get("parts", [])
                                            for part in parts:
                                                if part.get("kind") == "text":
                                                    return part.get("text", "No text in input-required response")
                                        return "Agent requires input but no message provided"
                                    
                                    # If still working or pending, continue polling
                                    if task_state in ["working", "pending"]:
                                        continue
                                    
                                    # Unknown state, log and continue polling
                                    print(f"   Unknown task state: {task_state}, continuing to poll...")
                                    continue
                                    
                            except Exception as poll_err:
                                print(f"   Polling error (attempt {attempt + 1}): {poll_err}")
                                # Continue polling on individual request errors
                                if attempt < max_attempts - 1:
                                    continue
                                else:
                                    raise
                        
                        print(f"   WARNING: Task did not complete within {max_attempts * poll_interval} seconds")
                        return f"Task did not complete within {max_attempts * poll_interval} seconds timeout"
                    
                    # If it's a direct Message response
                    elif "parts" in message_result:
                        for part in message_result.get("parts", []):
                            if part.get("type") == "text":
                                return part.get("text", "No text in message")
                        return "Message received but no text content"
                
                return "Unexpected response format from agent"
                
        except httpx.ConnectError as e:
            error_msg = f"Could not connect to agent at {endpoint}. Make sure the agent is running. Error: {str(e)}"
            print(f"   CONNECTION ERROR: {error_msg}")
            raise Exception(error_msg)
        except httpx.TimeoutException as e:
            error_msg = f"Request to agent at {endpoint} timed out. Error: {str(e)}"
            print(f"   TIMEOUT ERROR: {error_msg}")
            raise Exception(error_msg)
        except httpx.HTTPStatusError as e:
            error_msg = f"Agent at {endpoint} returned HTTP {e.response.status_code}: {e.response.text[:200]}"
            print(f"   HTTP ERROR: {error_msg}")
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Request forwarding failed: {str(e)}"
            print(f"   GENERAL ERROR: {error_msg}")
            import traceback
            print(f"   TRACEBACK: {traceback.format_exc()}")
            raise Exception(error_msg)

    async def process_request(self, request: str, session_id: Optional[str] = None) -> Dict:
        """Process a request through the LangGraph workflow with context management"""
        # Log incoming session_id for debugging
        print(f"process_request called with session_id: {session_id} (type: {type(session_id)})")
        
        # Get or create session
        session_id = self.context_manager.get_or_create_session(session_id)
        print(f"Validated session_id: {session_id}")
        
        # Store original request
        original_request = request
        
        # Enrich request with context if needed
        enriched_request = self.context_manager.enrich_query_with_context(session_id, request)
        
        # Log context enrichment if it occurred
        context_enriched = enriched_request != request
        if context_enriched:
            print(f"Context Enrichment Applied:")
            print(f"   Original: '{request}'")
            print(f"   Enriched: '{enriched_request}'")
        
        initial_state = RouterState(
            request=enriched_request,
            original_request=original_request,
            session_id=session_id,
            selected_agent="",
            confidence=0.0,
            reasoning="",
            response="",
            error="",
            metadata={"context_enriched": context_enriched}
        )
        
        try:
            final_state = await self.workflow.ainvoke(initial_state)
            
            # Handle case where no agent was selected
            if not final_state["selected_agent"]:
                return {
                    "success": True,
                    "request": request,
                    "original_request": final_state["original_request"],
                    "enriched_request": final_state["request"],
                    "session_id": final_state["session_id"],
                    "selected_agent_id": "",
                    "selected_agent_name": "None",
                    "agent_skills": [],
                    "confidence": 0.0,
                    "reasoning": final_state["reasoning"],
                    "response": final_state["response"],
                    "metadata": final_state["metadata"],
                    "context_enriched": final_state["metadata"].get("context_enriched", False)
                }
            
            # Check if selected agent exists in registry
            selected_agent_id = final_state["selected_agent"]
            if selected_agent_id not in self.agents:
                return {
                    "success": False,
                    "request": request,
                    "session_id": session_id,
                    "error": f"Selected agent '{selected_agent_id}' not found in registry. Available agents: {list(self.agents.keys())}",
                    "metadata": {
                        "request_id": str(uuid.uuid4()),
                        "error_timestamp": datetime.now().isoformat(),
                        "selected_agent_id": selected_agent_id
                    }
                }
            
            agent_card = self.agents[selected_agent_id]
            
            # Record conversation turn for context management
            if final_state["selected_agent"]:
                self.context_manager.add_conversation_turn(
                    session_id=final_state["session_id"],
                    user_query=final_state["original_request"],
                    agent_name=agent_card.name,
                    agent_response=final_state["response"],
                    routing_confidence=final_state["confidence"],
                    metadata={
                        "agent_id": final_state["selected_agent"],
                        "reasoning": final_state["reasoning"],
                        "context_enriched": final_state["metadata"].get("context_enriched", False)
                    }
                )
            
            return {
                "success": True,
                "request": request,
                "original_request": final_state["original_request"],
                "enriched_request": final_state["request"],
                "session_id": final_state["session_id"],
                "selected_agent_id": final_state["selected_agent"],
                "selected_agent_name": agent_card.name,
                "agent_skills": [skill.name for skill in agent_card.skills],
                "confidence": final_state["confidence"],
                "reasoning": final_state["reasoning"],
                "response": final_state["response"],
                "metadata": final_state["metadata"],
                "context_enriched": final_state["metadata"].get("context_enriched", False)
            }
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"ERROR: Error in process_request: {str(e)}")
            print(f"Traceback:\n{error_trace}")
            return {
                "success": False,
                "request": request,
                "session_id": session_id,
                "error": f"{str(e)}",
                "metadata": {
                    "request_id": str(uuid.uuid4()),
                    "error_timestamp": datetime.now().isoformat(),
                    "error_type": type(e).__name__
                }
            }