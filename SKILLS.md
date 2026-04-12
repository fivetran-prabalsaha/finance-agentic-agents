# SOD Compliance System - Skills & Capabilities

**Version:** 1.0
**Last Updated:** 2026-02-12
**System:** AI-Powered Segregation of Duties (SOD) Compliance System

---

## 🎯 Overview

This document catalogs all capabilities, tools, scripts, and skills available in the SOD Compliance System. Use this as a reference for what the system can do and how to leverage its features.

---

## 📊 Core Capabilities

### 1. **Autonomous Data Collection**
- **Capability:** Automatically sync user, role, and permission data from NetSuite
- **Frequency:** Daily full sync (2:00 AM) + Hourly incremental sync
- **Coverage:** 99.7% (1,928/1,933 users)
- **Skills:**
  - Full synchronization across all systems
  - Incremental updates for changed data
  - Error handling and retry logic
  - Governance-aware pagination (200 records/page)

### 2. **Context-Aware SOD Analysis**
- **Capability:** Intelligent violation detection with job role context
- **Reduction:** 67% fewer false positives vs traditional SOD
- **Skills:**
  - Recognize legitimate role combinations for specific job titles
  - Recommend compensating controls vs role removal
  - Calculate residual risk after controls applied
  - Generate business justifications

### 3. **AI-Powered Analysis**
- **Model:** Claude Opus 4.6 (200K context window)
- **Capability:** Deep analysis of access patterns and violations
- **Skills:**
  - Natural language violation explanations
  - Risk severity assessment (CRITICAL/HIGH/MEDIUM/LOW)
  - Remediation recommendations
  - Pattern recognition across users and roles

### 4. **Semantic Search (pgvector)**
- **Capability:** Vector-based knowledge base search
- **Technology:** PostgreSQL with pgvector extension
- **Skills:**
  - Semantic similarity search for compliance policies
  - Embedding-based document retrieval
  - Context-aware Q&A from knowledge base
  - 384-dimensional vector embeddings (HuggingFace)

### 5. **Real-Time Compliance Monitoring**
- **Capability:** Continuous monitoring of access changes
- **Skills:**
  - Violation detection on new access grants
  - Alert generation for critical violations
  - Audit trail maintenance
  - Compliance dashboard updates

---

## 🔧 MCP Tools (22 Tools Available)

### System Management

#### `list_systems`
**Purpose:** List all integrated systems with status
**Input:** None
**Output:** System inventory with user counts and sync status
**Use Case:** Check which systems are connected and their health

#### `trigger_manual_sync`
**Purpose:** Force immediate data synchronization
**Input:** `system_name` (optional), `sync_type` (full/incremental)
**Output:** Sync job ID and status
**Use Case:** Update data before running analysis or after major changes

#### `get_sync_status`
**Purpose:** Check status of data synchronization
**Input:** `sync_id` (optional)
**Output:** Sync progress, records processed, errors
**Use Case:** Monitor ongoing syncs or troubleshoot failures

---

### User & Access Analysis

#### `list_all_users`
**Purpose:** Get all users with role assignments
**Input:** `system_name`, `limit`, `offset`, `filter`
**Output:** User list with roles, permissions, status
**Use Case:** Review user access across systems

#### `get_user_details`
**Purpose:** Deep dive into specific user's access
**Input:** `user_email` or `user_id`
**Output:** Complete user profile with all roles, permissions, violations
**Use Case:** User access review, troubleshooting violations

#### `analyze_user_access`
**Purpose:** AI-powered analysis of user's access patterns
**Input:** `user_email`, `include_recommendations`
**Output:** SOD violations, risk assessment, remediation steps
**Use Case:** Quarterly access reviews, new hire audits

#### `compare_users`
**Purpose:** Compare access between two users
**Input:** `user1_email`, `user2_email`
**Output:** Access differences, common permissions, role gaps
**Use Case:** Role template creation, peer comparison

---

### SOD Violation Management

#### `get_violation_stats`
**Purpose:** Summary statistics on violations
**Input:** `system_name` (optional), `severity` (optional)
**Output:** Counts by severity, category, status
**Use Case:** Executive reporting, compliance dashboards

#### `list_violations`
**Purpose:** Get detailed violation list
**Input:** `system_name`, `severity`, `status`, `limit`
**Output:** Violations with user details, affected permissions
**Use Case:** Remediation planning, audit evidence

#### `get_violation_details`
**Purpose:** Deep analysis of specific violation
**Input:** `violation_id`
**Output:** Full violation context, history, recommendations
**Use Case:** Investigating specific compliance issues

#### `resolve_violation`
**Purpose:** Mark violation as resolved
**Input:** `violation_id`, `resolution_type`, `notes`
**Output:** Updated violation status
**Use Case:** Tracking remediation progress

---

### Role & Permission Analysis

#### `query_sod_rules`
**Purpose:** Get SOD rules and conflict definitions
**Input:** `severity` (optional), `category` (optional)
**Output:** Active SOD rules with conflicting permission pairs
**Use Case:** Understanding what constitutes a violation

#### `check_permission_conflict`
**Purpose:** Check if specific permissions conflict
**Input:** `permission1`, `permission2`, `system_name`
**Output:** Conflict status, severity, applicable SOD rules
**Use Case:** Pre-approval checking before granting access

#### `get_permission_categories`
**Purpose:** Get permission taxonomy
**Input:** `system_name`
**Output:** Permission categories and classifications
**Use Case:** Understanding permission structure

#### `search_permissions`
**Purpose:** Search for specific permissions
**Input:** `search_term`, `system_name`, `category`
**Output:** Matching permissions with descriptions
**Use Case:** Finding permissions for access requests

#### `analyze_role_permissions`
**Purpose:** Analyze what permissions a role grants
**Input:** `role_name`, `system_name`
**Output:** Complete permission breakdown, SOD implications
**Use Case:** Role design, access request validation

---

### Job Role Context & Recommendations

#### `validate_job_role`
**Purpose:** Check if role combination is acceptable for job title
**Input:** `job_title`, `role_names[]`
**Output:** Acceptability status, required controls, justification
**Use Case:** Access request approval, onboarding

#### `recommend_roles_for_job_title`
**Purpose:** Suggest appropriate roles for a job title
**Input:** `job_title`, `department`, `format`
**Output:** Recommended roles with priorities and justifications
**Use Case:** New hire provisioning, role templates

#### `get_compensating_controls`
**Purpose:** Get available compensating controls
**Input:** `severity` (optional), `control_type` (optional)
**Output:** Controls with effectiveness, costs, implementation steps
**Use Case:** Risk mitigation planning

#### `find_peers_by_job_title`
**Purpose:** Find users with same/similar job titles
**Input:** `job_title`, `department` (optional)
**Output:** List of peer users with their role assignments
**Use Case:** Peer comparison, role consistency checks

---

### Knowledge Base

#### `query_knowledge_base`
**Purpose:** Search compliance knowledge base
**Input:** `query`, `top_k`, `filter`
**Output:** Relevant documents with similarity scores
**Use Case:** Policy lookup, compliance guidance

#### `analyze_access_request`
**Purpose:** AI-powered access request analysis
**Input:** `user_info`, `requested_roles`, `justification`
**Output:** Approval recommendation, risks, required controls
**Use Case:** Automated access request workflow

---

## 🛠️ Management Scripts

### Server Management

#### `scripts/restart_mcp.sh`
**Purpose:** Restart MCP server with health checks
**Features:**
- Graceful shutdown of existing server
- Port availability check
- Python environment verification
- Startup validation (8 checks)
- Log tailing for immediate error detection

**Usage:**
```bash
./scripts/restart_mcp.sh
```

#### `scripts/check_mcp_status.sh`
**Purpose:** Comprehensive server health check (12 checks)
**Checks:**
1. Process status (PID, uptime, memory, CPU)
2. Port 8080 listening status
3. Database connectivity
4. Log file presence and recent errors
5. Autonomous agent status
6. MCP tools loaded count
7. Recent sync activity
8. Governance metrics

**Usage:**
```bash
./scripts/check_mcp_status.sh
```

**Output:** Color-coded status report with recommendations

---

### Database Management

#### `scripts/seed_job_role_mappings.py`
**Purpose:** Seed job role mappings into database
**Features:**
- Load from `data/job_role_mappings.json`
- Upsert logic (create or update)
- Validation of required fields
- Summary report

**Usage:**
```bash
python3 scripts/seed_job_role_mappings.py
```

#### `scripts/seed_sod_configurations.py`
**Purpose:** Seed SOD rules and configurations
**Features:**
- Load SOD rules from seed data
- Configure conflict matrices
- Set up permission categories
- Validate rule completeness

**Usage:**
```bash
python3 scripts/seed_sod_configurations.py
```

#### `scripts/update_user_job_titles.py`
**Purpose:** Update user job titles in bulk
**Features:**
- CSV import of job title mappings
- Email to job title association
- Validation and error handling
- Dry-run mode

**Usage:**
```bash
python3 scripts/update_user_job_titles.py --file mappings.csv [--dry-run]
```

---

### Analysis Scripts

#### `scripts/analyze_access_request_with_levels.py`
**Purpose:** Level-based SOD analysis for access requests
**Features:**
- Permission level analysis (View/Create/Edit/Full)
- Conflict matrix evaluation
- Risk scoring with level multipliers
- Resolution option generation
- Compensating control recommendations

**Usage:**
```bash
python3 scripts/analyze_access_request_with_levels.py \
  --user "jane.smith@company.com" \
  --job-title "Revenue Director" \
  --requested-roles "Revenue Manager,Revenue Approver" \
  --output report.json
```

**Output:** JSON report with:
- Inherent risk score
- Residual risk (after controls)
- Resolution options (reject, split, reduce levels, controls)
- Required approvals
- Implementation steps

#### `scripts/analyze_fivetran_permissions_advanced.py`
**Purpose:** Deep analysis of Fivetran-specific permissions
**Features:**
- Extract permissions from all Fivetran roles
- Categorize by functional area
- Identify overlaps and conflicts
- Generate permission matrices
- Export to CSV/JSON

**Usage:**
```bash
python3 scripts/analyze_fivetran_permissions_advanced.py \
  --role-prefix "Fivetran" \
  --output-dir analysis/
```

#### `scripts/analyze_all_roles_internal_sod.py`
**Purpose:** Analyze internal SOD conflicts within roles
**Features:**
- Check if single roles contain conflicting permissions
- Identify "super roles" with excessive access
- Generate risk reports
- Recommend role splitting

**Usage:**
```bash
python3 scripts/analyze_all_roles_internal_sod.py \
  --system netsuite \
  --output internal_conflicts.json
```

#### `scripts/analyze_and_categorize_permissions.py`
**Purpose:** Categorize and analyze permission structure
**Features:**
- Auto-categorization by naming patterns
- Functional area mapping
- Risk level assignment
- Permission taxonomy export

**Usage:**
```bash
python3 scripts/analyze_and_categorize_permissions.py \
  --system netsuite \
  --output-file permission_taxonomy.json
```

---

### Knowledge Base Management

#### `scripts/ingest_role_conflicts_to_kb.py`
**Purpose:** Ingest role conflict documentation into knowledge base
**Features:**
- Parse conflict definitions
- Generate embeddings
- Store in vector database
- Update semantic search index

**Usage:**
```bash
python3 scripts/ingest_role_conflicts_to_kb.py \
  --input-file conflicts.json \
  --kb-collection sod_rules
```

---

### Testing & Validation

#### `scripts/test_job_role_context.py`
**Purpose:** Test job role context-aware analysis
**Features:**
- Test scenarios for multiple job titles
- Validate recommendations
- Check control suggestions
- Verify false positive reduction

**Usage:**
```bash
python3 scripts/test_job_role_context.py \
  --job-title "Revenue Director" \
  --verbose
```

#### `smoke_test_mcp_live.py`
**Purpose:** Comprehensive system smoke test (12 tests)
**Tests:**
1. Database connection
2. Database tables & data
3. pgvector extension
4. Embedding service
5. Knowledge base agent
6. LLM service
7. Data collection agent
8. SOD analyzer agent
9. Notification agent
10. Cache system
11. MCP orchestrator
12. Data repositories

**Usage:**
```bash
python3 smoke_test_mcp_live.py
```

**Output:** Detailed test report with pass/fail status

---

## 📚 Data Configuration Files

### `data/job_role_mappings.json`
**Purpose:** Job title to role mappings with business justifications
**Contains:** 11 job role definitions including:
- Revenue Director
- Controller
- Accounts Payable Manager
- Accounts Receivable Manager
- Senior Accountant
- Tax Manager
- Financial Analyst
- Billing Specialist
- Accounting Manager
- System Administrator
- NetSuite Administrator

**Structure:**
```json
{
  "job_roles": {
    "revenue_director": {
      "title": "Revenue Director",
      "typical_netsuite_roles": [...],
      "acceptable_role_combinations": [...],
      "restrictions": {...}
    }
  }
}
```

### `data/compensating_controls.json`
**Purpose:** Library of compensating controls with effectiveness metrics
**Contains:**
- 12 individual controls
- 6 control packages (Low/Medium/High/Critical/Executive/Developer)
- Risk reduction percentages
- Implementation costs
- Implementation steps

**Controls Include:**
- Segregated Approval Workflows (70% risk reduction)
- Dual Approval Workflow (60% risk reduction)
- Transaction Amount Limits (40% risk reduction)
- Real-Time Monitoring (50% risk reduction)
- And 8 more...

### `data/netsuite_sod_config_unified.json`
**Purpose:** Level-based SOD conflict configuration
**Contains:**
- Permission level definitions (None/View/Create/Edit/Full)
- Permission categories (transaction_entry, transaction_approval, etc.)
- 5×5 conflict matrices for each SOD rule
- Resolution strategies by severity
- Level risk multipliers

### `data/netsuite_permission_mapping.json`
**Purpose:** Comprehensive NetSuite permission catalog (7,931 permissions)
**Contains:**
- Permission names and descriptions
- Functional categorization
- Level assignments
- Role associations

### `data/netsuite_permission_categories.json`
**Purpose:** Permission taxonomy and categorization
**Contains:**
- Functional areas (Finance, Operations, IT, etc.)
- Risk categories (Financial, Security, Compliance)
- Permission groupings

---

## 🎓 Knowledge & Expertise

### Domain Knowledge Built-In

#### SOD Compliance
- 18 active SOD rules across 3 risk categories
- Industry-standard conflict definitions
- Audit-ready documentation templates
- Regulatory framework alignment

#### NetSuite ERP
- Deep understanding of NetSuite permission model
- Role hierarchy and inheritance
- Custom vs standard role differences
- RESTlet API integration patterns

#### Financial Controls
- Maker-checker workflows
- Segregation of duties best practices
- Compensating control frameworks
- Risk assessment methodologies

#### Job Role Intelligence
- 11 pre-configured job role mappings
- Business justification templates
- Peer comparison capabilities
- Role template recommendations

---

## 🔍 Advanced Capabilities

### 1. **Risk Scoring**
- **Inherent Risk:** Base risk without controls (0-100)
- **Residual Risk:** Risk after controls applied
- **Risk Reduction %:** Effectiveness of controls
- **Severity Mapping:** CRITICAL/HIGH/MEDIUM/LOW

### 2. **Level-Based Analysis**
- **Permission Levels:** None(0), View(1), Create(2), Edit(3), Full(4)
- **Conflict Matrices:** 5×5 matrices for each SOD rule
- **Level Risk Multipliers:** Scale risk by privilege level
- **Granular Recommendations:** Reduce to View vs full removal

### 3. **Automated Workflows**
- **Daily Full Sync:** Complete data refresh at 2:00 AM
- **Hourly Incremental:** Changed data only
- **Real-Time Alerts:** Critical violation notifications
- **Scheduled Reviews:** Quarterly audit prep

### 4. **Reporting & Analytics**
- **Executive Dashboards:** High-level compliance metrics
- **Detailed Reports:** User-level violation breakdowns
- **Trend Analysis:** Violation patterns over time
- **Audit Evidence:** Export for compliance audits

---

## 💡 Use Cases & Workflows

### Use Case 1: New Hire Onboarding
**Workflow:**
1. Use `recommend_roles_for_job_title` with job title
2. Review recommended roles and justifications
3. Use `validate_job_role` to check combination
4. If conflicts exist, get `get_compensating_controls`
5. Use `analyze_access_request` for final approval
6. Grant access with documented justification

**Tools Used:** 3-4 MCP tools, 0 scripts

### Use Case 2: Quarterly Access Review
**Workflow:**
1. Run `list_all_users` to get user inventory
2. For each user, run `analyze_user_access`
3. Use `find_peers_by_job_title` to compare with peers
4. Review flagged violations with `get_violation_details`
5. Document resolutions with `resolve_violation`
6. Generate report with `get_violation_stats`

**Tools Used:** 6 MCP tools, 0 scripts

### Use Case 3: Access Request Approval
**Workflow:**
1. Receive access request with job title and roles
2. Run `scripts/analyze_access_request_with_levels.py`
3. Review conflict analysis and risk scores
4. Check if combination is acceptable with `validate_job_role`
5. If conflicts exist, review compensating controls
6. Obtain required approvals (CFO, Manager, etc.)
7. Grant access with documented controls
8. Schedule follow-up review

**Tools Used:** 2 MCP tools, 1 script

### Use Case 4: SOD Violation Remediation
**Workflow:**
1. Get violations with `list_violations` (severity=CRITICAL)
2. For each violation, run `get_violation_details`
3. Use `query_knowledge_base` to find remediation guidance
4. Check if job role justifies with `validate_job_role`
5. If not justified, split roles or implement controls
6. Document resolution with `resolve_violation`
7. Verify fix with `analyze_user_access`

**Tools Used:** 5 MCP tools, 0 scripts

### Use Case 5: Role Template Creation
**Workflow:**
1. Identify common job title (e.g., "Accountant")
2. Use `find_peers_by_job_title` to find existing users
3. Run `compare_users` for top 3-5 users
4. Identify common role combinations
5. Validate with `validate_job_role`
6. Document as template in `data/job_role_mappings.json`
7. Seed with `scripts/seed_job_role_mappings.py`

**Tools Used:** 3 MCP tools, 1 script

---

## 🚀 Quick Reference

### Most Common Commands

**Check System Health:**
```bash
./scripts/check_mcp_status.sh
```

**Restart Server:**
```bash
./scripts/restart_mcp.sh
```

**Run Smoke Tests:**
```bash
python3 smoke_test_mcp_live.py
```

**Analyze Access Request:**
```bash
python3 scripts/analyze_access_request_with_levels.py \
  --user "user@company.com" \
  --job-title "Role Title" \
  --requested-roles "Role1,Role2"
```

**Get Role Recommendations (via Python):**
```python
from mcp.orchestrator import ComplianceOrchestrator
orch = ComplianceOrchestrator()
result = orch.validate_job_role(
    job_title="Revenue Director",
    role_names=["Revenue Manager", "Revenue Approver"]
)
```

---

## 📊 Metrics & Performance

| Metric | Value |
|--------|-------|
| **User Coverage** | 99.7% (1,928/1,933) |
| **SOD Rules** | 24 active rules |
| **MCP Tools** | 22 tools available |
| **Job Role Mappings** | 11 pre-configured |
| **Compensating Controls** | 12 individual + 6 packages |
| **Permission Mappings** | 7,931 NetSuite permissions |
| **False Positive Reduction** | 67% improvement |
| **Query Performance** | 55x faster (cached) |
| **Sync Frequency** | Daily full + Hourly incremental |
| **Vector Dimensions** | 384 (HuggingFace embeddings) |

---

## 🔗 Related Documentation

- **CLAUDE.md** - Complete project guide for Claude Code
- **docs/LESSONS_LEARNED.md** - 17 documented issues with solutions
- **docs/MCP_SERVER_MANAGEMENT.md** - Server operations guide
- **SMOKE_TEST_RESULTS.md** - Latest test results
- **README.md** - Getting started guide

---

**Last Updated:** 2026-02-12
**Maintained By:** AI Development Team
**System Version:** 1.0 (Production-Ready)
