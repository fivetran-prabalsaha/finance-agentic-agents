# Angular UX Plan — Compliance Agent Configuration Portal
**Version:** 1.0
**Date:** 2026-02-22
**Scope:** Elevated-user configuration review portal backed by the existing MCP/FastAPI server

---

## 1. Objective

Provide elevated users (Controller, VP Finance, IT Director, CFO) with a secure, authenticated
web portal to review and manage all configuration items of the SOD compliance system — SOD rules,
risk thresholds, exceptions, integrations, feature flags, schedules, and audit trails.

---

## 2. All Configuration Items (Grouped by Domain)

### 2.1 AI / LLM Configuration
| Item | Source | Editable |
|---|---|---|
| Anthropic API Key | `ANTHROPIC_API_KEY` env | No (masked, show last 4 chars) |
| Fast model name | `CLAUDE_MODEL_FAST` | Yes |
| Reasoning model name | `CLAUDE_MODEL_REASONING` | Yes |
| Claude API rate limit (req/min) | `CLAUDE_API_RATE_LIMIT` | Yes |
| Token pricing rates (per model) | `utils/token_tracker.py` hardcoded | Read-only display |
| LLM temperature (analyzer) | `agents/analyzer.py` hardcoded `0` | Yes |
| LLM max tokens (analyzer) | `agents/analyzer.py` hardcoded `2048` | Yes |
| LLM timeout (services/llm/base.py) | `120` seconds | Yes |
| LLM max retries | `3` | Yes |
| LLM provider registry | factory.py (8 providers) | Read-only |
| Active embedding provider | `EMBEDDING_PROVIDER` | Yes |
| pgvector dimension | `PGVECTOR_DIMENSION=1536` | Read-only |

### 2.2 Risk Scoring Thresholds
| Item | Source | Editable |
|---|---|---|
| CRITICAL threshold (env) | `CRITICAL_THRESHOLD=90` | Yes |
| HIGH threshold (env) | `HIGH_THRESHOLD=70` | Yes |
| MEDIUM threshold (env) | `MEDIUM_THRESHOLD=40` | Yes |
| CRITICAL threshold (ApprovalService) | hardcoded `75` | Yes |
| HIGH threshold (ApprovalService) | hardcoded `60` | Yes |
| MEDIUM threshold (ApprovalService) | hardcoded `40` | Yes |
| Manager chain max traversal levels | hardcoded `5` | Yes |
| Role similarity threshold (recommendations) | `0.6` | Yes |

### 2.3 SOD Rules (18 Active Rules)
| Item | Source | Editable |
|---|---|---|
| Rule code | `sod_rules` table | No (audit immutable) |
| Rule name | `sod_rules` table | Yes |
| Category | `sod_rules` table | Yes |
| Severity (CRITICAL/HIGH/MEDIUM/LOW) | `sod_rules` table | Yes (with approval) |
| Conflicting permissions (JSON) | `sod_rules` table | Yes (with approval) |
| Is active flag | `sod_rules` table | Yes |
| Rule descriptions | `sod_rules` table | Yes |

### 2.4 Scheduling Configuration
| Item | Source | Editable |
|---|---|---|
| Scan interval (hours) | `SCAN_INTERVAL_HOURS=4` | Yes |
| Scan timezone | `SCAN_TIMEZONE=America/New_York` | Yes |
| Full sync schedule (cron) | `CronTrigger(hour=2, minute=0)` | Yes |
| Incremental sync interval | `IntervalTrigger(hours=1)` | Yes |
| Last sync timestamp | `sync_metadata` table | Read-only |
| Next scheduled scan | APScheduler runtime | Read-only |
| MCP in-memory cache TTL | `60 seconds` | Yes |
| Redis cache default TTL | `86400 seconds` | Yes |

### 2.5 Notification Settings
| Item | Source | Editable |
|---|---|---|
| Notify CRITICAL immediately | `NOTIFY_CRITICAL_IMMEDIATELY=true` | Yes |
| Notify HIGH daily | `NOTIFY_HIGH_DAILY=true` | Yes |
| Notify MEDIUM weekly | `NOTIFY_MEDIUM_WEEKLY=true` | Yes |
| Notify LOW weekly | `NOTIFY_LOW_WEEKLY=true` | Yes |
| Slack channel | `SLACK_CHANNEL=#compliance-alerts` | Yes |
| Slack webhook URL | `SLACK_WEBHOOK_URL` | Yes (masked) |
| SendGrid from email | `SENDGRID_FROM_EMAIL` | Yes |
| SendGrid API key | `SENDGRID_API_KEY` | No (masked) |

### 2.6 NetSuite Integration
| Item | Source | Editable |
|---|---|---|
| Account ID | `NETSUITE_ACCOUNT_ID` | Read-only |
| Realm | `NETSUITE_REALM` | Read-only |
| Consumer Key | `NETSUITE_CONSUMER_KEY` | No (masked) |
| Consumer Secret | `NETSUITE_CONSUMER_SECRET` | No (masked) |
| Token ID | `NETSUITE_TOKEN_ID` | No (masked) |
| Token Secret | `NETSUITE_TOKEN_SECRET` | No (masked) |
| RESTlet URL (main) | `NETSUITE_RESTLET_URL` | Yes |
| RESTlet URL (search) | `NETSUITE_SEARCH_RESTLET_URL` | Yes |
| RESTlet URL (Fivetran) | `NETSUITE_FIVETRAN_RESTLET_URL` | Yes |
| API rate limit (req/sec) | `NETSUITE_API_RATE_LIMIT=10` | Yes |
| Page size | hardcoded `200` | Read-only (documented limit) |

### 2.7 Okta Integration
| Item | Source | Editable |
|---|---|---|
| Okta domain | `OKTA_DOMAIN` | Yes |
| API token | `OKTA_API_TOKEN` | No (masked) |
| Pagination limit | hardcoded `200` | Read-only |
| Request timeout | hardcoded `30` seconds | Yes |

### 2.8 Feature Flags
| Item | Source | Editable |
|---|---|---|
| Enable vector search | `ENABLE_VECTOR_SEARCH=true` | Yes |
| Enable historical analysis | `ENABLE_HISTORICAL_ANALYSIS=true` | Yes |
| Enable ML scoring | `ENABLE_ML_SCORING=false` | Yes |
| Debug mode | `DEBUG=false` | Yes (dev/staging only) |
| Use mock data | `USE_MOCK_DATA=false` | Yes (dev only) |
| Mock users count | `MOCK_USERS_COUNT=50` | Yes (dev only) |
| Mock violations rate | `MOCK_VIOLATIONS_RATE=0.15` | Yes (dev only) |
| Environment | `ENVIRONMENT=development` | Read-only |

### 2.9 Slack Bot Settings
| Item | Source | Editable |
|---|---|---|
| Slack bot token | `SLACK_BOT_TOKEN` | No (masked) |
| Slack app token | `SLACK_APP_TOKEN` | No (masked) |
| Max tokens per response | `SLACK_MAX_TOKENS=1024` | Yes |
| Max history turns | `SLACK_MAX_HISTORY_TURNS=4` | Yes |
| Tool output max chars | `SLACK_TOOL_OUTPUT_MAX_CHARS=2000` | Yes |
| Rolling summary threshold | `SLACK_ROLLING_SUMMARY_MIN_CHARS=800` | Yes |

### 2.10 MCP Server Settings
| Item | Source | Editable |
|---|---|---|
| API key | `MCP_API_KEY` | No (masked) |
| Server host | `MCP_SERVER_HOST=0.0.0.0` | Yes |
| Server port | `MCP_SERVER_PORT=8080` | Yes |
| Allowed CORS origins | `MCP_ALLOWED_ORIGINS` | Yes |
| MCP protocol version | `2024-11-05` hardcoded | Read-only |

### 2.11 Database Configuration
| Item | Source | Editable |
|---|---|---|
| Database URL | `DATABASE_URL` | No (masked) |
| Connection pool size | hardcoded `5` | Yes |
| Max overflow | hardcoded `10` | Yes |
| Redis URL | `REDIS_URL` | No (masked) |

### 2.12 Exception Management Config
| Item | Source | Editable |
|---|---|---|
| All active exceptions | `approved_exceptions` table | Read-only (review mode) |
| Exception review frequencies | per-exception `review_frequency` | Yes |
| Compensating controls library | `compensating_controls` table | Yes |
| Exception violations | `exception_violations` table | Read-only |
| Exceptions due for review | `exception_reviews` table | Read-only |

### 2.13 Approval Authority Matrix
| Item | Source | Editable |
|---|---|---|
| CRITICAL approver roles | `ApprovalService` hardcoded list | Yes |
| HIGH approver roles | `ApprovalService` hardcoded list | Yes |
| MEDIUM approver roles | `ApprovalService` hardcoded list | Yes |
| LOW approver roles | `ApprovalService` hardcoded list | Yes |
| Manager chain max levels | hardcoded `5` | Yes |

---

## 3. Authentication & Authorization Design

### 3.1 Authentication Flow

```
Angular App
    │
    ▼
POST /auth/login  { email, password }
    │
    ▼
FastAPI auth endpoint
    ├── Look up user in NetSuite users table
    ├── Validate password (bcrypt hash)
    ├── Check user status = ACTIVE
    ├── Determine authority level (L1–L5) via ApprovalService
    └── Issue JWT (signed with JWT_SECRET, 8-hour expiry)
         payload: { sub: email, level: 4, roles: [...], exp: ... }
    │
    ▼
Angular stores JWT in memory (NOT localStorage — XSS risk)
All subsequent API calls: Authorization: Bearer <jwt>
    │
    ▼
FastAPI validates JWT on every request
Route guards enforce minimum authority level per section
```

### 3.2 Authorization Levels

| Level | Title | Portal Access |
|---|---|---|
| L3 | Director | Read-only: violations, exceptions, reports |
| L4 | Controller / VP Finance / IT Director | Read + edit thresholds, notifications, schedules, SOD rule severity |
| L5 | CFO / C-Suite | Full access including API key rotation and feature flags |

### 3.3 Route Guards

| Route | Minimum Level |
|---|---|
| `/dashboard` | L3 |
| `/violations` | L3 |
| `/exceptions` | L3 |
| `/sod-rules` | L3 (read) / L4 (edit) |
| `/configuration/thresholds` | L4 |
| `/configuration/notifications` | L4 |
| `/configuration/scheduling` | L4 |
| `/configuration/integrations` | L4 (read) / L5 (edit) |
| `/configuration/feature-flags` | L5 |
| `/configuration/llm` | L5 |
| `/audit-trail` | L4 |
| `/token-analytics` | L4 |

---

## 4. Angular Application Architecture

### 4.1 Tech Stack

```
Frontend:        Angular 17+ (standalone components, signals)
UI Library:      Angular Material 17
HTTP:            Angular HttpClient + interceptors
Auth:            JWT (in-memory), HTTP-only cookie option for production
State:           Angular Signals + Services (no NgRx — overkill for this scope)
Charts:          ng2-charts (Chart.js wrapper) for violation trends, token costs
Forms:           Angular Reactive Forms
Routing:         Angular Router with auth guards
Styling:         Angular Material theming + SCSS
Build:           Angular CLI
```

### 4.2 Folder Structure

```
angular-portal/
├── src/
│   ├── app/
│   │   ├── core/
│   │   │   ├── auth/
│   │   │   │   ├── auth.service.ts          # Login, JWT management, user context
│   │   │   │   ├── auth.guard.ts            # Route guard (level check)
│   │   │   │   └── jwt.interceptor.ts       # Attach Bearer token to all requests
│   │   │   ├── services/
│   │   │   │   ├── config.service.ts        # Read/write config items via API
│   │   │   │   ├── violations.service.ts    # Violation data
│   │   │   │   ├── exceptions.service.ts    # Exception data
│   │   │   │   ├── sod-rules.service.ts     # SOD rules CRUD
│   │   │   │   └── audit.service.ts         # Audit trail
│   │   │   └── models/                      # TypeScript interfaces (mirror DB models)
│   │   │
│   │   ├── features/
│   │   │   ├── login/                       # Login page
│   │   │   ├── dashboard/                   # System overview + health
│   │   │   ├── violations/                  # Violation list, filters, details
│   │   │   ├── exceptions/                  # Exception list, reviews due
│   │   │   ├── sod-rules/                   # SOD rule viewer/editor
│   │   │   ├── configuration/
│   │   │   │   ├── thresholds/              # Risk score thresholds
│   │   │   │   ├── notifications/           # Alert settings
│   │   │   │   ├── scheduling/              # Sync intervals, scan schedule
│   │   │   │   ├── integrations/            # NetSuite, Okta, Slack config
│   │   │   │   ├── feature-flags/           # Feature toggles
│   │   │   │   └── llm/                     # Model selection, token limits
│   │   │   ├── audit-trail/                 # Audit log viewer
│   │   │   └── token-analytics/             # LLM usage + cost dashboard
│   │   │
│   │   ├── shared/
│   │   │   ├── components/
│   │   │   │   ├── masked-field/            # Show/hide for API keys
│   │   │   │   ├── severity-badge/          # CRITICAL/HIGH/MEDIUM/LOW chips
│   │   │   │   ├── confirm-dialog/          # Confirmation before saving changes
│   │   │   │   └── status-indicator/        # Green/red health dots
│   │   │   └── pipes/
│   │   │       └── mask.pipe.ts             # Mask credential strings
│   │   │
│   │   └── app.routes.ts                    # All route definitions with guards
│   │
│   ├── environments/
│   │   ├── environment.ts                   # { apiUrl: 'http://localhost:8080' }
│   │   └── environment.prod.ts
│   └── styles/                              # Global SCSS, Material theme
```

### 4.3 Key Screens

#### Screen 1: Dashboard
- System health cards (NetSuite ✅, Okta ✅, MCP Server ✅)
- Last sync time + next scheduled sync
- Violations summary: total / by severity (donut chart)
- Exceptions due for review (alert badge)
- Recent audit trail events (last 10)
- Token usage this month + estimated cost

#### Screen 2: SOD Rules
- Table of all 18 rules: code, name, category, severity, active toggle
- Click row → detail panel: conflicting permissions, description, violation count
- L4+: edit severity, toggle active/inactive, edit description
- Change requires confirmation dialog + writes to `audit_trail`

#### Screen 3: Violations
- Filterable table: severity, department, status, date range
- Export button (CSV/Excel via `generate_violation_report` tool)
- Click row → full violation detail: user, roles, rule triggered, risk score, history
- Status update: OPEN → IN_REVIEW → RESOLVED

#### Screen 4: Exceptions
- Active exceptions list with expiry dates, review frequency, next review date
- "Due for Review" tab — exceptions where `next_review_date <= today`
- Effectiveness stats: cost, violations prevented, ROI
- Detail view: compensating controls, control implementation status

#### Screen 5: Configuration — Thresholds
- Slider/number inputs for CRITICAL, HIGH, MEDIUM score cutoffs
- Two threshold sets: env-based (scan alerts) + ApprovalService (approval routing)
- Visual: color-coded risk band diagram updates live as sliders move
- Save → writes via `/config/thresholds` API → updates env + restarts affected service

#### Screen 6: Configuration — Integrations
- NetSuite section: account ID, RESTlet URLs (editable), credentials (masked, rotate button)
- Okta section: domain, timeout
- Slack section: channel, webhook URL (masked)
- "Test Connection" button per integration → calls MCP `list_systems` and shows result

#### Screen 7: Configuration — Scheduling
- Cron expression editor for full sync (with human-readable preview)
- Interval slider for incremental sync
- Cache TTL inputs (Redis, MCP in-memory)
- "Run Now" button → calls `trigger_manual_sync`

#### Screen 8: Configuration — Feature Flags
- Toggle list for all boolean flags
- Environment badge (only show mock flags in dev/staging)
- Flags that affect production get a ⚠️ warning before toggling

#### Screen 9: Configuration — LLM
- Model dropdowns for FAST and REASONING models
- Temperature, max tokens, timeout sliders
- Token usage trend chart (last 30 days, by model)
- Cost breakdown by agent (Slack bot, Analyzer, Risk Assessor, Report Generator)

#### Screen 10: Audit Trail
- Paginated log: timestamp, actor, entity, action, changes (JSON diff)
- Filter by actor, entity type, date range
- Export to CSV

---

## 5. Backend Changes Required (FastAPI)

New endpoints needed on the existing MCP server (or a separate admin API):

```
POST   /auth/login                    # Issue JWT
GET    /auth/me                       # Current user info + authority level

GET    /admin/config                  # All non-secret config items
PATCH  /admin/config/thresholds       # Update risk thresholds
PATCH  /admin/config/notifications    # Update notification settings
PATCH  /admin/config/scheduling       # Update sync schedule + cache TTL
PATCH  /admin/config/feature-flags    # Toggle feature flags
PATCH  /admin/config/llm              # Update model names, token limits
PATCH  /admin/config/integrations     # Update RESTlet URLs, Slack channel
POST   /admin/config/test-connection  # Test integration connectivity

GET    /admin/sod-rules               # All 18 SOD rules
PATCH  /admin/sod-rules/{id}          # Edit rule (severity, description, active)

GET    /admin/violations              # Paginated violations with filters
PATCH  /admin/violations/{id}/status  # Update violation status

GET    /admin/exceptions              # Paginated exceptions
GET    /admin/exceptions/due-review   # Exceptions due for review

GET    /admin/audit-trail             # Paginated audit log
GET    /admin/token-analytics         # Token usage + cost by agent + model

GET    /admin/system-health           # Health of all integrations
```

All `/admin/*` routes protected by:
1. JWT validation (existing `JWT_SECRET`)
2. Minimum authority level check (from token payload)
3. All writes create an `AuditTrail` record

---

## 6. Implementation Phases

### Phase 1 — Foundation (Week 1-2)
- [ ] Angular project setup (CLI, Material, routing)
- [ ] Auth service + JWT interceptor + login screen
- [ ] FastAPI `/auth/login` + `/auth/me` endpoints
- [ ] Dashboard screen (read-only health + violation summary)
- [ ] Auth guard with L3/L4/L5 level enforcement

### Phase 2 — Read-Only Config Review (Week 3-4)
- [ ] SOD Rules screen (read-only)
- [ ] Violations screen with filters + export
- [ ] Exceptions screen with review status
- [ ] Configuration screens (all read-only, masked credentials)
- [ ] Audit Trail screen

### Phase 3 — Editable Configuration (Week 5-6)
- [ ] Threshold editor (sliders + validation)
- [ ] Notification settings form
- [ ] Scheduling editor (cron + intervals)
- [ ] Feature flags toggles
- [ ] All writes with confirmation dialog + audit trail

### Phase 4 — Advanced (Week 7-8)
- [ ] LLM config + token analytics charts
- [ ] SOD rule severity editing (with approval gate)
- [ ] Integration test-connection buttons
- [ ] Credential rotation UX (masked fields + rotate button)
- [ ] Export functionality (CSV/Excel)

---

## 7. Security Considerations

| Concern | Mitigation |
|---|---|
| JWT storage | Store in memory only (not localStorage/sessionStorage) — survives page refresh via `/auth/me` call |
| Credential display | All API keys/secrets masked with `****`. Show-last-4 only. Separate "Rotate" flow to update |
| CSRF | JWT in Authorization header (not cookie) eliminates CSRF risk |
| CORS | MCP server `MCP_ALLOWED_ORIGINS` restricted to portal domain |
| Audit trail | Every write via admin API creates an `AuditTrail` record with actor + diff |
| Sensitive flags | Dev-only flags (mock data, debug) hidden when `ENVIRONMENT=production` |
| Config changes | Threshold and SOD rule severity changes require L4+ and show a confirmation dialog with impact summary before saving |
