# MCP Server

**Version**: 3.0.0 | **Status**: Production | **Last Updated**: 2026-04-12

FastAPI server implementing MCP JSON-RPC 2.0 with 37 compliance tools and a JWT-authenticated admin portal.

---

## Quick Start

```bash
# Start (from compliance-agent root)
./scripts/restart_mcp.sh

# Verify
curl http://localhost:8080/health
# → {"status":"healthy","service":"compliance-mcp-server","tools":37}

# List tools
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-12345" \
  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}' | python3 -m json.tool
```

---

## Architecture

```
┌────────────────────────────────────────────────┐
│  Slack Bot / Shared Gateway :8090              │
└──────────────────┬─────────────────────────────┘
                   │ MCP JSON-RPC 2.0 (POST /mcp)
                   ▼
┌────────────────────────────────────────────────┐
│  mcp_server.py  :8080                         │
│  • 37 tools via /mcp endpoint                 │
│  • Admin portal via /auth + /admin endpoints  │
│  • CORS: localhost, localhost:4200 (Angular)  │
│  • Auth: X-API-Key or Authorization: Bearer   │
└──────────┬─────────────────────────────────────┘
           │
    ┌──────┴──────┐
    ▼             ▼
mcp_tools.py  admin_api.py
(37 tools)    (16 endpoints, JWT)
    │
    ▼
orchestrator.py → PostgreSQL / NetSuite RESTlet
```

---

## Files

| File | Purpose |
|------|---------|
| `mcp_server.py` | FastAPI app, MCP protocol handler, CORS, router mounting |
| `mcp_tools.py` | All 37 tool schemas and async handlers |
| `admin_api.py` | JWT auth + admin configuration endpoints |
| `orchestrator.py` | Routes tool calls to agents, connectors, and DB |
| `RESPONSE_STYLE_GUIDE.md` | Response formatting rules (concise, actionable, 10-15 lines max) |

---

## MCP Endpoint

```
POST /mcp
Headers:
  Content-Type: application/json
  X-API-Key: <api-key>          # or Authorization: Bearer <key>
Body: JSON-RPC 2.0
```

### Supported methods

| Method | Description |
|--------|-------------|
| `tools/list` | Returns all 37 tool schemas |
| `tools/call` | Execute a tool |
| `initialize` | MCP handshake |
| `ping` | Liveness check |

---

## 37 Tools Reference

### Discovery

#### `list_systems`
List available systems with connection status and user counts.
```json
{"name": "list_systems", "arguments": {}}
```

#### `list_all_users`
List users with optional department filter.
```json
{"name": "list_all_users", "arguments": {"department": "Finance", "limit": 50}}
```

#### `get_user_violations`
Get all violations for a specific user.
```json
{"name": "get_user_violations", "arguments": {"user_identifier": "john@company.com"}}
```

---

### Analysis

#### `perform_access_review`
Full SOD compliance review for a system or department.
```json
{
  "name": "perform_access_review",
  "arguments": {"system_name": "netsuite", "analysis_type": "sod_violations"}
}
```

#### `analyze_access_request`
Pre-assignment analysis — check if adding a role creates violations.
```json
{
  "name": "analyze_access_request",
  "arguments": {"user_identifier": "john@company.com", "requested_role": "Controller"}
}
```

#### `get_role_conflicts`
Role pair conflict matrix for specific roles.
```json
{"name": "get_role_conflicts", "arguments": {"role_names": ["Controller", "AP Clerk"]}}
```

#### `get_role_risk_matrix`
Precomputed conflict matrix for all 17 Fivetran roles (153 pairs). Supports `role_name`, `severity`, `intra`, `cross` filters. Cached 24h.
```json
{"name": "get_role_risk_matrix", "arguments": {"severity": "CRITICAL"}}
```

---

### Violations

#### `list_violations`
Paginated violations with department/severity filters. DISTINCT ON deduplication.
```json
{"name": "list_violations", "arguments": {"severity": "HIGH", "department": "Finance"}}
```

#### `get_violation_stats`
Aggregate violation counts grouped by severity, department, or rule.
```json
{"name": "get_violation_stats", "arguments": {"time_range": "month"}}
```

#### `get_violation_summary`
Human-readable violation summary grouped by severity for reporting.
```json
{"name": "get_violation_summary", "arguments": {}}
```

---

### Exceptions

#### `list_active_exceptions`
All currently approved SOD exceptions with expiry dates.

#### `request_exception_approval`
Submit a new SOD exception request with business justification.

#### `approve_exception`
Approve a pending exception (L4+ authority required).

---

### SOD Rules

#### `list_sod_rules`
All 18 active SOD rules with severity and risk category.

#### `check_sod_rule`
Check if a specific permission combination violates a rule.

#### `get_sod_rule_details`
Full details for a specific rule including remediation guidance.

---

### Reporting

#### `get_daily_report`
Full structured daily digest (JSON) — violations, metrics, recommendations.

#### `generate_compliance_report`
Executive compliance report for a time period.

#### `get_org_risk_assessment`
Organisation-wide risk posture summary.

#### `export_report`
Export a report (CSV/Excel). Google Sheets export: not yet implemented.

---

### Remediation

#### `remediate_violation`
Create a remediation plan for a specific violation.
```json
{
  "name": "remediate_violation",
  "arguments": {"violation_id": "uuid", "action": "remove_role", "notes": "..."}
}
```

#### `get_remediation_plan`
Fetch a previously generated remediation plan.

---

### Knowledge Base

#### `search_knowledge_base`
Semantic search over compliance policies and SOX guidance (pgvector).

#### `get_compensating_controls`
Retrieve compensating control recommendations for a violation type.

---

### Admin / System

#### `trigger_manual_sync`
Trigger a full or incremental NetSuite data sync.
```json
{"name": "trigger_manual_sync", "arguments": {"sync_type": "full"}}
```

#### `get_collection_agent_status`
Background sync agent status, last run time, success/error counts.

#### `check_my_approval_authority`
Returns the caller's NetSuite authority level (L3/L4/L5) and what they can approve.

---

## Admin Portal API (`admin_api.py`)

Mounted on the same FastAPI app. Requires JWT from `POST /auth/login`.

**Authority levels** (from NetSuite roles):
- **L3** (Director): read-only
- **L4** (Controller/VP): read + edit thresholds, rules, notifications, scheduling
- **L5** (CFO): full access including feature flags and LLM config

### Auth endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/login` | Issue JWT (L3+ required) |
| `GET` | `/auth/me` | Current user + authority level |

### Admin endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/admin/system-health` | L3+ | Integration health check |
| `GET` | `/admin/config` | L3+ | All non-secret config items |
| `PATCH` | `/admin/config/thresholds` | L4+ | Edit risk thresholds |
| `PATCH` | `/admin/config/notifications` | L4+ | Edit alert settings |
| `PATCH` | `/admin/config/scheduling` | L4+ | Edit sync schedules |
| `PATCH` | `/admin/config/feature-flags` | L5 | Toggle feature flags |
| `PATCH` | `/admin/config/llm` | L5 | Edit LLM model config |
| `GET` | `/admin/sod-rules` | L3+ | View all 18 SOD rules |
| `PATCH` | `/admin/sod-rules` | L4+ | Edit SOD rule severity |
| `GET` | `/admin/violations` | L3+ | Paginated violations |
| `PATCH` | `/admin/violations` | L4+ | Update violation status |
| `GET` | `/admin/exceptions` | L3+ | Active exceptions |
| `GET` | `/admin/exceptions/due-review` | L3+ | Overdue exceptions |
| `GET` | `/admin/audit-trail` | L3+ | Audit log |
| `GET` | `/admin/token-analytics` | L4+ | LLM cost/usage summary |

### Required env vars for admin portal

```bash
JWT_SECRET=<long-random-string>          # Required for JWT signing
ADMIN_PORTAL_PASSWORD=<portal-password>  # Portal login (dev)
JWT_EXPIRE_HOURS=8                       # Optional, default 8h
```

---

## CORS Configuration

Allowed origins are controlled by `MCP_ALLOWED_ORIGINS` env var (comma-separated).
Default: `http://localhost` and `http://localhost:4200` (Angular dev server).

```bash
# Production: restrict to your actual frontend origin
MCP_ALLOWED_ORIGINS=https://compliance.yourcompany.com
```

---

## Semantic Tool Router

The Slack bot uses `utils/semantic_router.py` (not this server) to pre-filter which tools to send Claude. To register a new tool:

1. Add tool schema/handler to `mcp_tools.py`
2. Add to `TOOL_GROUPS` in `utils/tool_router.py` (keyword fallback)
3. Add to `TOOL_EXEMPLARS` in `utils/semantic_router.py` with description + 3–5 example queries

Without step 3, the tool will never appear in Claude's shortlist.

---

## Environment Variables

```bash
# Required
DATABASE_URL=postgresql://user:pass@localhost:5432/compliance_db
ANTHROPIC_API_KEY=sk-ant-...
NETSUITE_ACCOUNT_ID=...
NETSUITE_CONSUMER_KEY=...
NETSUITE_CONSUMER_SECRET=...
NETSUITE_TOKEN_KEY=...
NETSUITE_TOKEN_SECRET=...
NETSUITE_RESTLET_URL=https://...

# Optional
REDIS_URL=redis://localhost:6379/0
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8080
MCP_API_KEY=dev-key-12345              # Change in production
MCP_ALLOWED_ORIGINS=http://localhost   # Comma-separated origins

# Admin portal
JWT_SECRET=<long-random-string>
ADMIN_PORTAL_PASSWORD=<portal-password>
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Server won't start | Port 8080 in use | `lsof -ti:8080 \| xargs kill -9` |
| `401 Unauthorized` | Wrong API key | Check `MCP_API_KEY` in `.env` |
| Tools fail with DB errors | PostgreSQL not running | `brew services start postgresql@16` |
| Admin login fails | `JWT_SECRET` not set | Add to `.env`, restart server |
| Angular CORS error | Origin not in allowed list | Set `MCP_ALLOWED_ORIGINS` in `.env` |
| Tool not selected by Slack bot | Not in `TOOL_EXEMPLARS` | Add entry to `utils/semantic_router.py` |

---

**Author**: Prabal Saha | **Version**: 3.0.0 | **Date**: 2026-04-12
