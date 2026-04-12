# Multi-Agent Playbook Template

**Version:** 1.0
**Purpose:** Reusable template for orchestrating parallel AI coding agents on complex systems.
**Based on:** Lessons from building the Fivetran Compliance Agent (Feb 2026).

---

## How to Use This Template

1. Copy this file to your project root as `CLAUDE_MULTI_AGENT.md`
2. Fill in every `[PLACEHOLDER]` — never leave them blank
3. Delete sections that don't apply (e.g. no Angular portal → remove Agent R equivalent)
4. Add project-specific critical rules to the rules table
5. Run Phase 8 (QA agents) after every non-trivial feature implementation

---

## Part 1: Document Header

```markdown
# Building [YOUR SYSTEM NAME]: A Multi-Agent Playbook

**Version:** 1.0
**Last Updated:** [DATE]
**Purpose:** [One sentence — what this system does and why agents are used]
```

**Best practices:**
- Keep the version number. Increment it when you add agents or change coordination rules.
- The purpose line should explain the *system*, not just the playbook. Future agents read
  this first and use it to understand scope.

---

## Part 2: System at a Glance

Show the data flow as ASCII — agents use this to understand how their output
feeds the next phase. Keep it to one screen (< 20 lines).

```markdown
## System at a Glance

```
[INPUT SOURCE]          ← [data format / protocol]
       ↓
[PROCESSING LAYER]      ← [technology]
       ↓
[STORAGE LAYER]         ← [database / cache]
       ↓
[SERVING LAYER]         ← [API / UI / bot]
       ↓
[CONSUMER / OUTPUT]
```

Stack: [language] · [framework] · [database] · [LLM] · [key libraries]
```

**Best practices:**
- Name every arrow with the protocol or format (REST, SQL, WebSocket, Redis RESP)
- Put the stack on one line — agents scan it to decide which packages to install
- If there are multiple consumers (API + Slack + CLI), show all of them

---

## Part 3: Agent Roster

Every agent gets a single letter ID, a name ending in "Agent", the phase it
belongs to, and which agents it can run alongside.

```markdown
## Agent Roster

| ID | Agent | Phase | Can Parallelise With |
|----|-------|-------|----------------------|
| A  | [Name] Agent | 0 | B |
| B  | [Name] Agent | 0 | A |
| C  | [Name] Agent | 1 | D, E |
| D  | [Name] Agent | 1 | C, E |
| E  | [Name] Agent | 1 | C, D |
| ...                               |
| T  | Test Agent   | N | U |
| U  | QA Agent     | N | T |
| V  | Bug Fix Agent | N | — (after T + U) |
```

**Best practices:**

- **One agent = one deployable concern.** An agent that owns "backend + frontend + DB"
  is too large — split it.
- **Phase 0 is always infrastructure.** DB, env, secrets. Nothing else can start without it.
- **Agents T, U, V are always the last phase.** They are reusable — invoke Phase 8 (QA)
  after every non-trivial feature, not just at the end.
- **"Can Parallelise With" must be honest.** If Agent D reads the output of Agent C,
  they cannot parallelise — mark D as phase 2, not phase 1.
- **Aim for 3–6 agents per phase.** Fewer means sequential bottlenecks; more means
  coordination overhead exceeds parallelism benefit.

---

## Part 4: Dependency Graph

```markdown
## Dependency Graph

```
Phase 0:  [A] [B]                    ← run first, in parallel
              ↓
Phase 1:  [C] [D] [E]                ← all parallel after Phase 0
              ↓
Phase 2:  [F] [G]                    ← parallel after Phase 1
              ↓
Phase N:  [T] [U] ──────→ [V]        ← T and U parallel; V after both
```
```

**Best practices:**
- Draw the actual arrows — do not just list phases. Agents read this to decide
  when they can start and what they must wait for.
- Never start a phase until every verification gate from the prior phase passes.
- The QA phase ([T][U]→[V]) should appear at the end of every feature group,
  not just once at the very end of the project.

---

## Part 5: Agent Definitions

For each agent, write four sections. This is the most important part of the file.

```markdown
## Phase N — [Phase Name]

### Agent X: [Name] Agent

**Goal:** One sentence. What observable output exists when this agent is done?

**Inputs:** What files, services, or data must already exist before this agent starts?
**Produces:** What files or DB state does this agent create?

**Prompt:**
```
You are the [Name] Agent. [Task description].

[Step-by-step instructions with explicit DO and DO NOT rules]

CRITICAL rules:
- [Rule 1 — describe what breaks if violated]
- [Rule 2]
```

**Verification gate:**
```bash
[Command that returns a measurable, pass/fail result]
# → expected output
```
```

**Best practices for the Goal line:**
- Write it as a completed fact, not a task: "Postgres running with pgvector" not "Set up Postgres"
- Make it testable: the verification gate must directly prove the goal

**Best practices for the Prompt:**
- Write CRITICAL in uppercase for rules that have caused data loss or crashes historically
- Number the steps — agents work better with explicit ordering
- Include both the correct pattern AND the wrong pattern agents commonly try:
  ```
  CORRECT:  get_users(page_size=200)
  WRONG:    get_users(page_size=1000)   ← silently loses 79% of data
  ```
- End with import/connection patterns to prevent agents inventing non-existent modules:
  ```
  DB session: from models.database_config import DatabaseConfig; session = DatabaseConfig().get_session()
  NEVER:      from database.db_setup import get_db_session  ← this module does not exist
  ```

**Best practices for the Verification gate:**
- Must be a shell command that exits non-zero on failure (so CI can run it)
- Must check the *output*, not just that the process ran:
  ```bash
  # GOOD — checks actual count
  psql $DATABASE_URL -c "SELECT COUNT(*) FROM sod_rules;" | grep -q "18"

  # BAD — only checks that the command ran
  python3 setup.py && echo "done"
  ```
- For network services: always test the endpoint, not just the process PID

---

## Part 6: Phase 8 — Quality Assurance (Always Include)

Copy this section verbatim into every playbook. Customize only the
regression test list and the stress test scenarios.

```markdown
## Phase 8 — Quality Assurance

Phase 8 runs after every non-trivial feature phase.
Agents T and U run in parallel. Agent V runs after both finish.

### Agent T: Test Agent

**Goal:** All smoke, regression, and stress tests pass.
**Inputs:** Running services + new/modified files
**Produces:** Structured PASS/FAIL report

**Prompt template:**
```
You are the Test Agent. Run smoke, regression, and stress tests for [FEATURE].

Working directory: [PATH]
Activate venv: source .venv/bin/activate

== SMOKE TESTS (happy path) ==
[4–6 scenarios covering the main success path]

== REGRESSION TESTS (guard known failure patterns) ==
[2–4 tests that verify previously broken behaviour stays fixed]

  Patterns to always guard:
  - [Project-specific rule 1]
  - [Project-specific rule 2]
  - SQL pgvector: use CAST(:param AS vector), never :param::vector
  - SQLAlchemy uuid arrays: pass "{uuid1,uuid2}" + ::uuid[] cast, not Python list
  - NetSuite page_size: must be 200, never 1000

== STRESS TESTS (edge cases) ==
[2–3 edge cases: empty inputs, None values, concurrent calls, large inputs]

Output format:
=== [FEATURE] TEST RESULTS ===
TEST N (description): PASS/FAIL — reason
TOTAL: X/Y PASS
FAILURES: [full error output]
ROOT CAUSE: [file:line + description]
```

---

### Agent U: QA Agent

**Goal:** All CRITICAL and MEDIUM code bugs identified and reported.
**Inputs:** New/modified source files (read-only — no code changes)
**Produces:** Structured QA report (CRITICAL / MEDIUM / LOW)

**Prompt template:**
```
You are the QA Agent. Review [FILES] for bugs and edge cases.

For each file check:

CORRECTNESS
  □ SQL parameters: named-style :param, no mixed pyformat/named styles
  □ pgvector casts: CAST(:param AS vector), never :param::vector
  □ UUID arrays: PostgreSQL literal "{uuid1}" + ::uuid[], not Python list
  □ session.close() in finally blocks (no connection leaks)
  □ DB writes wrapped in try/except with rollback()
  □ Side-effects non-blocking (threading.Thread daemon=True)

EDGE CASES
  □ None / empty string inputs
  □ Zero-row DB queries (don't crash on .fetchone()[0])
  □ Feature flag = False (all code paths gated?)
  □ Concurrent calls (thread safety)
  □ Downstream service unavailable (Redis, LangSmith, external API)

INTEGRATION
  □ New code reachable from entry point (Slack DM + mention paths)
  □ New MCP tools registered in tool_router.py
  □ Feature flags present in .env template
  □ LangSmith tags fire on correct metadata keys

Output format:
=== [FEATURE] QA REVIEW ===

CRITICAL BUGS (will cause errors or data loss):
  BUG-C1: file.py:line — description — fix

MEDIUM ISSUES (wrong behaviour, won't crash):
  BUG-M1: file.py:line — description — fix

LOW / SUGGESTIONS:
  BUG-L1: file.py:line — description — suggestion

OVERALL: SHIP / NEEDS FIXES
```

---

### Agent V: Bug Fix Agent

**Goal:** Every CRITICAL and MEDIUM bug fixed and verified with a live test.
**Inputs:** Test report (Agent T) + QA report (Agent U)
**Produces:** Fixed source files + live test confirmation per fix

**Prompt template:**
```
You are the Bug Fix Agent. Fix the bugs below. Fix ONLY what is listed.
Do not refactor, rename, or improve anything else.

== TEST FAILURES ==
[Paste T's FAILURES block]

== QA BUGS (CRITICAL + MEDIUM only) ==
[Paste U's CRITICAL and MEDIUM sections]

For each fix:
1. Read the file before editing
2. Apply the minimal change
3. Run a live test to confirm the fix
4. If the fix introduces a new failure, revert and report

Output format:
=== BUG FIX SUMMARY ===
BUG-Cx (description): FIXED/REVERTED — change made + live test result
Live test TOTAL: X/Y PASS
```

**Verification gate (Phase 8 passes when):**
- Every CRITICAL bug has a live test showing previously-failing scenario now passes
- No new failures introduced
- Entry point (Slack bot / API server) restarts cleanly
```

---

## Part 7: Coordination Patterns

Include all patterns that apply to your system. The first four are universal.

```markdown
## Coordination Patterns

### Pattern 1: Shared Database Session
```python
from models.database_config import DatabaseConfig
session = DatabaseConfig().get_session()
try:
    session.execute(...)
    session.commit()
except Exception:
    session.rollback()
    raise
finally:
    session.close()
```

### Pattern 2: Non-Blocking Side Effects
All write-backs (summaries, feedback, external API calls) must be non-blocking:
```python
threading.Thread(target=_write_thing, args=(...), daemon=True).start()
```
Never block the user-facing response path on a DB write or API call.

### Pattern 3: Thread-Local for Cross-Function State
When a value produced in a child function (e.g. run_id, cache_hit flag) is needed
by the parent handler, use threading.local():
```python
_tls = threading.local()
# In child:  _tls.run_id = str(root_run.id)
# In parent: run_id = getattr(_tls, "run_id", None)
```
Do not use globals or return values — the call chain crosses thread boundaries.

### Pattern 4: Prompt Constraint Strength
| Soft (often ignored)       | Hard (enforced)                       |
|----------------------------|---------------------------------------|
| "aim for concise"          | "MAXIMUM 1,200 characters"            |
| "prefer this tool"         | "ALWAYS call X. NEVER call Y."        |
| "should be under 1800"     | "HARD LIMIT: 1,800 chars"             |
| "try not to use X phrase"  | "NEVER use the phrase 'X'"            |

### Pattern 5: Tool / Module Registration
Every new tool or module added to the system must be registered in the
central router/registry. If not registered, it is silently excluded.
Check: after adding, verify it appears in the router output for a
representative input.

### Pattern 6: Three-Agent QA Loop
```
# Step 1: launch T and U in parallel (fully independent)
task(T, "run smoke/regression/stress tests for [feature]", background=True)
task(U, "review [files] for bugs",                         background=True)

# Step 2: wait for both
# Step 3: launch V with both reports
task(V, f"fix:\n\nT report:\n{T_output}\n\nU report:\n{U_output}")

# Step 4: re-run failing tests to confirm resolution
```
T and U are always parallel — they are independent (T exercises running code,
U reads source). V fixes ONLY what T + U reported — no scope creep.
```

---

## Part 8: Critical Rules Table

This is the most valuable section. Every row is a hard-won lesson.
When a new failure is discovered, add it immediately — before the next session.

```markdown
## Critical Rules for All Agents

| # | Rule | Impact if violated |
|---|------|--------------------|
| 1 | [Rule] | [What breaks] |
| 2 | [Rule] | [What breaks] |
```

**Rules that belong in every project using this stack:**

| # | Rule | Impact |
|---|------|--------|
| 1 | Never name a SQLAlchemy column `metadata` | Reserved name — breaks model init silently |
| 2 | pgvector: use `CAST(:param AS vector)` in `text()`, never `:param::vector` | psycopg2 misparses `::` after a named param — type error at runtime |
| 3 | UUID arrays in `text()`: pass `"{uuid1,uuid2}"` literal + `::uuid[]` cast | psycopg2 cannot infer array element type from a Python list |
| 4 | Python enum values must match DB CHECK constraints exactly (UPPERCASE) | Insert fails with IntegrityError or silently stores wrong value |
| 5 | `session.close()` must be in a `finally` block | Connection pool exhaustion under load |
| 6 | All side-effects must be in `threading.Thread(daemon=True)` | Blocks user-facing response; degrades P99 latency |
| 7 | Slack `views_open()` must be called synchronously on button click | `trigger_id` expires in 3 seconds — modal never opens |
| 8 | `_trim_history()` must advance to first HumanMessage after slicing | Orphaned `tool_result` block → Anthropic API 400 error |
| 9 | Every new MCP/plugin tool must be registered in the central router | Tool silently excluded from every Claude query |
| 10 | Use `HARD LIMIT` / `MAXIMUM N chars` in prompts, not soft wording | Soft constraints are routinely ignored by LLMs |

**How to add new rules:**
1. When a bug is found in Phase 8, ask: "would a future agent repeat this mistake?"
2. If yes, add a row immediately with the exact impact
3. Number rules sequentially — never reuse a number
4. Reference the rule number in agent prompts: "see Rule 8"

---

## Part 9: Verification Gates (Full System)

One master checklist to run after all phases complete.

```markdown
## Verification Gates (Full System)

```bash
# Infrastructure
[command to verify DB is up with correct table count]
# → [expected output]

[command to verify cache is up]
# → PONG

# Data layer
[command to verify seed data loaded]
# → [expected count]

# Services
[command to verify API is healthy]
# → {"status": "ok"}

[command to verify tool/endpoint count]
# → [N] tools

# Application
[command to verify bot/app process is running]
# → "Running!"

# Observability
# [manual step] Open [tracing dashboard URL]
# Send a test query → trace should appear within 30s

# Feedback
[command to verify feedback table exists and increments]
# → increments after user interaction
```
```

---

## Part 10: Environment Variables

One canonical reference. Never scatter env vars across README files.

```markdown
## Environment Variables Quick Reference

```bash
# [Category 1]
VAR_NAME=example_value   # description

# [Category 2]
VAR_NAME=example_value

# Feature Flags (all default true — set to false to disable)
USE_FEATURE_X=true
USE_FEATURE_Y=true

# Tuning
MAX_TOKENS=1024          # LLM output limit
MAX_RESPONSE_CHARS=2000  # UI truncation limit
```
```

**Best practices:**
- Group by category with a comment header
- For every feature flag, document the default and what disabling it does
- For every secret, show the format not the value (`sk-ant-...` not `sk-ant-abc123`)
- Include tuning knobs — they are always needed in production and agents forget to add them

---

## Part 11: Starting Order

```markdown
## Starting Order (Copy-Paste)

```bash
# 1. Infrastructure (always first)
[start DB command]
[start cache command]

# 2. Backend service
[start command] > /tmp/[service].log 2>&1 &

# Verify
[health check command]

# 3. Application
[start command] > /tmp/[app].log 2>&1 &

# 4. Optional UI
[start command]
```
```

**Best practices:**
- Include the log redirect (`> /tmp/x.log 2>&1 &`) — agents need to know where logs go
- Include a health-check between every step — don't assume the previous step succeeded
- The verify step must be a command that fails loudly if the service is not up

---

## Part 12: Common Anti-Patterns to Avoid

These mistakes appear repeatedly across AI-agent-built systems.

### Anti-pattern 1: One Mega-Agent
**Wrong:** Agent A builds the entire backend (DB + API + business logic + tests).
**Right:** Split by layer — one agent per concern. Parallelism is only possible with
small, independent agents.

### Anti-pattern 2: Implicit Agent Inputs
**Wrong:** "Agent D builds repositories" — doesn't say what it reads from.
**Right:** Always list explicit inputs: "Agent D reads models from Agent C's output."
Agents that don't know their inputs often invent the wrong interfaces.

### Anti-pattern 3: Soft Verification Gates
**Wrong:** "Verify the bot is working by sending a test message."
**Right:** `curl -s http://localhost:8080/health | python3 -c "import sys,json; assert json.load(sys.stdin)['status']=='ok'"`
Soft gates cannot run in CI and are frequently skipped.

### Anti-pattern 4: Undocumented Failure Modes
**Wrong:** Agent prompt says "handle errors" without specifying what errors have happened.
**Right:** List known failure modes explicitly in the prompt with their exact fix:
```
Known failure: `from database.db_setup import get_db_session` — this module does not exist.
Use: `from models.database_config import DatabaseConfig; session = DatabaseConfig().get_session()`
```

### Anti-pattern 5: No Phase 8
**Wrong:** Ship new features without running T + U + V.
**Right:** Phase 8 is not optional. Agents write plausible-looking code that has
subtle SQL type mismatches, session leaks, and threading bugs that only Phase 8 catches.

### Anti-pattern 6: Skipping the QA Agent's Independent Review
**Wrong:** Only run tests (Agent T) and fix what fails.
**Right:** Agent U (QA) reviews the source independently. In the Phase C example, U found
the UUID array bug (BUG-C2) before T even hit that code path. Static review catches
bugs that tests don't cover.

### Anti-pattern 7: Agent V Scope Creep
**Wrong:** Bug Fix Agent also refactors nearby code "while it's in there."
**Right:** V fixes exactly and only what T + U reported. Scope creep introduces new
bugs that require another Phase 8 cycle.

### Anti-pattern 8: Feature Flags as an Afterthought
**Wrong:** Build the feature, then add a flag later.
**Right:** Add `USE_[FEATURE]=true` to `.env` and check it at the entry point before
any code runs. This enables safe rollback in production without a deploy.

---

## Part 13: Version History

```markdown
## Version History

- **v1.0 ([DATE]):** Initial playbook — Phases 0–N, Agents A–V, Patterns 1–6.
```

**Best practices:**
- Increment version on every structural change (new agent, new pattern, new rule)
- Keep the history — future agents use it to understand what changed and why
- Each entry should say *what* was added and *why* (reference the incident or feature)

---

## Quick-Start Checklist

Use this when writing the playbook for a new project:

```
□ System at a Glance diagram — data flow + stack on one page
□ Agent Roster — every agent has a phase and parallelism declaration
□ Dependency Graph — ASCII showing exact phase ordering
□ Phase 0 — infrastructure (DB + env) defined first, before anything else
□ Agent definitions — Goal / Inputs / Produces / Prompt / Verification gate for every agent
□ Phase 8 — Agents T, U, V included (copy from this template verbatim)
□ Coordination Patterns — at minimum Patterns 1–6
□ Critical Rules table — at minimum the 10 universal rules from this template
□ Full System Verification Gates — all commands return measurable pass/fail
□ Environment Variables section — grouped, with feature flags and tuning knobs
□ Starting Order — with log paths and health checks between each step
□ Version History — even if it's just v1.0
```

---

**Template maintained by:** AI Development Team
**Template version:** 1.0 (2026-02-27)
**Based on:** Fivetran Compliance Agent — CLAUDE_MULTI_AGENT.md v1.1
