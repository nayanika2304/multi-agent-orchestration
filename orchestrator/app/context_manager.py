#!/usr/bin/env python3
"""
Orchestrator Context Manager

Maintains conversation context across multiple agents to enable
seamless multi-agent conversations with context continuity.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import re

@dataclass
class ConversationTurn:
    """Represents a single turn in a conversation"""
    timestamp: datetime
    user_query: str
    agent_name: str
    agent_response: str
    routing_confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ConversationSession:
    """Represents a complete conversation session"""
    session_id: str
    user_id: Optional[str]
    created_at: datetime
    last_activity: datetime
    turns: List[ConversationTurn] = field(default_factory=list)
    context_summary: Optional[str] = None
    active_topics: List[str] = field(default_factory=list)

class OrchestratorContextManager:
    """
    Manages conversation context across multiple agents.
    
    Features:
    - Session-based conversation tracking
    - Context enrichment for agent queries
    - Pronoun and reference resolution
    - Topic tracking and context summarization
    - Cross-agent context sharing
    """
    
    def __init__(self, session_timeout_hours: int = 24):
        self.sessions: Dict[str, ConversationSession] = {}
        self.session_timeout = timedelta(hours=session_timeout_hours)
        
        # Reference resolution patterns
        self.pronoun_patterns = [
            r'\bit\b', r'\bthat\b', r'\bthis\b', r'\bthey\b', r'\bthem\b',
            r'\bthe above\b', r'\bthe previous\b', r'\bthe data\b'
        ]
        
    def get_or_create_session(self, session_id: Optional[str] = None, user_id: Optional[str] = None) -> str:
        """Get existing session or create new one"""
        if session_id and session_id in self.sessions:
            # Update last activity
            self.sessions[session_id].last_activity = datetime.now()
            return session_id
        
        # Create new session
        new_session_id = session_id or str(uuid.uuid4())
        self.sessions[new_session_id] = ConversationSession(
            session_id=new_session_id,
            user_id=user_id,
            created_at=datetime.now(),
            last_activity=datetime.now()
        )
        return new_session_id
    
    def add_conversation_turn(
        self, 
        session_id: str, 
        user_query: str, 
        agent_name: str, 
        agent_response: str,
        routing_confidence: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a conversation turn to the session"""
        if session_id not in self.sessions:
            self.get_or_create_session(session_id)
        
        session = self.sessions[session_id]
        turn = ConversationTurn(
            timestamp=datetime.now(),
            user_query=user_query,
            agent_name=agent_name,
            agent_response=agent_response,
            routing_confidence=routing_confidence,
            metadata=metadata or {}
        )
        
        session.turns.append(turn)
        session.last_activity = datetime.now()
        
        # Update active topics
        self._update_active_topics(session, user_query, agent_response)
    
    def _update_active_topics(self, session: ConversationSession, user_query: str, agent_response: str) -> None:
        """Extract and update active topics from conversation"""
        # Simple topic extraction (can be enhanced with NLP)
        topics = []
        
        # Extract potential topics from queries and responses
        text = f"{user_query} {agent_response}".lower()
        
        # Weather-related topics
        if any(word in text for word in ['weather', 'temperature', 'winter', 'summer', 'rain', 'snow']):
            topics.append('weather')
        
        # Location topics
        cities = ['new york', 'california', 'chicago', 'boston', 'san francisco', 'los angeles']
        for city in cities:
            if city in text:
                topics.append(f'location:{city}')
        
        # Report topics
        if any(word in text for word in ['report', 'analysis', 'chart', 'graph', 'visualization']):
            topics.append('reporting')
        
        # Financial topics
        if any(word in text for word in ['currency', 'exchange', 'dollar', 'price', 'market']):
            topics.append('finance')
        
        # Update session topics (keep only recent topics)
        for topic in topics:
            if topic not in session.active_topics:
                session.active_topics.append(topic)
        
        # Keep only last 5 topics
        session.active_topics = session.active_topics[-5:]
    
    def get_conversation_context(self, session_id: str, last_n_turns: int = 3) -> Dict[str, Any]:
        """Get conversation context for a session"""
        if session_id not in self.sessions:
            return {"turns": [], "summary": None, "active_topics": []}
        
        session = self.sessions[session_id]
        recent_turns = session.turns[-last_n_turns:] if session.turns else []
        
        return {
            "session_id": session_id,
            "turns": [
                {
                    "user_query": turn.user_query,
                    "agent_name": turn.agent_name,
                    "agent_response": turn.agent_response,
                    "timestamp": turn.timestamp.isoformat(),
                    "confidence": turn.routing_confidence
                }
                for turn in recent_turns
            ],
            "summary": session.context_summary,
            "active_topics": session.active_topics,
            "last_activity": session.last_activity.isoformat()
        }
    
    def enrich_query_with_context(self, session_id: str, user_query: str) -> str:
        """Enrich user query with previous conversation context"""
        if session_id not in self.sessions:
            return user_query
        
        session = self.sessions[session_id]
        if not session.turns:
            return user_query
        
        # Check if query contains pronouns/references that need resolution
        needs_context = any(re.search(pattern, user_query.lower()) for pattern in self.pronoun_patterns)
        
        if not needs_context:
            return user_query
        
        # Get the most recent turn for context
        last_turn = session.turns[-1]
        
        # Build enriched query
        enriched_query = self._resolve_references(user_query, last_turn)
        
        return enriched_query
    
    def _resolve_references(self, user_query: str, last_turn: ConversationTurn) -> str:
        """Resolve pronouns and references in user query"""
        enriched_query = user_query
        
        # Extract key information from last turn
        last_query = last_turn.user_query
        last_response = last_turn.agent_response
        
        # Simple reference resolution patterns
        replacements = {
            r'\bit\b': self._extract_main_topic(last_query, last_response),
            r'\bthat\b': self._extract_main_topic(last_query, last_response),
            r'\bthis\b': self._extract_main_topic(last_query, last_response),
            r'\bthe above\b': f"the analysis: {last_response[:100]}...",
            r'\bthe previous\b': f"the previous query about {self._extract_subject(last_query)}",
            r'\bthe data\b': f"the data from: {last_response[:100]}..."
        }
        
        for pattern, replacement in replacements.items():
            if replacement:
                enriched_query = re.sub(pattern, replacement, enriched_query, flags=re.IGNORECASE)
        
        # If query is still unclear, add explicit context
        if len(enriched_query.split()) < 5 and any(word in enriched_query.lower() for word in ['it', 'that', 'this']):
            enriched_query = f"{enriched_query} [Context: Previous query was '{last_query}' with response about: {last_response[:150]}...]"
        
        return enriched_query
    
    def _extract_main_topic(self, query: str, response: str) -> str:
        """Extract the main topic from query and response"""
        # Look for location + weather pattern
        locations = re.findall(r'\b(New York|NYC|California|Chicago|Boston|San Francisco|Los Angeles)\b', query, re.IGNORECASE)
        weather_terms = re.findall(r'\b(weather|winter|summer|temperature|climate)\b', query, re.IGNORECASE)
        
        if locations and weather_terms:
            return f"{weather_terms[0]} in {locations[0]}"
        
        # Look for other specific topics
        if 'currency' in query.lower() or 'exchange' in query.lower():
            return "currency exchange analysis"
        
        if 'math' in query.lower() or any(op in query for op in ['+', '-', '*', '/']):
            return "mathematical calculation"
        
        # Fallback to first meaningful words from response
        response_words = response.split()[:10]
        meaningful_words = [word for word in response_words if len(word) > 3]
        if meaningful_words:
            return " ".join(meaningful_words[:3])
        
        return "the previous analysis"
    
    def _extract_subject(self, query: str) -> str:
        """Extract the main subject from a query"""
        # Simple subject extraction
        words = query.split()
        if len(words) > 2:
            return " ".join(words[-3:])  # Last few words often contain the subject
        return query
    
    def get_conversation_summary(self, session_id: str) -> Optional[str]:
        """Generate a summary of the conversation"""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        if not session.turns:
            return None
        
        # Simple summarization (can be enhanced with LLM)
        topics = list(set(session.active_topics))
        agents_used = list(set(turn.agent_name for turn in session.turns))
        turn_count = len(session.turns)
        
        summary = f"Conversation with {turn_count} turns involving {', '.join(agents_used)}. "
        if topics:
            summary += f"Topics discussed: {', '.join(topics)}."
        
        return summary
    
    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions and return count of removed sessions"""
        now = datetime.now()
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if now - session.last_activity > self.session_timeout
        ]
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
        
        return len(expired_sessions)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about active sessions"""
        return {
            "total_sessions": len(self.sessions),
            "total_turns": sum(len(session.turns) for session in self.sessions.values()),
            "active_topics": list(set(
                topic for session in self.sessions.values() 
                for topic in session.active_topics
            )),
            "agents_used": list(set(
                turn.agent_name for session in self.sessions.values()
                for turn in session.turns
            ))
        }
