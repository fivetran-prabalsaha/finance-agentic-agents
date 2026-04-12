# MCP Integration Technical Specification

**Project**: Claude UI to Compliance Agent Integration via MCP
**Version**: 2.6.0
**Date**: 2026-02-26
**Status**: ✅ Production — Fully Operational
**Branch**: `RD-1036683-billing-schedule-automation-dev`

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Project Goals](#project-goals)
3. [MCP Overview](#mcp-overview)
4. [System Architecture](#system-architecture)
5. [User Workflow](#user-workflow)
6. [Component Design](#component-design)
7. [NetSuite Integration](#netsuite-integration)
8. [Implementation Plan](#implementation-plan)
9. [Security & Compliance](#security--compliance)
10. [Technical Requirements](#technical-requirements)
11. [Success Criteria](#success-criteria)

---

## Executive Summary

This specification outlines the integration of the SOD Compliance System with Claude AI via the Model Context Protocol (MCP). The goal is to enable natural language interaction where users can request compliance reviews through Claude UI, and backend MCP agents will:

1. Parse natural language requests
2. Trigger appropriate compliance agents
3. Fetch data from external systems (NetSuite, Okta, etc.)
4. Perform compliance analysis
5. Return structured results to Claude UI

**Example User Interaction**:
```
User: "Please perform a user access review of NetSuite"
Claude: "I'll initiate a NetSuite user access review. Connecting to NetSuite and analyzing user permissions..."

[Backend MCP agents trigger NetSuite RESTlet, fetch users, analyze SOD violations]

Claude: "Access review complete. Found 23 users with 47 SOD violations across NetSuite roles.
        High-risk violations: 12 (Admin + Finance roles). Would you like details on specific users?"
```

---

## Project Goals

### Primary Goals

1. **Natural Language Interface**: Enable users to request compliance reviews using conversational language via Claude UI
2. **Automated Data Fetching**: Backend agents automatically connect to external systems (NetSuite, Okta) via APIs/RESTlets
3. **Real-Time Analysis**: Perform SOD analysis and return results within Claude conversation
4. **Multi-System Support**: Support multiple systems (NetSuite, Salesforce, SAP, etc.) through extensible architecture
5. **Audit Trail**: Log all user requests and compliance actions for audit purposes

### Secondary Goals

1. **Interactive Remediation**: Allow users to ask follow-up questions and drill into specific violations
2. **Scheduled Reviews**: Enable users to schedule recurring reviews via natural language
3. **Notification Integration**: Send results via email/Slack while maintaining conversation in Claude UI
4. **Export Capabilities**: Generate compliance reports in various formats (PDF, CSV, JSON)

---

## MCP Overview

### What is MCP?

The **Model Context Protocol (MCP)** is Anthropic's open protocol for connecting AI assistants (like Claude) to external data sources and tools. It enables:

- **Bidirectional Communication**: Claude can invoke tools and receive structured responses
- **Tool Discovery**: Claude automatically discovers available tools and their capabilities
- **Structured Data Exchange**: Type-safe communication between Claude and backend services
- **Session Management**: Maintain context across multiple interactions

### MCP Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLAUDE UI (Web/Desktop)                  │
│                                                                  │
│  User: "Perform user access review of NetSuite"                │
└────────────────────────────┬────────────────────────────────────┘
                             │ MCP Protocol (JSON-RPC)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MCP SERVER (Python)                         │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Tool Registry & Router (34 tools)            │  │
│  │  • list_systems()                                        │  │
│  │  • perform_access_review(system_name)                   │  │
│  │  • get_user_violations(user_id) - table format default  │  │
│  │  • generate_violation_report() - Excel/CSV export       │  │
│  │  • remediate_violation(violation_id)                    │  │
│  │  • schedule_review(system, frequency)                   │  │
│  │  • initialize_session(my_email)                         │  │
│  │  • check_my_approval_authority(my_email) ✅ NEW        │  │
│  │  • request_exception_approval(...) ✅ NEW               │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                        │
│                         ▼                                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │          Compliance Agent Orchestrator                    │  │
│  │  • Parse natural language intent                         │  │
│  │  • Route to appropriate agent                            │  │
│  │  • Aggregate results from multiple sources               │  │
│  └──────────────────────┬───────────────────────────────────┘  │
└────────────────────────┬┴───────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  COMPLIANCE AGENTS (Existing)                    │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Analyzer   │  │   Notifier   │  │  Knowledge   │         │
│  │    Agent     │  │    Agent     │  │     Base     │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                  │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SYSTEMS                              │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   NetSuite   │  │     Okta     │  │  Salesforce  │         │
│  │   RESTlet    │  │     API      │  │     API      │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

---

## System Architecture

### High-Level Components

```
┌───────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                          │
│  • Claude UI (Web/Desktop)                                        │
│  • Natural language input/output                                  │
└───────────────────────────┬───────────────────────────────────────┘
                            │ MCP Protocol
                            ▼
┌───────────────────────────────────────────────────────────────────┐
│                        MCP SERVER LAYER                            │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  mcp_server.py                                              │ │
│  │  • FastAPI/Starlette HTTP server                           │ │
│  │  • MCP protocol handler (JSON-RPC 2.0)                     │ │
│  │  • Tool registration and discovery                         │ │
│  │  • Authentication & authorization                          │ │
│  │  • Session management                                      │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  mcp_tools.py                                               │ │
│  │  • Tool definitions (schemas)                              │ │
│  │  • Tool implementation (handlers)                          │ │
│  │  • Input validation                                        │ │
│  │  • Output formatting                                       │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  orchestrator.py                                            │ │
│  │  • Intent parsing                                          │ │
│  │  • Agent routing                                           │ │
│  │  • Result aggregation                                      │ │
│  │  • Error handling                                          │ │
│  └─────────────────────────────────────────────────────────────┘ │
└───────────────────────────┬───────────────────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────────────┐
│                      COMPLIANCE AGENT LAYER                        │
│  (Existing agents - minimal changes required)                     │
│                                                                    │
│  • AnalysisAgent (SOD detection)                                  │
│  • NotificationAgent (alerts)                                     │
│  • KnowledgeBaseAgent (vector search)                            │
│  • RiskAssessmentAgent (scoring)                                 │
└───────────────────────────┬───────────────────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────────────┐
│                      DATA INTEGRATION LAYER                        │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  connectors/netsuite_connector.py                           │ │
│  │  • RESTlet client                                          │ │
│  │  • User/role fetching                                      │ │
│  │  • Permission mapping                                      │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  connectors/okta_connector.py (existing)                    │ │
│  │  • Already implemented                                     │ │
│  │  • User/group synchronization                              │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  connectors/base_connector.py                               │ │
│  │  • Abstract base class for all connectors                  │ │
│  │  • Standardized interface                                  │ │
│  └─────────────────────────────────────────────────────────────┘ │
└───────────────────────────┬───────────────────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────────────┐
│                        STORAGE LAYER                               │
│  • PostgreSQL (existing database)                                 │
│  • Redis (existing cache)                                         │
│  • Audit logs (new)                                               │
└───────────────────────────────────────────────────────────────────┘
```

### New Components to Build

1. **MCP Server** (`mcp/mcp_server.py`)
   - FastAPI-based server implementing MCP protocol
   - Tool registry and discovery
   - Session management

2. **MCP Tools** (`mcp/mcp_tools.py`)
   - Tool definitions and schemas
   - Handler implementations
   - Input/output validation

3. **Orchestrator** (`mcp/orchestrator.py`)
   - Intent parsing from natural language
   - Agent routing logic
   - Result aggregation

4. **NetSuite Connector** (`connectors/netsuite_connector.py`)
   - RESTlet client implementation
   - User/role data fetching
   - NetSuite-specific data mapping

5. **Audit Logger** (`services/audit_logger.py`)
   - Log all MCP requests
   - Track user actions
   - Compliance audit trail

---

## User Workflow

### Example 1: Simple Access Review

**Step 1: User Request**
```
User in Claude UI: "Please perform a user access review of NetSuite"
```

**Step 2: Claude Invokes MCP Tool**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "perform_access_review",
    "arguments": {
      "system_name": "netsuite",
      "analysis_type": "sod_violations"
    }
  },
  "id": 1
}
```

**Step 3: MCP Server Processes Request**
1. Orchestrator parses intent
2. Routes to AnalysisAgent
3. NetSuite connector fetches users/roles
4. AnalysisAgent detects SOD violations
5. Results formatted and returned

**Step 4: Claude Receives Response**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Access Review Complete:\n\nSystem: NetSuite\nUsers Analyzed: 142\nTotal Violations: 47\nHigh-Risk Violations: 12\n\nTop 3 High-Risk Users:\n1. John Smith (Admin + Finance Manager) - 5 violations\n2. Jane Doe (Developer + DBA) - 4 violations\n3. Bob Johnson (HR + Payroll) - 3 violations"
      }
    ]
  },
  "id": 1
}
```

**Step 5: User Sees Results in Claude UI**
```
Claude: "Access Review Complete:

System: NetSuite
Users Analyzed: 142
Total Violations: 47
High-Risk Violations: 12

Top 3 High-Risk Users:
1. John Smith (Admin + Finance Manager) - 5 violations
2. Jane Doe (Developer + DBA) - 4 violations
3. Bob Johnson (HR + Payroll) - 3 violations

Would you like to see details for any specific user or violation?"
```

### Example 2: Interactive Follow-Up

**User**: "Show me details for John Smith"

**Claude invokes**:
```json
{
  "method": "tools/call",
  "params": {
    "name": "get_user_violations",
    "arguments": {
      "system_name": "netsuite",
      "user_identifier": "john.smith@company.com"
    }
  }
}
```

**Response**:
```
Claude: "John Smith - Detailed Violation Report:

Email: john.smith@company.com
Roles: Administrator, Finance Manager, Approver

Violations (5 total):

1. HIGH RISK: Administrator + Finance Manager
   - Can create vendors AND approve payments
   - Risk: Fraudulent payment creation
   - Last detected: 2026-02-12
   - Status: Active

2. HIGH RISK: Finance Manager + Approver
   - Can enter invoices AND approve them
   - Risk: Unauthorized expense approval
   - Last detected: 2026-02-12
   - Status: Active

[... additional violations ...]

Recommended Actions:
- Remove Administrator role (reduces violations by 3)
- Implement approval workflow requiring dual authorization
- Review all recent financial transactions

Would you like me to generate a remediation ticket?"
```

### Example 3: Scheduling Recurring Review

**User**: "Schedule a weekly access review for NetSuite every Monday at 9 AM"

**Claude invokes**:
```json
{
  "method": "tools/call",
  "params": {
    "name": "schedule_review",
    "arguments": {
      "system_name": "netsuite",
      "frequency": "weekly",
      "day_of_week": "monday",
      "time": "09:00",
      "timezone": "America/Los_Angeles"
    }
  }
}
```

**Response**:
```
Claude: "✅ Scheduled successfully!

Review Configuration:
- System: NetSuite
- Frequency: Weekly
- Schedule: Every Monday at 9:00 AM PST
- Next run: 2026-02-17 09:00:00 PST

Results will be:
- Saved to database
- Sent via email to your registered address
- Available in this chat for review

You'll receive a notification when each review completes. To modify or cancel this schedule,
just ask me anytime!"
```

---

## Component Design

### 1. MCP Server (`mcp/mcp_server.py`)

```python
"""
MCP Server - Handles Model Context Protocol communication
"""
from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import logging

app = FastAPI(title="Compliance MCP Server")
logger = logging.getLogger(__name__)

# MCP Protocol Models
class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Dict[str, Any]
    id: int

class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: int

# Tool Registry
TOOLS_REGISTRY = {}

def register_tool(name: str, schema: Dict[str, Any], handler: callable):
    """Register a new MCP tool"""
    TOOLS_REGISTRY[name] = {
        "schema": schema,
        "handler": handler
    }
    logger.info(f"Registered tool: {name}")

@app.post("/mcp")
async def mcp_handler(request: MCPRequest):
    """Main MCP request handler"""
    logger.info(f"MCP Request: {request.method}")

    if request.method == "tools/list":
        # Return available tools
        return MCPResponse(
            id=request.id,
            result={
                "tools": [
                    {
                        "name": name,
                        "description": tool["schema"]["description"],
                        "inputSchema": tool["schema"]["inputSchema"]
                    }
                    for name, tool in TOOLS_REGISTRY.items()
                ]
            }
        )

    elif request.method == "tools/call":
        # Execute tool
        tool_name = request.params.get("name")
        arguments = request.params.get("arguments", {})

        if tool_name not in TOOLS_REGISTRY:
            return MCPResponse(
                id=request.id,
                error={
                    "code": -32601,
                    "message": f"Tool not found: {tool_name}"
                }
            )

        try:
            handler = TOOLS_REGISTRY[tool_name]["handler"]
            result = await handler(**arguments)

            return MCPResponse(
                id=request.id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": result
                        }
                    ]
                }
            )
        except Exception as e:
            logger.error(f"Tool execution error: {str(e)}", exc_info=True)
            return MCPResponse(
                id=request.id,
                error={
                    "code": -32000,
                    "message": f"Tool execution failed: {str(e)}"
                }
            )

    else:
        return MCPResponse(
            id=request.id,
            error={
                "code": -32601,
                "message": f"Method not found: {request.method}"
            }
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "compliance-mcp-server"}
```

### 2. MCP Tools (`mcp/mcp_tools.py`)

```python
"""
MCP Tools - Tool definitions and handlers
"""
from typing import List, Dict, Any, Optional
import logging
from .orchestrator import ComplianceOrchestrator

logger = logging.getLogger(__name__)
orchestrator = ComplianceOrchestrator()

# Tool Schemas
TOOL_SCHEMAS = {
    "list_systems": {
        "description": "List all available systems for compliance review",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },

    "perform_access_review": {
        "description": "Perform a user access review for a specific system",
        "inputSchema": {
            "type": "object",
            "properties": {
                "system_name": {
                    "type": "string",
                    "description": "Name of the system to review (e.g., 'netsuite', 'okta', 'salesforce')",
                    "enum": ["netsuite", "okta", "salesforce"]
                },
                "analysis_type": {
                    "type": "string",
                    "description": "Type of analysis to perform",
                    "enum": ["sod_violations", "excessive_permissions", "inactive_users", "all"],
                    "default": "sod_violations"
                },
                "include_recommendations": {
                    "type": "boolean",
                    "description": "Include AI-powered remediation recommendations",
                    "default": True
                }
            },
            "required": ["system_name"]
        }
    },

    "get_user_violations": {
        "description": "Get detailed violation information for a specific user",
        "inputSchema": {
            "type": "object",
            "properties": {
                "system_name": {
                    "type": "string",
                    "description": "System name",
                    "enum": ["netsuite", "okta", "salesforce"]
                },
                "user_identifier": {
                    "type": "string",
                    "description": "User email or ID"
                },
                "include_ai_analysis": {
                    "type": "boolean",
                    "description": "Include AI-powered risk analysis",
                    "default": True
                }
            },
            "required": ["system_name", "user_identifier"]
        }
    },

    "remediate_violation": {
        "description": "Create a remediation plan or ticket for a violation",
        "inputSchema": {
            "type": "object",
            "properties": {
                "violation_id": {
                    "type": "string",
                    "description": "Violation ID"
                },
                "action": {
                    "type": "string",
                    "description": "Remediation action",
                    "enum": ["remove_role", "request_approval", "create_ticket", "notify_manager"]
                },
                "notes": {
                    "type": "string",
                    "description": "Additional notes for remediation"
                }
            },
            "required": ["violation_id", "action"]
        }
    },

    "schedule_review": {
        "description": "Schedule a recurring compliance review",
        "inputSchema": {
            "type": "object",
            "properties": {
                "system_name": {
                    "type": "string",
                    "description": "System to review",
                    "enum": ["netsuite", "okta", "salesforce"]
                },
                "frequency": {
                    "type": "string",
                    "description": "Review frequency",
                    "enum": ["daily", "weekly", "monthly"]
                },
                "day_of_week": {
                    "type": "string",
                    "description": "Day of week (for weekly reviews)",
                    "enum": ["monday", "tuesday", "wednesday", "thursday", "friday"]
                },
                "time": {
                    "type": "string",
                    "description": "Time in HH:MM format (24-hour)",
                    "pattern": "^([0-1][0-9]|2[0-3]):[0-5][0-9]$"
                },
                "timezone": {
                    "type": "string",
                    "description": "Timezone (e.g., 'America/Los_Angeles')",
                    "default": "America/Los_Angeles"
                }
            },
            "required": ["system_name", "frequency"]
        }
    },

    "get_violation_stats": {
        "description": "Get aggregate violation statistics across systems",
        "inputSchema": {
            "type": "object",
            "properties": {
                "systems": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of systems to include (empty = all systems)"
                },
                "time_range": {
                    "type": "string",
                    "description": "Time range for statistics",
                    "enum": ["today", "week", "month", "quarter", "year"],
                    "default": "month"
                }
            },
            "required": []
        }
    }
}

# Tool Handlers

async def list_systems_handler() -> str:
    """List all available systems"""
    systems = await orchestrator.list_available_systems()

    result = "Available Systems for Compliance Review:\n\n"
    for system in systems:
        result += f"• {system['name']} ({system['type']})\n"
        result += f"  Status: {system['status']}\n"
        result += f"  Users: {system['user_count']}\n"
        result += f"  Last reviewed: {system['last_review']}\n\n"

    return result

async def perform_access_review_handler(
    system_name: str,
    analysis_type: str = "sod_violations",
    include_recommendations: bool = True
) -> str:
    """Perform access review"""
    logger.info(f"Performing access review: {system_name}, {analysis_type}")

    # Orchestrator coordinates the review
    result = await orchestrator.perform_access_review(
        system_name=system_name,
        analysis_type=analysis_type,
        include_recommendations=include_recommendations
    )

    # Format response
    output = f"Access Review Complete - {result['system_name']}\n\n"
    output += f"Users Analyzed: {result['users_analyzed']}\n"
    output += f"Total Violations: {result['total_violations']}\n"
    output += f"High-Risk Violations: {result['high_risk_count']}\n"
    output += f"Medium-Risk Violations: {result['medium_risk_count']}\n"
    output += f"Low-Risk Violations: {result['low_risk_count']}\n\n"

    if result['top_violators']:
        output += "Top Violators:\n"
        for i, user in enumerate(result['top_violators'][:5], 1):
            output += f"{i}. {user['name']} ({user['email']}) - {user['violation_count']} violations\n"

    if include_recommendations and result.get('recommendations'):
        output += f"\n{result['recommendations']}\n"

    return output

async def get_user_violations_handler(
    system_name: str,
    user_identifier: str,
    include_ai_analysis: bool = True
) -> str:
    """Get user violation details"""
    logger.info(f"Fetching violations for user: {user_identifier} in {system_name}")

    result = await orchestrator.get_user_violations(
        system_name=system_name,
        user_identifier=user_identifier,
        include_ai_analysis=include_ai_analysis
    )

    output = f"{result['user_name']} - Violation Report\n\n"
    output += f"Email: {result['email']}\n"
    output += f"System: {result['system']}\n"
    output += f"Roles: {', '.join(result['roles'])}\n"
    output += f"Total Violations: {result['violation_count']}\n\n"

    output += "Violations:\n\n"
    for i, violation in enumerate(result['violations'], 1):
        output += f"{i}. {violation['severity'].upper()}: {violation['rule_name']}\n"
        output += f"   Description: {violation['description']}\n"
        output += f"   Risk: {violation['risk_description']}\n"
        output += f"   Status: {violation['status']}\n\n"

    if include_ai_analysis and result.get('ai_analysis'):
        output += f"\nAI Analysis:\n{result['ai_analysis']}\n"

    return output

async def remediate_violation_handler(
    violation_id: str,
    action: str,
    notes: str = ""
) -> str:
    """Create remediation plan"""
    logger.info(f"Creating remediation for violation: {violation_id}, action: {action}")

    result = await orchestrator.remediate_violation(
        violation_id=violation_id,
        action=action,
        notes=notes
    )

    output = "✅ Remediation Initiated\n\n"
    output += f"Violation ID: {violation_id}\n"
    output += f"Action: {action}\n"
    output += f"Status: {result['status']}\n"

    if result.get('ticket_id'):
        output += f"Ticket Created: {result['ticket_id']}\n"

    if result.get('next_steps'):
        output += f"\nNext Steps:\n"
        for step in result['next_steps']:
            output += f"• {step}\n"

    return output

async def schedule_review_handler(
    system_name: str,
    frequency: str,
    day_of_week: Optional[str] = None,
    time: Optional[str] = None,
    timezone: str = "America/Los_Angeles"
) -> str:
    """Schedule recurring review"""
    logger.info(f"Scheduling review: {system_name}, {frequency}")

    result = await orchestrator.schedule_review(
        system_name=system_name,
        frequency=frequency,
        day_of_week=day_of_week,
        time=time,
        timezone=timezone
    )

    output = "✅ Review Scheduled Successfully\n\n"
    output += f"System: {result['system_name']}\n"
    output += f"Frequency: {result['frequency']}\n"
    output += f"Schedule: {result['schedule_description']}\n"
    output += f"Next Run: {result['next_run']}\n"
    output += f"Timezone: {result['timezone']}\n\n"
    output += "Notifications will be sent via:\n"
    for channel in result['notification_channels']:
        output += f"• {channel}\n"

    return output

async def get_violation_stats_handler(
    systems: List[str] = None,
    time_range: str = "month"
) -> str:
    """Get violation statistics"""
    logger.info(f"Fetching violation stats: {systems}, {time_range}")

    result = await orchestrator.get_violation_stats(
        systems=systems,
        time_range=time_range
    )

    output = f"Violation Statistics - {time_range.capitalize()}\n\n"
    output += f"Total Systems: {result['system_count']}\n"
    output += f"Total Users: {result['total_users']}\n"
    output += f"Total Violations: {result['total_violations']}\n"
    output += f"High-Risk: {result['high_risk']} ({result['high_risk_percent']}%)\n"
    output += f"Medium-Risk: {result['medium_risk']} ({result['medium_risk_percent']}%)\n"
    output += f"Low-Risk: {result['low_risk']} ({result['low_risk_percent']}%)\n\n"

    output += "Violations by System:\n"
    for system in result['by_system']:
        output += f"• {system['name']}: {system['violation_count']} violations\n"

    output += f"\nTrend: {result['trend_description']}\n"

    return output

# Register all tools
def register_all_tools(server):
    """Register all tools with the MCP server"""
    from .mcp_server import register_tool

    register_tool("list_systems", TOOL_SCHEMAS["list_systems"], list_systems_handler)
    register_tool("perform_access_review", TOOL_SCHEMAS["perform_access_review"], perform_access_review_handler)
    register_tool("get_user_violations", TOOL_SCHEMAS["get_user_violations"], get_user_violations_handler)
    register_tool("remediate_violation", TOOL_SCHEMAS["remediate_violation"], remediate_violation_handler)
    register_tool("schedule_review", TOOL_SCHEMAS["schedule_review"], schedule_review_handler)
    register_tool("get_violation_stats", TOOL_SCHEMAS["get_violation_stats"], get_violation_stats_handler)

    logger.info(f"Registered {len(TOOL_SCHEMAS)} MCP tools")
```

### 3. Orchestrator (`mcp/orchestrator.py`)

```python
"""
Compliance Orchestrator - Coordinates agents and connectors
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

# Import existing agents
from agents.analysis_agent import AnalysisAgent
from agents.notifier import NotificationAgent
from agents.knowledge_base_pgvector import KnowledgeBaseAgent

# Import connectors
from connectors.netsuite_connector import NetSuiteConnector
from connectors.okta_connector import OktaConnector

# Import repositories
from repositories.user_repository import UserRepository
from repositories.violation_repository import ViolationRepository
from repositories.sod_rule_repository import SODRuleRepository

# Import database
from models.database_config import DatabaseConfig

logger = logging.getLogger(__name__)

class ComplianceOrchestrator:
    """
    Orchestrates compliance operations across agents and connectors
    """

    def __init__(self):
        # Initialize database
        self.db_config = DatabaseConfig()
        self.session = self.db_config.get_session()

        # Initialize repositories
        self.user_repo = UserRepository(self.session)
        self.violation_repo = ViolationRepository(self.session)
        self.rule_repo = SODRuleRepository(self.session)

        # Initialize agents
        self.analysis_agent = AnalysisAgent(
            rule_repo=self.rule_repo,
            user_repo=self.user_repo,
            violation_repo=self.violation_repo
        )
        self.notifier_agent = NotificationAgent(
            violation_repo=self.violation_repo,
            user_repo=self.user_repo,
            enable_cache=True
        )
        self.kb_agent = KnowledgeBaseAgent(
            sod_rule_repo=self.rule_repo
        )

        # Initialize connectors
        self.connectors = {
            "netsuite": NetSuiteConnector(),
            "okta": OktaConnector()
        }

        logger.info("ComplianceOrchestrator initialized")

    async def list_available_systems(self) -> List[Dict[str, Any]]:
        """List all configured systems"""
        systems = []

        for name, connector in self.connectors.items():
            status = await connector.test_connection()
            users = await connector.get_user_count()
            last_review = self.violation_repo.get_last_review_date(name)

            systems.append({
                "name": name,
                "type": connector.get_system_type(),
                "status": "connected" if status else "disconnected",
                "user_count": users,
                "last_review": last_review.strftime("%Y-%m-%d") if last_review else "Never"
            })

        return systems

    async def perform_access_review(
        self,
        system_name: str,
        analysis_type: str = "sod_violations",
        include_recommendations: bool = True
    ) -> Dict[str, Any]:
        """
        Perform a comprehensive access review

        Steps:
        1. Fetch users/roles from external system
        2. Sync to local database
        3. Run SOD analysis
        4. Generate AI recommendations
        5. Return structured results
        """
        logger.info(f"Starting access review for {system_name}")

        # Step 1: Get connector
        connector = self.connectors.get(system_name)
        if not connector:
            raise ValueError(f"System not configured: {system_name}")

        # Step 2: Fetch data from external system
        logger.info(f"Fetching data from {system_name}...")
        users_data = await connector.fetch_users_with_roles()

        # Step 3: Sync to database
        logger.info(f"Syncing {len(users_data)} users to database...")
        synced_users = await connector.sync_to_database(users_data, self.user_repo)

        # Step 4: Run SOD analysis
        logger.info("Running SOD analysis...")
        violations = self.analysis_agent.detect_sod_violations(user_ids=[u.id for u in synced_users])

        # Step 5: Calculate statistics
        high_risk = len([v for v in violations if v.severity == "HIGH"])
        medium_risk = len([v for v in violations if v.severity == "MEDIUM"])
        low_risk = len([v for v in violations if v.severity == "LOW"])

        # Step 6: Get top violators
        user_violation_counts = {}
        for violation in violations:
            user_id = violation.user_id
            if user_id not in user_violation_counts:
                user_violation_counts[user_id] = {
                    "user": self.user_repo.get_user_by_id(user_id),
                    "count": 0
                }
            user_violation_counts[user_id]["count"] += 1

        top_violators = sorted(
            [{"name": v["user"].name, "email": v["user"].email, "violation_count": v["count"]}
             for v in user_violation_counts.values()],
            key=lambda x: x["violation_count"],
            reverse=True
        )

        # Step 7: Generate AI recommendations (if requested)
        recommendations = ""
        if include_recommendations and violations:
            logger.info("Generating AI recommendations...")
            recommendations = await self._generate_recommendations(system_name, violations)

        # Step 8: Store results
        await self._store_review_results(system_name, violations)

        return {
            "system_name": system_name,
            "timestamp": datetime.utcnow().isoformat(),
            "users_analyzed": len(synced_users),
            "total_violations": len(violations),
            "high_risk_count": high_risk,
            "medium_risk_count": medium_risk,
            "low_risk_count": low_risk,
            "top_violators": top_violators,
            "recommendations": recommendations
        }

    async def get_user_violations(
        self,
        system_name: str,
        user_identifier: str,
        include_ai_analysis: bool = True
    ) -> Dict[str, Any]:
        """Get detailed violations for a specific user"""
        logger.info(f"Fetching violations for {user_identifier} in {system_name}")

        # Find user
        user = self.user_repo.get_user_by_email(user_identifier)
        if not user:
            user = self.user_repo.get_user_by_id(user_identifier)

        if not user:
            raise ValueError(f"User not found: {user_identifier}")

        # Get violations
        violations = self.violation_repo.get_violations_by_user(user.id)

        # Get user roles
        roles = [ur.role.role_name for ur in user.user_roles]

        # Format violations
        formatted_violations = []
        for v in violations:
            formatted_violations.append({
                "id": str(v.id),
                "rule_name": v.rule.rule_name,
                "severity": v.severity,
                "description": v.rule.description,
                "risk_description": v.rule.risk,
                "status": v.status,
                "detected_at": v.detected_at.isoformat()
            })

        # Generate AI analysis (if requested)
        ai_analysis = ""
        if include_ai_analysis and violations:
            ai_analysis = self.notifier_agent._generate_ai_analysis(user, violations, roles)

        return {
            "user_name": user.name,
            "email": user.email,
            "system": system_name,
            "roles": roles,
            "violation_count": len(violations),
            "violations": formatted_violations,
            "ai_analysis": ai_analysis
        }

    async def remediate_violation(
        self,
        violation_id: str,
        action: str,
        notes: str = ""
    ) -> Dict[str, Any]:
        """Create remediation plan for violation"""
        logger.info(f"Creating remediation for violation {violation_id}: {action}")

        # Get violation
        violation = self.violation_repo.get_violation_by_id(violation_id)
        if not violation:
            raise ValueError(f"Violation not found: {violation_id}")

        # TODO: Implement actual remediation actions
        # For now, return a mock response

        return {
            "status": "initiated",
            "violation_id": violation_id,
            "action": action,
            "ticket_id": f"REM-{violation_id[:8]}",
            "next_steps": [
                "Notification sent to user's manager",
                "Remediation ticket created in ServiceNow",
                "Scheduled for review in 7 days"
            ]
        }

    async def schedule_review(
        self,
        system_name: str,
        frequency: str,
        day_of_week: Optional[str] = None,
        time: Optional[str] = None,
        timezone: str = "America/Los_Angeles"
    ) -> Dict[str, Any]:
        """Schedule recurring review"""
        logger.info(f"Scheduling {frequency} review for {system_name}")

        # TODO: Implement actual scheduling (use APScheduler or similar)
        # For now, return a mock response

        schedule_desc = self._build_schedule_description(frequency, day_of_week, time)
        next_run = self._calculate_next_run(frequency, day_of_week, time, timezone)

        return {
            "system_name": system_name,
            "frequency": frequency,
            "schedule_description": schedule_desc,
            "next_run": next_run,
            "timezone": timezone,
            "notification_channels": ["Email", "Claude UI"]
        }

    async def get_violation_stats(
        self,
        systems: Optional[List[str]] = None,
        time_range: str = "month"
    ) -> Dict[str, Any]:
        """Get aggregate violation statistics"""
        logger.info(f"Fetching violation stats for {time_range}")

        # TODO: Implement actual statistics queries
        # For now, return mock data

        return {
            "system_count": len(systems) if systems else 2,
            "total_users": 142,
            "total_violations": 47,
            "high_risk": 12,
            "high_risk_percent": 26,
            "medium_risk": 20,
            "medium_risk_percent": 43,
            "low_risk": 15,
            "low_risk_percent": 31,
            "by_system": [
                {"name": "netsuite", "violation_count": 30},
                {"name": "okta", "violation_count": 17}
            ],
            "trend_description": "Violations decreased 15% compared to last period"
        }

    # Helper methods

    async def _generate_recommendations(
        self,
        system_name: str,
        violations: List
    ) -> str:
        """Generate AI-powered recommendations"""
        # Use existing NotificationAgent for AI generation
        summary = f"Based on the analysis of {len(violations)} violations in {system_name}..."
        # TODO: Generate comprehensive recommendations
        return summary

    async def _store_review_results(self, system_name: str, violations: List):
        """Store review results for audit trail"""
        # TODO: Implement audit logging
        logger.info(f"Stored review results for {system_name}: {len(violations)} violations")

    def _build_schedule_description(
        self,
        frequency: str,
        day_of_week: Optional[str],
        time: Optional[str]
    ) -> str:
        """Build human-readable schedule description"""
        if frequency == "daily":
            return f"Every day at {time or '09:00'}"
        elif frequency == "weekly":
            return f"Every {day_of_week or 'Monday'} at {time or '09:00'}"
        elif frequency == "monthly":
            return f"First day of each month at {time or '09:00'}"
        return frequency

    def _calculate_next_run(
        self,
        frequency: str,
        day_of_week: Optional[str],
        time: Optional[str],
        timezone: str
    ) -> str:
        """Calculate next run timestamp"""
        # TODO: Implement actual calculation
        return "2026-02-17 09:00:00 PST"
```

---

## NetSuite Integration

### NetSuite RESTlet

The NetSuite connector will communicate with a NetSuite RESTlet (server-side script) to fetch user and role data.

**NetSuite RESTlet (SuiteScript 2.0)**:

```javascript
/**
 * @NApiVersion 2.1
 * @NScriptType Restlet
 * @NModuleScope SameAccount
 */
define(['N/search', 'N/record'], function(search, record) {

    /**
     * GET handler - Fetch users with roles
     */
    function doGet(requestParams) {
        try {
            var users = [];

            // Search for employees with roles
            var employeeSearch = search.create({
                type: search.Type.EMPLOYEE,
                filters: [
                    ['isinactive', 'is', 'F']
                ],
                columns: [
                    'entityid',
                    'email',
                    'firstname',
                    'lastname',
                    'role',
                    'subsidiary'
                ]
            });

            employeeSearch.run().each(function(result) {
                var userId = result.id;
                var email = result.getValue('email');
                var firstName = result.getValue('firstname');
                var lastName = result.getValue('lastname');
                var roleName = result.getText('role');
                var roleId = result.getValue('role');

                // Get additional permissions for this user
                var permissions = getUserPermissions(userId);

                users.push({
                    id: userId,
                    email: email,
                    name: firstName + ' ' + lastName,
                    roles: [{
                        id: roleId,
                        name: roleName,
                        permissions: permissions
                    }],
                    is_active: true,
                    source_system: 'netsuite'
                });

                return true; // Continue iteration
            });

            return {
                success: true,
                count: users.length,
                users: users
            };

        } catch (e) {
            return {
                success: false,
                error: e.message
            };
        }
    }

    /**
     * Get user permissions
     */
    function getUserPermissions(userId) {
        // Query user's effective permissions
        var permissions = [];

        // This is a simplified example - actual implementation
        // would query NetSuite permission records

        return permissions;
    }

    return {
        get: doGet
    };
});
```

### NetSuite Connector (`connectors/netsuite_connector.py`)

```python
"""
NetSuite Connector - Fetches data via RESTlet
"""
import os
import logging
from typing import List, Dict, Any
import aiohttp
import oauthlib
from oauthlib import oauth1

logger = logging.getLogger(__name__)

class NetSuiteConnector:
    """
    Connects to NetSuite via RESTlet to fetch user/role data
    """

    def __init__(self):
        # NetSuite OAuth 1.0 credentials
        self.account_id = os.getenv('NETSUITE_ACCOUNT_ID')
        self.consumer_key = os.getenv('NETSUITE_CONSUMER_KEY')
        self.consumer_secret = os.getenv('NETSUITE_CONSUMER_SECRET')
        self.token_id = os.getenv('NETSUITE_TOKEN_ID')
        self.token_secret = os.getenv('NETSUITE_TOKEN_SECRET')

        # RESTlet URL
        self.restlet_url = os.getenv('NETSUITE_RESTLET_URL')

        # OAuth client
        self.oauth_client = oauth1.Client(
            client_key=self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=self.token_id,
            resource_owner_secret=self.token_secret,
            realm=self.account_id,
            signature_method=oauth1.SIGNATURE_HMAC_SHA256
        )

        logger.info("NetSuiteConnector initialized")

    def get_system_type(self) -> str:
        return "ERP"

    async def test_connection(self) -> bool:
        """Test NetSuite connection"""
        try:
            async with aiohttp.ClientSession() as session:
                # Sign request
                uri, headers, body = self.oauth_client.sign(self.restlet_url)

                async with session.get(uri, headers=headers) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"NetSuite connection test failed: {str(e)}")
            return False

    async def get_user_count(self) -> int:
        """Get total user count"""
        # Could be optimized with a separate endpoint
        users = await self.fetch_users_with_roles()
        return len(users)

    async def fetch_users_with_roles(self) -> List[Dict[str, Any]]:
        """
        Fetch all users with their roles from NetSuite

        Returns:
            List of user dictionaries with roles
        """
        logger.info("Fetching users from NetSuite RESTlet...")

        try:
            async with aiohttp.ClientSession() as session:
                # Sign request with OAuth
                uri, headers, body = self.oauth_client.sign(
                    self.restlet_url,
                    http_method='GET'
                )

                # Add NetSuite headers
                headers['Content-Type'] = 'application/json'
                headers['Accept'] = 'application/json'

                async with session.get(uri, headers=headers) as response:
                    if response.status != 200:
                        raise Exception(f"NetSuite API error: {response.status}")

                    data = await response.json()

                    if not data.get('success'):
                        raise Exception(f"NetSuite RESTlet error: {data.get('error')}")

                    users = data.get('users', [])
                    logger.info(f"Fetched {len(users)} users from NetSuite")

                    return users

        except Exception as e:
            logger.error(f"Failed to fetch NetSuite users: {str(e)}")
            raise

    async def sync_to_database(self, users_data: List[Dict], user_repo) -> List:
        """
        Sync fetched users to local database

        Returns:
            List of synced User objects
        """
        logger.info(f"Syncing {len(users_data)} NetSuite users to database...")

        synced_users = []

        for user_data in users_data:
            # Upsert user
            user = user_repo.upsert_user(
                name=user_data['name'],
                email=user_data['email'],
                department=user_data.get('department'),
                is_active=user_data.get('is_active', True),
                source_system='netsuite'
            )

            # Sync roles
            for role_data in user_data.get('roles', []):
                user_repo.assign_role(
                    user_id=user.id,
                    role_name=role_data['name'],
                    source_system='netsuite'
                )

            synced_users.append(user)

        logger.info(f"Synced {len(synced_users)} users to database")
        return synced_users
```

---

## Implementation Plan

### Phase 1: Foundation (Week 1-2)

**Goal**: Build MCP server infrastructure

1. **Set up MCP Server** (3 days)
   - [ ] Create `mcp/` directory structure
   - [ ] Implement `mcp_server.py` with FastAPI
   - [ ] Implement MCP protocol (JSON-RPC 2.0)
   - [ ] Add authentication/authorization
   - [ ] Write unit tests

2. **Build Tool Registry** (2 days)
   - [ ] Implement tool registration system
   - [ ] Add tool discovery endpoint
   - [ ] Create tool schema validation
   - [ ] Write tests for tool registration

3. **Create NetSuite Connector** (3 days)
   - [ ] Implement `connectors/netsuite_connector.py`
   - [ ] Set up OAuth 1.0 authentication
   - [ ] Build RESTlet client
   - [ ] Test connection to NetSuite
   - [ ] Write unit tests

4. **Build Orchestrator** (2 days)
   - [ ] Implement `orchestrator.py`
   - [ ] Add agent routing logic
   - [ ] Implement result aggregation
   - [ ] Write tests

**Deliverables**:
- Working MCP server accepting connections
- NetSuite data fetching operational
- Basic tool registration working

---

### Phase 2: Core Tools (Week 3-4)

**Goal**: Implement primary MCP tools

1. **Implement `perform_access_review` Tool** (3 days)
   - [ ] Define tool schema
   - [ ] Implement handler
   - [ ] Connect to orchestrator
   - [ ] Add error handling
   - [ ] Write integration tests

2. **Implement `get_user_violations` Tool** (2 days)
   - [ ] Define tool schema
   - [ ] Implement handler
   - [ ] Add AI analysis integration
   - [ ] Write tests

3. **Implement `list_systems` Tool** (1 day)
   - [ ] Define tool schema
   - [ ] Implement handler
   - [ ] Write tests

4. **Implement `get_violation_stats` Tool** (2 days)
   - [ ] Define tool schema
   - [ ] Implement handler with aggregation queries
   - [ ] Add time-range filtering
   - [ ] Write tests

5. **End-to-End Testing** (2 days)
   - [ ] Test complete workflow via Claude UI
   - [ ] Test error scenarios
   - [ ] Performance testing

**Deliverables**:
- Core tools functional
- Claude UI can trigger access reviews
- Results display correctly in Claude

---

### Phase 3: Advanced Features (Week 5-6)

**Goal**: Add scheduling, remediation, and monitoring

1. **Implement Scheduling** (3 days)
   - [ ] Add APScheduler integration
   - [ ] Implement `schedule_review` tool
   - [ ] Add cron job management
   - [ ] Build notification system
   - [ ] Write tests

2. **Implement Remediation** (3 days)
   - [ ] Implement `remediate_violation` tool
   - [ ] Add ticket creation (ServiceNow/Jira integration)
   - [ ] Build approval workflow
   - [ ] Write tests

3. **Add Audit Logging** (2 days)
   - [ ] Create `services/audit_logger.py`
   - [ ] Log all MCP requests
   - [ ] Add audit trail queries
   - [ ] Build audit dashboard

4. **Monitoring & Observability** (2 days)
   - [ ] Add Prometheus metrics
   - [ ] Create health check endpoints
   - [ ] Build monitoring dashboard
   - [ ] Set up alerts

**Deliverables**:
- Scheduling functional
- Remediation workflow operational
- Full audit trail
- Monitoring dashboard

---

### Phase 4: RBAC and Approval Workflows (Week 7) ✅ **COMPLETE**

**Goal**: Implement role-based access control and intelligent approval routing

**Status**: ✅ **COMPLETED 2026-02-13**

1. **User Authentication & Authorization** ✅
   - [x] Implement ApprovalService for RBAC logic
   - [x] User authentication against active NetSuite users
   - [x] Role validation and authority checking
   - [x] Risk-based approval levels (LOW/MEDIUM/HIGH/CRITICAL)
   - [x] Write comprehensive tests

2. **Session Initialization** ✅
   - [x] Implement `initialize_session` tool
   - [x] Personalized welcome message with user profile
   - [x] Display approval authority matrix
   - [x] Show available actions based on permissions
   - [x] Prevent unauthorized access attempts

3. **Approval Authority Tools** ✅
   - [x] Implement `check_my_approval_authority` tool
   - [x] Authority matrix for all risk levels
   - [x] Specific risk score validation
   - [x] Manager chain lookup capability
   - [x] Write tests for all authority levels

4. **Exception Approval Workflow** ✅
   - [x] Implement `request_exception_approval` tool
   - [x] Automatic RBAC validation
   - [x] Manager chain traversal for escalations
   - [x] Jira ticket creation for unauthorized requests
   - [x] Auto-approve for authorized users
   - [x] Comprehensive error handling

5. **Bug Fixes & Enhancements** ✅
   - [x] Fix user status enum comparison
   - [x] Support non-prefixed role names (CFO, Controller, etc.)
   - [x] Add None checks for authentication failures
   - [x] Safe field access for optional data
   - [x] Update tests with real database users

**Deliverables**: ✅ **ALL COMPLETE**
- 3 new MCP tools (initialize_session, check_my_approval_authority, request_exception_approval)
- ApprovalService with 600+ lines of RBAC logic
- 6 integration tests (all passing)
- Complete documentation (PHASE4_COMPLETE.md)
- Bug fixes and code quality improvements

**Approval Authority Map**:
```python
CRITICAL (≥75): CFO, Audit Committee only
HIGH (≥60):     CFO, Controller, VP Finance, CAO
MEDIUM (≥40):   Controller, Director, Compliance Officer
LOW (<40):      Manager, Director, Supervisor
```

**Key Features**:
- ✅ Prevents self-approval (conflict of interest)
- ✅ Validates against NetSuite roles
- ✅ Automatic routing to authorized approvers
- ✅ Manager chain lookup (up to 5 levels)
- ✅ Jira integration for escalations
- ✅ Comprehensive audit trail
- ✅ Personalized login experience

---

### Phase 5: Testing & Documentation (Week 8)

**Goal**: Production readiness

1. **Comprehensive Testing** (4 days)
   - [ ] Unit tests (90%+ coverage)
   - [ ] Integration tests
   - [ ] Load testing
   - [ ] Security testing
   - [ ] Claude UI testing

2. **Documentation** (2 days)
   - [ ] API documentation
   - [ ] Deployment guide
   - [ ] User guide
   - [ ] Troubleshooting guide

3. **Production Deployment** (2 days)
   - [ ] Deploy MCP server
   - [ ] Configure Claude UI connection
   - [ ] Set up monitoring
   - [ ] Create runbooks

4. **Training & Handoff** (2 days)
   - [ ] User training sessions
   - [ ] Admin training
   - [ ] Documentation review
   - [ ] Handoff to operations

**Deliverables**:
- Production-ready system
- Complete documentation
- Trained users
- Operational runbooks

---

### Phase 6: Reporting & Demo Enhancements (Week 9) ✅ **COMPLETE**

**Goal**: Enhanced reporting capabilities and demo user management

**Status**: ✅ **COMPLETED 2026-02-14**

#### 1. Violation Report Generation ✅

**Tool**: `generate_violation_report`

**Features**:
- Multiple output formats:
  - **Markdown** - Top N violations in table format for console
  - **Detailed** - Role conflict matrix with full context
  - **Excel** - Full audit report with color-coded severity and metadata
  - **CSV** - Basic data export for external analysis
- Automatic file generation in `/tmp/compliance_reports/`
- Professional Excel formatting with:
  - Color-coded severity (Red/Orange/Yellow/Green)
  - Summary metadata sheet
  - Auto-sized columns
  - Header formatting

**Implementation**:
- `services/violation_report_service.py` - Report generation logic
- `generate_violation_report_handler()` - MCP tool handler
- Requires: `pandas`, `openpyxl` for Excel export

#### 2. Tabular Violation Analysis ✅

**Enhancement**: Updated `get_user_violations` tool

**New Formats**:
- **Table** (default) - Structured markdown tables:
  - Summary metrics table (total, severity breakdown)
  - Top 3 critical conflicts table (violation type, risk score, impact)
  - Action required table (priority, action, impact)
- **Concise** - Ultra-brief text format for quick analysis
- **Detailed** - Original full violation list format

**Default Format**: Changed from `detailed` to `table` for better UX

**Use Cases**:
- Executive summaries
- Screenshots for presentations
- External demo scenarios
- Quick compliance checks

#### 3. Demo User System ✅

**Purpose**: Sanitized test users for external demos without company branding

**Script**: `scripts/create_demo_user.py`

**Features**:
- Copies user profile from source user (e.g., Robin Turner)
- Sanitizes all data:
  - Removes "Fivetran -" prefix from role names
  - Changes `fivetran.com` → `xyz.com` in emails
  - Removes "Fivetran :" from department names
  - Replaces "Fivetran" → "Company" in text fields
- Creates sanitized roles if they don't exist
- Copies all violations with sanitized role references
- Supports custom names/emails for different demo scenarios

**Commands**:
```bash
# Create demo user
python3 scripts/create_demo_user.py --create

# Create custom demo user
python3 scripts/create_demo_user.py --create \
  --name "Jane Doe" \
  --email "jane.doe@acme.com" \
  --source "robin.turner@fivetran.com"

# Delete demo user
python3 scripts/create_demo_user.py --delete
```

**Demo User**: `test_user@xyz.com`
- Department: G&A : Finance (no "Fivetran")
- Roles: Controller, Administrator, NetSuite 360 (sanitized)
- Violations: 384 (same as source, sanitized data)

**Documentation**: `docs/DEMO_USER_GUIDE.md`

#### 4. Bug Fixes ✅

**Issue 1: Department Filtering - Exact Match**
- **Problem**: `list_all_users` used exact match for departments
- **Impact**: Query for "Finance" didn't match "Fivetran : G&A : Finance"
- **Fix**: Changed to partial/substring matching
- **File**: `mcp/orchestrator.py` line 751
- **Result**: "Finance" now matches 76 users

**Issue 2: Violation Count Always Zero**
- **Problem**: `get_user_by_email(email, system_name)` - wrong parameter count
- **Impact**: All users showed 0 violations in filtered lists
- **Fix**: Removed invalid `system_name` parameter
- **File**: `mcp/orchestrator.py` line 763
- **Result**: Violation counts now display correctly (Robin Turner: 384)

**Deliverables**:
- ✅ 1 new MCP tool (`generate_violation_report`)
- ✅ 3 output formats (markdown, Excel, CSV)
- ✅ Tabular analysis format (default)
- ✅ Demo user creation script
- ✅ Demo user guide documentation
- ✅ 2 critical bug fixes
- ✅ Department filtering enhancement

**Tool Count**: Now **34 total tools** (33 compliance + 1 reporting)

---

## Security & Compliance

### Authentication & Authorization

1. **MCP Server Authentication**
   - API key authentication for Claude UI
   - OAuth 2.0 for external systems
   - Token rotation every 90 days

2. **Authorization** ✅ **IMPLEMENTED**
   - Role-based access control (RBAC) for exception approvals
   - 4-tier approval authority (CRITICAL/HIGH/MEDIUM/LOW)
   - CFO/Controller/Director/Manager role validation
   - Users can only approve exceptions within their authority level
   - Automatic escalation to authorized approvers
   - Manager chain traversal for routing
   - Prevents self-approval (conflict of interest)
   - Session initialization shows user's permissions
   - Audit all authorization decisions

3. **Data Encryption**
   - TLS 1.3 for all connections
   - Encrypt sensitive data at rest
   - Use secrets manager for credentials

### Compliance Requirements

1. **SOX Compliance**
   - Audit trail for all actions
   - Segregation of duties enforced
   - Access review logs retained 7 years

2. **GDPR Compliance**
   - PII handling controls
   - Right to erasure implementation
   - Data minimization

3. **Security Controls**
   - Rate limiting (100 requests/minute)
   - Input validation
   - SQL injection prevention
   - XSS prevention

---

## Technical Requirements

### Infrastructure

1. **MCP Server**
   - Python 3.11+
   - FastAPI/Starlette
   - Redis for session storage
   - PostgreSQL for data storage

2. **NetSuite Integration**
   - OAuth 1.0 authentication
   - RESTlet deployment
   - TLS 1.3 connection

3. **Deployment**
   - Docker containers
   - Kubernetes (optional)
   - AWS/GCP/Azure compatible

### Performance Requirements

1. **Response Times**
   - Tool discovery: <100ms
   - Simple queries: <500ms
   - Access review: <30 seconds
   - Violation analysis: <5 seconds

2. **Scalability**
   - Support 1000+ concurrent users
   - Handle 10,000+ users per system
   - Process 100+ requests/second

3. **Availability**
   - 99.9% uptime SLA
   - Zero-downtime deployments
   - Automatic failover

---

### Response Style Guidelines (Added 2026-02-13)

**Requirement:** MCP tool responses must be concise and executive-friendly.

**Target Format:**
- **Length:** 10-15 lines (max 20 lines)
- **Structure:** Lead with recommendation → Key metrics → Options → Summary
- **Avoid:** Verbose bullet lists (6+ items), repetitive sections, extensive implementation details

**Example:**
```markdown
❌ DENY REQUEST

Conflicts: 31 SOD violations (29 CRITICAL)
Key Issue: User can create AND approve own transactions
Risk: 77.5/100

Options:
1. Deny (recommended) - $0, zero risk
2. Split roles - $0, assign to 2 people
3. Approve with controls - $100K/year

Recommendation: Keep roles separate.
```

**Implementation:**
- Tool descriptions include conciseness guidance
- `mcp/RESPONSE_STYLE_GUIDE.md` provides detailed format examples
- FastAPI server description includes response style guidance

### Dependency Requirements (Updated 2026-02-13)

**Core Dependencies:**
```python
# LangChain & AI
langchain>=0.3.12                   # AI framework
langchain-core>=0.3.34              # Core components
langchain-anthropic>=0.3.7          # Anthropic integration
anthropic>=0.45.0,<1.0.0           # Claude API client

# Data & Validation
pydantic>=2.7.4,<3.0.0             # Data validation
pydantic-settings>=2.4.0,<3.0.0    # Settings management

# API Framework
fastapi==0.104.1                    # Web framework
uvicorn==0.24.0                     # ASGI server

# Embeddings & ML
sentence-transformers>=2.3.0        # Text embeddings (upgraded from 2.2.2)

# Security
cryptography>=46.0.0                # Encryption (added)
```

**Key Changes:**
- Upgraded sentence-transformers (2.2.2 → 5.1.2) for huggingface-hub compatibility
- Added cryptography package for config encryption
- Changed from exact pins (`==`) to compatible ranges (`>=,<`) for better dependency resolution

**Rationale:** Using version ranges instead of exact pins prevents cascading dependency conflicts when packages update their requirements.


## Success Criteria

### Technical Metrics

✅ MCP server operational with <100ms latency
✅ Claude UI successfully triggers access reviews
✅ NetSuite data fetching working (100% success rate)
✅ SOD analysis completes in <30 seconds for 1000 users
✅ 90%+ test coverage
✅ Zero critical security vulnerabilities

### Business Metrics

✅ Users can request reviews via natural language
✅ 90% reduction in manual review time
✅ 100% of violations detected automatically
✅ Audit trail complete and compliant
✅ User satisfaction >4.5/5

### Operational Metrics

✅ 99.9% uptime
✅ <5 minutes to resolve incidents
✅ Zero data loss
✅ Complete audit trail

---

## Next Steps

1. **Immediate** (Today)
   - ✅ Create feature branch: `feature/mcp-integration`
   - ✅ Create technical specification (this document)
   - [ ] Review and approve specification
   - [ ] Set up project tracking (Jira/GitHub Issues)

2. **This Week**
   - [ ] Set up development environment
   - [ ] Create NetSuite developer account
   - [ ] Deploy test RESTlet to NetSuite sandbox
   - [ ] Begin Phase 1 implementation

3. **Next Week**
   - [ ] Complete MCP server foundation
   - [ ] Test NetSuite integration
   - [ ] Begin tool implementation

---

## Resolved Questions (Originally Open)

1. **NetSuite RESTlet Deployment** ✅ Resolved
   - RESTlet deployed to sandbox (5260239-SB1); scripts 3684, 3685, 3686 active
   - Incremental sync uses `lastModifiedDate` filter to fetch only changed records

2. **Claude UI Integration** ✅ Resolved
   - STDIO-HTTP bridge (`mcp_stdio_http_bridge.py`) connects Claude Desktop to MCP server
   - API key authentication via `X-API-Key` header; key stored in `.env`

3. **Scheduling Infrastructure** ✅ Resolved
   - APScheduler used (BackgroundScheduler in DataCollectionAgent)
   - Full sync: daily at 2:00 AM; incremental: hourly
   - Runs in the same process as the MCP server

4. **Notification Channels** ✅ Resolved
   - SendGrid for email alerts (active)
   - Slack webhook via `SLACK_WEBHOOK_URL` env var for operational alerts
   - Slack Socket Mode bot for interactive compliance queries (new Feb 2026)

5. **Deployment Target** ✅ In Progress
   - Current: Local/dev environment (macOS)
   - Target: AWS (see `docs/AWS_PRODUCTION_DEPLOYMENT.md`)

---

## Slack Bot Integration (Added Feb 2026, Updated Feb 2026)

The Slack bot (`slack_bot_local.py`) provides a natural language interface to all 35 MCP tools via Socket Mode.

### Architecture (Post-ChatAnthropic Migration)

```
User (Slack) → Socket Mode → slack_bolt App → handle_mention()
                                                    │
                                    ┌───────────────┴───────────────┐
                                    │                               │
                              channel starts with "D"       channel thread
                              fetch_dm_history()            fetch_thread_history()
                              (conversations_history)       (conversations_replies)
                                    │                               │
                                    └───────────────┬───────────────┘
                                                    │
                          @traceable(name="slack_compliance_query", run_type="chain")
                                      process_with_claude()
                                                    │
                                         ChatAnthropic(opus-4-6)
                                         + TokenTrackingCallback
                                         + bind_tools(35 MCP tools)
                                         (prompt caching on system msg)
                                                    │
                                            Agentic loop (5 turns)
                                             response.tool_calls
                                                    │
                                         call_mcp_tool() → MCP Server (port 8080)
                                         ToolMessage → messages list
                                                    │
                                         Rolling summary: ChatAnthropic(haiku-4-5)
                                         when tool result > 2000 chars
                                                    │
                                         format_as_blocks() → Slack Block Kit
```

### Key Features

| Feature | Implementation |
|---------|---------------|
| Multi-turn reasoning | 5-turn loop via `response.tool_calls` (LangChain) |
| @mention resolution | `extract_user_mentions()` → Slack `users_info` API → email |
| DM conversation context | `fetch_dm_history()` via `conversations_history()` for `"D"` channels |
| Thread conversation context | `fetch_thread_history()` via `conversations_replies()` |
| Animated thinking | `_animate_thinking()` background thread, 2.5s stage cycling |
| Block Kit output | `format_as_blocks()` splits on `---` → section + divider blocks |
| Token optimization | Intent routing, prefix caching, output sanitization, history trimming |
| Token tracking | `TokenTrackingCallback(agent_name="slack_bot")` bridges LangChain → `TokenTracker` |
| LangSmith tracing | `@traceable` parent span + ChatAnthropic child spans; full cost/token visibility |

### LangSmith Observability

Every Slack query produces one `slack_compliance_query` trace in LangSmith with:
- Nested `ChatAnthropicMessages` child spans per LLM turn
- `total_cost`, `prompt_tokens`, `completion_tokens` populated via LangChain callbacks
- `ls_model_name` metadata for model pricing lookup (maps `claude-opus-4-6` → `claude-3-opus-20240229`)

Required env vars:
```bash
LANGSMITH_API_KEY=lsv2_pt_...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=compliance-agent
```

### Security

| Control | Value |
|---------|-------|
| MCP_API_KEY | Required env var, no default; raised ValueError if unset |
| MCP_ALLOWED_ORIGINS | Env var, defaults to `http://localhost` only |
| Database credentials | `os.getenv('DATABASE_URL')` only, never hardcoded |
| SQL parameters | Parameterized queries (`%s`) for all dynamic values |
| DB connections | All `psycopg2.connect()` wrapped in `try/finally conn.close()` |

### Memory Management (Phase A + B)

| Phase | Status | Commit |
|-------|--------|--------|
| Phase A — Redis MCP Cache | ✅ Live | `71d6113` + `2134a00`; bugfix `424fcf7` (2026-02-25) |
| Phase B — Conversation Summarization | ✅ Live | `3d1a1b3` |
| Phase feedback — Human Answer Scoring | ✅ Live | `547c187` (2026-02-26) |
| Phase C — Semantic Catalogue | ⏳ Pending | — |

**Phase A** caches MCP tool responses in Redis (TTL 5min–24h by tool). Cache is busted on `trigger_manual_sync`. LangSmith tags: `context_cache_hit`.

> **Bugfix (2026-02-25, commit `424fcf7`):** The LangSmith `context_cache_hit` metadata tag was previously applied on the child `call_mcp_tool` span, which LangSmith's evaluator executor cannot read inline (S3-backed). The fix moves metadata tagging to the root `slack_compliance_query` run using `threading.local()` (`_cache_hit_tls`): the child span sets a thread-local flag and the root `@traceable` wrapper reads and clears it after each query, ensuring the tag lands on the top-level trace that evaluators actually inspect.

> **Load tested (2026-02-25):** 50-call concurrent load test confirmed Phase A — warm cache batch: **0 real MCP API calls, 50 Redis hits** (100 % cache hit rate). P99 latency under load: 12 ms (vs ~50 ms cold).

**Phase B** generates Haiku summaries of each DM exchange, stored in `conversation_summaries` table (90-day TTL). Injects 3 most recent summaries as prior context (~150 tokens vs ~2K raw). LangSmith tags: `context_summaries_injected`.

**Phase feedback** appends `✅ Correct / ❌ Wrong / 🔧 Partial` Block Kit buttons to every bot response. Button clicks are handled by `@app.action("feedback_button")` — non-blocking `_save_feedback()` writes to `answer_feedback` Postgres table, posts `human_rating` score to LangSmith `create_feedback()`, and on NEGATIVE signal busts Redis violation cache (`mcp:get_user_violations:*`). Feature-flagged: `USE_ANSWER_FEEDBACK=true`. Buttons display as 👎 👍 emoji (NEGATIVE/POSITIVE only; PARTIAL signal removed). System prompt updated to enforce FivetranChat-style clean prose responses — no decorative emojis, lead with answer.

---

---

## LangSmith Evaluator Integration

### Overview

Three online evaluators run automatically on every `slack_compliance_query` trace.

### Evaluator Architecture Constraint

**Critical:** LangSmith's evaluator executor fetches run data via `/api/v1/runs/{id}`.
Child LLM `outputs.generations` are stored in S3 and are **not** available inline.
Any evaluator code that attempts to read `child_run.outputs.generations` will see `{}`.

**Implication for MCP tool detection:** Tool calls requested by the LLM (visible in
`generations[*][*].message.kwargs.tool_calls`) cannot be read by the evaluator.
The only reliable signal is `child_run.run_type == "tool"`, which requires
`call_mcp_tool()` to be decorated with `@traceable(run_type="tool")`.

### Evaluator Specs

#### `mcp_tool_called` (ID: `0fd34f6a-78f3-4073-b71b-4a890162fdad`)

```
Fires on: every trace
Pass (score=1): at least one tool-type child run OR text grounding markers in output
Fail (score=0): no tool runs AND <tool_call> XML in output OR no grounding evidence
```

Detection priority:
1. `child_run.run_type == "tool"` → score 1
2. `<tool_call>` or `<tool_result>` in output → score 0 (hallucinated)
3. Domain markers (`netsuite role`, `approval authority`, `sod conflict`, …) → score 1
4. None of the above → score 0

#### `mcp_tool_coverage` (ID: `36ea7cc4-7b1e-4994-b3dc-16443882dcbb`)

```
Fires on: access-request traces (message contains "assign", "role to", "grant", etc.)
Pass (score=1): analyze_access_request tool run OR SOD conflict text in output
Fail (score=0): access query with no analyze_access_request evidence
N/A (score=1): non-access-request queries
```

#### `hallucination_heuristic` (ID: `67f9da6a-6413-4a72-80a9-31d99ac9134c`)

```
Fires on: every trace
Pass (score=1): no numeric claims, OR claims present but response is grounded
Fail (score=0): <tool_call> XML in output (hallucinated), OR ungrounded numeric claims
```

Grounding evidence (same as mcp_tool_called layers 1 and 3).

### Slack Bot Tracing: `call_mcp_tool()`

```python
# slack_bot_local.py:108
@traceable(run_type="tool")          # ← creates tool-type child span per MCP call
def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    ...
    response = requests.post(f"{MCP_SERVER_URL}/mcp", json=mcp_request, ...)
```

Each invocation creates a child span with:
- `run_type = "tool"`
- `name = call_mcp_tool` (function name; tool_name is in `inputs`)
- `inputs = {"tool_name": "...", "arguments": {...}}`
- `outputs = {"output": "<tool result text>"}` (from return value)

This is the primary signal all 3 evaluators rely on for the post-v1.3 traces.

### Verified Scores (2026-02-23)

| Trace | mcp_tool_called | mcp_tool_coverage | hallucination |
|---|---|---|---|
| "can you report violations" (real Slack) | ✅ 1 | N/A | ✅ 1 |
| "tell me about my permissions" (real Slack) | ✅ 1 | N/A | ✅ 1 |
| "what can you do?" (haiku+opus, c06830c0) | ✅ 1 | N/A | ✅ 1 |
| "assign Controller role" (XML hallucination) | ❌ 0 | ❌ 0 | ❌ 0 |

**Model split verified** (trace `c06830c0`, 2026-02-23):
- Tool-dispatch turns: `claude-haiku-4-5-20251001` (turns 1–3)
- Synthesis turn: `claude-opus-4-6` (turn 4, after ToolMessages in history)
- 2 real `call_mcp_tool` spans | latency: 14.3s | status: success

---

## Role Risk Matrix: Database Tables

The role risk matrix is a precomputed SOD conflict database covering all 17 Fivetran roles and 153 unique role pairs. It is built by `scripts/build_role_risk_matrix.py` and stored in two tables.

### `sod_permission_map`

Maps each Fivetran role to the individual permission-level it holds per functional area. Level ordering: `None < View < Create < Edit < Full`.

| Column | Type | Description |
|--------|------|-------------|
| `role_name` | text | Fivetran role display name (e.g., `"Fivetran - Controller"`) |
| `permission_area` | text | Functional area (e.g., `"AP Processing"`, `"Payroll"`) |
| `permission_level` | text | One of `None`, `View`, `Create`, `Edit`, `Full` |
| `numeric_level` | int | Ordinal encoding: None=0, View=1, Create=2, Edit=3, Full=4 |

**Row count:** varies by role (typically 15–25 permission areas per role).

### `role_pair_conflicts`

One row per (role_a, role_b, sod_rule) combination where the pair violates an active SOD rule.

| Column | Type | Description |
|--------|------|-------------|
| `role_a` | text | First role in the pair (alphabetically first) |
| `role_b` | text | Second role in the pair |
| `sod_rule_id` | uuid | FK → `sod_rules.id` |
| `rule_name` | text | Human-readable rule name |
| `severity` | text | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` |
| `conflict_type` | text | `intra_role` (single role self-conflict) or `cross_role` (between two roles) |
| `permission_area_a` | text | Conflicting permission area held by role_a |
| `permission_area_b` | text | Conflicting permission area held by role_b |
| `level_a` | text | Permission level of role_a in area_a |
| `level_b` | text | Permission level of role_b in area_b |

**Row count:** 443 rows across 153 role pairs (as of 2026-02-27).

**Level-aware conflict detection:** a permission area only constitutes a conflict when the role holds level `Create` or higher (not `None` or `View`). This eliminates false positives from read-only access.

**Rebuild command:**
```bash
python3 scripts/build_role_risk_matrix.py
```

---

## New MCP Tools (v2.8.0)

### `get_role_risk_matrix`

**Purpose:** Query the precomputed SOD conflict matrix for one or more roles without hitting the violations table. Ideal for access-request screening ("what conflicts would this role combination produce?") and role-level risk reporting.

**When to use vs `list_violations`:**
- Use `get_role_risk_matrix` when the question is about **roles** (e.g., "what are the conflicts for the Controller role?", "is this role combination safe?").
- Use `list_violations` when the question is about **users with active violations** (e.g., "who has CRITICAL violations in Finance?").

**Input schema:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `role_name` | string | No | Filter to conflicts involving this role (partial match). Omit to return all roles. |
| `severity` | string | No | Filter by severity: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`. |
| `include_intra_role` | boolean | No (default `true`) | Include single-role self-conflicts. |
| `include_cross_role` | boolean | No (default `true`) | Include conflicts between two distinct roles. |
| `limit` | integer | No (default `50`) | Maximum rows to return. |

**Caching:** Results are cached in Redis for 24 hours (key prefix: `mcp:get_role_risk_matrix:`).

**Example call:**
```json
{
  "name": "get_role_risk_matrix",
  "arguments": {
    "role_name": "Controller",
    "severity": "CRITICAL",
    "include_intra_role": false
  }
}
```

**Example output (abridged):**
```
Role Risk Matrix — Controller (CRITICAL, cross-role only)

Role Pair                              Rule                         Areas
Controller + Administrator             AP Entry vs Approval         AP Processing / Payment Approval
Controller + Fivetran - Full Access    Journal Entry vs GL Posting  GL / Journal Entries

2 CRITICAL cross-role conflicts found.
```

---

### `list_violations`

**Purpose:** Return active violations from the `violations` table with optional filtering by department, severity, and status. Supports a `roles_only` mode that collapses per-user rows into a deduplicated role-centric view.

**Input schema:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `department` | string | No | Partial match against `users.department` (e.g., `"Finance"`). |
| `severity` | string | No | Filter by severity: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`. |
| `status` | string | No | Filter by violation status: `OPEN`, `RESOLVED`, `EXCEPTION`. Defaults to `OPEN`. |
| `roles_only` | boolean | No (default `false`) | When `true`, returns one row per unique role-pair combination (`DISTINCT ON`) instead of one row per user-violation. |
| `limit` | integer | No (default `50`) | Maximum rows to return. |

**Two operating modes:**

1. **Default (`roles_only=false`):** Returns user-level violations. Each row includes user email, roles, rule violated, severity, and detection date. Use for "who is in violation?" queries.

2. **Roles-only (`roles_only=true`):** Uses `DISTINCT ON (role_a, role_b, sod_rule_id)` to return one representative row per role-pair conflict. Use for "what role combinations are causing violations?" without enumerating every affected user.

**Example call (roles-only):**
```json
{
  "name": "list_violations",
  "arguments": {
    "department": "Finance",
    "severity": "CRITICAL",
    "roles_only": true,
    "limit": 20
  }
}
```

**Example output (roles-only mode):**
```
CRITICAL Role-Pair Violations — Finance (roles_only)

Role A                    Role B                Rule                      Count
Controller                Administrator         AP Entry vs Approval      12 users
Fivetran - Full Access    Controller            GL Posting vs Entry       4 users

2 distinct CRITICAL role pairs. 16 users affected.
```

---

## Tool Router: `utils/tool_router.py`

### What it does

The tool router is a **pre-filter** executed before each Slack query. Instead of sending all 37 MCP tool definitions to Claude on every turn (which would consume ~8K tokens of context window), the router inspects the user's query and returns only the subset of tools that are relevant to the detected intent.

This has two benefits:
1. **Token savings:** ~8K tokens saved per query when the full tool list is not needed.
2. **Reduced noise:** Claude makes better tool-selection decisions when presented with 5–10 focused tools rather than 37.

### How it works

```
User query text
      │
      ▼
tool_router.route(query: str) → List[str]   # returns tool names
      │
      ├── keyword/regex matching against intent groups
      │
      └── returns union of matched groups + always-on tools
```

The router is called once per Slack message in `process_with_claude()`. The returned tool names are used to filter the full MCP tool list before binding tools to the LangChain model.

### Intent groups

| Group name | Trigger keywords (examples) | Tools included |
|------------|----------------------------|----------------|
| `violations` | violation, sod, conflict, breach | `list_violations`, `get_user_violations`, `get_violation_stats` |
| `access_request` | assign, grant, can I give, role to, access for | `analyze_access_request`, `check_my_approval_authority` |
| `role_risk` | role risk, what conflicts, risk matrix, role combination, safe to assign | `get_role_risk_matrix`, `list_violations` |
| `user_lookup` | who is, find user, list users, department | `list_all_users`, `get_user_profile` |
| `reporting` | report, export, excel, csv, summary | `generate_violation_report`, `get_violation_stats` |
| `exceptions` | exception, approve, waiver, compensating | `request_exception_approval`, `list_exceptions` |
| `admin` | sync, trigger, status, health | `trigger_manual_sync`, `get_system_health` |

Always-on tools (included regardless of intent): `initialize_session`, `list_systems`.

### How to add a new tool

1. Implement the tool in `mcp/mcp_server.py` and add it to the `TOOLS` list.
2. Open `utils/tool_router.py`.
3. Add the tool name to the `tools` list of the most relevant existing intent group, OR create a new group:
   ```python
   "my_new_group": {
       "keywords": ["keyword1", "keyword2"],
       "tools": ["my_new_tool", "related_existing_tool"],
   },
   ```
4. If the tool should always be available regardless of query intent, add it to the `ALWAYS_ON` list.
5. Restart the Slack bot and MCP server.

**Warning:** A tool that is not registered in `tool_router.py` will never be called by Claude, even if it is correctly registered in the MCP server. This is the most common cause of "Claude ignores my new tool" bugs.

---

**Document Status**: ✅ Production — Up to Date
**Last Updated**: 2026-02-27
**Approvers**: Prabal Saha

---

**Document Version**: 2.8.0
**Last Updated**: 2026-02-27
**Author**: Prabal Saha + Claude (Sonnet 4.6)
**Branch**: `RD-1036683-billing-schedule-automation-dev`

**Change Log:**
- v2.8.0 (2026-02-27): Role risk matrix tables (sod_permission_map, role_pair_conflicts); get_role_risk_matrix tool; list_violations tool; tool_router intent routing system
- v2.7.0 (2026-02-27): FivetranChat-style formatting (clean prose, no decorative emojis); feedback buttons simplified to 👎 👍, PARTIAL signal dropped (commit `948f495`)
- v2.6.0 (2026-02-26): Added Phase feedback — human answer scoring via Block Kit buttons, `answer_feedback` table, LangSmith `human_rating` write-back (commit `547c187`)
- v2.5.0 (2026-02-26): Fixed LangSmith `context_cache_hit` root-run tagging (commit `424fcf7`, 2026-02-25) — metadata moved from child `call_mcp_tool` span to root `slack_compliance_query` run via `threading.local()`; 50-call concurrent load test: 0 real MCP API calls, 50 Redis hits (warm cache)
- v2.4.0 (2026-02-25): Phase A Redis MCP cache (cache bust on sync), Phase B conversation summarization, paginated RESTlet blind spot fix, stale role removal fix
- v2.3.0 (2026-02-23): Verified Haiku/Opus model split; updated verified scores table with trace c06830c0
- v2.2.0 (2026-02-22): Added LangSmith Evaluator Integration section — evaluator specs, S3 constraint, call_mcp_tool @traceable, verified score table
- v2.1.0 (2026-02-22): ChatAnthropic migration (raw SDK → LangChain), LangSmith full cost tracing, DM conversation context via fetch_dm_history(), TokenTrackingCallback, updated architecture diagram
- v2.0.0 (2026-02-18): Updated to production status; resolved all open questions; added Slack Bot Integration section; added Security section; updated tool count 34→35; documented token optimization and Block Kit UI
- v1.0.0 (2026-02-12): Initial design specification
