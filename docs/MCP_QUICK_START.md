# MCP Integration - Quick Start Guide

**Version**: 1.0.0
**Branch**: `feature/mcp-integration`
**Status**: 🚧 In Development

---

## What is This?

This project enables natural language interaction with the SOD Compliance System through Claude UI. Users can simply type requests like:

> "Perform a user access review of NetSuite"

And the system will:
1. Connect to NetSuite via RESTlet
2. Fetch all users and their roles
3. Analyze for SOD violations
4. Return detailed results in the conversation

---

## Architecture Overview

```
Claude UI → MCP Server → Orchestrator → Compliance Agents → NetSuite/Okta/etc.
```

**Key Components**:
- **MCP Server**: Handles communication with Claude UI (JSON-RPC protocol)
- **Orchestrator**: Routes requests to appropriate agents
- **Connectors**: Fetch data from external systems (NetSuite, Okta)
- **Agents**: Existing compliance agents (Analysis, Notifier, etc.)

---

## Quick Examples

### Example 1: List Available Systems

**User Input**:
```
What systems can you review?
```

**Claude Response**:
```
Available Systems for Compliance Review:

• netsuite (ERP)
  Status: connected
  Users: 142
  Last reviewed: 2026-02-10

• okta (Identity)
  Status: connected
  Users: 156
  Last reviewed: 2026-02-11
```

---

### Example 2: Perform Access Review

**User Input**:
```
Perform a user access review of NetSuite
```

**Claude Response**:
```
Access Review Complete - NetSuite

Users Analyzed: 142
Total Violations: 47
High-Risk Violations: 12
Medium-Risk Violations: 20
Low-Risk Violations: 15

Top Violators:
1. John Smith (john.smith@company.com) - 5 violations
2. Jane Doe (jane.doe@company.com) - 4 violations
3. Bob Johnson (bob.johnson@company.com) - 3 violations

Recommendations:
• Remove Administrator role from 3 users to reduce high-risk violations
• Implement dual approval for financial transactions
• Review all users with both Admin + Finance roles

Would you like to see details for any specific user?
```

---

### Example 3: Drill Into User Details

**User Input**:
```
Show me details for John Smith
```

**Claude Response**:
```
John Smith - Detailed Violation Report

Email: john.smith@company.com
System: NetSuite
Roles: Administrator, Finance Manager, Approver
Total Violations: 5

Violations:

1. HIGH RISK: Administrator + Finance Manager
   Description: Can create vendors AND approve payments
   Risk: Fraudulent payment creation
   Last detected: 2026-02-12
   Status: Active

2. HIGH RISK: Finance Manager + Approver
   Can enter invoices AND approve them
   Risk: Unauthorized expense approval
   Last detected: 2026-02-12
   Status: Active

[... 3 more violations ...]

AI Analysis:
This user has extensive financial and administrative access, creating
significant risk for fraudulent activity. Primary concern is the ability
to create financial transactions and self-approve them. Recommend:
1. Remove Administrator role (eliminates 3 violations)
2. Require dual approval for all payments >$10,000
3. Audit all financial transactions from past 90 days

Would you like me to generate a remediation ticket?
```

---

### Example 4: Schedule Recurring Review

**User Input**:
```
Schedule a weekly access review for NetSuite every Monday at 9 AM
```

**Claude Response**:
```
✅ Scheduled successfully!

Review Configuration:
- System: NetSuite
- Frequency: Weekly
- Schedule: Every Monday at 9:00 AM PST
- Next run: 2026-02-17 09:00:00 PST

Results will be:
- Saved to database
- Sent via email to your registered address
- Available in this chat for review

You'll receive a notification when each review completes.
```

---

## Implementation Status

### ✅ Completed (Before MCP Integration)
- PostgreSQL database with SOD rules
- SOD violation detection agents
- Okta integration
- pgvector semantic search
- Redis caching
- LLM-powered analysis

### 🚧 In Progress (MCP Integration)
- Phase 1: MCP server foundation (Week 1-2)
- Phase 2: Core tools (Week 3-4)
- Phase 3: Advanced features (Week 5-6)
- Phase 4: Testing & docs (Week 7-8)

### 📋 Planned Features
- Natural language interface via Claude UI
- NetSuite RESTlet integration
- Automated scheduling
- Remediation workflow
- Audit logging

---

## Development Setup

### Prerequisites

```bash
# Already installed (from existing project)
- Python 3.11+
- PostgreSQL 17 with pgvector
- Redis 7+
- pip packages from requirements.txt

# New requirements for MCP
- NetSuite developer account
- Claude API key (for testing)
```

### Environment Variables

```bash
# Existing (already configured)
DATABASE_URL=postgresql://localhost/compliance_db
REDIS_URL=redis://localhost:6379/0
ANTHROPIC_API_KEY=your_key_here

# New for MCP integration
NETSUITE_ACCOUNT_ID=your_account_id
NETSUITE_CONSUMER_KEY=your_consumer_key
NETSUITE_CONSUMER_SECRET=your_consumer_secret
NETSUITE_TOKEN_ID=your_token_id
NETSUITE_TOKEN_SECRET=your_token_secret
NETSUITE_RESTLET_URL=https://your_account.restlets.api.netsuite.com/...
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8080
```

### Start Development Server

```bash
# Switch to MCP branch
git checkout feature/mcp-integration

# Install new dependencies (when available)
pip3 install -r requirements.txt

# Start MCP server (when implemented)
python3 -m mcp.mcp_server

# Test with curl
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "params": {},
    "id": 1
  }'
```

---

## File Structure

```
compliance-agent/
├── mcp/                              # NEW - MCP server components
│   ├── __init__.py
│   ├── mcp_server.py                 # FastAPI server, MCP protocol
│   ├── mcp_tools.py                  # Tool definitions and handlers
│   └── orchestrator.py               # Agent routing and coordination
│
├── connectors/                       # NEW - External system connectors
│   ├── __init__.py
│   ├── base_connector.py             # Abstract base class
│   ├── netsuite_connector.py         # NetSuite RESTlet client
│   └── okta_connector.py             # Already exists, refactor to base
│
├── services/
│   └── audit_logger.py               # NEW - Audit trail logging
│
├── docs/
│   ├── MCP_INTEGRATION_SPEC.md       # NEW - Full technical spec
│   └── MCP_QUICK_START.md            # NEW - This file
│
└── [existing files remain unchanged]
```

---

## API Reference

### Available MCP Tools

1. **list_systems()**
   - Lists all configured systems
   - No parameters
   - Returns: System list with status

2. **perform_access_review(system_name, analysis_type, include_recommendations)**
   - Performs full access review
   - Parameters:
     - `system_name`: "netsuite" | "okta" | "salesforce"
     - `analysis_type`: "sod_violations" | "excessive_permissions" | "inactive_users" | "all"
     - `include_recommendations`: boolean (default: true)
   - Returns: Violation summary with recommendations

3. **get_user_violations(system_name, user_identifier, include_ai_analysis)**
   - Gets violations for specific user
   - Parameters:
     - `system_name`: System identifier
     - `user_identifier`: Email or user ID
     - `include_ai_analysis`: boolean (default: true)
   - Returns: User violations with AI analysis

4. **remediate_violation(violation_id, action, notes)**
   - Creates remediation plan
   - Parameters:
     - `violation_id`: UUID
     - `action`: "remove_role" | "request_approval" | "create_ticket" | "notify_manager"
     - `notes`: String (optional)
   - Returns: Remediation status and ticket info

5. **schedule_review(system_name, frequency, day_of_week, time, timezone)**
   - Schedules recurring review
   - Parameters:
     - `system_name`: System identifier
     - `frequency`: "daily" | "weekly" | "monthly"
     - `day_of_week`: "monday" through "friday" (for weekly)
     - `time`: HH:MM format (24-hour)
     - `timezone`: IANA timezone (default: "America/Los_Angeles")
   - Returns: Schedule confirmation

6. **get_violation_stats(systems, time_range)**
   - Gets aggregate statistics
   - Parameters:
     - `systems`: Array of system names (empty = all)
     - `time_range`: "today" | "week" | "month" | "quarter" | "year"
   - Returns: Aggregated violation statistics

---

## Testing

### Manual Testing with curl

```bash
# List tools
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "params": {},
    "id": 1
  }'

# Perform access review
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "perform_access_review",
      "arguments": {
        "system_name": "netsuite",
        "analysis_type": "sod_violations"
      }
    },
    "id": 2
  }'
```

### Testing with Claude UI

1. Configure Claude Desktop to connect to MCP server
2. Open Claude and type natural language commands
3. Verify responses match expected format
4. Test error scenarios

---

## NetSuite Setup

### 1. Create RESTlet Script

1. Navigate to: **Customization > Scripting > Scripts > New**
2. Upload the RESTlet script (see MCP_INTEGRATION_SPEC.md)
3. Create Script Deployment
4. Note the deployment URL

### 2. Create Integration Record

1. Navigate to: **Setup > Integration > Manage Integrations > New**
2. Name: "Compliance System MCP"
3. Enable TBA (Token-Based Authentication)
4. Note Consumer Key/Secret

### 3. Create Access Token

1. Navigate to: **Setup > Users/Roles > Access Tokens > New**
2. Application: "Compliance System MCP"
3. User: Service account with appropriate permissions
4. Note Token ID/Secret

### 4. Test Connection

```bash
# Set environment variables
export NETSUITE_ACCOUNT_ID=your_account
export NETSUITE_CONSUMER_KEY=your_key
export NETSUITE_CONSUMER_SECRET=your_secret
export NETSUITE_TOKEN_ID=your_token_id
export NETSUITE_TOKEN_SECRET=your_token_secret
export NETSUITE_RESTLET_URL=https://...

# Test with Python
python3 -c "
from connectors.netsuite_connector import NetSuiteConnector
import asyncio

async def test():
    connector = NetSuiteConnector()
    result = await connector.test_connection()
    print(f'Connection: {\"success\" if result else \"failed\"}')

asyncio.run(test())
"
```

---

## Troubleshooting

### MCP Server Won't Start

**Check**:
- Port 8080 not already in use: `lsof -i :8080`
- All dependencies installed: `pip3 list`
- Environment variables set: `env | grep NETSUITE`

**Fix**:
```bash
# Kill existing process
lsof -ti:8080 | xargs kill -9

# Reinstall dependencies
pip3 install -r requirements.txt

# Check config
python3 -c "import os; print(os.getenv('NETSUITE_ACCOUNT_ID'))"
```

### NetSuite Connection Fails

**Check**:
- OAuth credentials valid
- RESTlet deployed and accessible
- Token not expired
- Network connectivity

**Fix**:
```bash
# Test RESTlet with curl
curl -X GET "https://your_account.restlets.api.netsuite.com/..." \
  -H "Authorization: OAuth ..."

# Regenerate token if expired
# (see NetSuite Setup section)
```

### Claude UI Not Connecting

**Check**:
- MCP server running and accessible
- Claude UI configured with correct URL
- Authentication token valid
- Network connectivity

**Fix**:
- Check MCP server logs: `tail -f logs/mcp_server.log`
- Verify health endpoint: `curl http://localhost:8080/health`
- Reconfigure Claude UI with correct endpoint

---

## Next Steps

1. **Review Technical Specification**
   - Read `docs/MCP_INTEGRATION_SPEC.md` in full
   - Ask questions, provide feedback
   - Approve to proceed

2. **Set Up NetSuite**
   - Deploy RESTlet to sandbox
   - Create integration credentials
   - Test connection

3. **Begin Implementation**
   - Start with Phase 1: MCP Server Foundation
   - Implement basic tool registry
   - Test with mock data

4. **Iterate**
   - Build tools incrementally
   - Test each tool thoroughly
   - Add features based on user feedback

---

## Resources

- **Full Technical Spec**: `docs/MCP_INTEGRATION_SPEC.md`
- **MCP Protocol**: https://modelcontextprotocol.io/
- **NetSuite RESTlet Guide**: https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_4387799690.html
- **Existing Project Docs**: `TECHNICAL_SPECIFICATION_V3.md`

---

## Support

For questions or issues:
1. Check this guide first
2. Review full technical specification
3. Check existing project documentation
4. Ask in team chat

---

**Document Version**: 1.0.0
**Last Updated**: 2026-02-12
**Author**: Prabal Saha + Claude (Sonnet 4.5)
**Branch**: `feature/mcp-integration`
