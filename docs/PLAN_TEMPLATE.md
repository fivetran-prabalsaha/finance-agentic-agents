> **Status: DRAFT**
> Last updated: 2026-02-27
> Author: Fivetran SysEng

# Plan.md Template — Best Practices for Claude Code Implementation Plans

**Version:** 1.0.0
**Date:** 2026-02-27
**Team:** Fivetran SysEng
**Purpose:** Reusable template for writing Claude Code plan.md files — the per-task implementation documents that describe what will be built, why, and exactly how.

---

## How to Use This Template

1. Enter Plan Mode in Claude Code (`/plan`) — Claude will create a file automatically under `~/.claude/plans/<generated-name>.md`
2. Fill in every `{{PLACEHOLDER}}` — never leave them blank in a plan you intend to execute
3. Delete sections that do not apply (e.g. no schema change → remove migration rows from the files table)
4. Review the Non-Goals section carefully before approving — missing non-goals cause scope creep
5. Update the Status block every time the plan changes state (DRAFT → IN PROGRESS → COMPLETE)

**Where plan files live:**

Plan files are created automatically by Claude Code in `~/.claude/plans/<name>.md` when you enter Plan Mode. The filename is generated (e.g. `mutable-pondering-adleman.md`) — treat it as an opaque identifier. Do not rename the file; Claude Code uses the path to track execution state.

**What this template is NOT:**

This template is for implementation plans — ephemeral documents that describe a specific change and are discarded (or archived as historical record) once complete. It is not for skill files (see `SKILL_TEMPLATE.md`) or multi-agent orchestration playbooks (see `CLAUDE_MULTI_AGENT_TEMPLATE.md`). A plan.md is consumed during execution; CLAUDE.md is the permanent project memory that outlives any individual plan.

**Relationship between plan.md, CLAUDE.md, and skill files:**

| Document | Lives at | Lifespan | Written by | Read by |
|----------|----------|----------|------------|---------|
| `plan.md` | `~/.claude/plans/` | Ephemeral — one change | Human + Claude (Plan Mode) | Claude (execution) |
| `CLAUDE.md` | Project root | Permanent | Human + Claude | Claude (every session) |
| `SKILL.md` | `~/.claude/skills/<name>/` | Permanent | Human | Claude (skill routing) |
| Multi-agent playbook | Project docs | Permanent | Human | Claude (orchestration) |

After a plan is executed, **update CLAUDE.md** with the new enhancement. The plan.md becomes a historical record but is no longer the authoritative source of truth.

---

## When to Write a Plan

Write a plan.md when the change involves any of the following:

- Touches 5 or more files
- Introduces a new pattern that future agents should follow (new model, new helper convention, new feature-flag pattern)
- Includes a database schema migration
- Adds shared infrastructure (a new service class, a new Postgres table, a new Redis key namespace)
- Spans multiple phases or weeks of work
- Has non-obvious rollback requirements

## When to Skip a Plan

Skip the plan and go directly to implementation when:

- The change is a single-file bug fix (e.g. correcting an off-by-one, fixing a typo in a prompt)
- The change is additive and isolated (e.g. adding one row to a seed data JSON file)
- The change is a trivial wording update (e.g. editing a Slack message string)
- The change is fully contained within a function you are already looking at

When in doubt, write the plan. A two-minute plan that turns out to be unnecessary costs less than a one-hour refactor caused by missing context.

---

# Part 2 — Status Block

Every plan.md must begin with a status block **above the title**. This block is the first thing Claude reads when it opens a plan file in a new session. An incorrect status is actively harmful — it misleads future agents about the state of the codebase.

## Status Block Format

```markdown
> **Status: DRAFT | IN PROGRESS | COMPLETE | ABANDONED**
> Last updated: {{YYYY-MM-DD}}
> Author: {{name or agent}}
```

Place this block as the very first content in the file, before the `#` title heading.

## Status Definitions

| Status | Meaning |
|--------|---------|
| `DRAFT` | Plan has been written but has not been reviewed and approved for execution. Code has not been touched. |
| `IN PROGRESS` | Plan has been approved. Execution has started. One or more phases may be complete. |
| `COMPLETE` | All phases are done. All verification steps have passed. CLAUDE.md has been updated. |
| `ABANDONED` | Plan was dropped before completion. A note must explain why (blocked dependency, requirements changed, superseded by a different approach). |

## Rule: Always Update the Status Block

A plan.md with `Status: DRAFT` that was actually completed is **worse than no plan.md at all**. It signals to future agents that the work has not been done, causing them to attempt to re-implement already-live code.

Update the status block at each of these moments:

- When you approve the plan for execution: `DRAFT` → `IN PROGRESS`
- When all phases are done and verification passes: `IN PROGRESS` → `COMPLETE`
- When the plan is dropped for any reason: `DRAFT` or `IN PROGRESS` → `ABANDONED` (add a note)

When a plan is ABANDONED, add a free-text note immediately below the status block:

```markdown
> **Status: ABANDONED**
> Last updated: 2026-02-27
> Author: prabal.saha

> **Note:** Superseded by `elastic-clever-turing.md`, which takes a different approach
> using pgvector embeddings rather than Redis sorted sets. Do not implement this plan.
```

---

# Part 3 — Context Section

## Template

```markdown
## Context

**Current state:** {{One paragraph. What does the system do today in the area this plan touches?
Be specific: name the files, the services, the tables. A future agent reading this section
should be able to locate the relevant code without reading CLAUDE.md.}}

**Problem or gap:** {{What is broken, missing, or suboptimal? Quantify where possible
(e.g. "accuracy measured by 3 automated evaluators only — no human signal").}}

**Why now:** {{Why is this the right time to address it? Is there a deadline, a dependency
on another team's work shipping, a user complaint that surfaced this week?}}

**Constraints:** {{What must this change NOT break? What existing behavior must be preserved?
Are there deadlines, budget limits, API rate limits, or approval requirements?}}
```

## Good Example (from the compliance agent feedback loop plan)

```markdown
## Context

**Current state:** The compliance agent answers SOD violation queries via Slack
(`slack_bot_local.py`). Accuracy is currently measured only by 3 automated LangSmith
evaluators (`mcp_tool_called`, `mcp_tool_coverage`, `hallucination_heuristic`). All three
fire on every trace automatically. There is no human signal — compliance officers cannot
flag wrong answers, and there is no mechanism to improve accuracy from real-world
corrections.

**Problem or gap:** Automated evaluators catch structural failures (wrong tool called,
hallucinated numbers) but cannot detect factually incorrect answers that are
structurally sound. A response that calls the right tool but misreads the output scores
1.0 on all three evaluators. Human judgment is required to catch this class of error.

**Why now:** The Slack bot is in daily use by 4 compliance officers as of Feb 2026.
Incorrect answers are currently invisible in LangSmith — there is no way to correlate
user complaints with specific traces. Adding feedback buttons now, while the user base
is small, lets us tune the system before broader rollout.

**Constraints:** Must not change the Slack message format for users who do not click
the buttons. Feature must be off by default in CI (`USE_ANSWER_FEEDBACK=false`).
Redis cache bust on negative feedback must be non-blocking — it cannot delay the
Slack acknowledgement.
```

## Bad Example

```markdown
## Context

We need to add feedback buttons to the Slack bot.
```

This fails because it contains no current state (what does the bot look like today?), no problem statement (why are feedback buttons needed?), and no constraint (what must not break?). A Claude agent reading this context cannot assess scope, cannot identify what files to touch, and cannot determine what "done" looks like.

The rule: **if a future agent could not reproduce your understanding of the problem from this section alone, the context is incomplete.**

---

# Part 4 — Goals and Non-Goals

## Template

```markdown
## Goals

- {{Goal 1. State what will be true when this goal is achieved. Attach a verifiable check.}}
  - Verify: `{{bash command, SQL query, or UI step that confirms this goal is met}}`
- {{Goal 2.}}
  - Verify: `{{...}}`
- {{Goal 3.}}
  - Verify: `{{...}}`

## Non-Goals

- {{Non-Goal 1. Something adjacent that this plan explicitly does NOT address.}}
- {{Non-Goal 2.}}
- {{Non-Goal 3.}}
```

Every goal must be verifiable. "Improve accuracy" is not a goal. "LangSmith shows `human_rating` score on every trace where a feedback button was clicked" is a goal.

## Good Example (from the compliance agent feedback loop plan)

```markdown
## Goals

- Block Kit feedback buttons (Correct / Wrong / Partial) appear on every bot response
  in Slack.
  - Verify: Send a compliance question in any channel → response shows 3 buttons.
- Feedback is stored in Postgres `answer_feedback` table with `run_id`, `signal`,
  `user_email`, and `query_preview`.
  - Verify: `SELECT * FROM answer_feedback ORDER BY created_at DESC LIMIT 1;`
- Scores are written to LangSmith via `create_feedback()` and visible in the Feedback tab
  alongside the 3 automated evaluators.
  - Verify: LangSmith trace → Feedback tab → `human_rating: 1.0` (after clicking Correct).
- Negative feedback immediately busts the Redis violation cache for that user.
  - Verify: Click Wrong → `redis-cli KEYS "mcp:get_user_violations:*"` returns 0.
- Feature is gated behind `USE_ANSWER_FEEDBACK=true` in `.env`.
  - Verify: Set flag to `false`, restart bot → no buttons appear on responses.

## Non-Goals

- Model retraining or fine-tuning from collected feedback (out of scope; addressed in
  Phase C plan `correction-embeddings.md`).
- A batch analytics dashboard showing feedback trends over time (future work; no
  delivery date committed).
- Mobile push notifications to compliance officers when wrong answers are flagged.
- Feedback on messages sent before this feature ships (no retroactive button injection).
```

## Rule: Non-Goals Are As Important As Goals

Without explicit non-goals, scope creep happens silently. When a future agent sees "store feedback in Postgres," it may reasonably infer that a reporting dashboard should also be built. The non-goals section removes that ambiguity. Every plan should have at least three non-goals. If you cannot think of three things this plan does NOT do, the scope is probably not well-defined.

---

# Part 5 — Implementation Phases

## Template

```markdown
## Phase {{N}} — {{Name}} ({{Timeline}})

### Deliverables

- {{Deliverable 1}} — `path/to/file.py` (New)
- {{Deliverable 2}} — `path/to/other.py` (Modify: `function_name()`)
- {{Deliverable 3}} — `database/migrations/NNN_name.sql` (New)

### {{Deliverable 1 Name}}

**File:** `path/to/file.py`

{{One sentence on the design decision or pattern being followed.}}

```python
# Copy-paste ready snippet for the most critical or non-obvious part
```

### {{Deliverable 2 Name}}

**File:** `path/to/other.py` — modify `function_name()` near L{{line number}}

```python
# Snippet showing exactly what changes — not the entire function
```

### Phase Gate

> Before starting Phase {{N+1}}, verify: {{One concrete, runnable check.
> Example: "SELECT COUNT(*) FROM answer_feedback;" returns at least 1 row after
> clicking a feedback button in Slack.}}
```

## Three-Phase Structure (from the compliance agent feedback loop)

The compliance agent plan used three phases with explicit dependency declarations:

**Phase A — Core Feedback Loop (Week 1)**
Builds the minimum viable feedback path: buttons on Slack responses, Postgres storage, LangSmith write-back, Redis cache bust on negative signal. This phase is independently deployable.

- New migration: `007_add_answer_feedback.sql`
- New model: `models/answer_feedback.py`
- Modify: `slack_bot_local.py` — add `_feedback_blocks()`, `_save_feedback()`, `handle_feedback()`, `_replace_feedback_block_with_confirmation()`, feature flag, `run_id` in thread-local, update `handle_dm()` and `handle_mention()`

Phase gate: Send a Slack question, click Correct, confirm `human_rating: 1.0` in LangSmith and one row in `answer_feedback`.

**Phase B — Correction Modal (Week 2, additive)**
On Wrong click, open a Slack modal prompting "What was the correct answer?" — store free-text in the `correction` column (already in the schema from Phase A). Write correction as a comment to LangSmith. No schema change required. Phase B requires Phase A to be running in production before it can be developed and tested end-to-end.

Phase gate: Click Wrong → modal appears → submit correction → `SELECT correction FROM answer_feedback ORDER BY created_at DESC LIMIT 1;` returns the submitted text.

**Phase C — Feedback to Accuracy Improvement (Month 2)**
Store corrections as pgvector embeddings in `correction_embeddings` (new table). Semantically similar future queries automatically receive the top-3 past corrections injected as few-shot context. Closes the feedback → improvement loop without model retraining. Phase C can be developed in parallel with Phase B once the `correction` column is being populated.

Phase gate: Submit a correction, run `python3 scripts/embed_corrections.py --backfill`, then query the same topic — confirm "Based on a past correction:" appears in the response.

## Rules for Phases

**Phases must be independently deployable.** If Phase B requires Phase A to be running in production, say so explicitly at the top of the Phase B section:

```markdown
## Phase B — Correction Modal (Week 2)

> Requires Phase A deployed and `answer_feedback` table populated. Phase B adds
> the correction column flow; it does not change Phase A behavior.
```

If two phases can be developed in parallel (e.g. by different agents), say that too:

```markdown
## Phase C — Embeddings (Month 2)

> Can be developed in parallel with Phase B. Only dependency: `correction` column
> must be present in `answer_feedback` (added in Phase A migration).
```

**Include code snippets for non-obvious parts.** A phase that says "add a Bolt action handler" without showing the handler signature forces the executing agent to guess the pattern. Show the scaffold. The agent will fill in the body.

**Snippets must be copy-paste ready.** If the snippet references a variable or import not shown, add a comment naming the source file and line number.

---

# Part 6 — Files to Create / Modify Table

Every plan must end with a complete file-level summary table. This table is the single source of truth for scope. If a file does not appear in this table, it must not be touched during execution.

## Table Format

```markdown
## Files to Create / Modify

| File | Change | Notes |
|------|--------|-------|
| `path/to/file.py` | New | One sentence on what it contains |
| `path/to/other.py` | Modify | Specific function or line range being changed |
| `database/migrations/NNN_name.sql` | New | Schema: what table/column/index is added |
| `database/migrations/NNN_name_rollback.sql` | New | Rollback for the above migration |
```

## Rules

1. **Every file touched anywhere in the plan must appear in this table.** If a phase section mentions a file that is not in this table, the plan is inconsistent — fix the table before executing.

2. **"Modify" entries must name the specific function or line range.** "Modify `slack_bot_local.py`" is not sufficient. "Modify `slack_bot_local.py` — add `_feedback_blocks()`, `_save_feedback()`, update `handle_dm()` and `handle_mention()`" is sufficient.

3. **Migration files must describe the schema change in the Notes column.** Naming the file `007_add_answer_feedback.sql` is not enough — the Notes column must state what table, columns, and indexes are created.

4. **If a rollback file is created, list it as a separate row.** Rollback files are first-class deliverables. An agent executing the plan that sees only the forward migration may not think to create the rollback.

5. **`.env` additions are deliverables.** If the plan introduces a new feature flag or API key, add a row for `.env` to the table.

## Compliance Agent Example

```markdown
## Files to Create / Modify

| File | Change | Notes |
|------|--------|-------|
| `database/migrations/007_add_answer_feedback.sql` | New | Creates `answer_feedback` table with columns `id`, `run_id`, `user_email`, `channel_id`, `message_ts`, `query_preview`, `answer_preview`, `signal`, `correction`, `tool_called`, `created_at`; indexes on `(user_email, created_at)`, `(signal, created_at)`, `(run_id)` |
| `database/migrations/007_add_answer_feedback_rollback.sql` | New | `DROP TABLE answer_feedback;` |
| `models/answer_feedback.py` | New | SQLAlchemy `AnswerFeedback` model following the pattern of `models/conversation_summary.py`; maps all columns with correct types and index declarations |
| `slack_bot_local.py` | Modify | Add feature flag `USE_ANSWER_FEEDBACK` near L61; add `_get_langsmith_client()` lazy init; store `run_id` in `_cache_hit_tls` at end of `process_with_claude()` (L754); new helpers `_feedback_blocks()`, `_save_feedback()`, `_replace_feedback_block_with_confirmation()`; new Bolt action handler `handle_feedback()`; update `handle_dm()` and `handle_mention()` to append feedback block after `chat_update()` |
| `.env` | Modify | Add `USE_ANSWER_FEEDBACK=true` |
```

This table makes the scope of the feedback loop plan unambiguous: five files, three new and two modified, with exact function names for the modify entries and exact schema detail for the migration.

---

# Part 7 — Verification Steps

This section answers: "How do I know the plan was executed correctly?"

Each verification step must be a concrete action (run a command, check a UI, query a database), pass/fail — not "it should look right," and listed in execution order, because some checks require previous checks to pass first.

## Template

```
1. {{What to verify}} → {{expected result}}
   Command: {{exact bash command, curl, or SQL query}}

2. {{What to verify}} → {{expected result}}
   Command: {{exact bash command, curl, or SQL query}}

3. {{What to verify — must be a database query}} → {{expected row or count}}
   Command:
   SELECT {{columns}} FROM {{table}} WHERE {{condition}} ORDER BY created_at DESC LIMIT 1;
```

**Rule:** At least one verification step must be a database query. UI checks alone are insufficient — the data layer must be verified independently. A button can appear to work while the Postgres write fails silently.

## Compliance Agent Example

```markdown
## Verification Steps

1. Slack response shows 3 buttons → actions block rendered with ✅ Correct / ❌ Wrong / 🔧 Partial
   Command: send a test compliance question to the bot in Slack; visually confirm the Block Kit
   actions block is present at the bottom of the response

2. Click ✅ → buttons replaced with confirmation text → "Thanks! Feedback recorded" context block
   appears; actions block no longer present (double-submit prevention verified)
   Command: click the ✅ Correct button; observe that the message updates in place

3. LangSmith trace has `human_rating` score → Feedback tab on the trace shows `human_rating: 1.0`
   Command: open smith.langchain.com → project `{{LANGCHAIN_PROJECT}}` → find the trace by
   `run_id` → Feedback tab

4. Database row exists → most recent `answer_feedback` row matches the signal just submitted
   Command:
   SELECT id, signal, user_email, run_id, created_at
   FROM answer_feedback
   ORDER BY created_at DESC
   LIMIT 1;

5. Cache busted on ❌ → all violation cache keys for the test user deleted immediately after
   negative feedback
   Command:
   redis-cli KEYS "mcp:get_user_violations:*"
   # Expected: (empty list) — 0 keys returned
```

---

# Part 8 — Rollback Plan

This section answers: "If something goes wrong mid-execution, how do I undo it?"

If a phase fails mid-execution, use the instructions below to undo only that phase. Never run `git reset --hard` on a shared branch — use `git revert` instead, which creates a new commit and preserves history.

**Rule:** Feature flags are the fastest rollback path for any phase. If a phase cannot be feature-flagged, explain why in that phase's rollback section and provide an alternative path.

## Template

```
### If Phase {{N}} fails

1. Set `{{FEATURE_FLAG}}=false` in `.env` and restart — no code change needed.
   This disables all user-facing behaviour added in this phase.

2. Run the rollback migration (if this phase added a schema change):
   psql $DATABASE_URL -f {{rollback_migration_file}}

3. Revert code changes with git if the flag alone is insufficient:
   git revert {{commit_sha}}   # creates a new commit, does not rewrite history

4. Verify rollback succeeded:
   {{SQL query or health check confirming the system is back to pre-phase state}}
```

## Compliance Agent Example

```markdown
## Rollback Plan

### If Phase A fails

Phase A adds the `answer_feedback` table and the feedback buttons. To roll back:

1. Run the rollback migration to drop the table and indexes:
   ```bash
   psql $DATABASE_URL -f compliance-agent/database/migrations/007_add_answer_feedback_rollback.sql
   ```
2. Disable the feature flag (no code change required — flag is read at runtime):
   ```bash
   # In .env:
   USE_ANSWER_FEEDBACK=false
   ```
   Then restart the bot:
   ```bash
   pkill -f slack_bot_local.py && python3 compliance-agent/slack_bot_local.py &
   ```
3. Verify buttons no longer appear in Slack responses.

---

### If Phase C fails

Phase C adds correction embeddings (`correction_embeddings` table, `ivfflat` index,
`CorrectionService`).

1. Disable the feature flag:
   ```bash
   # In .env:
   USE_CORRECTION_CONTEXT=false
   ```
2. Run the rollback migration:
   ```bash
   psql $DATABASE_URL -f compliance-agent/database/migrations/010_add_correction_embeddings_rollback.sql
   ```
3. Restart the bot.
4. Verify: send a query Claude has previously corrected and confirm the correction does not appear
   in the LangSmith trace metadata (`corrections_injected` should be `0` or absent).
```

---

# Part 9 — Dependencies and Prerequisites

Verify all dependencies before beginning any phase. Phases that list a data dependency on a previous phase cannot start until that phase is complete and verified.

## Template

```markdown
## Dependencies

### External dependencies
- [ ] {{Service}} running at {{URL/port}}
  Verify with: {{health check command}}
  Expected: {{expected output}}
  Restart if offline: {{restart command}}

### Code dependencies
- [ ] {{Branch or PR}} merged to main — {{why it is needed}}

### Data dependencies
- [ ] {{Table or dataset}} exists — required before Phase {{N}} starts
  Verify with:
  SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{{table}}';
  -- Expected: 1
```

## Compliance Agent Example

```markdown
## Dependencies

### External dependencies

- [ ] MCP server running at `localhost:8080`
  Verify with: `curl -s http://localhost:8080/health`
  Expected: `{"status": "ok"}`
  Restart if offline: `cd compliance-agent && python3 -m mcp.mcp_server > /tmp/mcp_server.log 2>&1 &`

- [ ] Redis running at `localhost:6379`
  Verify with: `redis-cli ping`
  Expected: `PONG`
  Restart if offline: `brew services restart redis` (macOS) or `sudo systemctl restart redis` (Linux)

- [ ] PostgreSQL running and reachable
  Verify with: `psql $DATABASE_URL -c "SELECT 1;"`
  Expected: single row with value `1`

- [ ] LangSmith API key configured
  Verify with: `grep LANGSMITH_API_KEY .env`
  Expected: non-empty value starting with `lsv2_`

### Code dependencies

- [ ] No upstream branches required — this plan is self-contained

### Data dependencies

- [ ] `answer_feedback` table exists (Phase C depends on Phase A completing first)
  Verify with:
  ```sql
  SELECT COUNT(*) FROM information_schema.tables
  WHERE table_name = 'answer_feedback';
  -- Expected: 1
  ```

- [ ] `run_id` is non-null in recent `answer_feedback` rows before Phase B starts
  (Phase B modal writes `correction` back to the same row — a null `run_id` means
  Phase A did not complete cleanly)
  Verify with:
  ```sql
  SELECT COUNT(*) FROM answer_feedback WHERE run_id IS NULL;
  -- Expected: 0
  ```
```

---

# Part 10 — Open Questions

This section captures things that need a decision before or during execution.

Every question must have an owner. Unresolved questions that block a phase must be resolved before that phase is marked IN PROGRESS. Resolved questions remain in the table — they are the permanent audit trail for why the system was built the way it was.

## Template

```markdown
## Open Questions

| # | Question | Owner | Decision | Date resolved |
|---|----------|-------|----------|---------------|
| 1 | {{Specific decision to be made — phrase as a question with a clear yes/no or option-A/option-B answer}} | {{Named person or role}} | {{Decision text or "TBD"}} | {{YYYY-MM-DD or blank}} |
```

**Rules:**
- Every row must have an owner — a named person or a specific role (e.g. "Backend lead"), never "the team"
- A question that blocks a phase must be resolved (Decision column filled) before that phase starts
- Do not delete resolved rows — the Decision column is the permanent record of why the system was built this way
- If a decision is later reversed, add a new row rather than editing the old one

## Compliance Agent Example

| # | Question | Owner | Decision | Date resolved |
|---|----------|-------|----------|---------------|
| 1 | Should negative feedback bust only the affected user's cache keys, or the full violations cache for all users? | {{Author}} | Bust only the user's own keys (`mcp:get_user_violations:*` filtered by user context) — a single user's wrong answer does not invalidate data for other users | 2026-02-24 |
| 2 | Should the correction modal appear immediately on ❌ click, or on a separate "Add correction" button shown after the rating? | {{Author}} | Open the modal directly on ❌ click — one interaction is faster, and corrections have higher quality when captured at the moment of frustration | 2026-02-25 |
| 3 | Which embedding model for correction storage — MiniLM (local, free, 384-dim) or OpenAI `text-embedding-3-small` (API, paid, 1536-dim)? | {{Author}} | MiniLM — 384 dimensions are sufficient for short compliance queries; avoids external API dependency and cost on every correction write | 2026-02-26 |
| 4 | {{Open question text}} | {{Person or role}} | TBD | |

---

# Part 11 — Anti-Patterns

| Anti-Pattern | Why It Fails | Correct Approach |
|---|---|---|
| No status block at the top | Future agents and developers cannot tell if the plan is active, paused, or historical. An agent that follows a COMPLETE plan will duplicate already-shipped work. | Always include the status block. Update it when state changes. The status block must be the first thing in the file — above the title. |
| Goals are vague ("improve the system") | Vague goals cannot be verified. The plan is "done" by definition as soon as anyone does anything. No one can tell when the work is actually complete. | Write goals as verifiable conditions: "Slack response shows 3 buttons" not "add feedback to Slack". Each goal must be testable with a specific command or observable outcome. |
| No Non-Goals section | Without explicit scope boundaries, scope creep happens silently across phases. Agents interpret adjacent tasks as in-scope. | Add at least 3 non-goals that someone might reasonably expect to be in scope. "Automated retraining on collected feedback" and "Admin dashboard for feedback review" are valid non-goals for a feedback-capture plan. |
| Phases cannot be independently rolled back | If Phase C breaks production, you need to roll back only Phase C — not everything since Phase A. A plan with no phase-level rollback path forces all-or-nothing recovery. | Feature-flag every phase. Write a `_rollback.sql` migration for every migration file. Test the rollback before shipping the phase. |
| Files to Create/Modify table is missing | Agents touch files not listed in the plan, causing undocumented changes and scope creep. Code reviewers have no reference for what should have changed. | Every file touched must be listed. If a file is added mid-execution, update the table before making the change — not after. |
| Code snippets are pseudocode | Agents treat pseudocode as real code and fail silently when it does not import, run, or match the actual API. A snippet with `# ...` placeholder bodies provides no safety. | Write copy-paste ready snippets with real imports, real parameter names, and real return types. Test the snippet in isolation before adding it to the plan. |
| Verification steps are UI-only | UI checks do not catch data layer bugs. A button can appear to work while the Postgres write fails silently. The plan looks verified; the data is wrong. | Include at least one SQL query as a verification step per phase. The data layer must be verified independently of the UI. |
| Open Questions left unresolved at execution start | Unresolved questions become implicit decisions made under time pressure, often inconsistently across agents working in parallel on the same plan. | Resolve all blocking open questions before marking the plan IN PROGRESS. Non-blocking questions may remain open if they do not affect the current phase. |
| Plan is never updated after execution | The plan becomes stale historical fiction. Future agents and developers follow the wrong instructions. Deviations made during implementation are invisible. | Update "Actual Implementation" notes after each phase. Mark phases COMPLETE when verified. Mark the whole plan COMPLETE when all phases pass verification. |
| Single giant phase | If one phase takes three weeks and fails on day 20, there is no checkpoint to roll back to. Everything shipped in that phase is at risk. | Break phases at natural rollback points: schema migration → model layer → integration/service → UI/bot surface. Each phase should be independently deployable and rollback-able. |
| Parallel agents write to the same file without coordination | ❌ Two agents both open `slack_bot_local.py`, each add different functions, and then both write the file back. One agent's changes silently overwrite the other's. The second write wins; the first is lost with no error or warning. | Assign file ownership per agent before parallel work begins. If two agents must touch the same file, designate a merge agent that reads both agents' diffs before writing the final version. Document file assignments in a "Parallel Execution Map" within the phase. |
| A merge agent writes without reading what was already produced | ❌ Agent M is asked to "merge Agent A's output and Agent B's output." Agent M reads only the task description and writes from scratch, discarding both agents' actual work. The merged file looks complete but contains neither agent's real implementation. | A merge agent must use its Read tool on every file produced by upstream agents before writing a single line. The merge agent's first action is always to read; its last action is to verify the merged file contains all content from all inputs. |

---

# Part 12 — Quick-Start Checklist and Version History

## Quick-Start Checklist

Use this checklist before marking a plan.md as ready for execution. Every item is a yes/no answer. A plan is not execution-ready until all 15 items are checked.

```
 1. [ ] Status block is at the very top of the file (above the title)

 2. [ ] Status is set to DRAFT (not left blank, not left as a placeholder)

 3. [ ] Context section explains current state, the problem being solved, and the
        constraint driving this plan — not just "what we're building"

 4. [ ] Goals section has at least 3 goals, each verifiable with a specific command
        or observable outcome (not "improve X" or "add Y feature")

 5. [ ] Non-Goals section has at least 3 explicit scope exclusions — things a
        reasonable person might expect to be in scope but are not

 6. [ ] At least 2 implementation phases (single-phase plans rarely need a plan.md;
        a single-phase change belongs in a GitHub PR description)

 7. [ ] Each phase has a phase gate — one condition that must be true before the
        next phase starts (e.g. "Phase A verification step 4 passes")

 8. [ ] Files to Create/Modify table is complete — every file touched anywhere in
        the plan appears in this table

 9. [ ] Modify entries in the Files table name the specific function or section
        being changed, not just the filename

10. [ ] Every migration file has a corresponding rollback file listed in the table

11. [ ] Verification Steps section has at least one SQL query per phase

12. [ ] Rollback Plan covers every phase that touches the database or shared
        infrastructure (Redis, Postgres, feature flags)

13. [ ] Dependencies section lists all external services with health check commands
        and expected output

14. [ ] Open Questions table has an owner (named person or named role) for every row

15. [ ] Code snippets are copy-paste ready — real imports, real parameter names,
        real return types; no pseudocode placeholders
```

---

## Version History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0.0 | {{YYYY-MM-DD}} | {{Author}} | Initial version |

**Versioning rules for plan.md files:**

| Change type | Version bump | Example |
|-------------|-------------|---------|
| Scope change that invalidates a previously approved phase — goals change, phases removed, file table contracts broken | Major (`1.0.0` → `2.0.0`) | Phase C removed; correction embeddings descoped to next quarter |
| New phase added, new files added to the scope table, new non-goal added | Minor (`1.0.0` → `1.1.0`) | Phase D added for analytics dashboard |
| Verification step added, open question resolved, status updated, actual implementation note added | Patch (`1.0.0` → `1.0.1`) | Q3 resolved; Phase A marked COMPLETE |

A major version bump requires re-approval from whoever approved the previous version. A minor bump requires the author to notify all agents currently executing the plan. A patch bump requires no notification — it is an in-place update that improves accuracy without changing scope.

**Full version history row format:**

```markdown
| 2.0.0 | 2026-03-15 | {{Author}} | Breaking: Phase C descoped. Correction embeddings moved to separate plan. Updated non-goals, removed Phase C files from scope table. |
| 1.1.0 | 2026-03-01 | {{Author}} | Added Phase D (analytics dashboard); added 3 new files to scope table. |
| 1.0.1 | 2026-02-28 | {{Author}} | Resolved Q3 (MiniLM decision); Phase A marked COMPLETE; added verification note for redis-cli output. |
| 1.0.0 | {{YYYY-MM-DD}} | {{Author}} | Initial version. |
```

---

*Template maintained by Fivetran SysEng. Last reviewed: 2026-02-27.*
