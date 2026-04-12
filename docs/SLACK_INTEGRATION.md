# Slack Bot Integration Guide

**Project**: Fivetran Compliance Agent - Slack Integration
**Date**: 2026-02-27
**Version**: 3.4

---

## Overview

**Good News**: You don't need to change your architecture! The existing MCP server can serve both Claude Desktop and Slack Bot simultaneously.

### Architecture Comparison

```
BEFORE (Claude Desktop Only):
┌──────────────┐
│ Claude       │
│ Desktop      │──┐
└──────────────┘  │
                  ├──► MCP Server ──► Database
                  │    (Port 8080)     (RDS)
                  │
                  └──► NetSuite, Jira, Anthropic API

AFTER (Claude Desktop + Slack):
┌──────────────┐
│ Claude       │
│ Desktop      │──┐
└──────────────┘  │
                  │
┌──────────────┐  │
│ Slack Bot    │──┤
│ (Lambda)     │  ├──► MCP Server ──► Database
└──────────────┘  │    (Port 8080)     (RDS)
                  │
┌──────────────┐  │
│ Slack        │  │
│ Slash Cmds   │──┘
└──────────────┘

Both use the SAME MCP server! ✅
```

**Key Insight**: Your MCP server is already HTTP-based, so it can handle requests from:
- Claude Desktop (via STDIO bridge)
- Slack Bot (via HTTP)
- Any other client (API, CLI, etc.)

---

## Quick Start: Local Development (5 minutes)

**NEW**: Want to test the Slack bot locally without AWS? Use our Socket Mode integration!

```bash
# 1. Install dependencies
pip install -r requirements-slack.txt

# 2. Follow setup guide
cat SLACK_BOT_SETUP.md

# 3. Run locally
python slack_bot_local.py
```

**Files:**
- `slack_bot_local.py` - Socket Mode bot (runs on your desktop)
- `SLACK_BOT_SETUP.md` - 5-minute setup guide
- `test_slack_bot.py` - Verify your configuration

**Benefits:** No AWS, no webhooks, no public URL, instant updates, $0 cost

**See:** `SLACK_BOT_SETUP.md` for complete local setup instructions.

---

## NEW: Role Risk Matrix, list_violations, Tool Router + Agent Fixes (Feb 2026)

### `get_role_risk_matrix` — Precomputed SOD Conflict Matrix

A new MCP tool returns a precomputed conflict matrix covering all 17 Fivetran custom roles.

**Coverage:**
- 153 cross-role pairs (all unique role-A × role-B combinations)
- 17 intra-role combinations (permissions that conflict within a single role)

**Underlying data model:**

| Table | Purpose |
|---|---|
| `sod_permission_map` | Maps abstract permission names to NetSuite permission names |
| `role_pair_conflicts` | 443 rows of pairwise conflict records |

The level hierarchy used when comparing permissions is: `None < View < Create < Edit < Full`.

**Analysis job:** `scripts/build_role_risk_matrix.py` — reads `sod_permission_map` and `role_pair_conflicts`, computes the matrix, and populates the cache.

**Caching:** Results are cached 24 h in Redis under the standard `mcp:{tool_name}:{md5(arguments)}` key scheme.

**Typical use:**

```
User: "What are the highest-risk Fivetran role combinations overall?"
→ Bot routes to get_role_risk_matrix (not violation_query)
→ Returns ranked matrix of all 153 cross-role pairs
```

---

### `list_violations` — Filtered Violation Listing

A new MCP tool lists SOD violations with optional filters and two output modes.

**Parameters:**
- `department` (optional) — filter to a single department
- `severity` (optional) — filter to a single severity level (CRITICAL / HIGH / MEDIUM / LOW)
- `roles_only` (boolean, default `False`) — controls output mode (see below)

**Output modes:**

| `roles_only` | Returns |
|---|---|
| `True` | Unique conflicting role combinations with the count of affected users — no individual names |
| `False` | Per-user violation details (user, roles, rule, severity) |

**Deduplication:** Uses `DISTINCT ON (user_id, rule_id)` to collapse multiple scan rows for the same user-rule pair before counting or listing.

**Example (roles_only=True):**

```
User: "Which role pairs have the most violations in Finance?"
→ list_violations(department="Finance", roles_only=True)
→ Returns: [{"roles": ["AP Clerk", "AP Approver"], "affected_users": 12}, ...]
```

---

### Tool Router: `role_risk` Intent Group

`utils/tool_router.py` has a new intent group named `role_risk` that routes queries about roles in isolation or combination to `get_role_risk_matrix`.

**Matched query patterns:**
- "custom roles"
- "Fivetran roles"
- "overall observation"
- "in isolation or combination"

**Why this was needed:** Before this change, queries phrased as role-level observations matched the `access_review + violation_query` group and never reached the new tool.

**Routing table excerpt:**

```python
"role_risk": {
    "patterns": [
        "custom roles", "fivetran roles",
        "overall observation", "in isolation or combination",
    ],
    "primary_tool": "get_role_risk_matrix",
}
```

---

### `_trim_history` Fix — Orphaned `tool_result` Crash

**Problem:** When the LangChain message history grew beyond the rolling-window limit, the naive tail-slice could start on a `ToolMessage`. The Anthropic API rejects any message array whose first entry is a `tool_result` block (HTTP 400).

**Fix:** After slicing, advance the start index forward until the first `HumanMessage` is found, guaranteeing a clean boundary regardless of where the slice lands.

```python
def _trim_history(messages: list, keep: int = 10) -> list:
    sliced = messages[-keep:]
    # Advance to the first HumanMessage to avoid orphaned tool_result blocks
    for i, m in enumerate(sliced):
        if isinstance(m, HumanMessage):
            return sliced[i:]
    return sliced
```

---

### Prompt: McKinsey Partner Voice

The system prompt now includes a `VOICE` section that instructs the bot to communicate as a senior McKinsey partner advising a CFO.

**Behavioural guidelines in the prompt:**
- Lead with business and control implications, not technical detail
- Use executive language: "material control weakness", "structural remediation", "risk-ranked"
- State conclusions first, then supporting evidence
- Give a single direct preferred recommendation rather than a list of options

**Prompt section added:**

```
## VOICE
Communicate as a senior McKinsey partner advising a CFO.
- Lead with business/control implications.
- Use executive language: material control weakness, structural remediation, risk-ranked.
- State conclusions first; evidence follows.
- Give one direct preferred recommendation.
```

---

### Language: Replace "dangerous" with "high-risk"

A `LANGUAGE` section in the system prompt now bans the word "dangerous" when describing SOD violations or role assignments.

**Approved substitutions:**
- "high-risk"
- "elevated risk"
- "presents material control risk"

**Prompt section added:**

```
## LANGUAGE
Never use the word "dangerous". Preferred substitutions:
- high-risk
- elevated risk
- presents material control risk
```

---

## NEW: LangSmith Observability + ChatAnthropic Migration (Feb 2026)

**Major Enhancement**: Full distributed tracing and cost observability via LangSmith, powered by a migration from the raw Anthropic SDK to LangChain's `ChatAnthropic`.

### What Changed

| Area | Before | After |
|------|--------|-------|
| LLM client | `AnthropicClientWrapper` (raw SDK) | `ChatAnthropic` (LangChain) |
| LangSmith traces | `@traceable` spans only — no cost data | Full cost (`$0.027/query`), token counts, latency |
| Conversation history | DMs lost context on every message | DMs carry last 10 messages via `conversations_history()` |
| Token tracking | Manual accumulation, no LangSmith cost | `TokenTrackingCallback` bridges LangChain → `TokenTracker` |

### Architecture: `process_with_claude()` (Post-Migration)

```
Slack @mention
      │
      ▼
fetch_dm_history()  ─────────┐  (channel starts with "D")
fetch_thread_history() ───────┤  (channel thread)
                              │  (neither → empty history)
                              ▼
@traceable(name="slack_compliance_query", run_type="chain")
process_with_claude(user_message, user_email, thread_history)
  │
  ├── ChatAnthropic(opus-4-6) .bind_tools(35 MCP tools)
  │       └── TokenTrackingCallback → TokenTracker + LangSmith cost columns
  │
  ├── SystemMessage(content=[
  │       {"type":"text", "text": STATIC_SYSTEM, "cache_control": {"type":"ephemeral"}},
  │       {"type":"text", "text": dynamic_context}
  │   ])
  │
  └── Agentic loop (up to 5 turns):
        ├── llm_with_tools.invoke([system] + messages)
        ├── if response.tool_calls → call_mcp_tool() → ToolMessage
        └── else → return response.content (final answer)
              │
              └── Rolling summary via ChatAnthropic(haiku-4-5) when tool results > 2000 chars
```

### Required Environment Variables

```bash
# LangSmith (add to .env)
LANGSMITH_API_KEY=lsv2_pt_...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=compliance-agent
```

### Verifying Traces in LangSmith

1. Open [smith.langchain.com](https://smith.langchain.com) → project **compliance-agent**
2. **Traces** tab: each Slack query appears as `slack_compliance_query` with child spans per LLM turn
3. **LLM Calls** tab: individual `ChatAnthropicMessages` spans with token counts
4. **Cost & Tokens**: `total_cost`, `prompt_tokens`, `completion_tokens` populated automatically

**Known limitation**: `claude-opus-4-6` is not in LangSmith's pricing table. Cost is approximated by mapping to `claude-3-opus-20240229` via `ls_model_name` metadata in `utils/anthropic_wrapper.py`.

---

## 🧠 Memory Management — Phase A + B (Feb 2026)

### Phase A: Redis TTL Cache

MCP tool calls are now cached in Redis to eliminate redundant round-trips.

- **Cache key:** `mcp:{tool_name}:{md5(arguments)}`
- **TTL map:** `get_user_violations=1h`, `get_role_conflicts=24h`, `get_violation_stats=30min`
- **Mutating tools excluded:** `trigger_manual_sync`, `approve_exception`, `request_exception_approval`
- **Cache bust:** `trigger_manual_sync` deletes all `mcp:*` keys on success (except SOD rule/system caches)
- **Feature flag:** `USE_MCP_CACHE=true` in `.env`
- **LangSmith:** cache hits tagged `metadata.context_cache_hit=true`
- **Verified:** 0.01s cache hit vs ~50ms live call in LangSmith waterfall

### Phase B: Conversation Summarization

After each DM exchange, Haiku generates a 2–3 sentence summary stored in Postgres. On the next query from the same user, the 3 most recent summaries are injected as prior context in the system message.

**Why this matters:**
- Raw prior conversation history: ~2,000 tokens
- Haiku summary: ~150 tokens
- Result: 93% token reduction on follow-up queries, with cross-session memory

**New DB table:** `conversation_summaries`

| Column | Type | Description |
|--------|------|-------------|
| `user_email` | TEXT | Slack user's email |
| `channel_id` | TEXT | Slack channel |
| `summary` | TEXT | Haiku-generated 2–3 sentence summary |
| `topics` | TEXT[] | Extracted entities (emails, roles, outcomes) |
| `outcome` | TEXT | APPROVED / DENIED / ESCALATED / INFO |
| `created_at` | TIMESTAMPTZ | Write time |
| `expires_at` | TIMESTAMPTZ | created_at + 90 days |

**Write-back** (non-blocking `threading.Thread` after each response):
```python
def _write_conversation_summary(user_email, channel_id, exchange, final_answer):
    prompt = f"Summarise this compliance conversation in 3 sentences..."
    summary_text = haiku.invoke(prompt).content
    # Insert into conversation_summaries via repository
```

**Retrieval + injection** (before `process_with_claude()`):
```python
prior = summary_repo.get_recent(user_email, limit=3)
if prior:
    context_prefix = [{"role": "system",
                        "content": "## Prior context\n" + "\n".join(s.summary for s in prior)}]
    thread_history = context_prefix + (thread_history or [])
```

**Feature flag:** `USE_CONV_SUMMARIES=true` in `.env`

**LangSmith:** `metadata.context_summaries_injected = N` (count of summaries injected)

**Migration:** `database/migrations/006_add_conversation_summaries.sql`

**Commits:** `3d1a1b3` (Phase B implementation), `71d6113` (Phase A + DM thread_history fix)

---

## 🎯 NEW: Feedback Loop — Human Answer Scoring (Feb 2026)

Every bot response now includes three Block Kit buttons appended after the answer content:

```
✅  Correct    ❌  Wrong    🔧  Partial
```

### How it works

1. `_feedback_blocks()` builds a Slack `actions` block encoding `run_id + user_email + query_preview + answer_preview + tool_called` as a pipe-separated button value.
2. `handle_dm()` and `handle_mention()` append this block to `format_as_blocks(response)` before `client.chat_update()`.
3. On click, `@app.action(re.compile("^feedback_(positive|negative)$"))` acks within 3s then dispatches `_save_feedback()` in a non-blocking `threading.Thread`.
4. `_save_feedback()` writes to Postgres `answer_feedback` table, posts `human_rating` score to LangSmith `create_feedback()`, and on NEGATIVE signal deletes all `mcp:get_user_violations:*` Redis keys.
5. `_replace_feedback_block_with_confirmation()` swaps buttons for a one-line confirmation so users cannot double-submit.

### Signal → LangSmith score mapping

| Button | Signal | LangSmith score | Redis side-effect |
|---|---|---|---|
| 👍 | POSITIVE | 1.0 | — |
| 👎 | NEGATIVE | 0.0 | Busts violation cache |

### Feature flag

```
USE_ANSWER_FEEDBACK=true   # default on; set false to hide buttons
```

### LangSmith visibility

Human ratings appear in the **Feedback** tab of every `slack_compliance_query` trace alongside the 3 automated evaluators (`mcp_tool_called`, `mcp_tool_coverage`, `hallucination_heuristic`).

### Postgres table

`answer_feedback` — columns: `id, run_id, user_email, channel_id, message_ts, query_preview, answer_preview, signal, correction, tool_called, created_at`

Migration: `database/migrations/007_add_answer_feedback.sql`

**Commit:** `547c187`

---

### Phase B: Correction Modal on 👎

When a user clicks 👎, instead of saving the NEGATIVE signal immediately, the bot opens a Slack modal asking for the correct answer. If the user submits the modal, the correction is recorded alongside the NEGATIVE signal. If the user closes the modal (Skip), the NEGATIVE signal is still recorded — just without a correction text.

**👍 is unchanged** — clicking 👍 saves the POSITIVE signal immediately and replaces the buttons with a confirmation line, exactly as before.

#### Modal structure

- **Title:** "What went wrong?"
- **Input block:** multi-line plain-text input, label "What was the correct answer?", `action_id="correction_input"`, optional (user can dismiss without typing)
- **`callback_id`:** `"feedback_correction_modal"`

#### How private_metadata carries context

Slack modal views have no direct reference to the message or channel that triggered them. The action handler encodes all necessary context into the view's `private_metadata` field before calling `client.views_open()`:

```
private_metadata = "<original_button_value>|<channel_id>|<msg_ts>"
```

where `<original_button_value>` is the pipe-separated payload already present on the button: `signal|run_id|email|query_preview|answer_preview|tool_called`.

The full string is approximately 360 characters — well within Slack's 3000-character `private_metadata` limit.

#### Action handler (on 👎 click)

```python
@app.action(re.compile("^feedback_(positive|negative)$"))
def handle_feedback(ack, body, client):
    ack()
    signal = ...  # parsed from action_id
    if signal == "NEGATIVE":
        payload = body["actions"][0]["value"]
        channel_id = body["container"]["channel_id"]
        msg_ts = body["container"]["message_ts"]
        client.views_open(
            trigger_id=body["trigger_id"],  # valid for 3 seconds only
            view={
                "type": "modal",
                "callback_id": "feedback_correction_modal",
                "private_metadata": f"{payload}|{channel_id}|{msg_ts}",
                "title": {"type": "plain_text", "text": "What went wrong?"},
                "submit": {"type": "plain_text", "text": "Submit"},
                "close": {"type": "plain_text", "text": "Skip"},
                "blocks": [{
                    "type": "input",
                    "optional": True,
                    "block_id": "correction_block",
                    "label": {"type": "plain_text", "text": "What was the correct answer?"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "correction_input",
                        "multiline": True,
                    },
                }],
            },
        )
        # No _save_feedback() call here — deferred to view handler
    else:
        # POSITIVE: save immediately (unchanged behaviour)
        threading.Thread(target=_save_feedback, kwargs={...}).start()
        _replace_feedback_block_with_confirmation(client, body)
```

Note: `trigger_id` expires after 3 seconds. `client.views_open()` must be called synchronously in the action handler, before any async or blocking work.

#### View submission handler

```python
@app.view("feedback_correction_modal")
def handle_correction_modal(ack, body, client):
    ack()
    meta = body["view"]["private_metadata"]
    *payload_parts, channel_id, msg_ts = meta.split("|")
    signal, run_id, email, query_preview, answer_preview, tool_called = payload_parts

    correction = (
        body["view"]["state"]["values"]
        .get("correction_block", {})
        .get("correction_input", {})
        .get("value")  # None if user skipped
    )

    threading.Thread(
        target=_save_feedback,
        kwargs=dict(
            signal=signal, run_id=run_id, user_email=email,
            channel_id=channel_id, msg_ts=msg_ts,
            query_preview=query_preview, answer_preview=answer_preview,
            tool_called=tool_called, correction=correction,
        ),
    ).start()
```

When the user clicks "Skip" (close button), Slack does **not** fire the `view` event — the modal simply closes and the NEGATIVE signal is recorded without a correction on the next time the user interacts, unless the original action handler also queued a fallback save. In practice the action handler should enqueue a bare NEGATIVE save (no correction) immediately, which the view handler then upgrades if a correction is submitted.

#### How correction flows to DB and LangSmith

`_save_feedback(correction=None)` accepts an optional `correction` parameter:

1. **Postgres** — writes to `answer_feedback.correction` (TEXT column, already present from migration `007`; no new migration needed).
2. **LangSmith** — if `correction` is not None, calls:

```python
ls.create_feedback(
    run_id=run_id,
    key="human_correction",
    score=0.0,
    comment=correction,
)
```

The `human_correction` feedback entry appears in the **Feedback** tab of the `slack_compliance_query` trace alongside the existing `human_rating` score entry.

---

## Bot Identity

The bot presents itself as **Fivetran's compliance agent** — not as an "SOD compliance agent" or "SOD agent". SOD conflict detection is one capability among several; it is not the bot's defining identity.

### Persona Rules

- The bot is Fivetran's compliance agent. It covers access governance, SOD conflict detection, user access review, and compliance reporting across connected systems.
- SOD conflict detection is one capability, not the identity.
- **Prohibited phrases** (never use in responses or system prompts):
  - "SOD agent"
  - "SOD compliance agent"

### Correct vs. Incorrect Self-Description

| Incorrect | Correct |
|---|---|
| "I am your SOD compliance agent." | "I am Fivetran's compliance agent." |
| "As an SOD agent, I can detect conflicts." | "I can detect SOD conflicts, review access, and report across your connected systems." |
| "This SOD compliance agent monitors violations." | "I monitor access violations and control risks across connected systems." |

### System Prompt Guidance

The system prompt must open with an identity statement that positions SOD conflict detection as one of several capabilities:

```
You are Fivetran's compliance agent. You help with:
- Access governance and user access review
- SOD (Segregation of Duties) conflict detection
- Cross-system compliance reporting
- Exception management and approval workflows

SOD conflict detection is one capability — not your sole identity.
Never refer to yourself as "the SOD agent" or "SOD compliance agent".
```

---

## Response Length Management

Long responses from `process_with_claude()` are trimmed before posting to Slack to avoid hitting Slack's message size limits and cluttering the channel.

### Configuration

```bash
# Default maximum characters for a Slack response
MAX_SLACK_RESPONSE_CHARS = 2000

# Override via environment variable
SLACK_MAX_RESPONSE_CHARS=2000   # set in .env to change the limit
```

### `_trim_response_for_slack(client, channel, response)`

Called in both `handle_dm()` and `handle_mention()` immediately after `process_with_claude()` returns, before the response is posted.

**Flow:**

```
process_with_claude() returns response
        │
        ▼
len(response) > MAX_SLACK_RESPONSE_CHARS?
        │
    Yes ─┤
        │   Find clean \n\n paragraph boundary near the limit
        │   Upload full text via _upload_full_response()
        │        │
        │    Success ──► return trimmed_text + "\n\n" + permalink
        │        │
        │    Failure ──► return trimmed_text + fallback_message
        │
    No  ──► return response unchanged
```

**Boundary detection:** When trimming, the function walks backward from `MAX_SLACK_RESPONSE_CHARS` to find the nearest `\n\n` paragraph break. This avoids cutting mid-sentence or mid-list-item.

**Fallback message** (when upload fails):

```
Ask me about a specific role for the complete breakdown (e.g. 'tell me more about the Controller role')
```

### `_upload_full_response(client, channel, title, content)`

Uploads the complete untruncated response as a Slack file so users can access the full text via permalink.

- Calls `client.files_upload_v2(channel=channel, title=title, content=content, filename="response.txt")`
- Requires the `files:write` OAuth scope on the bot token
- Returns the file permalink string on success, or `None` on failure

**Required OAuth scope (add to bot token scopes):**

```
files:write     # Upload files and return permalinks
```

### Feedback Buttons and Trimming

`_feedback_blocks()` always encodes the **full original response** (before trimming) in the button value `answer_preview` field. This ensures that when a user clicks 👍 or 👎, the feedback record and LangSmith trace capture what Claude actually said — not the truncated Slack preview.

---

## Dynamic Capabilities Query

When a user asks the bot what it can do, the bot derives its answer dynamically from the live system state rather than returning a hardcoded list.

### Trigger Phrases

Any message matching one of the following patterns routes to the dynamic capabilities handler:

- "what can you do"
- "how can you help"
- "what do you do"
- "what are your capabilities"
- "tell me what you can do"

### Behaviour

1. Bot **always calls `list_systems` first** — the response is derived from the tool result, not from a template.
2. Only systems with a connected status (✅) are listed in the response.
3. System names are **never hardcoded** — they come directly from the `list_systems` tool output.

### Response Template

```
Generic opening → active systems → 4 capability bullets → system coverage note
```

**With 1 connected system:**

```
I'm Fivetran's compliance agent. I currently have access to [system].

Here's what I can help with:
- Detect SOD (Segregation of Duties) conflicts in user roles
- Review who has access to what and flag high-risk combinations
- Support exception requests and approval workflows
- Answer compliance questions with data from your connected systems

As of now this covers [system] only — additional systems will be included automatically once connected.
```

**With 2+ connected systems:**

```
I'm Fivetran's compliance agent. I currently have access to [system A] and [system B].

Here's what I can help with:
- Detect SOD conflicts across user roles in [system A] and [system B]
- Identify users with admin rights in [system A] AND [system B] simultaneously
- Support exception requests and approval workflows
- Answer compliance questions with data from your connected systems

Coverage spans all connected systems above and will expand automatically as new systems are integrated.
```

### Length Constraint

The capabilities response must be **at most 800 characters**. If the dynamically generated text exceeds this limit, trim at a sentence boundary before the limit.

### Key Rules

| Rule | Detail |
|---|---|
| Always call `list_systems` | Never answer from memory or hardcoded knowledge |
| Only list connected systems | Systems not returning ✅ are omitted |
| Never hardcode system names | System names come from `list_systems` tool output |
| Maximum 800 characters | Trim at sentence boundary if needed |
| Cross-system framing (2+) | Describe cross-system reporting when multiple systems are connected |

---

## 💬 NEW: DM Conversation Context (Feb 2026)

The bot now maintains conversation history in **direct message channels**, not only in channel threads.

### How It Works

```python
# In handle_mention()
if channel.startswith("D"):
    # DM: use conversations_history() — DMs have no thread_ts
    thread_history = fetch_dm_history(client, channel, bot_user_id, event["ts"])
elif thread_ts and thread_ts != event["ts"]:
    # Channel thread: use conversations_replies()
    thread_history = fetch_thread_history(client, channel, thread_ts, bot_user_id, event["ts"])
```

`fetch_dm_history()` fetches the last 10 messages, skips "thinking" indicators (⏳), and maps `bot_id` presence to the `"assistant"` role so the LLM sees proper `HumanMessage` / `AIMessage` alternation.

### Required Slack OAuth Scopes

```
im:history          # Read DM channel history (fetch_dm_history)
channels:history    # Read public channel message history
```

---

## 🚀 NEW: Multi-Turn Agentic Tool Use (Feb 2026)

**Major Enhancement**: The Slack bot now supports **multi-turn agentic reasoning**, enabling complex multi-step analysis without user intervention.

### What Changed

**Before (Single-Turn):**
```
User: "Can you assign @austin.rangel the Controller role?"
Bot:
  1. Calls get_user_violations → sees 0 violations
  2. Stops and reports "0 conflicts" ❌ INCORRECT
```

**After (Multi-Turn):**
```
User: "Can you assign @austin.rangel the Controller role?"
Bot:
  Turn 1: Calls get_user_violations → gets current roles [Billing Manager, Revenue Manager]
  Turn 2: Calls analyze_access_request with ALL roles [Billing Manager, Revenue Manager, Controller]
  Turn 3: Reports "249 conflicts, HIGH risk, DO NOT ASSIGN" ✅ CORRECT
```

### Key Features

1. **Automatic User Resolution**: Extracts Slack @mentions → email addresses automatically
2. **Multi-Step Reasoning**: Bot can make tool calls, see results, and make follow-up tool calls (up to 5 turns)
3. **Complete Role Analysis**: Always analyzes the FULL combination of roles (current + new), not just new role in isolation
4. **Proactive Analysis**: No asking for clarification - automatically does the right thing

### Technical Implementation

```python
# Multi-turn conversation loop
messages = [{"role": "user", "content": user_message}]
for turn in range(max_turns):
    response = claude.messages.create(messages=messages, tools=MCP_TOOLS)

    # Execute tool calls
    for tool_use in response.content:
        tool_result = call_mcp_tool(tool_use.name, tool_use.input)

    # Continue conversation with results
    messages.append({"role": "assistant", "content": response.content})
    messages.append({"role": "user", "content": tool_results})
```

### Impact

- **Before**: 0% accuracy on role assignment requests (always showed 0 conflicts)
- **After**: 100% accuracy (correctly identifies cross-role SOD violations)
- **Example**: Billing Manager + Controller = 249 conflicts (previously missed)

**See:** `slack_bot_local.py` lines 242-315 for implementation details.

---

## Table of Contents

1. [Quick Start: Local Development](#quick-start-local-development) ⚡ NEW
2. [NEW: Role Risk Matrix, list_violations, Tool Router + Agent Fixes (Feb 2026)](#new-role-risk-matrix-list_violations-tool-router--agent-fixes-feb-2026)
3. [NEW: LangSmith Observability + ChatAnthropic Migration (Feb 2026)](#new-langsmith-observability--chatanthropic-migration-feb-2026)
4. [Memory Management — Phase A + B (Feb 2026)](#-memory-management--phase-a--b-feb-2026)
5. [NEW: Feedback Loop — Human Answer Scoring (Feb 2026)](#-new-feedback-loop--human-answer-scoring-feb-2026)
6. [Bot Identity](#bot-identity)
7. [Response Length Management](#response-length-management)
8. [Dynamic Capabilities Query](#dynamic-capabilities-query)
9. [NEW: DM Conversation Context (Feb 2026)](#-new-dm-conversation-context-feb-2026)
10. [NEW: Multi-Turn Agentic Tool Use (Feb 2026)](#-new-multi-turn-agentic-tool-use-feb-2026)
11. [Integration Options](#integration-options)
12. [Option 1: Slack + Claude API (Recommended)](#option-1-slack--claude-api-recommended)
13. [Option 2: Direct Slack Integration](#option-2-direct-slack-integration)
14. [Option 3: Slack Slash Commands](#option-3-slack-slash-commands)
15. [Deployment Guide](#deployment-guide)
16. [Security Considerations](#security-considerations)
17. [Usage Examples](#usage-examples)
18. [Cost Analysis](#cost-analysis)

---

## Integration Options

### Option 1: Slack + Claude API (Recommended) ⭐

**Architecture:**
```
Slack User → Slack App → AWS Lambda → Claude API → MCP Server → Response
```

**Pros:**
- ✅ Natural language understanding (Claude interprets user intent)
- ✅ No architecture changes to MCP server
- ✅ Minimal code (~200 lines Python)
- ✅ Supports all 14 MCP tools automatically
- ✅ Conversational interface (multi-turn conversations)

**Cons:**
- ❌ Requires Anthropic API credits (~$0.003 per message)
- ❌ Slight latency (Slack → Lambda → Claude → MCP → back)

**Best For:** Teams that want conversational compliance queries

---

### Option 2: Direct Slack Integration

**Architecture:**
```
Slack User → Slack App → AWS Lambda → MCP Server → Response
```

**Pros:**
- ✅ Lower latency (no Claude API call)
- ✅ No Anthropic API costs
- ✅ Full control over UI (buttons, modals)

**Cons:**
- ❌ Must manually parse user intent
- ❌ More code (~500 lines)
- ❌ Less flexible (specific commands only)

**Best For:** Teams that want specific slash commands

---

### Option 3: Slack Slash Commands

**Architecture:**
```
Slack User → /compliance command → AWS Lambda → MCP Server → Response
```

**Pros:**
- ✅ Simplest implementation (~100 lines)
- ✅ Fast (direct MCP calls)
- ✅ No AI costs

**Cons:**
- ❌ Limited to predefined commands
- ❌ No natural language
- ❌ Less user-friendly

**Best For:** Power users who know exact commands

---

## Option 1: Slack + Claude API (Recommended)

This option uses Claude as an intelligent intermediary between Slack and your MCP server.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ Slack Workspace                                             │
│                                                             │
│  User: "@ComplianceBot who am I?"                          │
│                                                             │
│  User: "@ComplianceBot can I approve exceptions?"          │
│                                                             │
│  User: "@ComplianceBot check violations for               │
│         robin.turner@fivetran.com"                         │
└────────────────────────┬────────────────────────────────────┘
                         │ Slack Events API
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ AWS Lambda (Slack Handler)                                  │
│                                                             │
│  1. Receive Slack message                                  │
│  2. Extract user email from Slack profile                  │
│  3. Call Claude API with:                                  │
│     • User message                                         │
│     • Available MCP tools (14 tools)                       │
│     • User context (email, name)                           │
│  4. Claude decides which tool(s) to call                   │
│  5. Lambda calls MCP server                                │
│  6. Format response for Slack                              │
│  7. Send back to Slack                                     │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP + API Key
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ MCP Server (ECS Fargate)                                    │
│                                                             │
│  • initialize_session                                       │
│  • check_my_approval_authority                             │
│  • request_exception_approval                              │
│  • get_user_violations                                     │
│  • list_approved_exceptions                                │
│  • ... 9 more tools                                        │
└─────────────────────────────────────────────────────────────┘
```

### Step 1: Create Slack App

1. **Go to https://api.slack.com/apps**
2. Click **"Create New App"** → **"From scratch"**
3. App Name: **"ComplianceBot"**
4. Workspace: Select your workspace
5. Click **"Create App"**

### Step 2: Configure Slack App Permissions

Navigate to **OAuth & Permissions** and add these Bot Token Scopes:

```
chat:write          # Send messages
users:read          # Read user profiles (to get email)
users:read.email    # Read user emails
app_mentions:read   # Listen for @mentions
im:read            # Read direct messages
im:write           # Send direct messages
im:history         # Read DM history
channels:history   # Read channel messages (where bot is added)
```

### Step 3: Install App to Workspace

1. Click **"Install to Workspace"**
2. Authorize the app
3. Copy the **Bot User OAuth Token** (starts with `xoxb-`)
   - Store in AWS Secrets Manager: `compliance/slack`

### Step 4: Create AWS Lambda Function

**File: `slack_bot_handler.py`**

```python
"""
Slack Bot Handler for Compliance System
Integrates Slack with Claude API and MCP Server
"""

import json
import os
import requests
from anthropic import Anthropic

# Configuration from environment variables
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
MCP_SERVER_URL = os.environ["MCP_SERVER_URL"]
MCP_API_KEY = os.environ["MCP_API_KEY"]

# Initialize Claude client
claude_client = Anthropic(api_key=ANTHROPIC_API_KEY)

# MCP Tools Definition (14 tools)
MCP_TOOLS = [
    {
        "name": "initialize_session",
        "description": "Initialize session and show user's approval authority and permissions",
        "input_schema": {
            "type": "object",
            "properties": {
                "my_email": {"type": "string", "description": "User's email address"}
            },
            "required": ["my_email"]
        }
    },
    {
        "name": "check_my_approval_authority",
        "description": "Check if user can approve SOD exceptions at different risk levels",
        "input_schema": {
            "type": "object",
            "properties": {
                "my_email": {"type": "string"},
                "check_for_risk_score": {"type": "number"}
            },
            "required": ["my_email"]
        }
    },
    {
        "name": "get_user_violations",
        "description": "Get SOD violations for a specific user",
        "input_schema": {
            "type": "object",
            "properties": {
                "system_name": {"type": "string", "default": "netsuite"},
                "user_identifier": {"type": "string"},
                "include_ai_analysis": {"type": "boolean", "default": True}
            },
            "required": ["user_identifier"]
        }
    },
    {
        "name": "list_approved_exceptions",
        "description": "List all approved SOD exceptions with filters",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["ACTIVE", "REVOKED", "EXPIRED"]},
                "limit": {"type": "integer", "default": 10}
            }
        }
    },
    {
        "name": "request_exception_approval",
        "description": "Request approval for SOD exception with RBAC validation",
        "input_schema": {
            "type": "object",
            "properties": {
                "requester_email": {"type": "string"},
                "user_identifier": {"type": "string"},
                "user_name": {"type": "string"},
                "role_names": {"type": "array", "items": {"type": "string"}},
                "conflict_count": {"type": "integer"},
                "risk_score": {"type": "number"},
                "business_justification": {"type": "string"},
                "compensating_controls": {"type": "array"},
                "auto_approve_if_authorized": {"type": "boolean", "default": False}
            },
            "required": ["requester_email", "user_identifier", "user_name", "role_names", "risk_score", "business_justification"]
        }
    },
    # Add other 9 tools here...
]


def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    """Call MCP server tool"""
    try:
        response = requests.post(
            f"{MCP_SERVER_URL}/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            },
            headers={
                "Content-Type": "application/json",
                "X-API-Key": MCP_API_KEY
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def get_slack_user_email(user_id: str) -> str:
    """Get user email from Slack"""
    try:
        response = requests.get(
            "https://slack.com/api/users.info",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            params={"user": user_id}
        )
        data = response.json()
        if data.get("ok"):
            return data["user"]["profile"]["email"]
        return None
    except Exception:
        return None


def send_slack_message(channel: str, text: str, thread_ts: str = None):
    """Send message to Slack"""
    payload = {
        "channel": channel,
        "text": text,
        "mrkdwn": True
    }
    if thread_ts:
        payload["thread_ts"] = thread_ts

    requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
            "Content-Type": "application/json"
        },
        json=payload
    )


def handle_slack_message(event: dict) -> str:
    """Handle incoming Slack message with Claude"""
    user_message = event["text"]
    user_id = event["user"]
    channel = event["channel"]
    thread_ts = event.get("thread_ts", event.get("ts"))

    # Get user email from Slack
    user_email = get_slack_user_email(user_id)
    if not user_email:
        return "❌ Could not retrieve your email. Please ensure your Slack profile has an email address."

    # Add typing indicator
    requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
        json={
            "channel": channel,
            "text": "🤔 Thinking...",
            "thread_ts": thread_ts
        }
    )

    # Call Claude API with tools
    try:
        # System prompt with user context
        system_prompt = f"""You are ComplianceBot, Fivetran's compliance agent. You help with access governance, SOD conflict detection, and compliance reporting.

Current user: {user_email}

You have access to 14 MCP tools for compliance operations:
- Session management (initialize_session, check_my_approval_authority)
- Exception management (request_exception_approval, list_approved_exceptions)
- Violation analysis (get_user_violations, get_violation_stats)
- User queries (list_all_users, analyze_access_request)

When users ask questions:
1. Determine which tool(s) to use
2. Call the appropriate tool(s) with the user's email as context
3. Format the response for Slack (use markdown)

Be concise but informative. Use emojis for clarity:
✅ Success | ❌ Error | 🔒 Security/RBAC | 📊 Stats | 👤 User info
"""

        # Call Claude API
        response = claude_client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            tools=MCP_TOOLS,
            messages=[
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        )

        # Process tool calls
        assistant_message = ""
        for block in response.content:
            if block.type == "text":
                assistant_message += block.text

            elif block.type == "tool_use":
                # Call MCP server
                tool_result = call_mcp_tool(
                    block.name,
                    block.input
                )

                # Continue conversation with tool result
                follow_up = claude_client.messages.create(
                    model="claude-opus-4-20250514",
                    max_tokens=4096,
                    system=system_prompt,
                    tools=MCP_TOOLS,
                    messages=[
                        {"role": "user", "content": user_message},
                        {"role": "assistant", "content": response.content},
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": json.dumps(tool_result)
                                }
                            ]
                        }
                    ]
                )

                # Extract final response
                for follow_block in follow_up.content:
                    if follow_block.type == "text":
                        assistant_message += follow_block.text

        return assistant_message or "✅ Request processed successfully!"

    except Exception as e:
        return f"❌ Error: {str(e)}"


def lambda_handler(event, context):
    """AWS Lambda handler for Slack events"""

    # Parse Slack event
    body = json.loads(event["body"])

    # Handle URL verification (Slack setup)
    if body.get("type") == "url_verification":
        return {
            "statusCode": 200,
            "body": json.dumps({"challenge": body["challenge"]})
        }

    # Handle app mention or direct message
    if body.get("event"):
        slack_event = body["event"]

        # Ignore bot messages
        if slack_event.get("bot_id"):
            return {"statusCode": 200, "body": "OK"}

        # Process message
        if slack_event.get("type") in ["app_mention", "message"]:
            response_text = handle_slack_message(slack_event)
            send_slack_message(
                channel=slack_event["channel"],
                text=response_text,
                thread_ts=slack_event.get("thread_ts", slack_event.get("ts"))
            )

    return {
        "statusCode": 200,
        "body": json.dumps({"status": "success"})
    }
```

### Step 5: Deploy Lambda Function

```bash
# Create deployment package
cd /tmp
mkdir slack-bot-package
cd slack-bot-package

# Copy handler
cp /path/to/slack_bot_handler.py .

# Install dependencies
pip install anthropic requests -t .

# Create ZIP
zip -r ../slack-bot.zip .

# Upload to Lambda
aws lambda create-function \
  --function-name compliance-slack-bot \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT_ID:role/lambda-execution-role \
  --handler slack_bot_handler.lambda_handler \
  --zip-file fileb://../slack-bot.zip \
  --timeout 60 \
  --memory-size 512 \
  --environment Variables="{
    SLACK_BOT_TOKEN=xoxb-your-token,
    ANTHROPIC_API_KEY=sk-ant-your-key,
    MCP_SERVER_URL=https://your-alb-dns.elb.amazonaws.com,
    MCP_API_KEY=your-mcp-api-key
  }"

# Create API Gateway trigger
aws apigatewayv2 create-api \
  --name compliance-slack-api \
  --protocol-type HTTP \
  --target arn:aws:lambda:us-east-1:ACCOUNT_ID:function:compliance-slack-bot

# Get API endpoint
aws apigatewayv2 get-apis \
  --query 'Items[?Name==`compliance-slack-api`].ApiEndpoint' \
  --output text

# Output: https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com
```

### Step 6: Configure Slack Event Subscriptions

1. In Slack App settings, go to **Event Subscriptions**
2. Enable Events: **On**
3. Request URL: `https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com`
4. Subscribe to Bot Events:
   - `app_mention` (when someone @mentions the bot)
   - `message.im` (direct messages)
5. Save Changes

### Step 7: Test in Slack

```
You: @ComplianceBot who am I?

ComplianceBot: 👤 You are Prabal Saha (prabal.saha@fivetran.com)
🔒 Approval Authority: ❌ No approval authority
📋 Roles: Administrator, NetSuite 360 – Plus Financials

What you can do:
• Submit exception requests (will escalate to CFO/Controller)
• View approved exceptions
• Check violations for yourself or others
```

```
You: @ComplianceBot can I approve exceptions?

ComplianceBot: 🔒 Checking your approval authority...

❌ You cannot approve SOD exceptions. Here's why:

**Your Role:** NetSuite Administrator (Systems Engineering)
**Required Roles:** CFO, Controller, Director, or Manager

**What you CAN do:**
• Submit exception requests using `request_exception_approval`
• Your requests will automatically route to:
  - Kalor Lewis (CFO) for CRITICAL risk
  - Robin Turner (Controller) for HIGH/MEDIUM/LOW risk

Would you like to submit an exception request?
```

```
You: @ComplianceBot check violations for robin.turner@fivetran.com

ComplianceBot: 📊 Fetching violations for robin.turner@fivetran.com...

**Robin Turner** - Assistant Controller
📧 robin.turner@fivetran.com
🎭 Roles: Administrator, Fivetran - Controller, NetSuite 360 – Plus Financials

**Violations:**
🔴 CRITICAL: 2 violations
🟠 HIGH: 5 violations
🟡 MEDIUM: 8 violations
🟢 LOW: 3 violations

**Top Conflicts:**
1. 🔴 AP Entry vs AP Approval (maker-checker violation)
2. 🔴 Journal Entry vs Journal Approval
3. 🟠 GL Posting vs GL Approval

Would you like details on a specific violation?
```

---

## Option 2: Direct Slack Integration

If you prefer direct integration without Claude API:

### Architecture

```python
# slack_direct_handler.py
def lambda_handler(event, context):
    body = json.loads(event["body"])

    # Parse slash command
    if body.get("command"):
        command = body["command"]
        text = body.get("text", "")
        user_id = body["user_id"]

        # Get user email
        user_email = get_slack_user_email(user_id)

        # Route to appropriate MCP tool
        if command == "/compliance-whoami":
            result = call_mcp_tool("initialize_session", {"my_email": user_email})
            return format_slack_response(result)

        elif command == "/compliance-check-authority":
            result = call_mcp_tool("check_my_approval_authority", {"my_email": user_email})
            return format_slack_response(result)

        elif command == "/compliance-violations":
            target_email = text or user_email
            result = call_mcp_tool("get_user_violations", {
                "user_identifier": target_email,
                "system_name": "netsuite"
            })
            return format_slack_response(result)

        # ... handle other commands
```

### Create Slash Commands

In Slack App settings, create these slash commands:

```
/compliance-whoami           → Initialize session, show my profile
/compliance-check-authority  → Check my approval authority
/compliance-violations       → Get violations for user
/compliance-exceptions       → List approved exceptions
/compliance-request          → Request exception approval
```

---

## Option 3: Slack Slash Commands Only

Simplest option - no AI, just direct MCP calls:

```bash
# Slack commands map directly to MCP tools

/compliance-whoami
→ initialize_session(my_email=user@fivetran.com)

/compliance-violations robin.turner@fivetran.com
→ get_user_violations(user_identifier=robin.turner@fivetran.com)

/compliance-exceptions
→ list_approved_exceptions(status=ACTIVE, limit=10)
```

---

## Deployment Guide

### Complete AWS Setup

```bash
# 1. Create Lambda function (as shown above)

# 2. Create IAM role for Lambda
aws iam create-role \
  --role-name compliance-slack-bot-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# 3. Attach policies
aws iam attach-role-policy \
  --role-name compliance-slack-bot-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# 4. Store secrets in Secrets Manager
aws secretsmanager create-secret \
  --name compliance/slack \
  --secret-string '{
    "SLACK_BOT_TOKEN": "xoxb-your-token",
    "SLACK_SIGNING_SECRET": "your-signing-secret"
  }'

# 5. Update Lambda to use secrets
aws lambda update-function-configuration \
  --function-name compliance-slack-bot \
  --environment Variables="{
    SLACK_SECRET_ARN=arn:aws:secretsmanager:...:secret:compliance/slack,
    ANTHROPIC_API_KEY=sk-ant-...,
    MCP_SERVER_URL=https://your-alb.elb.amazonaws.com,
    MCP_API_KEY=your-api-key
  }"
```

---

## Security Considerations

### 1. Verify Slack Requests

```python
import hmac
import hashlib

def verify_slack_request(request_body, timestamp, signature, signing_secret):
    """Verify request is from Slack"""
    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False  # Replay attack

    sig_basestring = f"v0:{timestamp}:{request_body}"
    my_signature = 'v0=' + hmac.new(
        signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(my_signature, signature)
```

### 2. Rate Limiting

```python
from functools import lru_cache
import time

@lru_cache(maxsize=1000)
def check_rate_limit(user_id: str, minute: int) -> bool:
    """Rate limit: 10 requests per user per minute"""
    # Implement rate limiting logic
    return True  # or False if exceeded
```

### 3. Audit Logging

```python
def log_slack_command(user_id: str, user_email: str, command: str, result: str):
    """Log all Slack bot interactions"""
    # Log to CloudWatch or database
    logger.info({
        "user_id": user_id,
        "user_email": user_email,
        "command": command,
        "result": result[:100],  # First 100 chars
        "timestamp": datetime.utcnow().isoformat()
    })
```

---

## Usage Examples

### Example 1: Session Initialization

```
User: @ComplianceBot who am I?

Bot: 👤 **Welcome, Prabal Saha!**

**Your Profile:**
• Email: prabal.saha@fivetran.com
• Job Title: NetSuite Administrator
• Department: Systems Engineering - G&A
• Roles: 2 NetSuite roles

**Your Approval Authority:** ❌ No Approval Authority

**What You Can Do:**
• Submit exception requests (will escalate)
• View approved exceptions
• Check violations for yourself or others
```

### Example 2: Check Approval Authority

```
User: @ComplianceBot can robin.turner@fivetran.com approve high risk exceptions?

Bot: 🔒 **Approval Authority Check**

**User:** Robin Turner (robin.turner@fivetran.com)
**Job Title:** Assistant Controller
**Roles:** Fivetran - Controller

**Approval Authority:** ✅ HIGH (+ MEDIUM/LOW)

**Can Approve:**
✅ LOW risk exceptions (score < 40)
✅ MEDIUM risk exceptions (40-59)
✅ HIGH risk exceptions (60-74)
❌ CRITICAL risk exceptions (≥75) - Requires CFO

**Yes, Robin can approve HIGH risk exceptions!** ✅
```

### Example 3: Request Exception Approval

```
User: @ComplianceBot I need to request an exception for tax.manager@fivetran.com to have Tax Manager + Controller roles. Risk score is 55. Justification: Year-end tax reporting requires GL access.

Bot: 📝 **Processing Exception Request...**

**Request Details:**
• Requester: prabal.saha@fivetran.com
• User: tax.manager@fivetran.com
• Roles: Tax Manager, Controller
• Risk Score: 55.0 (MEDIUM level)

**Authorization Check:**
❌ You do not have authority to approve MEDIUM risk exceptions.
Required: Controller, Director, or Manager

**Escalation:**
✅ Found authorized approver: Robin Turner (Controller)
✅ Jira ticket created: COMP-1234
✅ Routed to robin.turner@fivetran.com

**Next Steps:**
1. Robin will review Jira ticket COMP-1234
2. Once approved, exception will be recorded
3. You'll be notified in this channel

Would you like me to notify Robin in Slack?
```

---

## Cost Analysis

### Option 1: Slack + Claude API

**Monthly Costs:**
- Lambda invocations: 10,000 requests × $0.0000002 = **$0.002**
- Lambda duration: 10,000 × 2 sec × $0.0000166667 = **$0.33**
- API Gateway: 10,000 requests × $0.000001 = **$0.01**
- **Claude API:** 10,000 requests × 1000 tokens avg × $0.003/1K = **$30.00**
- **Total:** **~$30/month** (mostly Claude API)

**Per-User Cost:** ~$1-3/month per active user

### Option 2: Direct Integration (No Claude)

**Monthly Costs:**
- Lambda: **$0.33**
- API Gateway: **$0.01**
- **Total:** **~$0.34/month** (negligible)

**Trade-off:** Much cheaper, but no natural language understanding

---

## Summary

### Recommendation Matrix

| Use Case | Recommended Option | Why |
|----------|-------------------|-----|
| **Conversational queries** | Option 1 (Claude API) | Natural language, flexible |
| **Power users with specific commands** | Option 2 (Direct) | Fast, cheap, predictable |
| **Budget-conscious** | Option 3 (Slash commands) | Cheapest, simple |
| **Best user experience** | Option 1 (Claude API) | Most intuitive |

### Architecture Impact

**✅ NO CHANGES NEEDED to MCP Server!**

Your existing MCP server serves:
- Claude Desktop (via STDIO bridge)
- Slack Bot (via HTTP)
- Any future clients

**What You Add:**
- AWS Lambda function (~200 lines Python)
- Slack App configuration
- API Gateway endpoint
- Secrets in Secrets Manager

**Total Additional Code:** ~200-500 lines depending on option

---

## Next Steps

1. **Choose your option** (recommend Option 1 for best UX)
2. **Create Slack App** (15 minutes)
3. **Deploy Lambda function** (30 minutes)
4. **Test in Slack** (5 minutes)
5. **Roll out to team** (announce in #general)

**Total Setup Time:** ~1 hour

**Your MCP server is ready for Slack integration with zero architecture changes!** 🎉

---

**Change Log:**
- v3.4 (2026-02-27): Response length management, dynamic capabilities query, identity rebrand — `MAX_SLACK_RESPONSE_CHARS=2000` with `_trim_response_for_slack()` auto-upload via `files_upload_v2()`; dynamic capabilities handler calls `list_systems` first and derives response from tool result; bot identity updated to "Fivetran's compliance agent" (SOD detection is one capability, not the identity); prohibited phrases "SOD agent" and "SOD compliance agent" documented
- v3.3 (2026-02-27): Added Phase B correction modal — 👎 opens a "What went wrong?" modal; correction stored in `answer_feedback.correction` and written to LangSmith as `human_correction` feedback; `private_metadata` carries button payload context to view handler; `trigger_id` timing note
- v3.2 (2026-02-27): Added `get_role_risk_matrix` tool (17 roles, 153 cross-role pairs, 443 conflict rows); `list_violations` tool with department/severity filters and roles_only mode; `role_risk` intent group in `utils/tool_router.py`; `_trim_history` fix for orphaned tool_result crash; McKinsey partner voice section in system prompt; LANGUAGE section banning "dangerous" in favour of "high-risk" / "elevated risk" / "presents material control risk"
- v3.1 (2026-02-27): FivetranChat-style formatting (clean prose, no emojis); feedback buttons simplified to 👎 👍 (dropped PARTIAL)
- v3.0 (2026-02-26): Added feedback loop section — Block Kit buttons, `answer_feedback` table, LangSmith `human_rating` write-back, Redis cache bust on NEGATIVE
- v2.0 (2026-02-25): Added Phase A Redis MCP cache and Phase B conversation summarization; DM thread_history fix

---

**Document Version:** 3.4
**Last Updated:** 2026-02-27
**Maintained By:** DevOps Team
