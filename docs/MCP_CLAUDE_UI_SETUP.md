# Connecting Claude UI to MCP Server

**Version**: 1.0.0
**Date**: 2026-02-12
**Status**: Setup Guide

---

## Overview

This guide shows you how to connect Claude Desktop (or Claude API) to your local MCP server so you can interact with the compliance system using natural language.

---

## Prerequisites

✅ MCP server running on `http://localhost:8080`
✅ All tests passing (8/8)
✅ Claude Desktop installed OR Claude API access

---

## Method 1: Claude Desktop (Recommended for Local Testing)

### Step 1: Install Claude Desktop

If you haven't already:

**macOS**:
```bash
# Download from Anthropic
open https://claude.ai/download

# Or via Homebrew
brew install --cask claude
```

**Verify Installation**:
```bash
# Check if Claude is installed
ls -la "/Applications/Claude.app"
```

### Step 2: Configure MCP Server

Claude Desktop uses a configuration file to connect to MCP servers.

**Configuration File Location**:
```bash
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Create/Edit the configuration**:

```bash
# Create directory if it doesn't exist
mkdir -p ~/Library/Application\ Support/Claude

# Create configuration file
cat > ~/Library/Application\ Support/Claude/claude_desktop_config.json << 'EOF'
{
  "mcpServers": {
    "compliance-system": {
      "command": "python3",
      "args": [
        "/Users/prabal.saha/Documents/Celigo/syseng-celigo/compliance-agent/run_mcp_server.py"
      ],
      "env": {
        "MCP_SERVER_HOST": "127.0.0.1",
        "MCP_SERVER_PORT": "8080"
      }
    }
  }
}
EOF
```

**Alternative: Manual Configuration**:

Create `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "compliance-system": {
      "command": "python3",
      "args": [
        "/Users/prabal.saha/Documents/Celigo/syseng-celigo/compliance-agent/run_mcp_server.py"
      ],
      "env": {
        "MCP_SERVER_HOST": "127.0.0.1",
        "MCP_SERVER_PORT": "8080",
        "DATABASE_URL": "postgresql://localhost/compliance_db",
        "ANTHROPIC_API_KEY": "your_key_here",
        "NETSUITE_CONSUMER_KEY": "your_key",
        "NETSUITE_CONSUMER_SECRET": "your_secret",
        "NETSUITE_TOKEN_ID": "your_token",
        "NETSUITE_TOKEN_SECRET": "your_secret",
        "NETSUITE_REALM": "your_realm",
        "NETSUITE_RESTLET_URL": "your_url",
        "REDIS_URL": "redis://localhost:6379/0"
      }
    }
  }
}
```

**Note**: If you already have a `.env` file, you can omit the `env` section since `run_mcp_server.py` loads from `.env`.

### Step 3: Restart Claude Desktop

```bash
# Quit Claude completely
killall Claude 2>/dev/null || true

# Relaunch Claude
open -a Claude
```

### Step 4: Verify Connection

1. Open Claude Desktop
2. Start a new conversation
3. Claude should show available tools/capabilities
4. Look for "compliance-system" or the tool names in the UI

### Step 5: Test with Natural Language

Try these commands:

**Example 1: List Systems**
```
You: What systems can you review for compliance?

Claude: [Should invoke list_systems tool and show NetSuite]
```

**Example 2: Get Statistics**
```
You: Show me violation statistics for this month

Claude: [Should invoke get_violation_stats and show results]
```

**Example 3: Perform Review**
```
You: Perform a user access review of NetSuite

Claude: [Should invoke perform_access_review]
```

---

## Method 2: Claude API with MCP (Alternative)

If you're using the Claude API directly (not Claude Desktop):

### Step 1: Ensure Server is Running

```bash
# Start MCP server
python3 run_mcp_server.py

# Verify it's running
curl http://localhost:8080/health
```

### Step 2: Use MCP-Compatible Client

You'll need an MCP-compatible client. Here's a simple example:

```python
import anthropic
import requests
import json

# Initialize Claude client
client = anthropic.Anthropic(api_key="your_api_key")

# MCP server URL
MCP_URL = "http://localhost:8080/mcp"
API_KEY = "dev-key-12345"

# Step 1: Get available tools from MCP server
def get_mcp_tools():
    response = requests.post(
        MCP_URL,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": API_KEY
        },
        json={
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 1
        }
    )
    return response.json()["result"]["tools"]

# Step 2: Call MCP tool
def call_mcp_tool(tool_name, arguments):
    response = requests.post(
        MCP_URL,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": API_KEY
        },
        json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": 2
        }
    )
    result = response.json()
    return result["result"]["content"][0]["text"]

# Step 3: Chat with Claude using MCP tools
def chat_with_mcp(user_message):
    # Get available tools
    tools = get_mcp_tools()

    # Convert MCP tools to Claude format
    claude_tools = [{
        "name": tool["name"],
        "description": tool["description"],
        "input_schema": tool["inputSchema"]
    } for tool in tools]

    # Create message with tools
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        tools=claude_tools,
        messages=[{"role": "user", "content": user_message}]
    )

    # Check if Claude wants to use a tool
    if response.stop_reason == "tool_use":
        for block in response.content:
            if block.type == "tool_use":
                # Execute MCP tool
                tool_result = call_mcp_tool(
                    block.name,
                    block.input
                )

                # Send result back to Claude
                final_response = client.messages.create(
                    model="claude-sonnet-4-5-20250929",
                    max_tokens=4096,
                    tools=claude_tools,
                    messages=[
                        {"role": "user", "content": user_message},
                        {"role": "assistant", "content": response.content},
                        {
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": tool_result
                            }]
                        }
                    ]
                )

                return final_response.content[0].text

    return response.content[0].text

# Test it
if __name__ == "__main__":
    print(chat_with_mcp("What systems can you review?"))
```

---

## Method 3: Direct HTTP Testing (Development/Debugging)

For quick testing without Claude UI:

### Using curl

```bash
# List systems
curl -s -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-12345" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "list_systems",
      "arguments": {}
    },
    "id": 1
  }' | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['result']['content'][0]['text'])"

# Get violation stats
curl -s -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-12345" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "get_violation_stats",
      "arguments": {"time_range": "month"}
    },
    "id": 2
  }' | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['result']['content'][0]['text'])"
```

### Using Python

```python
import requests
import json

MCP_URL = "http://localhost:8080/mcp"
API_KEY = "dev-key-12345"

def call_tool(tool_name, arguments=None):
    response = requests.post(
        MCP_URL,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": API_KEY
        },
        json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {}
            },
            "id": 1
        }
    )
    result = response.json()
    return result["result"]["content"][0]["text"]

# Test
print(call_tool("list_systems"))
print(call_tool("get_violation_stats", {"time_range": "month"}))
```

---

## Troubleshooting

### Issue: Claude Desktop doesn't show MCP tools

**Check**:
1. Configuration file exists and is valid JSON
2. Server is running: `curl http://localhost:8080/health`
3. Restart Claude Desktop completely

**Fix**:
```bash
# Validate JSON
python3 -c "import json; print(json.load(open('~/Library/Application Support/Claude/claude_desktop_config.json')))"

# Check server
curl http://localhost:8080/tools

# Restart Claude
killall Claude && sleep 2 && open -a Claude
```

### Issue: "Connection refused"

**Check**:
1. Server is running: `ps aux | grep run_mcp_server`
2. Port 8080 is not blocked
3. Firewall allows localhost connections

**Fix**:
```bash
# Start server
python3 run_mcp_server.py &

# Check port
lsof -i :8080

# Test connection
curl http://localhost:8080/health
```

### Issue: "Authentication failed"

**Check**:
1. API key matches in server and config
2. Default key is: `dev-key-12345`

**Fix**:
```bash
# Update API key in config
export MCP_API_KEY="your-custom-key"

# Or edit config file
vim ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### Issue: Tools execute but return errors

**Check**:
1. Environment variables loaded: `python3 -c "import os; print(os.getenv('DATABASE_URL'))"`
2. Database is running: `pg_isready`
3. Redis is running: `redis-cli ping`

**Fix**:
```bash
# Check .env file
cat .env | grep -v "^#"

# Start dependencies
brew services start postgresql
brew services start redis

# Restart server
pkill -f run_mcp_server && python3 run_mcp_server.py &
```

---

## Example Conversations

### Example 1: Quick Check

```
You: What compliance systems do you have access to?

Claude: I can access the following systems for compliance review:

✅ **NETSUITE** (ERP)
   • Status: connected
   • Users: 1,933
   • Last reviewed: Never

Would you like me to perform an access review?
```

### Example 2: Detailed Analysis

```
You: Perform a complete access review of NetSuite and show me the high-risk violations

Claude: I'll perform a comprehensive access review of NetSuite now...

[Executing: perform_access_review for NetSuite]

Access Review Complete - NETSUITE

📊 Summary:
   • Users Analyzed: 142
   • Total Violations: 47
   • High-Risk: 12 🔴
   • Medium-Risk: 20 🟡
   • Low-Risk: 15 🟢

👥 Top Violators:
1. John Smith (john.smith@company.com)
   └─ 5 violations (3 high, 2 medium, 0 low)
2. Jane Doe (jane.doe@company.com)
   └─ 4 violations (3 high, 1 medium, 0 low)

Would you like me to show details for any specific user?
```

### Example 3: Follow-up Investigation

```
You: Show me details for John Smith

Claude: [Executing: get_user_violations for john.smith@company.com]

John Smith - Violation Report

📧 Email: john.smith@company.com
🏢 System: netsuite
🎭 Roles (3): Administrator, Finance Manager, Approver
⚠️  Total Violations: 5

Violations:

1. 🔴 HIGH: Administrator + Finance Manager
   • Description: Can create vendors AND approve payments
   • Risk: Fraudulent payment creation
   • Status: Active
   • Violation ID: abc123-def456

[... more violations ...]

🤖 AI Risk Analysis:
This user has extensive financial and administrative access...

Would you like me to create a remediation plan?
```

### Example 4: Taking Action

```
You: Yes, create a remediation ticket for the first violation

Claude: [Executing: remediate_violation]

✅ Remediation Initiated

📋 Ticket ID: REM-ABC123
👤 User: John Smith (john.smith@company.com)
⚠️  Violation ID: abc123-def456
🔧 Action: create_ticket

📌 Next Steps:
   • Create ServiceNow ticket with violation details
   • Assign to IT Security team
   • Set priority based on risk level
   • Track remediation progress

Ticket created successfully. Would you like me to schedule a follow-up review?
```

---

## Advanced: MCP Server as a Service

To run the MCP server as a background service:

### Using launchd (macOS)

Create `~/Library/LaunchAgents/com.compliance.mcp.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.compliance.mcp</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/Users/prabal.saha/Documents/Celigo/syseng-celigo/compliance-agent/run_mcp_server.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/mcp_server.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/mcp_server.error.log</string>
    <key>WorkingDirectory</key>
    <string>/Users/prabal.saha/Documents/Celigo/syseng-celigo/compliance-agent</string>
</dict>
</plist>
```

**Load the service**:
```bash
launchctl load ~/Library/LaunchAgents/com.compliance.mcp.plist
launchctl start com.compliance.mcp
```

**Check status**:
```bash
launchctl list | grep compliance
tail -f /tmp/mcp_server.log
```

---

## Security Notes

### For Production

1. **Change API Key**:
   ```bash
   # Generate secure key
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"

   # Set in .env
   echo "MCP_API_KEY=your_secure_key" >> .env
   ```

2. **Enable HTTPS**:
   - Use nginx or caddy as reverse proxy
   - Add SSL certificates
   - Update MCP_SERVER_HOST to use https://

3. **Restrict Access**:
   - Use firewall to limit connections
   - Consider VPN requirement
   - Add rate limiting

4. **Authentication**:
   - Implement OAuth 2.0
   - Add user-specific API keys
   - Enable audit logging

---

## Next Steps

1. ✅ **Start Server**: `python3 run_mcp_server.py`
2. ✅ **Configure Claude Desktop**: Edit config file
3. ✅ **Restart Claude**: Quit and reopen
4. ✅ **Test**: Try "What systems can you review?"
5. ✅ **Use**: Start natural language compliance reviews!

---

## Summary

You now have three ways to use the MCP server:

1. **Claude Desktop** (Recommended) - Natural language interface
2. **Claude API** - Programmatic access
3. **Direct HTTP** - Testing and debugging

The MCP server bridges Claude's conversational AI with your compliance system, enabling natural language commands like:
- "Show me all SOD violations"
- "Perform a user access review"
- "Create a remediation plan"

**Ready to start!** 🚀

---

**Document Version**: 1.0.0
**Author**: Prabal Saha + Claude (Sonnet 4.5)
**Date**: 2026-02-12
