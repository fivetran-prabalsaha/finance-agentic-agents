# Compliance Agent — Interview Q&A
*Generated: 2026-02-24 | System version: compliance-agent v2.3.0*

---

## System Design Questions (1–16)

---

**Q1. Walk me through the end-to-end flow of how a SOD violation is detected — from a NetSuite role change to a CRITICAL badge appearing on the dashboard.**

The `DataCollectionAgent` runs on APScheduler — a full sync daily at 2 AM, incremental hourly. On each cycle it calls `NetSuiteConnector.fetch_users_with_roles_sync()`, which issues paginated GET requests to the NetSuite RESTlet (page_size=200, the hard cap — a lesson from Issue #13 where requesting 1000 silently returned only 200 per page, dropping 79% of users). The fetched user/role records are upserted into PostgreSQL via `UserRepository` and `RoleRepository`.

After the sync, `SODAnalysisAgent.analyze_all_users()` iterates every active user. For each user it calls `_check_rule_violation()` against each of the 18 rules loaded from `database/seed_data/sod_rules.json`. The check is two-pronged: role-name heuristics (e.g., `Administrator` + any `Controller/Finance` role) and permission-set intersection against `conflicting_permissions.conflicts` pairs. Context-aware exemptions are applied first — IT/Systems Engineering users are exempt from financial rules, and users with an active entry in `approved_exceptions` are skipped entirely.

When a violation is found, `_calculate_violation_risk_score()` scores it 0–100 using severity base + conflict count + department + role-count penalties. A CRITICAL rule starts at 90. The result is written to the `violations` table via `ViolationRepository.create_violation()`. The dashboard (`get_violation_stats` MCP tool) reads directly from `violations` — so after the next sync the CRITICAL badge appears in the Slack bot's response to any `get_violation_stats` call.

---

**Q2. The system uses a `BaseConnector` ABC. What would you get for free if you added a Salesforce connector, and what would you have to implement?**

`BaseConnector` (`connectors/base_connector.py`) is an ABC with five `@abstractmethod` signatures: `test_connection_sync`, `get_user_count_sync`, `fetch_users_with_roles_sync`, `sync_to_database_sync`, and `get_system_type`. The `ComplianceOrchestrator` stores connectors in a plain dict — `self.connectors = {"netsuite": NetSuiteConnector()}` — and calls only these five methods. No part of the orchestrator knows which concrete class it's holding.

For Salesforce, you would implement the five abstract methods — the Salesforce REST API auth (OAuth 2.0 bearer token vs NetSuite's OAuth 1.0a HMAC-SHA256), the SOQL user/role query, and the field mapping to the standardised `{"email", "name", "roles", "department"}` dict shape.

You would get for free: the `timed_cache`-decorated `perform_access_review_sync` logic, the `get_user_violations_sync` auto-sync fallback (which already calls `connector.fetch_users_with_roles_sync()` generically), and the `list_systems` MCP tool that iterates `self.connectors` — Salesforce would appear there with zero additional code. Register it with one line: `self.connectors["salesforce"] = SalesforceConnector()`.

---

**Q3. Explain why `errors: Annotated[List[str], operator.add]` is used instead of `errors: List[str]` in `WorkflowState`. What problem would arise without it?**

In a LangGraph `WorkflowState` TypedDict, each field reducer controls how state is merged when multiple graph nodes emit partial state updates concurrently. The default reducer for a plain `List[str]` would overwrite the field entirely: if two nodes both write `errors = ["some error"]`, only the last write survives. `operator.add` makes the reducer concatenate instead — all partial error lists are accumulated:

```python
# Without Annotated — last writer wins
errors: List[str] = []

# With Annotated[List[str], operator.add] — all errors accumulated
errors: Annotated[List[str], operator.add] = []
```

The specific problem this solves is parallel fan-out. In this system, the orchestrator could dispatch a data-collection node and an analysis node simultaneously. Both may encounter errors. With a plain list, the analysis node's errors would silently overwrite the collector node's errors. With `operator.add`, the final state contains both, which is essential for the dashboard and LangSmith traces to surface every failure on a query that touched multiple sub-agents.

---

**Q4. How does the intent-routing system work, and what is the tradeoff when a new intent partially overlaps two existing ones?**

`utils/tool_router.py` implements two data structures: `INTENT_PATTERNS` (9 dicts of regex patterns, e.g. `r"\bviolation\b"` maps to `"violation_query"`) and `TOOL_GROUPS` (9 dicts mapping each intent to 3–6 tool names). `classify_intent()` scans the lowercase message against every pattern and returns all matching intents. `select_tools_for_intent()` then unions the tool lists up to `max_tools=8`, always prepending `initialize_session` and `check_my_approval_authority`. This cuts the per-request tool schema from ~10K tokens (all 35 tools) to ~1.5K tokens, an ~85% reduction.

```python
# "Can you check access request violations?" → matches both intents
intents = classify_intent(msg)  # ['access_review', 'violation_query']
tools = select_tools_for_intent(msg, MCP_TOOLS)
# → [initialize_session, check_my_approval_authority, get_user_violations,
#    analyze_access_request, validate_job_role, get_role_conflicts,
#    get_violation_stats, list_violations]  — 8 tools
```

For a new intent that partially overlaps two existing ones — say `"exception_access_review"` that needs `request_exception_approval` from `exception_mgmt` AND `get_role_conflicts` from `access_review` — the cleanest approach is to add the new intent group with the union of the needed tools, and add narrow patterns that won't fire on messages already cleanly classified to the parent intents. The tradeoff: you're now maintaining 10 groups instead of 9, and you risk the `max_tools` cap cutting off tools when 3 intents all match simultaneously. A defensive mitigation is to raise `max_tools` to 10 for multi-intent matches, at the cost of ~600 extra tokens on ambiguous queries.

---

**Q5. The MCP server always returns HTTP 200, even when a tool throws an exception. Why is this correct?**

The MCP server implements JSON-RPC 2.0 (`mcp/mcp_server.py`). In JSON-RPC 2.0, the HTTP response is merely a transport envelope — the protocol result or error lives inside the JSON body. The server correctly uses the `error` field for protocol-level failures (unknown method, missing parameter) and the `result.isError=True` field for tool execution failures:

```python
# Tool failure → HTTP 200, but result.isError = True
return MCPResponse(
    id=request_data.id,
    result={
        "content": [{"type": "text", "text": f"❌ Error: {str(e)}"}],
        "isError": True,
    }
)
```

If the server returned HTTP 500 on tool errors, it would break the MCP client (`call_mcp_tool` in `slack_bot_local.py`), which checks `response.status_code == 200` before parsing the body. An HTTP 500 would hit the `else` branch and return a generic string like `"❌ Error calling {tool_name}: HTTP 500"`, losing the actual error message from the tool. More critically, LangChain's `ChatAnthropic` is invoking these as `ToolMessage` results — a transport-level error would propagate as an exception up through the agentic loop rather than being gracefully surfaced to Claude as a failed tool result. The MCP spec deliberately separates transport errors (HTTP 4xx/5xx) from application errors (JSON-RPC `error` object) for this reason.

---

**Q6. The Haiku/Opus model switch uses `has_tool_results` instead of a turn counter. Why? What edge case does this handle?**

The switch condition in `slack_bot_local.py:461` is:

```python
has_tool_results = any(isinstance(m, ToolMessage) for m in messages)
active_model = llm_with_tools if has_tool_results else haiku_with_tools
```

A turn counter (e.g. `turn >= 1`) would switch to Opus on the second turn regardless of what happened in the first. The edge case this handles: a message where Haiku decides on turn 1 that it needs no tools at all and produces a direct answer. With a turn counter, Opus would never fire — which is fine. But the more important case is the reverse: a query that requires two consecutive tool dispatches before any results arrive (e.g., `get_user_violations` followed by `analyze_access_request`). With a turn counter switching at turn 2, Opus would attempt the second dispatch, wasting ~10x the token cost of Haiku on a purely structural routing task.

The `ToolMessage` check is semantically correct: Opus is needed exactly when there is data to reason over. Before any `ToolMessage` exists in `messages`, the agent is still in dispatch mode regardless of how many turns have elapsed. The verified trace `c06830c0` confirms this: `[haiku → call_mcp_tool → haiku → call_mcp_tool → haiku → opus]` — Haiku handles all dispatch turns and Opus fires only after tool results are in the history.

---

**Q7. What happens at the 5-turn cap if Claude hasn't produced a final answer yet? How would you redesign this for a genuinely deep workflow?**

At `max_turns=5`, if a query needs a sixth tool call, the loop exits after the fifth iteration. At that point, if the fifth turn still produced tool_calls and not a final text response, `final_text` remains `""`, and the function returns the fallback string `"I processed your request, but have nothing to report."` — the user gets a silent non-answer with no indication that the loop was truncated.

```python
for turn in range(max_turns):   # max_turns = 5
    ...
    if not response.tool_calls:
        final_text = ...
        break
# If we exit without break, final_text is still "" → fallback returned
return final_text.strip() if final_text else "I processed your request, but have nothing to report."
```

A production redesign would use three mechanisms together. First, replace the hard cap with a token budget check — track `total_output_tokens` across turns and stop when approaching the model's context limit, not an arbitrary turn count. Second, adopt a LangGraph `StateGraph` with explicit `should_continue` edge logic and a `recursion_limit` set in `RunnableConfig` — this makes early termination observable in LangSmith traces rather than silently swallowing the state. Third, for genuinely deep workflows (e.g., full-org access review that touches hundreds of users), move to async task queues (Celery is already wired in `celery_app.py`) so the Slack bot returns a job ID immediately and posts the result when the long-running task completes — avoiding the entire loop-cap problem for heavyweight operations.

---

**Q8. Walk through the prompt cache cost math. When is the cache invalidated?**

From `token_tracker.py` the pricing for `claude-opus-4.6` is:

```python
'claude-opus-4.6': {
    'input':       15.00 / 1_000_000,   # $15/M
    'cache_write': 18.75 / 1_000_000,   # $18.75/M
    'cache_read':  1.50  / 1_000_000,   # $1.50/M
}
```

For a 4,000-token system prompt: a **cache miss** (first call, writes the cache) costs 4,000 × $18.75/M = **$0.075**. A **cache hit** (subsequent calls, reads the cache) costs 4,000 × $1.50/M = **$0.006**. That is a 12.5x cost reduction per call, or $0.069 saved per request. With Slack bot traffic of even 100 queries/day, the cache saves ~$6.90/day on the system prompt alone.

The `cache_control: {"type": "ephemeral"}` annotation is placed only on the `_STATIC_SYSTEM` block in `slack_bot_local.py` (the portion that is identical across all users and turns). The `dynamic_context` block (user email + mentioned users) is intentionally left uncached because it changes per request. Anthropic's prompt cache is invalidated when: (1) the cached prefix changes — any edit to `_STATIC_SYSTEM` starts a new cache entry; (2) the cache TTL expires (5 minutes for ephemeral caches); (3) Anthropic rotates their cache infrastructure (invisible to the client, treated as a miss). This is why `_STATIC_SYSTEM` is defined as a module-level constant — it must be byte-for-byte identical on every call to get a hit.

---

**Q9. `_compress_tool_result()` fires in-loop before appending the ToolMessage. What information loss risk does this create, and how would you mitigate it?**

`_compress_tool_result()` in `slack_bot_local.py` fires in-loop, immediately after each `call_mcp_tool()` result, before appending the `ToolMessage` to `messages`. Haiku compresses to "≤150 tokens" targeting emails, role names, violation counts, risk scores, conflict names, approval status, and action items.

The structural risk is that the compressed summary becomes the only version of the tool result that future turns — including the Opus synthesis turn — ever see. If Haiku omits a fact (e.g., a `conflicting_roles` list entry, or a specific permission key name needed by a downstream `analyze_access_request` call), Claude cannot recover it because the raw output has been discarded. This is most dangerous in multi-step workflows where turn N+1's tool arguments depend on specific string values from turn N's output — for example, if `get_user_violations` returns a `violation_id` UUID that `remediate_violation` needs, and Haiku's summary drops the UUID, the follow-up tool call will fail.

Mitigations: (1) raise `ROLLING_SUMMARY_MIN_CHARS` from 800 to something closer to the actual token budget pressure point (~3000 chars) so compression only fires on genuinely large outputs; (2) add a structured pass-through for key identifiers — always preserve UUIDs, emails, and numeric scores verbatim even when summarising narrative text; (3) move compression to the `_trim_history()` path instead, so only older turns get compressed and the most recent tool result is always stored raw.

---

**Q10. `analyze_access_request` is called via `subprocess.run()`. What are the tradeoffs vs calling it in-process, and when would you refactor?**

`analyze_access_request_handler` in `mcp/mcp_tools.py` calls `scripts/analyze_access_request_with_levels.py` via `subprocess.run()` with `timeout=60`, passing role names as a CLI argument and reading output from a JSON file:

```python
cmd = ["python3", "scripts/analyze_access_request_with_levels.py",
       "--job-title", job_title, "--requested-roles", roles_arg, "--mode", "single-request"]
result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
```

The tradeoffs in favour of subprocess: the script loads heavy NetSuite configuration files (`netsuite_sod_config_unified.json`, `job_role_mappings.json`, `compensating_controls.json`) and does its own process isolation — a crash or OOM in the analysis doesn't take down the MCP server. It also allowed the analysis script to be developed and tested independently, which was the pattern used throughout the project.

The costs are significant: a cold `python3` startup adds 300–500ms; the file-based output protocol (`output/access_request_analysis.json`) is fragile under concurrent requests (two simultaneous calls would overwrite each other's output file); and `subprocess.run` with `timeout=60` blocks the FastAPI async event loop in a thread-pool thread via `asyncio.to_thread`, but if the process exceeds timeout it raises `TimeoutExpired` which the handler catches and converts to an error string. You would refactor to in-process when: the MCP server is deployed in a containerised environment with stable memory limits (so crash isolation is handled by the container runtime); when you need to support concurrent access requests without file collisions; or when the startup overhead is measurable in your p95 latency (currently the 60s timeout implies it's not the bottleneck). The refactor would instantiate `LevelBasedSODAnalyzer` once as part of `ComplianceOrchestrator.__init__` and call it directly.

---

**Q11. Why can't LangSmith evaluators read `child_run.outputs.generations`, and how does `@traceable(run_type="tool")` fix this?**

Issue #31 in `LESSONS_LEARNED.md` documents this precisely. LangSmith's evaluator executor fetches run data via the `/api/v1/runs/{id}` REST endpoint. Large output payloads — specifically LLM generation content including `tool_calls` — are offloaded to S3 and not returned inline in the API response. The executor therefore receives:

```python
child_llm_run["outputs"] == {}  # always empty in executor context
```

The Python SDK `client.list_runs()` transparently fetches from S3 on demand, which is why local dry-runs worked while the executor failed silently. The `@traceable(run_type="tool")` decorator on `call_mcp_tool()` creates a child span of type `"tool"`. Child run metadata — `run_type`, `name`, `start_time` — is always stored inline (never offloaded to S3). Evaluators can therefore detect tool execution by checking `child.run_type == "tool"` and `child.name == "call_mcp_tool"` without touching `outputs.generations` at all. This is the Layer 1 detection in the three-layer evaluator design: it's definitive, zero-cost, and immune to the S3 constraint.

---

**Q12. Name three root causes where `mcp_tool_called` scores 0 even though tools were actually called.**

**Root cause 1 — S3 storage miss**: the evaluator tried to read `child_run.outputs.generations` to detect tool calls, but that field is in S3 and returns `{}` inline. Diagnosis: add logging inside the evaluator to print `child_run.get("outputs")` — if it's empty for runs that clearly have tool results visible in LangSmith UI, this is the cause. Fix: pivot to `child_run.get("run_type") == "tool"` detection.

**Root cause 2 — `@traceable` decorator missing on `call_mcp_tool`**: without `@traceable(run_type="tool")`, the MCP HTTP call is not a child span in the run tree at all. The evaluator iterates `run.child_runs` and finds only LLM spans, none of `run_type="tool"`. Diagnosis: check in LangSmith UI whether the trace has any child spans with `run_type=tool`. Fix: ensure `call_mcp_tool` has `@traceable(run_type="tool")` as defined in `slack_bot_local.py:108`.

**Root cause 3 — Claude hallucinated tool calls (raw XML in response)**: the response content contains `<tool_call>` XML but `response.tool_calls` is empty — LangChain's `ChatAnthropic` did not parse them as structured tool calls, so no `ToolMessage` was appended and no `call_mcp_tool` span was created. This happens when `process_with_claude()` is called from a standalone script bypassing the full Slack event handler path (Issue #32). The evaluator correctly scores 0 here — but it looks like a false negative. Diagnosis: check the raw response text for `<tool_call>` or `<tool_result>` substrings. Fix: always trigger test traces through the live Slack bot, never via direct Python calls to `process_with_claude()`.

---

**Q13. Why must the `<tool_call>` XML check precede the text-grounding markers check in `hallucination_heuristic`? Give a concrete example where reversed ordering produces a wrong score.**

The evaluator's Layer 2 check (`<tool_call>` XML → score 0) exists to catch the case where Claude has outputted the tool invocation as text rather than executing it. The text grounding markers (Layer 3) check for strings like "violations:", "risk score:", "roles:" in the response — legitimate evidence that Claude cited real tool data. The problem with reversed ordering: a response that contains both `<tool_call>` XML **and** incidentally mentions a numeric claim like "risk score: 0" or "0 violations" would pass Layer 3 (text grounding check finds the numeric string) and receive score 1. But that response is actually a hallucination — the tool was never called, the number was confabulated. A concrete example:

```
# Claude's hallucinated response (contains XML + a grounding-like string)
"I would call <tool_call>get_violation_stats</tool_call>.
Based on typical patterns, users often have risk score: 75 with 3 violations."
```

If the grounding check runs first, it finds `"risk score: 75"` and scores 1. If the XML check runs first, it finds `<tool_call>` and immediately scores 0 — which is correct, because the tool was never actually executed and the number is fabricated. The XML check is both cheaper (string search) and semantically prior: if the output contains tool call XML, nothing downstream can be trusted as grounded data.

---

**Q14. What observability is lost when switching from LangChain `ChatAnthropic` to the raw Anthropic SDK?**

With `ChatAnthropic` + `LANGCHAIN_TRACING_V2=true`, LangSmith's callback chain automatically captures: `prompt_tokens`, `completion_tokens`, `total_cost`, per-turn latency, the full message sequence (system + human + AI + tool), and child span nesting. The `TokenTrackingCallback.on_llm_end` also fires, feeding the internal `TokenTracker`.

With the raw SDK, none of this is automatic. As documented in Issue #27, manually setting fields on the `RunTree` fails (`RunTree` has no `prompt_tokens` field), and `usage_metadata` in `extra` only populates the time-series token chart — not the per-run cost columns. To reproduce equivalent observability manually you would need to: (1) add `@traceable(name="slack_compliance_query")` on `process_with_claude()`; (2) manually extract `response.usage.input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens` after every `client.messages.create()` call; (3) call `get_current_run_tree().metadata.update({"ls_model_name": ..., "actual_cost": ...})` to populate the cost column with the `_PRICING_MAP` workaround from Issue #29; and (4) manually construct child span dicts for each tool call so the evaluators have something to inspect. This is approximately 40–60 lines of instrumentation boilerplate that `ChatAnthropic` provides for free.

---

**Q15. The `TokenTracker` shows $0.09 for the Slack bot and $0.03 for the analyzer on the same query. What does this tell you, and what should you investigate first?**

The `TokenTracker` accumulates cost per `agent_name` tag. The Slack bot is tagged `"slack_bot"` (via `TokenTrackingCallback(agent_name="slack_bot")`) and the analyzer is tagged `"analyzer"`. A $0.09 vs $0.03 split means the Slack bot's LLM calls account for 75% of the total spend on this query — the conversation management, tool dispatch, and synthesis turns are far more expensive than the SOD analysis itself.

This tells you the primary optimization target is the Slack bot's token profile. The most likely contributors are: (a) the full 35-tool schema being sent before intent routing was working correctly (~10K tokens/request), which the `tool_router.py` fix addresses; (b) large `ToolMessage` payloads that weren't being compressed by `_compress_tool_result()`; or (c) Opus being used for all turns before the Haiku split was implemented. The $0.03 analyzer cost is comparatively cheap — Opus with the static system prompt eligible for cache hits (`cache_control: ephemeral`) amortises to roughly $0.003/hit after the first call. The investigation priority is therefore: check `token_cb` records for whether cache hits are registering (`cache_read_tokens > 0`), then check whether the per-turn `input_tokens` in the Slack bot includes the full tool schema or the routed subset. If `cache_read_tokens` is zero across multiple queries for the same user, the cache is not warming — likely because `_STATIC_SYSTEM` changed between calls or the 5-minute TTL is expiring between queries.

---

**Q16. Does a SQLAlchemy transaction roll back if a tool handler catches its own exception and returns a formatted error string? What is the data-integrity risk?**

No. The transaction does **not** roll back in that case. The `get_session_context()` context manager in `models/database_config.py` only rolls back on an exception that propagates out of the `with` block:

```python
def get_session_context(self):
    session = self.SessionLocal()
    try:
        yield session
        session.commit()      # runs only if no exception propagated
    except Exception as e:
        session.rollback()    # only runs if exception escapes the with-block
        raise
    finally:
        session.close()
```

If a tool handler does this:

```python
async def my_tool_handler(...):
    with db_config.get_session_context() as session:
        try:
            repo.do_something_that_fails(session)
        except Exception as e:
            return f"❌ Error: {str(e)}"   # exception is swallowed here
```

The `except` in the handler catches the exception before it propagates to `get_session_context()`'s `except` clause. The context manager sees no exception, so it calls `session.commit()` — committing whatever partial work happened before the error. This is a genuine data-integrity risk: a failed multi-step write (e.g., insert user then insert violations) could leave the user row committed without the associated violation rows, creating an orphan record. The correct pattern is to not catch database exceptions in the handler, or to re-raise after logging, so the context manager's rollback fires. Alternatively, use SQLAlchemy savepoints (`session.begin_nested()`) around the risky operation so a partial failure rolls back only that unit of work without affecting the outer transaction.

---

## LLM, Agentic Patterns & Observability Questions (17–32)

---

**Q17. NetSuite silently truncates results when you request page_size=1000 but the hard cap is 200. How did this manifest and what is the defensive pattern?**

The issue manifested as seemingly successful syncs that returned only 200 users out of 1,933 — a silent 79.2% data loss with no HTTP error, no exception, and no warning in the response body. The RESTlet simply honoured 200 and ignored the rest of the request, returning a standard 200 OK with a full but truncated payload. This wasn't caught until a count comparison revealed a massive user-count discrepancy between NetSuite's admin UI and the local database.

The defensive pattern has three layers: (1) **hard-cap enforcement** — set `page_size = min(requested_size, 200)` in code, never trust the caller to know the limit; (2) **page-size comparison on response** — after each page, assert `len(response_records) <= page_size`; if you requested 200 and got exactly 200, assume there are more pages even if the API doesn't return a `hasMore` flag; (3) **post-sync count verification** — after every sync, query NetSuite's total user count endpoint separately and compare it to the local `users` table count; alert if the delta exceeds a threshold (e.g., >1%).

---

**Q18. The `violations` table uses UUID primary keys instead of auto-incrementing integers. What is the tradeoff, and when would you switch back to integers?**

UUIDs are globally unique and can be generated client-side before the INSERT, which enables optimistic insert patterns and makes IDs safe to include in external systems (Jira tickets, Slack messages) without revealing row counts or sequence gaps. They also support distributed writes across multiple MCP server instances without ID collision.

The tradeoff is B-tree index fragmentation: auto-increment integers insert in monotonically increasing order, keeping the B-tree balanced and cache-friendly. Random v4 UUIDs insert at random leaf positions, causing frequent page splits and a larger, less cache-resident index. For the `violations` table at ~50K rows/year, the difference is negligible. At multi-million row scale, you would switch to sequential UUIDs (UUID v7, which encodes a timestamp prefix) or back to BIGSERIAL — the timestamp prefix restores insert locality while preserving global uniqueness. The access pattern also matters: if violations are almost always queried by `user_id` or `scan_id` (FK lookups), the PK index is rarely used for range scans and the fragmentation cost is even lower.

---

**Q19. What does `pool_pre_ping=True` do in the SQLAlchemy engine, and what is the overhead cost?**

`pool_pre_ping=True` instructs SQLAlchemy to issue a lightweight `SELECT 1` probe to the database before returning a connection from the pool to a caller. If the probe fails (connection was dropped by the server, firewall timeout, network partition), SQLAlchemy discards that connection and attempts to establish a new one — transparently to the caller. Without it, a request would receive a stale connection, get a database error on first use, and have to handle the retry itself.

The overhead is approximately 1 additional round-trip (~0.5–2ms on localhost, ~5–15ms on a remote DB) per connection checkout. For a high-throughput service making hundreds of DB calls per second, this would be noticeable. For the compliance agent's traffic pattern (tens of queries/minute via Slack), it's negligible. The alternative is `pool_recycle` (e.g., `pool_recycle=3600`) which silently replaces connections older than N seconds, but this doesn't catch connections dropped mid-lifetime by firewalls (common in cloud environments with 10-minute idle TCP timeouts). `pool_pre_ping` is the correct default for cloud-hosted databases.

---

**Q20. Why does `compliance_scans` exist as a separate table from `sync_metadata`? What would break if you used `sync_metadata.id` as the FK on `violations`?**

`compliance_scans` represents a compliance analysis event — the execution of the SOD rule engine against a snapshot of user data. `sync_metadata` represents a data ingestion event — the fetching of user/role data from NetSuite. These are conceptually distinct: you can run a compliance analysis without triggering a new sync (e.g., re-analyzing existing data with a new rule), and a sync does not always trigger an analysis (e.g., an incremental sync that updates no records).

If `violations.scan_id` were a FK to `sync_metadata`, every violation would be tied to a data ingestion run rather than an analysis run. This breaks: (1) traceability — you couldn't tell which version of the SOD rules was used to generate a violation; (2) re-analysis — running the rule engine again would have no `sync_metadata` row to reference; (3) the cardinality — one sync can produce zero or multiple analysis runs (e.g., a sync followed by a what-if analysis of a proposed role change). The FK chain is: `sync_metadata → compliance_scans → violations`, which accurately models "data was fetched, then analyzed, and the analysis found these violations."

---

**Q21. The API key check uses `hmac.compare_digest` instead of `==`. Why? Write the vulnerable version and explain the attack.**

`hmac.compare_digest` performs a constant-time comparison — it evaluates every byte of both strings regardless of where they differ. A regular `==` comparison in CPython short-circuits on the first differing byte, returning `False` immediately.

```python
# Vulnerable version (timing attack possible)
def verify_api_key_vulnerable(provided: str, expected: str) -> bool:
    return provided == expected  # returns after first mismatch

# Safe version
import hmac
def verify_api_key_safe(provided: str, expected: str) -> bool:
    return hmac.compare_digest(provided.encode(), expected.encode())
```

The attack: an adversary sends thousands of requests with different candidate keys. For a key `"AAAA..."`, if the first byte is wrong, `==` returns in ~50ns. If the first byte is correct and the second is wrong, it returns in ~60ns. By measuring these ~10ns differences (using high-resolution timing and statistical averaging over thousands of requests), the attacker can determine the correct key one byte at a time — reducing the search space from O(256^N) to O(256 × N). `hmac.compare_digest` eliminates the timing signal entirely, making brute-force infeasible regardless of key structure.

---

**Q22. The Slack `app_mention` handler resolves `@mentioned_users` to email addresses. What amplification attack does this create, and how is it mitigated?**

The amplification attack: a malicious Slack user sends a message mentioning 50 users (`@u1 @u2 ... @u50`). The handler calls `app.client.users_info(user=uid)` for each mention — 50 serial API calls before `process_with_claude()` even starts. An attacker could send repeated messages with large mention lists to exhaust the Slack API rate limit (50 requests/min for `users.info` on most plans), causing a 429 for all users of the workspace.

Mitigations in the current code: (1) the `mentioned_users` dict is populated only for bot mentions in the event, not for arbitrary `@` strings in the text body — limiting the mention count to actual Slack `<@UXXXXXXX>` entities in the message; (2) `users_info` results are cached (the `dict` passed to `process_with_claude` is reused within the same request, preventing duplicate lookups for the same user mentioned twice). Additional hardening would include: a per-message cap (e.g., max 5 resolved mentions), a TTL-based `users_info` cache at the bot level (reuse across messages), and a rate-limit guard that debounces identical mentions from the same sender within a 60-second window.

---

**Q23. Self-approval is blocked at three layers. Enumerate them and explain which is the enforcement layer vs the advisory layer.**

**Layer 1 — Database constraint (enforcement):** The `approved_exceptions` table has a CHECK constraint ensuring `requester_id != target_user_id`. Any attempt to insert a self-approval exception at the SQL level raises a constraint violation before the application code sees the result. This is the true enforcement layer — it cannot be bypassed by application bugs.

**Layer 2 — MCP tool gate (enforcement):** The `request_exception_approval` tool handler checks `if requester_email == target_email: return error`. This is an enforcement layer at the API boundary — any MCP client (Claude, direct HTTP caller) is blocked here. However, it can be bypassed by direct database writes (which the constraint also blocks).

**Layer 3 — Skill rule (advisory):** The `employee-onboarding/SKILL.md` `## Critical` section instructs Claude to "immediately escalate to the requester's manager regardless of authority level." This is advisory — it guides Claude's reasoning but is not enforced by code. If Claude ignores this instruction (e.g., due to a context window truncation or a prompt injection in the Jira ticket body), layers 1 and 2 still catch the violation. The skill rule primarily prevents the ticket from being routed incorrectly in the first place, reducing operational noise.

---

**Q24. How would you rotate the Kubernetes secret holding the MCP API key without downtime?**

The rotation uses a blue/green secret strategy with a grace period for in-flight requests. The steps: (1) create a new secret version with the new key (`kubectl create secret generic mcp-api-key-v2 --from-literal=key=NEW_KEY`); (2) update the MCP server to accept **both** old and new keys simultaneously — add a `ACCEPTED_API_KEYS` list that contains both; (3) rolling-restart the MCP server pods with `kubectl rollout restart deployment/mcp-server` to pick up the new secret; (4) rolling-restart the Slack bot pods with the new key in their environment (they send the key in the `X-API-Key` header); (5) once all Slack bot pods are on the new key (confirmed via health check), remove the old key from `ACCEPTED_API_KEYS` and do a final rolling restart of the MCP server.

The grace period (between steps 3 and 5) is typically 5–10 minutes — long enough for all in-flight requests using the old key to complete. External Secrets Operator (ESO) can automate steps 1–3 by syncing secrets from AWS Secrets Manager or HashiCorp Vault, triggering a pod annotation update that forces a rolling restart via the `reloader` controller, eliminating manual steps entirely.

---

**Q25. A user reports that the bot said "3 CRITICAL violations" but LangSmith shows 0 violations in the tool result. What is the most likely cause and how do you confirm it?**

The most likely cause is **hallucination** — Claude answered from training-data priors rather than the tool result. The pattern: Claude calls `get_user_violations`, the result is either empty or contains a different count, but Claude's synthesis turn produces a number from its prior ("compliance systems typically have around 3 critical violations for Finance users") that doesn't match the actual tool output.

Confirmation steps: (1) open the LangSmith trace for the query; (2) click the `call_mcp_tool` child span for `get_user_violations` and read the `outputs.output` field — if it shows 0 violations or a count other than 3, Claude fabricated the number; (3) check whether `mcp_tool_called` scored 1 (tool was called) and `hallucination_heuristic` scored 0 (grounding check failed) — this combination is the signature of this failure mode; (4) check the raw response from the synthesis (Opus) turn — look for the number "3" appearing in text not preceded by a quote from the tool output. Fix: the `hallucination_heuristic` evaluator should alert on this pattern; if it didn't fire, check whether the evaluator's text grounding check is matching the wrong numeric string.

---

**Q26. `mcp_tool_called` scores 0 but the MCP server health endpoint returns 200. List the possible failure points between Claude and the tool result.**

The MCP server being healthy means requests can reach port 8080. The failure points between Claude deciding to call a tool and a `ToolMessage` appearing in the message history are:

1. **Tool not in active tool schema**: intent routing selected a tool subset that excluded the needed tool. Claude's `response.tool_calls` is empty because no matching tool was offered. Check `select_tools_for_intent()` output for the query.

2. **`call_mcp_tool` raised an exception that was caught silently**: if `call_mcp_tool()` throws and the exception is swallowed, no `ToolMessage` is appended. Check for bare `except: pass` patterns in the tool invocation path.

3. **`@traceable` not on `call_mcp_tool`**: the HTTP call executed but left no child span. The evaluator counts child spans of `run_type="tool"` — if the decorator is missing, the call is invisible to the evaluator. Confirm by checking `run.child_runs` for `run_type="tool"` entries.

4. **Claude decided no tool was needed**: Haiku's reasoning concluded the query was answerable without tools and produced a direct text response. The score is correctly 0 — Claude answered from training data. Confirm by checking whether `response.tool_calls` was non-empty in any turn.

5. **MCP client session not initialised**: `initialize_session` must be called first. If the session handshake failed silently, subsequent `tools/call` requests may return `{"error": "session not found"}` which `call_mcp_tool` converts to an error string — a ToolMessage is appended but contains an error, not a result. The evaluator still scores 1 (tool was called), so this would not produce a score of 0.

---

**Q27. On a fresh deploy the Slack bot logs `MCP_TOOLS=0` for the first 30 seconds then recovers. What is happening?**

This is a race condition between the Slack bot startup and the MCP server's `/tools/list` discovery call. The Slack bot calls `initialize_mcp_tools()` at startup, which issues a `POST /mcp` with method `tools/list`. If the MCP server is still starting up (FastAPI's lifespan startup hook is running `DataCollectionAgent.start()`, which blocks for a few seconds while the scheduler initialises and the DB connection pool warms), the `tools/list` request either fails with a connection error or returns an empty list. The bot catches this, logs `MCP_TOOLS=0`, and sets `MCP_TOOL_SCHEMAS = []`.

The recovery happens when the Slack bot's first real message arrives. `process_with_claude()` calls `initialize_session()` as the first tool, which internally re-fetches the tool list. By this time the MCP server is fully up and the list returns correctly — the `MCP_TOOLS` count updates for subsequent requests. The fix is a startup retry loop in `initialize_mcp_tools()` — retry up to 5 times with 5-second backoff before giving up, rather than failing silently. Kubernetes `readinessProbe` on the MCP server's `/health` endpoint would also prevent the Slack bot pod from starting before the MCP server is ready, eliminating the race entirely.

---

**Q28. The `analyze_access_request` script returned `KeyError: 'overall_recommendation'`. Walk through the root cause chain.**

The root cause chain:
1. `analyze_access_request_with_levels.py:analyze_access_request()` loads `roles_data` from `netsuite_sod_config_unified.json`. It looks up the requested role by name: `roles_data.get(role_name)`.
2. If the role name is not present in the JSON (e.g., informal name like "Controller access" instead of "Fivetran-Controller"), the method reaches its early return at approximately line 506: `return {"error": "Roles not found"}`.
3. The `main()` function at line 603 receives this result dict and accesses `result['overall_recommendation']` unconditionally — no guard for the `"error"` key.
4. Python raises `KeyError: 'overall_recommendation'` and the subprocess exits with a non-zero code.
5. The MCP tool handler reads `stdout` which is empty (the script crashed before writing to the output file), reads the output JSON file which contains `{"error": "Roles not found"}` from a previous run (or raises FileNotFoundError if no previous run), and returns a confusing error to Claude.

Fix applied (commit `501b298`): added `if 'error' in result: print error, sys.exit(1)` guard before accessing result keys in `main()`. Now unknown roles produce a clean `❌ Analysis Error: Roles not found` + exit code 1, which the MCP handler translates to a `isError: true` response.

---

**Q29. When would you switch the Slack bot from Socket Mode to webhook-based events? What does each mode sacrifice?**

**Socket Mode** (current): the bot maintains a persistent WebSocket connection to Slack's servers. Slack pushes events over the socket; the bot doesn't need a public URL. Advantages: works behind NAT/firewalls, no TLS certificate management, easy local development. Sacrifices: the single WebSocket connection is a stateful resource — if the process restarts, events sent during the gap are lost (Slack retries for ~30 seconds, then drops them). At high message volume, a single socket can become a throughput bottleneck.

**Webhook mode**: Slack sends HTTP POST requests to a public URL the bot owns. The bot is stateless — each event is an independent HTTP request. Advantages: horizontally scalable (multiple bot pods behind a load balancer all receive events), events are retried by Slack for up to 3 hours on failure (much better delivery guarantee), compatible with API gateways and CDN-level rate limiting. Sacrifices: requires a public IP/domain, TLS certificate, and a firewall rule; harder to develop locally without a tunnel (ngrok/cloudflared).

Switch trigger: when the compliance agent is deployed to Kubernetes in production with multiple replicas for HA. Socket Mode's single persistent connection doesn't distribute across pods — only one pod receives all events. Webhook mode + a Kubernetes `Service` load-balancer naturally distributes events across replicas.

---

**Q30. How would you make SOD rules dynamically configurable without redeploying the MCP server?**

The current architecture loads rules from `database/seed_data/sod_rules.json` at startup. Dynamic configuration requires moving this to the database and adding management tooling.

Architecture: (1) Add a `sod_rules` table with columns: `rule_code`, `rule_name`, `conflicting_permissions` (JSONB), `severity`, `is_active`, `effective_date`, `created_by`. (2) Add two MCP tools: `propose_sod_rule(rule_json)` — inserts with `is_active=False`, requires Controller approval; `approve_sod_rule(rule_code, approver_email)` — sets `is_active=True` after SOX-compliant approval. (3) The `SODAnalysisAgent` loads rules from the DB at the start of each analysis run (not at server startup), so new rules take effect on the next scheduled sync. (4) Add a rule-version FK on `compliance_scans` so each scan records which rule set was active when it ran — enabling reproducible audits even after rules change. (5) Add a LangSmith evaluator tag `rule_version=v{n}` on each trace so regressions introduced by rule changes are identifiable in the timeline.

---

**Q31. You need to run a full access review for all 1,928 users. The current architecture would hit the 5-turn cap and time out. Design a scalable approach.**

The key insight is that the 5-turn cap exists because the Slack bot is synchronous — it must respond within Slack's 3-second ack window and the user is waiting. Full-org reviews should be asynchronous.

Design: (1) The Slack command `"run full access review"` triggers the `perform_access_review` MCP tool, which enqueues a Celery task (`celery_app.py` is already wired) with a job ID and immediately responds to Slack: `"Full access review started. Job ID: abc123. I'll post results when complete."` (2) The Celery worker runs `SODAnalysisAgent.analyze_all_users()` in a background process — no turn cap, no Slack timeout pressure. (3) On completion, the worker calls `app.client.chat_postMessage()` with the results, including a LangSmith trace link and a summary table. (4) The MCP tool `get_review_status(job_id)` lets users poll progress. (5) For parallelism, use a Celery `chord` — partition users into batches of 100, run each batch as a parallel subtask, then aggregate results in a callback. With 10 workers, 1,928 users processes in ~2 minutes vs ~20 minutes sequential.

---

**Q32. How would you evaluate whether switching from Opus to Sonnet for the synthesis turn saves money without degrading quality?**

This is a shadow-mode evaluation problem. Steps:

(1) **Shadow deployment**: add a feature flag `SYNTHESIS_MODEL=opus|sonnet|ab`. In `ab` mode, run both models on every request but only return the Opus answer to the user. Log both responses with identical trace metadata.

(2) **LangSmith evaluators**: the existing `compliance_conversation_quality` multi-turn evaluator scores on 4 dimensions (DATA_GROUNDED, CORRECT_ROUTING, WORKFLOW_COMPLETE, CLEAR_VERDICT). Run it against both Opus and Sonnet traces on the same inputs. Compute `mean_score_opus` vs `mean_score_sonnet` over 200+ queries.

(3) **Domain-specific regression tests**: identify the 10 highest-risk query types (CRITICAL violation routing, self-approval detection, AP+GL role conflict). Run each with both models 5 times. A pass requires identical routing decisions (not just similar wording) — because a wrong approver is an audit finding.

(4) **Cost analysis**: use `TokenTracker` data. Sonnet is typically ~5x cheaper than Opus per output token. If `mean_score_sonnet >= mean_score_opus - 0.1` (within 5% on a 0–2 scale) and routing decisions match on all 10 regression tests, the switch is safe.

(5) **Rollback criteria**: if `correct_routing` drops below 1.5 on any 7-day moving window, auto-revert to Opus via the feature flag.

---

## Algorithm Questions (A1–A8)

---

**A1. Find All Conflicting Role Pairs**

**Problem:** Given a list of NetSuite roles (each with a set of permissions) and a list of SOD rules (each rule is a pair of conflicting permissions), find all pairs of roles that would create a SOD violation if assigned to the same user.

**Constraints:**
- 1 <= roles <= 500, each with 1–50 permissions
- 1 <= sod_rules <= 100, each is a tuple `(perm_a, perm_b)`
- A pair `(role_X, role_Y)` conflicts if role_X has `perm_a` AND role_Y has `perm_b` (or vice versa)
- Return sorted list of canonical `(min, max)` pairs; no duplicates

**Algorithm:** Build an inverted index: permission → set of roles that have it. For each SOD rule `(perm_a, perm_b)`, cross-product the roles-with-perm_a set and roles-with-perm_b set. Use canonical ordering `(min, max)` to deduplicate.

**Time complexity:** O(R·P + S·R²) where R=roles, P=permissions/role, S=sod_rules
**Space complexity:** O(R·P) for the inverted index

```python
from itertools import product
from collections import defaultdict

def find_conflicting_role_pairs(
    roles: dict[str, set[str]],          # {role_name: {permissions}}
    sod_rules: list[tuple[str, str]],    # [(perm_a, perm_b), ...]
) -> list[tuple[str, str]]:

    # Build inverted index: permission -> roles that have it
    perm_to_roles: dict[str, set[str]] = defaultdict(set)
    for role_name, perms in roles.items():
        for perm in perms:
            perm_to_roles[perm].add(role_name)

    conflicting_pairs: set[tuple[str, str]] = set()

    for perm_a, perm_b in sod_rules:
        roles_with_a = perm_to_roles.get(perm_a, set())
        roles_with_b = perm_to_roles.get(perm_b, set())

        for r1, r2 in product(roles_with_a, roles_with_b):
            if r1 != r2:
                # Canonical ordering to deduplicate (A,B) and (B,A)
                pair = (min(r1, r2), max(r1, r2))
                conflicting_pairs.add(pair)

    return sorted(conflicting_pairs)


# Example usage
roles = {
    "AP_Clerk":    {"create_invoice", "post_payment"},
    "AP_Approver": {"approve_invoice", "release_payment"},
    "GL_Admin":    {"post_payment", "approve_invoice"},
}
sod_rules = [
    ("create_invoice", "approve_invoice"),
    ("post_payment",   "release_payment"),
]
print(find_conflicting_role_pairs(roles, sod_rules))
# [('AP_Clerk', 'AP_Approver'), ('AP_Clerk', 'GL_Admin')]
```

---

**A2. Minimum Required Approval Level**

**Problem:** Given a list of violations each with a severity level, determine the minimum approval chain level (L1–L5) required to approve the entire set. Rules: LOW→L2, MEDIUM→L3, HIGH→L4, CRITICAL→L5. The required level is the maximum across all violations.

**Constraints:**
- 1 <= violations <= 10,000
- Severity is one of: `"LOW"`, `"MEDIUM"`, `"HIGH"`, `"CRITICAL"`

**Algorithm:** Map severity to level with a lookup dict. Single linear scan taking the running maximum. Short-circuits at L5.

**Time complexity:** O(n) | **Space complexity:** O(1)

```python
def minimum_approval_level(
    severities: list[str],
) -> tuple[int, str]:
    SEVERITY_TO_LEVEL = {
        "LOW":      2,
        "MEDIUM":   3,
        "HIGH":     4,
        "CRITICAL": 5,
    }
    LEVEL_TO_TITLE = {
        1: "Employee",
        2: "Manager",
        3: "Senior Manager",
        4: "Controller",
        5: "CFO",
    }

    if not severities:
        return (1, LEVEL_TO_TITLE[1])

    max_level = 1
    for sev in severities:
        level = SEVERITY_TO_LEVEL.get(sev.upper())
        if level is None:
            raise ValueError(f"Unknown severity: {sev}")
        if level > max_level:
            max_level = level
            if max_level == 5:
                break  # short-circuit: can't go higher

    return (max_level, LEVEL_TO_TITLE[max_level])


# Tests
print(minimum_approval_level(["LOW", "HIGH", "MEDIUM", "CRITICAL"]))  # (5, 'CFO')
print(minimum_approval_level(["LOW", "MEDIUM", "LOW"]))               # (3, 'Senior Manager')
print(minimum_approval_level([]))                                      # (1, 'Employee')
```

---

**A3. Detect a Cycle in an Approval Chain**

**Problem:** The approval chain is a directed graph where `u → v` means "u escalates to v." A misconfigured rule could create a cycle (e.g., L3→L4→L2→L3), causing infinite escalation. Given an adjacency list, detect whether a cycle exists and return one cycle path if found.

**Algorithm:** DFS with three-color marking (WHITE=unvisited, GRAY=in current path, BLACK=fully explored). When a GRAY node is reached again, a back edge (cycle) is found.

**Time complexity:** O(V + E) | **Space complexity:** O(V)

```python
def detect_cycle_clean(
    graph: dict[int, list[int]]
) -> tuple[bool, list[int]]:
    all_nodes: set[int] = set(graph.keys())
    for nbrs in graph.values():
        all_nodes.update(nbrs)

    visited:   set[int] = set()
    rec_stack: set[int] = set()
    path:      list[int] = []

    def dfs(node: int) -> bool:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                # Found cycle; trim path to the cycle
                idx = path.index(neighbor)
                path.append(neighbor)  # close the loop
                del path[:idx]
                return True

        path.pop()
        rec_stack.discard(node)
        return False

    for node in sorted(all_nodes):
        if node not in visited:
            if dfs(node):
                return (True, list(path))

    return (False, [])


# Tests
print(detect_cycle_clean({1: [2], 2: [3], 3: [4], 4: [2]}))
# (True, [2, 3, 4, 2])
print(detect_cycle_clean({1: [2], 2: [3], 3: [4], 4: [5], 5: []}))
# (False, [])
```

---

**A4. Paginated API Fetch with Deduplication**

**Problem:** Implement a paginated fetch from the NetSuite API that handles: (a) page size capped at 200, (b) incremental sync using `last_modified` timestamp, (c) deduplication of records that appear on multiple pages due to modifications mid-sync.

**Algorithm:** Dict keyed by record ID. On each page, upsert keeping the higher `last_modified` value. Stop when `len(page_results) < page_size`.

**Time complexity:** O(total_records) amortized | **Space complexity:** O(unique_records)

```python
from typing import Callable

def paginated_sync(
    api_call: Callable[[int, int, int], list[dict]],
    since: int = 0,
    page_size: int = 200,
    max_pages: int = 1000,     # safety cap
) -> list[dict]:
    PAGE_SIZE = min(page_size, 200)   # enforce hard cap
    seen: dict[str, dict] = {}        # id -> best record so far
    page = 1

    for _ in range(max_pages):
        results = api_call(page, PAGE_SIZE, since)

        if not results:
            break

        for record in results:
            record_id = record["id"]
            existing = seen.get(record_id)
            # Keep the version with the larger last_modified (most recent)
            if existing is None or record["last_modified"] > existing["last_modified"]:
                seen[record_id] = record

        page += 1

        # Termination: last page has fewer records than page_size
        if len(results) < PAGE_SIZE:
            break

    return list(seen.values())
```

---

**A5. Risk Score Aggregation Across Multiple Violations**

**Problem:** Compute an aggregate risk score using diminishing returns (each additional violation of the same severity contributes 50% of the previous one), plus a 1.2x cross-severity multiplier when both CRITICAL and HIGH violations exist simultaneously.

**Scoring:** CRITICAL=100, HIGH=40, MEDIUM=15, LOW=5. Geometric series decay per severity bucket.

**Algorithm:** Group by severity. For each group: `base * (1 - 0.5^n) / (1 - 0.5)`. Sum across groups, apply multiplier if applicable.

**Time complexity:** O(n) | **Space complexity:** O(1)

```python
from collections import Counter
from math import pow

def compute_risk_score(violations: list[str]) -> float:
    BASE_SCORES = {
        "CRITICAL": 100.0,
        "HIGH":      40.0,
        "MEDIUM":    15.0,
        "LOW":        5.0,
    }
    DECAY = 0.5
    CROSS_MULTIPLIER = 1.2

    counts = Counter(v.upper() for v in violations)

    def bucket_score(severity: str) -> float:
        n = counts.get(severity, 0)
        if n == 0:
            return 0.0
        base = BASE_SCORES[severity]
        # Geometric series: base * sum(DECAY^i for i in range(n))
        return base * (1.0 - pow(DECAY, n)) / (1.0 - DECAY)

    total = sum(bucket_score(sev) for sev in BASE_SCORES)

    # Apply cross-severity multiplier when both CRITICAL and HIGH exist
    if counts.get("CRITICAL", 0) > 0 and counts.get("HIGH", 0) > 0:
        total *= CROSS_MULTIPLIER

    return round(total, 2)


# Tests
print(compute_risk_score(["CRITICAL", "CRITICAL", "HIGH", "LOW"]))
# CRITICAL: 150, HIGH: 40, LOW: 5 → 195 * 1.2 = 234.0
print(compute_risk_score(["MEDIUM", "MEDIUM", "MEDIUM"]))
# 15 * (1-0.125) / 0.5 = 26.25
print(compute_risk_score([]))
# 0.0
```

---

**A6. LRU Cache for Idempotent MCP Tool Results**

**Problem:** Implement an LRU (Least Recently Used) cache for idempotent MCP tool results keyed by `(tool_name, kwargs)`. Max capacity; on overflow evict the LRU entry. Each entry has a TTL in seconds; expired entries are treated as cache misses.

**Algorithm:** `OrderedDict` maintains insertion order. `move_to_end` on get (O(1)). On put, add to end; if over capacity, `popitem(last=False)` evicts front (LRU). Check TTL on get.

**Time complexity:** O(1) get and put | **Space complexity:** O(capacity)

```python
import time
from collections import OrderedDict
from typing import Any

class LRUToolCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        # key -> (result, expiry_epoch or None)
        self._cache: OrderedDict[tuple, tuple[Any, float | None]] = OrderedDict()

    def _make_key(self, tool_name: str, kwargs: dict) -> tuple:
        return (tool_name, frozenset(kwargs.items()))

    def get(self, tool_name: str, kwargs: dict) -> Any | None:
        key = self._make_key(tool_name, kwargs)
        if key not in self._cache:
            return None

        result, expiry = self._cache[key]

        if expiry is not None and time.monotonic() > expiry:
            del self._cache[key]
            return None

        self._cache.move_to_end(key)  # mark as most recently used
        return result

    def put(self, tool_name: str, kwargs: dict, result: Any, ttl: int = 0) -> None:
        key = self._make_key(tool_name, kwargs)
        expiry = (time.monotonic() + ttl) if ttl > 0 else None

        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache[key] = (result, expiry)
        else:
            if len(self._cache) >= self.capacity:
                self._cache.popitem(last=False)  # evict LRU (front)
            self._cache[key] = (result, expiry)


# Tests
cache = LRUToolCache(capacity=2)
cache.put("get_violations", {"user_id": "u1"}, ["v1", "v2"], ttl=60)
cache.put("get_violations", {"user_id": "u2"}, ["v3"],       ttl=60)
print(cache.get("get_violations", {"user_id": "u1"}))  # ['v1', 'v2'] — u1 now MRU
cache.put("get_violations", {"user_id": "u3"}, ["v4"],       ttl=60)  # u2 evicted
print(cache.get("get_violations", {"user_id": "u2"}))  # None (evicted)
print(cache.get("get_violations", {"user_id": "u3"}))  # ['v4']
```

---

**A7. Minimum Role Removal to Eliminate All CRITICAL Violations**

**Problem:** A user has a set of roles. Some pairs create CRITICAL SOD violations. Find the minimum number of roles to remove such that no CRITICAL violations remain. This is the Minimum Vertex Cover problem — polynomial for bipartite graphs via König's theorem.

**Algorithm:** Greedy vertex cover for general graphs (optimal approximation); exact bipartite solution via Hopcroft-Karp matching + König's theorem.

**Time complexity (greedy):** O(E²) | **Space complexity:** O(V + E)

```python
from collections import defaultdict, deque

def minimum_role_removal(
    roles: list[str],
    critical_conflicts: list[tuple[str, str]],
) -> list[str]:
    if not critical_conflicts:
        return []

    remaining_edges: set[tuple[str, str]] = set()
    for r1, r2 in critical_conflicts:
        remaining_edges.add((min(r1, r2), max(r1, r2)))

    cover: set[str] = set()

    while remaining_edges:
        # Count degree in remaining graph
        degree: dict[str, int] = defaultdict(int)
        for r1, r2 in remaining_edges:
            degree[r1] += 1
            degree[r2] += 1

        # Pick node with highest degree (greedy vertex cover)
        best = max(degree, key=lambda x: degree[x])
        cover.add(best)

        # Remove all edges incident to best
        remaining_edges = {
            (r1, r2) for r1, r2 in remaining_edges
            if r1 != best and r2 != best
        }

    return sorted(cover)


# Test
print(minimum_role_removal(
    ["R1", "R2", "R3", "R4"],
    [("R1", "R2"), ("R1", "R3"), ("R2", "R4")]
))
# e.g. ['R1', 'R2'] — removing R1 eliminates R1-R2 and R1-R3;
# removing R2 (or R4) eliminates R2-R4
```

---

**A8. Topological Sort of LangGraph Workflow Stages**

**Problem:** The LangGraph compliance workflow has stages with explicit dependencies. Given a dict mapping each stage to its list of prerequisites, produce a valid execution order. If a circular dependency exists, raise an error identifying the cycle.

**Algorithm:** Kahn's BFS algorithm. Compute in-degree for each node. Enqueue all nodes with in-degree 0. For each dequeued node, decrement in-degree of dependents. If processed count < total nodes, a cycle exists.

**Time complexity:** O(V + E) | **Space complexity:** O(V + E)

```python
from collections import defaultdict, deque

class CircularDependencyError(Exception):
    pass

def topological_sort_workflow(
    dependencies: dict[str, list[str]]
) -> list[str]:
    all_stages: set[str] = set(dependencies.keys())
    for prereqs in dependencies.values():
        all_stages.update(prereqs)

    adj: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = {stage: 0 for stage in all_stages}

    for stage, prereqs in dependencies.items():
        for prereq in prereqs:
            adj[prereq].append(stage)
            in_degree[stage] += 1

    # Start with nodes that have no prerequisites
    queue: deque[str] = deque(
        sorted(s for s in all_stages if in_degree[s] == 0)
    )
    order: list[str] = []

    while queue:
        stage = queue.popleft()
        order.append(stage)
        for dependent in sorted(adj[stage]):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    if len(order) != len(all_stages):
        cycle_candidates = sorted(all_stages - set(order))
        raise CircularDependencyError(
            f"Circular dependency detected among stages: {cycle_candidates}"
        )

    return order


# Tests
deps = {
    "INIT":     [],
    "COLLECT":  ["INIT"],
    "ANALYZE":  ["COLLECT"],
    "ASSESS":   ["COLLECT"],
    "NOTIFY":   ["ANALYZE", "ASSESS"],
    "COMPLETE": ["NOTIFY"],
    "ERROR":    [],
}
print(topological_sort_workflow(deps))
# e.g. ['ERROR', 'INIT', 'COLLECT', 'ANALYZE', 'ASSESS', 'NOTIFY', 'COMPLETE']

# Cyclic — should raise
try:
    topological_sort_workflow({
        "INIT": [], "ANALYZE": ["ASSESS"], "ASSESS": ["ANALYZE"]
    })
except CircularDependencyError as e:
    print(f"Caught: {e}")
# Caught: Circular dependency detected among stages: ['ANALYZE', 'ASSESS']
```

---

## Quick Reference Table

| # | Topic | Key Concept |
|---|-------|-------------|
| 1 | SOD detection end-to-end | APScheduler → NetSuite → PostgreSQL → SOD engine → violations table |
| 2 | BaseConnector ABC | 5 abstract methods, orchestrator is connector-agnostic |
| 3 | `Annotated[List, operator.add]` | Accumulate errors across parallel LangGraph nodes |
| 4 | Intent routing | INTENT_PATTERNS regex → TOOL_GROUPS union → 85% token reduction |
| 5 | HTTP 200 on tool errors | JSON-RPC 2.0 transport vs application error separation |
| 6 | `has_tool_results` switch | Opus only when ToolMessages exist in history |
| 7 | 5-turn cap behaviour | Silent fallback string; fix: token budget + LangGraph recursion_limit |
| 8 | Prompt cache math | 12.5x cost reduction; invalidated on prefix change or 5-min TTL |
| 9 | `_compress_tool_result` risk | UUID/identifier loss; fix: raise `ROLLING_SUMMARY_MIN_CHARS` |
| 10 | subprocess vs in-process | Process isolation vs startup latency + file collision |
| 11 | S3 + `@traceable(run_type="tool")` | Child span metadata always inline; never offloaded to S3 |
| 12 | `mcp_tool_called` false zero | S3 miss / missing decorator / hallucinated XML |
| 13 | XML check before text grounding | XML = tool never ran; grounding check could false-positive on XML |
| 14 | ChatAnthropic vs raw SDK | 40-60 lines boilerplate = automatic cost/token/latency tracking |
| 15 | $0.09/$0.03 cost split | Slack bot = 75% of spend; investigate cache hits + tool schema size |
| 16 | Exception-swallowing + SQLAlchemy | Context manager commits partial work; use savepoints or re-raise |
| 17 | NetSuite truncation | Hard-cap enforcement + page-size comparison |
| 18 | UUID vs auto-increment | Index fragmentation vs portability |
| 19 | `pool_pre_ping` | Dead connection detection, ~1ms overhead |
| 20 | `compliance_scan` FK | Analysis event vs ingestion event lineage |
| 21 | Timing attack on API key | `hmac.compare_digest` constant-time comparison |
| 22 | Slack mention amplification | Mention cap + `users.info` caching |
| 23 | Self-approval enforcement layers | DB=enforced, MCP=gate, skill=advisory |
| 24 | K8s secrets rotation | External Secrets Operator + rolling restart |
| 25 | Hallucinated violation counts | LangSmith trace + `mcp_tool_called` score |
| 26 | `mcp_tool_called=0`, server healthy | Client session / tool discovery failure |
| 27 | `MCP_TOOLS=0` on new deploy | Race condition at session init, reconnect |
| 28 | `KeyError 'overall_recommendation'` | Missing role → empty result → missing key |
| 29 | Socket Mode vs webhooks | Stateful/reconnection vs guaranteed delivery |
| 30 | Dynamic SOD rules | `sod_rules` table + propose/approve MCP tools |
| 31 | Bulk review at scale | Task queue + worker pool decoupling |
| 32 | Model evaluation framework | Role-specific evals, shadow mode, rollback |
| A1 | Conflicting role pairs | Inverted index + cross product, O(R·P + S·R²) |
| A2 | Minimum approval level | Linear scan max, O(n) |
| A3 | Cycle in approval chain | Three-color DFS, O(V+E) |
| A4 | Paginated fetch + deduplication | Dict upsert by ID, keep max `last_modified` |
| A5 | Risk score aggregation | Geometric series decay + cross-severity multiplier |
| A6 | LRU cache for MCP tools | `OrderedDict` O(1) get/put + TTL |
| A7 | Minimum role removal | Greedy vertex cover / König's theorem bipartite |
| A8 | Workflow topological sort | Kahn's BFS, cycle detection, O(V+E) |
