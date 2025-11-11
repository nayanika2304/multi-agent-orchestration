import argparse
import logging
import os
import sys

import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from pathlib import Path
from dotenv import load_dotenv

from app.agent import CurrencyAgent
from app.agent_executor import CurrencyAgentExecutor


# Load environment variables from .env file in project root
project_root = Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=project_root / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MissingAPIKeyError(Exception):
    """Exception for missing API key."""


def main():
    """Starts the Currency Agent server."""
    parser = argparse.ArgumentParser(
        description="Currency Agent server"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host to bind to (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8002,
        help="Port to bind to (default: 8002)"
    )
    args = parser.parse_args()
    
    host = args.host
    port = args.port
    
    try:
        if not os.getenv('OPENAI_API_KEY'):
            raise MissingAPIKeyError(
                'OPENAI_API_KEY environment variable not set. Please set it in the .env file.'
            )
    
        capabilities = AgentCapabilities(streaming=True)
        
        # Enhanced skills with currency codes for better orchestrator routing
        currency_skills = [
            AgentSkill(
                id="currency_exchange",
                name="Currency exchange operations",
                description="Currency exchange operations and rate lookups",
                tags=["currency", "exchange", "usd", "eur", "inr", "gbp", "jpy", "dollar"],
                examples=["What is exchange rate between USD and GBP?", "Convert 100 USD to EUR"]
            ),
            AgentSkill(
                id="financial_data",
                name="Financial data analysis",
                description="Financial data analysis and currency information",
                tags=["financial", "data", "usd", "eur", "dollar", "money"],
                examples=["Get financial data for EUR", "Show me currency trends"]
            ),
            AgentSkill(
                id="market_analysis",
                name="Market analysis and trends",
                description="Market analysis and currency trends",
                tags=["market", "analysis", "bitcoin", "crypto"],
                examples=["Analyze currency market trends", "Bitcoin price analysis"]
            ),
            AgentSkill(
                id="rate_conversion",
                name="Currency rate conversion",
                description="Currency rate conversion and calculations",
                tags=["conversion", "rates", "usd", "eur", "inr", "dollar"],
                examples=["Convert 50 USD to INR", "Calculate exchange rates"]
            ),
            AgentSkill(
                id="historical_data",
                name="Historical financial data",
                description="Historical financial data and currency rates",
                tags=["historical", "data"],
                examples=["Historical USD to EUR rates", "Past currency data"]
            )
        ]
        
        agent_card = AgentCard(
            name='Currency Agent',
            description='Handles currency exchange and financial data',
            url=f'http://{host}:{port}/',
            version='1.0.0',
            defaultInputModes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=currency_skills,
        )

        # --8<-- [start:DefaultRequestHandler]
        request_handler = DefaultRequestHandler(
            agent_executor=CurrencyAgentExecutor(),
            task_store=InMemoryTaskStore(),
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