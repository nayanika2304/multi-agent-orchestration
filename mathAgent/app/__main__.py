#!/usr/bin/env python3
"""
Math Agent - A2A MCP Integration
Mathematical calculations, equation solving, calculus, statistics, and matrix operations
"""

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

from app.agent import MathAgent
from app.agent_executor import MathAgentExecutor


# Load environment variables from .env file in project root
project_root = Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=project_root / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MissingAPIKeyError(Exception):
    """Exception for missing API key."""


def main():
    """Starts the Math Agent server."""
    parser = argparse.ArgumentParser(
        description="Math Agent server"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host to bind to (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8003,
        help="Port to bind to (default: 8003)"
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
        
        # Math skills with comprehensive tags for better orchestrator routing
        math_skills = [
            AgentSkill(
                id="arithmetic_calculation",
                name="Arithmetic Calculation",
                description="Perform basic and advanced arithmetic calculations",
                tags=["math", "calculation", "arithmetic", "compute", "calculate", "add", "subtract", "multiply", "divide", "power", "sqrt", "sin", "cos", "tan", "log", "exp", "what is", "plus", "minus", "times", "+", "-", "*", "/", "^", "sum", "product", "number", "numbers"],
                examples=["Calculate 2 + 2", "What is sin(pi/4)?", "Compute sqrt(16)"]
            ),
            AgentSkill(
                id="equation_solving",
                name="Equation Solving",
                description="Solve algebraic equations and systems of equations",
                tags=["equation", "solve", "algebra", "polynomial", "quadratic", "linear", "system", "roots", "solutions"],
                examples=["Solve x^2 - 4 = 0", "Find roots of 2x + 5 = 11"]
            ),
            AgentSkill(
                id="calculus_operations",
                name="Calculus Operations", 
                description="Calculate derivatives and integrals of mathematical functions",
                tags=["calculus", "derivative", "integral", "differentiate", "integrate", "limit", "function", "dx", "dy"],
                examples=["Find derivative of x^2 + 3x + 2", "Integrate x^2 dx"]
            ),
            AgentSkill(
                id="matrix_operations",
                name="Matrix Operations",
                description="Perform matrix calculations including multiplication, inversion, determinant",
                tags=["matrix", "linear", "algebra", "determinant", "inverse", "transpose", "multiply", "eigenvalue", "vector"],
                examples=["Determinant of [[1,2],[3,4]]", "Multiply matrices"]
            ),
            AgentSkill(
                id="statistics_analysis",
                name="Statistics Analysis",
                description="Calculate statistical measures and analyze data sets",
                tags=["statistics", "stats", "mean", "median", "mode", "standard", "deviation", "variance", "data", "analysis"],
                examples=["Mean of [1,2,3,4,5]", "Standard deviation of data"]
            )
        ]
        
        agent_card = AgentCard(
            name='Math Agent',
            description='Advanced mathematical assistant for calculations, equation solving, calculus, statistics, and matrix operations via MCP',
            url=f'http://{host}:{port}/',
            version='1.0.0',
            defaultInputModes=MathAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=MathAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=math_skills,
        )

        # Create request handler with math agent executor
        request_handler = DefaultRequestHandler(
            agent_executor=MathAgentExecutor(),
            task_store=InMemoryTaskStore(),
        )
        server = A2AStarletteApplication(
            agent_card=agent_card, http_handler=request_handler
        )

        print(f"Starting Math Agent on port {port}")
        print("Available capabilities (via MCP):")
        print("  • Arithmetic calculations (2+2, sin(pi/4), sqrt(16))")
        print("  • Equation solving (x^2 - 4 = 0)")
        print("  • Calculus (derivatives and integrals)")
        print("  • Matrix operations (multiply, inverse, determinant)")
        print("  • Statistics (mean, median, std dev, etc.)")

        uvicorn.run(server.build(), host=host, port=port)

    except MissingAPIKeyError as e:
        logger.error(f'Error: {e}')
        sys.exit(1)
    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}')
        sys.exit(1)


if __name__ == "__main__":
    main()