# MCP Tools for SOD Analysis

**Date**: 2026-02-12
**Status**: ✅ Ready to Use

---

## Overview

The MCP server now exposes 7 new tools for SOD (Segregation of Duties) analysis that leverage the level-based conflict detection system and permission categorization.

These tools allow you to:
- Analyze access requests with level-based SOD detection
- Query SOD rules and compensating controls from the database
- Validate job role combinations
- Check permission conflicts
- Search and explore NetSuite permissions

---

## Available Tools

### 1. `analyze_access_request`

Analyze an access request for SOD conflicts using level-based analysis with compensating controls.

**Parameters**:
- `job_title` (required): Job title of the user (e.g., "Revenue Director", "Controller")
- `requested_roles` (required): Array of NetSuite role names
- `user_email` (optional): Email address of the user

**Example**:
```json
{
  "job_title": "Revenue Director",
  "requested_roles": [
    "Fivetran - Revenue Manager",
    "Fivetran - Revenue Approver"
  ]
}
```

**Returns**:
- Conflicts found with severity levels
- Job role validation results
- Recommended compensating controls
- Inherent and residual risk scores
- Overall recommendation (APPROVE/CONTROLS/REJECT)

---

### 2. `query_sod_rules`

Query SOD rules from the database with optional filters.

**Parameters**:
- `category1` (optional): First permission category
- `category2` (optional): Second permission category
- `severity` (optional): Filter by severity (CRITICAL, HIGH, MEDIUM, LOW)
- `limit` (optional): Maximum results (default: 10)

**Example**:
```json
{
  "category1": "transaction_entry",
  "category2": "transaction_approval",
  "severity": "CRITICAL"
}
```

**Returns**:
- List of SOD rules matching criteria
- Rule principles and descriptions
- Category mappings
- Base risk scores

---

### 3. `get_compensating_controls`

Get recommended compensating controls for a specific severity level.

**Parameters**:
- `severity` (required): Severity level (CRITICAL, HIGH, MEDIUM, LOW)
- `include_cost` (optional): Include cost estimates (default: true)

**Example**:
```json
{
  "severity": "CRITICAL",
  "include_cost": true
}
```

**Returns**:
- Control package details
- List of included controls with descriptions
- Risk reduction percentages
- Annual costs and implementation time

---

### 4. `validate_job_role`

Validate if a role combination is typical for a specific job title.

**Parameters**:
- `job_title` (required): Job title to validate
- `requested_roles` (required): Array of NetSuite roles

**Example**:
```json
{
  "job_title": "Controller",
  "requested_roles": ["Fivetran - Controller"]
}
```

**Returns**:
- Whether combination is typical for the role
- Typical roles for this job title
- Required compensating controls
- Business justification
- Recommendation (APPROVE/REVIEW)

---

### 5. `check_permission_conflict`

Check if two specific permissions conflict based on their levels.

**Parameters**:
- `permission1_name` (required): First permission name
- `permission1_level` (required): Level (None/View/Create/Edit/Full)
- `permission2_name` (required): Second permission name
- `permission2_level` (required): Level (None/View/Create/Edit/Full)

**Example**:
```json
{
  "permission1_name": "Invoice",
  "permission1_level": "Full",
  "permission2_name": "Invoice Approval",
  "permission2_level": "Full"
}
```

**Returns**:
- Conflict severity (OK/LOW/MED/HIGH/CRIT)
- Explanation of the conflict
- Recommended actions

---

### 6. `get_permission_categories`

Get all permission categories and their risk scores.

**Parameters**:
- `include_permissions` (optional): Include permissions list (default: false)

**Example**:
```json
{
  "include_permissions": false
}
```

**Returns**:
- List of all permission categories
- Base risk scores for each category
- Category descriptions

---

### 7. `search_permissions`

Search and filter NetSuite permissions by name, category, or risk level.

**Parameters**:
- `search_term` (optional): Search term for permission names
- `category` (optional): Filter by category
- `risk_level` (optional): Filter by risk (HIGH/MEDIUM/LOW/MINIMAL)
- `limit` (optional): Maximum results (default: 20)

**Example**:
```json
{
  "search_term": "invoice",
  "category": "transaction_entry",
  "risk_level": "HIGH"
}
```

**Returns**:
- List of matching permissions
- Permission categories and risk levels
- Permission levels granted (View/Create/Edit/Full)
- Usage statistics (how many roles have this permission)

---

## Use Cases

### Use Case 1: Analyze Revenue Director Access Request

**Scenario**: A new Revenue Director needs both management and approval authority.

**Tools to use**:
1. `analyze_access_request` - Analyze the complete request
2. `get_compensating_controls` - Get CRITICAL controls if needed
3. `validate_job_role` - Confirm this is typical for Revenue Director

**Example conversation**:
```
User: "Analyze access for Revenue Director requesting Revenue Manager and Revenue Approver roles"

Claude uses: analyze_access_request
{
  "job_title": "Revenue Director",
  "requested_roles": [
    "Fivetran - Revenue Manager",
    "Fivetran - Revenue Approver"
  ]
}

Result shows:
- 2 CRITICAL conflicts found
- Inherent risk: 97.5/100
- Recommended controls: Segregated workflows, dual approval, transaction limits
- Residual risk: 9.75/100 (with controls)
- Recommendation: APPROVE_WITH_COMPENSATING_CONTROLS
```

---

### Use Case 2: Investigate Controller Role

**Scenario**: Understand what conflicts exist within the Controller role itself.

**Tools to use**:
1. `analyze_access_request` - Analyze Controller role
2. `query_sod_rules` - See which rules apply to financial transactions
3. `get_compensating_controls` - Get HIGH/CRITICAL controls

**Example conversation**:
```
User: "What conflicts exist in the Controller role?"

Claude uses: analyze_access_request
{
  "job_title": "Controller",
  "requested_roles": ["Fivetran - Controller"]
}

Result shows:
- Multiple internal conflicts (Full access to entry, approval, payment)
- Inherent risk: 95/100
- Required: CEO approval + extensive controls
- Residual risk: 48/100 (with controls)
- Recommendation: APPROVE_WITH_EXTENSIVE_CONTROLS
```

---

### Use Case 3: Check Specific Permission Conflict

**Scenario**: Before granting permissions, check if they conflict.

**Tools to use**:
1. `check_permission_conflict` - Check specific permission pair
2. `get_compensating_controls` - Get controls if conflict exists

**Example conversation**:
```
User: "Does Invoice at Full conflict with Invoice Approval at Full?"

Claude uses: check_permission_conflict
{
  "permission1_name": "Invoice",
  "permission1_level": "Full",
  "permission2_name": "Invoice Approval",
  "permission2_level": "Full"
}

Result shows:
- Conflict Severity: CRITICAL 🔴
- Can create and approve own invoices (maker-checker violation)
- Recommendation: Reject or require executive override
```

---

### Use Case 4: Explore Transaction Permissions

**Scenario**: Understand what transaction entry permissions exist.

**Tools to use**:
1. `get_permission_categories` - See all categories
2. `search_permissions` - Find transaction permissions
3. `query_sod_rules` - See SOD rules for these categories

**Example conversation**:
```
User: "Show me all transaction entry permissions"

Claude uses: search_permissions
{
  "category": "transaction_entry",
  "limit": 20
}

Result shows:
- 93 transaction_entry permissions
- Invoice, Vendor Bill, Journal Entry, etc.
- Risk levels and usage statistics
```

---

### Use Case 5: Plan AP Manager Access

**Scenario**: Determine appropriate access for an Accounts Payable Manager.

**Tools to use**:
1. `validate_job_role` - Check typical roles for AP Manager
2. `analyze_access_request` - Analyze proposed combination
3. `get_compensating_controls` - Get required controls

**Example conversation**:
```
User: "What roles should an AP Manager have?"

Claude uses: validate_job_role
{
  "job_title": "Accounts Payable Manager",
  "requested_roles": ["Fivetran - A/P Analyst"]
}

Result shows:
- Single role is typical for AP Manager
- No conflicts with single role
- Recommendation: APPROVE without additional controls

Alternative:
If user requests AP Analyst + Billing Manager:
- Some conflicts exist (payment + billing oversight)
- Recommendation: Reduce Billing Manager to View level
- Or: Approve with transaction limits
```

---

## Integration with Claude Desktop

To use these tools in Claude Desktop:

1. **Start the MCP server**:
   ```bash
   cd /Users/prabal.saha/Documents/Celigo/syseng-celigo/compliance-agent
   python3 -m mcp.mcp_server
   ```

2. **Configure Claude Desktop** (in `~/Library/Application Support/Claude/claude_desktop_config.json`):
   ```json
   {
     "mcpServers": {
       "compliance": {
         "command": "python3",
         "args": [
           "-m",
           "mcp.mcp_server"
         ],
         "cwd": "/Users/prabal.saha/Documents/Celigo/syseng-celigo/compliance-agent",
         "env": {
           "PYTHONPATH": "/Users/prabal.saha/Documents/Celigo/syseng-celigo/compliance-agent"
         }
       }
     }
   }
   ```

3. **Use in conversation**:
   ```
   You: "Analyze access request for Revenue Director requesting Revenue Manager and Revenue Approver"

   Claude: [Uses analyze_access_request tool]
   Claude: Here's the analysis...
   ```

---

## Example Workflows

### Workflow 1: Complete Access Request Review

```
1. User requests: "Evaluate access for Jane Smith (Revenue Director) requesting Revenue Manager + Revenue Approver"

2. Claude uses: validate_job_role
   → Confirms this is typical for Revenue Director

3. Claude uses: analyze_access_request
   → Finds 2 CRITICAL conflicts
   → Inherent risk: 97.5/100

4. Claude uses: get_compensating_controls (severity=CRITICAL)
   → Shows Critical Risk Control Package
   → 90% risk reduction, $100K/year

5. Claude presents recommendation:
   "APPROVE with compensating controls:
    - Segregated workflows (can't approve own)
    - Dual approval for >$50K
    - Transaction limits ($100K max)
    - Real-time monitoring
    - Weekly CFO review
    - Residual risk: 9.75/100"
```

### Workflow 2: Permission Research

```
1. User asks: "What are the high-risk transaction permissions?"

2. Claude uses: search_permissions
   { "category": "transaction_entry", "risk_level": "HIGH" }
   → Lists high-risk transaction permissions

3. Claude uses: query_sod_rules
   { "category1": "transaction_entry", "severity": "CRITICAL" }
   → Shows which rules apply

4. Claude uses: get_permission_categories
   → Shows all categories and their base risks

5. Claude presents findings:
   "High-risk transaction permissions include:
    - Invoice (Full) - used by 18 roles
    - Vendor Bill (Full) - used by 11 roles
    - Journal Entry (Full) - used by 17 roles

    These conflict with approval permissions..."
```

---

## Tool Response Formats

### analyze_access_request
```
**Access Request Analysis: Revenue Director**

📋 **Requested Roles** (2):
   • Fivetran - Revenue Manager
   • Fivetran - Revenue Approver

**Overall Assessment:**
   • Conflicts Found: 2
   • Risk Level: 🔴 CRITICAL
   • Recommendation: **APPROVE_WITH_COMPENSATING_CONTROLS**

**Job Role Validation:**
   • Is Typical Combination: ✅ Yes
   • Requires Controls: ⚠️  Yes
   • Justification: Revenue Directors typically need...

**Detected Conflicts** (2):
1. 🔴 **CRIT** - SOD-001: Maker-Checker Segregation
   • Revenue Recognition (Full)
   • Approve Revenue Recognition (Full)
   • Inherent Risk: 97.5/100

**Recommended Controls:**
1. **REJECT_OR_EXECUTIVE_OVERRIDE**
   • Inherent Risk: 97.5/100
   • Residual Risk: 9.75/100
   • Risk Reduction: 90%
   • Package: Critical Risk Control Package
   • Annual Cost: $100,000
```

### check_permission_conflict
```
**Permission Conflict Analysis**

**Permission 1**: Invoice (Full, level 4)
**Permission 2**: Invoice Approval (Full, level 4)

**Conflict Severity**: 🔴 **CRIT**

🔴 Critical conflict - Reject or require executive override with maximum controls.

ℹ️  _Use `get_compensating_controls` with severity='CRIT' to see recommended controls._
```

---

## Error Handling

### Common Errors

1. **Analysis timeout**:
   ```
   ❌ **Analysis Timeout**
   The analysis took too long to complete.
   ```
   Solution: Try with fewer roles or simpler request

2. **Job role not found**:
   ```
   ❌ **Job Role Not Found**
   No mapping found for job title: XYZ
   ```
   Solution: Use `get_permission_categories` to see available job roles

3. **Permission mapping missing**:
   ```
   ❌ Permission mapping file not found.
   Run `analyze_and_categorize_permissions.py` first.
   ```
   Solution: Run the categorization script:
   ```bash
   python3 scripts/analyze_and_categorize_permissions.py
   ```

---

## Performance

- **analyze_access_request**: ~2-5 seconds (calls Python script)
- **query_sod_rules**: <100ms (direct DB query)
- **get_compensating_controls**: <100ms (direct DB query)
- **validate_job_role**: <100ms (direct DB query)
- **check_permission_conflict**: <50ms (matrix lookup)
- **search_permissions**: <200ms (JSON file read + filter)

---

## Next Steps

1. **Try the tools** in Claude Desktop
2. **Test use cases** from this document
3. **Provide feedback** on tool responses
4. **Request new tools** for additional SOD analysis needs

---

**Status**: ✅ **Tools are live and ready for use!**

Start the MCP server and try analyzing your first access request.
