#!/usr/bin/env python3
"""
MCP Server for Claude Desktop - Stdio Transport

This version uses stdio (stdin/stdout) for communication with Claude Desktop.
The HTTP version (run_mcp_server.py) is for API/web integration.

Claude Desktop expects MCP servers to communicate via stdio.
"""
import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

# Suppress most logging for stdio (only errors to stderr)
import logging

logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr  # Important: logs go to stderr, not stdout
)


async def main():
    """Main entry point for stdio MCP server"""
    try:
        # Import here to avoid loading issues
        from mcp.mcp_tools import TOOLS, get_tool_handler

        # Simple stdio loop
        print("MCP Stdio Server Ready", file=sys.stderr)

        # Read from stdin line by line
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                request = json.loads(line.strip())

                # Handle MCP protocol
                if request.get("method") == "initialize":
                    response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "result": {
                            "protocolVersion": "2025-06-18",
                            "capabilities": {
                                "tools": {}
                            },
                            "serverInfo": {
                                "name": "compliance-system",
                                "version": "1.0.0"
                            }
                        }
                    }
                    print(json.dumps(response), flush=True)

                elif request.get("method") == "tools/list":
                    response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "result": {
                            "tools": TOOLS
                        }
                    }
                    print(json.dumps(response), flush=True)

                elif request.get("method") == "tools/call":
                    tool_name = request["params"]["name"]
                    arguments = request["params"].get("arguments", {})

                    # Route to appropriate handler using registry
                    handler = get_tool_handler(tool_name)
                    if not handler:
                        raise ValueError(f"Unknown tool: {tool_name}")

                    result_text = await handler(**arguments)

                    response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": result_text
                                }
                            ]
                        }
                    }
                    print(json.dumps(response), flush=True)

                elif request.get("method") == "ping":
                    response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "result": {}
                    }
                    print(json.dumps(response), flush=True)

                else:
                    # Unknown method
                    response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {request.get('method')}"
                        }
                    }
                    print(json.dumps(response), flush=True)

            except Exception as e:
                print(f"Error processing request: {e}", file=sys.stderr)
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id") if 'request' in locals() else None,
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                }
                print(json.dumps(error_response), flush=True)

    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
