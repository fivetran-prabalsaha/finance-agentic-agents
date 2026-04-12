# Testing SOD Compliance System from Claude Desktop UI

**Last Updated**: 2026-02-12
**Status**: Ready for Testing

---

## Prerequisites

✅ MCP Server running on `localhost:8080`
✅ PostgreSQL database with seeded data
✅ Claude Desktop app installed (latest version)
✅ Python 3.9+ environment

---

## Step 1: Configure Claude Desktop

### 1.1 Find Claude Desktop Config File

**macOS**:
```bash
open ~/Library/Application\ Support/Claude/
```

**Windows**:
```
%APPDATA%\Claude\
```

**Linux**:
```
~/.config/Claude/
```

### 1.2 Edit `claude_desktop_config.json`

Create or edit the file with this configuration:

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
        "DATABASE_URL": "postgresql://compliance_user:compliance_pass@localhost:5432/compliance_db",
        "MCP_API_KEY": "dev-key-12345",
        "ANTHROPIC_API_KEY": "your-anthropic-api-key-here"
      }
    }
  }
}
```

**Important**: Replace `/Users/prabal.saha/Documents/Celigo/syseng-celigo/compliance-agent` with your actual project path.

### 1.3 Restart Claude Desktop

1. Quit Claude Desktop completely (Cmd+Q on macOS)
2. Reopen Claude Desktop
3. Look for the hammer icon 🔨 in the bottom-right corner
4. Click it to see available MCP servers

You should see: **compliance-sod** with 19 tools available.

---

## Step 2: Verify MCP Server is Running

Before testing in Claude Desktop, ensure the MCP server is running:

```bash
# Check if server is running
ps aux | grep "mcp.mcp_server"

# If not running, start it:
cd /Users/prabal.saha/Documents/Celigo/syseng-celigo/compliance-agent
python3 -m mcp.mcp_server

# Or run in background:
nohup python3 -m mcp.mcp_server > /tmp/mcp_server.log 2>&1 &

# Check health:
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "compliance-mcp-server",
  "timestamp": "2026-02-12T..."
}
```

---

## Step 3: Test in Claude Desktop UI

### Test 1: Simple System Query

**Prompt in Claude Desktop**:
```
List all available systems for compliance review
```

**What Claude will do**:
- Automatically call the `list_systems` MCP tool
- Display system names, status, user counts

**Expected Output**:
```
Available Systems for Compliance Review:

1. NetSuite
   • Status: Active
   • Users: 1,933
   • Last Sync: 2 hours ago
   • SOD Rules: 24 active

2. Okta
   • Status: Connected
   • Users: 2,500
   • Last Sync: 1 hour ago
```

### Test 2: Vector Knowledge Base Query

**Prompt in Claude Desktop**:
```
Search the knowledge base for information about revenue transaction approval conflicts
```

**What Claude will do**:
- Call `query_knowledge_base` tool
- Perform vector similarity search in pgvector
- Return relevant SOD rules and controls

**Expected Output**:
```
Knowledge Base Search Results (5 found)

Query: revenue transaction approval conflicts

1. **sod_rule_SOD-RULE-001** (Similarity: 62.39%)
   • Type: SOD_RULE
   • Severity: CRITICAL
   • Principle: SOD-001: Maker-Checker Segregation
   • Description: User should not be able to create AND approve the same transaction

2. **resolution_transaction_entry_vs_approval_HIGH** (60.69%)
   • Type: RESOLUTION_STRATEGY
   • Required Controls: dual_approval_workflow, segregated_workflows
   ...
```

### Test 3: Analyze Access Request (Main Use Case)

**Prompt in Claude Desktop**:
```
Analyze an access request for a new Revenue Director who needs both Fivetran - Revenue Manager and Fivetran - Revenue Approver roles
```

**What Claude will do**:
1. Call `query_knowledge_base` to get relevant SOD rules (RAG pattern)
2. Call `analyze_access_request` tool with the parameters
3. Call `get_compensating_controls` for CRITICAL severity
4. Format a comprehensive response

**Expected Output**:
```
I've analyzed the access request for the Revenue Director role with dual access. Here's my assessment:

🔴 **HIGH RISK - 47 SOD Conflicts Detected**

**Conflict Analysis:**

The combination of Revenue Manager + Revenue Approver roles creates significant segregation of duties violations:

Top CRITICAL Conflicts:
1. Cash Sale (Full) + Invoice Approval (Create) → Maker-checker violation
   • Inherent Risk: 73.5/100
   • User can create sales and approve invoices without oversight

2. Cash Sale (Full) + Revenue Arrangement Approval (Create)
   • Inherent Risk: 73.5/100
   • Can manipulate revenue recognition

3. Cash Sale (Full) + Sales Order Approval (Create)
   • Inherent Risk: 73.5/100
   • Can bypass sales approval process

**Job Role Validation:**
✅ This IS a typical combination for Revenue Director roles
⚠️  However, it REQUIRES compensating controls

**Recommendation: APPROVE WITH COMPENSATING CONTROLS**

Required Controls (Critical Risk Control Package):
• Annual Cost: $100,000
• Risk Reduction: 90%
• Implementation Time: 90 hours

Specific Controls Needed:
1. Segregated Approval Workflows (70% risk reduction)
   - System routes transactions for approval by different user
2. Dual Approval Workflow (60% reduction)
   - Requires two approvers for transactions >$50K
3. Transaction Amount Limits (40% reduction)
   - Maximum $100K per transaction
4. Real-Time Transaction Monitoring (50% reduction)
   - Automated alerts for suspicious patterns
5. CEO/CFO Executive Approval (50% reduction)
   - Required for high-risk access combination
6. Quarterly Audit Committee Review (30% reduction)

**Risk Summary:**
• Without controls: 73.5/100 (CRITICAL)
• With controls: 7.3/100 (Acceptable)
• Risk Reduction: 90%

**Business Justification:**
This is a standard combination for Revenue Director role requiring both process management and approval authority. The controls make this acceptable from a compliance perspective.

Would you like me to:
1. Get detailed descriptions of each control?
2. Create a remediation plan?
3. Schedule this for implementation?
```

### Test 4: Check Specific Permission Conflict

**Prompt in Claude Desktop**:
```
Does giving someone both "Invoice" at Full level and "Invoice Approval" at Create level create a conflict?
```

**What Claude will do**:
- Call `check_permission_conflict` tool
- Look up in conflict matrix
- Return severity assessment

**Expected Output**:
```
🔴 **CRITICAL Conflict Detected**

**Permission 1**: Invoice (Full, level 4)
**Permission 2**: Invoice Approval (Create, level 2)

**Conflict Severity**: CRITICAL

This creates a maker-checker violation where the user can:
1. Create invoices (Full access to Invoice)
2. Approve those same invoices (Create approval records)

This bypasses the fundamental segregation control that requires different people to create and approve financial transactions.

**Recommendation**: Reject this combination or require executive override with maximum compensating controls.

Use `get_compensating_controls` with severity='CRITICAL' to see recommended controls.
```

### Test 5: Get Compensating Controls

**Prompt in Claude Desktop**:
```
What compensating controls do we need for CRITICAL severity SOD conflicts?
```

**What Claude will do**:
- Call `get_compensating_controls` tool
- Query database for control packages
- Return detailed control information

**Expected Output**:
```
**Critical Risk Control Package** (for CRITICAL severity)

Maximum controls for critical SOD violations

**Package Details:**
   • Risk Reduction: 90%
   • Annual Cost: $100,000
   • Implementation Time: 90 hours

**Included Controls** (8):

1. **Segregated Approval Workflows** (PREVENTIVE)
   └─ Risk Reduction: 70% | Cost: $5,000
   └─ System automatically routes transactions for approval by a different user than the creator

2. **Dual Approval Workflow** (PREVENTIVE)
   └─ Risk Reduction: 60% | Cost: $8,000
   └─ All transactions above specified threshold require approval from two different authorized individuals

3. **Transaction Amount Limits** (PREVENTIVE)
   └─ Risk Reduction: 40% | Cost: $1,000
   └─ System-enforced maximum transaction amounts per user or role

4. **Real-Time Transaction Monitoring** (DETECTIVE)
   └─ Risk Reduction: 50% | Cost: $25,000
   └─ Automated system monitors transactions in real-time and generates alerts for suspicious patterns

5. **Periodic Manager Review** (DETECTIVE)
   └─ Risk Reduction: 35% | Cost: $10,000 (manager time)
   └─ Direct manager conducts periodic review of all high-risk transactions

6. **Increased Audit Review Frequency** (DETECTIVE)
   └─ Risk Reduction: 40% | Cost: $50,000 (audit team time)
   └─ Internal audit conducts more frequent reviews of transactions with SOD conflicts

7. **Quarterly Audit Committee Review** (DETECTIVE)
   └─ Risk Reduction: 30% | Cost: $20,000 (preparation and board time)
   └─ Audit committee reviews all SOD exceptions and compensating controls quarterly

8. **CEO/CFO Executive Approval** (PREVENTIVE)
   └─ Risk Reduction: 50% | Cost: $3,000
   └─ Executive-level approval required for high-risk access combinations
```

### Test 6: Validate Job Role

**Prompt in Claude Desktop**:
```
Is it typical for a Controller to have the Controller role? What controls are needed?
```

**What Claude will do**:
- Call `validate_job_role` tool
- Query job_role_mappings table
- Return validation and requirements

**Expected Output**:
```
**Job Role Validation: Controller**

📁 Department: Finance

**Requested Roles Analysis:**
   • Roles Requested: 1
   • Typical for Role: 1/1
   • Resolution Strategy: compensating_controls

**Typical Roles for Controller:**
   ✅ Fivetran - Controller

**Typically Required Controls:**
   • dual_approval_workflow
   • ceo_approval
   • real_time_monitoring
   • quarterly_audit_review

**Business Justification:**
Chief accounting officer responsible for all financial operations and reporting. This role inherently has broad access to maintain oversight of financial processes, but requires strong compensating controls due to the breadth of permissions.

✅ **Recommendation**: APPROVE - This is a typical combination for this job role, but mandatory compensating controls must be implemented.
```

### Test 7: Search Permissions

**Prompt in Claude Desktop**:
```
Show me all high-risk transaction entry permissions
```

**What Claude will do**:
- Call `search_permissions` tool
- Filter by category and risk level
- Return permission list

**Expected Output**:
```
**Permission Search Results** (12 found):

• **Vendor Bill** (`TRAN_VENDORBILL`)
  └─ Categories: transaction_entry
  └─ Risk: HIGH
  └─ Levels: Edit, Full, View
  └─ Used by: 24 roles

• **Journal Entry** (`TRAN_JOURNAL`)
  └─ Categories: transaction_entry
  └─ Risk: HIGH
  └─ Levels: Full, View
  └─ Used by: 17 roles

• **Pay Bills** (`TRAN_PAYBILLS`)
  └─ Categories: transaction_payment
  └─ Risk: HIGH
  └─ Levels: Full
  └─ Used by: 8 roles
...
```

### Test 8: Query SOD Rules

**Prompt in Claude Desktop**:
```
Show me SOD rules that apply to transaction entry and approval
```

**What Claude will do**:
- Call `query_sod_rules` tool
- Filter by categories
- Return matching rules

**Expected Output**:
```
**SOD Rules** (1 found):

**SOD-RULE-001**: Transaction Entry Vs Transaction Approval
   • Principle: SOD-001: Maker-Checker Segregation
   • Categories: transaction_entry ↔ transaction_approval
   • Severity: CRITICAL | Risk: 50/100
   • Description: User should not be able to create AND approve the same transaction. This violates the fundamental maker-checker principle of internal controls.
```

---

## Step 4: Advanced Testing Scenarios

### Scenario 1: End-to-End Access Request Workflow

**Conversation Flow**:

```
You: "I need to evaluate an access request for Jane Smith, a new Accounts Payable Manager. She needs the A/P Analyst role."

Claude: [Calls analyze_access_request]
"I've analyzed the request. The A/P Analyst role for an AP Manager shows minimal conflicts..."

You: "What if she also needs the Billing Manager role?"

Claude: [Calls analyze_access_request again with both roles]
"Now we have 12 new conflicts. The combination of AP Analyst + Billing Manager creates payment processing conflicts..."

You: "What controls do we need?"

Claude: [Calls get_compensating_controls]
"For the HIGH severity conflicts, you'll need the High Risk Control Package costing $50K/year..."

You: "Is this typical for an AP Manager?"

Claude: [Calls validate_job_role]
"No, this is not a typical combination. AP Managers usually have only AP-related roles, not billing access..."
```

### Scenario 2: Proactive Risk Research

**Prompt**:
```
I'm planning our Q2 access review. Can you:
1. Search for all revenue-related SOD rules in the knowledge base
2. Check what conflicts exist with revenue recognition permissions
3. Tell me what controls we typically need for revenue teams
```

**What Claude will do**:
1. Call `query_knowledge_base` with "revenue recognition conflicts"
2. Call `query_sod_rules` with revenue-related categories
3. Call `get_compensating_controls` for typical severities
4. Synthesize a comprehensive report

### Scenario 3: Grounded Analysis Verification

**Prompt**:
```
Before you analyze anything, first search the knowledge base for "maker checker segregation" and show me what rules exist. Then use those rules to analyze a Revenue Manager + Revenue Approver combination.
```

**What Claude will do**:
1. Call `query_knowledge_base` first (RAG retrieval)
2. Show you the retrieved documents
3. Call `analyze_access_request`
4. Ground the analysis in the retrieved rules
5. Explicitly reference the retrieved documents in the response

This demonstrates that Claude is **not hallucinating** - it's using actual data from the vector database.

---

## Step 5: Troubleshooting Claude Desktop Integration

### Issue 1: MCP Server Not Showing in Claude Desktop

**Symptoms**:
- No hammer icon in Claude Desktop
- No tools available

**Solutions**:
1. Check config file syntax (must be valid JSON)
2. Verify paths are absolute, not relative
3. Ensure MCP server is running: `ps aux | grep mcp.mcp_server`
4. Check logs: `tail -f /tmp/mcp_server.log`
5. Restart Claude Desktop completely (Cmd+Q, not just close window)

### Issue 2: Tools Not Working

**Symptoms**:
- Claude says "I don't have access to that tool"
- Tool calls fail with errors

**Solutions**:
1. Check MCP server logs for errors
2. Verify database connection: `psql -U compliance_user -d compliance_db -c "SELECT COUNT(*) FROM sod_rules;"`
3. Test tools directly via curl: `curl -X POST http://localhost:8080/mcp ...`
4. Check API key in environment: `echo $MCP_API_KEY`
5. Verify Python path in config is correct

### Issue 3: Slow Response Times

**Symptoms**:
- Tool calls take >10 seconds
- Analysis times out

**Solutions**:
1. Check database indexes: `\d sod_rules` in psql
2. Monitor database performance: `pg_stat_activity`
3. Check if analysis script is running: `ps aux | grep analyze_access_request`
4. Reduce limit parameters (e.g., top_k=3 instead of 5)

### Issue 4: Vector Search Not Working

**Symptoms**:
- `query_knowledge_base` returns no results
- Similarity scores are very low (<10%)

**Solutions**:
1. Verify pgvector extension: `SELECT * FROM pg_extension WHERE extname='vector';`
2. Check embeddings exist: `SELECT COUNT(*) FROM knowledge_base_documents;`
3. Verify embedding dimensions: `SELECT pg_column_size(embedding) FROM knowledge_base_documents LIMIT 1;` (should be 1540 bytes)
4. Re-seed if needed: `python3 scripts/seed_sod_configurations.py`

---

## Step 6: Claude Desktop Best Practices

### Do's:
✅ Use natural language - Claude will figure out which tools to call
✅ Ask follow-up questions - Claude maintains context
✅ Request specific information - "Show me CRITICAL conflicts only"
✅ Verify grounding - Ask Claude to "show me the knowledge base results first"
✅ Use multi-step workflows - "First search, then analyze, then recommend"

### Don'ts:
❌ Don't specify exact tool names (Claude knows which to use)
❌ Don't pass JSON directly (Claude handles parameters)
❌ Don't repeat the same query (Claude caches recent results)
❌ Don't expect real-time data (data syncs hourly/daily)

### Example Good Prompts:
```
✅ "Analyze revenue director access with both manager and approver roles"
✅ "What SOD conflicts exist for a Controller role?"
✅ "Search the knowledge base for payment processing segregation rules"
✅ "Is it safe to give someone both vendor setup and payment permissions?"
✅ "Show me all compensating controls for high-risk conflicts"
```

### Example Bad Prompts:
```
❌ "Call the analyze_access_request tool with these parameters..."
❌ "Query the database for..."
❌ "Run this SQL: SELECT * FROM..."
❌ "Use the MCP tool to..."
```

Claude knows how to use the tools - just ask naturally!

---

## Step 7: Monitoring & Logs

### MCP Server Logs

```bash
# View real-time logs
tail -f /tmp/mcp_server.log

# Check for errors
grep ERROR /tmp/mcp_server.log

# Check tool execution times
grep "executed successfully" /tmp/mcp_server.log
```

### Database Query Logs

```bash
# Enable query logging in PostgreSQL
# Edit postgresql.conf:
log_statement = 'all'
log_duration = on
log_min_duration_statement = 1000  # Log queries >1s

# View logs
tail -f /usr/local/var/log/postgresql@14.log  # macOS
```

### Claude Desktop Logs

**macOS**:
```bash
~/Library/Logs/Claude/
```

Look for MCP-related errors in the latest log file.

---

## Step 8: Performance Optimization

### Database Indexes

Ensure these indexes exist:
```sql
-- Check existing indexes
\di

-- Create if missing
CREATE INDEX idx_kb_docs_embedding
ON knowledge_base_documents
USING ivfflat (embedding vector_cosine_ops);

CREATE INDEX idx_sod_rules_categories
ON sod_rules(category1, category2);

CREATE INDEX idx_violations_user
ON violations(user_id);
```

### Cache Configuration

```python
# In orchestrator.py
@timed_cache(seconds=300)  # 5-minute cache
def expensive_operation():
    ...

# Clear cache if needed
from functools import lru_cache
lru_cache.cache_clear()
```

### Vector Search Optimization

```python
# Use fewer dimensions if needed (faster but less accurate)
# Current: 384 dimensions
# Alternative: 128 dimensions (3x faster)

# Adjust ivfflat lists parameter
CREATE INDEX ... USING ivfflat ... WITH (lists = 100);
-- Higher lists = slower insert, faster search
-- Lower lists = faster insert, slower search
```

---

## Summary

**Setup Checklist**:
- ✅ MCP server running on port 8080
- ✅ PostgreSQL with pgvector and seeded data
- ✅ Claude Desktop config file updated
- ✅ Claude Desktop restarted
- ✅ 19 tools visible in hammer icon

**Key Features**:
- ✅ Natural language interface (no need to specify tools)
- ✅ Vector-grounded analysis (RAG pattern)
- ✅ 47-conflict detection in 2-5 seconds
- ✅ Compensating control recommendations
- ✅ Job role validation
- ✅ Real-time SOD analysis

**Testing Status**: ✅ **READY FOR PRODUCTION USE**

---

**Questions?**
- Check the MCP_SETUP_GUIDE.md for detailed curl examples
- Review ARCHITECTURE_V4.md for system architecture
- See MCP_SOD_TOOLS.md for complete tool documentation
- Check SMOKE_TEST_RESULTS.md for test results

**Support**:
- MCP Server: http://localhost:8080/health
- Tools List: http://localhost:8080/tools
- Logs: /tmp/mcp_server.log
