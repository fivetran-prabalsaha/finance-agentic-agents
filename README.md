# SOD Compliance & Risk Assessment System

> **Status**: ✅ Production Ready | **Version**: 3.0.0 | Last Updated: 2026-04-12

[![CI](https://github.com/fivetran-prabalsaha/finance-agentic-agents/actions/workflows/ci.yml/badge.svg?branch=feature%2Fmcp-integration)](https://github.com/fivetran-prabalsaha/finance-agentic-agents/actions/workflows/ci.yml)

An agentic compliance system for automated Segregation of Duties (SOD) analysis, access reviews, and risk assessment across NetSuite environments. Operated via Slack and a web admin portal.

---

## What's Working

- **Slack Bot** — multi-turn agentic reasoning, Haiku dispatch + Opus synthesis, correction embeddings
- **37 MCP Tools** — full compliance toolkit via Model Context Protocol
- **SOD Violation Detection** — 18 rules covering SOX and internal controls
- **Semantic Tool Router** — MiniLM embeddings, Hit Rate@10=1.00, MRR=0.91
- **Angular Admin Portal** — JWT-authenticated, Dashboard/Violations/Exceptions/SOD Rules
- **LangSmith Observability** — distributed tracing, 3 online evaluators, eval suite
- **NetSuite Integration** — OAuth 1.0a, 1,933 active users, 99.7% sync coverage
- **CI/CD** — GitHub Actions: lint (ruff) + pytest on every push/PR

### Key Metrics

| Metric | Value |
|--------|-------|
| Users synced | 1,928 / 1,933 (99.7%) |
| SOD rules | 18 active |
| MCP tools | 37 |
| Search time | 2 sec (was 110 sec — 55x faster) |
| Tool Hit Rate@10 | 1.00 (semantic router) |
| Tool MRR | 0.91 (semantic router) |

---

## Architecture

```
Slack DM / @mention
        │
        ▼
┌─────────────────────────────────────────┐
│         Slack Bot (slack_bot_local.py)  │
│  • Haiku dispatch (tool_choice: any)    │
│  • Opus synthesis (adaptive thinking)  │
│  • Redis TTL cache (Phase A)           │
│  • Conversation summaries (Phase B)    │
│  • Correction embeddings (Phase C)     │
└────────────────┬────────────────────────┘
                 │ MCP JSON-RPC
                 ▼
┌─────────────────────────────────────────┐
│     MCP Server :8080 (mcp_server.py)   │
│  • 37 compliance tools                 │
│  • JWT admin portal (admin_api.py)     │
│  • CORS for Angular dev server (:4200) │
└────────────────┬────────────────────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
  PostgreSQL          NetSuite
  + pgvector          RESTlet API
  + Redis             (1,933 users)
```

**Two-turn LLM pipeline:**
```
Turn 1 — Claude Haiku 4.5   tool_choice: any  → picks MCP tool
Turn 2 — Claude Opus 4.6    adaptive thinking  → synthesizes answer
```

**Semantic tool router** (`utils/semantic_router.py`):
- Embeds all tool descriptions + curated example queries with `all-MiniLM-L6-v2` (local, no API key)
- At query time: embeds user message, ranks tools by cosine similarity
- Drop-in over keyword fallback (`utils/tool_router.py`)

---

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 16+ with pgvector extension
- Redis
- Claude API key

### Install & Run

```bash
# Install dependencies
pip install -r requirements.txt

# Set up database
psql $DATABASE_URL -f database/schema.sql
psql $DATABASE_URL -f database/schema_extensions.sql

# Start MCP server
./scripts/restart_mcp.sh
curl http://localhost:8080/health

# Start Slack bot (foreground)
python3 slack_bot_local.py

# Start Angular admin portal (dev)
cd angular-portal && ng serve
# → http://localhost:4200
```

---

## Project Structure

```
compliance-agent/
├── agents/                    # Autonomous agents
│   ├── analyzer.py            # SOD rule engine (18 rules, Claude Opus 4.6)
│   ├── data_collector.py      # Background sync (daily full + hourly incremental)
│   ├── knowledge_base.py      # RAG knowledge retrieval
│   └── ...
├── angular-portal/            # Angular 17 admin UI
│   └── src/app/features/      # Dashboard, Violations, Exceptions, SOD Rules
├── connectors/                # External system integrations
├── database/
│   ├── schema.sql             # PostgreSQL base schema (pgvector)
│   ├── schema_extensions.sql  # Extension tables
│   └── migrations/            # 10 Alembic migrations
├── eval/                      # LangSmith evaluation suite
│   ├── golden_set.py          # 32 tool-selection + 10 answer-quality queries
│   ├── evaluators.py          # Hit Rate@K, MRR, NDCG@K, Precision@K, Faithfulness
│   └── run_eval.py            # CLI runner
├── mcp/
│   ├── mcp_server.py          # FastAPI MCP server (37 tools)
│   ├── admin_api.py           # JWT admin portal backend (16 endpoints)
│   └── mcp_tools.py           # Tool definitions and handlers
├── models/                    # SQLAlchemy ORM models
├── repositories/              # Data access layer (10 repositories)
├── scripts/                   # Management + backfill scripts
├── services/
│   ├── correction_service.py  # Phase C correction embeddings
│   ├── netsuite_client.py     # NetSuite OAuth + REST
│   └── ...
├── skills/                    # Guided compliance workflows
│   ├── sod-compliance/
│   ├── sod-access-review/
│   └── employee-onboarding/
├── tests/                     # Test suites
├── utils/
│   ├── semantic_router.py     # Embedding-based tool router (active)
│   └── tool_router.py         # Keyword router (fallback)
├── slack_bot_local.py         # Slack Socket Mode bot
├── .github/workflows/ci.yml   # GitHub Actions CI
└── pyproject.toml             # Ruff, pytest, mypy config
```

---

## MCP Tools (37 total)

| Category | Tools |
|----------|-------|
| **Discovery** | `list_systems`, `list_all_users`, `get_user_violations` |
| **Analysis** | `perform_access_review`, `analyze_access_request`, `get_role_conflicts`, `get_role_risk_matrix` |
| **Violations** | `list_violations`, `get_violation_stats`, `get_violation_summary` |
| **Exceptions** | `list_active_exceptions`, `request_exception_approval`, `approve_exception` |
| **SOD Rules** | `list_sod_rules`, `check_sod_rule`, `get_sod_rule_details` |
| **Reporting** | `get_daily_report`, `generate_compliance_report`, `get_org_risk_assessment`, `export_report` |
| **Remediation** | `remediate_violation`, `get_remediation_plan` |
| **Knowledge** | `search_knowledge_base`, `get_compensating_controls` |
| **Admin** | `trigger_manual_sync`, `get_collection_agent_status`, `check_my_approval_authority` |

See `mcp/README.md` for full tool documentation.

---

## Admin Portal

Angular 17 portal at `http://localhost:4200` backed by JWT-authenticated FastAPI endpoints.

**Authority levels** (derived from NetSuite roles):
- L3 (Director): read-only
- L4 (Controller/VP): read + edit thresholds, rules, notifications
- L5 (CFO): full access including feature flags, LLM config

**Required env vars:**
```bash
JWT_SECRET=<long-random-string>
ADMIN_PORTAL_PASSWORD=<portal-password>
JWT_EXPIRE_HOURS=8
```

See `mcp/README.md` for full admin API endpoint reference.

---

## Slack Bot Features

| Feature | Description |
|---------|-------------|
| Multi-turn reasoning | Up to 5 tool calls per query, Haiku dispatch + Opus synthesis |
| Phase A: Redis cache | MCP tool results cached 30min–24h by tool type |
| Phase B: Summaries | Haiku-generated conversation summaries injected as prior context |
| Phase C: Corrections | Past ❌ corrections embedded (MiniLM 384-dim) + injected as few-shot context |
| Human feedback | Block Kit ✅/❌ buttons → LangSmith + Redis cache bust on ❌ |
| LangSmith tracing | Full cost/token/latency per trace + 3 online evaluators |

---

## Evaluation

```bash
# Push golden datasets to LangSmith (one-time)
LANGSMITH_API_KEY=... python -m eval.golden_set

# Run semantic router eval
LANGSMITH_API_KEY=... python -m eval.run_eval --router=semantic

# Compare keyword vs semantic side-by-side
LANGSMITH_API_KEY=... python -m eval.run_eval --suite=compare

# Answer quality eval (requires live MCP server)
LANGSMITH_API_KEY=... python -m eval.run_eval --suite=answer_quality
```

Results: smith.langchain.com → project `compliance-agent` → Datasets → Experiments

---

## Testing & CI

```bash
# Run tests locally
pytest tests/ -v

# Excluded from CI (require live external APIs):
#   test_end_to_end_stress.py, test_collection_agent.py,
#   test_mcp_server.py, test_restlet_optimization.py

# Lint
ruff check .
```

CI runs automatically on push/PR via GitHub Actions. See `.github/workflows/ci.yml`.

---

## Environment Variables

```bash
# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# NetSuite (OAuth 1.0a)
NETSUITE_ACCOUNT_ID=...
NETSUITE_CONSUMER_KEY=...
NETSUITE_CONSUMER_SECRET=...
NETSUITE_TOKEN_KEY=...
NETSUITE_TOKEN_SECRET=...
NETSUITE_RESTLET_URL=https://...

# Database & Cache
DATABASE_URL=postgresql://user:pass@localhost:5432/compliance_db
REDIS_URL=redis://localhost:6379/0

# Slack (Socket Mode)
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...

# Admin Portal
JWT_SECRET=<long-random-string>
ADMIN_PORTAL_PASSWORD=<portal-password>

# LangSmith
LANGSMITH_API_KEY=lsv2_pt_...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=compliance-agent

# Feature flags
USE_MCP_CACHE=true
USE_CONV_SUMMARIES=true
USE_ANSWER_FEEDBACK=true
USE_CORRECTION_CONTEXT=true
```

See `.env.example` for the full list.

---

## SOD Rules Coverage

18 rules across 5 categories:

| Category | Rules | Examples |
|----------|-------|---------|
| Financial (SOX) | 8 | AP Entry vs Approval, Payroll vs Employee Master |
| Procurement | 2 | PO Creation vs Approval, Vendor Master vs AP |
| IT Access | 4 | Admin vs Regular User, Script Dev vs Production |
| Sales | 2 | Pricing vs Sales Order, Commission Setup vs Processing |
| Compliance | 2 | Audit Log vs Financial, Compliance Officer Independence |

---

## DB Schema

```sql
users                  -- NetSuite users, sync status
roles                  -- Roles with sensitivity levels
user_roles             -- User-role assignments
sod_rules              -- 18 rules with conflicting_permissions JSONB
violations             -- Detected violations with risk_score (0-100)
compliance_scans       -- Scan execution history
conversation_summaries -- Slack conversation context (90d TTL)
answer_feedback        -- ✅/❌ feedback from Block Kit buttons
approved_exceptions    -- Approved SOD exception records
correction_embeddings  -- Phase C few-shot correction vectors (384-dim)
sod_permission_map     -- Permission → SOD category mapping
role_pair_conflicts    -- Precomputed 153-pair conflict matrix
```

---

## Documentation

| Document | Contents |
|----------|----------|
| `CLAUDE.md` | Full developer guide, architecture, anti-patterns, version history |
| `mcp/README.md` | MCP server, 37 tools reference, admin portal API |
| `docs/LESSONS_LEARNED.md` | 15+ issues with root causes and fixes (read before changing anything) |
| `docs/SLACK_INTEGRATION.md` | Slack bot setup, capabilities, formatting |
| `docs/ARCHITECTURE.md` | Full system architecture |
| `docs/TECHNICAL_SPECIFICATION.md` | Complete technical specs |

---

**Built with**: Claude Opus 4.6 | FastAPI | PostgreSQL + pgvector | Redis | Angular 17 | LangSmith
