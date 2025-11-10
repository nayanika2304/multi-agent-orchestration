"""
Simple pytest tests for CurrencyAgent
"""
import pytest
from unittest.mock import Mock, patch
import os
from app.agent import CurrencyAgent, get_exchange_rate, ResponseFormat


class TestCurrencyAgent:
    """Test suite for CurrencyAgent"""
    
    def test_agent_initialization(self):
        """Test that CurrencyAgent can be initialized"""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            agent = CurrencyAgent()
            assert agent is not None
            assert agent.model is not None
            assert len(agent.tools) > 0
            assert agent.graph is not None
    
    def test_supported_content_types(self):
        """Test that SUPPORTED_CONTENT_TYPES is defined"""
        assert hasattr(CurrencyAgent, 'SUPPORTED_CONTENT_TYPES')
        assert isinstance(CurrencyAgent.SUPPORTED_CONTENT_TYPES, list)
        assert len(CurrencyAgent.SUPPORTED_CONTENT_TYPES) > 0
    
    def test_response_format_model(self):
        """Test ResponseFormat model"""
        response = ResponseFormat(status='completed', message='Test message')
        assert response.status == 'completed'
        assert response.message == 'Test message'
    
    def test_get_exchange_rate_tool_exists(self):
        """Test that get_exchange_rate tool is defined"""
        assert callable(get_exchange_rate)
        assert hasattr(get_exchange_rate, 'name')
    
    @patch('httpx.get')
    def test_get_exchange_rate_tool_success(self, mock_get):
        """Test get_exchange_rate tool with successful API response"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'rates': {'EUR': 0.85},
            'base': 'USD'
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Use invoke() method for LangChain tools
        result = get_exchange_rate.invoke({'currency_from': 'USD', 'currency_to': 'EUR', 'currency_date': 'latest'})
        assert 'rates' in result or 'error' not in result
    
    def test_get_agent_response_structure(self):
        """Test that get_agent_response returns expected structure"""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            agent = CurrencyAgent()
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

