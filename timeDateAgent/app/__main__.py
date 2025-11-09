#!/usr/bin/env python3
"""
Time/Date Agent - A2A MCP Integration
Time and date operations using Python datetime and timezone libraries
"""

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
from pathlib import Path
from dotenv import load_dotenv

from app.agent import TimeDateAgent
from app.agent_executor import TimeDateAgentExecutor


# Load environment variables from .env file in project root
project_root = Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=project_root / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MissingAPIKeyError(Exception):
    """Exception for missing API key."""


@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=8001)
def main(host, port):
    """Starts the Time/Date Agent server."""
    try:
        if not os.getenv('OPENAI_API_KEY'):
            raise MissingAPIKeyError(
                'OPENAI_API_KEY environment variable not set. Please set it in the .env file.'
            )
    
        capabilities = AgentCapabilities(
            streaming=True, 
            pushNotifications=False
        )
        
        # Time/Date skills with comprehensive tags for better orchestrator routing
        time_date_skills = [
            AgentSkill(
                id="current_time",
                name="Current Time",
                description="Get the current time in any timezone",
                tags=["time", "current", "now", "what time", "what's the time", "timezone", "clock", "hour", "minute"],
                examples=["What time is it in New York?", "Current time in London", "What's the time in Tokyo?"]
            ),
            AgentSkill(
                id="timezone_conversion",
                name="Timezone Conversion",
                description="Convert time between different timezones",
                tags=["convert", "timezone", "time zone", "convert time", "EST to PST", "UTC", "GMT"],
                examples=["Convert 3:00 PM EST to London time", "What is 10 AM PST in UTC?"]
            ),
            AgentSkill(
                id="date_calculation",
                name="Date Calculation",
                description="Calculate differences between dates and perform date arithmetic",
                tags=["date", "difference", "days between", "how many days", "add days", "subtract", "until", "from now"],
                examples=["How many days until Christmas?", "What date is 30 days from now?", "Days between two dates"]
            ),
            AgentSkill(
                id="date_formatting",
                name="Date Formatting",
                description="Format dates in various formats",
                tags=["format", "date format", "ISO", "timestamp", "readable date", "date string"],
                examples=["Format today's date as ISO", "Convert timestamp to readable date"]
            ),
        ]
        
        agent_card = AgentCard(
            name='Time/Date Agent',
            description='Time and date operations including timezone conversions, date calculations, and formatting via MCP',
            url=f'http://{host}:{port}/',
            version='1.0.0',
            defaultInputModes=TimeDateAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=TimeDateAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=time_date_skills,
        )

        # Create request handler with time/date agent executor
        httpx_client = httpx.AsyncClient()
        request_handler = DefaultRequestHandler(
            agent_executor=TimeDateAgentExecutor(),
            task_store=InMemoryTaskStore(),
            push_config_store=InMemoryPushNotificationConfigStore(),
            push_sender=BasePushNotificationSender(httpx_client, InMemoryPushNotificationConfigStore()),
        )
        server = A2AStarletteApplication(
            agent_card=agent_card, http_handler=request_handler
        )

        print(f"Starting Time/Date Agent on port {port}")
        print("Available capabilities (via MCP):")
        print("  - Get current time in any timezone")
        print("  - Convert time between timezones")
        print("  - Calculate date differences")
        print("  - Add/subtract time from dates")
        print("  - Format dates in various formats")
        print("  - List and search timezones")

        uvicorn.run(server.build(), host=host, port=port)

    except MissingAPIKeyError as e:
        logger.error(f'Error: {e}')
        sys.exit(1)
    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}')
        sys.exit(1)


if __name__ == "__main__":
    main()

