# Building the Fivetran Compliance Agent: A Multi-Agent Playbook

**Version:** 1.1
**Last Updated:** 2026-02-27
**Purpose:** Reconstructing this system from scratch using autonomous parallel agents

---

## What This File Is

This is the build playbook for the Fivetran Compliance Agent — written as if you are
orchestrating a team of autonomous coding agents (Claude Code, Codex, etc.) rather than
a single developer working top-to-bottom.

Every section defines one agent's scope, inputs, outputs, prompt template, and
verification gate. Agents within the same Phase can run in parallel. Never start
a Phase until every gate from the prior Phase passes.

---

## System at a Glance

```
NetSuite / Okta / Salesforce
         ↓  (REST + OAuth)
   Data Collection Agent  ←── APScheduler (hourly/daily)
         ↓
   PostgreSQL 14 + pgvector
         ↓
   SOD Rules Engine (18 rules, 4 severities)
         ↓
   MCP Server (FastAPI, 37 tools, port 8080)
         ↓
   Slack Bot (Bolt, Socket Mode)  ←── Claude Opus 4.6 (LangChain)
         ↓
   LangSmith (tracing + human feedback)
```

**Stack:** Python 3.9 · FastAPI · SQLAlchemy 2.0 · PostgreSQL + pgvector · Redis ·
LangChain + LangSmith · Slack Bolt · Claude Opus 4.6 / Haiku 4.5 · Angular 17

---

## Agent Roster

| ID | Agent | Phase | Can Parallelise With |
|----|-------|-------|----------------------|
| A | Infrastructure Agent | 0 | B |
| B | Environment Agent | 0 | A |
| C | ORM Model Agent | 1 | D, E |
| D | Repository Agent | 1 | C, E |
| E | Connector Agent | 1 | C, D |
| F | LLM Service Agent | 2 | G, H |
| G | Embedding & Vector Agent | 2 | F, H |
| H | Redis Cache Agent | 2 | F, G |
| I | SOD Rules Engine Agent | 3 | J, K |
| J | Knowledge Base Agent | 3 | I, K |
| K | Data Sync Agent | 3 | I, J |
| L | MCP Server Agent | 4 | M |
| M | Tool Router Agent | 4 | L |
| N | Slack Bot Core Agent | 5 | Q, R |
| O | Memory & Cache Agent | 5 | P, Q, R |
| P | Feedback Loop Agent | 5 | O, Q, R |
| Q | LangSmith Observability Agent | 6 | R |
| R | Admin Portal Agent | 6 | Q |
| S | Role Risk Matrix Agent | 7 | — |
| T | Test Agent | 8 | U |
| U | QA Agent | 8 | T |
| V | Bug Fix Agent | 8 | — (runs after T + U complete) |

---

## Dependency Graph

```
Phase 0:  [A] [B]                          ← run first, in parallel
              ↓
Phase 1:  [C] [D] [E]                      ← all parallel after Phase 0
              ↓
Phase 2:  [F] [G] [H]                      ← all parallel after Phase 1
              ↓
Phase 3:  [I] [J] [K]                      ← all parallel after Phase 2
              ↓
Phase 4:  [L] [M]                          ← parallel after Phase 3
              ↓
Phase 5:  [N] [O] [P]   Phase 6: [Q] [R]  ← 5 and 6 run in parallel after Phase 4
              ↓
Phase 7:  [S]                              ← after Phase 4 (can overlap Phase 5/6)
              ↓
Phase 8:  [T] [U] ──────────→ [V]         ← T and U in parallel; V after both complete
```

---

## Phase 0 — Foundation

### Agent A: Infrastructure Agent

**Goal:** Postgres 14 + pgvector running; all migrations applied; SOD rules seeded.

**Inputs:** None
**Produces:**
- Local Postgres database `compliance_db` with pgvector extension
- All 9 migration files applied (`database/migrations/001–009`)
- `sod_rules` table seeded from `database/seed_data/sod_rules.json`

**Prompt:**
```
You are the Infrastructure Agent. Set up the compliance agent database:

1. Create local Postgres database: createdb compliance_db
2. Enable pgvector: psql compliance_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
3. Apply the base schema: psql compliance_db < database/schema.sql
4. Apply schema extensions: psql compliance_db < database/schema_extensions.sql
5. Apply all migrations in order (001→009) from database/migrations/
6. Seed SOD rules from database/seed_data/sod_rules.json into the sod_rules table
7. Verify: psql compliance_db -c "SELECT COUNT(*) FROM sod_rules;" must return 18

CRITICAL rules:
- NEVER use 'metadata' as a SQLAlchemy column name — it is reserved
- Enum values in Python must EXACTLY match DB CHECK constraints (use UPPERCASE)
- Always create compliance_scans records before inserting violations (FK dependency)
- NetSuite page_size must be 200, never 1000 (silent truncation)
```

**Verification gate:**
```bash
psql $DATABASE_URL -c "SELECT COUNT(*) FROM sod_rules;"       # → 18
psql $DATABASE_URL -c "\dt"                                     # → all tables present
psql $DATABASE_URL -c "SELECT extname FROM pg_extension WHERE extname='vector';"
```

---

### Agent B: Environment Agent

**Goal:** `.env` configured, Python venv active, all packages installed.

**Inputs:** `requirements.txt`
**Produces:** `.env` file, `.venv/` with all packages installed

**Prompt:**
```
You are the Environment Agent. Set up the Python environment:

1. Create .venv: python3 -m venv .venv
2. Activate and install: .venv/bin/pip install -r requirements.txt
3. Create .env with all required variables (see template below)
4. Verify imports: .venv/bin/python -c "import anthropic, langsmith, slack_bolt, fastapi, sqlalchemy, redis, pgvector"

.env template:
DATABASE_URL=postgresql://localhost/compliance_db
ANTHROPIC_API_KEY=sk-ant-...
LANGSMITH_API_KEY=lsv2_pt_...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=compliance-agent
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
REDIS_URL=redis://localhost:6379/0
NETSUITE_ACCOUNT_ID=...
NETSUITE_CONSUMER_KEY=...
NETSUITE_CONSUMER_SECRET=...
NETSUITE_TOKEN_ID=...
NETSUITE_TOKEN_SECRET=...
NETSUITE_RESTLET_URL=https://...
USE_MCP_CACHE=true
USE_CONV_SUMMARIES=true
USE_ANSWER_FEEDBACK=true
MAX_TOKENS_SLACK=1024
SLACK_MAX_RESPONSE_CHARS=2000
JWT_SECRET=<64-char-random>
ADMIN_PORTAL_PASSWORD=<password>
```

**Verification gate:**
```bash
.venv/bin/python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('DATABASE_URL'))"
.venv/bin/python -c "import redis; r=redis.from_url('redis://localhost:6379/0'); r.ping()"
```

---

## Phase 1 — Data Layer

### Agent C: ORM Model Agent

**Goal:** All SQLAlchemy models defined, matching the schema exactly.

**Inputs:** `database/schema.sql`, `database/schema_extensions.sql`
**Produces:** All files in `models/`

**Prompt:**
```
You are the ORM Model Agent. Create SQLAlchemy 2.0 models for every table in schema.sql.

File pattern — follow models/database.py exactly:
  - Use declarative_base()
  - Every model gets __tablename__, primary key UUID with default=uuid.uuid4
  - Timestamps: created_at = Column(DateTime, default=datetime.utcnow)
  - Foreign keys must match the actual table name, not the class name

CRITICAL: NEVER name any column 'metadata' — SQLAlchemy reserves it for internal use.
Use 'sync_metadata', 'rule_metadata', 'extra_data', etc. instead.

Models to create:
  - User, Role, Permission, UserRole, UserPermission
  - SodRule, Violation, ComplianceScan, SyncMetadata
  - ApprovedExceptionRequest, AuditTrail
  - ConversationSummary (models/conversation_summary.py)
  - AnswerFeedback (models/answer_feedback.py) — includes run_id, signal, correction fields
  - SodPermissionMap, RolePairConflicts (for the precomputed role risk matrix)

For AnswerFeedback, signal must be constrained to: POSITIVE | NEGATIVE | PARTIAL | UNCLEAR
```

**Verification gate:**
```bash
.venv/bin/python -c "from models.database import Base; from models.answer_feedback import AnswerFeedback; print('OK')"
```

---

### Agent D: Repository Agent

**Goal:** Data access layer — one repository per domain entity.

**Inputs:** Models from Agent C
**Produces:** All files in `repositories/`

**Prompt:**
```
You are the Repository Agent. Create repository classes for every SQLAlchemy model.

Pattern (from repositories/user_repository.py):
  class UserRepository:
      def __init__(self, session: Session): self.session = session
      def get_by_id(self, id: UUID) -> Optional[User]: ...
      def get_by_email(self, email: str) -> Optional[User]: ...
      def list_active(self, limit=100) -> List[User]: ...
      def upsert(self, user_data: dict) -> User: ...

Repositories needed:
  user_repository, role_repository, violation_repository
  sod_rule_repository, exception_repository, sync_metadata_repository
  audit_trail_repository, job_role_mapping_repository

Do NOT add methods that don't have a clear caller — keep repositories thin.
Verify every method exists before calling it elsewhere (past agents failed on this).
```

---

### Agent E: Connector Agent

**Goal:** NetSuite RESTlet connector that pages correctly.

**Inputs:** NetSuite credentials from `.env`
**Produces:** `connectors/netsuite_connector.py`, `services/netsuite_client.py`

**Prompt:**
```
You are the Connector Agent. Build the NetSuite OAuth 1.0a RESTlet connector.

CRITICAL — NetSuite pagination:
  page_size MUST be 200. The API silently caps at 200 — using 1000 returns only
  the first 200 records with no error. This caused 79.2% data loss historically.

  CORRECT:  get_all_users_paginated(page_size=200)
  WRONG:    get_all_users_paginated(page_size=1000)

The connector must:
1. Sign requests with OAuth 1.0a (requests-oauthlib)
2. GET /services/rest/record/v1/employee with pagination
3. Return normalized user dicts: {id, email, name, is_active, roles[], last_modified}
4. Handle rate limiting with exponential backoff (max 3 retries)
5. Verify total: after sync, count rows in users table and log if < 1900
```

---

## Phase 2 — Core Services

### Agent F: LLM Service Agent

**Goal:** Multi-provider LLM abstraction; Claude Opus 4.6 as primary.

**Inputs:** API keys from `.env`
**Produces:** `services/llm/` (base, factory, anthropic provider, config_manager)

**Prompt:**
```
You are the LLM Service Agent. Build a multi-provider LLM abstraction layer.

Primary provider: Anthropic Claude (use langchain-anthropic ChatAnthropic, NOT the raw SDK).
Why LangChain: it integrates with LangSmith tracing automatically — raw SDK calls do not.

Factory pattern:
  LLMFactory.create(provider="anthropic", model="claude-opus-4-6") → BaseLLM

Model split (implement in Slack bot, document here):
  - Tool dispatch turns: claude-haiku-4-5-20251001 (fast, cheap)
  - Synthesis turns (after tool results arrive): claude-opus-4-6 (high quality)
  Detection: has_tool_results = any(isinstance(m, ToolMessage) for m in messages)

Token tracking: implement TokenTrackingCallback(LangChain BaseCallbackHandler)
  — logs prompt_tokens, completion_tokens, total_cost per call to LangSmith metadata
```

---

### Agent G: Embedding & Vector Agent

**Goal:** pgvector-backed semantic search for compliance policies.

**Inputs:** Postgres + pgvector (Agent A), sentence-transformers
**Produces:** `services/embedding_service.py`, `utils/vector_search.py`, `utils/violation_embedder.py`

**Prompt:**
```
You are the Embedding & Vector Agent. Build semantic search over compliance policies.

Stack: sentence-transformers (all-MiniLM-L6-v2) + pgvector.

Schema needed (add to schema_extensions.sql if not present):
  CREATE TABLE context_catalogue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding vector(384),
    source TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
  );
  CREATE INDEX ON context_catalogue USING ivfflat (embedding vector_cosine_ops);

EmbeddingService:
  - embed(text: str) → np.ndarray  (shape: 384,)
  - store(content, source) → UUID
  - search(query, limit=5, threshold=0.7) → List[dict]

Use cosine similarity: 1 - (embedding <=> query_vec) > threshold
```

---

### Agent H: Redis Cache Agent

**Goal:** Redis-backed MCP tool call cache with per-tool TTL.

**Inputs:** Redis URL from `.env`
**Produces:** `services/cache_service.py`

**Prompt:**
```
You are the Redis Cache Agent. Build the MCP tool call cache.

Cache key format: "mcp:{tool_name}:{md5(json.dumps(sorted_args))}"

TTL map (seconds):
  get_user_violations:    3600   # 1 hour
  get_violation_stats:    1800   # 30 min
  get_role_conflicts:     86400  # 24 hours
  get_role_risk_matrix:   86400  # 24 hours
  analyze_access_request: 3600   # 1 hour
  initialize_session:     300    # 5 min
  list_systems:           3600

Mutating tools — NEVER cache:
  trigger_manual_sync, approve_exception, request_exception_approval,
  remediate_violation, notify_manager

Cache hit: tag LangSmith root run with metadata.context_cache_hit=true
           and metadata.cache_tool=<tool_name>

Feature flag: USE_MCP_CACHE env var (default true). Check before every cache read/write.
```

---

## Phase 3 — Business Logic

### Agent I: SOD Rules Engine Agent

**Goal:** 18 SOD rules implemented; violation detection pipeline operational.

**Inputs:** sod_rules table (Agent A), repositories (Agent D)
**Produces:** `agents/analyzer.py`, `agents/risk_assessor.py`

**Prompt:**
```
You are the SOD Rules Engine Agent. Build the violation detection pipeline.

18 active SOD rules across 3 categories:
  Financial (8): AP Entry vs AP Approval, Journal Entry vs Journal Approval,
                 Bill Entry vs Pay Bills, Vendor Create vs AP Processing, etc.
  Security  (5): Admin vs Regular User, Script Deploy vs Production, etc.
  Compliance(5): Compliance Officer Independence, Audit Log Access, etc.

Severity: CRITICAL → HIGH → MEDIUM → LOW (use UPPERCASE in DB CHECK constraints)

Analyzer pipeline:
  1. Load user's current roles + permissions from DB
  2. For each SOD rule: check if user has both conflicting permissions
  3. Score: CRITICAL=100, HIGH=75, MEDIUM=50, LOW=25
  4. Write Violation records with scan_id FK to ComplianceScan

CRITICAL: Always create ComplianceScan record BEFORE inserting Violations.
          Violation.scan_id is a FK to compliance_scans — not to sync_metadata.
```

**Verification gate:**
```bash
psql $DATABASE_URL -c "SELECT severity, COUNT(*) FROM violations GROUP BY severity;"
# Should show rows for each severity level
```

---

### Agent J: Knowledge Base Agent

**Goal:** RAG pipeline for compliance policy lookup.

**Inputs:** Embedding service (Agent G), pgvector schema
**Produces:** `agents/knowledge_base_pgvector.py`, `scripts/seed_knowledge_base.py`

**Prompt:**
```
You are the Knowledge Base Agent. Build a RAG pipeline for compliance policy lookup.

Sources to embed:
  - SOD rules (from sod_rules table — include rule_name, description, risk_category)
  - Remediation guidance (from database/seed_data/)
  - Policy text (add to database/seed_data/compliance_policies.txt if needed)

KnowledgeBase.query(user_question, limit=5):
  1. Embed the question
  2. Cosine search context_catalogue
  3. Return top-k chunks above threshold 0.7
  4. Format as few-shot context for the LLM system prompt

MCP tool: query_knowledge_base(search_term, limit=5) → formatted string
```

---

### Agent K: Data Sync Agent

**Goal:** Autonomous scheduled data collection — full daily + incremental hourly.

**Inputs:** NetSuite connector (Agent E), repositories (Agent D)
**Produces:** `agents/data_collector.py`, `agents/orchestrator.py`, `manage_collector.py`

**Prompt:**
```
You are the Data Sync Agent. Build the autonomous data collection pipeline.

Schedule (APScheduler):
  - Full sync: daily at 02:00 UTC — all users, roles, permissions
  - Incremental: every hour — only records modified since last sync

Sync flow:
  1. Create SyncMetadata record (status=RUNNING)
  2. Fetch users from NetSuite (page_size=200 — NEVER 1000)
  3. Upsert into users table
  4. Fetch roles, permissions, user-role assignments
  5. Run SOD analyzer (Agent I)
  6. Write violations, update SyncMetadata (status=SUCCESS, record_count)

Error handling:
  - NetSuite timeout: retry 3× with exponential backoff
  - DB error: rollback, set SyncMetadata.status=FAILED, log full traceback
  - NEVER silently swallow exceptions in the sync loop

MCP tools to expose: trigger_manual_sync, get_sync_status
```

---

## Phase 4 — MCP Server Layer

### Agent L: MCP Server Agent

**Goal:** FastAPI MCP server on port 8080 with all 37 tools registered.

**Inputs:** All agents from Phase 3
**Produces:** `mcp/mcp_server.py`, `mcp/mcp_tools.py`

**Prompt:**
```
You are the MCP Server Agent. Build the FastAPI MCP server.

Transport: HTTP JSON-RPC at POST /mcp  (NOT stdio — we use a bridge for Claude Desktop)
Port: 8080

Required endpoints:
  POST /mcp         → JSON-RPC dispatch (tools/list, tools/call)
  GET  /health      → {"status": "ok", "tools": N, "db": "connected"}

Tool categories (37 total):
  User & Violation:  get_user_violations, list_violations, get_violation_details,
                     get_violation_stats, list_all_users
  Access Review:     analyze_access_request, validate_job_role, list_sod_rules,
                     get_sod_rule_details, query_sod_rules
  Exceptions:        request_exception_approval, approve_exception, list_active_exceptions,
                     get_exception_details, check_my_approval_authority
  Remediation:       remediate_violation, schedule_review, notify_manager,
                     create_remediation_ticket
  Reports:           generate_compliance_report, get_org_risk_assessment,
                     get_violation_report
  Sync:              trigger_manual_sync, get_sync_status
  Systems:           list_systems, initialize_session, get_compensating_controls
  Role Risk:         get_role_risk_matrix, get_role_conflicts
  Knowledge:         query_knowledge_base, find_similar_approved_exceptions
  Admin:             get_compliance_report, list_permissions, search_permissions,
                     get_user_details, get_role_details, get_department_stats

Every tool handler must:
  1. Log entry with parameters
  2. Use DatabaseConfig().get_session() pattern (NOT from database.db_setup import get_db_session)
  3. Return a formatted string (not JSON) — the MCP server wraps it in content[].text
  4. Include LIMIT parameter defaulting to 25-50 rows

NEVER import from database.db_setup — that module does not exist.
Use: from models.database_config import DatabaseConfig
```

**Verification gate:**
```bash
curl -s http://localhost:8080/health
curl -s -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d['result']['tools']), 'tools')"
# → 37 tools
```

---

### Agent M: Tool Router Agent

**Goal:** Pre-filter tools to reduce prompt tokens and force correct tool selection.

**Inputs:** MCP tool list from Agent L
**Produces:** `utils/tool_router.py`

**Prompt:**
```
You are the Tool Router Agent. Build a tool pre-filter that limits which MCP tools
Claude sees for each query — reducing prompt tokens by ~8K and preventing wrong tool selection.

Implementation: keyword-based intent classification → tool group selection

Intent groups:
  access_review:   [analyze_access_request, get_user_violations, validate_job_role,
                    get_compensating_controls, initialize_session, list_sod_rules]
  violation_query: [list_violations, get_violation_details, get_violation_stats,
                    get_user_violations, list_all_users]
  exception_mgmt:  [request_exception_approval, approve_exception, list_active_exceptions,
                    get_exception_details, check_my_approval_authority,
                    find_similar_approved_exceptions]
  remediation:     [remediate_violation, schedule_review, notify_manager,
                    create_remediation_ticket]
  reporting:       [generate_compliance_report, get_org_risk_assessment,
                    get_violation_report, get_violation_stats, get_department_stats]
  role_risk:       [get_role_risk_matrix, get_role_conflicts, list_violations]
  sync:            [trigger_manual_sync, get_sync_status]
  general:         [list_systems, initialize_session, list_sod_rules,
                    query_knowledge_base, list_permissions]

CRITICAL: Every new MCP tool MUST be registered in the appropriate intent group here.
          If a tool is not registered, Claude will never see it — it will be silently
          excluded from the tool list for every query.

select_tools_for_intent(query: str, all_tools: list) → list
  - Classify intent from query keywords
  - Return only the tools for matching intent groups
  - Always include: list_systems, initialize_session (universal context tools)
  - Fall back to all tools if no intent matches
```

---

## Phase 5 — Slack Bot

### Agent N: Slack Bot Core Agent

**Goal:** Multi-turn agentic Slack bot; DMs + @mentions; McKinsey partner voice.

**Inputs:** MCP server (Phase 4), LangChain (Phase 2), Redis (Phase 2)
**Produces:** `slack_bot_local.py` (core: handlers, process_with_claude, system prompt)

**Prompt:**
```
You are the Slack Bot Core Agent. Build the Slack bot using slack_bolt in Socket Mode.

Architecture:
  - Socket Mode (SLACK_APP_TOKEN=xapp-...) — no public webhook URL needed
  - Two entry points: @app.event("app_mention") and @app.event("message") for DMs
  - Core function: process_with_claude(user_message, user_email, ...) → str
    Uses ChatAnthropic (NOT raw Anthropic SDK) for LangSmith tracing
    Multi-turn loop (max 5 turns): Claude → tool calls → results → Claude → ...

Model split:
  - Haiku (claude-haiku-4-5-20251001): tool dispatch turns (decide which tool to call)
  - Opus (claude-opus-4-6): synthesis turns (after tool results arrive)
  Detection: has_tool_results = any(isinstance(m, ToolMessage) for m in messages)

System prompt must include these sections (in order):
  1. IDENTITY: "You are Fivetran's compliance agent" — NEVER "SOD compliance agent"
  2. DATA GROUNDING: always call MCP tools, never use training knowledge for counts/rules
  3. TOOL SELECTION: hard routing rules (get_role_risk_matrix vs list_violations)
  4. GLOBAL RESPONSE LENGTH: max 1,800 chars; if longer, top 3 points + follow-up offer
  5. HARD LIMIT (get_role_risk_matrix): max 3 bullets, 1,200 chars, no permission detail
  6. CAPABILITIES QUERY: call list_systems first; only ✅ systems; max 800 chars
  7. LANGUAGE: no "violator"; say "affected users"; no "dangerous"; say "high-risk"
  8. VOICE: senior McKinsey partner — conclusions first, evidence second, direct recommendations
  9. FORMATTING: Slack mrkdwn only; no ### headings; no markdown tables; no double asterisks

Response length guard:
  MAX_SLACK_RESPONSE_CHARS = 2000 (env-overridable)
  _trim_response_for_slack(response, client, channel):
    if len(response) > MAX_SLACK_RESPONSE_CHARS:
      upload full text via files_upload_v2() (requires files:write scope)
      return trimmed + permalink  (fallback: "Ask me about X for the complete breakdown")

History management:
  _trim_history(): NEVER naive tail-slice — always advance to first HumanMessage
  after slicing, or you orphan tool_use/tool_result pairs → Anthropic API 400.

Animate the "thinking" state: post "⏳ Thinking..." → update in-place with real response.
```

**Required Slack OAuth scopes:**
```
app_mentions:read, channels:history, channels:read, chat:write,
files:write, im:history, im:read, im:write, users:read, users:read.email
```

---

### Agent O: Memory & Cache Agent

**Goal:** Conversation summaries + MCP Redis cache integrated into the Slack bot.

**Inputs:** Agent N (bot core), Agent H (Redis), Postgres (models)
**Produces:** Additions to `slack_bot_local.py`, `models/conversation_summary.py`

**Prompt:**
```
You are the Memory Agent. Add two memory layers to the Slack bot:

LAYER 1 — Redis MCP Cache (Phase A):
  Wrap every MCP tool call: check cache first, return cached result on HIT.
  Cache key: "mcp:{tool_name}:{md5(json.dumps(sorted_args))}"
  On HIT: tag LangSmith root run: metadata.context_cache_hit=true
  Use threading.local() to propagate cache hit flag from child thread to root span.
  Feature flag: USE_MCP_CACHE (default true)

LAYER 2 — Conversation Summaries (Phase B):
  After each DM exchange, run Haiku to write a 2-3 sentence summary.
  Store in conversation_summaries table (user_email, channel_id, summary, expires_at 90d).
  On next query from same user: fetch 3 most recent non-expired summaries.
  Inject as prior_context string into system message (~150 tokens vs ~2K raw history).
  Write-back must be non-blocking: threading.Thread(target=_write_summary, daemon=True).
  Feature flag: USE_CONV_SUMMARIES (default true)

History fetch for DMs: fetch_dm_history() using conversations_history() — NOT
conversations_replies() (DMs have no thread_ts).
```

---

### Agent P: Feedback Loop Agent

**Goal:** Human feedback buttons on every response; LangSmith write-back; correction modal.

**Inputs:** Agent N (bot core), `models/answer_feedback.py`, LangSmith client
**Produces:** Additions to `slack_bot_local.py`, migration `007_add_answer_feedback.sql`

**Prompt:**
```
You are the Feedback Loop Agent. Add human feedback capture to every bot response.

PHASE A — Buttons:
  Append a Slack actions block to every bot response: 👍 (POSITIVE) and 👎 (NEGATIVE).
  Encode context in button value (pipe-separated, max 2000 chars):
    "SIGNAL|run_id|user_email|query_preview|answer_preview|tool_called"
  On click: write to answer_feedback table + call LangSmith create_feedback()
    POSITIVE → score 1.0, NEGATIVE → score 0.0
  On NEGATIVE: bust Redis cache: r.delete(*r.keys("mcp:get_user_violations:*"))
  Replace buttons with confirmation text (prevent double-submit).
  Feature flag: USE_ANSWER_FEEDBACK (default true)

PHASE B — Correction Modal:
  On 👎 click: ALSO open Slack modal via client.views_open(trigger_id=...) — SYNCHRONOUSLY.
  trigger_id is valid for only 3 seconds — do not async before calling views_open().
  Encode channel_id + message_ts in modal private_metadata ("|".join([button_value, channel, ts])).
  Max private_metadata: 3000 chars. Current usage: ~360 chars.
  @app.view("feedback_correction_modal"): extract correction, call _save_feedback(correction=...).
  _save_feedback with correction: UPDATE existing row by run_id, write human_correction to LangSmith.

LangSmith run_id: capture from get_current_run_tree() at end of process_with_claude().
Store in threading.local() so the response handler can read it after the function returns.
```

---

## Phase 6 — Observability

### Agent Q: LangSmith Observability Agent

**Goal:** Full distributed tracing; 3 online evaluators; cost + token tracking.

**Inputs:** LangSmith API key, LangChain integration
**Produces:** Additions to `slack_bot_local.py`, `utils/langchain_callback.py`

**Prompt:**
```
You are the LangSmith Observability Agent. Wire full tracing into every LLM call.

Required env vars:
  LANGSMITH_API_KEY=lsv2_pt_...
  LANGCHAIN_TRACING_V2=true
  LANGCHAIN_PROJECT=compliance-agent

Trace structure per Slack query:
  slack_compliance_query (root, @traceable)
    └── LLM call 1 — haiku — tool dispatch
    └── tool: get_user_violations
    └── LLM call 2 — haiku — tool dispatch
    └── tool: analyze_access_request
    └── LLM call 3 — opus — synthesis

TokenTrackingCallback(BaseCallbackHandler):
  on_llm_end → extract usage_metadata → log to LangSmith and internal TokenTracker

3 Online Evaluators (register via LangSmith API):
  1. mcp_tool_called — score 0 if no MCP tool was called at all
  2. mcp_tool_coverage — score 0 if access-request query skipped analyze_access_request
  3. hallucination_heuristic — score 0 if response contains <tool_call> XML or
     fabricated numbers not grounded in tool result

Human feedback: use langsmith.Client().create_feedback(run_id, key="human_rating", score=N)
  LangSmith Feedback tab shows human + auto-eval scores side by side.
```

---

### Agent R: Admin Portal Agent

**Goal:** Angular 17 admin UI + JWT-secured FastAPI admin endpoints.

**Inputs:** MCP server (Agent L), JWT library
**Produces:** `mcp/admin_api.py`, `angular-portal/`

**Prompt:**
```
You are the Admin Portal Agent. Build a JWT-secured admin portal.

Backend (mcp/admin_api.py — FastAPI, mounted on the MCP server):
  POST /auth/login        → issue JWT (8h expiry)
  GET  /auth/me           → current user + authority level
  GET  /admin/system-health
  GET  /admin/config
  PATCH /admin/config/thresholds|notifications|feature-flags|llm
  GET/PATCH /admin/sod-rules
  GET/PATCH /admin/violations
  GET /admin/exceptions + /due-review
  GET /admin/audit-trail
  GET /admin/token-analytics

Authority levels (from NetSuite roles):
  L3 Director: read-only
  L4 Controller/VP: read + edit thresholds, rules, notifications
  L5 CFO: full access including feature flags, LLM config

Required env vars: JWT_SECRET, ADMIN_PORTAL_PASSWORD, JWT_EXPIRE_HOURS=8
New packages: python-jose[cryptography], passlib[bcrypt]

Frontend (angular-portal/):
  Angular 17, standalone components, Angular Material, signals
  JWT stored in-memory only (no localStorage — XSS risk)
  Auth guard + level guard for route protection
  Lazy-loaded routes: Dashboard, Violations, Exceptions, SOD Rules, Thresholds, Feature Flags
  Dev proxy: proxy.conf.json → /auth and /admin → localhost:8080
```

---

## Phase 7 — Analysis Jobs

### Agent S: Role Risk Matrix Agent

**Goal:** Precomputed SOD conflict matrix for all Fivetran custom roles.

**Inputs:** Postgres with violations + user data (Phase 3), sod_permission_map table
**Produces:** `scripts/build_role_risk_matrix.py`, populated `role_pair_conflicts` table

**Prompt:**
```
You are the Role Risk Matrix Agent. Build the precomputed role risk matrix.

Tables to populate:
  sod_permission_map (abstract_name, netsuite_name, level)
    Levels (ordered): None < View < Create < Edit < Full
  role_pair_conflicts (role_a, role_b, conflict_type, severity, rule_name, perm_a, level_a, perm_b, level_b)
    conflict_type: 'intra' (same role, conflicting perms) or 'cross' (two roles combined)

Expected output: ~443 conflict rows, 153 role pairs, 17 Fivetran roles

SQL migration runner — CRITICAL bug to avoid:
  When splitting on ';', do NOT discard an entire block just because it starts with '--'.
  Strip leading comment LINES from each block line-by-line before the startswith('--') check.
  Otherwise CREATE TABLE statements with header comments are silently dropped.

  WRONG:
    for stmt in sql.split(';'):
        if stmt.strip().startswith('--'): continue  # drops entire block!
  CORRECT:
    for raw_stmt in sql.split(';'):
        lines = [l for l in raw_stmt.splitlines() if l.strip() and not l.strip().startswith('--')]
        stmt = '\n'.join(lines).strip()
        if stmt: session.execute(text(stmt))

DB import pattern — ONLY this works:
  from models.database_config import DatabaseConfig
  session = DatabaseConfig().get_session()
  # NEVER: from database.db_setup import get_db_session  (module does not exist)

MCP tool: get_role_risk_matrix(role_name=None, severity=None, limit=50)
  Call with NO arguments for full overview. Cache TTL: 86400s (24h).
  Add to utils/tool_router.py 'role_risk' intent group — or Claude will never see it.
```

**Verification gate:**
```bash
psql $DATABASE_URL -c "SELECT COUNT(*) FROM role_pair_conflicts;"          # → 443
psql $DATABASE_URL -c "SELECT severity, COUNT(*) FROM role_pair_conflicts GROUP BY severity;"
curl -s -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_role_risk_matrix","arguments":{}}}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['result']['content'][0]['text'][:300])"
```

---

## Phase 8 — Quality Assurance

Phase 8 runs after every new feature phase (Phase 5, 6, or 7) completes.
Agents T and U run in parallel. Agent V runs after both finish.

The three-agent loop is reusable — invoke it after any non-trivial code change
by providing T and U with the specific files and scenarios relevant to the change.

---

### Agent T: Test Agent

**Goal:** Execute smoke tests, regression tests, and stress tests for new code.
Produce a structured PASS/FAIL report that V and U can act on.

**Inputs:** New or modified files from the completed phase; running services
**Produces:** Structured test report with per-test PASS/FAIL + exact error output

**When to invoke:** After every new feature (new migration, new service, new Slack bot handler).
Always run T and U in parallel — they are independent.

**Prompt template:**
```
You are the Test Agent. Run smoke, regression, and stress tests for [FEATURE NAME].

Working directory: /path/to/compliance-agent
Activate venv: source .venv/bin/activate

== SMOKE TESTS (happy path) ==
[List 4-6 happy-path scenarios with exact Python or bash commands]

== REGRESSION TESTS (guard against known past failures) ==
[List 2-4 tests that verify previously broken behaviour stays fixed]
  Known failure patterns to guard:
  - psycopg2 + pgvector: use CAST(:param AS vector), never :param::vector
  - SQLAlchemy ANY(:ids): use PostgreSQL array literal + ::uuid[] cast
  - NetSuite pagination: page_size must be 200, never 1000
  - Orphaned tool_result: _trim_history must advance to first HumanMessage
  - views_open() must be synchronous (trigger_id expires in 3s)

== STRESS TESTS (edge cases and high load) ==
[List 2-3 edge-case scenarios: empty inputs, None values, large inputs,
 concurrent calls, high-volume DB queries]

After all tests output this report format:
=== [FEATURE NAME] TEST RESULTS ===
TEST N (description): PASS/FAIL — one-line reason
...
TOTAL: X/Y PASS
FAILURES: detailed error output for each failure
ROOT CAUSE (if identifiable): precise file:line + description
```

**Regression test suite — always include these:**
```bash
# 1. Slack bot syntax check
python3 -c "import ast; ast.parse(open('slack_bot_local.py').read()); print('syntax OK')"

# 2. DB migration idempotency — reapply should not error
psql $DATABASE_URL -f database/migrations/<latest>.sql

# 3. Feature flag OFF — verify no crash when feature is disabled
USE_FEATURE_FLAG=false python3 -c "import slack_bot_local"

# 4. MCP server still responds after change
curl -s http://localhost:8080/health | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['status']=='ok', d"
```

**Stress test patterns:**
```python
# Empty / None inputs
service.method(run_id=None, query_preview="", correction="", tool_called=None)

# Very long inputs (truncation handling)
service.method(query_preview="x" * 10000, correction="y" * 10000)

# Concurrent calls (threading check)
import threading
threads = [threading.Thread(target=service.method, args=(...)) for _ in range(10)]
[t.start() for t in threads]; [t.join() for t in threads]

# High-similarity / low-similarity boundary (for vector search)
results_high = service.find(query_that_should_match)    # expect ≥1 result
results_low  = service.find("completely unrelated text") # expect 0 results
```

**Verification gate (Test Agent passes when):**
- All smoke tests PASS
- All regression guards PASS
- Stress tests produce no unhandled exceptions (warnings are acceptable)

---

### Agent U: QA Agent

**Goal:** Static code review — find bugs, edge cases, and integration issues
that tests might not catch. Focus on correctness, not style.

**Inputs:** New or modified source files from the completed phase
**Produces:** Structured QA report (CRITICAL / MEDIUM / LOW) with exact file:line + fix

**When to invoke:** In parallel with Agent T — independent of test execution.

**Prompt template:**
```
You are the QA Agent. Perform a thorough code review of [FEATURE NAME].

Read these files in full:
  [list all new/modified files]

For each file check:

CORRECTNESS
  □ Are all SQL parameters correctly bound? (named-style :param, no mixed styles)
  □ For pgvector: are all vector casts using CAST(:param AS vector), not :param::vector?
  □ For uuid arrays: is ANY(:ids) using a PostgreSQL array literal + ::uuid[] cast?
  □ Are session.close() calls in finally blocks to prevent connection leaks?
  □ Are all DB writes wrapped in try/except with session.rollback() on failure?
  □ Is every side-effect call (DB write, API call, cache bust) non-blocking?

EDGE CASES
  □ What happens with None / empty string inputs?
  □ What happens if the DB table is empty (zero-row query)?
  □ What happens if the feature flag is False?
  □ What happens on concurrent calls (thread safety)?
  □ What happens if a downstream service (Redis, LangSmith) is unavailable?

INTEGRATION
  □ Does the feature flag actually gate all code paths?
  □ Is the new code reachable from the Slack bot? (DM + mention paths)
  □ Is every new MCP tool registered in utils/tool_router.py?
  □ Do LangSmith tags fire correctly (check metadata keys)?

Produce this report:
=== [FEATURE NAME] QA REVIEW ===

CRITICAL BUGS (will cause errors or data loss):
  BUG-C1: file.py:line — description — fix

MEDIUM ISSUES (incorrect behavior, won't crash):
  BUG-M1: file.py:line — description — fix

LOW / SUGGESTIONS:
  BUG-L1: file.py:line — description — suggestion

OVERALL: SHIP / NEEDS FIXES
```

**Standard QA checklist items (always check):**

| Check | Common failure | Correct pattern |
|-------|---------------|-----------------|
| pgvector SQL cast | `:param::vector` (psycopg2 misparsed) | `CAST(:param AS vector)` |
| UUID array in SQL | `ANY(:ids)` with Python list | `ANY(:ids::uuid[])` + `{uuid1,uuid2}` literal |
| Session leak | Missing `finally: session.close()` | Always close in `finally` |
| Blocking side-effect | Direct DB write in Slack handler | `threading.Thread(daemon=True)` |
| Feature flag scope | Flag checked too late | Check at entry point, not deep in stack |
| Empty table query | Exception on `.fetchone()[0]` | `or 0` / `or []` default |
| Slack trigger_id | `views_open()` after `await` | Must be synchronous, within 3s |
| History trim | Slicing mid-tool-pair | Advance to next HumanMessage boundary |

---

### Agent V: Bug Fix Agent

**Goal:** Fix all CRITICAL and MEDIUM bugs identified by T (test failures) and
U (QA review). Verify each fix with a live test. Never fix more than was reported.

**Inputs:** Test report from Agent T + QA report from Agent U
**Produces:** Fixed source files + live test confirmation for each fix

**When to invoke:** After both T and U have completed. Pass both reports in the prompt.

**Prompt template:**
```
You are the Bug Fix Agent. Fix the bugs listed below.

== TEST FAILURES (from Test Agent) ==
[Paste full failure block from T's report]

== QA BUGS (from QA Agent — fix CRITICAL and MEDIUM only) ==
[Paste CRITICAL and MEDIUM sections from U's report]

Rules:
1. Fix only what is listed. Do not refactor, rename, or clean up anything else.
2. Read the file before editing — never edit blind.
3. For each fix, run a live test to confirm it resolves the failure.
4. If a fix introduces a new failure, revert and report it — do not compound.

After all fixes, output:
=== BUG FIX SUMMARY ===
BUG-C1 (description): FIXED / REVERTED — what changed + live test result
BUG-M1 (description): FIXED / REVERTED — what changed + live test result
...
Live test result: PASS/FAIL
```

**Known fix patterns (reference when applying):**

```python
# pgvector CAST — use SQL function form, not :: operator
# WRONG:  ":param::vector"
# RIGHT:  "CAST(:param AS vector)"

# UUID array in SQLAlchemy text()
# WRONG:  WHERE id = ANY(:ids)   with {"ids": python_list}
# RIGHT:  WHERE id = ANY(:ids::uuid[])  with {"ids": "{uuid1,uuid2}"}

# Session close
# WRONG:
session = get_session()
session.execute(...)
session.commit()
# RIGHT:
session = get_session()
try:
    session.execute(...)
    session.commit()
except Exception:
    session.rollback()
finally:
    session.close()

# Non-blocking side-effect
# WRONG:  _save_to_db(data)   # blocks Slack response
# RIGHT:  threading.Thread(target=_save_to_db, args=(data,), daemon=True).start()
```

**Verification gate (Bug Fix Agent passes when):**
- Every CRITICAL bug has a live test showing the previously-failing scenario now passes
- No new failures introduced
- Slack bot restarts cleanly after edits

---

### Phase 8 Orchestration Example

This is the exact pattern used to validate Feedback Phase C (2026-02-27):

```
Step 1: Launch T (Test Agent) and U (QA Agent) simultaneously
        — T runs 10 smoke/regression/stress tests
        — U does static review of correction_service.py + slack_bot_local.py changes

Step 2: T finds: TEST 3 / TEST 5 / TEST 7 FAIL
        Root cause: psycopg2 misparses :qvec::vector — treats :: as new named param

        U finds independently:
          BUG-C1: :param::vector in SELECT (lines 133/135/136) — misparsed by psycopg2
          BUG-C2: ANY(:ids) with Python UUID list — type inference fails → uuid[] cast needed

Step 3: Launch V (Bug Fix Agent) with both reports
        V reads correction_service.py, applies CAST(:qvec AS vector) to all 4 vector sites,
        applies ::uuid[] + array literal fix to the UPDATE statement.
        V runs live test: store_correction() → find_similar_corrections() → PASS

Step 4: Orchestrator re-runs critical tests from T's report to confirm resolution
        Results: 6/6 PASS (store, find-match, find-no-match, format, used_count, edge-case)
```

**When to skip Phase 8:**
- Trivial one-line changes (typo fix, comment update, log message)
- Changes that are already covered by an existing passing test suite
- Documentation-only changes

**When to always run Phase 8:**
- New SQL migrations
- New service modules (e.g., `services/correction_service.py`)
- New Slack bot handlers (action handlers, view handlers)
- Changes to `process_with_claude()` or `_save_feedback()`
- Any change touching pgvector queries

---

## Coordination Patterns

### Pattern 1: Shared Database Session
Every agent that touches Postgres must use:
```python
from models.database_config import DatabaseConfig
session = DatabaseConfig().get_session()
try:
    # work
    session.commit()
except Exception:
    session.rollback()
    raise
finally:
    session.close()
```
Never use `from database.db_setup import get_db_session` — that module does not exist.

### Pattern 2: Non-Blocking Side Effects
All write-backs (summaries, feedback, LangSmith tags) must be non-blocking:
```python
threading.Thread(target=_write_thing, args=(...), daemon=True).start()
```
Never block the Slack response path on a DB write or API call.

### Pattern 3: thread-local for Cross-Function State
When a value produced in a child function (e.g. run_id, cache_hit) is needed by
the parent Slack handler, use `threading.local()`:
```python
_tls = threading.local()
# In child: _tls.run_id = str(root_run.id)
# In parent: run_id = getattr(_tls, "run_id", None)
```
Do not use globals or return values for this — the call chain crosses thread boundaries.

### Pattern 4: Prompt Constraint Strength
| Soft (ignored)           | Hard (enforced)                  |
|--------------------------|----------------------------------|
| "aim for concise"        | "MAXIMUM 1,200 characters"       |
| "prefer this tool"       | "ALWAYS call X. NEVER call Y."   |
| "try to avoid SOD agent" | "NEVER use the phrase 'SOD agent'" |
| "should be under 1800"   | "HARD LIMIT: 1,800 chars"        |

### Pattern 5: Tool Router Registration
Every new MCP tool MUST be added to `utils/tool_router.py` intent groups.
If not registered, the tool is silently excluded from every Claude query.
Check: after adding a tool, verify it appears in select_tools_for_intent() output
for a representative query string.

### Pattern 6: Three-Agent QA Loop (Test → QA → Bug Fix)

Use this pattern after every non-trivial feature implementation. Launch T and U in
parallel, then V after both complete.

```
# Step 1: Launch T and U simultaneously (independent — no shared state)
task(agent=T, prompt="Run smoke/regression/stress tests for [feature]", background=True)
task(agent=U, prompt="Review [files] for bugs and edge cases", background=True)

# Step 2: Wait for both to complete
# Step 3: Launch V with both reports
task(agent=V, prompt=f"Fix these bugs:\n\nT report:\n{T_output}\n\nU report:\n{U_output}")

# Step 4: Orchestrator re-runs any previously-failing tests to confirm resolution
```

**Why parallel T + U?** They are completely independent — T exercises the running code
while U reads the source. Running them together halves wall-clock time and prevents
T's findings from anchoring U's review (independent analysis catches more bugs).

**Agent V constraint:** V must fix ONLY what T and U reported. It must not refactor,
clean up, or improve anything beyond the listed bugs — scope creep introduces new bugs.

**Key signals that Phase 8 is needed:**
- Any new `session.execute(sqla_text(...))` call with vector or UUID parameters
- Any new `threading.Thread(...)` side-effect
- Any new Slack modal or action handler
- Any new feature flag added to `.env`

---

## Verification Gates (Full System)

Run these after all phases complete:

```bash
# 1. MCP server health
curl -s http://localhost:8080/health | python3 -m json.tool

# 2. Tool count
curl -s -X POST http://localhost:8080/mcp \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  -H "Content-Type: application/json" \
  | python3 -c "import sys,json; print(len(json.load(sys.stdin)['result']['tools']),'tools')"
# → 37

# 3. User sync coverage
psql $DATABASE_URL -c "SELECT COUNT(*) FROM users WHERE is_active=true;"
# → ~1,928 (99.7% of 1,933 total NetSuite users)

# 4. SOD violations
psql $DATABASE_URL -c "SELECT severity, COUNT(*) FROM violations GROUP BY severity ORDER BY 1;"

# 5. Role risk matrix
psql $DATABASE_URL -c "SELECT COUNT(*) FROM role_pair_conflicts;"
# → 443

# 6. Redis cache
redis-cli PING
redis-cli KEYS "mcp:*" | wc -l    # → some entries after first queries

# 7. Slack bot
tail -5 /tmp/slack_bot.log
# → "Bolt app is running!"

# 8. LangSmith
# Open smith.langchain.com → project compliance-agent
# Send a Slack query → trace should appear within 30s

# 9. Feedback
psql $DATABASE_URL -c "SELECT COUNT(*) FROM answer_feedback;"
# → increments after clicking 👍/👎

# 10. Conversation summaries
psql $DATABASE_URL -c "SELECT COUNT(*) FROM conversation_summaries;"
# → increments after DM exchanges
```

---

## Critical Rules for All Agents

These are hard-won lessons. Violating any of them has caused data loss or silent failures:

| # | Rule | Impact if violated |
|---|------|--------------------|
| 1 | Never name a column `metadata` in SQLAlchemy | Reserved — breaks model init |
| 2 | NetSuite `page_size=200`, never 1000 | 79.2% data loss, no error thrown |
| 3 | Python enum values must match DB CHECK (UPPERCASE) | Insert fails silently or raises IntegrityError |
| 4 | Always create `ComplianceScan` before inserting `Violation` | FK violation crash |
| 5 | Import DB session from `models.database_config` | `database.db_setup` module does not exist |
| 6 | `_trim_history()` must advance to first HumanMessage | Orphaned tool_result → Anthropic API 400 |
| 7 | `views_open()` must be called synchronously on 👎 | `trigger_id` expires in 3 seconds |
| 8 | SQL migration runner: strip comment lines per-line, not per-block | Header-comment blocks silently dropped |
| 9 | Every new MCP tool must be registered in `tool_router.py` | Claude never sees the tool |
| 10 | `files_upload_v2()` requires `files:write` OAuth scope | Upload silently fails, fallback shown |
| 11 | Use `HARD LIMIT` / `MAXIMUM N chars` in prompts, not soft wording | Ignored by Claude |
| 12 | Never hardcode system names (NetSuite/Okta/Salesforce) in capabilities response | Call `list_systems` first |
| 13 | pgvector casts in SQLAlchemy `text()`: use `CAST(:param AS vector)` never `:param::vector` | psycopg2 misparses `::` after a named param as a second param — silent type error |
| 14 | UUID arrays in `text()`: pass `"{uuid1,uuid2}"` literal + `::uuid[]` cast, not Python list | psycopg2 cannot infer array element type from a Python list in a named parameter |

---

## Environment Variables Quick Reference

```bash
# Database
DATABASE_URL=postgresql://localhost/compliance_db

# LLM
ANTHROPIC_API_KEY=sk-ant-...

# Observability
LANGSMITH_API_KEY=lsv2_pt_...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=compliance-agent

# Slack
SLACK_BOT_TOKEN=xoxb-...       # Bot User OAuth Token (from api.slack.com)
SLACK_APP_TOKEN=xapp-...       # App-Level Token for Socket Mode

# Infrastructure
REDIS_URL=redis://localhost:6379/0

# NetSuite
NETSUITE_ACCOUNT_ID=...
NETSUITE_CONSUMER_KEY=...
NETSUITE_CONSUMER_SECRET=...
NETSUITE_TOKEN_ID=...
NETSUITE_TOKEN_SECRET=...
NETSUITE_RESTLET_URL=https://...

# Feature Flags (all default true)
USE_MCP_CACHE=true
USE_CONV_SUMMARIES=true
USE_ANSWER_FEEDBACK=true
USE_CORRECTION_CONTEXT=true   # Phase C — pgvector correction embeddings

# Phase C tuning
CORRECTION_MIN_SIMILARITY=0.70  # Cosine similarity threshold for correction retrieval
CORRECTION_TOP_K=3              # Max past corrections to inject per query

# Tuning
MAX_TOKENS_SLACK=1024
SLACK_MAX_RESPONSE_CHARS=2000
SLACK_TOOL_OUTPUT_MAX_CHARS=2000
SLACK_MAX_HISTORY_TURNS=4

# Admin Portal
JWT_SECRET=<64-char-random-string>
ADMIN_PORTAL_PASSWORD=<password>
JWT_EXPIRE_HOURS=8
```

---

## Starting Order (Copy-Paste)

```bash
# 1. Infrastructure
redis-server --daemonize yes
pg_ctl start   # or: brew services start postgresql

# 2. MCP Server
cd compliance-agent
.venv/bin/python -m mcp.mcp_server > /tmp/mcp_server.log 2>&1 &

# Verify
curl -s http://localhost:8080/health

# 3. Slack Bot
.venv/bin/python slack_bot_local.py > /tmp/slack_bot.log 2>&1 &

# 4. Angular Portal (optional)
cd angular-portal && ng serve
```

---

**Maintained by:** AI Development Team
**Original System Built:** February 2026
**This Playbook Version:** 1.0 (2026-02-27)
