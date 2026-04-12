# Fivetran Role Permission Analysis

**Purpose:** Extract Fivetran roles, analyze permission conflicts, and generate SOD rules
**Date:** 2026-02-12
**Status:** Ready for deployment

---

## Overview

This system provides a **role-centric approach** to SOD compliance analysis:

1. **Extract** all "Fivetran - XXX" roles and their permissions from NetSuite
2. **Analyze** permissions across roles to identify conflicts
3. **Generate** SOD rules based on actual permission conflicts
4. **Apply** rules to user access review

### Why Role-Centric?

**Traditional approach (user-centric):**
```
Users → Roles → Analyze conflicts
```
- ❌ Only analyzes roles assigned to users
- ❌ Misses unassigned roles
- ❌ Hard to establish baseline rules

**New approach (role-centric):**
```
Roles → Permissions → Identify conflicts → Generate rules → Apply to users
```
- ✅ Analyzes ALL Fivetran roles (even unassigned)
- ✅ Establishes permission-based SOD rules
- ✅ Clear foundation for compliance

---

## Architecture

### Components

```
┌──────────────────────────────────────────────────────────────┐
│                        NetSuite                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Fivetran Roles                                        │  │
│  │  • Fivetran - Controller                              │  │
│  │  • Fivetran - AP Clerk                                │  │
│  │  • Fivetran - Analyst                                 │  │
│  │  • Fivetran - Administrator                           │  │
│  └────────────────────────────────────────────────────────┘  │
│                           │                                   │
│                           ▼                                   │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Fivetran Roles RESTlet                               │  │
│  │  fivetran_roles_permissions_restlet.js                │  │
│  │  • Searches for "Fivetran -" roles                    │  │
│  │  • Queries RolePermissions table                      │  │
│  │  • Returns role + permission data                     │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                           │
                           │ JSON/HTTP
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                Python Analysis Script                         │
│  analyze_fivetran_permissions.py                             │
│                                                               │
│  Step 1: Fetch Roles                                         │
│  └─> Calls RESTlet, gets all Fivetran roles + permissions   │
│                                                               │
│  Step 2: Build Permission Matrix                             │
│  └─> Maps permissions to roles                              │
│                                                               │
│  Step 3: Analyze Conflicts                                   │
│  └─> Identifies SOD violations in role combinations         │
│                                                               │
│  Step 4: Generate SOD Rules                                  │
│  └─> Creates rule definitions                               │
│                                                               │
│  Step 5: Export Results                                      │
│  └─> JSON files + human-readable report                     │
└──────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    Output Files                               │
│  • fivetran_roles_TIMESTAMP.json                             │
│  • permission_matrix_TIMESTAMP.json                          │
│  • conflicts_TIMESTAMP.json                                  │
│  • sod_rules_fivetran_TIMESTAMP.json                         │
│  • analysis_report_TIMESTAMP.txt                             │
└──────────────────────────────────────────────────────────────┘
```

---

## Deployment Guide

> **⚠️ IMPORTANT**: Use the **SuiteQL version** of the RESTlet, not the record.load() version!
>
> **Why?** All Fivetran roles are standard NetSuite roles (not custom), and `record.load()` cannot access standard roles. The SuiteQL version queries the database tables directly, bypassing this limitation.
>
> **Details**: See [NETSUITE_PERMISSION_EXTRACTION_ISSUE.md](./NETSUITE_PERMISSION_EXTRACTION_ISSUE.md) for complete technical analysis.

### Step 1: Deploy NetSuite RESTlet (SuiteQL Version)

#### 1.1 Upload Script to NetSuite

1. Log into NetSuite
2. Go to **Customization > Scripting > Scripts > New**
3. Click **Upload File**
4. Select `netsuite_scripts/fivetran_roles_permissions_suiteql.js` ⚠️ **Use this SuiteQL version!**
5. Click **Create Script Record**

#### 1.2 Configure Script

- **Name:** Fivetran Roles & Permissions RESTlet
- **ID:** `customscript_fivetran_roles_perms`
- **Owner:** (Your user)
- **Status:** Testing (change to Released after testing)
- **Log Level:** Debug (change to Error in production)

#### 1.3 Deploy Script

1. Click **Deploy Script** tab
2. Create new deployment:
   - **Title:** Fivetran Roles Deployment
   - **ID:** `customdeploy_fivetran_roles_perms`
   - **Status:** Testing
   - **Audience:** All Roles (or restrict as needed)
   - **Execute As Role:** Administrator
3. Click **Save**

#### 1.4 Get RESTlet URL

After deployment, copy the External URL:
```
https://XXXXXX.restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=YYYY&deploy=1
```

Save this URL - you'll need it for the Python script.

### Step 2: Configure Python Environment

#### 2.1 Set Environment Variable

Add the RESTlet URL to your `.env` file:

```bash
# Add to .env
NETSUITE_FIVETRAN_RESTLET_URL=https://XXXXXX.restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=YYYY&deploy=1
```

Or export directly:
```bash
export NETSUITE_FIVETRAN_RESTLET_URL="https://XXXXXX.restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=YYYY&deploy=1"
```

#### 2.2 Make Script Executable

```bash
chmod +x scripts/analyze_fivetran_permissions.py
```

### Step 3: Test the Setup

#### 3.1 Test RESTlet Directly

```bash
# Test with curl
curl -X GET "https://XXXXXX.restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=YYYY&deploy=1" \
  -H "Authorization: YOUR_OAUTH_HEADER" \
  -H "Content-Type: application/json"
```

**Expected response:**
```json
{
  "success": true,
  "data": {
    "roles": [
      {
        "role_id": "customrole_fivetran_controller",
        "role_name": "Fivetran - Controller",
        "is_inactive": false,
        "is_assignable": true,
        "is_custom": true,
        "permissions": [
          {
            "permission_id": "123",
            "permission_name": "TRAN_VENDPYMT",
            "permission_level": "2"
          }
        ],
        "permission_count": 45
      }
    ],
    "metadata": {
      "total_roles": 5,
      "execution_time_ms": 1234,
      "governance_used": 50
    }
  }
}
```

#### 3.2 Test Python Script

```bash
# Dry run to verify setup
python3 scripts/analyze_fivetran_permissions.py --output-dir test_output
```

---

## Running the Analysis

### Full Analysis

```bash
python3 scripts/analyze_fivetran_permissions.py
```

This will:
1. Fetch all Fivetran roles from NetSuite
2. Build permission matrix
3. Analyze conflicts
4. Generate SOD rules
5. Export results to `output/` directory

### With Custom Parameters

```bash
# Custom output directory
python3 scripts/analyze_fivetran_permissions.py --output-dir /path/to/output

# Custom RESTlet URL (override env var)
python3 scripts/analyze_fivetran_permissions.py --restlet-url "https://..."
```

---

## Understanding the Output

### Output Files

After running, you'll get 5 files in the output directory:

#### 1. `fivetran_roles_TIMESTAMP.json`
**Raw role data from NetSuite**

```json
{
  "roles": [
    {
      "role_id": "customrole_fivetran_controller",
      "role_name": "Fivetran - Controller",
      "permissions": [...],
      "permission_count": 45
    }
  ],
  "metadata": {
    "total_roles": 5,
    "execution_time_ms": 1234
  }
}
```

#### 2. `permission_matrix_TIMESTAMP.json`
**Permission → Roles mapping**

```json
{
  "TRAN_VENDPYMT": [
    {
      "role_name": "Fivetran - Controller",
      "role_id": "customrole_fivetran_controller",
      "permission_level": "2"
    },
    {
      "role_name": "Fivetran - AP Clerk",
      "role_id": "customrole_fivetran_ap_clerk",
      "permission_level": "1"
    }
  ]
}
```

**Interpretation:**
- Permission shared by 2+ roles = potential conflict
- `permission_level`: 0=None, 1=View, 2=Create, 3=Edit, 4=Full

#### 3. `conflicts_TIMESTAMP.json`
**Identified SOD conflicts**

```json
[
  {
    "role1": "Fivetran - Controller",
    "role2": "Fivetran - AP Clerk",
    "severity": "HIGH",
    "description": "Same user can create and approve transactions",
    "conflicting_permissions": [
      "TRAN_VENDPYMT",
      "TRAN_VENDBILL",
      "TRAN_VENDCRED"
    ],
    "risk_category": "Financial"
  }
]
```

#### 4. `sod_rules_fivetran_TIMESTAMP.json`
**Generated SOD rules (ready to import)**

```json
[
  {
    "rule_id": "SOD-FIVETRAN-001",
    "rule_name": "Fivetran - Controller vs. Fivetran - AP Clerk Separation",
    "rule_type": "Financial",
    "description": "Same user can create and approve transactions. Conflicting permissions: TRAN_VENDPYMT, TRAN_VENDBILL, TRAN_VENDCRED",
    "conflicting_permissions": ["TRAN_VENDPYMT", "TRAN_VENDBILL", "TRAN_VENDCRED"],
    "severity": "HIGH",
    "is_active": true
  }
]
```

#### 5. `analysis_report_TIMESTAMP.txt`
**Human-readable summary**

```
================================================================================
FIVETRAN ROLE PERMISSION ANALYSIS REPORT
================================================================================
Generated: 2026-02-12 15:30:00

SUMMARY
--------------------------------------------------------------------------------
Total Fivetran Roles: 5
Unique Permissions: 123
Conflicts Identified: 8

FIVETRAN ROLES
--------------------------------------------------------------------------------

Fivetran - Controller:
   Role ID: customrole_fivetran_controller
   Permissions: 45
   Active: Yes

IDENTIFIED CONFLICTS
--------------------------------------------------------------------------------

1. Fivetran - Controller + Fivetran - AP Clerk
   Severity: HIGH
   Description: Same user can create and approve transactions
   Conflicting Permissions (12):
      - TRAN_VENDPYMT
      - TRAN_VENDBILL
      ...
```

---

## Importing SOD Rules

After reviewing the generated rules, import them into the database:

### Method 1: Direct Import

```bash
# Copy generated rules to seed data
cp output/sod_rules_fivetran_TIMESTAMP.json database/seed_data/sod_rules_fivetran.json

# Restart MCP server to load new rules
./scripts/restart_mcp.sh
```

### Method 2: Merge with Existing Rules

```python
# Python script to merge rules
import json

# Load existing rules
with open('database/seed_data/sod_rules.json', 'r') as f:
    existing_rules = json.load(f)

# Load new Fivetran rules
with open('output/sod_rules_fivetran_TIMESTAMP.json', 'r') as f:
    fivetran_rules = json.load(f)

# Merge (keep existing + add new)
all_rules = existing_rules + fivetran_rules

# Save merged rules
with open('database/seed_data/sod_rules.json', 'w') as f:
    json.dump(all_rules, f, indent=2)

print(f"Merged {len(existing_rules)} + {len(fivetran_rules)} = {len(all_rules)} rules")
```

### Method 3: Manual Review and Import

1. Open `sod_rules_fivetran_TIMESTAMP.json`
2. Review each rule
3. Adjust severity/description as needed
4. Copy relevant rules to `sod_rules.json`
5. Restart server

---

## Analyzing Users with New Rules

After importing Fivetran SOD rules:

### Step 1: Sync Users with Fivetran Roles

```bash
# Trigger full sync (this will get users with Fivetran roles)
# Via MCP tool or Python
trigger_manual_sync(sync_type="full")
```

### Step 2: Run SOD Analysis

The system will automatically:
1. Load Fivetran SOD rules from database
2. Analyze users for Fivetran role combinations
3. Create violations for conflicts

### Step 3: View Results

```sql
-- Check violations
SELECT
    u.name,
    u.email,
    sr.rule_name,
    v.severity,
    v.status
FROM violations v
JOIN users u ON v.user_id = u.id
JOIN sod_rules sr ON v.rule_id = sr.id
WHERE sr.rule_id LIKE 'SOD-FIVETRAN-%'
ORDER BY v.severity DESC, u.name;
```

Or via MCP tool:
```
get_violation_stats()
```

---

## Troubleshooting

### Issue: RESTlet returns 0 roles

**Possible causes:**
1. No roles in NetSuite start with "Fivetran -"
2. Role names have different capitalization
3. RESTlet permissions issue

**Debug:**
```javascript
// Add to RESTlet
log.audit('Role Search', 'Searching for: ' + rolePrefix);
log.audit('Filters', JSON.stringify(filters));
```

### Issue: No permissions returned

**Possible causes:**
1. RolePermissions table empty
2. SuiteQL query syntax error
3. Governance unit limit reached

**Debug:**
```javascript
// Check query results
log.audit('Permission Query Results', results.length + ' records');
log.audit('Sample Result', JSON.stringify(results[0]));
```

### Issue: Python script fails with authentication error

**Solution:**
```bash
# Verify NetSuite credentials
echo $NETSUITE_CONSUMER_KEY
echo $NETSUITE_TOKEN_ID
echo $NETSUITE_REALM

# Test NetSuite client
python3 -c "from services.netsuite_client import NetSuiteClient; c=NetSuiteClient(); print('OK')"
```

### Issue: No conflicts identified

**Possible causes:**
1. Fivetran roles are properly segregated (good!)
2. Conflict detection logic too strict
3. Permission categorization needs tuning

**Solution:**
Adjust conflict patterns in `analyze_fivetran_permissions.py`:
```python
# Line ~200 - Add/modify SOD patterns
sod_patterns = [
    (['create_edit'], ['approve'], 'HIGH', 'Create and approve conflict'),
    # Add custom patterns here
]
```

---

## Advanced Configuration

### Custom Role Prefix

If your roles use a different prefix:

```bash
# Instead of "Fivetran -", use "Celigo -"
python3 scripts/analyze_fivetran_permissions.py --custom-prefix "Celigo -"
```

Or modify RESTlet payload in Python:
```python
payload = {
    "rolePrefix": "Celigo -"  # Custom prefix
}
```

### Custom Conflict Rules

Edit `_check_role_pair_conflict()` in the Python script:

```python
# Add industry-specific patterns
sod_patterns = [
    # Healthcare SOD
    (['patient_data'], ['billing'], 'CRITICAL', 'Healthcare data segregation'),

    # Manufacturing SOD
    (['bom_edit'], ['production'], 'HIGH', 'BOM and production segregation'),
]
```

### Exclude Specific Permissions

Some permissions are low-risk and create noise:

```python
# In build_permission_matrix()
EXCLUDED_PERMISSIONS = ['LOGIN', 'LIST_EMPLOYEE', 'VIEW_DASHBOARD']

for perm in permissions:
    if perm['permission_name'] in EXCLUDED_PERMISSIONS:
        continue  # Skip low-risk permissions
```

---

## Next Steps

After completing role permission analysis:

1. **Review Results**
   - Validate identified conflicts
   - Adjust severities as needed
   - Add business context to descriptions

2. **Import SOD Rules**
   - Merge with existing rules
   - Test rule application
   - Document rationale

3. **Run User Analysis**
   - Sync users with Fivetran roles
   - Apply new SOD rules
   - Review violations

4. **Iterate**
   - Refine conflict detection
   - Add more SOD patterns
   - Adjust sensitivity

5. **Document**
   - Update LESSONS_LEARNED.md
   - Create runbooks
   - Train team

---

## Related Documentation

- **RESTlet Code:** `netsuite_scripts/fivetran_roles_permissions_restlet.js`
- **Analysis Script:** `scripts/analyze_fivetran_permissions.py`
- **Role Filtering:** `docs/NETSUITE_ROLE_FILTERING.md`
- **SOD Rules:** `database/seed_data/sod_rules.json`
- **Architecture:** `docs/SOD_COMPLIANCE_ARCHITECTURE.md`

---

**Version:** 1.0
**Author:** Prabal Saha
**Last Updated:** 2026-02-12
