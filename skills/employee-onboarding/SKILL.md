---
name: employee-onboarding
description: NetSuite role assignment approval routing triggered by Jira tickets. Use when a Jira ticket is created containing keywords like "Assign role", "Fivetran-", or a NetSuite role name paired with a user email. Reads ticket metadata, resolves the requester's NetSuite authority, runs an SOD compliance check on the requested role, and routes to the correct approver (Manager, Controller, or CFO) based on requester permissions and violation severity. Does NOT orchestrate Okta/Workday/Celigo provisioning — that is a separate automated flow.
metadata:
  author: Prabal Saha
  version: 2.1.0
  compatibility: "Claude Code, Claude.ai — requires compliance MCP server at localhost:8080"
  mcp-server: compliance-system
---

# Employee Onboarding — Role Assignment Approval Routing

## Instructions

This skill is triggered when a Jira ticket is created with role assignment intent.
It does not orchestrate system provisioning (Okta → Workday → Celigo → NetSuite).
That flow is handled by Celigo integrations automatically.

**This skill's sole job:**
1. Parse the Jira ticket to extract role, target user, and requester
2. Determine the requester's authority level in NetSuite
3. Run an SOD compliance check on the requested role
4. Route the ticket to the correct approver based on authority + risk

This skill applies five design patterns:
- **Pattern 1 — Sequential Orchestration**: parse → authority check → SOD check → route, in strict order
- **Pattern 2 — Multi-MCP Coordination**: Jira metadata feeds NetSuite lookups; SOD result feeds routing decision
- **Pattern 3 — Iterative Refinement**: if routing is ambiguous, escalate one level up and re-evaluate
- **Pattern 4 — Context-Aware Tool Selection**: approval chain determined by requester's role, requested role's risk tier, and department
- **Pattern 5 — Domain-Specific Intelligence**: SOX approval authority rules, financial role segregation, and Controller as the default approver for NetSuite financial roles

Consult `references/approval-chain.md` for the full authority matrix.
Consult `references/role-matrix.md` for role definitions and risk tiers.

---

## Critical

CRITICAL: Self-approval is never permitted. If the requester and target user are the same
person, immediately escalate to the requester's manager regardless of authority level.
Add comment to Jira: "Self-approval not permitted per SOX policy."

CRITICAL: Financial roles (AP, GL, Controller, Journal Entry) always require minimum
Controller (L4) approval — even if the requester already holds L4+ authority, always
add Controller as reviewer for the audit trail.

CRITICAL: Always pass `include_existing_roles: true` to `analyze_access_request`.
Never analyze a requested role in isolation from the user's existing roles.

---

### Step 1: Parse the Jira Ticket (Pattern 1 + 2)

Extract the following fields from the Jira ticket:

| Field | How to identify |
|---|---|
| **Target user** | Email address in the ticket (e.g., `abc@fivetran.com`) |
| **Requested role** | NetSuite role name or code (e.g., `Fivetran-Controller`, `Fivetran-AP-Approver`) |
| **Requester** | `reporter` field in Jira metadata — the person who created the ticket |
| **Ticket ID** | Jira issue key (e.g., `NS-ONBOARD-1042`) |
| **Justification** | Description field — business reason for the role assignment |

**Trigger keywords to match (case-insensitive):**
- `"Assign role"`
- `"Fivetran-"` followed by a role name
- `"NetSuite role"` + email address
- `"Enable user"` + role name

If any of these fields are missing or ambiguous, comment on the Jira ticket asking for clarification before proceeding. Do not route an incomplete request.

---

### Step 2: Resolve the Target User in NetSuite (Pattern 2)

Look up the target user to confirm they exist and get their current role set:

1. Call `get_user_violations(user_identifier={target_email})`
   - Confirms the user exists in NetSuite
   - Returns current roles and any existing violations
   - If user not found: comment on Jira ticket — "Target user not found in NetSuite. Confirm user has been provisioned before submitting a role assignment request."

---

### Step 3: Determine the Requester's Authority Level (Pattern 4 + 5)

Look up the person who raised the Jira ticket to determine what they are authorized to approve:

1. Call `get_user_violations(user_identifier={requester_email})` — returns requester's current NetSuite roles
2. Call `check_my_approval_authority` — returns the requester's approval authority tier
3. Map to authority level using `references/approval-chain.md`:

```
Authority Levels:
  L1 — Regular employee / IT Analyst     → Can REQUEST only, cannot approve
  L2 — Manager / Team Lead               → Can approve LOW risk roles
  L3 — Senior Manager / Director         → Can approve MEDIUM risk roles
  L4 — Controller / VP Finance           → Can approve HIGH risk roles
  L5 — CFO / C-Suite                     → Can approve CRITICAL risk roles
```

**Key rule (Pattern 5 — Domain Intelligence):**
- Financial roles (AP Approval, GL Full Access, Controller, Journal Entry Approval) always require minimum L4 (Controller) regardless of the requester's level
- Compliance roles require the Compliance Officer to sign off independently
- IT Admin / Script Deploy roles require IT Director (L4 equivalent in IT)

---

### Step 4: Run SOD Compliance Check (Pattern 3 — Iterative)

1. Call `analyze_access_request(user_id={target_user_id}, requested_role={role}, include_existing_roles=true)`
2. Evaluate the result:

```
Result: CLEAR or LOW
  → Proceed to Step 5 with required approver from authority matrix

Result: MEDIUM
  → Proceed to Step 5 — flag in ticket, note compensating controls required

Result: HIGH
  → Proceed to Step 5 — escalate to minimum L4 (Controller) regardless of requester level
    If requester is already L4+, proceed with their approval

Result: CRITICAL
  → Escalate to L5 (CFO) — comment on Jira ticket with full SOD conflict details
    Do not route to Controller for CRITICAL violations

Result: Multiple conflicts (Pattern 3 — Iterative)
  → For each conflict: call get_compensating_controls(violation_id)
  → If compensating controls exist for all conflicts: document in ticket, proceed to L4
  → If no compensating controls available for any CRITICAL conflict: reject ticket,
    comment explaining why the role cannot be assigned
```

---

### Step 5: Route to Correct Approver (Pattern 4)

Based on the requester's authority level (Step 3) and the SOD risk result (Step 4),
determine the required approver using this decision tree:

```
Requested role is financial (AP, GL, Controller, Journal)?
  └─ YES → Minimum approver: Controller (L4), regardless of requester level
  └─ NO  → Continue below

SOD result is CRITICAL?
  └─ YES → Route to CFO (L5)

SOD result is HIGH?
  └─ YES → Route to Controller (L4)

Requester authority ≥ required level for this risk tier?
  └─ YES → Requester can self-approve → still add Controller as reviewer for audit trail
  └─ NO  → Route to next authority level above requester
```

**Routing actions:**
1. Assign the Jira ticket to the determined approver
2. Add a comment to the Jira ticket with:

```
*SOD Compliance Check — [ticket ID]*

Target user: {email}
Requested role: {role name}
Requested by: {requester email} (Authority level: L{n})

SOD Result: {CLEAR / LOW / MEDIUM / HIGH / CRITICAL}
Violations found: {count} — {brief description or "None"}

*Routing decision:*
Required approver: {name / role title}
Reason: {one sentence — e.g., "Financial role requires minimum Controller approval per SOX policy"}

Compensating controls required: {Yes / No}
{If yes: list them}

Next step: {Approver name}, please review and approve/deny in this ticket.
If approved, assign roles in NetSuite and set isInactive: false if not already active.
```

---

### Step 6: Post-Approval — Execute Role Assignment and Enable User

Once the Jira ticket status moves to `Approved` (or the approver comments "Approved"):

1. **Assign the role in NetSuite**
   - Call `validate_job_role(user_id={target_user_id}, job_title={title}, proposed_roles=[{approved_role}])`
   - Confirms the role is safe to assign given current role set
   - If validation passes: assign role via NetSuite REST API:
     ```
     PATCH /services/rest/record/v1/employee/{internalId}
     { "roles": [{ "role": { "id": "{roleId}" } }] }
     ```

2. **Enable the user in NetSuite** (if not already active)
   - Call `get_user_violations(user_identifier={email})` — check current `isInactive` status
   - If `isInactive: true`: set `isInactive: false`
     ```
     PATCH /services/rest/record/v1/employee/{internalId}
     { "isinactive": false }
     ```
   - If already active: skip, proceed to step 3

3. **Run final SOD verification**
   - Call `analyze_access_request(user_id={id}, requested_role={role}, include_existing_roles=true)`
   - Confirm result is still CLEAR/LOW now that the role is live
   - If a new conflict appears (e.g., another role was assigned between approval and execution): pause, comment on Jira ticket, re-route to approver

4. **Close the Jira ticket** with a completion comment:

```
*Role Assignment Complete — [ticket ID]*

User: {email}
Role assigned: {role name}
NetSuite status: Active
Final SOD check: {CLEAR / LOW — no violations}

Completed by: Compliance Agent
Timestamp: {ISO datetime}
```

5. **Trigger incremental sync** to ensure compliance DB reflects the new role:
   - Call `trigger_manual_sync(sync_type="incremental")`

---

## Performance Notes

- Parse the Jira ticket completely before calling any MCP tools
- Run all 6 steps in order — do not skip the post-approval SOD re-verification
- Quality of routing decisions is more important than speed; wrong routing = audit finding
- If any field is ambiguous, comment on the Jira ticket and wait — never guess

---

## Examples

### Example 1: Standard financial role request

Jira ticket: "Assign role Fivetran-AP-Approver to sarah.chen@fivetran.com"
Requester: mike.torres@fivetran.com (Accounting Manager, L3)

Steps:
1. Parse: target = sarah.chen, role = AP-Approver, requester = mike.torres
2. `get_user_violations("sarah.chen@fivetran.com")` → user found, current roles: AP Processor
3. `get_user_violations("mike.torres@fivetran.com")` → L3 authority (Senior Manager)
4. `analyze_access_request` → HIGH risk (AP Processor + AP Approver = CRITICAL SOD violation)
5. Result: CRITICAL SOD conflict → escalate beyond L4
6. Route: assign ticket to CFO. Comment: "AP Entry + AP Approval is a CRITICAL SOD conflict. Cannot be assigned without CFO approval and documented compensating controls."

---

### Example 2: Low-risk IT role request

Jira ticket: "Assign role Fivetran-Report-Viewer to james.park@fivetran.com"
Requester: lisa.nguyen@fivetran.com (IT Director, L4)

Steps:
1. Parse: target = james.park, role = Report-Viewer, requester = lisa.nguyen
2. `get_user_violations("james.park@fivetran.com")` → user found, current roles: Employee Center
3. `get_user_violations("lisa.nguyen@fivetran.com")` → L4 authority
4. `analyze_access_request` → CLEAR (no conflicts)
5. Route: Lisa (L4) has sufficient authority. Assign ticket back to her for self-approval.
6. Comment: "SOD check CLEAR. Lisa Nguyen (L4) has authority to approve. Assign role and close ticket."

---

## Troubleshooting

**Requester not found in NetSuite**
Cause: Ticket raised by someone who is not a NetSuite user (e.g., HR or external party).
Solution: Default to L1 (no approval authority). Route to the requester's manager for sponsorship, then re-evaluate.

**Role name not recognized**
Cause: Ticket uses an informal name (e.g., "Controller access" instead of "Fivetran-Controller").
Solution: Call `search_permissions(search_term={role_name_from_ticket})` to fuzzy-match to a known role. If no match, comment on ticket asking for the exact NetSuite role name.

**Multiple roles requested in one ticket**
Cause: Ticket says "Assign roles Fivetran-AP-Processor and Fivetran-AP-Approver to user X".
Solution: Run `analyze_access_request` with ALL requested roles together. A combination that is individually safe may be CRITICAL together. Route based on the highest severity result.

**Requester and target user are the same person**
Cause: User requesting their own elevated access.
Solution: Flag immediately. Self-approval is a SOD violation. Route to the requester's manager minimum, regardless of the requester's authority level. Add comment: "Self-approval not permitted per SOX policy. Escalated to manager."
