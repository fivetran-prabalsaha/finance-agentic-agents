#!/usr/bin/env python3
"""
Startup script for MCP Server

Run with:
    python3 run_mcp_server.py

Or make executable:
    chmod +x run_mcp_server.py
    ./run_mcp_server.py
"""
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables from .env
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_environment():
    """Check required environment variables"""
    required_vars = [
        'DATABASE_URL',
        'ANTHROPIC_API_KEY',
        'NETSUITE_CONSUMER_KEY',
        'NETSUITE_CONSUMER_SECRET',
        'NETSUITE_TOKEN_ID',
        'NETSUITE_TOKEN_SECRET',
        'NETSUITE_REALM',
        'NETSUITE_RESTLET_URL'
    ]

    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)

    if missing:
        logger.warning("Missing environment variables:")
        for var in missing:
            logger.warning(f"  • {var}")
        logger.warning("Set them in .env file or export them")

        # Don't fail - some may be optional
        return False

    return True


def main():
    """Start MCP server"""
    logger.info("=" * 80)
    logger.info("SOD Compliance MCP Server")
    logger.info("=" * 80)

    # Check environment
    env_ok = check_environment()
    if not env_ok:
        logger.warning("Some environment variables are missing - server may have limited functionality")

    # Print configuration
    host = os.getenv('MCP_SERVER_HOST', '0.0.0.0')
    port = int(os.getenv('MCP_SERVER_PORT', 8080))
    api_key = os.getenv('MCP_API_KEY', 'dev-key-12345')

    logger.info(f"Host: {host}")
    logger.info(f"Port: {port}")
    logger.info(f"API Key: {api_key[:10]}..." if len(api_key) > 10 else f"API Key: {api_key}")
    logger.info("=" * 80)

    # Import and run server
    try:
        from mcp.mcp_server import main as run_server
        run_server()
    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
