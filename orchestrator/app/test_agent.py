"""
Simple pytest tests for SmartOrchestrator
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import os
from app.orchestrator import SmartOrchestrator, RouterState


class TestSmartOrchestrator:
    """Test suite for SmartOrchestrator"""
    
    @patch('app.orchestrator.SmartOrchestrator._initialize_default_agents')
    def test_orchestrator_initialization(self, mock_init):
        """Test that SmartOrchestrator can be initialized"""
        mock_init.return_value = None
        orchestrator = SmartOrchestrator()
        assert orchestrator is not None
        assert hasattr(orchestrator, 'agents')
        assert hasattr(orchestrator, 'workflow')
        assert hasattr(orchestrator, 'context_manager')
    
    def test_router_state_typing(self):
        """Test RouterState TypedDict structure"""
        state = RouterState(
            request="test request",
            original_request="test request",
            session_id="test-session",
            selected_agent="",
            confidence=0.0,
            reasoning="",
            response="",
            error="",
            metadata={}
        )
        assert state["request"] == "test request"
        assert state["session_id"] == "test-session"
    
    @patch('app.orchestrator.SmartOrchestrator._initialize_default_agents')
    def test_get_available_agents_structure(self, mock_init):
        """Test that get_available_agents returns a list"""
        mock_init.return_value = None
        orchestrator = SmartOrchestrator()
        agents = orchestrator.get_available_agents()
        assert isinstance(agents, list)
    
    @patch('app.orchestrator.SmartOrchestrator._initialize_default_agents')
    def test_get_conversation_context(self, mock_init):
        """Test that get_conversation_context returns a dict"""
        mock_init.return_value = None
        orchestrator = SmartOrchestrator()
        context = orchestrator.get_conversation_context("test-session")
        assert isinstance(context, dict)
    
    @patch('app.orchestrator.SmartOrchestrator._initialize_default_agents')
    def test_get_session_stats(self, mock_init):
        """Test that get_session_stats returns a dict"""
        mock_init.return_value = None
        orchestrator = SmartOrchestrator()
        stats = orchestrator.get_session_stats()
        assert isinstance(stats, dict)
    
    @patch('app.orchestrator.SmartOrchestrator._initialize_default_agents')
    def test_cleanup_expired_sessions(self, mock_init):
        """Test that cleanup_expired_sessions returns an int"""
        mock_init.return_value = None
        orchestrator = SmartOrchestrator()
        count = orchestrator.cleanup_expired_sessions()
        assert isinstance(count, int)
        assert count >= 0
    
    @patch('app.orchestrator.SmartOrchestrator._initialize_default_agents')
    @pytest.mark.asyncio
    async def test_register_agent_structure(self, mock_init):
        """Test that register_agent returns expected structure"""
        mock_init.return_value = None
        orchestrator = SmartOrchestrator()
        
        with patch('app.orchestrator.httpx.AsyncClient') as mock_client:
            # Mock failed agent registration
            mock_response = Mock()
            mock_response.status_code = 404
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=Exception("Connection failed")
            )
            
            result = await orchestrator.register_agent("http://localhost:9999")
            assert isinstance(result, dict)
            assert 'success' in result
    
    @patch('app.orchestrator.SmartOrchestrator._initialize_default_agents')
    @pytest.mark.asyncio
    async def test_unregister_agent_structure(self, mock_init):
        """Test that unregister_agent returns expected structure"""
        mock_init.return_value = None
        orchestrator = SmartOrchestrator()
        
        result = await orchestrator.unregister_agent("non-existent-agent")
        assert isinstance(result, dict)
        assert 'success' in result
        assert result['success'] is False

