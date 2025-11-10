"""
Simple pytest tests for RAGAgent
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import sys
from pathlib import Path

# Add the parent directory to path for imports
current_dir = Path(__file__).parent
rag_dir = current_dir.parent.parent
sys.path.insert(0, str(rag_dir))

from app.agent import RAGAgent, ResponseFormat


class TestRAGAgent:
    """Test suite for RAGAgent"""
    
    @patch('app.agent.VectorStore')
    def test_agent_initialization(self, mock_vectorstore):
        """Test that RAGAgent can be initialized"""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            mock_vs = Mock()
            mock_vs.vs = Mock()
            mock_vectorstore.return_value = mock_vs
            
            agent = RAGAgent(mock_vs)
            assert agent is not None
            assert agent.model is not None
            assert agent.vs is not None
            assert len(agent.tools) > 0
            assert agent.graph is not None
    
    def test_supported_content_types(self):
        """Test that SUPPORTED_CONTENT_TYPES is defined"""
        assert hasattr(RAGAgent, 'SUPPORTED_CONTENT_TYPES')
        assert isinstance(RAGAgent.SUPPORTED_CONTENT_TYPES, list)
        assert len(RAGAgent.SUPPORTED_CONTENT_TYPES) > 0
    
    def test_response_format_model(self):
        """Test ResponseFormat model"""
        response = ResponseFormat(status='completed', message='Test message')
        assert response.status == 'completed'
        assert response.message == 'Test message'
    
    @patch('app.agent.VectorStore')
    def test_get_agent_response_structure(self, mock_vectorstore):
        """Test that get_agent_response returns expected structure"""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            mock_vs = Mock()
            mock_vs.vs = Mock()
            mock_vectorstore.return_value = mock_vs
            
            agent = RAGAgent(mock_vs)
            config = {'configurable': {'thread_id': 'test-context'}}
            
            # Mock the graph state
            mock_state = Mock()
            mock_state.values = {}
            agent.graph.get_state = Mock(return_value=mock_state)
            
            response = agent.get_agent_response(config)
            assert isinstance(response, dict)
            assert 'is_task_complete' in response
            assert 'require_user_input' in response
            assert 'content' in response
    
    @patch('app.agent.VectorStore')
    def test_invoke_structure(self, mock_vectorstore):
        """Test that invoke returns expected structure"""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            mock_vs = Mock()
            mock_vs.vs = None  # Simulate uninitialized vector store
            mock_vectorstore.return_value = mock_vs
            
            agent = RAGAgent(mock_vs)
            result = agent.invoke("test query", "test-context")
            
            assert isinstance(result, dict)
            assert 'is_task_complete' in result
            assert 'require_user_input' in result
            assert 'content' in result

