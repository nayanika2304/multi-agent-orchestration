import logging
import os
import sys

import click
import httpx
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import BasePushNotificationSender, InMemoryPushNotificationConfigStore, InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from dotenv import load_dotenv

from app.agent import RAGAgent
from app.agent_executor import RAGAgentExecutor


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MissingAPIKeyError(Exception):
    """Exception for missing API key."""


@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=8004)
def main(host, port):
    """Starts the RAG Agent server."""
    try:
        # Check for OpenAI API key
        if not os.getenv('OPENAI_API_KEY') and not os.getenv('API_KEY'):
            raise MissingAPIKeyError(
                'OPENAI_API_KEY environment variable not set.'
            )
    
        capabilities = AgentCapabilities(
            streaming=True, 
            pushNotifications=True
            )
        
        # Enhanced skills with MCP tools for better orchestrator routing
        rag_skills = [
            AgentSkill(
                id="rag_search",
                name="RAG search operations",
                description="RAG search operations and answer generation",
                tags=["rag", "search", "weather", "data", "bitcoin", "crypto", "market", "analysis", "weather"],
                examples=["What is the weather in Tokyo?", "Get financial data for EUR", "Show me currency trends", "Analyze currency market trends", "Bitcoin price analysis", "What is the weather in Tokyo?"]
            ),
            AgentSkill(
                id="document_search",
                name="Document search and retrieval",
                description="Search through documents using semantic search with MCP tools",
                tags=["search", "documents", "semantic", "retrieval", "mcp"],
                examples=["Search for documents about AI", "Find information on climate change", "Retrieve documents containing financial data"]
            ),
            AgentSkill(
                id="database_query",
                name="Database querying",
                description="Execute database queries to retrieve structured data via MCP",
                tags=["database", "query", "sql", "data", "mcp"],
                examples=["Query database for user information", "Get analytics data", "Retrieve structured data"]
            ),
            AgentSkill(
                id="context_retrieval",
                name="Context and background retrieval",
                description="Retrieve relevant context and background information",
                tags=["context", "background", "information", "research"],
                examples=["Get context about machine learning", "Retrieve background on company history", "Find related information"]
            ),
            AgentSkill(
                id="semantic_search",
                name="Semantic search capabilities",
                description="Perform advanced semantic search across indexed content",
                tags=["semantic", "search", "advanced", "indexed", "similarity"],
                examples=["Semantic search for similar concepts", "Find semantically related content", "Advanced content discovery"]
            ),
            AgentSkill(
                id="complete_rag",
                name="Complete RAG processing",
                description="Full RAG query processing with planning, retrieval, analysis, and synthesis",
                tags=["rag", "complete", "planning", "analysis", "synthesis"],
                examples=["Comprehensive analysis of market trends", "Complete research on technology adoption", "Full analysis with citations"]
            )
        ]
        
        agent_card = AgentCard(
            name='RAG Agent',
            description='Handles RAG search operations with MCP tool capabilities for document search, database queries, and semantic retrieval',
            url=f'http://{host}:{port}/',
            version='1.0.0',
            defaultInputModes=RAGAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=RAGAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=rag_skills,
        )

        # --8<-- [start:DefaultRequestHandler]
        httpx_client = httpx.AsyncClient()
        request_handler = DefaultRequestHandler(
            agent_executor=RAGAgentExecutor(),
            task_store=InMemoryTaskStore(),
            push_config_store=InMemoryPushNotificationConfigStore(),
            push_sender=BasePushNotificationSender(httpx_client, InMemoryPushNotificationConfigStore()),
        )
        server = A2AStarletteApplication(
            agent_card=agent_card, http_handler=request_handler
        )

        uvicorn.run(server.build(), host=host, port=port)
        # --8<-- [end:DefaultRequestHandler]

    except MissingAPIKeyError as e:
        logger.error(f'Error: {e}')
        sys.exit(1)
    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()