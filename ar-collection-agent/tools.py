"""MCP toolset connections for NetSuite and Atlassian."""
import os

from dotenv import load_dotenv
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, SseServerParams

load_dotenv()

netsuite_toolset = MCPToolset(
    connection_params=SseServerParams(
        url=os.environ["NETSUITE_MCP_URL"],
        headers={"Authorization": f"Bearer {os.environ['NETSUITE_MCP_API_KEY']}"},
    ),
    tool_filter=[
        "ns_createRecord",
        "ns_updateRecord",
        "ns_getRecord",
        "ns_searchRecord",
    ],
)

atlassian_toolset = MCPToolset(
    connection_params=SseServerParams(
        url=os.environ["ATLASSIAN_MCP_URL"],
        headers={"Authorization": f"Bearer {os.environ['ATLASSIAN_MCP_API_KEY']}"},
    ),
    tool_filter=[
        "create_issue",
        "get_issue",
        "search_issues",
        "add_comment",
    ],
)
