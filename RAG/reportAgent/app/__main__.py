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

from app.agent import ReportAgent
from app.agent_executor import ReportAgentExecutor


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MissingAPIKeyError(Exception):
    """Exception for missing API key."""


@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=8005)
def main(host, port):
    """Starts the Report Agent server."""
    try:
        # Check for OpenAI API key (required for both agent orchestration and report generation)
        if not os.getenv('OPENAI_API_KEY') and not os.getenv('API_KEY'):
            raise MissingAPIKeyError(
                'OPENAI_API_KEY environment variable not set. '
                'Required for agent orchestration and report generation.'
            )
    
        capabilities = AgentCapabilities(
            streaming=True, 
            pushNotifications=True
            )
        
        # Enhanced skills with report generation and data visualization keywords for better orchestrator routing
        report_skills = [
            AgentSkill(
                id="report_generation",
                name="Professional report generation",
                description="Generate professional reports from data and insights",
                tags=["report", "document", "pdf", "analysis", "summary"],
                examples=["Generate a report from this data", "Create a professional document", "Make a PDF report"]
            ),
            AgentSkill(
                id="data_visualization",
                name="Data visualization and charting",
                description="Create charts, graphs, and visual representations of data",
                tags=["chart", "graph", "visualization", "bar", "line", "pie", "scatter", "histogram", "plot"],
                examples=["Create a bar chart from this data", "Generate graphs for analysis", "Visualize this data"]
            ),
            AgentSkill(
                id="data_analysis_reporting",
                name="Data analysis and reporting",
                description="Analyze data and create comprehensive reports with visualizations",
                tags=["data", "analysis", "insights", "findings", "recommendations", "visualization"],
                examples=["Analyze this data and create a report", "Generate insights report with charts"]
            ),
            AgentSkill(
                id="document_formatting",
                name="Document formatting and structuring",
                description="Format documents with proper structure and styling",
                tags=["format", "structure", "document", "professional"],
                examples=["Format this document professionally", "Create structured report"]
            ),
            AgentSkill(
                id="executive_summary",
                name="Executive summary creation",
                description="Create executive summaries and key findings",
                tags=["executive", "summary", "findings", "recommendations"],
                examples=["Create executive summary", "Summarize key findings"]
            ),
            AgentSkill(
                id="pdf_generation",
                name="PDF document generation with charts",
                description="Generate PDF documents from text and data with embedded visualizations",
                tags=["pdf", "export", "save", "document", "charts", "visualizations"],
                examples=["Save as PDF", "Export to PDF document with charts", "Generate PDF report with graphs"]
            ),
            AgentSkill(
                id="statistical_analysis",
                name="Statistical analysis and visualization",
                description="Perform statistical analysis and create visual representations",
                tags=["statistics", "statistical", "trends", "patterns", "metrics"],
                examples=["Statistical analysis of this dataset", "Show trends in this data", "Analyze performance metrics"]
            )
        ]
        
        agent_card = AgentCard(
            name='Report Agent',
            description='Generates professional reports and documents with data visualization and charting capabilities',
            url=f'http://{host}:{port}/',
            version='1.0.0',
            defaultInputModes=ReportAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=ReportAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=report_skills,
        )

        httpx_client = httpx.AsyncClient()
        request_handler = DefaultRequestHandler(
            agent_executor=ReportAgentExecutor(),
            task_store=InMemoryTaskStore(),
            push_config_store=InMemoryPushNotificationConfigStore(),
            push_sender=BasePushNotificationSender(httpx_client, InMemoryPushNotificationConfigStore()),
        )
        server = A2AStarletteApplication(
            agent_card=agent_card, http_handler=request_handler
        )

        uvicorn.run(server.build(), host=host, port=port)

    except MissingAPIKeyError as e:
        logger.error(f'Error: {e}')
        sys.exit(1)
    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
