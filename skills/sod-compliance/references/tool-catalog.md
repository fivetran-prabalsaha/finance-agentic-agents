# Compliance MCP Tool Catalog

All 35 tools available on the compliance MCP server (http://localhost:8080).
Organized by workflow group matching the tool router intent classification.

---

## Group: Access Review

| Tool | Key Parameters | Returns |
|------|---------------|---------|
| `analyze_access_request` | `user_id`, `requested_role`, `include_existing_roles` (bool, **always true**) | Conflict list with severity, affected SOD rules, risk score |
| `get_user_violations` | `user_identifier` (name, email, or ID) | User record, current roles, all violations, risk score |
| `validate_job_role` | `user_id`, `job_title`, `proposed_roles` | Whether role set is appropriate for the job function |
| `get_role_conflicts` | `role_name` | All other roles that conflict with this role |
| `recommend_roles_for_job_title` | `job_title`, `department` | Recommended minimal role set for the job title |

---

## Group: Violation Query

| Tool | Key Parameters | Returns |
|------|---------------|---------|
| `list_violations` | `severity`, `department`, `status`, `user_id`, `limit` | Paginated violation list |
| `get_violation_stats` | _(none)_ | Counts by severity, department, and status; compliance rate |
| `get_violation_details` | `violation_id` | Full violation record: user, conflicting permissions, rule, risk score, history |
| `get_violation_history` | `user_id`, `days_back` | Historical violation trend for a user |

---

## Group: Exception Management

| Tool | Key Parameters | Returns |
|------|---------------|---------|
| `request_exception_approval` | `violation_id`, `business_justification`, `compensating_controls`, `expiry_date` | Exception ID, status |
| `check_my_approval_authority` | _(none)_ | Max severity level current user can approve, pending items |
| `get_exception_details` | `exception_id` | Full exception record, justification, compensating controls, approver chain |
| `list_active_exceptions` | `department`, `user_id`, `status` | Active exception list |
| `approve_exception` | `exception_id`, `approval_notes` | Updated exception status |
| `revoke_exception` | `exception_id`, `reason` | Confirmation of revocation |

---

## Group: SOD Rules

| Tool | Key Parameters | Returns |
|------|---------------|---------|
| `list_sod_rules` | `category`, `severity` | All rules with code, name, severity, category |
| `query_sod_rules` | `keyword` | Rules matching keyword in name or description |
| `get_sod_rule_details` | `rule_code` | Full rule: conflicting permissions, rationale, example violations, compensating controls |

---

## Group: Knowledge Base

| Tool | Key Parameters | Returns |
|------|---------------|---------|
| `query_knowledge_base` | `query`, `top_k` | Semantic search results from policy documents |
| `get_compensating_controls` | `violation_id` or `rule_code` | Recommended compensating controls |
| `get_permission_categories` | _(none)_ | Taxonomy of all NetSuite permission categories |
| `search_permissions` | `search_term` | Permissions matching the search term |

---

## Group: Role Analysis

| Tool | Key Parameters | Returns |
|------|---------------|---------|
| `analyze_role_permissions` | `role_name` | All permissions granted by the role |
| `get_role_conflicts` | `role_name` | Conflicting roles with reason |
| `recommend_roles_for_job_title` | `job_title`, `department` | Minimal compliant role set |
| `validate_job_role` | `user_id`, `job_title`, `proposed_roles` | Validation result with gap analysis |

---

## Group: Reporting

| Tool | Key Parameters | Returns |
|------|---------------|---------|
| `get_violation_stats` | _(none)_ | Org-wide counts; use for report preamble |
| `get_org_risk_assessment` | _(none)_ | Org-wide risk score, high-risk user list, department rankings |
| `generate_compliance_report` | `report_type`, `audience`, `department`, `focus_areas` | Formatted report string |
| `export_report` | `report_id`, `format` (pdf/csv/json) | Download URL or base64 content |

**report_type values:** `executive_summary`, `detailed_analysis`, `department_report`, `audit_report`, `trend_analysis`
**audience values:** `executives`, `compliance_team`, `auditors`, `it_security`, `department_heads`

---

## Group: Remediation

| Tool | Key Parameters | Returns |
|------|---------------|---------|
| `remediate_violation` | `violation_id`, `action` (remove_role/restrict_access), `role_to_remove` | Remediation record ID |
| `schedule_review` | `violation_id`, `review_date` (ISO), `reviewer_id` | Scheduled review record |
| `create_remediation_ticket` | `violation_id`, `ticket_system` (jira/servicenow) | Ticket URL/ID |
| `notify_manager` | `user_id`, `violation_id`, `message` | Notification confirmation |

---

## Group: System / Data Sync

| Tool | Key Parameters | Returns |
|------|---------------|---------|
| `initialize_session` | `user_identifier` (optional) | Session context, current user info |
| `list_systems` | _(none)_ | Connected systems: NetSuite, Okta, Salesforce, Coupa |
| `get_system_status` | `system_name` | Health, last sync time, record count |
| `trigger_manual_sync` | `sync_type` (full/incremental) | Sync job ID, estimated duration |
| `get_sync_status` | `job_id` (optional) | Last sync result or status of running job |

---

## Common Parameter Patterns

```
user_identifier: accepts email, display name, or internal user ID
violation_id:    format "VIO-{numeric}" e.g. "VIO-1234"
exception_id:    format "EX-{year}-{numeric}" e.g. "EX-2024-001"
rule_code:       uppercase with underscores e.g. "AP_ENTRY_VS_AP_APPROVAL"
severity:        CRITICAL | HIGH | MEDIUM | LOW
status:          OPEN | PENDING_REVIEW | RESOLVED | EXCEPTED
```
