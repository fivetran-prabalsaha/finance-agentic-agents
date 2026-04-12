---
name: sod-compliance
description: "SOD (Segregation of Duties) compliance workflows for Celigo's NetSuite environment. Use when asked about user access violations or role conflicts, compliance risk scores, CRITICAL/HIGH violation lists, exception approvals or requests, SOX audit readiness, compliance reports, role permission analysis, manual NetSuite sync, compensating controls, or SOD rule lookups. Handles multi-step access review — fetches current roles, analyzes full role combination for conflicts, and gives a risk-scored recommendation. Requires the compliance MCP server running at localhost:8080."
metadata:
  author: Celigo SysEng
  version: 1.3.0
  compatibility: "Claude Code, Claude.ai — requires compliance MCP server at localhost:8080"
  mcp-server: compliance-system
---

# SOD Compliance Skill

## Instructions

This skill orchestrates multi-step SOD compliance workflows against Celigo's live NetSuite data
using the compliance MCP server (35 tools, 18 SOD rules, 1,928 users).

Always use MCP tools to fetch real data. Never fabricate violation counts, role names, or risk scores.

Consult `references/tool-catalog.md` for the full tool list with parameter details.
Consult `references/sod-rules.md` for all 18 active SOD rules and their severity.

---

## Critical

CRITICAL: Never answer compliance questions from training data. Every violation count,
role name, risk score, and SOD rule MUST come from a live MCP tool call.

CRITICAL: Always pass `include_existing_roles: true` to `analyze_access_request`.
Omitting it produces false "0 conflicts" results for existing role combinations.

---

### Before Any Workflow: MCP Health Check

If a tool call returns a connection error, stop and tell the user:

```
The compliance MCP server appears offline.
Start it with: cd compliance-agent && python3 -m mcp.mcp_server > /tmp/mcp_server.log 2>&1 &
Then verify: curl -s http://localhost:8080/health
```

---

### Workflow 1: Access Review ("Can we assign role X to user Y?")

Use when: user asks if a person can receive a new role, permission, or system access.

**Steps:**
1. Call `initialize_session` to load the user's compliance context.
2. Resolve the user's email if given a name: call `get_user_violations(user_identifier=<name>)` — the response includes the canonical user ID and current roles.
3. Call `analyze_access_request` with:
   - `user_id`: from step 2
   - `requested_role`: the new role being considered
   - `include_existing_roles: true` — this is critical; it analyzes ALL roles together, not just the new one in isolation
4. If conflicts exist, call `get_compensating_controls` for each CRITICAL or HIGH conflict.
5. Synthesize the result:
   - Lead with the risk verdict: APPROVED / CONDITIONAL / DENIED
   - List each SOD conflict with severity and the two clashing permissions
   - Suggest compensating controls if conflicts are present
   - If CRITICAL conflicts exist, recommend rejection and explain the fraud risk

**Key rule:** Always use `include_existing_roles: true`. Omitting it causes false "0 conflicts" results.

---

### Workflow 2: Violation Query ("Show me CRITICAL violations in Finance")

Use when: user wants to see existing violations filtered by severity, department, or user.

**Steps:**
1. Call `list_violations` with any applicable filters:
   - `severity`: CRITICAL | HIGH | MEDIUM | LOW
   - `department`: e.g., "Finance", "IT"
   - `status`: OPEN | PENDING_REVIEW | RESOLVED
   - `limit`: default 20
2. For detailed context on specific violations, call `get_violation_details(violation_id=<id>)`.
3. For a statistical overview first, call `get_violation_stats` (returns counts by severity and department).
4. Format results: group by severity, show user name, conflicting roles/permissions, risk score, and days open.

---

### Workflow 3: User Risk Profile ("What's John Smith's compliance status?")

Use when: user asks about a specific person's access risk, violations, or role set.

**Steps:**
1. Call `get_user_violations(user_identifier=<name or email>)`.
2. The response includes: current roles, all violations, individual risk score (0–100), violation severity breakdown.
3. If violations exist, call `get_violation_details` for each CRITICAL/HIGH one.
4. Summarize: overall risk tier (High/Medium/Low/Compliant), violation count by severity, top conflicting role pairs, recommended next action (remediate, schedule review, or document compensating control).

---

### Workflow 4: Exception Management ("Request an exception for Jane's AP conflict")

Use when: user wants to approve, request, view, or revoke a SOD exception.

**Steps for requesting an exception:**
1. Call `get_user_violations(user_identifier=<user>)` to confirm the violation exists and get the `violation_id`.
2. Call `check_my_approval_authority` to confirm you/the requestor has authority for this severity.
3. Call `request_exception_approval` with:
   - `violation_id`: from step 1
   - `business_justification`: required — ask the user for this if not provided
   - `compensating_controls`: describe the controls that mitigate the risk
   - `expiry_date`: ISO date string (default: 90 days from today)
4. Confirm success and return the exception ID.

**Steps for listing active exceptions:**
1. Call `list_active_exceptions` (optionally filter by user or department).

**Steps for approving a pending exception:**
1. Call `get_exception_details(exception_id=<id>)` to review it.
2. Call `approve_exception(exception_id=<id>, approval_notes=<notes>)`.

---

### Workflow 5: Compliance Report ("Generate the weekly executive SOD report")

Use when: user asks for a compliance summary, department breakdown, or executive report.

**Steps:**
1. Call `get_violation_stats` to get current counts by severity and department.
2. Call `get_org_risk_assessment` for organization-wide risk scores.
3. Call `generate_compliance_report` with:
   - `report_type`: executive_summary | detailed_analysis | department_report | audit_report
   - `audience`: executives | compliance_team | auditors | department_heads
   - `department` (optional): filter to a specific department
4. Present the report. For executive audience, lead with the compliance rate percentage and top 3 action items.

---

### Workflow 6: SOD Rule Lookup ("What SOD rules cover AP approvals?")

Use when: user asks about specific rules, what permissions conflict, or rule severity.

**Steps:**
1. Call `list_sod_rules` to get all 18 active rules with severity.
2. For keyword search, call `query_sod_rules(keyword=<term>)`.
3. For full detail on a specific rule, call `get_sod_rule_details(rule_code=<code>)`.
4. The rule detail includes: conflicting permission pairs, example violation scenarios, recommended compensating controls.

Consult `references/sod-rules.md` for the full rule table — useful for quickly identifying which rule applies without a tool call.

---

### Workflow 7: Remediation ("Fix John's violation" / "Schedule a review")

Use when: user wants to act on an existing violation.

**Steps:**
1. Confirm violation ID: call `get_violation_details(violation_id=<id>)` if not already known.
2. Choose action:
   - **Role removal**: call `remediate_violation(violation_id=<id>, action="remove_role", role_to_remove=<role>)`
   - **Schedule review**: call `schedule_review(violation_id=<id>, review_date=<ISO date>)`
   - **Notify manager**: call `notify_manager(user_id=<id>, violation_id=<id>)`
   - **Create ticket**: call `create_remediation_ticket(violation_id=<id>, ticket_system="jira")`
3. Confirm the action and tell the user the expected resolution timeline (CRITICAL: immediate; HIGH: 30 days; MEDIUM: 90 days).

---

### Workflow 8: NetSuite Sync ("Sync latest data from NetSuite")

Use when: user wants to refresh compliance data from NetSuite.

**Steps:**
1. Call `get_sync_status` to check when the last sync ran and if one is in progress.
2. If a sync is already running, report its status and estimated completion.
3. Otherwise, call `trigger_manual_sync(sync_type="full")` for full sync or `sync_type="incremental"` for recent changes only.
4. Report: sync triggered, expected duration (~5 min for full, ~1 min for incremental), and how to check status again.

---

## Performance Notes

- Take time to fetch all relevant data before synthesizing an answer
- Run referenced workflow steps completely — do not skip verification steps
- Quality of compliance decisions matters more than response speed
- Do not skip the MCP Health Check when tools are unresponsive

---

## Examples

### Example 1: Role assignment decision

User: "Can we assign the Controller role to Austin Chen?"

Actions:
1. `initialize_session` → confirm user context
2. `get_user_violations(user_identifier="Austin Chen")` → get user ID + current roles
3. `analyze_access_request(user_id=<id>, requested_role="Controller", include_existing_roles=true)` → 249 conflicts
4. `get_compensating_controls` for top CRITICAL conflicts

Result: "DENIED — 249 SOD conflicts detected (HIGH risk). Austin's existing AP Processor role combined with Controller creates 3 CRITICAL conflicts: AP Entry vs AP Approval, Create Vendor vs Approve Vendor, and Journal Entry vs Journal Approval. These represent direct fraud pathways. If this access is required, contact your compliance officer to document compensating controls."

---

### Example 2: Department violation summary

User: "How many violations does Finance have?"

Actions:
1. `get_violation_stats` → Finance: 28 violations
2. `list_violations(department="Finance", severity="CRITICAL")` → 3 CRITICAL

Result: "Finance has 28 open violations: 3 CRITICAL, 8 HIGH, 12 MEDIUM, 5 LOW. The 3 CRITICAL violations involve AP Entry + AP Approval conflicts and require immediate remediation."

---

### Example 3: Exception approval

User: "Approve exception EX-2024-001 for the Finance controller"

Actions:
1. `get_exception_details(exception_id="EX-2024-001")` → review justification
2. `check_my_approval_authority` → confirm sufficient authority
3. `approve_exception(exception_id="EX-2024-001", approval_notes="Business necessity confirmed; monthly reconciliation review in place as compensating control")`

Result: "Exception EX-2024-001 approved. Valid for 90 days (expires 2026-05-18). Compensating control documented."

---

## Observability

Three online evaluators run automatically in LangSmith on every trace:

| Evaluator | Type | Fires on | Fail signal |
|-----------|------|----------|-------------|
| `mcp_tool_called` | Custom code | Every trace | Score = 0 |
| `mcp_tool_coverage` | Custom code | Access-request traces | Score = 0 |
| `hallucination_heuristic` | Custom code | Every trace | Score = 0 |

### Evaluator logic (3-layer detection)

Each evaluator checks in priority order:

**Layer 1 — Tool child runs** (primary, definitive)
`call_mcp_tool()` is decorated with `@traceable(run_type="tool")`, so every MCP call creates
a `tool`-type child span. Evaluators check `child_runs[*].run_type == "tool"` first.

**Layer 2 — Raw `<tool_call>` XML in output** (hallucination signal)
If the response contains `<tool_call>` or `<tool_result>` markup, Claude generated tool calls
as text without executing them. This is always a failure. Score = 0 on both `mcp_tool_called`
and `hallucination_heuristic`.

**Layer 3 — Data-grounding markers** (fallback for pre-v1.3 traces)
If no tool child runs and no XML markup, scan the output for markers that only appear in
live-data responses: `netsuite role`, `approval authority`, `sod conflict`, `risk score`, etc.

### What each score means

**`mcp_tool_called` = 0** — the agent answered without executing any MCP tool.
Check: did `call_mcp_tool()` run? Is the MCP server up? Does the output contain `<tool_call>` XML?

**`mcp_tool_coverage` = 0** — an access-request query was answered without calling
`analyze_access_request`. This means the conflict check was skipped entirely.

**`hallucination_heuristic` = 0** — the response either contained `<tool_call>` XML
(fabricated calls) or stated specific numeric claims (violation counts, risk scores) with
no grounding evidence. Open the trace and verify the numbers against tool results.

### Key architecture note

LangSmith's evaluator executor receives raw API run data. Child LLM `outputs.generations`
are stored in S3 and are **not** available inline — evaluators cannot read them. This is why
`call_mcp_tool()` must be `@traceable(run_type="tool")`: it creates a child span the
evaluator CAN see without needing S3 access.

---

## Troubleshooting

**Error: "Connection refused" or tool timeouts**
Cause: MCP server not running.
Solution: `cd compliance-agent && python3 -m mcp.mcp_server > /tmp/mcp_server.log 2>&1 &`

**Error: "User not found"**
Cause: Name doesn't exactly match NetSuite record.
Solution: Try email address instead, or call `list_all_users(search=<partial name>)` to find the correct identifier.

**Error: "0 conflicts" on access review that should have conflicts**
Cause: `include_existing_roles` was not set to true.
Solution: Always pass `include_existing_roles: true` to `analyze_access_request`.

**Error: "Insufficient approval authority"**
Cause: The current session user cannot approve exceptions at this severity level.
Solution: Call `check_my_approval_authority` to see your approval limits, then escalate to a user with sufficient authority.

**Stale violation data**
Cause: NetSuite sync hasn't run recently.
Solution: Call `get_sync_status` to check last sync time, then `trigger_manual_sync(sync_type="incremental")`.

**Evaluator scores all = 0 or AttributeError in LangSmith**
Cause: Evaluator code tried to read `child_run.outputs.generations` — these are stored in S3
and are not available in the inline API response the evaluator executor receives.
Solution: Use `child_run.run_type == "tool"` to detect MCP calls (requires `@traceable(run_type="tool")`
on `call_mcp_tool()`). Never try to parse LLM generation outputs inside an evaluator.

**Evaluator shows `<tool_call>` XML hallucination but bot is running normally**
Cause: `process_with_claude()` was called outside the Slack event context (e.g., a test script)
before `llm.bind_tools(MCP_TOOLS)` ran. Claude fell back to outputting raw tool call markup.
Solution: Always trigger test traces through the actual Slack bot, not by calling
`process_with_claude()` directly from a standalone script.
