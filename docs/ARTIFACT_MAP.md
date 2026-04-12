# Compliance Agent — Artifact Map

> One-stop reference: every file, what it does, what it depends on, and when it runs.
>
> **Date:** 2026-02-27
> **Project version:** 1.6 (CLAUDE.md)
> **Tool count:** 37 MCP tools operational

## How to Read This Map

- **Runtime path**: which process owns this file (MCP server / Slack bot / analysis job / migration)
- **Depends on**: other files this artifact imports or requires to be in a certain state
- **Used by**: what calls or reads this file

Every new MCP tool must be registered in **both** `mcp/mcp_tools.py` (handler + schema) and `utils/tool_router.py` (intent group). Skipping `tool_router.py` means Claude will never see the tool because the router pre-filters the tool list before each query.

---

## 1. Entry Points

These are the four top-level processes. Each can run independently.

### `slack_bot_local.py`

| Field | Value |
|---|---|
| **Runtime path** | Slack bot process (long-running, Socket Mode WebSocket) |
| **Language / framework** | Python; `slack-bolt` + `langchain-anthropic` |
| **Starts via** | `python slack_bot_local.py` |
| **Depends on** | `mcp/mcp_server.py` (HTTP), `utils/tool_router.py`, `models/conversation_summary.py`, `models/answer_feedback.py`, Anthropic API, Redis, PostgreSQL, LangSmith |
| **Used by** | Slack workspace users via `@mention` or DM |

The Slack bot is the primary human-facing entry point. It handles Slack events (mentions, DMs, button actions), drives the multi-turn agentic Claude loop, caches MCP tool results in Redis, writes conversation summaries and answer feedback to PostgreSQL, and ships every trace to LangSmith. All user-facing compliance queries flow through this file.

---

### `mcp/mcp_server.py`

| Field | Value |
|---|---|
| **Runtime path** | MCP server process (long-running, port 8080) |
| **Language / framework** | Python; FastAPI + Uvicorn |
| **Starts via** | `python3 -m mcp.mcp_server` or `./scripts/restart_mcp.sh` |
| **Depends on** | `mcp/mcp_tools.py`, `mcp/admin_api.py`, `models/database_config.py` |
| **Used by** | `slack_bot_local.py` (HTTP POST `/mcp`), Claude Desktop (via STDIO bridge at `/Users/prabal.saha/mcp_stdio_http_bridge.py`), Angular portal frontend |

FastAPI application that implements the MCP JSON-RPC 2.0 protocol. Exposes two key routes:

- `POST /mcp` — tool discovery (`tools/list`) and tool execution (`tools/call`)
- `/auth/*` and `/admin/*` — JWT-protected admin REST API (mounted from `admin_api.py`)

CORS is controlled via `MCP_ALLOWED_ORIGINS` env var; defaults allow `localhost` and `localhost:4200` (Angular dev server). The `DataCollectionAgent` APScheduler is started in the FastAPI startup event, so the sync agent runs inside the MCP server process.

---

### `scripts/build_role_risk_matrix.py`

| Field | Value |
|---|---|
| **Runtime path** | One-shot analysis job (run manually or after full sync) |
| **Language / framework** | Pure Python; no web framework |
| **Starts via** | `cd compliance-agent && python3 scripts/build_role_risk_matrix.py` |
| **Depends on** | `models/database_config.py`, PostgreSQL tables `sod_rules`, `roles`, `sod_permission_map`, `role_pair_conflicts` |
| **Used by** | Run by engineers after a full NetSuite sync or when SOD rules change |

Builds the precomputed SOD conflict matrix for all 17 Fivetran custom roles (153 unique cross-role pairs + 17 intra-role combinations). Executes migrations 008 and 009 idempotently, seeds `sod_permission_map` with the abstract-to-NetSuite permission name mappings, then iterates every role pair using level-aware logic (`None < View < Create < Edit < Full`) and upserts results into `role_pair_conflicts` (443 rows). Re-running is always safe due to the `ON CONFLICT DO UPDATE` (upsert) constraint. Must be re-run whenever: (a) NetSuite roles gain new permissions, (b) SOD rules change, or (c) new Fivetran roles are added.

---

### `mcp/admin_api.py`

| Field | Value |
|---|---|
| **Runtime path** | Mounted on the MCP server process (no separate process) |
| **Language / framework** | FastAPI `APIRouter`; `python-jose` for JWT |
| **Depends on** | `models/database_config.py`, `services/approval_service.py`, `python-jose[cryptography]`, `passlib[bcrypt]` |
| **Used by** | Angular portal (`angular-portal/`) via dev proxy; mounted by `mcp/mcp_server.py` |

Provides 16 JWT-authenticated REST endpoints for the Angular configuration portal. Authority levels are derived from NetSuite role keywords stored in the JWT claims: L3 (Director) = read-only, L4 (Controller/VP) = read + edit thresholds/rules/notifications/scheduling, L5 (CFO) = full access including feature flags and LLM config. Key env vars: `JWT_SECRET`, `ADMIN_PORTAL_PASSWORD`, `JWT_EXPIRE_HOURS` (default 8).

Endpoints:

| Endpoint | Authority |
|---|---|
| `POST /auth/login` | Public |
| `GET /auth/me` | L3+ |
| `GET /admin/system-health` | L3+ |
| `GET /admin/config` | L3+ |
| `PATCH /admin/config/thresholds\|notifications\|scheduling\|feature-flags\|llm` | L4+/L5 |
| `GET/PATCH /admin/sod-rules` | L4+ |
| `GET/PATCH /admin/violations` | L3+ / L4+ |
| `GET /admin/exceptions` + `/due-review` | L3+ |
| `GET /admin/audit-trail` | L3+ |
| `GET /admin/token-analytics` | L3+ |

---

## 2. MCP Tools Layer

All tools are defined in `mcp/mcp_tools.py`. The file contains: (a) `TOOL_SCHEMAS` dict (JSON schema for each tool), (b) async handler functions (one per tool), and (c) `TOOL_HANDLERS` dict mapping names to handlers. The helper `get_orchestrator()` is `lru_cache(maxsize=1)` — the `ComplianceOrchestrator` singleton is created once at server startup.

### Access Review Tools

| Tool name | One-line description | DB tables / services |
|---|---|---|
| `list_systems` | Lists all available compliance systems with status and user counts | `users`, `sync_metadata` |
| `perform_access_review` | Full system audit: SOD violations, excessive permissions, inactive users across ALL users (heavyweight) | `users`, `violations`, `compliance_scans`, NetSuite |
| `get_user_violations` | SOD violations for a specific user (by email or name) with optional AI analysis | `users`, `violations`, `sod_rules`, Anthropic API |
| `analyze_access_request` | Evaluates whether a role assignment is safe given a user's current roles; always analyzes ALL roles combined | `users`, `roles`, `sod_rules`, `job_role_mappings`, Anthropic API |
| `validate_job_role` | Checks whether a user's job title and roles are an acceptable combination per `job_role_mappings` | `job_role_mappings`, `users` |
| `list_all_users` | Paginated user list with optional department/status filter (`filter_by_department` param) | `users`, `user_roles`, `roles` |

### Violation Query Tools

| Tool name | One-line description | DB tables / services |
|---|---|---|
| `get_violation_stats` | Aggregated violation statistics (counts by severity, status, department) | `violations`, `users` |
| `list_violations` | Filtered violation listing with `department`, `severity`, and `roles_only` params; uses `DISTINCT ON (user_id, rule_id)` deduplication | `violations`, `users`, `sod_rules` |
| `remediate_violation` | Records a remediation action against a specific violation | `violations` |
| `schedule_review` | Schedules a future access review for a user | `compliance_scans` |

### Role Risk Tools (NEW — 2026-02-27)

| Tool name | One-line description | DB tables / services |
|---|---|---|
| `get_role_risk_matrix` | Queries the precomputed role-pair conflict matrix; supports `role_name`, `severity`, `intra_only`, `cross_only` filters; cached 24 h in Redis | `role_pair_conflicts`, `sod_permission_map`, Redis |
| `get_role_conflicts` | Returns SOD conflicts for a single named role against all other roles | `role_pair_conflicts`, `roles` |
| `analyze_role_permissions` | Deep permission-level analysis for one role, including intra-role conflicts | `roles`, `sod_rules`, `sod_permission_map` |
| `recommend_roles_for_job_title` | Recommends low-conflict role combinations for a given job title | `job_role_mappings`, `role_pair_conflicts` |

### Exception Management Tools

| Tool name | One-line description | DB tables / services |
|---|---|---|
| `record_exception_approval` | Records a newly approved SOD exception with compensating controls | `approved_exceptions`, `exception_controls` |
| `find_similar_exceptions` | pgvector similarity search for precedent exceptions | `approved_exceptions` (vector column) |
| `get_exception_details` | Full detail for one exception including controls and review history | `approved_exceptions`, `exception_controls`, `exception_reviews` |
| `list_approved_exceptions` | Paginated list of exceptions with status/user filters | `approved_exceptions` |
| `record_exception_violation` | Records that a compensating control failed or was violated | `exception_violations` |
| `get_exception_effectiveness_stats` | Aggregated exception effectiveness metrics | `approved_exceptions`, `exception_violations` |
| `detect_exception_violations` | Scans active exceptions to detect controls that have lapsed | `approved_exceptions`, `exception_controls`, `violations` |
| `conduct_exception_review` | Processes a periodic review decision (continue/modify/revoke/escalate) | `exception_reviews`, `approved_exceptions` |
| `get_exceptions_for_review` | Lists exceptions due for periodic review | `approved_exceptions` |

### SOD Rules Tools

| Tool name | One-line description | DB tables / services |
|---|---|---|
| `query_sod_rules` | Text/semantic search across SOD rules | `sod_rules` (pgvector) |
| `check_permission_conflict` | Checks whether two specific permission names conflict under any active rule | `sod_rules` |
| `get_permission_categories` | Returns the taxonomy of permission categories | `sod_rules` |
| `search_permissions` | Free-text search across all known permissions | `roles` (JSON permissions column) |

### Reporting Tools

| Tool name | One-line description | DB tables / services |
|---|---|---|
| `generate_violation_report` | Generates a formatted compliance report (PDF-ready text) for a user, department, or full org | `violations`, `users`, `sod_rules`, Anthropic API |

### Exception RBAC / Approval Workflow Tools

| Tool name | One-line description | DB tables / services |
|---|---|---|
| `initialize_session` | Resolves user email to profile, approval authority level, and active roles | `users`, `approved_exceptions` |
| `check_my_approval_authority` | Returns whether caller can approve exceptions at a given risk score | `users` (role → authority mapping) |
| `request_exception_approval` | Creates a new exception approval request with RBAC validation; auto-approves if requester has authority | `approved_exceptions`, `exception_controls`, Jira (optional) |

### Knowledge Base Tools

| Tool name | One-line description | DB tables / services |
|---|---|---|
| `query_knowledge_base` | Semantic (RAG) search over compliance policy documents | `context_catalogue` (pgvector), Anthropic/OpenAI embeddings |
| `get_compensating_controls` | Returns recommended compensating controls for a given risk pattern | `compensating_controls`, `context_catalogue` |

### System / Sync Tools

| Tool name | One-line description | DB tables / services |
|---|---|---|
| `start_collection_agent` | Starts the background APScheduler data collection agent | `sync_metadata` |
| `stop_collection_agent` | Stops the background data collection agent | `sync_metadata` |
| `get_collection_agent_status` | Returns current agent status and last sync metrics | `sync_metadata` |
| `trigger_manual_sync` | Immediately triggers a full or incremental NetSuite sync; busts all `mcp:*` Redis cache keys on success | `sync_metadata`, `users`, `roles`, NetSuite, Redis |

---

## 3. Database Layer

PostgreSQL 14+ with the `pgvector` extension. Connection managed via `DATABASE_URL` env var and `models/database_config.py`.

### Core Tables (defined in `models/database.py`)

#### `users`

| Field | Detail |
|---|---|
| **Purpose** | NetSuite users synced from the RESTlet API |
| **Key columns** | `user_id` (NS internal ID), `email`, `status`, `department`, `job_function`, `title`, `supervisor`, `hire_date` |
| **Populated by** | `agents/data_collector.py` → `repositories/user_repository.py` |
| **Queried by** | Nearly every MCP tool handler; `initialize_session`, `get_user_violations`, `list_all_users`, `analyze_access_request` |

#### `roles`

| Field | Detail |
|---|---|
| **Purpose** | NetSuite role definitions including full permissions JSON |
| **Key columns** | `role_id`, `role_name`, `is_custom`, `permissions` (JSON), `embedding` (Vector 384) |
| **Populated by** | `agents/data_collector.py` → `repositories/role_repository.py` |
| **Queried by** | `analyze_access_request`, `analyze_role_permissions`, `get_role_conflicts`, `search_permissions`, `build_role_risk_matrix.py` |
| **Notes** | `embedding` column uses pgvector for semantic role search |

#### `user_roles`

| Field | Detail |
|---|---|
| **Purpose** | Many-to-many join table between `users` and `roles` |
| **Key columns** | `user_id` (FK → `users`), `role_id` (FK → `roles`), `assigned_at`, `assigned_by` |
| **Populated by** | `agents/data_collector.py` |
| **Queried by** | `get_user_violations`, `analyze_access_request`, `list_all_users` |

#### `violations`

| Field | Detail |
|---|---|
| **Purpose** | Detected SOD violations; one row per (user, rule) pair per scan |
| **Key columns** | `user_id`, `rule_id`, `scan_id`, `severity` (enum), `status` (enum), `risk_score`, `conflicting_roles` (JSON), `embedding` (Vector 384) |
| **Populated by** | `agents/analyzer.py` → `repositories/violation_repository.py` |
| **Queried by** | `get_user_violations`, `list_violations`, `get_violation_stats`, `generate_violation_report` |
| **Notes** | `DISTINCT ON (user_id, rule_id)` used in `list_violations` to deduplicate multi-scan rows. `embedding` enables `find_similar_exceptions` semantic search |

#### `compliance_scans`

| Field | Detail |
|---|---|
| **Purpose** | Scan execution history; parent record that violations reference via FK |
| **Key columns** | `id`, `scan_type`, `status`, `users_scanned`, `violations_found`, `violations_critical/high/medium/low` |
| **Populated by** | `agents/analyzer.py` (creates record before inserting violations — see LESSONS_LEARNED Issue #15) |
| **Queried by** | `perform_access_review`, `get_collection_agent_status` |
| **Critical note** | A `compliance_scans` record MUST exist before any `violations` row with that `scan_id` is inserted |

#### `sync_metadata`

| Field | Detail |
|---|---|
| **Purpose** | Tracks each NetSuite sync job (timing, record counts, errors) |
| **Key columns** | `sync_type` (FULL/INCREMENTAL/MANUAL), `system_name`, `status`, `users_synced`, `violations_detected`, `extra_metadata` (column named `metadata` in DB) |
| **Populated by** | `agents/data_collector.py` → `repositories/sync_metadata_repository.py` |
| **Queried by** | `get_collection_agent_status`, `trigger_manual_sync`, `check_mcp_status.sh` |
| **Critical note** | Column is named `metadata` in the database but `extra_metadata` in the ORM attribute to avoid SQLAlchemy's reserved `metadata` name — see LESSONS_LEARNED Issue #1 |

#### `sod_rules`

| Field | Detail |
|---|---|
| **Purpose** | The 18 active SOD rules defining which permission pairs conflict |
| **Key columns** | `rule_id` (e.g. `SOD-FIN-001`), `rule_name`, `category`, `conflicting_permissions` (JSON), `severity`, `is_active`, `embedding` (Vector 384) |
| **Populated by** | `database/seed_data/sod_rules.json` loaded by `scripts/seed_sod_configurations.py` |
| **Queried by** | `agents/analyzer.py`, `query_sod_rules`, `check_permission_conflict`, `build_role_risk_matrix.py` |
| **Notes** | `embedding` enables semantic rule search in `query_knowledge_base` |

#### `sod_permission_map` (NEW — migration 008)

| Field | Detail |
|---|---|
| **Purpose** | Rosetta-stone table mapping abstract SOD rule permission names to actual NetSuite `permission_name` strings and the minimum level at which each side of a conflict fires |
| **Key columns** | `rule_id` (FK → `sod_rules`), `conflict_index`, `side` (`left`/`right`), `abstract_name`, `ns_permission`, `min_level` (`View`/`Create`/`Edit`/`Full`) |
| **Populated by** | `scripts/build_role_risk_matrix.py` (seeded from `PERMISSION_MAP_SEED` constant) |
| **Queried by** | `scripts/build_role_risk_matrix.py` when computing role pair conflicts; `get_role_risk_matrix` handler |

#### `role_pair_conflicts` (NEW — migration 009)

| Field | Detail |
|---|---|
| **Purpose** | Precomputed SOD conflict matrix; one row per directional (permission-pair, rule, role-pair) conflict |
| **Key columns** | `role_a_id`, `role_b_id` (normalised alphabetically), `rule_id`, `severity`, `role_a_permission`, `role_a_level`, `role_b_permission`, `role_b_level`, `is_intra_role` |
| **Populated by** | `scripts/build_role_risk_matrix.py` (443 rows for 17 Fivetran roles) |
| **Queried by** | `get_role_risk_matrix` handler (cached 24 h), `get_role_conflicts` handler |
| **Notes** | Pairs are normalised so `role_a_id <= role_b_id` alphabetically; intra-role rows have `role_a_id = role_b_id` |

### Memory / Feedback Tables (migrations 006, 007)

#### `conversation_summaries` (migration 006)

| Field | Detail |
|---|---|
| **Purpose** | Phase B memory: Haiku-generated 2-3 sentence summaries of past DM exchanges; injected as prior context (~150 tokens vs ~2K raw history) |
| **Key columns** | `user_email`, `channel_id`, `summary`, `topics` (TEXT[]), `outcome` (APPROVED/DENIED/ESCALATED/INFO), `expires_at` (90 days) |
| **Populated by** | `slack_bot_local.py` → `_write_conversation_summary()` (non-blocking `threading.Thread`) |
| **Queried by** | `slack_bot_local.py` → `_get_prior_summaries()` at the start of each DM |
| **Feature flag** | `USE_CONV_SUMMARIES` (default `true`) |

#### `answer_feedback` (migration 007)

| Field | Detail |
|---|---|
| **Purpose** | Human feedback scores from Slack Block Kit thumbs-up/thumbs-down buttons; linked to LangSmith traces via `run_id` |
| **Key columns** | `run_id` (LangSmith trace ID), `user_email`, `signal` (POSITIVE/NEGATIVE), `correction`, `tool_called`, `query_preview`, `answer_preview` |
| **Populated by** | `slack_bot_local.py` → `_save_feedback()` (non-blocking `threading.Thread` after button click) |
| **Queried by** | LangSmith (via `create_feedback()` call from `_save_feedback()`); admin portal `GET /admin/token-analytics` |
| **Side effects** | NEGATIVE signal deletes all `mcp:get_user_violations:*` Redis cache keys |
| **Feature flag** | `USE_ANSWER_FEEDBACK` (default `true`) |

### Exception Management Tables (migration 005)

These are defined in `models/approved_exception.py`:

| Table | Purpose |
|---|---|
| `approved_exceptions` | Master record for each approved SOD exception (user, roles, approver, dates, risk score) |
| `exception_controls` | Compensating controls linked to an exception (implementation status, review schedule) |
| `exception_violations` | Records when an active exception's controls fail |
| `exception_reviews` | Periodic review decisions (continue/modify/revoke/escalate) per exception |

### Knowledge Base Table

#### `context_catalogue` (pgvector RAG)

| Field | Detail |
|---|---|
| **Purpose** | Chunked compliance policy documents with 384-dimensional vector embeddings for semantic search |
| **Key columns** | `content` (TEXT), `embedding` (Vector 384), `source_file`, `chunk_index`, `metadata_col` (JSONB) |
| **Populated by** | `scripts/enrich_knowledge_base.py` or `agents/knowledge_base_pgvector.py` |
| **Queried by** | `query_knowledge_base` handler, `get_compensating_controls` handler |

### Additional Tables (defined in `models/database.py`)

| Table | Purpose |
|---|---|
| `agent_logs` | Per-scan agent execution logs (FK → `compliance_scans`) |
| `notifications` | Violation notification delivery log |
| `audit_trail` | Immutable compliance action audit log (CREATE/UPDATE/DELETE/RESOLVE) |
| `okta_users` | Okta user data synced for Okta-NetSuite reconciliation |
| `user_reconciliations` | Cross-system reconciliation status (MATCHED/ORPHANED/STATUS_MISMATCH) |
| `deactivation_approvals` | Approval workflow for bulk NetSuite user deactivations |
| `deactivation_logs` | Per-user deactivation action log |
| `violation_exemptions` | Phase 3: Approved violation exemptions with pgvector embeddings for precedent search |
| `job_role_mappings` | Acceptable role combinations per job title; used by `validate_job_role` |

---

### Migration Files (`database/migrations/`)

| File | Date | What it creates |
|---|---|---|
| `005_add_exception_tables.sql` | 2026-02-13 | `approved_exceptions`, `exception_controls`, `exception_violations`, `exception_reviews`; associated enums (`exception_status`, `implementation_status`, `remediation_status`, `review_outcome`) |
| `006_add_conversation_summaries.sql` | 2026-02-24 | `conversation_summaries` table + indexes |
| `007_add_answer_feedback.sql` | 2026-02-26 | `answer_feedback` table + indexes |
| `008_add_sod_permission_map.sql` | 2026-02-27 | `sod_permission_map` table + indexes |
| `009_add_role_pair_conflicts.sql` | 2026-02-27 | `role_pair_conflicts` table + indexes |

Each migration has a corresponding `_rollback.sql` file. Apply with `psql $DATABASE_URL -f database/migrations/NNN_*.sql` (Alembic is used for ORM-level migrations; raw SQL files are used for these schema additions).

---

## 4. Models (SQLAlchemy ORM)

All models use `Base` from `models/database_config.py`.

### `models/database.py`

The main ORM module. Contains all core models:

| SQLAlchemy class | DB table | Used by |
|---|---|---|
| `User` | `users` | `user_repository.py`, most tool handlers |
| `Role` | `roles` | `role_repository.py`, `analyze_access_request`, `build_role_risk_matrix.py` |
| `UserRole` | `user_roles` | `user_repository.py`, `data_collector.py` |
| `SODRule` | `sod_rules` | `sod_rule_repository.py`, `analyzer.py` |
| `Violation` | `violations` | `violation_repository.py`, `get_user_violations`, `list_violations` |
| `SyncMetadata` | `sync_metadata` | `sync_metadata_repository.py`, `data_collector.py` |
| `ComplianceScan` | `compliance_scans` | `analyzer.py`, `perform_access_review` |
| `AgentLog` | `agent_logs` | `analyzer.py` |
| `Notification` | `notifications` | `notifier.py` (agents/) |
| `AuditTrail` | `audit_trail` | `audit_trail_repository.py` |
| `OktaUser` | `okta_users` | `okta_user_repository.py` |
| `UserReconciliation` | `user_reconciliations` | `user_reconciliation_repository.py` |
| `DeactivationApproval` | `deactivation_approvals` | `deactivation_approval_repository.py` |
| `DeactivationLog` | `deactivation_logs` | `deactivation_log_repository.py` |
| `ViolationExemption` | `violation_exemptions` | `exemption_repository.py` |
| `JobRoleMapping` | `job_role_mappings` | `job_role_mapping_repository.py`, `validate_job_role` |

**Enum classes in this file:** `UserStatus`, `ViolationSeverity`, `ViolationStatus`, `ScanStatus`, `SyncStatus`, `SyncType`, `NotificationChannel`, `NotificationStatus`, `OktaUserStatus`, `ReconciliationStatus`, `RiskLevel`, `ApprovalStatus`, `ExecutionStatus`, `ExecutionMethod`, `DeactivationAction`.

All enum values are UPPERCASE strings matching PostgreSQL `CHECK` constraints — see LESSONS_LEARNED Issue #14.

### `models/approved_exception.py`

Exception management models, imported at the bottom of `models/database.py`:

| SQLAlchemy class | DB table | Used by |
|---|---|---|
| `ApprovedExceptionModel` | `approved_exceptions` | `exception_repository.py`, `request_exception_approval`, `record_exception_approval` |
| `ExceptionControlModel` | `exception_controls` | `exception_repository.py` |
| `ExceptionViolationModel` | `exception_violations` | `exception_repository.py`, `record_exception_violation` |
| `ExceptionReviewModel` | `exception_reviews` | `exception_repository.py`, `conduct_exception_review` |
| `CompensatingControl` (aliased `CompensatingControlRef`) | `compensating_controls` | `get_compensating_controls` handler |

Enum classes: `ExceptionStatus`, `ImplementationStatus`, `RemediationStatus`, `ReviewOutcome`.

### `models/conversation_summary.py`

| SQLAlchemy class | DB table | Used by |
|---|---|---|
| `ConversationSummary` | `conversation_summaries` | `slack_bot_local.py` (`_get_prior_summaries`, `_write_conversation_summary`) |

### `models/answer_feedback.py`

| SQLAlchemy class | DB table | Used by |
|---|---|---|
| `AnswerFeedback` | `answer_feedback` | `slack_bot_local.py` (`_save_feedback`) |

### `models/database_config.py`

Not a model itself; provides `Base` (declarative base), `DatabaseConfig` class (session factory), and `get_db_config()` singleton. Used by every model and every tool handler.

---

## 5. Repositories (Data Access Layer)

All repositories follow the same pattern: `__init__(self, session: Session)` and CRUD methods. They are instantiated by `mcp/orchestrator.py` and tool handlers.

| File | Class | Wraps model(s) | Used by |
|---|---|---|---|
| `repositories/user_repository.py` | `UserRepository` | `User`, `UserRole` | `data_collector.py`, `initialize_session`, `get_user_violations`, `list_all_users`, `analyze_access_request` |
| `repositories/role_repository.py` | `RoleRepository` | `Role` | `data_collector.py`, `analyze_role_permissions`, `get_role_conflicts` |
| `repositories/violation_repository.py` | `ViolationRepository` | `Violation` | `analyzer.py`, `get_user_violations`, `remediate_violation`, `get_violation_stats` |
| `repositories/sod_rule_repository.py` | `SODRuleRepository` | `SODRule` | `analyzer.py`, `query_sod_rules`, `knowledge_base_pgvector.py` |
| `repositories/sync_metadata_repository.py` | `SyncMetadataRepository` | `SyncMetadata` | `data_collector.py`, `get_collection_agent_status`, `trigger_manual_sync` |
| `repositories/exception_repository.py` | `ExceptionRepository` | `ApprovedExceptionModel`, `ExceptionControlModel`, `ExceptionViolationModel`, `ExceptionReviewModel` | `record_exception_approval`, `list_approved_exceptions`, `get_exception_details`, `conduct_exception_review` |
| `repositories/exemption_repository.py` | `ExemptionRepository` | `ViolationExemption` | `knowledge_base_pgvector.py`, `find_similar_exceptions` |
| `repositories/audit_trail_repository.py` | `AuditTrailRepository` | `AuditTrail` | `admin_api.py` (`GET /admin/audit-trail`) |
| `repositories/job_role_mapping_repository.py` | `JobRoleMappingRepository` | `JobRoleMapping` | `validate_job_role`, `recommend_roles_for_job_title` |
| `repositories/okta_user_repository.py` | `OktaUserRepository` | `OktaUser` | `services/okta_client.py` |
| `repositories/user_reconciliation_repository.py` | `UserReconciliationRepository` | `UserReconciliation` | Okta-NetSuite reconciliation flows |
| `repositories/deactivation_approval_repository.py` | `DeactivationApprovalRepository` | `DeactivationApproval` | Bulk deactivation workflow |
| `repositories/deactivation_log_repository.py` | `DeactivationLogRepository` | `DeactivationLog` | Bulk deactivation workflow |

---

## 6. Agents

Background and analysis agents. All live in `agents/`.

### `agents/data_collector.py` — Scheduled NetSuite Sync

**Class:** `DataCollectionAgent`

**Purpose:** Autonomous agent that keeps the local PostgreSQL database in sync with NetSuite. Runs inside the MCP server process (started in FastAPI startup event via `mcp/orchestrator.py`).

**Schedule:**
- Full sync: daily at 2:00 AM (APScheduler `CronTrigger`)
- Incremental sync: every hour (APScheduler `IntervalTrigger`)

**Depends on:** `connectors/netsuite_connector.py`, `repositories/user_repository.py`, `repositories/role_repository.py`, `repositories/sync_metadata_repository.py`, `agents/analyzer.py`

**Runtime flow:**
1. Creates a `SyncMetadata` record with `status=RUNNING`
2. Calls `NetSuiteConnector.get_users_paginated(page_size=200)` — **critical**: page size must be 200 (NetSuite caps at 200; 1000 silently loses 79.2% of data — LESSONS_LEARNED Issue #13)
3. Upserts users and roles via repositories
4. Updates `SyncMetadata` with `status=SUCCESS` and record counts
5. Triggers `SODAnalysisAgent` to detect violations on updated users

### `agents/analyzer.py` — SOD Violation Detection

**Class:** `SODAnalysisAgent`

**Purpose:** Evaluates user-role-permission combinations against the 18 active SOD rules and stores violations in PostgreSQL.

**Depends on:** `repositories/violation_repository.py`, `repositories/user_repository.py`, `repositories/role_repository.py`, `repositories/sod_rule_repository.py`, `utils/langchain_callback.py`, Anthropic API (via `langchain-anthropic` `ChatAnthropic`)

**Runtime flow:**
1. Loads SOD rules from `sod_rule_repository`
2. For each user, retrieves their roles and permissions
3. Runs rule-matching logic to detect conflicts
4. For ambiguous cases, calls `claude-opus-4.6` via `ChatAnthropic` for reasoning (wrapped by `TokenTrackingCallback`)
5. Creates a `ComplianceScan` record first, then inserts `Violation` rows referencing it (FK constraint — LESSONS_LEARNED Issue #15)

**LangSmith:** All LLM calls traced via `LANGCHAIN_TRACING_V2=true` environment variable; `TokenTrackingCallback` bridges costs to the global `TokenTracker`.

### `agents/knowledge_base_pgvector.py` — pgvector RAG

**Class:** `KnowledgeBaseAgentPgvector`

**Purpose:** Provides semantic search over compliance policy documents stored as vector embeddings in the `context_catalogue` table.

**Depends on:** `services/embedding_service.py`, `services/llm/` (LLM factory), `repositories/sod_rule_repository.py`, `repositories/exemption_repository.py`, `utils/vector_search.py`

**Embedding provider:** Configurable; defaults to `huggingface` (sentence-transformers, 384 dimensions). Can be switched to `openai` (requires `OPENAI_API_KEY`) or `voyage`.

**Used by:** `query_knowledge_base` tool handler, `get_compensating_controls` tool handler.

### Other Agents

| File | Class | Purpose |
|---|---|---|
| `agents/orchestrator.py` | `ComplianceOrchestrator` (also at `mcp/orchestrator.py`) | Wires together collector, analyzer, knowledge base; provides `get_orchestrator()` singleton to tool handlers |
| `agents/risk_assessor.py` | `RiskAssessmentAgent` | Calculates per-user risk scores and org-level risk posture |
| `agents/report_generator.py` | `ReportGenerationAgent` | Generates formatted compliance reports; used by `generate_violation_report` |
| `agents/notifier.py` | `ComplianceNotifier` | Sends violation notifications via email/Slack/webhook; writes to `notifications` table |
| `agents/knowledge_base.py` | `KnowledgeBaseAgent` | Original in-memory knowledge base (superseded by `knowledge_base_pgvector.py` for production) |

---

## 7. Services

Thin service/client wrappers. All live in `services/`.

### `services/netsuite_client.py` — NetSuite OAuth 1.0a Client

**Class:** `NetSuiteClient`

**Purpose:** Authenticated HTTP client for the NetSuite RESTlet API using OAuth 1.0a (`requests-oauthlib`).

**Key credentials (from `.env`):** `NETSUITE_CONSUMER_KEY`, `NETSUITE_CONSUMER_SECRET`, `NETSUITE_TOKEN_ID`, `NETSUITE_TOKEN_SECRET`, `NETSUITE_REALM` (account ID), `NETSUITE_RESTLET_URL`

**Page size limit:** 200 records per request (NetSuite hard cap — see LESSONS_LEARNED Issue #13). Method `get_all_users_paginated(page_size=200)` must always use 200.

**Used by:** `connectors/netsuite_connector.py`

### `services/llm/` — LLM Abstraction Layer

Multi-provider LLM abstraction. Directory structure:

| File | Purpose |
|---|---|
| `services/llm/base.py` | Abstract base class `BaseLLMProvider`; `LLMMessage`, `LLMResponse`, `LLMStreamChunk` dataclasses; `LLMProvider` enum (Anthropic, OpenAI, Google, Cohere, Azure, Ollama, vLLM, HuggingFace) |
| `services/llm/factory.py` | `get_llm_from_config()` factory function — reads `LLM_PROVIDER` env var and instantiates the correct provider |
| `services/llm/config_manager.py` | Loads and validates LLM config from env vars |
| `services/llm/providers/` | Concrete provider implementations (Anthropic, OpenAI, etc.) |

**Used by:** `agents/knowledge_base_pgvector.py`, `agents/risk_assessor.py`, `agents/report_generator.py`

### `services/cache_service.py` — Redis Cache

**Class:** `CacheService`

**Purpose:** Redis-backed cache for expensive LLM responses and analysis results. Default TTL 24 hours. Separate from the MCP tool-call cache in `slack_bot_local.py` (which uses `redis_lib` directly with the `_MCP_CACHE_TTL` map).

**Used by:** `agents/risk_assessor.py`, `agents/report_generator.py`

### `services/embedding_service.py`

**Purpose:** Creates vector embeddings for documents and SOD rules. Provider-switchable (HuggingFace sentence-transformers, OpenAI, Voyage).

**Used by:** `agents/knowledge_base_pgvector.py`, `scripts/enrich_knowledge_base.py`

### `services/approval_service.py`

**Purpose:** Business logic for exception approval workflows — authority level calculation, Jira ticket creation, approver routing.

**Used by:** `mcp/admin_api.py`, `request_exception_approval` handler

### `services/okta_client.py`

**Purpose:** Okta Management API client for syncing Okta user data into `okta_users` table.

### `services/violation_report_service.py`

**Purpose:** Formats violation data into structured reports for `generate_violation_report`.

### `services/role_recommendation_service.py`

**Purpose:** Computes role recommendations for a given job title; used by `recommend_roles_for_job_title`.

---

## 8. Connectors

Thin adapters that bridge the service layer to the MCP tool layer.

### `connectors/netsuite_connector.py`

**Class:** `NetSuiteConnector` (extends `BaseConnector`)

**Purpose:** Wraps `NetSuiteClient` and provides a synchronous interface for use by `DataCollectionAgent`. Key methods: `test_connection_sync()`, `get_user_count_sync()`, `get_users_paginated_sync(page_size=200)`.

**Depends on:** `connectors/base_connector.py`, `services/netsuite_client.py`

**Used by:** `agents/data_collector.py`

### `connectors/base_connector.py`

**Class:** `BaseConnector`

**Purpose:** Abstract interface that all connectors must implement. Defines `connect()`, `disconnect()`, `test_connection()`, `get_users()`, `get_roles()`.

---

## 9. Utils

### `utils/tool_router.py` — Intent-Based Tool Pre-Filter (CRITICAL)

**Purpose:** Reduces token usage by sending only the 3-8 tools relevant to the user's intent instead of the full 37-tool schema on every Slack request (~10K tokens reduced to ~1.5K tokens).

**Key exports:**
- `TOOL_GROUPS` — dict mapping intent names to lists of tool names
- `INTENT_PATTERNS` — dict mapping intent names to lists of regex patterns
- `classify_intent(user_message)` → `List[str]` — keyword/regex matcher
- `select_tools_for_intent(user_message, all_tools, always_include, max_tools=8)` → `List[Dict]`

**Always-included tools:** `initialize_session`, `check_my_approval_authority`

**Intent groups:**

| Intent group | Tool names included | Key patterns |
|---|---|---|
| `access_review` | `get_user_violations`, `analyze_access_request`, `validate_job_role`, `get_role_conflicts`, `recommend_roles_for_job_title` | "can assign", "access request", "check access" |
| `violation_query` | `get_violation_stats`, `list_violations`, `get_violation_details`, `get_user_violations` | "violation", "sod conflict", "conflicts" |
| `exception_mgmt` | `request_exception_approval`, `check_my_approval_authority`, `get_exception_details`, `list_active_exceptions`, `approve_exception`, `revoke_exception` | "exception", "approval", "waiver" |
| `sod_rules` | `query_sod_rules`, `get_sod_rule_details`, `list_sod_rules` | "sod rule", "segregation of duties", "what rules" |
| `knowledge` | `query_knowledge_base`, `get_compensating_controls`, `get_permission_categories`, `search_permissions` | "compensating control", "best practice", "policy" |
| `role_analysis` | `analyze_role_permissions`, `get_role_conflicts`, `recommend_roles_for_job_title`, `validate_job_role` | "role permission", "analyze role", "role conflict" |
| `role_risk` | `get_role_risk_matrix`, `get_role_conflicts`, `list_violations` | "all roles", "custom roles", "fivetran roles", "role risk", "role matrix", "in isolation or combination" |
| `reporting` | `get_violation_stats`, `generate_compliance_report`, `get_org_risk_assessment`, `export_report` | "report", "summary", "overview", "dashboard" |
| `system` | `list_systems`, `get_system_status`, `trigger_manual_sync`, `get_sync_status`, `initialize_session` | "sync", "system status", "health" |
| `remediation` | `remediate_violation`, `schedule_review`, `create_remediation_ticket`, `notify_manager` | "remediate", "fix violation", "ticket" |

**IMPORTANT:** Every new MCP tool must be added to the appropriate `TOOL_GROUPS` entry (or a new group created) plus its `INTENT_PATTERNS` patterns updated. Without this, Claude will never receive the tool schema.

### `utils/anthropic_wrapper.py` — Anthropic Client Wrapper

**Classes:** `AnthropicClientWrapper`, `MessagesWrapper`

**Purpose:** Wraps the raw Anthropic SDK `messages.create()` to automatically record token usage to the global `TokenTracker` and tag LangSmith traces with `ls_model_name` metadata (maps `claude-opus-4-6` to `claude-3-opus-20240229` for cost approximation in LangSmith's pricing table).

**Decorated with:** `@traceable` from `langsmith`

**Used by:** `agents/` that have not yet been migrated to `langchain-anthropic`

### `utils/langchain_callback.py` — LangChain Token Tracking Bridge

**Class:** `TokenTrackingCallback` (extends `BaseCallbackHandler`)

**Purpose:** LangChain callback that intercepts `on_llm_end` events from `ChatAnthropic` and forwards token usage to the global `TokenTracker`. Eliminates the need to rewrite agents to use the raw Anthropic SDK for cost tracking.

**Used by:** `slack_bot_local.py` (`process_with_claude`), `agents/analyzer.py`, all agents using `ChatAnthropic`

### `utils/token_tracker.py` — Global Token / Cost Tracker

**Class:** `TokenTracker`; `get_global_tracker()` singleton

**Purpose:** Accumulates token usage and calculates costs using the pricing table (`claude-opus-4.6`: $15/$75 per million input/output tokens; `claude-haiku-4.5`: $1/$5).

**Used by:** `utils/anthropic_wrapper.py`, `utils/langchain_callback.py`, `admin_api.py` (`GET /admin/token-analytics`)

### `utils/vector_search.py` — pgvector Similarity Search

**Class:** `VectorSearcher`; `create_vector_searcher()` factory

**Purpose:** Abstracts pgvector similarity queries (cosine / L2 / inner product distance metrics) over any table with a `Vector` column.

**Used by:** `agents/knowledge_base_pgvector.py`

### `utils/violation_embedder.py`

**Purpose:** Generates and stores embeddings for `Violation` records to enable `find_similar_exceptions` semantic search.

---

## 10. Slack Bot Components (`slack_bot_local.py`)

All key functions in the single-file Slack bot:

### `process_with_claude(user_message, user_email, mentioned_users, thread_history, prior_context)` (line 767)

**The main agentic loop.** Decorated with `@traceable(name="slack_compliance_query")` for LangSmith.

**Model split:**
- Tool-dispatch turns (no tool results yet): `claude-haiku-4-5-20251001` (`haiku_with_tools`) — fast and cheap
- Synthesis turns (tool results available): `claude-opus-4-6` (`llm_with_tools`) — high-quality reasoning

**Loop (up to 5 turns):**
1. Filters tools via `select_tools_for_intent()` from `utils/tool_router.py`
2. Builds `SystemMessage` with static prompt + dynamic context (prior summaries, mentioned user details); static part tagged `cache_control: ephemeral` for Anthropic prompt caching
3. Calls `llm.invoke([system] + messages)`
4. If `tool_calls` present: executes each via `call_mcp_tool()`, appends `ToolMessage`, continues loop
5. If no tool calls: returns final answer string

**Post-loop (non-blocking background threads):**
- `_write_conversation_summary()` — Haiku summarisation written to `conversation_summaries`
- LangSmith root-run metadata patched with `context_cache_hit`, `context_summaries_injected` via `_cache_hit_tls` thread-local

### `_trim_history(messages, keep=10)` (line 464)

**Purpose:** Limits the LangChain message history to `keep` most recent messages. After slicing, advances the start index forward to the first `HumanMessage` to prevent orphaned `tool_result` blocks that would cause Anthropic API HTTP 400 errors (fixed 2026-02-27).

```python
def _trim_history(messages: list, keep: int = 10) -> list:
    sliced = messages[-keep:]
    for i, m in enumerate(sliced):
        if isinstance(m, HumanMessage):
            return sliced[i:]
    return sliced
```

### `_feedback_blocks(run_id, user_email, query_preview, answer_preview, tool_called)` (line 573)

Builds a Slack `actions` block with two buttons (thumbs up / thumbs down). Button value encodes `signal|run_id|user_email|query_preview|answer_preview|tool_called` as a pipe-separated string for stateless decoding in `handle_feedback()`.

### `_save_feedback(signal, run_id, user_email, channel_id, ...)` (line 609)

Non-blocking feedback persistence: writes `AnswerFeedback` row to Postgres and calls `LangSmith.create_feedback(run_id, key="human_rating", score=1.0/0.0)`. On NEGATIVE signal, deletes all `mcp:get_user_violations:*` keys from Redis.

### `_replace_feedback_block_with_confirmation(client, body, signal)` (line 676)

Swaps the feedback action buttons with a one-line confirmation text so users cannot double-submit.

### `fetch_dm_history(client, channel, bot_user_id, current_ts, limit=10)` (line 708)

Fetches the last 10 messages from a DM channel using `conversations_history()` (DMs have no `thread_ts`). Skips "thinking" indicator messages (⏳). Maps `bot_id` presence to `"assistant"` role for proper `HumanMessage`/`AIMessage` alternation.

**Required Slack scope:** `im:history`

### `fetch_thread_history(client, channel, thread_ts, bot_user_id, current_ts)` (line 738)

Fetches thread context using `conversations_replies()` for channel threads.

**Required Slack scope:** `channels:history`

### `call_mcp_tool(tool_name, arguments)` (line 304)

Decorated with `@traceable(run_type="tool")`. MCP HTTP bridge:

1. Checks Redis cache (`mcp:{tool_name}:{md5(arguments)}`); returns cached string if HIT
2. On MISS: POST to `{MCP_SERVER_URL}/mcp` with JSON-RPC 2.0 `tools/call`
3. Writes result to Redis with TTL from `_MCP_CACHE_TTL` map (skips mutating tools in `_MUTATING_TOOLS`)
4. Sets `_cache_hit_tls.hit` thread-local flag so the root LangSmith trace can be tagged

### `_compress_tool_result(tool_name, content, llm)` (line 489)

Rolling compression: if a tool result exceeds `ROLLING_SUMMARY_MIN_CHARS` (default 800), calls Haiku to summarise it before storing in message history. Reduces context window consumption on multi-turn queries.

### `handle_dm(event, say, client)` (line 1146)

Slack event handler for direct messages. Flow:
1. Resolves caller email via `users_info()`
2. Calls `fetch_dm_history()` (prior conversation context)
3. Retrieves prior summaries via `_get_prior_summaries()`
4. Calls `process_with_claude()`
5. Posts response via `client.chat_update()` and appends `_feedback_blocks()`
6. Spawns `threading.Thread` for `_write_conversation_summary()`

### `handle_mention(event, say, client)` (line 1060)

Slack event handler for `@mention` in channels. Same flow as `handle_dm` but uses `fetch_thread_history()` and resolves `@mention` tokens to emails via `extract_user_mentions()`.

### Constants

| Constant | Type | Default | Env override | Purpose |
|---|---|---|---|---|
| `MAX_SLACK_RESPONSE_CHARS` | `int` | `2000` | `SLACK_MAX_RESPONSE_CHARS` | Responses longer than this threshold trigger auto-upload via `files_upload_v2()` instead of inline posting |

### Helper Functions

#### `_upload_full_response(client, channel, title, content)` (NEW — 2026-02-27)

Uploads the full response text as a Slack file using `files_upload_v2()`. Returns the file permalink on success, or `None` on failure.

**Required Slack bot scope:** `files:write`

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `client` | `WebClient` | Slack SDK client instance |
| `channel` | `str` | Slack channel or DM channel ID to share the file into |
| `title` | `str` | Display title for the uploaded file |
| `content` | `str` | Full response text to upload |

**Returns:** `str | None` — permalink URL of the uploaded file, or `None` if the upload fails.

#### `_trim_response_for_slack(response, client, channel)` (NEW — 2026-02-27)

Called immediately after `process_with_claude()` returns. If the response exceeds `MAX_SLACK_RESPONSE_CHARS`, the function finds the nearest clean boundary (sentence end or newline), uploads the full text via `_upload_full_response()`, and returns the trimmed excerpt appended with a link to the full file.

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `response` | `str` | Full response string returned by `process_with_claude()` |
| `client` | `WebClient` | Slack SDK client instance (passed through to `_upload_full_response`) |
| `channel` | `str` | Destination channel ID (passed through to `_upload_full_response`) |

**Returns:** `str` — either the original response unchanged (if within limit) or the trimmed excerpt + permalink to the full file.

### System Prompt Sections (NEW — 2026-02-27)

The static system prompt injected into every `process_with_claude()` call contains the following named blocks in addition to the existing McKinsey-voice and role-context blocks:

#### `CAPABILITIES QUERY`

Instructs Claude to call `list_systems` before answering any question of the form "what can you do" or "what systems do you cover". Active systems are derived exclusively from the ✅ entries returned by `list_systems` — Claude **never** hardcodes system names. Max block length: 800 chars.

#### `GLOBAL RESPONSE LENGTH`

Caps all responses at 1,800 characters. If a response would exceed this limit, Claude must instead summarise in 3 bullet points and offer to provide further detail on any specific point.

#### `HARD LIMIT (get_role_risk_matrix)`

When answering with data from `get_role_risk_matrix`, Claude is constrained to: max 3 bullets, max 1,200 characters total, and no permission-level detail (role names and severity only). This prevents overly verbose matrix dumps in Slack threads.

### Feature Flags

| Flag | `.env` key | Default | Effect |
|---|---|---|---|
| MCP tool-call Redis cache | `USE_MCP_CACHE` | `true` | Cache read-only tool results in Redis with per-tool TTLs |
| Conversation summarization | `USE_CONV_SUMMARIES` | `true` | Write Haiku summaries to `conversation_summaries`; inject as prior context |
| Human answer feedback | `USE_ANSWER_FEEDBACK` | `true` | Append thumbs-up/thumbs-down buttons to every response |

---

## 11. Configuration & Scripts

### `.env` — Required Environment Variables

```bash
# Database
DATABASE_URL="postgresql://user:pass@localhost:5432/compliance_db"

# NetSuite OAuth 1.0a
NETSUITE_ACCOUNT_ID="5260239_SB1"
NETSUITE_CONSUMER_KEY="..."
NETSUITE_CONSUMER_SECRET="..."
NETSUITE_TOKEN_ID="..."
NETSUITE_TOKEN_SECRET="..."
NETSUITE_RESTLET_URL="https://..."

# LLM Providers
ANTHROPIC_API_KEY="sk-ant-..."      # Required: Claude (SOD analysis, Slack bot)
OPENAI_API_KEY="sk-..."             # Optional: embeddings (knowledge base)

# LangSmith Observability
LANGSMITH_API_KEY="lsv2_pt_..."
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=compliance-agent

# Slack Bot
SLACK_BOT_TOKEN="xoxb-..."
SLACK_APP_TOKEN="xapp-..."

# Redis (MCP tool-call cache)
REDIS_URL="redis://localhost:6379/0"

# Admin Portal (JWT)
JWT_SECRET="<long-random-string>"
ADMIN_PORTAL_PASSWORD="<portal-password>"
JWT_EXPIRE_HOURS=8                  # Optional, default 8

# Feature flags
USE_MCP_CACHE=true
USE_CONV_SUMMARIES=true
USE_ANSWER_FEEDBACK=true

# Slack bot tuning (optional)
SLACK_MAX_TOKENS=1024
SLACK_MAX_HISTORY_TURNS=4
SLACK_TOOL_OUTPUT_MAX_CHARS=2000
SLACK_ROLLING_SUMMARY_MIN_CHARS=800
SLACK_MAX_RESPONSE_CHARS=2000        # Responses longer than this trigger auto-upload via files_upload_v2()

# CORS (optional)
MCP_ALLOWED_ORIGINS="http://localhost,http://localhost:4200"
```

### `scripts/restart_mcp.sh`

**Purpose:** Gracefully stops any running `mcp.mcp_server` process, waits for port 8080 to clear, verifies the Python environment, starts the server via `nohup python3 -m mcp.mcp_server`, and polls logs for `"Uvicorn running"` to confirm successful startup. Exits with code 0 (success), 1 (warnings), or 2 (failure).

**Usage:** `./scripts/restart_mcp.sh [log_file]` (default log: `/tmp/mcp_server.log`)

### `scripts/check_mcp_status.sh`

**Purpose:** Comprehensive health check covering: process status + PID/memory/CPU, port 8080, database connection, log file size, recent errors, autonomous collection agent status, MCP tool count, and last sync record. Exits with code 0 (all OK), 1 (warnings), or 2 (critical).

**Usage:** `./scripts/check_mcp_status.sh`

### `scripts/build_role_risk_matrix.py`

**Purpose:** One-shot analysis job. See Section 1 (Entry Points) for full details.

**When to re-run:**
- After any full NetSuite sync that changes role permissions
- After SOD rules are added or modified
- After new Fivetran custom roles are created in NetSuite
- Result is stale if `role_pair_conflicts` has not been rebuilt since the last role/rule change

**Command:** `cd compliance-agent && python3 scripts/build_role_risk_matrix.py`

---

## 12. External Dependencies & Integrations

### Anthropic API

| Model | Used for | Call site |
|---|---|---|
| `claude-opus-4-6` | SOD violation analysis, access request evaluation, final Slack answer synthesis | `agents/analyzer.py`, `slack_bot_local.py` (`process_with_claude` synthesis turns), `analyze_access_request`, `generate_violation_report` |
| `claude-haiku-4-5-20251001` | Tool-dispatch turns in Slack bot, rolling tool-result compression, conversation summarization | `slack_bot_local.py` (`process_with_claude` dispatch turns, `_compress_tool_result`, `_write_conversation_summary`) |

Context window: 200K tokens for Opus 4.6. Prompt caching enabled on the static system prompt (`cache_control: ephemeral`).

### LangSmith

| Feature | How it is used |
|---|---|
| Distributed tracing | Every Slack query produces one `slack_compliance_query` `@traceable` root run; nested child spans for each LLM turn and tool call |
| Cost/token tracking | `ChatAnthropic` + `TokenTrackingCallback` automatically populates `prompt_tokens`, `completion_tokens`, `total_cost` per trace |
| Human feedback | `create_feedback(run_id, key="human_rating", score=1.0/0.0)` called from `_save_feedback()` — visible in the Feedback tab |
| Online evaluators (3) | `mcp_tool_called` (scores 0 if no tool called), `mcp_tool_coverage` (scores 0 if access request skipped `analyze_access_request`), `hallucination_heuristic` (scores 0 if `<tool_call>` XML or ungrounded numeric claims detected) |
| Cache-hit tagging | `_cache_hit_tls` thread-local propagates `context_cache_hit=true` from `call_mcp_tool()` to the root run via patching `metadata` after the trace completes |

Required env vars: `LANGSMITH_API_KEY`, `LANGCHAIN_TRACING_V2=true`, `LANGCHAIN_PROJECT=compliance-agent`.

Known limitation: `claude-opus-4-6` is not in LangSmith's pricing table; cost is approximated by mapping via `ls_model_name=claude-3-opus-20240229` in `utils/anthropic_wrapper.py`.

### Redis

Used in two places:

**1. MCP tool-call cache (`slack_bot_local.py`)**

Cache key pattern: `mcp:{tool_name}:{md5(json(arguments))}`

| Tool | TTL |
|---|---|
| `get_user_violations` | 3600 s (1 h) |
| `get_violation_stats` | 1800 s (30 min) |
| `get_role_conflicts` | 86400 s (24 h) |
| `get_role_risk_matrix` | 86400 s (24 h) |
| `analyze_access_request` | 3600 s (1 h) |
| `initialize_session` | 300 s (5 min) |
| `list_systems` | 3600 s (1 h) |
| `list_all_users` | 1800 s (30 min) |
| `get_compliance_report` | 1800 s (30 min) |
| `search_permissions` | 3600 s (1 h) |
| `check_my_approval_authority` | 3600 s (1 h) |
| `validate_job_role` | 3600 s (1 h) |

Mutating tools never cached: `trigger_manual_sync`, `approve_exception`, `request_exception_approval`, `remediate_violation`, `update_exception_status`. On NEGATIVE feedback, all `mcp:get_user_violations:*` keys are deleted.

**2. LLM response cache (`services/cache_service.py`)**

Used by `risk_assessor.py` and `report_generator.py` for expensive analysis results. Default TTL 86400 s (24 h). Separate from the MCP cache.

### PostgreSQL + pgvector

| Table | Vector column | Dimensions | Distance metric |
|---|---|---|---|
| `roles` | `embedding` | 384 | Cosine (semantic role search) |
| `sod_rules` | `embedding` | 384 | Cosine (semantic rule search) |
| `violations` | `embedding` | 384 | Cosine (similar violation search) |
| `violation_exemptions` | `embedding` | 384 | Cosine (precedent exemption search) |
| `context_catalogue` | `embedding` | 384 | Cosine (RAG policy search) |

PostgreSQL 14+ required. Enable extension: `CREATE EXTENSION IF NOT EXISTS vector;`

### Slack API (Socket Mode)

| Credential | Env var | Purpose |
|---|---|---|
| Bot User OAuth Token | `SLACK_BOT_TOKEN` (`xoxb-`) | Post messages, read user profiles, read channel/DM history |
| App-Level Token | `SLACK_APP_TOKEN` (`xapp-`) | Socket Mode WebSocket connection (replaces webhooks) |

Required OAuth scopes: `chat:write`, `users:read`, `users:read.email`, `app_mentions:read`, `im:read`, `im:write`, `im:history`, `channels:history`, `reactions:write`, `files:write` (required by `_upload_full_response()` for auto-upload of long responses)

The bot handles: `app_mention` events → `handle_mention()`, `message.im` events → `handle_dm()`, `action` events (feedback buttons) → `handle_feedback()`.

### NetSuite RESTlet

| Parameter | Value |
|---|---|
| Protocol | OAuth 1.0a (HMAC-SHA256) |
| Endpoint | `NETSUITE_RESTLET_URL` (SuiteScript RESTlet) |
| Max page size | **200 records** (hard cap — exceeding 200 silently truncates; 1000 would lose 79.2% of data) |
| Auth credentials | `NETSUITE_ACCOUNT_ID` (realm), `NETSUITE_CONSUMER_KEY/SECRET`, `NETSUITE_TOKEN_ID/SECRET` |
| Client class | `services/netsuite_client.py` → `NetSuiteClient` |
| Connector class | `connectors/netsuite_connector.py` → `NetSuiteConnector` |

---

## 13. Artifact Dependency Graph (text)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SLACK PATH (user-initiated, real-time)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Slack message (@mention or DM)
  │
  ▼
slack_bot_local.py
  │  handle_mention() / handle_dm()
  │    ├── fetch_thread_history() / fetch_dm_history()
  │    │       └── Slack API (conversations_replies / conversations_history)
  │    │
  │    ├── _get_prior_summaries()
  │    │       └── PostgreSQL → conversation_summaries
  │    │
  │    └── process_with_claude()   [@traceable → LangSmith root span]
  │            │
  │            ├── utils/tool_router.py
  │            │       └── select_tools_for_intent()
  │            │               filters 37 tools → 3-8 relevant tools
  │            │
  │            ├── [Turn 1..N, max 5]
  │            │     ├── ChatAnthropic(haiku-4-5)   [dispatch turn]
  │            │     │       └── TokenTrackingCallback → TokenTracker → LangSmith
  │            │     │
  │            │     ├── call_mcp_tool(tool_name, args)   [@traceable]
  │            │     │       ├── Redis GET mcp:{tool}:{md5(args)}   [CACHE HIT → return]
  │            │     │       │
  │            │     │       └── [CACHE MISS]
  │            │     │               POST http://localhost:8080/mcp (JSON-RPC 2.0)
  │            │     │                 └── mcp/mcp_server.py
  │            │     │                       └── mcp/mcp_tools.py (handler)
  │            │     │                             ├── PostgreSQL (models + repositories)
  │            │     │                             └── NetSuite API (connectors)
  │            │     │               Redis SET mcp:{tool}:{md5(args)} TTL
  │            │     │
  │            │     └── ChatAnthropic(opus-4-6)   [synthesis turn, after tool results]
  │            │             └── TokenTrackingCallback → TokenTracker → LangSmith
  │            │
  │            └── Final answer string
  │
  ├── format_as_blocks() + _feedback_blocks()
  │       └── Slack API chat_update() [posts response with feedback buttons]
  │
  ├── threading.Thread → _write_conversation_summary()
  │       ├── ChatAnthropic(haiku-4-5) [summarise]
  │       └── PostgreSQL → conversation_summaries [write]
  │
  └── [On feedback button click]
        handle_feedback()
          └── threading.Thread → _save_feedback()
                ├── PostgreSQL → answer_feedback [write]
                ├── LangSmith create_feedback(human_rating)
                └── [NEGATIVE] Redis DEL mcp:get_user_violations:*


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 MCP SERVER PATH (tool execution)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

POST http://localhost:8080/mcp
  │
  ▼
mcp/mcp_server.py (FastAPI)
  │  route: POST /mcp, method tools/call
  ├── mcp/mcp_tools.py
  │       ├── TOOL_HANDLERS[tool_name](args)
  │       │       ├── models/database_config.py (session)
  │       │       ├── repositories/*.py (data access)
  │       │       │       └── models/database.py (ORM → PostgreSQL)
  │       │       ├── mcp/orchestrator.py (agent wiring)
  │       │       │       ├── agents/analyzer.py
  │       │       │       │       └── Anthropic API (claude-opus-4-6)
  │       │       │       ├── agents/data_collector.py
  │       │       │       │       └── connectors/netsuite_connector.py
  │       │       │       │               └── services/netsuite_client.py
  │       │       │       │                       └── NetSuite RESTlet
  │       │       │       └── agents/knowledge_base_pgvector.py
  │       │       │               └── PostgreSQL (pgvector similarity)
  │       │       └── services/ (LLM, cache, approval, etc.)
  │       │
  │       └── TOOL_SCHEMAS[tool_name] (JSON schema for tools/list)
  │
  └── mcp/admin_api.py (JWT-protected admin routes)
          └── PostgreSQL (violations, exceptions, audit trail, analytics)


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 BACKGROUND SYNC PATH (scheduled, autonomous)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

APScheduler (inside mcp_server.py process)
  │  CronTrigger 02:00 daily / IntervalTrigger 1h
  ▼
agents/data_collector.py (DataCollectionAgent)
  ├── connectors/netsuite_connector.py
  │       └── services/netsuite_client.py
  │               └── NetSuite RESTlet (page_size=200)
  │
  ├── repositories/user_repository.py    → PostgreSQL users, user_roles
  ├── repositories/role_repository.py    → PostgreSQL roles
  ├── repositories/sync_metadata_repository.py → PostgreSQL sync_metadata
  │
  └── agents/analyzer.py (SODAnalysisAgent)
          ├── repositories/violation_repository.py → PostgreSQL violations
          ├── repositories/sod_rule_repository.py  → PostgreSQL sod_rules
          └── Anthropic API (claude-opus-4-6 via ChatAnthropic)
                  └── LangSmith (auto-traced via LANGCHAIN_TRACING_V2)


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ROLE RISK MATRIX BUILD PATH (one-shot job)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

scripts/build_role_risk_matrix.py
  ├── PostgreSQL sod_rules    (reads rule + conflicting_permissions)
  ├── PostgreSQL roles        (reads permissions JSON for each role)
  ├── PostgreSQL sod_permission_map   (seeds + reads abstract→NS mapping)
  └── PostgreSQL role_pair_conflicts  (upserts 443 conflict rows)


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ANGULAR PORTAL PATH (admin web UI)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Browser → angular-portal/ (Angular 17, http://localhost:4200)
  │  proxy.conf.json forwards /auth + /admin to localhost:8080
  ▼
mcp/admin_api.py (JWT-protected routers)
  ├── POST /auth/login      → JWT issuance
  └── GET/PATCH /admin/*   → PostgreSQL (violations, exceptions, config, audit)
```

---

*Last updated: 2026-02-27*
*Maintained by: AI Development Team*
