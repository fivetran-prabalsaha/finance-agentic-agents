# Claude Code Skill File Template (SKILL.md)

**Version:** 1.0
**Purpose:** Reusable template for writing Claude Code skill files — the per-skill instruction documents that tell Claude exactly how to behave when a specific capability is invoked.
**Based on:** The `sod-compliance` and `employee-onboarding` skills (Feb 2026).

---

## How to Use This Template

1. Copy this file to `~/.claude/skills/{{SKILL_NAME}}/SKILL.md`
2. Fill in every `{{PLACEHOLDER}}` — never leave them blank
3. Delete sections that do not apply (e.g. no MCP server → remove the health check section)
4. Keep the Non-Negotiable Rules section ruthlessly short — five rules maximum
5. Test each trigger phrase by sending it to Claude Code and confirming the skill activates

**Where skill files live:**

Skill files are loaded automatically by Claude Code from `~/.claude/skills/<skill-name>/SKILL.md`. The directory name must match the `name` field in the frontmatter YAML. Claude Code discovers all skills in `~/.claude/skills/` at startup and uses the `description` field of each skill to decide which one to activate for a given user query.

**What this template is NOT:**

This template is for skill files — per-capability instruction documents. It is not for multi-agent orchestration playbooks (see `CLAUDE_MULTI_AGENT_TEMPLATE.md` for that). A skill file describes how Claude should behave; a multi-agent playbook describes how multiple Claude agents should coordinate.

---

## Part 1 — File Header

A skill file has no title section of its own inside the YAML — the `name` field in frontmatter is the canonical identifier. The first heading after the YAML block should be a human-readable skill title followed immediately by a one-paragraph purpose statement that answers three questions:

1. What does this skill do?
2. What does it explicitly NOT do (scope boundary)?
3. What external systems or tools does it require?

**Template:**

```markdown
# {{SKILL_TITLE}}

## What This Skill Does

{{One paragraph. State the single job this skill performs, the systems it touches,
and one clear boundary — what it does NOT handle. See the employee-onboarding skill
for the canonical example of a tight scope statement.}}
```

**Example (from `employee-onboarding`):**

```markdown
# Employee Onboarding — Role Assignment Approval Routing

## What This Skill Does

One job: take a Jira role-assignment ticket → run SOD + authority checks → route to
the right approver with a structured comment.

It does NOT provision accounts in Okta, Workday, or Celigo. Those flows are automated.
This skill handles the compliance gating that must happen before provisioning.
```

The scope boundary sentence ("It does NOT...") is not optional. Without it, Claude will attempt to do adjacent things the skill was not designed or tested for.

---

## Part 2 — Frontmatter YAML

Every skill file must begin with a YAML frontmatter block. This block is the machine-readable metadata Claude Code uses for skill routing, version tracking, and dependency declaration.

```yaml
---
# REQUIRED — slug in kebab-case. Must exactly match the directory name
# under ~/.claude/skills/. Example: ~/.claude/skills/sod-compliance/SKILL.md
name: {{skill-name}}

# REQUIRED — the single most important field. Claude Code reads this description
# to decide whether to activate this skill for a given user query. Write it as
# one or two sentences. It must mention: (1) the trigger conditions, (2) what the
# skill does, and (3) any required infrastructure (MCP server, API, etc.).
description: "{{What this skill does and when to use it. Include trigger keywords.
  Mention required infrastructure. 1–2 sentences maximum.}}"

metadata:
  # Who owns this skill. Use team name or individual.
  author: {{Author or Team Name}}

  # Semantic version. Increment MINOR for new workflows, PATCH for fixes,
  # MAJOR for breaking changes to trigger phrases or tool signatures.
  version: {{1.0.0}}

  # ISO 8601 date of last meaningful change to workflows or rules.
  updated: {{YYYY-MM-DD}}

  # Which Claude surfaces this skill works on. Always list Claude Code.
  # If it requires an MCP server, say so here — it will not work without it.
  compatibility: "Claude Code, Claude.ai — {{any required server or dependency}}"

  # OPTIONAL — name of the MCP server this skill requires. Must match the
  # server name registered in the Claude Desktop or Claude Code MCP config.
  # Omit this field entirely if the skill needs no MCP server.
  mcp-server: {{mcp-server-name}}

  # OPTIONAL — number of MCP tools this skill can call. Useful for auditing
  # whether Claude is routing correctly and for documentation purposes.
  tools: {{N}}
---
```

### The `description` field — the most important field

Claude Code uses the `description` to decide whether to activate a skill. A vague description means the skill will either never activate or activate for the wrong queries.

**✅ Good description:**

```yaml
description: "NetSuite role assignment approval routing triggered by Jira tickets.
  Use when a Jira ticket contains 'Assign role', 'Fivetran-', or a NetSuite role name
  paired with a user email. Parses the ticket, resolves the requester's NetSuite
  authority level (L1–L5), runs a full SOD compliance check against the user's
  existing roles, and routes to the correct approver — Manager, Controller, or CFO —
  based on risk severity. Does NOT orchestrate Okta/Workday/Celigo provisioning;
  that is a separate automated flow."
```

This description works because it names the input format (Jira ticket), the exact trigger phrases, the key actions, and the explicit out-of-scope boundary.

**❌ Bad description:**

```yaml
description: "Handles compliance-related tasks for role assignments and user access."
```

This fails because it gives Claude no signal about when to activate it versus any other compliance skill, it lists no trigger phrases, and it says nothing about what infrastructure is required. Claude Code will either never activate this skill or activate it for every compliance question regardless of whether it is appropriate.

**Rule:** If your description does not contain at least one specific trigger condition and one mention of required infrastructure (if any), rewrite it.

---

## Part 3 — Non-Negotiable Rules Section

### When to use this section

The Non-Negotiable Rules section is for hard constraints that Claude must never violate regardless of what the user says, what other instructions exist, or what seems locally reasonable. These are not guidelines, preferences, or defaults — they are invariants.

Use this section when:
- Omitting a parameter produces silently wrong results (not an error — wrong results)
- A specific persona, voice, or identity constraint must hold across all responses
- A security or compliance boundary must never be crossed (e.g. self-approval prohibition)
- A specific phrasing is forbidden because it misrepresents the system

Do not use this section for:
- Workflow steps (those go in the workflow sections)
- Troubleshooting guidance (that goes in a Troubleshooting section)
- Preferences or style suggestions (those go in workflow-specific notes)

**Maximum 5 rules.** If you find yourself writing a sixth rule, you have a guideline, not a rule. Move it to the relevant workflow section.

### Format

```markdown
## Non-Negotiable Rules

These apply to every workflow. Violation causes {{consequence}}.

**{{THE RULE STATED AS A SHORT IMPERATIVE SENTENCE.}}** {{One or two sentences explaining
why this rule exists and what goes wrong if it is violated. Be specific about the failure
mode — vague explanations are ignored.}}

**{{RULE 2.}}** {{Explanation with specific failure mode.}}

**{{RULE 3.}}** {{Explanation with specific failure mode.}}
```

### Template (fill in your rules)

```markdown
## Non-Negotiable Rules

These apply to every workflow. Violation causes wrong answers or data loss.

**{{RULE 1 — e.g. NEVER answer questions from memory.}}** {{Explanation of why live
tool calls are required and what training-data staleness looks like in practice.}}

**{{RULE 2 — e.g. ALWAYS pass `include_existing_roles: true` to `analyze_access_request`.}}**
{{Explanation of what happens when this is omitted — name the silent failure.}}

**{{RULE 3 — e.g. NEVER allow self-approval.}}** {{Explanation of the compliance or
security boundary being protected and what to do instead.}}
```

### Real examples of well-written rules

From `sod-compliance`:

> **NEVER answer compliance questions from memory.** Every violation count, role name, risk score, and conflict must come from a live MCP tool call. Training data is stale and wrong.

> **ALWAYS pass `include_existing_roles: true` to `analyze_access_request`.** Omitting it analyzes the new role in isolation — produces false "0 conflicts" for users who already hold conflicting roles. This is the single most common silent failure.

From `employee-onboarding`:

> **Self-approval is never permitted.** If the requester and target user are the same person, immediately escalate to the requester's manager regardless of authority level. Comment on Jira: "Self-approval not permitted per SOX policy. Escalated to manager."

Notice the pattern: **Rule stated in bold** followed by the specific failure mode in plain text. The failure mode is concrete — "produces false '0 conflicts'" is more actionable than "may produce incorrect results."

---

## Part 4 — Trigger Phrases / Activation Section

### Purpose

Trigger phrases tell Claude Code when to activate this skill. They are the bridge between a user's natural-language message and the skill's structured workflows.

### Important: how Claude Code matches triggers

Claude Code uses **semantic matching**, not exact string matching. A trigger phrase of `"Can user X get role Y?"` will also activate the skill for `"Is it safe to assign the Controller role to Sarah?"` — the phrasing is different but the intent is the same. This means:

- Specific phrases are better than vague ones, even though exact matching is not required
- Phrases that name the objects being acted on (role names, ticket IDs, user emails) help disambiguation when multiple skills could match
- Overlapping triggers across two skills will cause routing ambiguity — differentiate them

**What happens if a skill has no trigger section:** The skill will not be auto-activated. The user must invoke it manually (e.g. `/sod-compliance` or by explicitly asking Claude to use the skill). If your skill is meant to activate automatically, the trigger section is required.

### Format

Use one of two heading styles depending on whether your skill has a single activation mode or multiple workflows with different triggers:

**Single-mode skill (one set of triggers for the whole skill):**

```markdown
## Trigger Phrases

Activate this skill when the user's message contains any of:

- `"{{exact phrase or pattern}}"` — {{optional note on what variation is also matched}}
- `"{{phrase}}"` + {{qualifier, e.g. "a user email address"}}
- `"{{phrase}}"` + `"{{secondary keyword}}"`
- {{Pattern note: e.g. any reference to "NetSuite role" combined with an email}}
```

**Multi-workflow skill (each workflow has its own triggers):**

List the global activation triggers at the top level, then repeat relevant sub-triggers inside each workflow section. See Part 5 for the per-workflow trigger format.

### Real example (from `employee-onboarding`)

```markdown
## Trigger Keywords

Activate this skill when a Jira ticket contains any of:

- `"Assign role"` + a user email
- `"Fivetran-"` followed by a role name
- `"NetSuite role"` + email
- `"Enable user"` + role name
- `"Grant access"` + `"NetSuite"` or `"Fivetran-"`
```

Note how the `employee-onboarding` skill pairs keywords with qualifiers (e.g. `"Assign role"` + a user email) rather than listing bare keywords. This prevents false activation on messages like "what roles exist?" which contains no assignment intent.

### Template

```markdown
## When to Activate This Skill

Activate this skill when the user's message contains any of:

- `"{{trigger phrase 1}}"` {{+ qualifier if needed}}
- `"{{trigger phrase 2}}"` {{+ qualifier if needed}}
- `"{{trigger phrase 3}}"` {{+ qualifier if needed}}
- {{Any reference to {{domain concept}} combined with {{action keyword}}}}

Do NOT activate this skill for: {{list 1–2 adjacent topics this skill does NOT cover,
to help Claude distinguish it from related skills.}}
```

---

## Part 5 — Workflow Definitions

Each discrete task the skill performs gets its own workflow section. A workflow is a numbered sequence of steps that Claude must follow in order to complete a specific type of request.

### Section structure

```markdown
## Workflow {{N}}: {{Name}}

**Trigger phrases:** "{{phrase 1}}", "{{phrase 2}}", "{{phrase 3 with variable}}"

**Steps:**
1. {{Tool call or action}} — {{what it returns or why it is needed}}
2. {{Tool call or action}} — {{what it returns or why it is needed}}
3. {{Conditional step}} — see decision table below
4. {{Response format instruction}}

**Decision table:**

| {{Condition}} | {{Action}} |
|--------------|-----------|
| {{Case 1}}   | {{What to do}} |
| {{Case 2}}   | {{What to do}} |
| {{Case 3}}   | {{What to do}} |

**Key rule:** {{The single most important constraint for this workflow. Bold this
paragraph. If there is only one thing Claude can get wrong, it is this.}}
```

### Format notes

- **Numbered steps, not bullets.** Order matters in workflows. Bullets imply the steps can be done in any order; numbers make sequencing explicit.
- **Decision tables for conditional logic.** Prose conditionals ("if X do Y, unless Z, in which case do W") are harder to follow correctly than a table with one row per case.
- **Trigger phrases in each workflow.** In a multi-workflow skill, each workflow lists only the phrases that activate it specifically — not the global skill triggers.
- **Code blocks for exact tool signatures.** When a tool call has a required parameter or a specific argument format, show the exact call in a code block.
- **Key rule callout.** One bold paragraph per workflow naming the single constraint that is most commonly violated. If a rule applies to all workflows, it belongs in Non-Negotiable Rules instead.

### Filled-in example: Access Review workflow (from `sod-compliance`)

```markdown
## Workflow 1: Access Review

**Trigger phrases:** "Can user X get role Y?", "assign role", "would this create a conflict",
"is it safe to give", "access request", "onboard with role"

**Steps:**
1. `initialize_session` — load compliance context
2. `get_user_violations(user_identifier=<name or email>)` — get canonical user ID + current roles
3. `analyze_access_request(user_id=<id>, requested_role=<role>, include_existing_roles=true)`
4. If CRITICAL or HIGH conflicts: `get_compensating_controls(violation_id=<id>)` for each
5. Respond with verdict first: **APPROVED / CONDITIONAL / DENIED**
   - List each conflict: severity, two clashing permissions, fraud risk
   - For CRITICAL: recommend rejection, name the fraud scenario
   - For HIGH: list compensating controls required to proceed

**Decision table:**

| SOD result    | Response verdict  | Required action                                              |
|---------------|-------------------|--------------------------------------------------------------|
| CLEAR / LOW   | APPROVED          | State approval. No additional controls required.             |
| MEDIUM        | CONDITIONAL       | State conditions. Note compensating controls required.       |
| HIGH          | CONDITIONAL       | Escalate to minimum L4 (Controller). List required controls. |
| CRITICAL      | DENIED            | Recommend rejection. Name the specific fraud scenario.       |

**Key rule:** Step 3 must always include `include_existing_roles: true`.
Without it, the analysis only checks the new role — misses all existing role combinations.
This is the single most common silent failure in access review queries.
```

### Multi-step call sequence example

When a workflow requires a specific sequence of calls where each call depends on the result of the previous one, show it as a linear chain with annotations:

```markdown
**Steps:**
1. `get_user_violations(user_identifier={target_email})`
   → returns: user_id, current_roles[], existing_violations[]

2. `get_user_violations(user_identifier={requester_email})` + `check_my_approval_authority`
   → returns: requester L-tier (L1–L5)

3. `analyze_access_request(user_id={target_user_id}, requested_role={role}, include_existing_roles=true)`
   → returns: SOD result (CLEAR / LOW / MEDIUM / HIGH / CRITICAL), conflict list

4. If CRITICAL or HIGH: `get_compensating_controls(violation_id={id})` for each conflict
   → returns: controls[], whether controls exist for this conflict type
```

The `→ returns:` annotation after each step tells Claude what information to carry forward into the next step. Without it, Claude may call the steps in order but discard the outputs it needs.

---

## Part 6 — Before/During Workflow: Health Checks and Prerequisites

Every skill that depends on external infrastructure — an MCP server, a database, an API — must document how to verify that infrastructure is available before any workflow begins.

### When to run health checks

Claude should check infrastructure health:

1. At the start of any workflow, before the first tool call
2. When any tool call returns a connection error, timeout, or unexpected empty response
3. When a user reports stale data or unexpected results

### MCP server health check pattern

```markdown
## Before Any Workflow: MCP Health Check

If any tool call returns a connection error or timeout:

```
The {{SKILL_NAME}} MCP server is offline.
Restart: {{exact restart command, e.g.: cd compliance-agent && python3 -m mcp.mcp_server > /tmp/mcp_server.log 2>&1 &}}
Verify:  curl -s http://localhost:{{PORT}}/health
```
```

**Real example (from `sod-compliance`):**

```
The compliance MCP server is offline.
Restart: cd compliance-agent && python3 -m mcp.mcp_server > /tmp/mcp_server.log 2>&1 &
Verify:  curl -s http://localhost:8080/health
```

The message Claude shows the user must contain three things: a diagnosis ("the server is offline"), a restart command the user can copy-paste, and a verification command that returns a clear pass/fail signal. Do not write "please check if the server is running" — write the exact command.

### Database connection check pattern

If your skill requires a direct database connection (not mediated by an MCP server):

```markdown
## Before Any Workflow: Database Check

If queries return no results or connection errors:

```
Database connection failed.
Check: psql $DATABASE_URL -c "SELECT 1;"
If unreachable: verify DATABASE_URL in .env and that PostgreSQL is running.
Restart PostgreSQL: brew services restart postgresql  # macOS
                    sudo systemctl restart postgresql  # Linux
```
```

### Required environment variables

List every environment variable the skill depends on, grouped by category. If a variable is missing, the skill will fail silently or produce wrong results — Claude needs to know what to check.

```markdown
## Required Environment Variables

The following must be set in `.env` before this skill will work:

```bash
# {{Category 1 — e.g. MCP Server}}
{{VAR_NAME}}={{example_format}}   # {{what it is used for}}

# {{Category 2 — e.g. External API}}
{{VAR_NAME}}={{example_format}}

# {{Feature flags — list defaults}}
{{USE_FEATURE_X}}=true            # Set false to disable {{what it controls}}
```

If any of these are missing, {{describe the failure symptom — e.g. "tool calls will return 401 Unauthorized"}}. Check with: `cat .env | grep {{KEY_PREFIX}}`.
```

### Full prerequisites template

```markdown
## Prerequisites

Before activating any workflow, verify:

**1. MCP server running**
```bash
curl -s http://localhost:{{PORT}}/health
# Expected: {"status": "ok"} or HTTP 200
# If offline: {{restart command}}
```

**2. Database reachable**
```bash
psql $DATABASE_URL -c "SELECT COUNT(*) FROM {{key_table}};"
# Expected: a count > 0
# If connection refused: check DATABASE_URL in .env
```

**3. Required environment variables present**
```bash
cat .env | grep -E "{{KEY_PREFIX_1}}|{{KEY_PREFIX_2}}"
# Must show non-empty values for all listed keys
```

If any prerequisite fails, stop and report the specific failure before attempting any workflow step. Do not proceed with partial infrastructure — the result will be wrong and may be silently wrong.
```

---

## Examples

### Example 1: Access review — role assignment decision (complete)

**User:** "Can we give Austin Chen the Controller role?"

**MCP tool calls, in order:**

```
1. initialize_session()
   → session_id=sess-8821, compliance context loaded

2. get_user_violations(user_identifier="Austin Chen")
   → user_id=u-4421
   → current roles: [Fivetran-AP-Processor, Fivetran-Employee-Center]
   → existing violations: 2 MEDIUM (AP Entry + GL View)

3. analyze_access_request(
     user_id="u-4421",
     requested_role="Fivetran-Controller",
     include_existing_roles=true
   )
   → result: DENIED
   → conflicts: 249 total — 3 CRITICAL, 11 HIGH, 47 MEDIUM, 188 LOW
   → CRITICAL conflict IDs: [viol-8810, viol-8811, viol-8812]

4. get_compensating_controls(violation_id="viol-8810")
   → conflict: AP Entry + AP Approval
   → controls: none available — direct fraud pathway, no mitigating control is sufficient

5. get_compensating_controls(violation_id="viol-8811")
   → conflict: Create Vendor + Approve Vendor
   → controls: none available

6. get_compensating_controls(violation_id="viol-8812")
   → conflict: Journal Entry + Journal Approval
   → controls: none available
```

**Synthesized response:**

"DENIED. Assigning Controller to Austin Chen creates 249 SOD conflicts, including 3 CRITICAL risks: AP Entry + AP Approval, Create Vendor + Approve Vendor, and Journal Entry + Journal Approval. Each is a direct fraud pathway — a single user could create, approve, and pay fictitious invoices with no second approver in the chain. No compensating controls exist for any of the three CRITICAL conflicts. If this access is genuinely required for business continuity, the only viable path is a CFO-level exception with independent transaction monitoring documented as a compensating control."

---

This example is complete because it:
- Uses a realistic user name (`Austin Chen`) and a real role name (`Fivetran-Controller`)
- Shows every tool call in execution order with actual parameters
- Includes `include_existing_roles=true` on `analyze_access_request`
- Shows the follow-up `get_compensating_controls` calls triggered by CRITICAL severity
- Leads the response with a single-word verdict (`DENIED`) before explanation
- Cites specific conflict names, not just counts

---

### Example 2: Thin example (what not to write)

Do not write examples like this:

```
User: "Check Austin's roles"

Tool call: get_user_violations(user="Austin")
Response: "Austin has some violations."
```

**Why this fails:**
- `user="Austin"` is not the correct parameter name (`user_identifier` is required)
- A partial first name is not a realistic identifier — use `"Austin Chen"` or `austin.chen@fivetran.com`
- The response "Austin has some violations" gives Claude nothing to pattern-match against
- No severity counts, no role names, no next-action recommendation
- Does not demonstrate the multi-step tool call pattern the skill requires

---

### Example 3: Employee onboarding — self-approval blocked

**User (Jira ticket NS-ONBOARD-1042):** "Assign role Fivetran-Controller to prabal.saha@fivetran.com — Requester: prabal.saha@fivetran.com"

**MCP tool calls, in order:**

```
1. Parse ticket fields:
   → target_user: prabal.saha@fivetran.com
   → requested_role: Fivetran-Controller
   → requester: prabal.saha@fivetran.com
   → ticket_id: NS-ONBOARD-1042

2. Self-approval check (no MCP call needed):
   → requester == target_user → BLOCK immediately
   → Do not call analyze_access_request or check_my_approval_authority
```

**Jira comment posted:**

"Self-approval not permitted per SOX policy. Escalated to prabal.saha@fivetran.com's direct manager for sponsorship and approval. Ticket NS-ONBOARD-1042 reassigned pending manager review."

**Why no further MCP calls are made:** The self-approval rule is a hard block. Running the SOD check first and then blocking wastes tool calls and implies the request might be approvable by a sufficiently senior reviewer — it is not. Self-approval is categorically rejected regardless of the requester's authority level.

---

### Example 4: Violation query — department breakdown

**User:** "How many violations does Finance have, and which are the most urgent?"

**MCP tool calls, in order:**

```
1. get_violation_stats()
   → Finance: 28 total (3 CRITICAL, 8 HIGH, 12 MEDIUM, 5 LOW)
   → Org-wide: 147 total

2. list_violations(department="Finance", severity="CRITICAL", limit=20)
   → 3 violations returned:
     - viol-0041: jenna.walsh@fivetran.com — AP Entry + AP Approval — 47 days open
     - viol-0042: derek.moss@fivetran.com — AP Entry + AP Approval — 31 days open
     - viol-0043: sarah.kim@fivetran.com — Journal Entry + Journal Approval — 12 days open
```

**Synthesized response:**

"Finance carries 28 open violations: 3 CRITICAL, 8 HIGH, 12 MEDIUM, 5 LOW. The 3 CRITICAL violations all involve AP Entry + AP Approval or Journal Entry + Journal Approval conflicts — the highest-priority remediation targets this quarter. Jenna Walsh's conflict is 47 days past due; immediate role removal or a CFO-approved exception is required. Recommend scheduling remediation reviews for all 3 CRITICAL violations this week."

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `Connection refused` / tool call times out | MCP server not running | `cd compliance-agent && python3 -m mcp.mcp_server > /tmp/mcp_server.log 2>&1 &` then verify with `curl -s http://localhost:8080/health` |
| `"User not found"` on `get_user_violations` | Name doesn't match NetSuite record exactly, or user hasn't been provisioned | Retry with email: `get_user_violations(user_identifier="first.last@fivetran.com")` — or use `list_all_users(search="partial name")` to find the canonical identifier |
| `analyze_access_request` returns `"0 conflicts"` when conflicts are expected | `include_existing_roles` was omitted — the call analyzed the new role in isolation | Re-run with `include_existing_roles=true` explicitly set. This is the single most common silent false-negative in access reviews. |
| `"Insufficient approval authority"` on `approve_exception` | The session user's NetSuite role does not meet the severity threshold | Call `check_my_approval_authority` to confirm your tier, then escalate to the correct approver role (L4 for HIGH, L5 for CRITICAL) |
| Violation counts appear lower than expected / data looks stale | NetSuite sync has not run recently | `get_sync_status` to check last sync time → `trigger_manual_sync(sync_type="incremental")` for a 1-minute refresh, or `sync_type="full"` for a 5-minute complete refresh |
| LangSmith evaluator scores show `0` on every trace | MCP tool calls are not being detected by evaluators | Verify `call_mcp_tool()` has the `@traceable(run_type="tool")` decorator. Without it, evaluators see no child tool spans and score 0 for every query. |
| Role risk matrix returns empty result set | `role_pair_conflicts` table has not been populated | Run `python3 scripts/build_role_risk_matrix.py` to rebuild the precomputed matrix |
| `<tool_call>` XML appears in the final Slack response | `process_with_claude()` was invoked before `llm.bind_tools()` completed | Always test new workflows via the Slack bot, not standalone scripts. Confirm `llm_with_tools` is the active model object before the agentic loop. |
| `"Self-approval not permitted"` appears unexpectedly | Requester email in the Jira ticket matches the target user email | Confirm both fields in the ticket. If they differ and the error still appears, check that the Jira `reporter` field is not auto-populated with the target user's email. |

**Rules for the Fix column:**
- Every fix must be a runnable command, a specific parameter to add, or a concrete escalation path.
- "Contact support" or "check the configuration" are not acceptable fixes.
- If the fix requires a shell command, show the exact command — not a description of what to run.

---

## Infrastructure and Memory Notes

Include this section when your skill runs on infrastructure with caching, conversation memory, or learning mechanisms. If your skill is stateless, omit this section entirely.

### When to include this section

Include it if any of these are true:
- The skill's MCP server caches tool results (Redis or in-memory TTL)
- The skill injects prior conversation context into queries
- The skill uses a correction or feedback loop to improve over time
- Tool results may be served from cache (users need to know how to bust stale data)

### Template

```markdown
## Infrastructure and Memory Notes

### Redis TTL Cache (Phase A)

MCP tool results are cached in Redis per tool. Cache key format: `mcp:{tool_name}:{md5(arguments)}`.

| Tool | TTL | Notes |
|------|-----|-------|
| `{{tool_name_1}}` | {{TTL, e.g. 1h}} | {{what is cached}} |
| `{{tool_name_2}}` | {{TTL}} | {{notes}} |
| `{{mutating_tool}}` | never cached | {{why: e.g. write operation}} |

Cache hits are observable in LangSmith: `metadata.context_cache_hit = true` on the root trace.
To bust the cache: a NEGATIVE feedback signal (`❌` button) automatically deletes all
`mcp:get_user_violations:*` keys for that user.
Feature flag: `USE_MCP_CACHE=false` in `.env` disables caching entirely.

### Conversation Summaries (Phase B)

After each exchange, a lightweight model (Haiku) writes a 2–3 sentence summary to the
`conversation_summaries` Postgres table. On the next query from the same user, the 3 most
recent non-expired summaries are injected into the system message as prior context.

- Storage: `conversation_summaries` table (user_email, summary, topics, outcome, expires_at 90d)
- Token cost: ~150 tokens per summary set vs ~2,000 tokens for raw conversation history
- Observable in LangSmith: `metadata.context_summaries_injected = N`
- Feature flag: `USE_CONV_SUMMARIES=false` in `.env` disables injection

### Correction Embeddings (Phase C)

When a user submits a correction via the `❌` feedback modal, the query + correction is
embedded ({{embedding model, e.g. MiniLM, 384-dim}}) and stored in the `correction_embeddings`
table. On future queries with cosine similarity > {{threshold, e.g. 0.70}} to a stored
correction, the correction is injected as a few-shot example before Claude answers.

- Storage: `correction_embeddings` table with ivfflat index
- Retrieval: top-3 corrections by cosine ANN search per query
- Observable in LangSmith: `metadata.corrections_injected = N`
- Feature flag: `USE_CORRECTION_CONTEXT=false` in `.env` disables injection
- Backfill existing corrections: `python3 scripts/embed_corrections.py`
```

---

## Anti-Patterns

| Anti-Pattern | Why It Fails | Correct Approach |
|---|---|---|
| Description is vague (`"handles compliance stuff"`) | The skill activation system matches descriptions against user queries. A vague description never triggers a match. | Write the description as: trigger condition + what it does + what it does NOT do. Example from employee-onboarding: `"NetSuite role assignment approval routing triggered by Jira tickets. Use when a Jira ticket contains 'Assign role', 'Fivetran-', or a NetSuite role name paired with a user email. [...] Does NOT orchestrate Okta/Workday/Celigo provisioning; that is a separate automated flow."` |
| No Non-Negotiable Rules section | Claude will answer compliance questions from training data when no rule prohibits it. Training data is stale, wrong, and does not reflect your actual user population or role structure. | Add an explicit `## Non-Negotiable Rules` section. The first rule must be: `NEVER answer compliance questions from memory. Every violation count, role name, risk score, and conflict must come from a live MCP tool call.` |
| Workflows described in prose instead of numbered steps | Under token pressure, Claude skips steps described in paragraphs. Numbered steps create an explicit sequence Claude treats as a checklist. | Use numbered steps, one action per step. Each step names exactly one MCP tool call or decision. |
| Examples use fake data (`user@example.com`, `"SomeRole"`) | Claude pattern-matches examples to real queries. Fake data does not pattern-match to real user emails or role names. | Use realistic data: real role names like `Fivetran-AP-Approver`, real email format like `first.last@fivetran.com`, real violation counts like `249 conflicts, 3 CRITICAL`. |
| No trigger phrases | Without trigger phrases, the skill is never auto-activated. | Add at least 3 trigger phrases per workflow. Use the exact phrasing your users type. |
| `include_existing_roles` not mentioned anywhere | Every access review call silently analyzes only the new role in isolation. A user holding `Fivetran-AP-Processor` requesting `Fivetran-Controller` returns 0 conflicts instead of 249. Real fraud risk consequence. | Make it a Non-Negotiable Rule: `ALWAYS pass include_existing_roles: true to analyze_access_request. Omitting it produces false "0 conflicts" for users who already hold conflicting roles.` |
| Troubleshooting Fix column says `"contact support"` | Not actionable. | Every fix must be a runnable shell command, a specific parameter to add, or a named escalation path. |
| Self-approval rule absent from onboarding skills | Without an explicit block, Claude may route through a normal SOD check and find an approver — potentially approving the request at a high authority level. SOX prohibits this. | Add as Non-Negotiable Rule: `Self-approval is never permitted. If requester == target user, immediately escalate to manager before running any MCP tools.` |
| Multiple roles in one ticket treated as independent checks | Two individually LOW-risk roles can be CRITICAL in combination. Checking them separately misses the combined conflict. | Document in Troubleshooting and in the workflow: `"Multiple roles in one ticket: run analyze_access_request with ALL requested roles together. Route on the highest severity returned."` |
| Skill identity bleeds into responses (`"As the SOD compliance agent, I can tell you..."`) | The skill name is an implementation detail. Exposing it implies a narrower scope than the agent actually has. | Add a Non-Negotiable Rule: `NEVER say "[skill name] agent". You are {{organization}}'s compliance agent. This skill is one capability, not your identity.` |
| Trigger phrases are too generic (`"help"`, `"access"`, `"role"`) | Generic triggers activate the skill on unrelated queries. | Use specific, multi-word phrases: `"would this create a conflict"` not `"access"`. |
| Workflow steps use bullets instead of numbered lists for ordered sequences | Bullets imply items are unordered. Claude may re-order or skip them. | Use numbered lists for all ordered sequences. Reserve bullets for genuinely unordered lists (e.g., trigger phrase options). |

---

## Voice and Tone Guidelines

### Response format

Lead with the verdict or conclusion, then provide evidence.

- First line: verdict (`APPROVED`, `CONDITIONAL`, `DENIED`, or a quantified summary like `"Finance carries 28 open violations"`)
- Second through final lines: supporting evidence — counts, role names, specific conflict descriptions, recommended next action
- Never bury the conclusion at the end of a paragraph

### Vocabulary

| Avoid | Use instead |
|-------|-------------|
| `dangerous` | `high-risk` |
| `violator` | `affected user` |
| `illegal` | `non-compliant` |
| `broken` | `misconfigured` or `in violation` |
| `you can't do that` | `this action is blocked per SOX policy` |
| `obviously` | *(omit)* |
| `unfortunately` | *(omit — state the fact directly)* |

### Response length constraints

Specify hard limits per response type. Soft wording is routinely ignored under token pressure. Use `HARD LIMIT` in the prompt.

| Response type | Constraint |
|---------------|------------|
| Access review verdict | `HARD LIMIT: 1,200 characters` |
| Role risk matrix summary | `Maximum 3 bullet points, 1,200 characters` |
| Full compliance report | `HARD LIMIT: 1,800 characters. If longer, use file upload.` |
| Exception approval confirmation | `Maximum 3 sentences` |

### Skill identity

Claude must never identify itself by the skill name. The skill name is an internal routing label.

"Finance carries 28 open violations."

Not: "As the SOD Compliance Agent, I have checked Finance and found 28 violations."

If tone and identity consistency are critical, add a Voice rule to Non-Negotiable Rules:

```
**Voice:** Senior McKinsey partner. Lead with the conclusion, then evidence.
Direct recommendations. No hedging. Replace "dangerous" with "high-risk",
"violator" with "affected user". NEVER say "[skill name] agent".
You are {{organization}}'s compliance agent. This skill is one of your capabilities, not your identity.
```

---

## Quick-Start Checklist

Use this checklist before marking a SKILL.md as production-ready. Every item is verifiable with a yes/no answer.

```
 1. [ ] Frontmatter `description` field explicitly states the trigger condition
        (the exact query type or phrase that should activate this skill)

 2. [ ] Frontmatter `description` states what the skill does NOT do
        (prevents activation on queries that belong to a different skill)

 3. [ ] `## Non-Negotiable Rules` section exists and contains at least one rule

 4. [ ] If the skill calls `analyze_access_request`, a Non-Negotiable Rule explicitly
        requires `include_existing_roles: true` with an explanation of what breaks without it

 5. [ ] If the skill calls any write or mutating tool (approve, sync, remediate),
        a Non-Negotiable Rule requires confirming the violation/request exists before writing

 6. [ ] Every workflow has a `**Trigger phrases:**` line with at least 3 specific phrases

 7. [ ] Every workflow uses numbered steps, not bullets, for the ordered sequence of tool calls

 8. [ ] At least 2 worked examples exist, each with realistic data
        (real role names like `Fivetran-AP-Approver`, real email format, real violation counts)

 9. [ ] Every example shows the full tool call sequence with parameter names and values,
        not just the tool names

10. [ ] A Troubleshooting table exists with at least 5 rows

11. [ ] Every row in the Troubleshooting Fix column contains a runnable command or
        a specific parameter — no row says "contact support" or "check the configuration"

12. [ ] A Non-Negotiable Rule or Voice line prohibits Claude from identifying itself
        by the skill name (e.g., "NEVER say 'SOD compliance agent'")

13. [ ] Response length constraints are stated as `HARD LIMIT N characters` or
        `Maximum N bullet points` — not as soft guidance

14. [ ] If the skill has caching or memory infrastructure, an Infrastructure Notes section
        documents TTLs, cache keys, LangSmith metadata keys, and feature flags

15. [ ] Version history table is present with at least a v1.0.0 row
```

---

## Version History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0.0 | {{YYYY-MM-DD}} | {{Author}} | Initial version |

**Versioning rules:**

| Change type | Version bump | Example |
|-------------|-------------|---------|
| Breaking change to workflow steps (tool call order, required parameters change, step removed) | Major (`1.0.0` → `2.0.0`) | `analyze_access_request` gains a new required parameter |
| New workflow added, new Non-Negotiable Rule added, new trigger phrase group added | Minor (`1.0.0` → `1.1.0`) | New Workflow 9: NetSuite Sync added |
| New example added, troubleshooting row added, wording clarification | Patch (`1.0.0` → `1.0.1`) | Added Example 3: Self-approval blocked |

A breaking change is any change that would cause a Claude instance running the previous version of the skill to produce a wrong answer or call a tool with the wrong parameters.

**Full version history row format:**

```markdown
| 2.0.0 | 2026-02-27 | Fivetran SysEng | Breaking: analyze_access_request now requires role_id instead of role name string. Updated all workflows and examples. |
| 1.1.0 | 2026-02-15 | Fivetran SysEng | Added Workflow 9: NetSuite Sync; added trigger phrases for data-freshness queries. |
| 1.0.1 | 2026-02-10 | Fivetran SysEng | Added Example 3 (self-approval); added troubleshooting row for multi-role tickets. |
| 1.0.0 | 2026-02-01 | {{Author}} | Initial version. |
```

---

*Template maintained by Fivetran SysEng. Last reviewed: 2026-02-27.*