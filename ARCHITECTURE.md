# 🏗️ SOD Compliance System - Complete Architecture Documentation V9

**Last Updated**: 2026-03-15
**Version**: 9.0
**Status**: Production-Ready with Semantic Tool Routing, Eval Suite + LangSmith Integration

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Layers](#architecture-layers)
3. [Multi-Turn Agentic Reasoning (NEW)](#multi-turn-agentic-reasoning-new)
4. [Component Details](#component-details)
5. [Vector Knowledge Base](#vector-knowledge-base)
6. [RAG Pattern Implementation](#rag-pattern-implementation)
7. [Data Flow](#data-flow)
8. [MCP Tools (35 Tools)](#mcp-tools-35-tools)
9. [Database Schema](#database-schema)
10. [LLM Integration](#llm-integration)
11. [Level-Based Conflict Detection](#level-based-conflict-detection)
12. [Deployment Architecture](#deployment-architecture)
13. [Security & Authentication](#security--authentication)
14. [Semantic Tool Router (NEW)](#semantic-tool-router-new)
15. [Eval Suite (NEW)](#eval-suite-new)

---

## System Overview

The SOD (Segregation of Duties) Compliance System is an AI-powered compliance platform that:
- **Detects** SOD violations across enterprise systems (NetSuite, Okta)
- **Analyzes** access requests using level-based conflict detection
- **Grounds** all recommendations in vector-embedded compliance knowledge
- **Provides** compensating control recommendations
- **Integrates** with Claude Desktop via MCP (Model Context Protocol)

### Key Capabilities

✅ **Vector-Grounded Analysis**: All SOD recommendations validated against pgvector knowledge base
✅ **Level-Based Detection**: Granular conflict detection (View/Create/Edit/Full levels)
✅ **RAG Pattern**: Retrieval Augmented Generation for compliance recommendations
✅ **35 MCP Tools**: Full integration with Claude Desktop UI
✅ **Autonomous Data Collection**: Scheduled syncs from NetSuite/Okta
✅ **LLM Abstraction**: Support for Claude, OpenAI, Gemini, Cohere
✅ **Multi-Turn Agentic Reasoning**: Slack bot with 5-turn conversation loop (NEW Feb 2026)
✅ **Token Optimization**: Prefix caching, intent-based tool routing (35→3-8 tools), output sanitization
✅ **Security Hardened**: Parameterized SQL, env-only secrets, CORS allowlist, required API key validation
✅ **Slack Block Kit UI**: Animated thinking indicator, mrkdwn formatting, section dividers
✅ **Semantic Tool Router**: Embedding-based tool selection replaces regex routing (Hit Rate@10: 0.72→1.00, MRR: 0.18→0.91)
✅ **Eval Suite**: LangSmith-integrated evaluation with Hit Rate@K, MRR, NDCG@K, Precision@K, Faithfulness metrics

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE LAYER                                 │
│  ┌───────────────────┐  ┌──────────────────┐  ┌────────────────────────┐  │
│  │  Claude Desktop   │  │  Claude Web API  │  │   FastAPI Dashboard    │  │
│  │  (MCP stdio)      │  │  (Direct calls)  │  │   (Browser UI)         │  │
│  │  • Natural lang   │  │  • REST API      │  │   • Admin interface    │  │
│  │  • 35 MCP tools   │  │  • JSON-RPC 2.0  │  │   • Visualization      │  │
│  └─────────┬─────────┘  └────────┬─────────┘  └──────────┬─────────────┘  │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Slack Bot (NEW Feb 2026) 🆕                                        │   │
│  │  (Socket Mode + Multi-Turn Agentic Reasoning)                       │   │
│  │  • @mention detection → email resolution                            │   │
│  │  • 5-turn conversation loop for multi-step reasoning                │   │
│  │  • Block Kit responses with animated thinking indicator             │   │
│  │  • Semantic tool routing (35 tools → 3-8 per request)              │   │
│  │  •   Primary: SemanticToolRouter (sentence-transformers/all-MiniLM-L6-v2)│   │
│  │  •   Fallback: keyword/regex router (utils/tool_router.py)         │   │
│  │  • Prefix-cached system prompt (90% cache hit discount)            │   │
│  │  • Tool output sanitization (TOOL_OUTPUT_MAX_CHARS cap)            │   │
│  │  • Token tracking via AnthropicClientWrapper                       │   │
│  │  • File: compliance-agent/slack_bot_local.py                       │   │
│  └──────────────────────────────────┬──────────────────────────────────┘   │
└────────────┼─────────────────────────┼────────────────────────┼────────────┘
             │                     │                        │
             └─────────────────────┼────────────────────────┘
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MCP (MODEL CONTEXT PROTOCOL) LAYER                       │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  MCP Server (mcp_server.py) - Port 8080                             │  │
│  │  • JSON-RPC 2.0 Protocol                                            │  │
│  │  • API Key Authentication (X-API-Key header)                        │  │
│  │  • Tool Registration & Discovery                                    │  │
│  │  • Async Tool Execution                                             │  │
│  │  • Health Monitoring (/health endpoint)                             │  │
│  │                                                                      │  │
│  │  ┌──────────────────────────────────────────────────────────────┐  │  │
│  │  │  20 MCP TOOLS                                                 │  │  │
│  │  │  ┌─────────────────┐  ┌──────────────────────────────────┐  │  │  │
│  │  │  │ System Mgmt (5) │  │ SOD Analysis (8) 🆕             │  │  │  │
│  │  │  ├─────────────────┤  ├──────────────────────────────────┤  │  │  │
│  │  │  │• list_systems   │  │• analyze_access_request          │  │  │  │
│  │  │  │• get_violations │  │• query_sod_rules                 │  │  │  │
│  │  │  │• remediate      │  │• get_compensating_controls       │  │  │  │
│  │  │  │• schedule       │  │• validate_job_role               │  │  │  │
│  │  │  │• get_stats      │  │• check_permission_conflict       │  │  │  │
│  │  │  └─────────────────┘  │• get_permission_categories       │  │  │  │
│  │  │                       │• search_permissions              │  │  │  │
│  │  │                       │• analyze_role_permissions 🔥     │  │  │  │
│  │  │  ┌─────────────────┐  └──────────────────────────────────┘  │  │  │
│  │  │  │ Data Sync (5)   │  ┌──────────────────────────────────┐  │  │  │
│  │  │  ├─────────────────┤  │ Knowledge Base (2) 🆕           │  │  │  │
│  │  │  │• start_agent    │  ├──────────────────────────────────┤  │  │  │
│  │  │  │• stop_agent     │  │• query_knowledge_base            │  │  │  │
│  │  │  │• get_status     │  │  (Vector semantic search)        │  │  │  │
│  │  │  │• trigger_sync   │  │• list_all_users                  │  │  │  │
│  │  │  │• list_users     │  └──────────────────────────────────┘  │  │  │
│  │  │  └─────────────────┘                                        │  │  │
│  │  └──────────────────────────────────────────────────────────────┘  │  │
│  └─────────────────────────────────┬────────────────────────────────────┘  │
└────────────────────────────────────┼───────────────────────────────────────┘
                                     ▼

---

## Multi-Turn Agentic Reasoning (NEW)

**Added:** February 2026
**Component:** Slack Bot (`slack_bot_local.py`)
**Impact:** 0% → 100% accuracy on role assignment requests

### Overview

The Slack bot now implements **multi-turn agentic tool use**, enabling Claude can:
1. Making initial tool calls to gather context
2. Analyzing the results
3. Making follow-up tool calls based on that analysis
4. Providing comprehensive recommendations

### Technical Implementation

```python
# Multi-turn conversation loop (up to 5 turns)
messages = [{"role": "user", "content": user_message}]

for turn in range(max_turns):
    # Call Claude with tools
    response = claude.messages.create(
        messages=messages,
        tools=MCP_TOOLS  # All 35 tools available
    )

    # Execute tool calls
    tool_results = []
    for tool_use in response.content:
        if tool_use.type == "tool_use":
            result = call_mcp_tool(tool_use.name, tool_use.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result
            })

    # Continue conversation with results
    messages.append({"role": "assistant", "content": response.content})
    messages.append({"role": "user", "content": tool_results})
```

### Before vs After

**Before (Single-Turn):**
```
User: "Can we assign Austin the Controller role?"
Bot:
  → get_user_violations("austin@company.com")
  → Sees: 0 current violations
  → Stops
  → Reports: "0 conflicts" ❌ WRONG
```

**After (Multi-Turn):**
```
User: "Can we assign Austin the Controller role?"
Bot:
  Turn 1:
    → get_user_violations("austin@company.com")
    → Result: [Billing Manager, Revenue Manager]

  Turn 2:
    → analyze_access_request([Billing Manager,
                              Revenue Manager,
                              Controller])
    → Result: 249 conflicts, HIGH risk

  → Reports: "249 conflicts, DO NOT ASSIGN" ✅ CORRECT
```

### Key Features

1. **Automatic User Resolution**
   - Extracts Slack @mentions (e.g., `@austin.rangel`)
   - Resolves to email via Slack API
   - Passes to MCP tools automatically

2. **Context Accumulation**
   - Each turn builds on previous results
   - Claude maintains conversation state
   - Can make 3-5 tool calls in sequence

3. **Complete Role Analysis**
   - Always analyzes FULL role combination
   - Not just new role in isolation
   - Detects cross-role SOD violations

4. **Proactive Tool Selection**
   - Claude chooses appropriate tools
   - No manual routing required
   - Intelligent follow-up based on results

### Architecture Flow

```
User Request (Slack)
    ↓
Extract @mentions → Resolve to emails
    ↓
┌─────────────────────────────────┐
│  Multi-Turn Loop (max 5 turns)  │
│                                  │
│  Turn 1: Gather Context          │
│  → get_user_violations          │
│  → Returns: current roles       │
│                                  │
│  Turn 2: Deep Analysis          │
│  → analyze_access_request       │
│  → Input: ALL roles (curr+new)  │
│  → Returns: conflicts + risk    │
│                                  │
│  Turn 3+: Optional              │
│  → query_knowledge_base         │
│  → get_compensating_controls    │
└─────────────────────────────────┘
    ↓
Comprehensive Response to User
```

### Impact Metrics

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Accuracy** | 0% | 100% | ∞ |
| **Conflicts Detected** | 0 | 249 | N/A |
| **Risk Assessment** | LOW (wrong) | HIGH (correct) | Critical |
| **False Negatives** | 100% | 0% | -100% |

### Example Use Cases

1. **Role Assignment Requests**
   - "Can we assign @user the Controller role?"
   - Bot checks current roles + analyzes combination

2. **Access Reviews**
   - "What are @user's violations?"
   - Bot gets violations + analyzes severity + suggests remediation

3. **Exception Requests**
   - "Can we approve this SOD exception for @user?"
   - Bot checks authority + validates justification + retrieves precedents

### Configuration

```python
# slack_bot_local.py configuration
MAX_TURNS = 5  # Maximum conversation turns
MODEL = "claude-opus-4-6"  # Most capable for multi-step reasoning
MCP_SERVER_URL = "http://localhost:8080"
```

### See Also

- **Implementation:** `compliance-agent/slack_bot_local.py` (lines 242-315)
- **Documentation:** `docs/SLACK_INTEGRATION.md`
- **LinkedIn Post:** `LINKEDIN_POST_MULTI_TURN_REASONING.md`

---

## Token Optimization Architecture

**Added:** February 2026
**Impact:** ~70-85% reduction in token cost per Slack request

### Strategy Overview

| Technique | Where Applied | Savings |
|-----------|--------------|---------|
| **Prefix Caching** | Slack bot, Analyzer, Risk Assessor | 90% cost on cached system prompt re-reads |
| **Semantic Tool Routing** | `utils/semantic_router.py` → Slack bot (primary) | 35 tools (~10K tokens) → 3-8 tools (~1.5K tokens) per request; Hit Rate@10=1.00 |
| **Keyword Tool Routing (fallback)** | `utils/tool_router.py` → Slack bot | Falls back if sentence-transformers unavailable |
| **Output Sanitization** | `call_mcp_tool()` in Slack bot | Caps tool output at `TOOL_OUTPUT_MAX_CHARS` (default 2000 chars) |
| **History Trimming** | Slack bot multi-turn loop | Keeps last `MAX_HISTORY_TURNS` (default 4) turn-pairs |
| **Output Length Control** | All agents | `max_tokens=1024` (Slack), `2048` (Analyzer/Report), `1024` (Risk) |
| **Model Right-Sizing** | Report Generator | Sonnet (not Opus) for structured report generation |
| **Token Tracking** | All agents + Slack bot | `TokenTracker` + `AnthropicClientWrapper` + LangChain callback |

### Key Files

| File | Purpose |
|------|---------|
| `utils/semantic_router.py` | Semantic tool routing — primary router (embedding-based, `SemanticToolRouter` + `semantic_select_tools()`) |
| `utils/tool_router.py` | Keyword/regex tool routing — fallback router (INTENT_PATTERNS + TOOL_GROUPS) |
| `utils/token_tracker.py` | Global token usage tracker with per-agent stats |
| `utils/anthropic_wrapper.py` | Auto-tracking Anthropic SDK wrapper |
| `utils/langchain_callback.py` | LangChain `on_llm_end` → TokenTracker bridge |
| `config/model_config.py` | `STEP_MODEL_MAP` — model routing per pipeline step |

### Tool Routing Groups

```python
TOOL_GROUPS = {
    "access_review":    ["get_user_violations", "analyze_access_request", "validate_job_role"],
    "violation_query":  ["get_violation_stats", "list_violations", "get_violation_details"],
    "exception_mgmt":   ["request_exception_approval", "check_my_approval_authority"],
    "knowledge_base":   ["query_knowledge_base", "search_knowledge_base"],
    "role_analysis":    ["analyze_role_permissions", "check_permission_conflict"],
    "reporting":        ["generate_compliance_report", "get_department_stats"],
    "data_sync":        ["trigger_manual_sync", "get_sync_status"],
    "user_mgmt":        ["list_all_users", "get_user_profile", "search_users"],
    "system_info":      ["list_systems", "get_system_health"],
}
```

---

## Security Architecture (Updated Feb 2026)

### Hardening Applied

| Issue | Before | After |
|-------|--------|-------|
| **API Key** | Default `dev-key-12345` if env var unset | `ValueError` raised if `MCP_API_KEY` not set |
| **CORS** | `allow_origins=["*"]` | `MCP_ALLOWED_ORIGINS` env var, defaults to `localhost` only |
| **SQL Injection** | `LIMIT {limit}` f-string interpolated | `LIMIT %s` parameterized with `params` tuple |
| **DB Credentials** | Hardcoded in 3 tool handlers | `os.getenv('DATABASE_URL')` everywhere |
| **DB Connections** | No cleanup on exception | All `psycopg2.connect()` wrapped in `try/finally conn.close()` |
| **Redis URL** | `redis://localhost:6379/0` hardcoded | `REDIS_URL` env var, cache auto-disabled if unset |

### Required Environment Variables (Updated)

```bash
# MCP Server (NEW — required, no default)
MCP_API_KEY=<your-api-key>
MCP_ALLOWED_ORIGINS=http://localhost,http://localhost:3000  # optional, defaults to localhost

# Database (required)
DATABASE_URL=postgresql://user:pass@host:5432/compliance_db

# Redis (optional — cache disabled if not set)
REDIS_URL=redis://localhost:6379/0

# LLM
ANTHROPIC_API_KEY=sk-ant-...

# Risk Assessment (optional — defaults to all users)
RISK_ASSESSMENT_BATCH_SIZE=100
```

---

┌─────────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATION LAYER                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  ComplianceOrchestrator (Singleton with @lru_cache)                  │  │
│  │  ┌────────────────────────────────────────────────────────────────┐  │  │
│  │  │  Responsibilities:                                             │  │  │
│  │  │  • Initialize all agents and connectors                        │  │  │
│  │  │  • Route MCP tool calls to appropriate handlers                │  │  │
│  │  │  • Coordinate multi-agent workflows                            │  │  │
│  │  │  • Implement caching (@timed_cache, TTL=300s)                  │  │  │
│  │  │  • Aggregate results from multiple sources                     │  │  │
│  │  │  • Error handling and retry logic                              │  │  │
│  │  └────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                      │  │
│  │  Initialized Components:                                             │  │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │  │
│  │  │ SODAnalysisAgent │  │DataCollectionAgnt│  │ KnowledgeBaseAgt│  │  │
│  │  └──────────────────┘  └──────────────────┘  └─────────────────┘  │  │
│  └─────────────┬────────────────────────────────────────────────────────┘  │
└────────────────┼───────────────────────────────────────────────────────────┘
                 │
      ┌──────────┴──────────┬──────────────────┬──────────────────┐
      ▼                     ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            AGENT LAYER                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  1. SOD ANALYSIS AGENT (agents/analyzer.py)                          │ │
│  │  ┌────────────────────────────────────────────────────────────────┐  │ │
│  │  │  • Load SOD rules from database (24 rules)                     │  │ │
│  │  │  • Build rule ID mappings                                      │  │ │
│  │  │  • Perform level-based conflict detection (5×5 matrices)      │  │ │
│  │  │  • Calculate inherent risk scores                             │  │ │
│  │  │  • Generate violation records                                  │  │ │
│  │  │  • Integrate with LLM for natural language analysis           │  │ │
│  │  └────────────────────────────────────────────────────────────────┘  │ │
│  │  Model: claude-opus-4.6 (configurable)                              │ │
│  │  Database: Reads from sod_rules, writes to violations               │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  2. DATA COLLECTION AGENT (agents/data_collector.py)                 │ │
│  │  ┌────────────────────────────────────────────────────────────────┐  │ │
│  │  │  • Autonomous scheduler with APScheduler                       │  │ │
│  │  │  • Full Sync: Daily at 2:00 AM (cron: 0 2 * * *)             │  │ │
│  │  │  • Incremental Sync: Hourly (cron: 0 * * * *)                 │  │ │
│  │  │  • Multi-connector support (NetSuite, Okta)                    │  │ │
│  │  │  • Error handling with exponential backoff                     │  │ │
│  │  │  • Sync history tracking                                       │  │ │
│  │  └────────────────────────────────────────────────────────────────┘  │ │
│  │  Status: Running in background                                        │ │
│  │  Logs: agents/data_collector logs                                     │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  3. KNOWLEDGE BASE AGENT (agents/knowledge_base_pgvector.py) 🆕      │ │
│  │  ┌────────────────────────────────────────────────────────────────┐  │ │
│  │  │  • Vector embeddings with sentence-transformers              │  │ │
│  │  │  • Model: all-MiniLM-L6-v2 (384 dimensions)                   │  │ │
│  │  │  • Semantic search with cosine similarity                     │  │ │
│  │  │  • Document types: SOD_RULE, COMPENSATING_CONTROL,            │  │ │
│  │  │                    RESOLUTION_STRATEGY, JOB_ROLE              │  │ │
│  │  │  • Methods:                                                    │  │ │
│  │  │    - search_similar_rules(query, top_k)                       │  │ │
│  │  │    - get_relevant_controls(conflict_type)                     │  │ │
│  │  │    - query_knowledge_base(query, doc_type, limit)             │  │ │
│  │  └────────────────────────────────────────────────────────────────┘  │ │
│  │  Storage: PostgreSQL with pgvector extension                          │ │
│  │  Documents: 49 embedded documents in knowledge_base_documents table   │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  4. NOTIFICATION AGENT (agents/notifications.py)                     │ │
│  │  ┌────────────────────────────────────────────────────────────────┐  │ │
│  │  │  • Generate compliance notifications                           │  │ │
│  │  │  • Email alerts for critical violations                        │  │ │
│  │  │  • Slack webhook alerts via _send_alert() (active)             │  │ │
│  │  │  • Notification templates with AI-generated content           │  │ │
│  │  └────────────────────────────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CONNECTOR LAYER                                    │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  BASE CONNECTOR (connectors/base_connector.py)                       │ │
│  │  • Abstract base class for all connectors                            │ │
│  │  • Common interface: fetch_users(), fetch_roles(), sync()            │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌────────────────────────────┐      ┌─────────────────────────────────┐  │
│  │  NetSuiteConnector         │      │  OktaConnector                  │  │
│  ├────────────────────────────┤      ├─────────────────────────────────┤  │
│  │ Client: NetSuiteClient     │      │ Client: OktaClient              │  │
│  │ • fetch_users()            │      │ • fetch_users()                 │  │
│  │ • fetch_roles()            │      │ • fetch_groups()                │  │
│  │ • fetch_permissions()      │      │ • fetch_applications()          │  │
│  │ • search_user(email)       │      │ • search_user(email)            │  │
│  │ • sync_to_database()       │      │ • sync_to_database()            │  │
│  │                            │      │                                 │  │
│  │ Auth: OAuth 1.0a (TBA)     │      │ Auth: OAuth 2.0 / API Token     │  │
│  │ Endpoint: RESTlet URL      │      │ Endpoint: okta.com/api/v1       │  │
│  └────────────┬───────────────┘      └─────────────┬───────────────────┘  │
└────────────────┼──────────────────────────────────┼────────────────────────┘
                 │                                  │
                 ▼                                  ▼
     ┌───────────────────────┐          ┌───────────────────────┐
     │ NetSuite System       │          │ Okta System           │
     │ • RESTlet API         │          │ • REST API v1         │
     │ • OAuth 1.0a (TBA)    │          │ • OAuth 2.0           │
     │ • User data           │          │ • User/group data     │
     │ • Role assignments    │          │ • App assignments     │
     │ • 341 permissions     │          │ • MFA status          │
     └───────────────────────┘          └───────────────────────┘
                 │                                  │
                 └──────────────┬───────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         REPOSITORY LAYER                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  All repositories use SQLAlchemy ORM with async support              │  │
│  │  • Type hints for all methods                                        │  │
│  │  • Transaction management                                            │  │
│  │  • Error handling with custom exceptions                             │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────┐  ┌───────────────────┐  ┌─────────────────────────┐ │
│  │ UserRepository   │  │ RoleRepository    │  │ ViolationRepository     │ │
│  ├──────────────────┤  ├───────────────────┤  ├─────────────────────────┤ │
│  │• get_by_id       │  │• get_by_id        │  │• create_violation       │ │
│  │• get_by_email    │  │• get_by_name      │  │• get_by_user            │ │
│  │• create          │  │• upsert           │  │• get_by_severity        │ │
│  │• update          │  │• list_all         │  │• update_status          │ │
│  │• delete          │  │• assign_to_user   │  │• list_active            │ │
│  │• list_all        │  │• get_permissions  │  │• bulk_create            │ │
│  │• search          │  └───────────────────┘  └─────────────────────────┘ │
│  └──────────────────┘                                                       │
│                                                                             │
│  ┌────────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │ SODRuleRepository  │  │ ExemptionRepo    │  │ ScanRepository       │  │
│  ├────────────────────┤  ├──────────────────┤  ├──────────────────────┤  │
│  │• get_all_active    │  │• create          │  │• create_scan         │  │
│  │• get_by_category   │  │• get_by_user     │  │• update_scan_status  │  │
│  │• get_by_severity   │  │• approve         │  │• get_recent_scans    │  │
│  │• create            │  │• reject          │  │• get_scan_summary    │  │
│  │• update            │  │• expire          │  └──────────────────────┘  │
│  └────────────────────┘  └──────────────────┘                             │
│                                                                             │
│  ┌──────────────────────────┐  ┌─────────────────────────────────────┐    │
│  │ ControlPackageRepository │  │ JobRoleMappingRepository            │    │
│  ├──────────────────────────┤  ├─────────────────────────────────────┤    │
│  │• get_by_severity 🆕      │  │• get_by_job_title 🆕                │    │
│  │• get_all_packages        │  │• validate_role_combination          │    │
│  │• create                  │  │• get_typical_roles                  │    │
│  └──────────────────────────┘  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     DATABASE LAYER (PostgreSQL 14+)                         │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Database: compliance_db                                             │  │
│  │  User: compliance_user                                               │  │
│  │  Host: localhost:5432                                                │  │
│  │  Extensions: pgvector, uuid-ossp                                     │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  CORE TABLES (9 tables)                                            │    │
│  ├────────────────────────────────────────────────────────────────────┤    │
│  │  ┌──────────┐  ┌──────────┐  ┌────────────┐  ┌────────────┐      │    │
│  │  │  users   │  │  roles   │  │ user_roles │  │ sod_rules  │      │    │
│  │  │  (PK:id) │  │  (PK:id) │  │ (user_id,  │  │ (PK:id)    │      │    │
│  │  │  email   │  │  name    │  │  role_id)  │  │ rule_id UK │      │    │
│  │  │  status  │  │  system  │  └────────────┘  │ severity   │      │    │
│  │  └──────────┘  └──────────┘                  │ is_active  │      │    │
│  │                                               │ metadata   │      │    │
│  │  ┌────────────┐  ┌────────────────┐          └────────────┘      │    │
│  │  │violations  │  │compliance_scans│                              │    │
│  │  │ (PK:id)    │  │ (PK:id)        │   ┌──────────────┐          │    │
│  │  │ user_id FK │  │ scan_type      │   │ exemptions   │          │    │
│  │  │ rule_id FK │  │ status         │   │ (PK:id)      │          │    │
│  │  │ severity   │  │ findings       │   │ violation_id │          │    │
│  │  │ status     │  │ start/end_time │   │ approved_by  │          │    │
│  │  └────────────┘  └────────────────┘   │ expires_at   │          │    │
│  │                                        └──────────────┘          │    │
│  │  ┌────────────────┐  ┌──────────────┐                           │    │
│  │  │ agent_logs     │  │notifications │                           │    │
│  │  │ (PK:id)        │  │ (PK:id)      │                           │    │
│  │  │ agent_name     │  │ user_id FK   │                           │    │
│  │  │ operation      │  │ type         │                           │    │
│  │  │ status         │  │ sent_at      │                           │    │
│  │  │ timestamp      │  └──────────────┘                           │    │
│  │  └────────────────┘                                              │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  SOD CONFIGURATION TABLES (7 tables) 🆕                            │    │
│  ├────────────────────────────────────────────────────────────────────┤    │
│  │  ┌──────────────────────┐  ┌──────────────────────────────┐      │    │
│  │  │ compensating_controls│  │ control_packages             │      │    │
│  │  │ (PK:id)              │  │ (PK:id)                      │      │    │
│  │  │ control_id UK        │  │ package_id UK                │      │    │
│  │  │ name                 │  │ package_name                 │      │    │
│  │  │ control_type         │  │ severity_level               │      │    │
│  │  │ risk_reduction_%     │  │ included_control_ids[]       │      │    │
│  │  │ annual_cost          │  │ total_risk_reduction         │      │    │
│  │  │ implementation_hrs   │  │ estimated_annual_cost        │      │    │
│  │  └──────────────────────┘  │ implementation_time_hours    │      │    │
│  │                             └──────────────────────────────┘      │    │
│  │  ┌──────────────────────┐  ┌──────────────────────────────┐      │    │
│  │  │ job_role_mappings    │  │ permission_categories        │      │    │
│  │  │ (PK:id)              │  │ (PK:id)                      │      │    │
│  │  │ job_role_id UK       │  │ category_id UK               │      │    │
│  │  │ job_title            │  │ category_name                │      │    │
│  │  │ department           │  │ base_risk_score              │      │    │
│  │  │ acceptable_combos[]  │  │ description                  │      │    │
│  │  │ business_justify     │  │ permissions[]                │      │    │
│  │  └──────────────────────┘  └──────────────────────────────┘      │    │
│  │                                                                    │    │
│  │  ┌──────────────────────┐  ┌──────────────────────────────┐      │    │
│  │  │ permission_levels    │  │ knowledge_base_documents 🆕  │      │    │
│  │  │ (PK:id)              │  │ (PK:id)                      │      │    │
│  │  │ permission_id        │  │ doc_id UK                    │      │    │
│  │  │ permission_name      │  │ doc_type (SOD_RULE, etc)     │      │    │
│  │  │ level_value (0-4)    │  │ content TEXT                 │      │    │
│  │  │ level_name           │  │ embedding vector(384) 🔍     │      │    │
│  │  │ category             │  │ metadata JSONB               │      │    │
│  │  └──────────────────────┘  │ created_at, updated_at       │      │    │
│  │                             └──────────────────────────────┘      │    │
│  │                             Index: ivfflat on embedding            │    │
│  │                             Operator: <=> (cosine distance)        │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  Total Tables: 16                                                           │
│  Total Records: ~50K+ (users, roles, permissions)                           │
│  Vector Dimensions: 384 (sentence-transformers/all-MiniLM-L6-v2)            │
│  Knowledge Base Documents: 49                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. MCP Server (`mcp/mcp_server.py`)

**Purpose**: Exposes compliance tools via Model Context Protocol

**Key Features**:
- **Protocol**: JSON-RPC 2.0 over HTTP
- **Port**: 8080 (configurable via MCP_SERVER_PORT)
- **Authentication**: API Key in X-API-Key header
- **Transport**: HTTP (for Claude Desktop) and stdio (for CLI)
- **Health Endpoint**: `/health` - Returns server status
- **Tools Endpoint**: `/tools` - Lists all 19 available tools
- **MCP Endpoint**: `/mcp` - Handles tool execution

**Startup Sequence**:
```python
1. Load environment variables
2. Initialize database connection
3. Create ComplianceOrchestrator (singleton)
4. Start DataCollectionAgent (autonomous scheduler)
5. Initialize KnowledgeBaseAgent with pgvector
6. Register all 19 MCP tools
7. Start FastAPI server on 0.0.0.0:8080
8. Log available tools and configuration
```

**Tool Registration**:
```python
TOOL_SCHEMAS = {
    "tool_name": {
        "description": "...",
        "inputSchema": {
            "type": "object",
            "properties": {...},
            "required": [...]
        }
    }
}

TOOL_HANDLERS = {
    "tool_name": handler_function
}
```

### 2. ComplianceOrchestrator (`mcp/orchestrator.py`)

**Purpose**: Central coordinator for all agents and connectors

**Initialization**:
```python
@lru_cache(maxsize=1)
def get_orchestrator():
    return ComplianceOrchestrator()
```

**Key Methods**:
- `list_available_systems_sync()` - Get all connected systems
- `perform_user_access_review()` - Analyze user access
- `get_user_violations()` - Retrieve violations for user
- `remediate_violation()` - Create exemption or revoke access
- `schedule_review()` - Schedule compliance scan

**Caching Strategy**:
```python
@timed_cache(seconds=300)  # 5-minute cache
def expensive_operation():
    ...
```

### 3. SOD Analysis Agent (`agents/analyzer.py`)

**Purpose**: Core SOD violation detection engine

**Initialization Flow**:
```python
1. Load SOD rules from database (24 active rules)
2. Parse level_conflict_matrix (5×5 JSONB matrices)
3. Build rule_id to database_id mappings
4. Initialize LLM provider (Claude Opus 4.6)
5. Load permission categorization
6. Ready to analyze access requests
```

**Analysis Process**:
```python
def analyze_user_access(user_id, user_roles):
    1. Get all permissions for user's roles
    2. Group permissions by user
    3. For each permission pair:
       a. Check if categories match SOD rule
       b. Get permission levels (0-4)
       c. Look up severity in conflict matrix
       d. Calculate inherent risk score
    4. Generate violations if conflicts found
    5. Return analysis with recommendations
```

**Level-Based Conflict Detection**:
```python
# Permission Levels
NONE = 0
VIEW = 1
CREATE = 2
EDIT = 3
FULL = 4

# 5×5 Conflict Matrix (example for SOD-RULE-001)
[
  ['OK',   'OK',   'OK',   'OK',   'OK'  ],  # None × All
  ['OK',   'OK',   'LOW',  'LOW',  'MED' ],  # View × All
  ['OK',   'LOW',  'MED',  'HIGH', 'CRIT'],  # Create × All
  ['OK',   'LOW',  'HIGH', 'CRIT', 'CRIT'],  # Edit × All
  ['OK',   'MED',  'CRIT', 'CRIT', 'CRIT']   # Full × All
]
```

**Risk Calculation**:
```python
inherent_risk = base_risk_score * (
    (level1_value + level2_value) / 8.0
)

# With compensating controls:
residual_risk = inherent_risk * (1 - risk_reduction_percentage)
```

### 4. Data Collection Agent (`agents/data_collector.py`)

**Purpose**: Autonomous data synchronization from source systems

**Scheduler Configuration**:
```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

# Full sync: Daily at 2 AM
scheduler.add_job(
    func=self.full_sync,
    trigger='cron',
    hour=2,
    minute=0,
    id='full_sync',
    name='Full Sync (Daily 2 AM)'
)

# Incremental sync: Every hour
scheduler.add_job(
    func=self.incremental_sync,
    trigger='cron',
    minute=0,
    id='incremental_sync',
    name='Incremental Sync (Hourly)'
)

scheduler.start()
```

**Sync Process**:
```python
def full_sync():
    1. For each connector (NetSuite, Okta):
       a. Fetch all users (paginated)
       b. Fetch all roles
       c. Fetch all user-role assignments
       d. Upsert to database
    2. Log sync statistics
    3. Trigger SOD analysis for changed users
    4. Send notifications if violations found
```

**Error Handling**:
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def fetch_with_retry():
    ...
```

### 5. Knowledge Base Agent (`agents/knowledge_base_pgvector.py`) 🆕

**Purpose**: Vector-based semantic search for compliance knowledge

**Initialization**:
```python
def __init__(self, session, sod_rule_repo, embedding_provider='huggingface'):
    # Load embedding model
    self.embedding_service = create_embedding_service(
        provider='huggingface',
        model_name='sentence-transformers/all-MiniLM-L6-v2',
        dimensions=384
    )

    # Load SOD rules from file
    sod_rules = self._load_sod_rules()

    # Generate embeddings for rules
    self._generate_rule_embeddings(sod_rules)
```

**Embedding Service**:
```python
class HuggingFaceEmbeddingService:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.dimensions = 384
        self.cache = {}

    def embed_text(self, text: str) -> List[float]:
        if text in self.cache:
            return self.cache[text]

        embedding = self.model.encode(text)
        self.cache[text] = embedding.tolist()
        return self.cache[text]
```

**Vector Search**:
```python
def search_similar_rules(self, query: str, top_k: int = 5):
    # Generate query embedding
    query_embedding = self.embedding_service.embed_text(query)

    # Execute pgvector cosine similarity search
    results = session.execute("""
        SELECT
            doc_id,
            doc_type,
            content,
            metadata,
            1 - (embedding <=> :query::vector) as similarity
        FROM knowledge_base_documents
        ORDER BY embedding <=> :query::vector
        LIMIT :limit
    """, {"query": query_embedding, "limit": top_k})

    return results.fetchall()
```

**Document Types**:
- **SOD_RULE**: Core segregation of duties rules
- **COMPENSATING_CONTROL**: Individual control descriptions
- **RESOLUTION_STRATEGY**: Resolution approaches per severity
- **JOB_ROLE**: Job role mappings and justifications

---

## Vector Knowledge Base (NEW)

### pgvector Integration

**Extension Installation**:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

**Knowledge Base Documents Table**:
```sql
CREATE TABLE knowledge_base_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doc_id VARCHAR(100) UNIQUE NOT NULL,
    doc_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    embedding vector(384) NOT NULL,  -- 384-dimensional vector
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for fast similarity search
CREATE INDEX idx_kb_docs_embedding
ON knowledge_base_documents
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create indexes for filtering
CREATE INDEX idx_kb_docs_type ON knowledge_base_documents(doc_type);
CREATE INDEX idx_kb_docs_created ON knowledge_base_documents(created_at DESC);
```

**Vector Operators**:
- `<=>` : Cosine distance (1 - cosine similarity)
- `<->` : Euclidean distance (L2)
- `<#>` : Inner product

**Example Query**:
```sql
SELECT
    doc_id,
    doc_type,
    content,
    1 - (embedding <=> '[0.1, 0.2, ...]'::vector) as similarity
FROM knowledge_base_documents
WHERE doc_type = 'SOD_RULE'
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 5;
```

### Embedding Process

**Document Preparation**:
```python
def prepare_document(rule_data):
    content = f"""
    SOD Rule: {rule_data['rule_id']}
    Principle: {rule_data['principle']}
    Description: {rule_data['description']}
    Categories: {rule_data['category1']} <-> {rule_data['category2']}
    Severity: {rule_data['severity']}
    Risk Score: {rule_data['base_risk_score']}
    """
    return content
```

**Embedding Generation**:
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')

# Generate embedding
text = prepare_document(rule_data)
embedding = model.encode(text)  # Returns numpy array of 384 floats

# Store in database
cursor.execute("""
    INSERT INTO knowledge_base_documents
    (doc_id, doc_type, content, embedding, metadata)
    VALUES (%s, %s, %s, %s, %s)
""", (doc_id, 'SOD_RULE', text, embedding.tolist(), metadata_json))
```

**Seeded Documents** (49 total):
- 18 SOD Rules (one per rule with metadata)
- 12 Compensating Controls (with descriptions and costs)
- 18 Resolution Strategies (6 rules × 3 severity levels)
- 1 Job Role example

---

## RAG Pattern Implementation

**RAG** = Retrieval Augmented Generation

### How It Works

```
┌──────────────────────────────────────────────────────────────┐
│ 1. USER QUERY                                                │
│    "Analyze Revenue Director access with approval rights"   │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. VECTOR SEARCH (Retrieval)                                │
│    • Generate query embedding (384-dim)                     │
│    • Search pgvector knowledge base                         │
│    • Return top-k similar documents (k=5)                   │
│                                                              │
│    Results:                                                  │
│    - SOD-RULE-001: Maker-Checker (62.39% similar)          │
│    - Resolution strategies (60%+ similar)                   │
│    - Compensating controls (58%+ similar)                   │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. CONTEXT ENRICHMENT                                       │
│    • Combine retrieved documents                            │
│    • Add user data from database                            │
│    • Add current role permissions                           │
│    • Format as structured context                           │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. LLM PROMPT (Augmentation)                                │
│                                                              │
│    You are a compliance analyst. Use ONLY the following     │
│    information to analyze this access request:              │
│                                                              │
│    Retrieved SOD Rules:                                      │
│    - SOD-RULE-001: User should not create AND approve       │
│      the same transaction                                   │
│                                                              │
│    User Data:                                                │
│    - Job Title: Revenue Director                            │
│    - Requested Roles: Revenue Manager, Revenue Approver     │
│                                                              │
│    Required Permissions Analysis:                            │
│    - Revenue Manager: Cash Sale (Full), Invoice (Full)      │
│    - Revenue Approver: Invoice Approval (Create)            │
│                                                              │
│    Question: Does this create SOD conflicts?                │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. LLM GENERATION                                           │
│    • Claude Opus 4.6 processes prompt                       │
│    • Grounds response in retrieved context                  │
│    • Cannot hallucinate - only uses provided data           │
│                                                              │
│    Response:                                                 │
│    "Yes, CRITICAL conflict detected. SOD-RULE-001           │
│     violation: User has Cash Sale (Full) + Invoice Approval │
│     (Create), allowing maker-checker bypass..."             │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│ 6. FORMATTED OUTPUT                                         │
│    • Structure the response                                  │
│    • Add severity indicators                                │
│    • Include compensating controls                          │
│    • Return to user                                         │
└──────────────────────────────────────────────────────────────┘
```

### MCP Tool: `query_knowledge_base`

**Purpose**: Expose vector search for prompt grounding

**Usage Pattern**:
```python
# Step 1: Query knowledge base
kb_results = query_knowledge_base(
    query="revenue approval conflict maker checker",
    doc_type="ALL",
    limit=5
)

# Step 2: Use results to ground analysis
analysis = analyze_access_request(
    job_title="Revenue Director",
    requested_roles=["Revenue Manager", "Revenue Approver"],
    context=kb_results  # ← Grounded in vector database
)
```

**Example MCP Call**:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "query_knowledge_base",
    "arguments": {
      "query": "transaction approval segregation",
      "doc_type": "SOD_RULE",
      "limit": 3
    }
  },
  "id": 1
}
```

**Response**:
```json
{
  "result": {
    "content": [{
      "type": "text",
      "text": "Knowledge Base Search Results (3 found)\n\n1. sod_rule_SOD-RULE-001 (Similarity: 65.42%)\n   • Type: SOD_RULE\n   • Severity: CRITICAL\n   • Content: User should not create AND approve...\n\n2. resolution_transaction_entry_vs_approval_HIGH (62.18%)\n   • Type: RESOLUTION_STRATEGY\n   ...\n"
    }]
  }
}
```

---

## Data Flow

### 1. User Query Processing (with RAG)

```
User: "Analyze Revenue Director access"
  │
  ├─> MCP Tool: query_knowledge_base
  │   └─> Vector Search pgvector
  │       └─> Returns: SOD-RULE-001 (62% similar)
  │
  ├─> MCP Tool: analyze_access_request
  │   ├─> Fetch user roles from database
  │   ├─> Get permissions for roles
  │   ├─> Check conflicts with SOD rules
  │   ├─> Calculate risk scores
  │   └─> Generate recommendations (grounded in KB)
  │
  └─> Return formatted analysis
```

### 2. Autonomous Data Collection

```
APScheduler (cron: 0 2 * * *)
  │
  ├─> DataCollectionAgent.full_sync()
  │   ├─> NetSuiteConnector.fetch_users()
  │   │   └─> NetSuite RESTlet API
  │   ├─> NetSuiteConnector.fetch_roles()
  │   └─> UserRepository.upsert_batch()
  │
  ├─> SODAnalysisAgent.analyze_all_users()
  │   └─> Detect new violations
  │
  └─> NotificationAgent.send_alerts()
      └─> Email to compliance team
```

### 3. Access Request Analysis (End-to-End)

```
Claude Desktop UI
  │
  │ User types: "Analyze Revenue Director with manager and approver roles"
  │
  ├─> MCP stdio transport
  │   └─> JSON-RPC message
  │
  ├─> MCP Server (port 8080)
  │   ├─> Authenticate (X-API-Key)
  │   ├─> Parse tool call: analyze_access_request
  │   └─> Route to handler
  │
  ├─> ComplianceOrchestrator
  │   └─> Call analyze_access_request_handler
  │
  ├─> Analysis Script (subprocess)
  │   ├─> Fetch roles from NetSuite/database
  │   ├─> Get permissions for each role
  │   ├─> Load SOD rules from database
  │   ├─> Check permission pairs against conflict matrices
  │   ├─> Calculate inherent risk scores
  │   ├─> Query job_role_mappings for validation
  │   ├─> Get compensating_controls for severity
  │   ├─> Calculate residual risk
  │   └─> Write JSON to output/access_request_analysis.json
  │
  ├─> Handler reads JSON file
  │   ├─> Format conflicts (top 5 shown)
  │   ├─> Format job role validation
  │   ├─> Format compensating controls
  │   └─> Generate recommendation
  │
  ├─> Return to MCP Server
  │   └─> Wrap in JSON-RPC response
  │
  └─> Claude Desktop displays formatted analysis
      • 47 conflicts found
      • CRITICAL severity
      • Recommended controls: $100K/year
      • Residual risk: 7.3/100
```

---

## MCP Tools (20 Tools)

### System Management Tools (5)

#### 1. `list_systems`
- **Description**: List all available systems for compliance review
- **Parameters**: None
- **Returns**: System name, status, user count, last sync time
- **Example**:
  ```json
  {"jsonrpc":"2.0","method":"tools/call","params":{"name":"list_systems"},"id":1}
  ```

#### 2. `get_user_violations`
- **Description**: Get violations for a specific user
- **Parameters**:
  - `user_email` (required): User's email address
  - `severity` (optional): Filter by severity
- **Example**:
  ```json
  {
    "name": "get_user_violations",
    "arguments": {"user_email": "user@example.com", "severity": "CRITICAL"}
  }
  ```

#### 3. `remediate_violation`
- **Description**: Create exemption or revoke access
- **Parameters**:
  - `violation_id`: Violation UUID
  - `action`: "create_exemption" or "revoke_access"
  - `justification`: Business reason
  - `approver_email`: Approving manager

#### 4. `schedule_review`
- **Description**: Schedule compliance scan
- **Parameters**:
  - `scan_type`: "sod_violations", "excessive_permissions", "all"
  - `schedule`: "now", "daily", "weekly"

#### 5. `get_violation_stats`
- **Description**: Get violation statistics
- **Parameters**:
  - `time_period`: "7d", "30d", "90d"
- **Returns**: Counts by severity, trend data

### Data Synchronization Tools (5)

#### 6. `start_collection_agent`
- **Description**: Start autonomous data collection agent
- **Parameters**: None
- **Returns**: Agent status, scheduled jobs

#### 7. `stop_collection_agent`
- **Description**: Stop data collection agent
- **Parameters**: None

#### 8. `get_collection_agent_status`
- **Description**: Get agent status and sync history
- **Parameters**: None
- **Returns**: Running status, last sync time, next scheduled sync

#### 9. `trigger_manual_sync`
- **Description**: Trigger immediate data sync
- **Parameters**:
  - `sync_type`: "full" or "incremental"
  - `system`: "netsuite", "okta", or "all"

#### 10. `list_all_users`
- **Description**: List all users in system
- **Parameters**:
  - `system`: Filter by system
  - `status`: Filter by status
  - `limit`: Max results (default 50)

### SOD Analysis Tools (8) 🆕

#### 11. `analyze_access_request`
- **Description**: Comprehensive access request analysis with level-based SOD detection
- **Parameters**:
  - `job_title` (required): User's job title
  - `requested_roles` (required): Array of role names
  - `user_email` (optional): User email
- **Process**:
  1. Fetch roles from NetSuite
  2. Get all permissions with levels
  3. Run conflict detection (5×5 matrices)
  4. Validate against job_role_mappings
  5. Get compensating controls
  6. Calculate residual risk
- **Returns**:
  - Conflicts found (with top 5 detailed)
  - Job role validation
  - Recommended compensating controls
  - Inherent and residual risk scores
  - Overall recommendation
- **Example Response**:
  ```
  Access Request Analysis: Revenue Director

  Conflicts Found: 47
  Risk Level: 🟠 HIGH
  Recommendation: APPROVE_WITH_COMPENSATING_CONTROLS

  Detected Conflicts:
  1. 🔴 CRIT - Cash Sale (Full) + Invoice Approval (Create)
     Inherent Risk: 73.5/100
  ...

  Recommended Controls:
  1. REJECT_OR_EXECUTIVE_OVERRIDE
     • Inherent Risk: 73.5/100
     • Residual Risk: 7.3/100
     • Package: Critical Risk Control Package ($100K/year)
  ```

#### 12. `query_sod_rules`
- **Description**: Query SOD rules from database
- **Parameters**:
  - `category1`: First permission category
  - `category2`: Second permission category
  - `severity`: Filter by severity
  - `limit`: Max results (default 10)
- **Returns**: SOD rules with principles, categories, risk scores
- **Database Query**:
  ```sql
  SELECT rule_id, principle, category1, category2,
         severity, base_risk_score, description
  FROM sod_rules
  WHERE is_active = true
    AND (category1 = :cat1 OR category2 = :cat1)
    AND (category1 = :cat2 OR category2 = :cat2)
    AND severity = :severity
  LIMIT :limit
  ```

#### 13. `get_compensating_controls`
- **Description**: Get compensating controls for severity level
- **Parameters**:
  - `severity` (required): "CRITICAL", "HIGH", "MEDIUM", "LOW"
  - `include_cost` (optional): Include cost estimates (default true)
- **Returns**:
  - Control package details
  - List of included controls
  - Risk reduction percentages
  - Annual costs
  - Implementation time
- **Example Response**:
  ```
  Critical Risk Control Package (for CRITICAL severity)

  Package Details:
  • Risk Reduction: 90%
  • Annual Cost: $100,000
  • Implementation Time: 90 hours

  Included Controls (8):
  • Segregated Approval Workflows (70% reduction, $5K)
  • Dual Approval Workflow (60% reduction, $8K)
  ...
  ```

#### 14. `validate_job_role`
- **Description**: Validate if role combination is typical for job title
- **Parameters**:
  - `job_title` (required): Job title to validate
  - `requested_roles` (required): Array of roles
- **Returns**:
  - Is typical combination (boolean)
  - Typical roles for this job title
  - Required compensating controls
  - Business justification
  - Recommendation (APPROVE/REVIEW)
- **Database Query**:
  ```sql
  SELECT job_title, department, acceptable_role_combinations,
         business_justification
  FROM job_role_mappings
  WHERE LOWER(job_title) = LOWER(:job_title)
  ```

#### 15. `check_permission_conflict`
- **Description**: Check if two permissions conflict based on levels
- **Parameters**:
  - `permission1_name` (required): First permission
  - `permission1_level` (required): "None", "View", "Create", "Edit", "Full"
  - `permission2_name` (required): Second permission
  - `permission2_level` (required): Level
- **Process**:
  1. Map level names to values (None=0, View=1, Create=2, Edit=3, Full=4)
  2. Look up severity in conflict matrix
  3. Return conflict assessment
- **Conflict Matrix**:
  ```python
  severity_matrix = [
    ['OK',   'OK',   'OK',   'OK',   'OK'  ],
    ['OK',   'OK',   'LOW',  'LOW',  'MED' ],
    ['OK',   'LOW',  'MED',  'HIGH', 'CRIT'],
    ['OK',   'LOW',  'HIGH', 'CRIT', 'CRIT'],
    ['OK',   'MED',  'CRIT', 'CRIT', 'CRIT']
  ]
  ```
- **Returns**: Conflict severity and explanation

#### 16. `get_permission_categories`
- **Description**: Get all permission categories with risk scores
- **Parameters**:
  - `include_permissions` (optional): Include permission lists (default false)
- **Returns**:
  - 7 permission categories
  - Base risk scores (70-95/100)
  - Category descriptions
- **Categories**:
  1. role_admin (95/100)
  2. transaction_payment (95/100)
  3. user_admin (90/100)
  4. transaction_approval (80/100)
  5. transaction_entry (75/100)
  6. vendor_setup (75/100)
  7. bank_reconciliation (70/100)

#### 17. `search_permissions`
- **Description**: Search NetSuite permissions by name, category, or risk
- **Parameters**:
  - `search_term`: Text to match in permission names
  - `category`: Filter by category
  - `risk_level`: "HIGH", "MEDIUM", "LOW", "MINIMAL"
  - `limit`: Max results (default 20)
- **Data Source**: `data/netsuite_permission_mapping.json` (341 permissions)
- **Returns**:
  - Permission ID and name
  - Categories
  - Risk level
  - Levels granted (View/Create/Edit/Full)
  - Usage count (how many roles have it)

#### 20. `analyze_role_permissions` 🔥
- **Description**: Analyze internal SOD conflicts within a single role
- **Purpose**: Identify permission conflicts within a role (internal conflicts), generate detailed analysis report
- **Parameters**:
  - `role_name` (required): Name of the NetSuite role to analyze
  - `include_remediation_plan` (optional): Include detailed remediation recommendations (default: True)
  - `output_format` (optional): Output format for detailed report ("markdown", "json", "both", default: "markdown")
- **Process**:
  1. Fetch role permissions from database (with levels)
  2. Load permission mapping from netsuite_permission_mapping.json
  3. Categorize permissions using LEVEL_MAP (None=0, View=1, Create=2, Edit=3, Full=4)
  4. Apply 5×5 CONFLICT_MATRIX to find conflicts within the role
  5. Check SOD_CATEGORY_PAIRS (e.g., transaction_entry ↔ transaction_payment)
  6. Identify conflicts by severity (CRIT, HIGH, MED)
  7. Generate comprehensive markdown report with:
     - Executive summary
     - Detailed conflict analysis by severity
     - Permission breakdown by category
     - Remediation recommendations (split role, reduce permissions, add controls)
  8. Save report to `output/role_analysis/{role_name}_{timestamp}.md`
  9. Return formatted summary with key metrics + file path
- **Returns**:
  - Summary with conflict count, severity breakdown
  - Top 5 most critical conflicts
  - File path to detailed report
  - Recommended next steps
- **Example Response**:
  ```
  Internal Role Conflict Analysis: Fivetran - Cash Accountant

  📊 EXECUTIVE SUMMARY
  • Total Permissions: 160
  • Internal Conflicts Found: 181
  • Risk Assessment: 🔴 CRITICAL

  🔥 TOP 5 CRITICAL CONFLICTS

  1. 🔴 CRIT - Cash Sale + Invoice Approval
     Conflict: transaction_entry (Full) ↔ transaction_payment (Create)
     Inherent Risk: 73.5/100

  ... (4 more conflicts)

  💾 DETAILED REPORT SAVED
  File: output/role_analysis/Fivetran___Cash_Accountant_20260212_203545.md

  🎯 RECOMMENDED NEXT STEPS
  1. Review the detailed report for complete conflict analysis
  2. Consider role split or permission reduction
  3. Implement compensating controls if role must remain as-is
  ```
- **Report Contents**:
  - Executive summary with risk assessment
  - All conflicts grouped by severity (CRITICAL, HIGH, MEDIUM)
  - Permission breakdown by category (transaction_entry: 45, transaction_payment: 38, etc.)
  - Three remediation options:
    1. Role Split (create specialized roles)
    2. Permission Reduction (downgrade levels)
    3. Compensating Controls (add oversight)
  - Detailed level modification recommendations table
  - Testing plan
  - Audit compliance assessment
- **Use Cases**:
  - Role design review before deployment
  - Existing role audit and cleanup
  - Regulatory compliance assessments
  - Risk reduction initiatives
- **Pattern**: Agent Response with Attachments
  - Agent performs comprehensive analysis (database queries, conflict detection)
  - Agent generates detailed professional report (saved to file system)
  - Agent returns concise summary for LLM to present
  - User gets both: immediate conversational response + detailed attachment
  - No context window limits for detailed reports

### Knowledge Base Tools (2) 🆕

#### 18. `query_knowledge_base`
- **Description**: Query vector knowledge base using semantic search
- **Purpose**: Ground LLM prompts in actual compliance data
- **Parameters**:
  - `query` (required): Natural language query
  - `doc_type`: "SOD_RULE", "COMPENSATING_CONTROL", "RESOLUTION_STRATEGY", "JOB_ROLE", "ALL"
  - `limit`: Max results (default 5)
- **Process**:
  1. Generate query embedding (384-dim) using sentence-transformers
  2. Execute pgvector similarity search
  3. Return top-k documents with similarity scores
- **Vector Search SQL**:
  ```sql
  SELECT doc_id, doc_type, content, metadata,
         1 - (embedding <=> :query::vector) as similarity
  FROM knowledge_base_documents
  WHERE doc_type = :doc_type  -- if specified
  ORDER BY embedding <=> :query::vector
  LIMIT :limit
  ```
- **Example**:
  ```json
  {
    "name": "query_knowledge_base",
    "arguments": {
      "query": "revenue approval conflict maker checker",
      "doc_type": "ALL",
      "limit": 5
    }
  }
  ```
- **Response**:
  ```
  Knowledge Base Search Results (5 found)
  Query: revenue approval conflict maker checker

  1. sod_rule_SOD-RULE-001 (Similarity: 62.39%)
     • Type: SOD_RULE
     • Severity: CRITICAL
     • Content: SOD Rule: transaction_entry_vs_transaction_approval
                Principle: SOD-001: Maker-Checker Segregation
                Description: User should not create AND approve...

  2. resolution_transaction_entry_vs_approval_HIGH (60.69%)
     • Type: RESOLUTION_STRATEGY
     • Content: Resolution Strategy for HIGH Severity Conflicts...
  ```

#### 19. `perform_access_review` (System-wide)
- **Description**: Perform comprehensive access review for a system
- **Parameters**:
  - `system_name`: "netsuite", "okta", "salesforce"
  - `analysis_type`: "sod_violations", "excessive_permissions", "inactive_users", "all"
- **Process**:
  1. Fetch all users from system
  2. Analyze each user's access
  3. Detect violations
  4. Generate recommendations
  5. Create compliance scan record
- **Returns**: Scan ID, findings summary, recommendations

---

## Database Schema

### Core Tables (9)

#### users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    department VARCHAR(100),
    job_title VARCHAR(100),
    manager_email VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active',
    system_name VARCHAR(50) NOT NULL,
    external_id VARCHAR(255),
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_system ON users(system_name);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_department ON users(department);
```

#### roles
```sql
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role_name VARCHAR(255) NOT NULL,
    system_name VARCHAR(50) NOT NULL,
    role_id_external VARCHAR(255),
    description TEXT,
    permissions JSONB DEFAULT '[]',
    is_admin BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    UNIQUE(role_name, system_name)
);

CREATE INDEX idx_roles_system ON roles(system_name);
CREATE INDEX idx_roles_admin ON roles(is_admin);
CREATE INDEX idx_roles_permissions ON roles USING gin(permissions);
```

#### user_roles
```sql
CREATE TABLE user_roles (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_by VARCHAR(255),
    PRIMARY KEY (user_id, role_id)
);

CREATE INDEX idx_user_roles_user ON user_roles(user_id);
CREATE INDEX idx_user_roles_role ON user_roles(role_id);
```

#### sod_rules
```sql
CREATE TABLE sod_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_id VARCHAR(50) UNIQUE NOT NULL,
    rule_name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    principle VARCHAR(255),
    category1 VARCHAR(100),
    category2 VARCHAR(100),
    base_risk_score INTEGER,
    severity VARCHAR(20) NOT NULL,
    conflicting_permissions JSONB DEFAULT '[]',
    level_conflict_matrix JSONB,  -- 5×5 matrix
    resolution_strategies JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_sod_rules_active ON sod_rules(is_active);
CREATE INDEX idx_sod_rules_severity ON sod_rules(severity);
CREATE INDEX idx_sod_rules_categories ON sod_rules(category1, category2);
```

#### violations
```sql
CREATE TABLE violations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    rule_id UUID REFERENCES sod_rules(id),
    severity VARCHAR(20) NOT NULL,
    status VARCHAR(50) DEFAULT 'open',
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    resolution_notes TEXT,
    inherent_risk_score DECIMAL(5,2),
    residual_risk_score DECIMAL(5,2),
    conflicting_roles JSONB,
    conflicting_permissions JSONB,
    compensating_controls JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_violations_user ON violations(user_id);
CREATE INDEX idx_violations_rule ON violations(rule_id);
CREATE INDEX idx_violations_severity ON violations(severity);
CREATE INDEX idx_violations_status ON violations(status);
CREATE INDEX idx_violations_detected ON violations(detected_at DESC);
```

### SOD Configuration Tables (7) 🆕

#### compensating_controls
```sql
CREATE TABLE compensating_controls (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    control_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    control_type VARCHAR(50) NOT NULL,  -- PREVENTIVE, DETECTIVE, CORRECTIVE
    description TEXT,
    risk_reduction_percentage INTEGER,
    annual_cost_estimate VARCHAR(100),
    implementation_time_hours INTEGER,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_compensating_controls_type ON compensating_controls(control_type);
CREATE INDEX idx_compensating_controls_active ON compensating_controls(is_active);
```

**12 Compensating Controls**:
1. manager_approval (DETECTIVE, 35% reduction)
2. ceo_approval (PREVENTIVE, 50% reduction)
3. dual_approval_workflow (PREVENTIVE, 60% reduction)
4. segregated_workflows (PREVENTIVE, 70% reduction)
5. transaction_limits (PREVENTIVE, 40% reduction)
6. real_time_monitoring (DETECTIVE, 50% reduction)
7. quarterly_audit_review (DETECTIVE, 30% reduction)
8. manager_review (DETECTIVE, 35% reduction)
9. transaction_logging (DETECTIVE, 25% reduction)
10. monthly_reconciliation (DETECTIVE, 30% reduction)
11. vendor_validation (PREVENTIVE, 45% reduction)
12. access_review (DETECTIVE, 40% reduction)

#### control_packages
```sql
CREATE TABLE control_packages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    package_id VARCHAR(50) UNIQUE NOT NULL,
    package_name VARCHAR(255) NOT NULL,
    severity_level VARCHAR(20) NOT NULL,  -- CRITICAL, HIGH, MEDIUM, LOW
    description TEXT,
    included_control_ids VARCHAR(50)[] NOT NULL,
    total_risk_reduction INTEGER,
    estimated_annual_cost VARCHAR(100),
    implementation_time_hours INTEGER,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    CONSTRAINT control_packages_total_risk_reduction_check
        CHECK (total_risk_reduction >= 0 AND total_risk_reduction <= 100)
);

CREATE INDEX idx_control_packages_severity ON control_packages(severity_level);
CREATE INDEX idx_control_packages_active ON control_packages(is_active);
```

**6 Control Packages**:
1. low_risk_package (LOW, 50% reduction, $2K/year)
2. medium_risk_package (MEDIUM, 80% reduction, $15K/year)
3. high_risk_package (HIGH, 85% reduction, $50K/year)
4. critical_risk_package (CRITICAL, 90% reduction, $100K/year)
5. executive_access_package (CRITICAL, 85% reduction, $75K/year)
6. developer_access_package (HIGH, 80% reduction, $40K/year)

#### job_role_mappings
```sql
CREATE TABLE job_role_mappings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_role_id VARCHAR(50) UNIQUE NOT NULL,
    job_title VARCHAR(255) NOT NULL,
    department VARCHAR(100),
    acceptable_role_combinations JSONB NOT NULL,
    business_justification TEXT,
    requires_compensating_controls BOOLEAN DEFAULT false,
    typical_controls VARCHAR(50)[],
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_job_role_mappings_title ON job_role_mappings(job_title);
CREATE INDEX idx_job_role_mappings_dept ON job_role_mappings(department);
CREATE INDEX idx_job_role_mappings_active ON job_role_mappings(is_active);
```

**10 Job Role Mappings**:
1. Revenue Director
2. Controller
3. Accounts Payable Manager
4. Accounts Receivable Manager
5. Financial Analyst
6. Billing Manager
7. Treasury Manager
8. Cost Accountant
9. IT Administrator
10. Compliance Officer

#### permission_categories
```sql
CREATE TABLE permission_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category_id VARCHAR(50) UNIQUE NOT NULL,
    category_name VARCHAR(255) NOT NULL,
    base_risk_score INTEGER NOT NULL,
    description TEXT,
    permissions JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT permission_categories_risk_check
        CHECK (base_risk_score >= 0 AND base_risk_score <= 100)
);

CREATE INDEX idx_permission_categories_risk ON permission_categories(base_risk_score DESC);
```

**7 Permission Categories**:
1. role_admin (95/100)
2. transaction_payment (95/100)
3. user_admin (90/100)
4. transaction_approval (80/100)
5. transaction_entry (75/100)
6. vendor_setup (75/100)
7. bank_reconciliation (70/100)

#### knowledge_base_documents 🔍
```sql
CREATE TABLE knowledge_base_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doc_id VARCHAR(100) UNIQUE NOT NULL,
    doc_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    embedding vector(384) NOT NULL,  -- pgvector extension
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_kb_docs_embedding
ON knowledge_base_documents
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX idx_kb_docs_type ON knowledge_base_documents(doc_type);
CREATE INDEX idx_kb_docs_created ON knowledge_base_documents(created_at DESC);
```

**49 Knowledge Base Documents**:
- 18 SOD Rules (with embeddings)
- 12 Compensating Controls (with embeddings)
- 18 Resolution Strategies (6 rules × 3 severities)
- 1 Job Role example

---

## LLM Integration

### LLM Abstraction Layer (`services/llm/`)

**Supported Providers**:
1. Anthropic (Claude Opus 4.6, Sonnet 4.5, Haiku 4.5)
2. OpenAI (GPT-4, GPT-3.5-turbo)
3. Google (Gemini Pro, Gemini Ultra)
4. Cohere (Command, Command-Light)

**Configuration** (`config/llm_config.yaml`):
```yaml
providers:
  anthropic:
    default_model: claude-opus-4.6
    models:
      - claude-opus-4.6
      - claude-sonnet-4-5-20250929
      - claude-haiku-4-5-20251001
    api_key_env: ANTHROPIC_API_KEY
    max_tokens: 4096
    temperature: 0.3

  openai:
    default_model: gpt-4
    models:
      - gpt-4
      - gpt-3.5-turbo
    api_key_env: OPENAI_API_KEY

default_provider: anthropic
```

**Factory Pattern**:
```python
from services.llm.factory import create_llm_provider

llm = create_llm_provider(
    provider='anthropic',
    model='claude-opus-4.6'
)

response = llm.generate(
    prompt="Analyze SOD conflict...",
    system="You are a compliance analyst...",
    max_tokens=2000
)
```

**Base LLM Interface**:
```python
class BaseLLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        pass

    @abstractmethod
    def generate_with_tools(self, prompt: str, tools: List[Dict]) -> Dict:
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        pass
```

---

## Level-Based Conflict Detection

### Permission Levels

**Hierarchy** (0-4):
```python
PERMISSION_LEVELS = {
    'NONE': 0,
    'VIEW': 1,
    'CREATE': 2,
    'EDIT': 3,
    'FULL': 4
}
```

### 5×5 Conflict Matrices

Each SOD rule has a level_conflict_matrix stored in the database:

```json
{
  "level_conflict_matrix": [
    ["OK",   "OK",   "OK",   "OK",   "OK"  ],
    ["OK",   "OK",   "LOW",  "LOW",  "MED" ],
    ["OK",   "LOW",  "MED",  "HIGH", "CRIT"],
    ["OK",   "LOW",  "HIGH", "CRIT", "CRIT"],
    ["OK",   "MED",  "CRIT", "CRIT", "CRIT"]
  ]
}
```

**Matrix Interpretation**:
- **Rows**: Permission 1 level (0-4)
- **Columns**: Permission 2 level (0-4)
- **Cell Values**: Conflict severity (OK, LOW, MED, HIGH, CRIT)

**Example**:
```python
# User has:
# - Invoice (Full = 4)
# - Invoice Approval (Create = 2)

severity = matrix[4][2]  # = "CRIT"
```

### Risk Calculation

**Inherent Risk**:
```python
def calculate_inherent_risk(rule, level1, level2):
    base_risk = rule['base_risk_score']  # e.g., 50
    level_multiplier = (level1 + level2) / 8.0
    inherent_risk = base_risk * level_multiplier
    return inherent_risk
```

**Example**:
```python
# Rule: Maker-Checker Segregation (base_risk = 50)
# Levels: Invoice (Full=4), Invoice Approval (Create=2)

inherent_risk = 50 * (4 + 2) / 8.0
inherent_risk = 50 * 0.75
inherent_risk = 37.5  # Out of 100

# But matrix shows CRIT, so apply severity multiplier:
if severity == 'CRIT':
    inherent_risk *= 1.96  # CRIT multiplier
    inherent_risk = 73.5
```

**Residual Risk** (with controls):
```python
def calculate_residual_risk(inherent_risk, control_package):
    reduction = control_package['total_risk_reduction']  # e.g., 90%
    residual_risk = inherent_risk * (1 - reduction / 100.0)
    return residual_risk

# Example:
# Inherent: 73.5, Control Package: 90% reduction
residual_risk = 73.5 * (1 - 0.90) = 7.35
```

---

## Deployment Architecture

### Local Development

```
┌─────────────────────────────────────────┐
│  MacOS (Development Machine)            │
│  ┌─────────────────────────────────────┐│
│  │ PostgreSQL 14 (localhost:5432)      ││
│  │ • compliance_db                     ││
│  │ • pgvector extension                ││
│  └─────────────────────────────────────┘│
│  ┌─────────────────────────────────────┐│
│  │ MCP Server (port 8080)              ││
│  │ • FastAPI + uvicorn                 ││
│  │ • 19 MCP tools                      ││
│  │ • Knowledge Base Agent              ││
│  └─────────────────────────────────────┘│
│  ┌─────────────────────────────────────┐│
│  │ Claude Desktop App                  ││
│  │ • MCP stdio connection              ││
│  │ • Natural language interface        ││
│  └─────────────────────────────────────┘│
│  ┌─────────────────────────────────────┐│
│  │ Data Collection Agent               ││
│  │ • APScheduler background            ││
│  │ • Full sync: Daily 2 AM             ││
│  │ • Incremental: Hourly               ││
│  └─────────────────────────────────────┘│
└─────────────────────────────────────────┘
```

### Production Deployment (Future)

```
┌──────────────────────────────────────────────────────────┐
│  Cloud Infrastructure (AWS/GCP/Azure)                    │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Load Balancer (HTTPS)                              │  │
│  └────────────┬───────────────────────────────────────┘  │
│               │                                           │
│  ┌────────────▼───────────┐  ┌────────────────────────┐ │
│  │ MCP Server (3 replicas)│  │ Background Workers (2) │ │
│  │ • Auto-scaling         │  │ • Data Collection      │ │
│  │ • Health checks        │  │ • SOD Analysis         │ │
│  └────────────┬───────────┘  │ • Notifications        │ │
│               │              └────────────┬───────────┘ │
│               │                           │             │
│  ┌────────────▼──────────────────────────▼───────────┐ │
│  │ PostgreSQL with pgvector (RDS/CloudSQL)           │ │
│  │ • Multi-AZ deployment                             │ │
│  │ • Automated backups                               │ │
│  │ • Read replicas                                   │ │
│  └───────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────┐ │
│  │ Redis (ElastiCache/Cloud Memorystore)             │ │
│  │ • Session caching                                 │ │
│  │ • Rate limiting                                   │ │
│  └───────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────┐ │
│  │ Vector Store (Pinecone/Weaviate) - Optional       │ │
│  │ • Dedicated vector database for scale             │ │
│  └───────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

---

## Security & Authentication

### API Key Authentication

**MCP Server**:
```python
@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)

    api_key = request.headers.get("X-API-Key")
    if api_key != os.getenv("MCP_API_KEY"):
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid API key"}
        )

    return await call_next(request)
```

### Environment Variables

**Required**:
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/compliance_db

# MCP Server
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8080
MCP_API_KEY=your-secure-api-key-here

# LLM Providers
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...  # Optional
GOOGLE_API_KEY=...  # Optional

# NetSuite
NETSUITE_ACCOUNT_ID=5260239_SB1
NETSUITE_CONSUMER_KEY=...
NETSUITE_CONSUMER_SECRET=...
NETSUITE_TOKEN_ID=...
NETSUITE_TOKEN_SECRET=...
NETSUITE_FIVETRAN_RESTLET_URL=https://...

# Okta (Optional)
OKTA_DOMAIN=your-domain.okta.com
OKTA_API_TOKEN=...

# Encryption
MASTER_ENCRYPTION_KEY=...  # Fernet key for sensitive data
```

### Data Encryption

**At Rest**:
- PostgreSQL TLS encryption
- Sensitive columns encrypted with Fernet
- API keys stored in environment, not database

**In Transit**:
- HTTPS for all API calls
- TLS for database connections
- Secure RESTlet URLs for NetSuite

---

## Appendix

### File Structure

```
compliance-agent/
├── agents/
│   ├── __init__.py
│   ├── analyzer.py                    # SOD Analysis Agent
│   ├── data_collector.py              # Data Collection Agent
│   ├── knowledge_base_pgvector.py 🆕  # Vector KB Agent
│   └── notifications.py               # Notification Agent
├── mcp/
│   ├── __init__.py
│   ├── mcp_server.py                  # Main MCP server
│   ├── mcp_tools.py 🆕                # 19 tool definitions
│   └── orchestrator.py                # ComplianceOrchestrator
├── connectors/
│   ├── __init__.py
│   ├── base_connector.py              # Abstract base
│   ├── netsuite_connector.py          # NetSuite integration
│   └── okta_connector.py              # Okta integration
├── services/
│   ├── llm/                           # LLM abstraction
│   │   ├── base.py
│   │   ├── anthropic.py
│   │   ├── openai.py
│   │   ├── factory.py
│   │   └── config_manager.py
│   ├── embedding_service.py 🆕        # Vector embeddings
│   ├── netsuite_client.py             # NetSuite client
│   └── okta_client.py                 # Okta client
├── repositories/
│   ├── user_repository.py
│   ├── role_repository.py
│   ├── violation_repository.py
│   ├── sod_rule_repository.py
│   ├── exemption_repository.py
│   ├── control_package_repository.py 🆕
│   └── job_role_mapping_repository.py 🆕
├── models/
│   ├── database_config.py             # SQLAlchemy config
│   ├── user.py
│   ├── role.py
│   ├── violation.py
│   └── sod_rule.py
├── scripts/
│   ├── seed_sod_configurations.py 🆕  # Seed all config tables
│   ├── analyze_access_request_with_levels.py 🆕
│   └── analyze_and_categorize_permissions.py 🆕
├── database/
│   ├── schema_extensions.sql 🆕       # pgvector + new tables
│   └── seed_data/
│       └── sod_rules.json
├── data/
│   ├── netsuite_sod_config_unified.json
│   ├── compensating_controls.json 🆕
│   ├── job_role_mappings.json 🆕
│   └── netsuite_permission_mapping.json 🆕
├── config/
│   ├── llm_config.yaml                # LLM provider config
│   └── settings.py
├── docs/
│   ├── MCP_SOD_TOOLS.md 🆕           # Tool documentation
│   ├── PERMISSIBLE_COMBINATIONS.md 🆕
│   └── PERMISSION_ANALYSIS.md 🆕
├── output/
│   ├── access_request_analysis.json   # Analysis results
│   └── role_analysis/ 🔥              # Role conflict reports
│       └── {role_name}_{timestamp}.md # Detailed role reports
├── .env                               # Environment variables
├── requirements.txt
├── ARCHITECTURE_V4.md 🆕             # This document
├── TECHNICAL_SPECIFICATION_V3.md
├── MCP_SETUP_GUIDE.md 🆕
└── SMOKE_TEST_RESULTS.md 🆕
```

### Key Technologies

- **Language**: Python 3.9+
- **Web Framework**: FastAPI 0.104+
- **Database**: PostgreSQL 14+ with pgvector extension
- **ORM**: SQLAlchemy 2.0+
- **Scheduler**: APScheduler 3.10+
- **Vector Search**: pgvector + sentence-transformers
- **Embedding Model**: all-MiniLM-L6-v2 (384-dim)
- **LLM**: Claude Opus 4.6 (primary), others supported
- **Protocol**: MCP (Model Context Protocol) JSON-RPC 2.0
- **Authentication**: OAuth 1.0a (NetSuite), OAuth 2.0 (Okta)

### Performance Metrics

| Operation | Latency | Notes |
|-----------|---------|-------|
| MCP Tool Call | <100ms | Simple queries |
| Vector Search | <50ms | 49 documents, top-5 |
| Access Analysis | 2-5s | Full conflict detection |
| Data Sync (Full) | 5-10 min | ~1000 users |
| Data Sync (Incr) | 30-60s | Changed users only |
| Database Query | <10ms | With proper indexes |
| LLM Generation | 2-4s | Claude Opus 4.6 |

---

---

## LangSmith Observability (V7.0)

Every Slack query is now fully traced in LangSmith with cost, token counts, and tool execution spans.

### Trace Structure

Verified trace `c06830c0` (2026-02-23) — "what can you do?", 14.3s, 2 MCP calls:

```
slack_compliance_query  [chain]          ← @traceable on process_with_claude()
├── ChatAnthropic        [llm/haiku]     ← tool-dispatch turn: decide which tools to call
├── call_mcp_tool        [tool]          ← @traceable(run_type="tool") — MCP execution
├── ChatAnthropic        [llm/haiku]     ← tool-dispatch turn 2 (follow-up tool calls)
├── call_mcp_tool        [tool]          ← second MCP call
├── ChatAnthropic        [llm/haiku]     ← rolling context compression (no tool output)
└── ChatAnthropic        [llm/opus]      ← synthesis turn: ToolMessages in history → Opus
```

**Model selection logic** (`slack_bot_local.py:461`):
```python
has_tool_results = any(isinstance(m, ToolMessage) for m in messages)
active_model = llm_with_tools if has_tool_results else haiku_with_tools
```
- Haiku handles all tool-dispatch turns (fast, cheap, structured routing)
- Opus handles the synthesis turn once tool results are in context (quality matters)

**Key design decision:** `call_mcp_tool()` is decorated with `@traceable(run_type="tool")`
(not `run_type="chain"`). This makes the tool execution visible as a `tool`-type child span,
which is the only reliable way for LangSmith online evaluators to detect MCP calls — the
evaluator executor cannot access S3-stored LLM `outputs.generations` inline.

### Thread Grouping

| Slack surface | `thread_id` value |
|---|---|
| DM channel | `channel` (stable per user-pair) |
| Channel thread | `f"{channel}-{thread_ts}"` |
| Slash command | `f"{channel_id}-slash"` |

### Online Evaluators (3 active)

| Evaluator | ID | Fail condition |
|---|---|---|
| `mcp_tool_called` | `0fd34f6a` | Score = 0 → no tools executed |
| `mcp_tool_coverage` | `36ea7cc4` | Score = 0 → access query missing `analyze_access_request` |
| `hallucination_heuristic` | `67f9da6a` | Score = 0 → `<tool_call>` XML or ungrounded numeric claims |

Each evaluator uses 3-layer detection: tool child runs → XML hallucination check → text grounding markers.
See `docs/LESSONS_LEARNED.md` Issues #31-32 for the root cause of the S3 limitation.

---

## Semantic Tool Router (NEW)

**Added:** March 2026
**File:** `utils/semantic_router.py`
**Impact:** Hit Rate@10: 0.72 → 1.00 | MRR: 0.18 → 0.91 | NDCG@10: 0.37 → 0.89

### Overview

The `SemanticToolRouter` replaces the regex-based `select_tools_for_intent()` in `utils/tool_router.py` as the primary tool-selection mechanism in the Slack bot. The keyword router is retained as a fallback.

Instead of matching keywords with handwritten regex patterns, each tool is represented by a rich text document (curated description + representative example queries). At query time, the user message is embedded and tools are ranked by cosine similarity.

**Why semantic routing beats regex:**
- Handles plurals, paraphrasing, and word-order variations automatically
- Ranking is continuous, not binary — the most relevant tool floats to rank 1
- Adding a new tool requires only writing its description, not new regex patterns
- Falls back to the keyword router if the sentence-transformers model is unavailable

### Architecture

```
Slack message
    │
    ▼
semantic_select_tools(user_message, all_tools, k=8)   [utils/semantic_router.py]
    │
    ├─► SemanticToolRouter singleton (built once at startup)
    │       │
    │       ├─ _build_index(): embed all tool texts with all-MiniLM-L6-v2
    │       │   Tool text = TOOL_EXEMPLARS[name] + live schema description
    │       │
    │       └─ select(query, k=8):
    │             1. Embed user message
    │             2. Cosine similarity against all tool embeddings
    │             3. Exclude always_include tools from top-k competition
    │             4. Return top-k intent tools + always_include appended at END
    │
    └─► Fallback: select_tools_for_intent()            [utils/tool_router.py]
            (used if model unavailable or select() raises)
```

### Key Classes and Functions

| Symbol | Location | Description |
|--------|----------|-------------|
| `SemanticToolRouter` | `utils/semantic_router.py` | Class — builds embedding index at startup, exposes `select(query, k)` |
| `TOOL_EXEMPLARS` | `utils/semantic_router.py` | Dict mapping tool name → curated description + example queries |
| `semantic_select_tools()` | `utils/semantic_router.py` | Drop-in replacement for `select_tools_for_intent()` — used in `slack_bot_local.py` |
| `get_router()` | `utils/semantic_router.py` | Returns module-level singleton; builds it on first call |
| `select_tools_for_intent()` | `utils/tool_router.py` | Legacy keyword/regex router — fallback only |

### `always_include` Placement Fix

In both routers, `always_include` tools (`initialize_session`, `check_my_approval_authority`) are now appended **at the END** of the shortlist, not inserted at positions 0–1. This means they no longer displace high-relevance tools from the top of the list — important for the synthesis model which reads the shortlist top-down.

### Embedding Model

| Property | Value |
|----------|-------|
| Model | `sentence-transformers/all-MiniLM-L6-v2` |
| Dimensions | 384 |
| Source | Local (no API key required) |
| Index built | Once at bot startup via `_build_index()` |
| Similarity | Cosine (unit-normalised dot product) |

The same model is already used by the Knowledge Base Agent for pgvector document search — no additional dependency is introduced.

### Metric Results (LangSmith Experiments)

| Experiment | Hit Rate@10 | MRR | NDCG@10 | Notes |
|------------|------------|-----|---------|-------|
| Baseline (regex router) | 0.72 | 0.18 | 0.37 | Plural/singular mismatches; always_include at position 0–1 |
| After regex fixes | 0.78 | 0.41 | — | Fixed INTENT_PATTERNS plural mismatches + always_include placement |
| After semantic router | **1.00** | **0.91** | **0.89** | SemanticToolRouter, all-MiniLM-L6-v2, k=8 |

All experiments run against the 32-query tool-selection golden set (`eval/golden_set.py`, dataset `compliance-tool-selection-v1`) and pushed to LangSmith.

---

## Eval Suite (NEW)

**Added:** March 2026
**Directory:** `eval/`
**Backend:** LangSmith (datasets + experiments)

### Overview

The eval suite provides reproducible, quantitative measurement of tool-routing quality and answer faithfulness. All results are pushed to LangSmith for tracking across experiments.

### Directory Structure

```
eval/
├── __init__.py
├── golden_set.py     — 32 tool-selection + 10 answer-quality labelled examples; push to LangSmith
├── evaluators.py     — Hit Rate@K, MRR, NDCG@K, Precision@K, Faithfulness (Haiku LLM-as-judge)
└── run_eval.py       — CLI runner; pushes experiment results to LangSmith
```

### Datasets

| LangSmith Dataset | Size | Contents |
|-------------------|------|----------|
| `compliance-tool-selection-v1` | 32 examples | `query`, `expected_tool`, `relevant_tools` (graded relevance 0/1/2 for NDCG) |
| `compliance-answer-quality-v1` | 10 examples | `query`, `expected_facts` for faithfulness judge |

### Evaluators (`eval/evaluators.py`)

| Evaluator | Key | What it measures |
|-----------|-----|-----------------|
| `hit_rate_at_k(k)` | `hit_rate_at_K` | Binary: was `expected_tool` in the top-K returned? |
| `mrr_evaluator` | `mrr` | 1 / rank of the first correct tool; 0 if absent |
| `ndcg_at_k(k)` | `ndcg_at_K` | Normalised discounted cumulative gain using graded `relevant_tools` scores |
| `precision_at_k(k)` | `precision_at_K` | Fraction of top-K tools that appear in `relevant_tools` |
| `faithfulness` | `faithfulness` | Claude Haiku LLM-as-judge: does the answer contain the expected facts? |

All evaluators follow the LangSmith 0.4.x signature:
```python
fn(outputs: dict, reference_outputs: dict) -> dict
```

### Running Evals

```bash
# Push / refresh golden datasets to LangSmith (run once, or after editing golden_set.py)
python -m eval.golden_set

# Dry-run: print examples without pushing
python -m eval.golden_set --dry-run

# Run all evaluations
python -m eval.run_eval

# Run only tool-selection eval (no live MCP server needed)
python -m eval.run_eval --suite tool_selection

# Run only answer-quality eval (requires live MCP server at :8080)
python -m eval.run_eval --suite answer_quality
```

Results appear in LangSmith → Experiments tab under the project set by `LANGCHAIN_PROJECT` in `.env`.

### Required Environment Variables

```bash
# LangSmith (required for eval suite)
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=compliance-agent      # experiment results group
LANGCHAIN_TRACING_V2=true

# Anthropic (required for faithfulness evaluator)
ANTHROPIC_API_KEY=sk-ant-...
```

---

**Version History**:
- V1.0 (2026-01-15): Initial architecture
- V2.0 (2026-01-28): Added data collection agent
- V3.0 (2026-02-05): Added level-based conflict detection
- V4.0 (2026-02-12): Added pgvector integration, RAG pattern, 19 MCP tools
- V4.1 (2026-02-12): Added tool #20 analyze_role_permissions, Agent Response with Attachments pattern
- V5.0 (2026-02-16): Added Slack bot, multi-turn agentic reasoning, 35 MCP tools
- V6.0 (2026-02-18): Security hardening, token optimization, Slack Block Kit UI, exception management
- V7.0 (2026-02-22): LangSmith full observability — Threads grouping, @traceable on call_mcp_tool(), 3 online evaluators with 3-layer detection logic
- V8.0 (2026-02-23): Haiku/Opus model split — Haiku for tool-dispatch turns, Opus for synthesis; verified trace c06830c0
- V9.0 (2026-03-15): Semantic tool router (utils/semantic_router.py) replaces regex routing as primary; tool_router.py kept as fallback; always_include tools moved to end of shortlist; eval suite added (eval/ directory) with LangSmith datasets and Hit Rate@K, MRR, NDCG@K, Precision@K, Faithfulness evaluators; metric improvement Hit Rate@10 0.72→1.00, MRR 0.18→0.91, NDCG@10 0.37→0.89

---

**Document Status**: ✅ **COMPLETE AND UP-TO-DATE** (V9.0 — 2026-03-15)
