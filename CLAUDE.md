# Claude Code Project Guide: SOD Compliance System

**Project:** AI-Powered Segregation of Duties (SOD) Compliance System
**Version:** 2.0
**Last Updated:** 2026-03-15
**Primary Language:** Python 3.9+
**Framework:** FastAPI with MCP (Model Context Protocol)

---

## 🎯 Project Overview

This is an autonomous compliance monitoring system that peforms user access review, sod analysis, risk assessement and reporting across key business systems - NetSuite ERP, Okta, Salesforce, Coupa etc. The system uses Claude Opus 4.6 for intelligent analysis and operates as an MCP server, providing compliance tools to Claude Code and other MCP clients.

### Core Capabilities

1. **Autonomous Data Collection**: Background agent syncs user/role/permission data from NetSuite (daily full sync + hourly incremental)
2. **AI-Powered Analysis**: Claude Opus 4.6 analyzes 18 SOD rules against user access patterns
3. **MCP Integration**: 11 tools available via Model Context Protocol for real-time compliance queries
4. **Knowledge Base**: pgvector-powered semantic search for compliance policies and remediation guidance

### Success Metrics

- ✅ 1,928/1,933 users synced from NetSuite (99.7% coverage)
- ✅ 18 SOD rules implemented and active
- ✅ 55x query performance improvement (on-demand → cached)
- ✅ 37 MCP tools operational (updated from 11)
- ✅ Autonomous agent running 24/7
- ✅ **NEW**: Slack bot with multi-turn agentic reasoning (Feb 2026)
- ✅ **NEW**: Semantic tool router — embedding-based, MRR 0.18 → 0.91, Hit Rate@10 → 1.00 (Mar 2026)
- ✅ **NEW**: LangSmith eval suite — Hit Rate@K, MRR, NDCG, Precision@K, Faithfulness (Mar 2026)

### 🚀 Latest Enhancement: Multi-Turn Agentic Tool Use (Feb 2026)

The Slack bot now supports **multi-step reasoning** where Claude can:
1. Make initial tool calls to gather information
2. Analyze the results
3. Make follow-up tool calls based on that analysis
4. Provide comprehensive recommendations

**Example Impact:**
- **Before**: User asks "Can we assign Controller role to Austin?" → Bot checks new role only → Reports "0 conflicts" ❌
- **After**: Bot gets current roles → Analyzes ALL roles together → Reports "249 conflicts, HIGH risk" ✅

**Technical Details:**
- Multi-turn conversation loop (up to 5 turns)
- Automatic Slack @mention → email resolution
- Complete role combination analysis (not just new role in isolation)
- File: `compliance-agent/slack_bot_local.py` (lines 242-315)

**See:** `docs/SLACK_INTEGRATION.md` for complete documentation.

### 🔭 Latest Enhancement: LangSmith Observability + ChatAnthropic Migration (Feb 2026)

Full distributed tracing is now wired into every LLM call site via LangSmith.

**Tracing coverage:**

| Call site | Mechanism | Trace name |
|-----------|-----------|-----------|
| Slack bot main loop | `ChatAnthropic` + `@traceable` | `slack_compliance_query` |
| Direct Anthropic SDK calls | `@traceable` + `usage_metadata` | `claude.messages.create` |
| LangChain agents (analyzer, risk_assessor, etc.) | Auto via `LANGCHAIN_TRACING_V2=true` | `RunnableSequence` |
| `AnthropicProvider.generate/stream` | `@traceable` | `anthropic_provider.generate` |

**Slack bot architecture change:**

The Slack bot `process_with_claude()` was migrated from `AnthropicClientWrapper` (raw SDK) to `ChatAnthropic` (LangChain). This enables LangSmith to automatically populate `total_cost`, `prompt_tokens`, and `completion_tokens` per trace. A `TokenTrackingCallback` bridges LangChain's callback events to the existing `TokenTracker`.

**DM conversation history:**

`fetch_dm_history()` was added to carry the last 10 messages as context for DM channel requests (Slack DMs have no `thread_ts`, so `conversations_history()` is used instead of `conversations_replies()`).

**Required env vars (add to `.env`):**
```bash
LANGSMITH_API_KEY=lsv2_pt_...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=compliance-agent
```

**Verifying traces:** Open smith.langchain.com → project `compliance-agent`. Each Slack query appears as one `slack_compliance_query` trace with nested LLM call spans showing cost, token counts, and latency.

**See:** `docs/LESSONS_LEARNED.md` Issues #27-30 for detailed root causes and solutions.

---

### 🧠 Latest Enhancement: Memory Management — Phase A + B (Feb 2026)

**Phase A — Redis TTL Cache** (`slack_bot_local.py`, deployed 2026-02-24):

MCP tool calls are now cached in Redis to eliminate redundant calls within a TTL window.

- Cache key: `mcp:{tool_name}:{md5(arguments)}`
- TTL map: `get_user_violations=1h`, `get_role_conflicts=24h`, `get_violation_stats=30min`, `analyze_access_request=1h`
- Mutating tools excluded: `trigger_manual_sync`, `approve_exception`, `request_exception_approval`
- Feature flag: `USE_MCP_CACHE=false` in `.env` to disable
- LangSmith: cache hits tagged with `metadata.context_cache_hit=true` and `metadata.cache_tool` — note: the tag is applied on the ROOT run (not child span) via `_cache_hit_tls` thread-local (fixed commit `424fcf7`, 2026-02-25)
- Verified: Cache HIT at 0.01s vs MISS at ~50ms in logs

**Phase A bugfix also included:** `handle_dm()` was calling `process_with_claude()` without `thread_history`. Fixed to call `fetch_dm_history()` first. Token impact: 3,485 → 5,494 per follow-up query (expected — prior context now injected).

**Phase B — Conversation Summarization** (`slack_bot_local.py` + `models/conversation_summary.py`, deployed 2026-02-24):

After each DM exchange, Haiku generates a 2-3 sentence summary stored in Postgres. On the next query from the same user, the 3 most recent summaries are injected into the system message (~150 tokens vs ~2K raw tokens).

- New table: `conversation_summaries` (user_email, channel_id, summary, topics, outcome, expires_at 90d)
- Write-back: non-blocking `threading.Thread` after each response
- Retrieval: 3 most recent non-expired summaries per user
- Feature flag: `USE_CONV_SUMMARIES=false` in `.env` to disable
- LangSmith: injected summary count tagged as `metadata.context_summaries_injected`
- Token reduction: ~2,000 raw prior tokens → ~150 summary tokens per follow-up query

**Required env vars:**
```bash
USE_MCP_CACHE=true          # Phase A (default: true)
USE_CONV_SUMMARIES=true     # Phase B (default: true)
USE_ANSWER_FEEDBACK=true    # Phase feedback loop (default: true)
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgresql://...  # already required
```

**See:** `database/migrations/006_add_conversation_summaries.sql` for schema.

**Phase feedback — Human Answer Scoring** (`slack_bot_local.py` + `models/answer_feedback.py`, deployed 2026-02-26):

Block Kit ✅/❌/🔧 buttons appended to every bot response. On click, feedback written non-blocking to Postgres and LangSmith `create_feedback()`. Negative feedback busts the Redis violation cache immediately.

- New table: `answer_feedback` (run_id, signal, correction, tool_called, query_preview, answer_preview)
- Migration: `database/migrations/007_add_answer_feedback.sql`
- Model: `models/answer_feedback.py`
- LangSmith: `human_rating` score (1.0/0.0/0.5) visible in Feedback tab alongside 3 auto-evals
- Redis: NEGATIVE signal deletes all `mcp:get_user_violations:*` keys
- Feature flag: `USE_ANSWER_FEEDBACK=false` in `.env` to disable

---

### 🔍 Latest Enhancement: Semantic Tool Router + LangSmith Eval Suite (Mar 2026)

**Problem:** The regex-based `select_tools_for_intent()` in `utils/tool_router.py` was scoring:
- Hit Rate@10: 0.72 — correct tool missing from shortlist 28% of queries
- MRR: 0.18 — correct tool buried at rank ~5 due to `always_include` pollution

**Root causes identified via eval:**
1. `initialize_session` + `check_my_approval_authority` always placed at positions 0–1, burying intent tools
2. Regex plural/singular mismatches (`\bexception\b` doesn't match `exceptions`, `\bsod rule\b` doesn't match `rules`)
3. No intra-group ranking — correct tool buried within group

**Fix 1 — Regex patches + always_include moved to end** (`utils/tool_router.py`):
Scores after fix: Hit Rate@10: 0.78, MRR: 0.41

**Fix 2 — Semantic router** (`utils/semantic_router.py`):
`SemanticToolRouter` embeds all tool descriptions + curated example queries using `sentence-transformers/all-MiniLM-L6-v2` (local, no API key). At query time embeds the user message and ranks tools by cosine similarity.

```python
# Drop-in replacement in slack_bot_local.py
from utils.semantic_router import semantic_select_tools
relevant_tools = semantic_select_tools(user_message, MCP_TOOLS) if MCP_TOOLS else []
```

**Final scores after semantic router:**

| Metric | Baseline | Semantic | Delta |
|--------|----------|----------|-------|
| hit_rate_at_10 | 0.72 | 1.00 | +0.28 |
| hit_rate_at_5 | 0.56 | 0.97 | +0.41 |
| mrr | 0.18 | 0.91 | +0.73 |
| ndcg_at_10 | 0.37 | 0.89 | +0.52 |
| precision_at_5 | 0.24 | 0.39 | +0.15 |

**LangSmith Eval Suite** (`eval/`):

| File | Purpose |
|------|---------|
| `eval/golden_set.py` | 32 labelled tool-selection queries + 10 answer-quality queries. Run once to push datasets to LangSmith. |
| `eval/evaluators.py` | Hit Rate@K, MRR, NDCG@K, Precision@K, Faithfulness (Haiku judge) |
| `eval/run_eval.py` | CLI runner — pushes results to LangSmith Experiments tab |

```bash
# Push golden datasets to LangSmith (one-time or after golden set changes)
LANGSMITH_API_KEY=... python -m eval.golden_set

# Run keyword router eval
LANGSMITH_API_KEY=... python -m eval.run_eval --router=keyword

# Run semantic router eval
LANGSMITH_API_KEY=... python -m eval.run_eval --router=semantic

# Side-by-side comparison of both routers (pushes two experiments)
LANGSMITH_API_KEY=... python -m eval.run_eval --suite=compare

# Run answer quality eval (requires live MCP server at :8080)
LANGSMITH_API_KEY=... python -m eval.run_eval --suite=answer_quality
```

Results appear in LangSmith → Datasets → `compliance-tool-selection-v1` → Experiments tab.

**Adding a new tool to the semantic router:**
Add an entry to `TOOL_EXEMPLARS` in `utils/semantic_router.py` with the tool description and 3–5 example queries. No regex patterns needed.

---

### ⚡ Latest Enhancement: Haiku/Opus Model Split + LangSmith Evaluators (Feb 2026)

**Haiku for tool dispatch, Opus for synthesis** (`slack_bot_local.py:461`):

```python
has_tool_results = any(isinstance(m, ToolMessage) for m in messages)
active_model = llm_with_tools if has_tool_results else haiku_with_tools
```

Tool-dispatch turns (decide which MCP tool to call) use `claude-haiku-4-5-20251001` — fast and cheap.
Once tool results arrive, the synthesis turn switches to `claude-opus-4-6` for high-quality reasoning.

**Verified trace `c06830c0`:** `haiku → call_mcp_tool → haiku → call_mcp_tool → haiku → opus` | 14.3s | 2 tools

**3 online LangSmith evaluators** fire on every trace:
- `mcp_tool_called` — scores 0 if Claude answered without calling any MCP tool
- `mcp_tool_coverage` — scores 0 if access-request query skipped `analyze_access_request`
- `hallucination_heuristic` — scores 0 if response contains `<tool_call>` XML or ungrounded numeric claims

All evaluators use 3-layer detection: tool child spans → XML hallucination → text grounding markers.

**See:** `docs/LESSONS_LEARNED.md` Issues #31-33 for root causes and solutions.

---

## 🏗️ Architecture

### Three-Phase System

```
Phase 1: Data Collection (Autonomous Agent)
├── NetSuite RESTlet API → Python Connector
├── Scheduled Sync (APScheduler)
└── PostgreSQL Storage

Phase 2: AI Analysis (Claude Opus 4.6)
├── SOD Rule Engine (18 rules)
├── LLM Abstraction Layer (multi-provider)
└── Violation Detection & Severity Scoring

Phase 3: Knowledge Base (pgvector)
├── Policy Documents (chunked, embedded)
├── Semantic Search (OpenAI embeddings)
└── RAG for Remediation Guidance
```

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| **MCP Server** | `mcp/mcp_server.py` | FastAPI server exposing 11 compliance tools |
| **Data Collector** | `agents/data_collector.py` | Autonomous agent for scheduled syncing |
| **SOD Analyzer** | `agents/analyzer.py` | AI-powered violation detection |
| **NetSuite Connector** | `connectors/netsuite_connector.py` | RESTlet API integration |
| **Knowledge Agent** | `agents/knowledge_base_agent.py` | pgvector semantic search |
| **LLM Layer** | `services/llm_service.py` | Multi-provider abstraction (Anthropic/OpenAI/Gemini) |
| **Tool Router (keyword)** | `utils/tool_router.py` | Regex/keyword pre-filter. Kept as fallback. Every new tool must be registered in `TOOL_GROUPS`. |
| **Tool Router (semantic)** | `utils/semantic_router.py` | Embedding-based router (MiniLM-L6-v2, local). Drop-in replacement. Register new tools in `TOOL_EXEMPLARS`. **Active in production.** |
| **Eval Suite** | `eval/` | LangSmith evaluation: golden sets, metric evaluators, CLI runner. |

---

## 📁 Directory Structure

```
compliance-agent/
├── agents/              # Autonomous agents (collector, analyzer, knowledge)
├── connectors/          # External system integrations (NetSuite)
├── database/
│   ├── migrations/     # Alembic database migrations
│   └── seed_data/      # SOD rules, test data
├── docs/               # Comprehensive documentation
│   ├── LESSONS_LEARNED.md       # All 15 issues + solutions (CRITICAL REFERENCE)
│   ├── MCP_SERVER_MANAGEMENT.md # Operations guide
│   └── *.md            # Architecture, troubleshooting, user guides
├── mcp/                # Model Context Protocol server
├── models/             # SQLAlchemy ORM models
├── repositories/       # Data access layer
├── scripts/            # Management scripts (restart, status check)
├── services/           # Business logic (NetSuite client, LLM service)
├── tests/              # Test suites
└── eval/               # LangSmith evaluation suite
    ├── golden_set.py   # 32 tool-selection + 10 answer-quality labelled examples
    ├── evaluators.py   # Hit Rate@K, MRR, NDCG@K, Precision@K, Faithfulness
    └── run_eval.py     # CLI runner (--router=keyword|semantic, --suite=compare)

Key Files:
- .env                  # Environment config (DATABASE_URL, API keys)
- requirements.txt      # Python dependencies
- CLAUDE.md            # This file
```

---

## 🔧 Technology Stack

### Core Technologies

- **Python 3.9+**: Primary language
- **FastAPI**: Web framework for MCP server
- **SQLAlchemy**: ORM for PostgreSQL
- **PostgreSQL 14+**: Database with pgvector extension
- **APScheduler**: Background job scheduling
- **Alembic**: Database migrations

### External Integrations

- **NetSuite RESTlet API**: User/role/permission data source
- **Anthropic API (Claude Opus 4.6)**: SOD analysis LLM
- **OpenAI API**: Embeddings for semantic search
- **pgvector**: Vector similarity search for RAG

### Key Libraries

```python
fastapi==0.104.1          # MCP server
uvicorn==0.24.0           # ASGI server
sqlalchemy==2.0.23        # ORM
psycopg2-binary==2.9.9    # PostgreSQL driver
anthropic==0.8.0          # Claude API client
openai==1.6.1             # OpenAI API client
apscheduler==3.10.4       # Job scheduler
pgvector==0.2.4           # Vector search
alembic==1.13.0           # Migrations
```

---

## 🚀 Getting Started

### Prerequisites

```bash
# Check Python version (requires 3.9+)
python3 --version

# Check PostgreSQL (requires 14+ with pgvector)
psql --version

# Ensure environment variables are set
cat .env | grep -E "DATABASE_URL|ANTHROPIC_API_KEY|NETSUITE_"
```

### Starting the MCP Server

```bash
# Option 1: Using restart script (recommended)
./scripts/restart_mcp.sh

# Option 2: Manual start
python3 -m mcp.mcp_server > /tmp/mcp_server.log 2>&1 &

# Check status
./scripts/check_mcp_status.sh

# View logs
tail -f /tmp/mcp_server.log
```

### Connecting Claude Desktop (STDIO Bridge)

The MCP server uses HTTP transport, but Claude Desktop expects STDIO. We use a bridge to connect them:

**Bridge File:** `/Users/prabal.saha/mcp_stdio_http_bridge.py`

```bash
# Add to Claude Desktop config:
# ~/Library/Application Support/Claude/claude_desktop_config.json

{
  "mcpServers": {
    "compliance-system": {
      "command": "python3",
      "args": ["/Users/prabal.saha/mcp_stdio_http_bridge.py"]
    }
  }
}

# Test bridge
echo '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}' | python3 /Users/prabal.saha/mcp_stdio_http_bridge.py

# Check Claude Desktop logs
tail -f ~/Library/Logs/Claude/mcp-server-compliance-system.log
```

**See:** `docs/MCP_STDIO_HTTP_BRIDGE.md` for complete documentation.

### Database Operations

```bash
# Connect to database
psql $DATABASE_URL

# Run migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Create new migration
alembic revision --autogenerate -m "Description"
```

---

## 📋 Development Guidelines

### Code Conventions

1. **Python Style**: Follow PEP 8, use type hints
2. **Naming**:
   - Classes: `PascalCase` (e.g., `DataCollectionAgent`)
   - Functions/methods: `snake_case` (e.g., `analyze_user`)
   - Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_PAGE_SIZE`)
3. **Imports**: Standard library → Third-party → Local (separated by blank lines)
4. **Docstrings**: Use for all public classes/functions

### Database Guidelines

⚠️ **CRITICAL**: See `docs/LESSONS_LEARNED.md` Issues #1, #14 for database pitfalls

1. **Reserved Names**: Never use `metadata` as a column name (SQLAlchemy reserves it)
2. **Enum Values**: Python enums use UPPERCASE, ensure DB constraints match
3. **Foreign Keys**: Always verify referential integrity chain before inserting
4. **Transactions**: Use proper session management, handle rollbacks

Example:
```python
# ✅ GOOD: Enum values match DB constraints
class SyncStatus(enum.Enum):
    PENDING = "PENDING"     # DB constraint expects UPPERCASE
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"

# ✅ GOOD: Proper column naming
class SyncMetadata(Base):
    sync_metadata = Column(JSON)  # Avoid 'metadata' (reserved)

# ✅ GOOD: Foreign key chain
# sync_metadata ← users
# compliance_scans → violations (scan_id FK)
```

### NetSuite Integration

⚠️ **CRITICAL**: See `docs/LESSONS_LEARNED.md` Issue #13 for pagination bug

1. **Page Size Limit**: NetSuite RESTlet caps at 200 users per request (not 1000!)
2. **Pagination**: Always use `page_size=200` for user queries
3. **Error Handling**: NetSuite silently truncates, verify record counts
4. **Rate Limiting**: Respect API limits (consider delays for large syncs)

Example:
```python
# ✅ GOOD: Correct page size
result = self.client.get_all_users_paginated(
    page_size=200,  # NetSuite's actual limit
    include_permissions=True
)

# ❌ BAD: Will silently lose 79.2% of data
result = self.client.get_all_users_paginated(
    page_size=1000,  # NetSuite caps at 200
    include_permissions=True
)
```

### LLM Integration

1. **Model Selection**: Use `claude-opus-4.6` for SOD analysis (most capable)
2. **Message Format**: Use proper roles (`system`, `user`, `assistant`)
3. **Error Handling**: LLM calls can fail, implement retries with exponential backoff
4. **Token Management**: Be mindful of context limits (200K tokens for Opus 4.6)

Example:
```python
# ✅ GOOD: Proper message format
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_query}
]

# ❌ BAD: Wrong key names
messages = [
    {"type": "system", "text": system_prompt}  # Wrong keys
]
```

---

## 🧪 Testing

### Eval Suite (LangSmith)

```bash
# Push golden datasets (one-time setup or after changing golden_set.py)
LANGSMITH_API_KEY=... python -m eval.golden_set

# Run semantic router eval (no live server needed)
LANGSMITH_API_KEY=... python -m eval.run_eval --router=semantic

# Compare keyword vs semantic side-by-side
LANGSMITH_API_KEY=... python -m eval.run_eval --suite=compare

# Run answer faithfulness eval (requires MCP server at :8080)
LANGSMITH_API_KEY=... python -m eval.run_eval --suite=answer_quality
```

View results: smith.langchain.com → project `compliance-agent` → Datasets → Experiments

### Smoke Test Suite

```bash
# Run all tests
python3 -m pytest tests/

# Run specific test
python3 -m pytest tests/test_data_collection.py::test_full_sync

# Run with verbose output
python3 -m pytest -v tests/
```

### Manual Testing Commands

```bash
# Test MCP tools (from Claude Code or MCP client)
list_systems
get_violation_stats
list_all_users(limit=10)

# Test data collection
python3 -c "from agents.data_collector import DataCollectionAgent; agent = DataCollectionAgent(); agent.full_sync()"

# Test database connection
psql $DATABASE_URL -c "SELECT COUNT(*) FROM users;"

# Test NetSuite connection
python3 -c "from services.netsuite_client import NetSuiteClient; client = NetSuiteClient(); print(client.get_all_users_paginated(page_size=10))"
```

---

## 🔍 Common Tasks

### 1. Adding a New SOD Rule

1. Add rule to `database/seed_data/sod_rules.json`
2. Rule format:
   ```json
   {
     "rule_code": "UNIQUE_CODE",
     "rule_name": "Descriptive Name",
     "description": "What this rule checks",
     "conflicting_permissions": ["PERM1", "PERM2"],
     "severity": "CRITICAL|HIGH|MEDIUM|LOW",
     "risk_category": "Financial|Security|Compliance"
   }
   ```
3. Restart MCP server to load new rule
4. Trigger sync to apply: `trigger_manual_sync(sync_type="full")`

### 2. Adding a New MCP Tool

1. Add tool function to `mcp/mcp_server.py`
2. Follow FastAPI route pattern:
   ```python
   @app.post("/tools/{tool_name}")
   async def tool_name(request: ToolRequest) -> ToolResponse:
       # Implementation
       pass
   ```
3. Add to `TOOLS` list in startup function
4. **Register in both routers:**
   - `utils/tool_router.py` — add to the appropriate `TOOL_GROUPS` entry (keyword fallback)
   - `utils/semantic_router.py` — add an entry to `TOOL_EXEMPLARS` with description + 3–5 example queries (primary router)
   Without this step, the tool will never appear in Claude's shortlist.
5. Restart server
6. Verify with `tools/list` MCP request

### 3. Debugging Data Collection Issues

```bash
# 1. Check agent status
./scripts/check_mcp_status.sh

# 2. Check recent logs
tail -100 /tmp/mcp_server.log | grep -i "error\|warning"

# 3. Check sync history
psql $DATABASE_URL -c "SELECT * FROM sync_metadata ORDER BY started_at DESC LIMIT 5;"

# 4. Check user counts
psql $DATABASE_URL -c "SELECT COUNT(*) FROM users;"
psql $DATABASE_URL -c "SELECT COUNT(*) FROM users WHERE is_active = true;"

# 5. Trigger manual sync
# From Claude Code: trigger_manual_sync(sync_type="full")

# 6. Check for violations
psql $DATABASE_URL -c "SELECT severity, COUNT(*) FROM violations GROUP BY severity;"
```

### 4. Database Migration

```bash
# Create migration after model changes
alembic revision --autogenerate -m "Add new column to violations table"

# Review generated migration in database/migrations/versions/

# Apply migration
alembic upgrade head

# If issues, rollback
alembic downgrade -1

# Check current version
alembic current
```

---

## ⚠️ Critical Issues to Avoid

### **MUST READ**: `docs/LESSONS_LEARNED.md`

This document contains 15 major issues encountered during development. **Read this before making changes** to avoid repeating mistakes.

### Top 5 Critical Issues

1. **Issue #13**: NetSuite page_size=1000 causes 79.2% data loss (use 200)
2. **Issue #1**: Never use `metadata` as SQLAlchemy column name (reserved)
3. **Issue #14**: Python enum values must match DB CHECK constraints (use UPPERCASE)
4. **Issue #15**: Create `compliance_scans` record before inserting violations
5. **Issue #9**: Verify repository methods exist before calling (check interfaces)

### Common Pitfalls

```python
# ❌ WRONG: These will break
class MyModel(Base):
    metadata = Column(JSON)  # SQLAlchemy reserves this

sync.status = "pending"  # DB expects "PENDING" (uppercase)

# Inserting violation without compliance_scan
violation.scan_id = sync.id  # FK references compliance_scans, not sync_metadata

# ❌ WRONG: NetSuite pagination
get_users(page_size=1000)  # Silently caps at 200, loses data

# ✅ RIGHT: Correct implementations
class MyModel(Base):
    sync_metadata = Column(JSON)  # Use different name

sync.status = SyncStatus.PENDING  # Use enum (UPPERCASE value)

# Create scan first, then violations
scan = ComplianceScan(...)
session.add(scan)
session.commit()
violation.scan_id = scan.id  # Now FK is valid

get_users(page_size=200)  # NetSuite's actual limit
```

---

## 🛠️ Troubleshooting

### Server Won't Start

```bash
# Check if port 8080 is in use
lsof -i :8080

# Kill existing process
pkill -f "mcp.mcp_server"

# Check Python environment
python3 -c "import mcp.mcp_server"

# Check database connection
psql $DATABASE_URL -c "SELECT 1;"

# Review startup logs
cat /tmp/mcp_server.log
```

### Data Collection Not Working

```bash
# 1. Check agent status
psql $DATABASE_URL -c "SELECT * FROM sync_metadata ORDER BY started_at DESC LIMIT 1;"

# 2. Check for errors in logs
grep -i "error" /tmp/mcp_server.log | tail -20

# 3. Verify NetSuite credentials
python3 -c "from services.netsuite_client import NetSuiteClient; c=NetSuiteClient(); print(c.get_all_users_paginated(page_size=1))"

# 4. Check scheduled jobs
grep -i "scheduler\|job" /tmp/mcp_server.log | tail -10
```

### Database Issues

```bash
# Check connection
psql $DATABASE_URL -c "\conninfo"

# Check table structure
psql $DATABASE_URL -c "\d users"

# Check for constraint violations
psql $DATABASE_URL -c "SELECT conname, contype FROM pg_constraint WHERE conrelid = 'violations'::regclass;"

# Reset database (⚠️ DESTRUCTIVE)
psql $DATABASE_URL -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
alembic upgrade head
```

### MCP Tools Not Working

```bash
# List available tools
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# Test specific tool
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"list_systems","arguments":{}}}'
```

---

## 📚 Documentation

### Essential Reading

1. **LESSONS_LEARNED.md**: All 15 issues + root causes + solutions (READ FIRST)
2. **MCP_SERVER_MANAGEMENT.md**: Server operations, monitoring, troubleshooting
3. **MCP_STDIO_HTTP_BRIDGE.md**: STDIO-HTTP bridge for Claude Desktop
4. **ARCHITECTURE.md**: System design, data flow, component interactions
5. **DEMO_INSTRUCTIONS.md**: Step-by-step demo walkthrough

### Quick Reference

| Topic | Document | Section |
|-------|----------|---------|
| Database schema | `ARCHITECTURE.md` | Database Design |
| SOD rules | `database/seed_data/sod_rules.json` | - |
| API endpoints | `mcp/mcp_server.py` | FastAPI routes |
| Server management | `MCP_SERVER_MANAGEMENT.md` | All sections |
| Claude Desktop bridge | `MCP_STDIO_HTTP_BRIDGE.md` | All sections |
| Known issues | `LESSONS_LEARNED.md` | Issues #1-15 |

---

## 🎓 Project-Specific Knowledge

### SOD (Segregation of Duties) Basics

**Definition**: Security principle that no single person should have permissions that could enable fraud

**Example Violation**: Same user can:
- Create vendor (Vendor Master Data)
- Create invoice (AP Processing)
- Approve payment (AP Approval)
→ Risk: Could create fake vendor and pay themselves

### 18 Active SOD Rules

| Risk Category | Rule Count | Examples |
|---------------|------------|----------|
| Financial | 8 | AP Entry vs Approval, Journal Entry vs Approval |
| Security | 5 | Admin vs Regular User, Script Dev vs Production |
| Compliance | 5 | Compliance Officer Independence, Audit Log Access |

### Severity Levels

- **CRITICAL**: Direct fraud risk, immediate remediation required
- **HIGH**: Significant risk, remediate within 30 days
- **MEDIUM**: Moderate risk, remediate within 90 days
- **LOW**: Minor risk, document compensating controls

---

## 🔐 Security Considerations

### Sensitive Files (Never Commit)

```bash
.env                    # API keys, database credentials
*.log                   # May contain sensitive data
database/compliance_db/ # Local database files
__pycache__/           # Compiled Python files
```

### Environment Variables Required

```bash
# Database
DATABASE_URL="postgresql://user:pass@localhost:5432/compliance_db"

# NetSuite
NETSUITE_ACCOUNT_ID="5260239_SB1"
NETSUITE_CONSUMER_KEY="..."
NETSUITE_CONSUMER_SECRET="..."
NETSUITE_TOKEN_ID="..."
NETSUITE_TOKEN_SECRET="..."
NETSUITE_RESTLET_URL="https://..."

# LLM Providers (at least one required)
ANTHROPIC_API_KEY="sk-ant-..."  # For Claude (SOD analysis)
OPENAI_API_KEY="sk-..."         # For embeddings (knowledge base)

# LangSmith Observability (required for cost/token tracing)
LANGSMITH_API_KEY="lsv2_pt_..."
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=compliance-agent

# Slack Bot
SLACK_BOT_TOKEN="xoxb-..."
SLACK_APP_TOKEN="xapp-..."
```

---

## 🚀 Deployment

### Production Checklist

- [ ] Environment variables set in production environment
- [ ] Database migrations applied (`alembic upgrade head`)
- [ ] PostgreSQL has pgvector extension installed
- [ ] NetSuite credentials validated
- [ ] LLM API keys validated
- [ ] Firewall allows port 8080 access
- [ ] Log rotation configured for `/tmp/mcp_server.log`
- [ ] Monitoring alerts set up (use `check_mcp_status.sh`)
- [ ] Backup strategy for PostgreSQL database
- [ ] Documentation reviewed by operations team

### Running in Production

```bash
# Use systemd service (recommended)
# Create /etc/systemd/system/mcp-server.service
[Unit]
Description=MCP Compliance Server
After=network.target postgresql.service

[Service]
Type=simple
User=mcp-user
WorkingDirectory=/opt/compliance-agent
Environment="PATH=/usr/bin:/usr/local/bin"
EnvironmentFile=/opt/compliance-agent/.env
ExecStart=/usr/bin/python3 -m mcp.mcp_server
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# Enable and start
sudo systemctl enable mcp-server
sudo systemctl start mcp-server
sudo systemctl status mcp-server
```

---

## 📞 Support & Resources

### Internal Resources

- **Documentation**: `docs/` directory
- **Issue Tracker**: `docs/LESSONS_LEARNED.md` (15 documented issues)
- **Architecture**: `docs/ARCHITECTURE.md`
- **Operations**: `docs/MCP_SERVER_MANAGEMENT.md`

### External Resources

- **Model Context Protocol**: https://modelcontextprotocol.io
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **SQLAlchemy Docs**: https://docs.sqlalchemy.org
- **Claude API Docs**: https://docs.anthropic.com
- **NetSuite SuiteScript**: https://docs.oracle.com/en/cloud/saas/netsuite

### Common Questions

**Q: Why is the server running on port 8080?**
A: Default MCP server port. Change in `mcp/mcp_server.py` if needed.

**Q: How often does data sync?**
A: Full sync daily at 2:00 AM, incremental sync every hour.

**Q: Can I change the SOD rules?**
A: Yes, edit `database/seed_data/sod_rules.json` and restart server.

**Q: Why Claude Opus 4.6?**
A: Most capable model for complex compliance reasoning and context understanding.

**Q: How do I add a new data source besides NetSuite?**
A: Create new connector in `connectors/`, implement `BaseConnector` interface, register in `data_collector.py`.

---

## 🎯 Current Status (2026-02-27)

### ✅ Completed

- [x] Phase 1: Autonomous data collection (daily + hourly sync)
- [x] Phase 2: AI-powered SOD analysis (18 rules active)
- [x] Phase 3: pgvector knowledge base (RAG operational)
- [x] MCP server with 35 tools
- [x] Production-ready scripts (restart, status check)
- [x] Comprehensive documentation (4 major docs)
- [x] 99.7% user coverage (1,928/1,933 users synced)
- [x] **NEW**: Slack bot with multi-turn agentic reasoning (Feb 2026)
- [x] **NEW**: LangSmith distributed tracing — cost, tokens, latency per query (Feb 2026)
- [x] **NEW**: DM conversation context — bot maintains history across messages (Feb 2026)
- [x] **NEW**: Haiku/Opus model split — Haiku dispatches tools, Opus synthesizes answers (Feb 2026)
- [x] **NEW**: 3 online LangSmith evaluators — hallucination, tool enforcement, coverage (Feb 2026)
- [x] **NEW**: Phase A Redis TTL cache — MCP tool call deduplication within TTL window (Feb 2026)
- [x] **NEW**: Phase B conversation summarization — Haiku summaries stored in Postgres, injected as prior context (Feb 2026)
- [x] **NEW**: DM thread_history fix — handle_dm() now correctly passes prior conversation to Claude (Feb 2026)
- [x] **NEW**: Fixed LangSmith `context_cache_hit` root-run tagging — `threading.local()` propagates cache hit flag from child span to root trace (2026-02-26)
- [x] **NEW**: Angular Configuration Portal Phase 1 — JWT auth, 16 admin API endpoints, Angular 17 frontend with Dashboard/Violations/Exceptions/SOD Rules/Thresholds/Feature Flags screens (2026-02-26)
- [x] **NEW**: Feedback loop — Block Kit buttons on every response; `answer_feedback` Postgres table; LangSmith `human_rating` write-back; Redis cache bust on NEGATIVE signal (2026-02-26)
- [x] **NEW**: FivetranChat-style formatting — clean prose responses, no decorative emojis; feedback buttons simplified to 👎 👍 (2026-02-27)
- [x] **NEW**: Role risk matrix — precomputed SOD conflict matrix for all 17 Fivetran roles and 153 role pairs. Tables: `sod_permission_map`, `role_pair_conflicts` (443 rows). Analysis job: `scripts/build_role_risk_matrix.py`. Level-aware: None < View < Create < Edit < Full. (2026-02-27)
- [x] **NEW**: `get_role_risk_matrix` MCP tool — queries precomputed matrix with role_name/severity/intra/cross filters. Cached 24h. (2026-02-27)
- [x] **NEW**: `list_violations` MCP tool — department/severity filters, roles_only mode, DISTINCT ON deduplication. (2026-02-27)
- [x] **NEW**: `role_risk` intent group in `utils/tool_router.py` — routes role-risk queries to `get_role_risk_matrix`. (2026-02-27)
- [x] **NEW**: McKinsey partner voice in system prompt — executive language, conclusions first, direct recommendations. (2026-02-27)
- [x] **NEW**: `_trim_history` fix — prevents orphaned tool_result blocks (Anthropic API 400) by trimming only at HumanMessage boundaries. (2026-02-27)
- [x] **NEW**: Response length management — `MAX_SLACK_RESPONSE_CHARS=2000`, `_trim_response_for_slack()` auto-uploads long responses via `files_upload_v2()`, user-friendly fallback when upload fails (requires `files:write` scope) (2026-02-27)
- [x] **NEW**: Response length prompt constraints — `HARD LIMIT` for `get_role_risk_matrix` (3 bullets, 1200 chars max), `GLOBAL RESPONSE LENGTH` rule (1800 chars max for all responses) (2026-02-27)
- [x] **NEW**: Dynamic capabilities intro — bot calls `list_systems` when asked "what can you do", lists only connected systems, describes cross-system compliance when multiple systems active (2026-02-27)
- [x] **NEW**: Identity rebrand — removed "SOD compliance agent"; bot is now "Fivetran's compliance agent"; SOD is one capability, not the identity; explicit prohibition in system prompt (2026-02-27)
- [x] **NEW**: Feedback Phase C — Correction embeddings (pgvector, MiniLM 384-dim) stored on every ❌ Wrong correction; cosine ANN search injects top-3 similar past corrections as few-shot context into every future query; `correction_embeddings` table + ivfflat index; `services/correction_service.py`; backfill via `scripts/embed_corrections.py`; feature flag `USE_CORRECTION_CONTEXT=true` (2026-02-27)
- [x] **NEW**: Regex tool router fixed — plural/singular patterns corrected; `always_include` moved to end of shortlist; MRR 0.18 → 0.41 (2026-03-15)
- [x] **NEW**: Semantic tool router (`utils/semantic_router.py`) — MiniLM-L6-v2 embeddings, curated exemplars per tool; Hit Rate@10 1.00, MRR 0.91, NDCG 0.89 (2026-03-15)
- [x] **NEW**: LangSmith eval suite (`eval/`) — golden sets, 5 retrieval metrics + faithfulness judge; `--suite=compare` runs keyword vs semantic side-by-side (2026-03-15)

### 🚧 Known Issues

- OpenSSL warning (urllib3 v2 with LibreSSL 2.8.3) - cosmetic, non-blocking
- FastAPI deprecation warnings (on_event → lifespan) - non-critical
- Optional LLM packages not installed (OpenAI, Gemini, Cohere) - features work without them

### 🖥️ Latest Enhancement: Angular Configuration Portal — Phase 1 (Feb 2026)

A full Angular 17 admin portal is now live in `angular-portal/` backed by new FastAPI admin endpoints.

**Backend — New admin API (`mcp/admin_api.py`):**
- `POST /auth/login` — JWT issuance (L3+ NetSuite roles required)
- `GET /auth/me` — current user + authority level
- `GET /admin/system-health` — integration health check
- `GET /admin/config` — all non-secret config items
- `PATCH /admin/config/thresholds|notifications|scheduling|feature-flags|llm` — editable config
- `GET/PATCH /admin/sod-rules` — view and edit 18 SOD rules
- `GET/PATCH /admin/violations` — paginated violations with status updates
- `GET /admin/exceptions` + `/due-review` — approved exceptions + overdue list
- `GET /admin/audit-trail` — audit log
- `GET /admin/token-analytics` — LLM cost/usage summary

**Authority levels (derived from NetSuite roles):**
- L3 (Director): read-only access
- L4 (Controller/VP): read + edit thresholds, rules, notifications, scheduling
- L5 (CFO): full access including feature flags, LLM config

**Frontend — Angular portal (`angular-portal/`):**
- Angular 17 + Angular Material (standalone components + signals)
- JWT stored in-memory only (no localStorage, XSS-safe)
- Auth guard + level guard for route protection
- Lazy-loaded routes: Dashboard, Violations, Exceptions, SOD Rules, Thresholds, Feature Flags
- Dev proxy: `proxy.conf.json` forwards `/auth` + `/admin` to `localhost:8080`

**New dependencies:**
```bash
pip install "python-jose[cryptography]>=3.3.0" "passlib[bcrypt]>=1.7.4"
```

**Required new env vars:**
```bash
JWT_SECRET=<long-random-string>         # Required for JWT signing
ADMIN_PORTAL_PASSWORD=<portal-password> # Portal login password (dev)
JWT_EXPIRE_HOURS=8                      # Optional, default 8h
```

**Run the portal:**
```bash
# Start MCP server (includes new admin routes)
./scripts/restart_mcp.sh

# Start Angular dev server (with proxy)
cd angular-portal && ng serve
# Open http://localhost:4200
```

**See:** `docs/ANGULAR_UX_PLAN.md` for full spec and remaining phases (2-4).

### 📈 Future Enhancements

See `docs/LESSONS_LEARNED.md` → Technical Debt section for full list.

Priority items:
1. Angular Portal Phase 2 — Read-only screens: Audit Trail, Token Analytics
2. Angular Portal Phase 3 — Editable config: Notifications, Scheduling, Integrations
3. Angular Portal Phase 4 — LLM config, SOD rule severity editing, credential rotation
4. Migrate FastAPI startup/shutdown to lifespan handlers
5. Add integration tests for full sync workflow
6. Implement log rotation for production

---

## 💡 Tips for Claude Code Sessions

### When Starting a New Session

1. Read this file (CLAUDE.md) first
2. Review `docs/LESSONS_LEARNED.md` for context on past issues
3. Check current server status: `./scripts/check_mcp_status.sh`
4. Review recent logs: `tail -50 /tmp/mcp_server.log`

### Before Making Database Changes

1. Check `docs/LESSONS_LEARNED.md` Issues #1, #14, #15
2. Create Alembic migration: `alembic revision --autogenerate`
3. Review generated SQL carefully
4. Test migration on dev database first
5. Backup production database before applying

### Before Modifying Data Collection

1. Check `docs/LESSONS_LEARNED.md` Issue #13 (NetSuite pagination)
2. Verify page_size=200 (not 1000)
3. Test with small dataset first
4. Monitor sync_metadata table for errors
5. Verify user counts match NetSuite

### When Debugging

1. Use `./scripts/check_mcp_status.sh` for comprehensive health check
2. Check logs: `tail -f /tmp/mcp_server.log`
3. Query database: `psql $DATABASE_URL`
4. Review relevant documentation in `docs/`
5. Check if issue is documented in LESSONS_LEARNED.md

---

**Version History:**
- v2.0 (2026-03-15): Semantic tool router (MiniLM embeddings, Hit Rate@10=1.00, MRR=0.91); LangSmith eval suite (golden sets, 5 metrics + faithfulness); regex router fixes (plural patterns, always_include ranking)
- v1.8 (2026-02-27): Feedback Phase C — correction embeddings + few-shot injection (correction_embeddings table, CorrectionService, embed_corrections.py backfill)
- v1.7 (2026-02-27): Response length management (auto-upload + truncation); dynamic capabilities intro (list_systems-driven); identity rebrand (compliance agent, not SOD agent); HARD LIMIT prompt constraints
- v1.6 (2026-02-27): Role risk matrix (17 roles, 153 pairs, 443 conflict rows); get_role_risk_matrix + list_violations tools; tool_router role_risk intent group; McKinsey partner voice; _trim_history API-400 fix
- v1.5 (2026-02-27): FivetranChat-style formatting (clean prose, no emoji); feedback buttons 👎 👍
- v1.4 (2026-02-26): Feedback loop — Block Kit buttons, answer_feedback table, LangSmith human_rating, Redis cache bust on NEGATIVE
- v1.3 (2026-02-26): Fixed LangSmith context_cache_hit tagging (threading.local fix)
- v1.2 (2026-02-22): LangSmith observability, ChatAnthropic migration, DM conversation context
- v1.1 (2026-02-16): MCP tool count 11→35, Slack bot multi-turn agentic tool use
- v1.0 (2026-02-12): Initial guide

**Maintained by:** AI Development Team
**Last Verified:** 2026-03-15
