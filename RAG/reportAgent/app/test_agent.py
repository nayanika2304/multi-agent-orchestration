"""
Simple pytest tests for ReportAgent
"""
import pytest
from unittest.mock import Mock, patch
import os
from app.agent import ReportAgent, ResponseFormat, generate_chart, save_pdf


class TestReportAgent:
    """Test suite for ReportAgent"""
    
    def test_agent_initialization(self):
        """Test that ReportAgent can be initialized"""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            agent = ReportAgent()
            assert agent is not None
            assert agent.model is not None
            assert len(agent.tools) > 0
            assert agent.graph is not None
    
    def test_supported_content_types(self):
        """Test that SUPPORTED_CONTENT_TYPES is defined"""
        assert hasattr(ReportAgent, 'SUPPORTED_CONTENT_TYPES')
        assert isinstance(ReportAgent.SUPPORTED_CONTENT_TYPES, list)
        assert len(ReportAgent.SUPPORTED_CONTENT_TYPES) > 0
    
    def test_response_format_model(self):
        """Test ResponseFormat model"""
        response = ResponseFormat(status='completed', message='Test message')
        assert response.status == 'completed'
        assert response.message == 'Test message'
    
    def test_generate_chart_tool_exists(self):
        """Test that generate_chart tool is defined"""
        assert callable(generate_chart)
        assert hasattr(generate_chart, 'name')
    
    def test_save_pdf_tool_exists(self):
        """Test that save_pdf tool is defined"""
        assert callable(save_pdf)
        assert hasattr(save_pdf, 'name')
    
    @patch('matplotlib.pyplot.savefig')
    @patch('matplotlib.pyplot.close')
    def test_generate_chart_tool(self, mock_close, mock_savefig):
        """Test generate_chart tool"""
        import json
        data = json.dumps({"A": 10, "B": 20, "C": 30})
        
        result = generate_chart(data, "bar", "Test Chart")
        assert isinstance(result, str)
        # Should return path or error message
        assert len(result) > 0
    
    @patch('app.agent.SimpleDocTemplate')
    def test_save_pdf_tool(self, mock_doc_template):
        """Test save_pdf tool"""
        mock_doc = Mock()
        mock_doc_template.return_value = mock_doc
        
        result = save_pdf("Test report text", "test_report.pdf")
        assert isinstance(result, str)
        assert result == "test_report.pdf"
    
    def test_get_agent_response_structure(self):
        """Test that get_agent_response returns expected structure"""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            agent = ReportAgent()
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

