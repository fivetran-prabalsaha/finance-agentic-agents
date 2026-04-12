# MCP Server Setup Guide

**Quick start guide for testing the SOD Analysis MCP tools**

---

## Prerequisites

✅ Python 3.9+ installed
✅ PostgreSQL running with seeded data
✅ All dependencies installed (`pip install -r requirements.txt`)
✅ Environment variables configured (`.env` file)

---

## Quick Start

### 1. Start the MCP Server

```bash
cd /Users/prabal.saha/Documents/Celigo/syseng-celigo/compliance-agent

# Start the server
python3 -m mcp.mcp_server
```

**Expected output**:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     ============================================================
INFO:     Starting Compliance MCP Server
INFO:     ============================================================
INFO:     Available tools: 18
INFO:       • list_systems
INFO:       • perform_access_review
INFO:       • ...
INFO:       • analyze_access_request  ← NEW
INFO:       • query_sod_rules  ← NEW
INFO:       • get_compensating_controls  ← NEW
INFO:       • validate_job_role  ← NEW
INFO:       • check_permission_conflict  ← NEW
INFO:       • get_permission_categories  ← NEW
INFO:       • search_permissions  ← NEW
INFO:     ============================================================
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080
```

### 2. Test the Server

Open another terminal and test the health endpoint:

```bash
curl http://localhost:8080/health
```

**Expected**:
```json
{
  "status": "healthy",
  "service": "compliance-mcp-server",
  "timestamp": "2026-02-12T..."
}
```

### 3. List Available Tools

```bash
curl http://localhost:8080/tools
```

**Expected**: JSON list of all 18 tools including the 7 new SOD analysis tools.

---

## Testing SOD Analysis Tools

### Test 1: Analyze Access Request

```bash
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-12345" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "analyze_access_request",
      "arguments": {
        "job_title": "Revenue Director",
        "requested_roles": [
          "Fivetran - Revenue Manager",
          "Fivetran - Revenue Approver"
        ]
      }
    },
    "id": 1
  }'
```

### Test 2: Check Permission Conflict

```bash
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-12345" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "check_permission_conflict",
      "arguments": {
        "permission1_name": "Invoice",
        "permission1_level": "Full",
        "permission2_name": "Invoice Approval",
        "permission2_level": "Full"
      }
    },
    "id": 2
  }'
```

### Test 3: Get Compensating Controls

```bash
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-12345" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "get_compensating_controls",
      "arguments": {
        "severity": "CRITICAL",
        "include_cost": true
      }
    },
    "id": 3
  }'
```

### Test 4: Validate Job Role

```bash
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key": dev-key-12345" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "validate_job_role",
      "arguments": {
        "job_title": "Controller",
        "requested_roles": ["Fivetran - Controller"]
      }
    },
    "id": 4
  }'
```

### Test 5: Search Permissions

```bash
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-12345" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "search_permissions",
      "arguments": {
        "search_term": "invoice",
        "category": "transaction_entry",
        "limit": 10
      }
    },
    "id": 5
  }'
```

---

## Configure Claude Desktop (Optional)

To use these tools in Claude Desktop app:

### 1. Find your Claude Desktop config

```bash
# macOS
open ~/Library/Application\ Support/Claude/
```

### 2. Edit `claude_desktop_config.json`

```json
{
  "mcpServers": {
    "compliance-sod": {
      "command": "python3",
      "args": [
        "-m",
        "mcp.mcp_server"
      ],
      "cwd": "/Users/prabal.saha/Documents/Celigo/syseng-celigo/compliance-agent",
      "env": {
        "PYTHONPATH": "/Users/prabal.saha/Documents/Celigo/syseng-celigo/compliance-agent",
        "DATABASE_URL": "postgresql://compliance_user:compliance_pass@localhost:5432/compliance_db"
      }
    }
  }
}
```

### 3. Restart Claude Desktop

After saving the config, restart Claude Desktop. You should see the MCP tools available in the UI.

### 4. Test in Claude Desktop

Try these prompts:

**Example 1**:
```
Analyze an access request for a Revenue Director requesting both Revenue Manager and Revenue Approver roles
```

**Example 2**:
```
Check if Invoice at Full level conflicts with Invoice Approval at Full level
```

**Example 3**:
```
What compensating controls are recommended for CRITICAL severity conflicts?
```

**Example 4**:
```
Is it typical for a Controller to have the Controller role?
```

**Example 5**:
```
Search for all transaction entry permissions that are high risk
```

---

## Troubleshooting

### Issue: Server won't start

**Error**: `ModuleNotFoundError: No module named 'fastapi'`

**Solution**:
```bash
pip install fastapi uvicorn
```

### Issue: Database connection failed

**Error**: `could not connect to server: Connection refused`

**Solution**:
```bash
# Check if PostgreSQL is running
pg_isready

# If not running, start it
brew services start postgresql@14  # macOS
# or
sudo systemctl start postgresql  # Linux
```

### Issue: Permission mapping not found

**Error**: `❌ Permission mapping file not found`

**Solution**:
```bash
# Generate the permission mapping
python3 scripts/analyze_and_categorize_permissions.py
```

### Issue: Analysis script fails

**Error**: `scripts/analyze_access_request_with_levels.py not found`

**Solution**: Ensure you're running from the project root directory:
```bash
cd /Users/prabal.saha/Documents/Celigo/syseng-celigo/compliance-agent
python3 -m mcp.mcp_server
```

---

## Environment Variables

Make sure these are set in your `.env` file:

```bash
# Database
DATABASE_URL=postgresql://compliance_user:compliance_pass@localhost:5432/compliance_db

# MCP Server
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8080
MCP_API_KEY=dev-key-12345

# NetSuite (if using data collection)
NETSUITE_FIVETRAN_RESTLET_URL=https://...
NETSUITE_ACCOUNT_ID=...
NETSUITE_CONSUMER_KEY=...
NETSUITE_CONSUMER_SECRET=...
NETSUITE_TOKEN_ID=...
NETSUITE_TOKEN_SECRET=...
```

---

## Tool Examples in Natural Language

Once the MCP server is running and configured in Claude Desktop, you can use natural language:

### Example Conversations

**User**: "Analyze access for an Accounts Payable Manager requesting the A/P Analyst role"

**Claude**: [Uses `analyze_access_request` tool automatically]
"I've analyzed the access request. The A/P Analyst role for an Accounts Payable Manager shows no conflicts..."

---

**User**: "Does giving someone both vendor setup and payment permissions create a conflict?"

**Claude**: [Uses `check_permission_conflict` tool]
"Yes, that's a CRITICAL conflict. A user with Vendor Setup (Full) and Pay Bills (Full) can create a fake vendor and authorize payments to them..."

---

**User**: "What controls do we need for a CRITICAL conflict?"

**Claude**: [Uses `get_compensating_controls` tool]
"For CRITICAL severity, the recommended control package includes:
- CEO/CFO Executive Approval (50% risk reduction)
- Dual Approval Workflow (60% risk reduction)
- Segregated Workflows (70% risk reduction)
..."

---

## Next Steps

1. ✅ Start the MCP server
2. ✅ Test with curl commands
3. ✅ Configure Claude Desktop
4. ✅ Try natural language queries
5. 📖 Review [MCP_SOD_TOOLS.md](docs/MCP_SOD_TOOLS.md) for detailed tool documentation

---

**Status**: ✅ Ready to test!

The MCP server is now exposing 7 new SOD analysis tools. Start the server and begin testing use cases.
