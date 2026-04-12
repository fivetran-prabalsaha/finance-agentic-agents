# SOD Compliance Agent — Architecture & Trust Mechanisms

**Version:** 1.2
**Last Updated:** 2026-02-26
**Audience:** Engineering team presentation

---

```
╔══════════════════════════════════════════════════════════════════════════╗
║           SOD COMPLIANCE AGENT — ARCHITECTURE + TRUST MECHANISMS        ║
╚══════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────────────┐
│  SURFACE LAYER                                                           │
│  Slack DM  ────────────────────────────────  Slack @mention             │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  PROMPT ASSEMBLY  (slack_bot_local.py L635–685)                          │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  STATIC SYSTEM PROMPT  (hardcoded, Anthropic prompt cache)      │    │  ◄── WHERE PROMPT IS STORED
│  │                                                                  │    │      L635 — inline string constant
│  │  • Role: "You are a Compliance Agent for SOD and access review" │    │      cache_control: ephemeral
│  │  • DATA GROUNDING rule: "query MCP tools before answering.      │    │      (re-used across turns,
│  │    Never generate violation counts, role lists, or risk scores  │    │       billed once)
│  │    from general knowledge. Every answer must cite a tool result"│    │
│  │  • Tool-use rules: always use include_existing_roles=true       │    │
│  │  • Formatting rules: Slack mrkdwn, no markdown tables           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  DYNAMIC CONTEXT  (assembled per request)                        │    │  ◄── WHERE GROUND TRUTH IS INJECTED
│  │                                                                  │    │
│  │  • current user email                                           │    │
│  │  • mentioned users (@handle → email map)                        │    │
│  │  • Phase B summaries: last 3 verified decisions from Postgres   │    │
│  │    (~150 tokens — Haiku-written after every DM, 90d TTL)        │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  THREAD HISTORY  (Slack API, last 10 messages)                   │    │
│  │  fetch_dm_history() / conversations_replies()                    │    │
│  │  _trim_history() caps at MAX_HISTORY_TURNS to prevent drift      │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │  full context window
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  AGENTIC LOOP  (multi-turn, up to 5 rounds)                              │
│                                                                          │
│  ┌──────────────┐     ┌────────────────────────────────────────────┐    │
│  │ Claude Haiku │────►│  Which tool(s) to call?                    │    │
│  │ tool dispatch│     │  tool_router selects 4 of 35 tools by      │    │
│  └──────────────┘     │  intent (saves ~8K tokens per request)     │    │
│                       └──────────────────┬─────────────────────────┘    │
│                                          │                               │
│                                          ▼                               │
│                       ┌────────────────────────────────────────────┐    │
│                       │  call_mcp_tool()                            │    │
│                       │                                             │    │
│                       │  1. Redis cache?  → return in ~0ms          │    │  ◄── ANTI-HALLUCINATION #1
│                       │  2. Cache miss?  → live NetSuite MCP call   │    │      Same verified data reused
│                       │  3. _sanitize_tool_output() — trim noise   │    │      within TTL, not regenerated
│                       │  4. _compress_tool_result() via Haiku      │    │
│                       │     (rolling summary of key facts only)    │    │  ◄── ANTI-HALLUCINATION #2
│                       └──────────────────┬─────────────────────────┘    │      Haiku extracts facts before
│                                          │  ToolMessage injected         │      Opus re-reads history
│                                          ▼                               │
│  ┌──────────────┐     ┌────────────────────────────────────────────┐    │
│  │ Claude Opus  │────►│  Synthesise answer from tool results only  │    │  ◄── GROUNDING ENFORCED BY PROMPT
│  │ synthesis    │     │  (switches from Haiku once ToolMessage     │    │      "Every answer must cite
│  └──────────────┘     │   present in context)                      │    │       a tool result"
│                       └────────────────────────────────────────────┘    │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │  answer + ✅❌🔧 buttons posted to Slack
                               │  + non-blocking threads:
                               │    Haiku summary   → Postgres (Phase B)
                               │    Button click     → _save_feedback() (Phase feedback)
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  FEEDBACK LOOP  (on button click, non-blocking)                          │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  _save_feedback()                                                 │   │
│  │                                                                   │   │
│  │  1. Postgres → answer_feedback table                              │   │
│  │     signal: POSITIVE 👍(1.0) | NEGATIVE 👎(0.0)                   │   │
│  │                                                                   │   │
│  │  2. LangSmith → create_feedback(run_id, human_rating=score)       │   │
│  │     Human score visible alongside 3 auto-evals in Feedback tab   │   │
│  │                                                                   │   │
│  │  3. On NEGATIVE → Redis cache bust                                │   │
│  │     delete mcp:get_user_violations:*                              │   │
│  │     Next query forces fresh live NetSuite call                    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  OBSERVABILITY + ANTI-HALLUCINATION GUARDRAILS  (LangSmith, online)      │
│                                                                          │
│  Every trace auto-evaluated by 3 online evaluators:                     │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  mcp_tool_called       score=0 if Claude answered without any   │    │  ◄── GUARDRAIL #1
│  │                        MCP tool call (pure hallucination)       │    │      Forces tool use
│  ├─────────────────────────────────────────────────────────────────┤    │
│  │  mcp_tool_coverage     score=0 if access-request query skipped  │    │  ◄── GUARDRAIL #2
│  │                        analyze_access_request                   │    │      Enforces correct workflow
│  ├─────────────────────────────────────────────────────────────────┤    │
│  │  hallucination_heuristic  score=0 if response contains raw      │    │  ◄── GUARDRAIL #3
│  │                           <tool_call> XML or ungrounded         │    │      Detects format leakage
│  │                           numeric claims                        │    │      + unsupported numbers
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  Metadata tagged per trace:                                              │
│   context_cache_hit · cache_tool · context_summaries_injected           │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  MCP SERVER  (FastAPI :8080)  ──  35 tools  ──  JSON-RPC 2.0             │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  DATA LAYER  (single source of truth)                                    │
│  NetSuite ERP  ──►  PostgreSQL  (1,928 users, 59 roles, 18 SOD rules)   │
│  APScheduler: full sync 2 AM daily · incremental hourly                 │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Anti-Hallucination — 5 Layers

```
╔══════════════════════════════════════════════════════════════════════════╗
║  ANTI-HALLUCINATION — 5 LAYERS SUMMARISED                               ║
╠══════════════════════════════════════════════════════════════════════════╣
║  Layer      │  Mechanism                          │  Where               ║
║─────────────┼─────────────────────────────────────┼─────────────────────║
║  Prompt     │  DATA GROUNDING rule in system       │  L641–646 (static   ║
║             │  prompt: "never answer from          │  system prompt)      ║
║             │  training data"                      │                      ║
║─────────────┼─────────────────────────────────────┼─────────────────────║
║  Tool use   │  Haiku forced to call MCP tools      │  tool_router L688   ║
║             │  before Opus synthesises             │  agentic loop L711  ║
║─────────────┼─────────────────────────────────────┼─────────────────────║
║  Context    │  _compress_tool_result() — Haiku     │  L455               ║
║  hygiene    │  summarises raw tool output to key   │                      ║
║             │  facts; _trim_history() caps turns   │  L444               ║
║─────────────┼─────────────────────────────────────┼─────────────────────║
║  Eval       │  3 online LangSmith evaluators fire  │  LangSmith project  ║
║             │  on every trace, score 0/1           │  compliance-agent   ║
║─────────────┼─────────────────────────────────────┼─────────────────────║
║  Human eval │  👎 👍 buttons on every response     │  answer_feedback    ║
║             │  NEGATIVE busts Redis cache —        │  Postgres table     ║
║             │  next answer uses fresh live data    │  + LangSmith        ║
║  Formatting │  Clean prose, no decorative emojis,  │  system prompt      ║
║             │  lead with answer (FivetranChat style)│  L808–818           ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## Tech Stack

```
╔══════════════════════════════════════════════════════════════════╗
║  TECH STACK                                                      ║
╠══════════════════════════════════════════════════════════════════╣
║  Layer          │  Technology                                    ║
║─────────────────┼──────────────────────────────────────────────║
║  LLM            │  Claude Haiku 4.5  (tool dispatch)            ║
║                 │  Claude Opus 4.6   (synthesis + reasoning)    ║
║─────────────────┼──────────────────────────────────────────────║
║  Agent          │  LangChain · ChatAnthropic · Slack Bolt       ║
║  Observability  │  LangSmith  (traces, cost, evaluators)        ║
║─────────────────┼──────────────────────────────────────────────║
║  Memory         │  Redis  (Phase A — TTL tool cache)            ║
║                 │  PostgreSQL  (Phase B — conv. summaries)      ║
║─────────────────┼──────────────────────────────────────────────║
║  API server     │  FastAPI + Uvicorn  (MCP, port 8080)          ║
║  Protocol       │  Model Context Protocol  (JSON-RPC 2.0)       ║
║─────────────────┼──────────────────────────────────────────────║
║  Database       │  PostgreSQL 14  +  pgvector  +  Alembic       ║
║  Scheduler      │  APScheduler                                  ║
║─────────────────┼──────────────────────────────────────────────║
║  Source system  │  NetSuite ERP  (RESTlet API, OAuth 1.0a)      ║
║  Language       │  Python 3.9                                   ║
║─────────────────┼──────────────────────────────────────────────║
║  Feedback       │  Block Kit buttons · answer_feedback          ║
║                 │  Postgres · LangSmith create_feedback()       ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## Prompt Storage & Generation — Quick Reference

| Component | Location | Generated by |
|---|---|---|
| Static system prompt | `slack_bot_local.py` L635 | Hardcoded — Anthropic prompt cache (`cache_control: ephemeral`) |
| Dynamic context | `slack_bot_local.py` L661–684 | Assembled per request — user email + @mention map |
| Prior context (Phase B) | `conversation_summaries` Postgres table | Haiku writes after each DM; retrieved by `_get_prior_summaries()` |
| Thread history | Slack API (`fetch_dm_history` / `conversations_replies`) | Last 10 messages; trimmed by `_trim_history()` |
| Tool result summaries | In-memory `ToolMessage` objects | Haiku via `_compress_tool_result()` — fires when result > 800 chars |
| Feedback context (Phase C) | `answer_feedback` Postgres table | Written by `_save_feedback()` non-blocking after button click |

---

**Maintained by:** AI Development Team
**Last Verified:** 2026-02-26
