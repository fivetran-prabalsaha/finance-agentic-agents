"""
MCP Server - Model Context Protocol server for Claude UI integration

This FastAPI server implements the MCP protocol (JSON-RPC 2.0) and provides
tool discovery and execution for Claude UI.
"""
import os
import logging
from typing import Any, Dict, Optional
from datetime import datetime
import asyncio

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from .mcp_tools import (
    get_all_tool_schemas,
    get_tool_schema,
    get_tool_handler,
    TOOL_SCHEMAS
)
from .admin_api import auth_router, admin_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Compliance MCP Server",
    description="""Model Context Protocol server for SOD Compliance System.

Response Style: Provide concise, actionable analysis. Lead with recommendation (APPROVE/DENY/REVIEW),
summarize key metrics (conflicts, risk scores), list 3-5 critical issues, and present options as table
or short list. Avoid verbose bullet-point lists. Target 10-15 lines per response.
See RESPONSE_STYLE_GUIDE.md for details.""",
    version="1.0.0"
)

# Add CORS middleware — restrict to internal origins via MCP_ALLOWED_ORIGINS env var
_allowed_origins_raw = os.getenv('MCP_ALLOWED_ORIGINS', '')
_allowed_origins = (
    [o.strip() for o in _allowed_origins_raw.split(',') if o.strip()]
    or ["http://localhost", "http://localhost:4200"]   # 4200 = Angular dev server
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount admin portal routers
app.include_router(auth_router)
app.include_router(admin_router)


# ============================================================================
# MODELS
# ============================================================================

class MCPRequest(BaseModel):
    """MCP JSON-RPC 2.0 request or notification"""
    jsonrpc: str = Field(default="2.0")
    method: str
    params: Dict[str, Any] = Field(default_factory=dict)
    id: Optional[int] = None  # None for notifications, int for requests


class MCPResponse(BaseModel):
    """MCP JSON-RPC 2.0 response"""
    model_config = {"exclude_none": True}  # Exclude None values from JSON

    jsonrpc: str = Field(default="2.0")
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[int] = None  # Must match request id


class MCPError(BaseModel):
    """MCP error object"""
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None


# ============================================================================
# ERROR CODES
# ============================================================================

class ErrorCode:
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    SERVER_ERROR = -32000


# ============================================================================
# AUTHENTICATION (Simple API Key)
# ============================================================================

API_KEY = os.getenv('MCP_API_KEY')
if not API_KEY:
    raise ValueError("MCP_API_KEY environment variable is required and must be set")


async def verify_api_key(request: Request):
    """Verify API key from request headers"""
    api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization', '').replace('Bearer ', '')

    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")

    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")

    return api_key


# ============================================================================
# ROUTES
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint - server info"""
    return {
        "service": "Compliance MCP Server",
        "version": "1.0.0",
        "status": "running",
        "protocol": "MCP (Model Context Protocol)",
        "endpoints": {
            "health": "/health",
            "mcp": "/mcp (POST)",
            "tools": "/tools (GET)"
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "compliance-mcp-server",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/tools")
async def list_tools():
    """List all available tools (for debugging)"""
    tools = []
    for name, schema in TOOL_SCHEMAS.items():
        tools.append({
            "name": name,
            "description": schema["description"],
            "input_schema": schema["inputSchema"]
        })

    return {
        "tools": tools,
        "count": len(tools)
    }


@app.post("/mcp")
async def mcp_handler(
    request_data: MCPRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Main MCP request handler

    Implements JSON-RPC 2.0 protocol for MCP communication
    """
    logger.info(f"MCP Request: {request_data.method} (id={request_data.id})")

    try:
        # Handle notifications (no id, no response expected)
        if request_data.id is None:
            logger.info(f"Received notification: {request_data.method} (no response needed)")
            # For notifications, return 204 No Content
            from fastapi.responses import Response
            return Response(status_code=204)

        # Handle different MCP methods
        if request_data.method == "initialize":
            response = await handle_initialize(request_data)

        elif request_data.method == "tools/list":
            response = await handle_tools_list(request_data)

        elif request_data.method == "tools/call":
            response = await handle_tools_call(request_data)

        elif request_data.method == "ping":
            response = MCPResponse(
                id=request_data.id,
                result={"status": "pong"}
            )

        else:
            response = MCPResponse(
                id=request_data.id,
                error={
                    "code": ErrorCode.METHOD_NOT_FOUND,
                    "message": f"Method not found: {request_data.method}",
                    "data": {
                        "available_methods": ["initialize", "tools/list", "tools/call", "ping"]
                    }
                }
            )

        # Return as dict with None values excluded (JSON-RPC 2.0 compliance)
        return JSONResponse(content=response.model_dump(exclude_none=True))

    except Exception as e:
        logger.error(f"MCP handler error: {str(e)}", exc_info=True)
        response = MCPResponse(
            id=request_data.id,
            error={
                "code": ErrorCode.INTERNAL_ERROR,
                "message": f"Internal server error: {str(e)}"
            }
        )
        return JSONResponse(content=response.model_dump(exclude_none=True))


async def handle_initialize(request_data: MCPRequest) -> MCPResponse:
    """Handle initialize request"""
    logger.info("Handling initialize request")

    return MCPResponse(
        id=request_data.id,
        result={
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "compliance-mcp-server",
                "version": "1.0.0"
            }
        }
    )


async def handle_tools_list(request_data: MCPRequest) -> MCPResponse:
    """Handle tools/list request - return available tools"""
    logger.info("Handling tools/list request")

    tools = []
    for name, schema in TOOL_SCHEMAS.items():
        tools.append({
            "name": name,
            "description": schema["description"],
            "inputSchema": schema["inputSchema"]
        })

    return MCPResponse(
        id=request_data.id,
        result={"tools": tools}
    )


async def handle_tools_call(request_data: MCPRequest) -> MCPResponse:
    """Handle tools/call request - execute a tool"""
    tool_name = request_data.params.get("name")
    arguments = request_data.params.get("arguments", {})

    if not tool_name:
        return MCPResponse(
            id=request_data.id,
            error={
                "code": ErrorCode.INVALID_PARAMS,
                "message": "Missing 'name' parameter"
            }
        )

    logger.info(f"Executing tool: {tool_name} with args: {arguments}")

    # Get tool handler
    handler = get_tool_handler(tool_name)
    if not handler:
        return MCPResponse(
            id=request_data.id,
            error={
                "code": ErrorCode.METHOD_NOT_FOUND,
                "message": f"Tool not found: {tool_name}",
                "data": {
                    "available_tools": list(TOOL_SCHEMAS.keys())
                }
            }
        )

    # Validate arguments against schema
    schema = get_tool_schema(tool_name)
    required_params = schema["inputSchema"].get("required", [])
    for param in required_params:
        if param not in arguments:
            return MCPResponse(
                id=request_data.id,
                error={
                    "code": ErrorCode.INVALID_PARAMS,
                    "message": f"Missing required parameter: {param}",
                    "data": {
                        "required_parameters": required_params,
                        "provided_parameters": list(arguments.keys())
                    }
                }
            )

    # Execute tool
    try:
        start_time = datetime.utcnow()

        # Call handler (async)
        result_text = await handler(**arguments)

        execution_time = (datetime.utcnow() - start_time).total_seconds()

        logger.info(f"Tool {tool_name} executed successfully in {execution_time:.2f}s")

        # Return result in MCP format
        return MCPResponse(
            id=request_data.id,
            result={
                "content": [
                    {
                        "type": "text",
                        "text": result_text
                    }
                ],
                "isError": False,
                "_meta": {
                    "execution_time_seconds": execution_time,
                    "tool_name": tool_name,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )

    except Exception as e:
        logger.error(f"Tool execution error: {str(e)}", exc_info=True)

        # Return error
        return MCPResponse(
            id=request_data.id,
            result={
                "content": [
                    {
                        "type": "text",
                        "text": f"❌ Error executing tool: {str(e)}"
                    }
                ],
                "isError": True,
                "_meta": {
                    "error": str(e),
                    "tool_name": tool_name,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": ErrorCode.INTERNAL_ERROR,
                "message": "Internal server error"
            }
        }
    )


# ============================================================================
# STARTUP/SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Startup event - initialize connections and start collection agent"""
    logger.info("=" * 80)
    logger.info("Starting Compliance MCP Server")
    logger.info("=" * 80)
    logger.info(f"Available tools: {len(TOOL_SCHEMAS)}")
    for tool_name in TOOL_SCHEMAS.keys():
        logger.info(f"  • {tool_name}")
    logger.info("=" * 80)

    # Start autonomous collection agent
    try:
        logger.info("Starting Autonomous Collection Agent...")
        from agents.data_collector import start_collection_agent
        await asyncio.to_thread(start_collection_agent)
        logger.info("✅ Autonomous Collection Agent started successfully")
    except Exception as e:
        logger.error(f"Failed to start collection agent: {str(e)}", exc_info=True)
        logger.warning("Server will continue without autonomous collection agent")

    # Initialize knowledge base with embeddings
    try:
        logger.info("Initializing Knowledge Base Agent...")
        from models.database_config import DatabaseConfig
        from repositories.sod_rule_repository import SODRuleRepository
        from agents.knowledge_base_pgvector import create_knowledge_base

        db_config = DatabaseConfig()
        session = db_config.get_session()
        rule_repo = SODRuleRepository(session)

        # This will auto-create embeddings from sod_rules.json if missing
        kb_agent = create_knowledge_base(
            session=session,
            sod_rule_repo=rule_repo
        )
        logger.info("✅ Knowledge Base Agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize knowledge base: {str(e)}", exc_info=True)
        logger.warning("Server will continue without knowledge base embeddings")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event - cleanup and stop collection agent"""
    logger.info("Shutting down Compliance MCP Server")

    # Stop autonomous collection agent
    try:
        logger.info("Stopping Autonomous Collection Agent...")
        from agents.data_collector import stop_collection_agent
        await asyncio.to_thread(stop_collection_agent)
        logger.info("✅ Autonomous Collection Agent stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping collection agent: {str(e)}", exc_info=True)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run the MCP server"""
    host = os.getenv('MCP_SERVER_HOST', '0.0.0.0')
    port = int(os.getenv('MCP_SERVER_PORT', 8080))

    logger.info(f"Starting MCP server on {host}:{port}")

    uvicorn.run(
        "mcp.mcp_server:app",
        host=host,
        port=port,
        log_level="info",
        reload=False  # Set to True for development
    )


if __name__ == "__main__":
    main()
