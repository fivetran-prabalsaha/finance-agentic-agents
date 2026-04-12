# Technical Specification - SOD Compliance System v3.0

## Document Information

| Property | Value |
|----------|-------|
| **Document Version** | 3.4.0 |
| **Last Updated** | 2026-03-15 |
| **Status** | ✅ Production Ready - LLM Agnostic + Okta + pgvector + Redis Cache + Agent Response Pattern + Semantic Tool Router + Eval Suite |
| **Owner** | Prabal Saha |
| **Project** | SOD Compliance & Risk Assessment System |

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagrams](#architecture-diagrams)
3. [Data Flow](#data-flow)
4. [Database Schema](#database-schema)
5. [Business Logic](#business-logic)
6. [Component Specifications](#component-specifications)
7. [Integration Points](#integration-points)
8. [Semantic Tool Router](#semantic-tool-router)
9. [Evaluation Suite](#evaluation-suite)
10. [Security & Encryption](#security--encryption)
11. [Performance Metrics](#performance-metrics)
12. [Deployment](#deployment)

---

## System Overview

### Executive Summary

The SOD Compliance System is a **multi-agent AI system** that automates Segregation of Duties compliance monitoring across SOX compliant business systems. The system features:

- **LLM-Agnostic Architecture** - Switch between any LLM provider (Anthropic, OpenAI, Google, etc.)
- **6 Specialized Agents** - Data collection, analysis, risk assessment, knowledge base, AI insights, notifications
- **Context-Aware Analysis** - Job function-based exemptions reduce false positives by 67%
- **Okta Integration** - User lifecycle reconciliation with automated deactivation workflow
- **Real-time Monitoring** - Automated scans with configurable intervals
- **Cost Optimization** - Automatic cost tracking across all LLM providers

### Key Capabilities

✅ **185 users/sec** analysis throughput
✅ **95% accuracy** with context-aware exemptions
✅ **67% reduction** in IT staff false positives
✅ **8 LLM providers** supported (Anthropic, OpenAI, Google, Cohere, Azure, Ollama, vLLM, HuggingFace)
✅ **Vector search** with pgvector - semantic rule matching with 384-dim embeddings
✅ **Redis caching** - 90% cost reduction, 10-500x faster repeated queries
✅ **Encrypted API keys** with Fernet encryption
✅ **Okta-NetSuite reconciliation** for user lifecycle management
✅ **Human-in-the-loop** approval workflow for deactivations

---

## Architecture Diagrams

### 1. High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         COMPLIANCE SYSTEM                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
        ┌───────────────┐  ┌──────────────┐  ┌──────────────┐
        │   NetSuite    │  │     Okta     │  │    Claude    │
        │   (OAuth)     │  │   (API)      │  │  (via LLM)   │
        │   RESTlet     │  │   Users      │  │  Abstraction │
        └───────┬───────┘  └──────┬───────┘  └──────┬───────┘
                │                  │                  │
                │                  │                  │
        ┌───────▼──────────────────▼──────────────────▼───────┐
        │           INTEGRATION & ABSTRACTION LAYER            │
        │  ┌────────────┐  ┌─────────────┐  ┌──────────────┐ │
        │  │  NetSuite  │  │    Okta     │  │     LLM      │ │
        │  │   Client   │  │   Client    │  │  Abstraction │ │
        │  └────────────┘  └─────────────┘  └──────────────┘ │
        └──────────────────────────┬───────────────────────────┘
                                   │
        ┌──────────────────────────▼───────────────────────────┐
        │              MULTI-AGENT ORCHESTRATOR                 │
        │                  (LangGraph)                          │
        │  ┌─────────────────────────────────────────────────┐ │
        │  │           Agent Workflow Engine                 │ │
        │  └─────────────────────────────────────────────────┘ │
        └──────────────────────────┬───────────────────────────┘
                                   │
        ┌──────────────────────────▼───────────────────────────┐
        │                   AGENT LAYER                         │
        │                                                       │
        │  ┌──────────┐  ┌──────────┐  ┌────────────────┐    │
        │  │   Data   │  │   SOD    │  │  Reconciliation│    │
        │  │Collector │  │ Analyzer │  │     Agent      │    │
        │  └──────────┘  └──────────┘  └────────────────┘    │
        │                                                       │
        │  ┌──────────┐  ┌──────────┐  ┌────────────────┐    │
        │  │   Risk   │  │Knowledge │  │  Deactivation  │    │
        │  │ Assessor │  │   Base   │  │     Agent      │    │
        │  └──────────┘  └──────────┘  └────────────────┘    │
        │                                                       │
        │  ┌──────────┐  ┌──────────┐                        │
        │  │   AI     │  │Notifier  │                        │
        │  │ Analyst  │  │  Agent   │                        │
        │  └──────────┘  └──────────┘                        │
        └──────────────────────────┬───────────────────────────┘
                                   │
        ┌──────────────────────────▼───────────────────────────┐
        │              DATA & REPOSITORY LAYER                  │
        │                                                       │
        │  ┌──────────┐  ┌──────────┐  ┌────────────────┐    │
        │  │   User   │  │   Role   │  │   Violation    │    │
        │  │   Repo   │  │   Repo   │  │      Repo      │    │
        │  └──────────┘  └──────────┘  └────────────────┘    │
        │                                                       │
        │  ┌──────────┐  ┌──────────┐  ┌────────────────┐    │
        │  │   Okta   │  │   Recon  │  │   Deactivation │    │
        │  │   Repo   │  │   Repo   │  │   Approval     │    │
        │  └──────────┘  └──────────┘  └────────────────┘    │
        └──────────────────────────┬───────────────────────────┘
                                   │
        ┌──────────────────────────▼───────────────────────────┐
        │               DATABASE LAYER                          │
        │                                                       │
        │  ┌─────────────────────────────────────────────┐    │
        │  │         PostgreSQL 17 + pgvector 0.8.1       │    │
        │  │                                              │    │
        │  │  Core:    users, roles, user_roles           │    │
        │  │  Rules:   sod_rules, violations              │    │
        │  │  Vectors: embedding vector(384) in 3 tables  │    │
        │  │  Okta:    okta_users, reconciliations        │    │
        │  │  Workflow: deactivation_approvals, logs      │    │
        │  │  Tracking: compliance_scans, agent_logs      │    │
        │  └─────────────────────────────────────────────┘    │
        │                                                       │
        │  ┌─────────────────────────────────────────────┐    │
        │  │         Redis 7 (Cache - ACTIVE)             │    │
        │  │  • AI analysis caching (24h TTL)             │    │
        │  │  • Violation results (1h TTL)                │    │
        │  │  • Risk scores (1h TTL)                      │    │
        │  │  • 90% cost reduction on repeated queries    │    │
        │  └─────────────────────────────────────────────┘    │
        └───────────────────────────────────────────────────────┘
```

### 2. LLM Abstraction Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                           │
│  (Agents: Analyzer, Risk Assessor, Notifier, AI Analyst)        │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   LLM ABSTRACTION LAYER                          │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │             Unified Interface (BaseLLMProvider)           │  │
│  │                                                           │  │
│  │  Methods:                                                 │  │
│  │  • generate(messages) -> LLMResponse                      │  │
│  │  • generate_stream(messages) -> Iterator                 │  │
│  │  • count_tokens(text) -> int                             │  │
│  │  • get_model_info() -> Dict                              │  │
│  │  • test_connection() -> bool                             │  │
│  │  • calculate_cost(input, output) -> float                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│              ┌───────────────┼──────────────┐                  │
│              │               │              │                   │
│  ┌───────────▼──┐  ┌────────▼──────┐  ┌───▼──────────┐       │
│  │   Factory    │  │    Config     │  │  Encryption  │       │
│  │   Pattern    │  │   Manager     │  │  (Fernet)    │       │
│  └───────┬──────┘  └────────┬──────┘  └──────────────┘       │
│          │                   │                                  │
│          └──────────┬────────┘                                  │
│                     │                                           │
│  ┌──────────────────▼─────────────────────────────────────┐   │
│  │              Provider Implementations                   │   │
│  │                                                         │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────┐ │   │
│  │  │Anthropic │  │  OpenAI  │  │  Google  │  │Cohere │ │   │
│  │  │  Claude  │  │   GPT    │  │  Gemini  │  │Command│ │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └───────┘ │   │
│  │                                                         │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐             │   │
│  │  │  Azure   │  │  Ollama  │  │  vLLM    │             │   │
│  │  │ OpenAI   │  │  Local   │  │  Local   │             │   │
│  │  └──────────┘  └──────────┘  └──────────┘             │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     EXTERNAL LLM APIS                            │
│                                                                  │
│  Claude API    OpenAI API    Gemini API    Cohere API          │
│  (Anthropic)   (OpenAI)      (Google)      (Cohere)            │
│                                                                  │
│  Azure OpenAI  Ollama        vLLM Server                        │
│  (Microsoft)   (localhost)   (localhost)                        │
└─────────────────────────────────────────────────────────────────┘
```

### 3. Data Flow Diagram - Complete System

```
┌──────────────┐
│   NetSuite   │
│    Users     │
└──────┬───────┘
       │
       │ ① Fetch User Data
       │    (RESTlet v5)
       ▼
┌──────────────────────┐        ┌──────────────┐
│  Data Collection     │───────▶│  PostgreSQL  │
│      Agent           │        │    Users     │
│  • Search users      │        │    Roles     │
│  • Extract roles     │        │  UserRoles   │
│  • Job function      │        └──────────────┘
└──────────────────────┘
       │
       │ ② User & Role Data
       ▼
┌──────────────────────┐        ┌──────────────┐
│   SOD Analyzer       │───────▶│  PostgreSQL  │
│      Agent           │        │  Violations  │
│  • Load 18 rules     │        └──────────────┘
│  • Check conflicts   │
│  • Context-aware     │        ┌──────────────┐
│  • Pattern match     │───────▶│     LLM      │
└──────────────────────┘        │  (Claude)    │
       │                         └──────────────┘
       │ ③ Violations
       ▼
┌──────────────────────┐        ┌──────────────┐
│   Risk Assessor      │───────▶│  PostgreSQL  │
│      Agent           │        │   Updated    │
│  • User risk score   │        │  Violations  │
│  • Org risk level    │        │  + Scores    │
│  • Risk distribution │        └──────────────┘
└──────────────────────┘
       │
       │ ④ Risk Scores
       ▼
┌──────────────────────┐        ┌──────────────┐
│  AI Analysis Agent   │───────▶│     LLM      │
│  • Generate insights │        │  (Claude)    │
│  • Explain risks     │        │  Abstraction │
│  • Recommendations   │        └──────────────┘
└──────────────────────┘
       │
       │ ⑤ AI Insights
       ▼
┌──────────────────────┐
│   Knowledge Base     │
│      Agent           │        ┌──────────────┐
│  • Semantic search   │───────▶│  Embeddings  │
│  • Rule lookup       │        │  (HuggingFace│
│  • Similar cases     │        │   pgvector)  │
└──────────────────────┘        └──────────────┘
       │
       │ ⑥ Knowledge + Context
       ▼
┌──────────────────────┐
│   Notifier Agent     │
│  • Format reports    │        ┌──────────────┐
│  • User comparison   │───────▶│   SendGrid   │
│  • Send alerts       │        │    Email     │
│  • Track delivery    │        └──────────────┘
└──────────────────────┘
       │                         ┌──────────────┐
       └────────────────────────▶│    Slack     │
                                 │   Webhook    │
                                 └──────────────┘
```

### 4. Okta-NetSuite Reconciliation Flow

```
┌──────────────┐                    ┌──────────────┐
│     Okta     │                    │   NetSuite   │
│    Users     │                    │    Users     │
└──────┬───────┘                    └──────┬───────┘
       │                                    │
       │ ① Sync Okta Users                 │ ② Fetch NS Users
       │    (status, dept, etc)            │    (active status)
       ▼                                    ▼
┌─────────────────────────────────────────────────────┐
│         Enhanced Data Collection Agent              │
│  • Fetch from Okta (get_users API)                  │
│  • Fetch from NetSuite (RESTlet)                    │
│  • Store both in separate tables                    │
└──────────────────┬──────────────────────────────────┘
                   │
                   │ ③ Both datasets ready
                   ▼
┌─────────────────────────────────────────────────────┐
│           Reconciliation Agent                      │
│  • Compare by email (primary key)                   │
│  • Identify status mismatches                       │
│  • Detect orphaned users                            │
│  • Calculate risk levels                            │
│  • Flag actions needed                              │
└──────────────────┬──────────────────────────────────┘
                   │
                   │ ④ Reconciliation records created
                   ▼
┌─────────────────────────────────────────────────────┐
│              PostgreSQL Database                     │
│  • okta_users table                                 │
│  • user_reconciliations table                       │
│    - MATCHED: Both active                           │
│    - ORPHANED: Active in NS, deprovisioned in Okta  │
│    - MISSING_IN_OKTA: Only in NS                    │
│    - MISSING_IN_NETSUITE: Only in Okta              │
└──────────────────┬──────────────────────────────────┘
                   │
                   │ ⑤ High-risk orphaned users identified
                   ▼
┌─────────────────────────────────────────────────────┐
│           Deactivation Agent                        │
│  • Create approval request                          │
│  • Generate user list                               │
│  • Send to approver                                 │
│  • Wait for approval                                │
└──────────────────┬──────────────────────────────────┘
                   │
                   │ ⑥ Approval request sent
                   ▼
┌─────────────────────────────────────────────────────┐
│              Human Approver                         │
│  • Review user list                                 │
│  • Check justifications                             │
│  • Approve or Reject                                │
└──────────────────┬──────────────────────────────────┘
                   │
       ┌───────────┴───────────┐
       │                       │
       ▼ Approved              ▼ Rejected
┌─────────────────┐     ┌────────────────┐
│  Execute        │     │   Log & Alert  │
│  Deactivation   │     │   No Action    │
└────────┬────────┘     └────────────────┘
         │
         │ ⑦ Deactivate users
         ▼
┌─────────────────────────────────────────────────────┐
│        NetSuite Deactivation Scripts                │
│                                                      │
│  If ≤10 users:                                       │
│  ┌────────────────────────────────────────────┐    │
│  │  RESTlet Script (Single/Small Batch)       │    │
│  │  • Load employee record                    │    │
│  │  • Set isinactive = true                   │    │
│  │  • Add audit comment                       │    │
│  │  • Save record                             │    │
│  └────────────────────────────────────────────┘    │
│                                                      │
│  If >10 users:                                       │
│  ┌────────────────────────────────────────────┐    │
│  │  Map/Reduce Script (Bulk)                  │    │
│  │  getInputData: Parse user IDs              │    │
│  │  map: Deactivate each user                 │    │
│  │  reduce: Aggregate results                 │    │
│  │  summarize: Final report                   │    │
│  └────────────────────────────────────────────┘    │
└──────────────────┬──────────────────────────────────┘
                   │
                   │ ⑧ Results logged
                   ▼
┌─────────────────────────────────────────────────────┐
│              PostgreSQL Database                     │
│  • deactivation_approvals (request tracking)        │
│  • deactivation_logs (audit trail)                  │
│    - user, action, status, timestamp                │
│    - NS status before/after                         │
│    - Okta status at time                            │
└─────────────────────────────────────────────────────┘
```

---

## Database Schema

### Core Tables (Existing)

```sql
┌─────────────────────────────────────────────────────────┐
│                      users                              │
├─────────────────────────────────────────────────────────┤
│ id                UUID PRIMARY KEY                      │
│ user_id           VARCHAR(255) UNIQUE (NS ID)          │
│ internal_id       VARCHAR(50) UNIQUE (NS Internal)     │
│ name              VARCHAR(255)                          │
│ email             VARCHAR(255) UNIQUE                   │
│ status            ENUM(ACTIVE, INACTIVE, SUSPENDED)     │
│ department        VARCHAR(255)                          │
│ subsidiary        VARCHAR(255)                          │
│ employee_id       VARCHAR(100)                          │
│ last_login        TIMESTAMP                             │
│                                                          │
│ -- Context Fields (for SOD analysis)                   │
│ job_function      VARCHAR(100) [IT, FINANCE, OTHER]    │
│ business_unit     VARCHAR(255)                          │
│ title             VARCHAR(255)                          │
│ supervisor        VARCHAR(255)                          │
│ supervisor_id     VARCHAR(100)                          │
│ location          VARCHAR(255)                          │
│ hire_date         TIMESTAMP                             │
│                                                          │
│ synced_at         TIMESTAMP                             │
│ created_at        TIMESTAMP                             │
│ updated_at        TIMESTAMP                             │
└─────────────────────────────────────────────────────────┘
                     │
                     │ 1:N
                     ▼
┌─────────────────────────────────────────────────────────┐
│                   user_roles                            │
├─────────────────────────────────────────────────────────┤
│ id                UUID PRIMARY KEY                      │
│ user_id           UUID FK → users(id)                   │
│ role_id           UUID FK → roles(id)                   │
│ assigned_at       TIMESTAMP                             │
│ assigned_by       VARCHAR(255)                          │
│ notes             TEXT                                  │
└─────────────────────────────────────────────────────────┘
                     │
                     │ N:1
                     ▼
┌─────────────────────────────────────────────────────────┐
│                     roles                               │
├─────────────────────────────────────────────────────────┤
│ id                UUID PRIMARY KEY                      │
│ role_id           VARCHAR(100) UNIQUE                   │
│ role_name         VARCHAR(255)                          │
│ is_custom         BOOLEAN                               │
│ description       TEXT                                  │
│ permission_count  INTEGER                               │
│ permissions       JSON                                  │
│ embedding         vector(384) (pgvector)                │
│ created_at        TIMESTAMP                             │
│ updated_at        TIMESTAMP                             │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                   sod_rules                             │
├─────────────────────────────────────────────────────────┤
│ id                UUID PRIMARY KEY                      │
│ rule_id           VARCHAR(100) UNIQUE                   │
│ rule_name         VARCHAR(255)                          │
│ category          VARCHAR(100) [FINANCIAL, AP, AR, ...]│
│ description       TEXT                                  │
│ conflicting_perms JSON                                  │
│ severity          ENUM(CRITICAL, HIGH, MEDIUM, LOW)     │
│ is_active         BOOLEAN                               │
│ embedding         vector(384) (pgvector)                │
└─────────────────────────────────────────────────────────┘
                     │
                     │ 1:N
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  violations                             │
├─────────────────────────────────────────────────────────┤
│ id                UUID PRIMARY KEY                      │
│ user_id           UUID FK → users(id)                   │
│ rule_id           UUID FK → sod_rules(id)               │
│ scan_id           UUID FK → compliance_scans(id)        │
│ severity          ENUM(CRITICAL, HIGH, MEDIUM, LOW)     │
│ status            ENUM(OPEN, IN_REVIEW, RESOLVED, ...)  │
│ risk_score        FLOAT (0-100)                         │
│ title             VARCHAR(500)                          │
│ description       TEXT                                  │
│ conflicting_roles JSON                                  │
│ conflicting_perms JSON                                  │
│ detected_at       TIMESTAMP                             │
│ resolved_at       TIMESTAMP                             │
│ resolved_by       VARCHAR(255)                          │
│ resolution_notes  TEXT                                  │
└─────────────────────────────────────────────────────────┘
```

### Okta Integration Tables (New - Phase 1 Complete)

```sql
┌─────────────────────────────────────────────────────────┐
│                   okta_users                            │
├─────────────────────────────────────────────────────────┤
│ id                UUID PRIMARY KEY                      │
│ okta_id           VARCHAR(255) UNIQUE                   │
│ email             VARCHAR(255) UNIQUE                   │
│ first_name        VARCHAR(255)                          │
│ last_name         VARCHAR(255)                          │
│ status            ENUM(ACTIVE, SUSPENDED,               │
│                       DEPROVISIONED, STAGED, ...)       │
│ login             VARCHAR(255)                          │
│ activated         TIMESTAMP                             │
│ status_changed    TIMESTAMP                             │
│ last_login        TIMESTAMP                             │
│ last_updated      TIMESTAMP                             │
│ password_changed  TIMESTAMP                             │
│ department        VARCHAR(255)                          │
│ title             VARCHAR(255)                          │
│ employee_number   VARCHAR(100)                          │
│ manager           VARCHAR(255)                          │
│ manager_id        VARCHAR(255)                          │
│ okta_groups       JSON                                  │
│ synced_at         TIMESTAMP                             │
│ created_at        TIMESTAMP                             │
│ updated_at        TIMESTAMP                             │
└─────────────────────────────────────────────────────────┘
                     │
                     │ 1:N
                     ▼
┌─────────────────────────────────────────────────────────┐
│              user_reconciliations                       │
├─────────────────────────────────────────────────────────┤
│ id                UUID PRIMARY KEY                      │
│ netsuite_user_id  UUID FK → users(id)                   │
│ okta_user_id      UUID FK → okta_users(id)              │
│ email             VARCHAR(255)                          │
│ netsuite_status   VARCHAR(50)                           │
│ okta_status       VARCHAR(50)                           │
│ reconciliation_   ENUM(MATCHED, ORPHANED,               │
│   status          MISSING_IN_OKTA,                      │
│                   MISSING_IN_NETSUITE,                  │
│                   STATUS_MISMATCH)                      │
│ discrepancy_      TEXT                                  │
│   reason                                                │
│ risk_level        ENUM(HIGH, MEDIUM, LOW)               │
│ requires_action   BOOLEAN                               │
│ action_required   VARCHAR(100)                          │
│ reconciled_at     TIMESTAMP                             │
│ scan_id           UUID                                  │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│             deactivation_approvals                      │
├─────────────────────────────────────────────────────────┤
│ id                UUID PRIMARY KEY                      │
│ request_id        VARCHAR(100) UNIQUE                   │
│ user_ids          JSON (array of NS IDs)                │
│ user_count        INTEGER                               │
│ status            ENUM(PENDING, APPROVED,               │
│                       REJECTED, EXPIRED)                │
│ requested_by      VARCHAR(255)                          │
│ requested_at      TIMESTAMP                             │
│ approved_by       VARCHAR(255)                          │
│ approved_at       TIMESTAMP                             │
│ rejected_by       VARCHAR(255)                          │
│ rejected_at       TIMESTAMP                             │
│ rejection_reason  TEXT                                  │
│ execution_status  ENUM(NOT_STARTED, IN_PROGRESS,        │
│                       COMPLETED, FAILED, PARTIAL)       │
│ execution_method  ENUM(RESTLET, MAPREDUCE, MANUAL)      │
│ execution_        TIMESTAMP                             │
│   started_at                                            │
│ execution_        TIMESTAMP                             │
│   completed_at                                          │
│ users_deactivated INTEGER                               │
│ users_failed      INTEGER                               │
│ execution_errors  JSON                                  │
│ expires_at        TIMESTAMP                             │
│ approval_metadata JSON                                  │
└─────────────────────────────────────────────────────────┘
                     │
                     │ 1:N
                     ▼
┌─────────────────────────────────────────────────────────┐
│               deactivation_logs                         │
├─────────────────────────────────────────────────────────┤
│ id                UUID PRIMARY KEY                      │
│ netsuite_user_id  UUID FK → users(id)                   │
│ netsuite_         VARCHAR(100)                          │
│   internal_id                                           │
│ email             VARCHAR(255)                          │
│ approval_         UUID FK → deactivation_approvals(id)  │
│   request_id                                            │
│ action            ENUM(DEACTIVATE, REACTIVATE)          │
│ method            ENUM(RESTLET, MAPREDUCE, MANUAL)      │
│ status            VARCHAR(50) [SUCCESS, FAILED, ...]    │
│ error_message     TEXT                                  │
│ performed_by      VARCHAR(255)                          │
│ performed_at      TIMESTAMP                             │
│ reason            TEXT                                  │
│ okta_status_      VARCHAR(50)                           │
│   at_time                                               │
│ netsuite_status_  VARCHAR(50)                           │
│   before                                                │
│ netsuite_status_  VARCHAR(50)                           │
│   after                                                 │
│ log_metadata      JSON                                  │
└─────────────────────────────────────────────────────────┘
```

### Table Relationships

```
users ──┬── 1:N ──▶ user_roles ──┬── N:1 ──▶ roles
        │                        │
        ├── 1:N ──▶ violations ──┴── N:1 ──▶ sod_rules
        │
        ├── 1:N ──▶ user_reconciliations ──┬── N:1 ──▶ okta_users
        │                                   │
        └── 1:N ──▶ deactivation_logs ──────┴── N:1 ──▶ deactivation_approvals

compliance_scans ── 1:N ──▶ violations
                 ── 1:N ──▶ agent_logs
```

### Index Strategy

**High Performance Indexes:**
```sql
-- Users
CREATE INDEX idx_user_email ON users(email);
CREATE INDEX idx_user_status ON users(status);
CREATE INDEX idx_user_job_function ON users(job_function);
CREATE INDEX idx_user_department ON users(department);

-- Violations
CREATE INDEX idx_violation_user_status ON violations(user_id, status);
CREATE INDEX idx_violation_severity ON violations(severity);
CREATE INDEX idx_violation_detected_at ON violations(detected_at);

-- Reconciliations
CREATE INDEX idx_recon_status ON user_reconciliations(reconciliation_status);
CREATE INDEX idx_recon_requires_action ON user_reconciliations(requires_action);
CREATE INDEX idx_recon_risk_level ON user_reconciliations(risk_level);
CREATE INDEX idx_recon_email ON user_reconciliations(email);

-- Okta Users
CREATE INDEX idx_okta_email ON okta_users(email);
CREATE INDEX idx_okta_status ON okta_users(status);
CREATE INDEX idx_okta_synced ON okta_users(synced_at);

-- Deactivation
CREATE INDEX idx_approval_status ON deactivation_approvals(status);
CREATE INDEX idx_approval_requested_at ON deactivation_approvals(requested_at);
CREATE INDEX idx_deactivation_email ON deactivation_logs(email);
CREATE INDEX idx_deactivation_performed_at ON deactivation_logs(performed_at);
```

---

## Business Logic

### 1. SOD Analysis Flowchart

```
                    START
                      │
                      ▼
            ┌─────────────────────┐
            │  Load User from DB  │
            └─────────┬───────────┘
                      │
                      ▼
            ┌─────────────────────┐
            │  Get User's Roles   │
            │  & Permissions      │
            └─────────┬───────────┘
                      │
                      ▼
            ┌─────────────────────┐
            │  Load SOD Rules     │
            │  (18 rules)         │
            └─────────┬───────────┘
                      │
                      ▼
         ┌────────────────────────────┐
         │  For Each Rule:            │
         │  Check if user's roles     │
         │  contain conflicting perms │
         └────────────┬───────────────┘
                      │
                      ▼
              ┌───────────────┐
              │  Conflict?    │
              └───────┬───────┘
                      │
            ┌─────────┴──────────┐
            │                    │
           YES                  NO
            │                    │
            ▼                    ▼
    ┌──────────────────┐   ┌──────────────┐
    │ Check Context-   │   │  Continue to │
    │ Aware Exemptions │   │  Next Rule   │
    └────────┬─────────┘   └──────────────┘
             │
             ▼
    ┌──────────────────┐
    │ Is IT/Systems    │
    │ User + Financial │
    │ Rule?            │
    └────────┬─────────┘
             │
    ┌────────┴─────────┐
    │                  │
   YES                NO
    │                  │
    ▼                  ▼
┌─────────────┐  ┌──────────────┐
│  EXEMPT     │  │   Create     │
│  Skip this  │  │  Violation   │
│  rule       │  │  Record      │
└─────────────┘  └──────┬───────┘
                        │
                        ▼
                 ┌──────────────┐
                 │ Calculate    │
                 │ Risk Score   │
                 │ (0-100)      │
                 └──────┬───────┘
                        │
                        ▼
                 ┌──────────────┐
                 │ Determine    │
                 │ Severity     │
                 │ Level        │
                 └──────┬───────┘
                        │
                        ▼
                 ┌──────────────┐
                 │ Store in DB  │
                 └──────┬───────┘
                        │
                        ▼
                 ┌──────────────┐
                 │ Create Audit │
                 │ Log Entry    │
                 └──────────────┘
                        │
                        ▼
                      END
```

### 2. Risk Scoring Algorithm

```
Risk Score Calculation (0-100 scale):

Base Score = Severity Weight
  • CRITICAL: 100 points
  • HIGH: 75 points
  • MEDIUM: 50 points
  • LOW: 25 points

Modifiers:
  +20: Has "Approve" permission conflict
  +15: Has financial transaction access
  +10: Multiple conflicting roles (>2)
  +5:  Recently assigned role
  +5:  Unreviewed violation

  -10: Mitigating control documented
  -5:  Low-risk department
  -5:  Supervisor approval recorded

Final Score = min(100, Base + Modifiers)

Risk Level Mapping:
  90-100: CRITICAL (Immediate action required)
  70-89:  HIGH (Review within 24 hours)
  40-69:  MEDIUM (Review within 1 week)
  0-39:   LOW (Monitor)
```

### 3. Context-Aware Exemption Logic

```
┌─────────────────────────────────────────────────────┐
│         Context-Aware Exemption Engine              │
└─────────────────────────────────────────────────────┘

INPUT: User, Violation Rule

Step 1: Identify User Job Function
  ├─ From user.job_function field
  ├─ Derived from: department, title, business_unit
  └─ Values: IT/SYSTEMS_ENGINEERING, FINANCE, SALES, OTHER

Step 2: Identify Rule Category
  ├─ From rule.category field
  └─ Values: FINANCIAL, AP, AR, IT_ACCESS, PAYROLL, etc.

Step 3: Apply Exemption Matrix

┌────────────────────┬──────────────────────────────┐
│  Job Function      │  Exempt From Rule Categories │
├────────────────────┼──────────────────────────────┤
│ IT/SYSTEMS_        │ • FINANCIAL                  │
│ ENGINEERING        │ • AP (Accounts Payable)      │
│                    │ • AR (Accounts Receivable)   │
│                    │ • PAYROLL                    │
│                    │ • ACCOUNTING                 │
│                    │                              │
│                    │ NOT Exempt: IT_ACCESS rules  │
├────────────────────┼──────────────────────────────┤
│ FINANCE            │ • IT_ACCESS                  │
│                    │ • SYSTEM_ADMIN               │
│                    │                              │
│                    │ NOT Exempt: FINANCIAL rules  │
├────────────────────┼──────────────────────────────┤
│ OTHER              │ (No blanket exemptions)      │
└────────────────────┴──────────────────────────────┘

Step 4: Make Decision
  IF (user.job_function, rule.category) IN exemption_matrix:
    RETURN: EXEMPT (do not create violation)
  ELSE:
    RETURN: VIOLATION (create violation record)

Example 1: IT User + Financial Rule
  User: job_function = "IT/SYSTEMS_ENGINEERING"
  Rule: category = "FINANCIAL" (AP Entry vs Approval)
  Result: EXEMPT ✅ (IT users need admin access)

Example 2: Finance User + Financial Rule
  User: job_function = "FINANCE"
  Rule: category = "FINANCIAL" (AP Entry vs Approval)
  Result: VIOLATION ❌ (Finance users must follow SOD)

Example 3: IT User + IT Access Rule
  User: job_function = "IT/SYSTEMS_ENGINEERING"
  Rule: category = "IT_ACCESS" (Admin vs Regular User)
  Result: VIOLATION ❌ (Still applies to IT users)
```

### 4. Okta Reconciliation Decision Tree

```
                    START: Compare Users
                            │
                            ▼
                ┌─────────────────────────┐
                │ Does email exist in     │
                │ both Okta and NetSuite? │
                └────────┬────────────────┘
                         │
              ┌──────────┴──────────┐
             YES                   NO
              │                     │
              ▼                     ▼
    ┌────────────────┐    ┌─────────────────────┐
    │ Status Match?  │    │ Exists in Okta only?│
    └────────┬───────┘    └────────┬────────────┘
             │                     │
    ┌────────┴────────┐     ┌─────┴─────┐
   YES               NO     YES          NO
    │                 │      │            │
    ▼                 ▼      ▼            ▼
┌─────────┐   ┌──────────────┐  ┌──────────┐  ┌──────────┐
│MATCHED  │   │ Okta Status? │  │MISSING_  │  │MISSING_  │
│         │   └──────┬───────┘  │IN_       │  │IN_OKTA   │
│Risk:LOW │          │          │NETSUITE  │  │          │
└─────────┘   ┌──────┴──────┐  │          │  │Risk:HIGH │
              │             │   │Risk:LOW  │  └──────────┘
         DEPROVISIONED   ACTIVE │          │
              │             │   └──────────┘
              ▼             ▼
    ┌─────────────────────────────────┐
    │ NetSuite Status?                │
    └─────────┬───────────────────────┘
              │
      ┌───────┴────────┐
   ACTIVE          INACTIVE
      │                 │
      ▼                 ▼
┌─────────────┐  ┌────────────────┐
│  ORPHANED   │  │ STATUS_        │
│             │  │ MISMATCH       │
│ Risk: HIGH  │  │                │
│ Action:     │  │ Risk: MEDIUM   │
│ DEACTIVATE  │  │ Action:        │
│             │  │ INVESTIGATE    │
└─────────────┘  └────────────────┘
```

### 5. Deactivation Approval Workflow

```
                        START
                          │
                          ▼
              ┌───────────────────────┐
              │ Reconciliation Agent  │
              │ identifies orphaned   │
              │ users (HIGH risk)     │
              └───────────┬───────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │ Deactivation Agent    │
              │ creates approval      │
              │ request               │
              └───────────┬───────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │ Generate user list    │
              │ with context:         │
              │ • Name, email         │
              │ • Okta status         │
              │ • Last login          │
              │ • Reason              │
              └───────────┬───────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │ Send to approver      │
              │ • Email notification  │
              │ • Slack alert         │
              │ • Dashboard entry     │
              └───────────┬───────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │ Wait for approval     │
              │ (max 48 hours)        │
              └───────────┬───────────┘
                          │
          ┌───────────────┴────────────────┐
          │                                │
      APPROVED                         REJECTED
          │                                │
          ▼                                ▼
┌─────────────────────┐        ┌──────────────────┐
│ Check user count    │        │ Log rejection    │
└─────────┬───────────┘        │ Send notification│
          │                     │ Update status    │
   ┌──────┴──────┐             └──────────────────┘
   │             │                      │
 ≤10           >10                      ▼
   │             │                    END
   ▼             ▼
┌────────┐  ┌──────────┐
│RESTlet │  │Map/Reduce│
│Script  │  │ Script   │
└────┬───┘  └────┬─────┘
     │           │
     └─────┬─────┘
           │
           ▼
┌─────────────────────┐
│ Execute deactivation│
│ in NetSuite         │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ For each user:      │
│ • Load record       │
│ • Set inactive=true │
│ • Add audit comment │
│ • Save record       │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Log results:        │
│ • Success count     │
│ • Failure count     │
│ • Error details     │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Update approval     │
│ record status       │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Send completion     │
│ notification        │
└─────────────────────┘
          │
          ▼
        END
```

---

## Component Specifications

### 1. LLM Abstraction Layer

**Purpose**: Provide provider-agnostic interface for all LLM operations

**Components**:

#### A. Base Provider (`services/llm/base.py`)
```python
class BaseLLMProvider(ABC):
    @abstractmethod
    def generate(messages, temperature, max_tokens) -> LLMResponse

    @abstractmethod
    def generate_stream(messages) -> Iterator[str]

    @abstractmethod
    def count_tokens(text: str) -> int

    @abstractmethod
    def get_model_info() -> Dict[str, Any]

    @abstractmethod
    def test_connection() -> bool

    def calculate_cost(input_tokens, output_tokens) -> float
```

#### B. Provider Implementations
- **AnthropicProvider**: Claude Opus 4.6, Sonnet 4.5, Haiku 4.5
- **OpenAIProvider**: GPT-4o, GPT-4 Turbo, GPT-4o-mini
- **GoogleProvider**: Gemini 1.5 Pro, Gemini 1.5 Flash
- **CohereProvider**: Command R+, Command R
- **AzureProvider**: Azure OpenAI (all models)
- **LocalProvider**: Ollama, vLLM (local models)

#### C. Factory Pattern (`services/llm/factory.py`)
```python
class LLMProviderFactory:
    _providers = {
        'anthropic': AnthropicProvider,
        'openai': OpenAIProvider,
        'google': GoogleProvider,
        # ...
    }

    @classmethod
    def create_provider(config: LLMConfig) -> BaseLLMProvider

    @classmethod
    def register_provider(name: str, provider_class: Type)
```

#### D. Config Manager (`services/llm/config_manager.py`)
```python
class LLMConfigManager:
    def load_config() -> None
    def save_config() -> None
    def get_provider_config(provider_name) -> LLMConfig
    def get_llm_provider(provider_name) -> BaseLLMProvider
    def encrypt_api_key(key: str) -> str
    def set_provider_config(**kwargs) -> None
```

#### E. Encryption (`services/llm/config_manager.py`)
```python
class ConfigEncryption:
    def __init__(master_key: str)
    def encrypt(plaintext: str) -> str
    def decrypt(ciphertext: str) -> str
    @staticmethod
    def generate_key() -> str
```

**Configuration Format**:
```yaml
default_provider: anthropic

providers:
  anthropic:
    model: claude-sonnet-4-5-20250929
    api_key_env: ANTHROPIC_API_KEY
    temperature: 0.0
    max_tokens: 4096
    timeout: 120
    max_retries: 3
```

**Usage Example**:
```python
from services.llm import get_llm_from_config, LLMMessage

# Load from config
llm = get_llm_from_config()

# Generate
messages = [LLMMessage(role="user", content="Analyze this...")]
response = llm.generate(messages)

# Access results
print(response.content)
print(f"Cost: ${response.cost:.4f}")
print(f"Tokens: {response.usage['total_tokens']}")
```

### 2. Okta Integration Layer

**Components**:

#### A. Okta Client (`services/okta_client.py`)
```python
class OktaClient:
    def __init__(domain, api_token)
    def get_users(status, limit) -> Dict
    def get_user_by_email(email) -> Optional[Dict]
    def get_user_by_id(user_id) -> Optional[Dict]
    def get_active_users() -> Dict
    def get_deprovisioned_users() -> Dict
    def get_user_groups(user_id) -> Dict
    def transform_user_data(okta_user) -> Dict
    def fetch_all_users_with_groups() -> Dict
    def test_connection() -> bool
```

#### B. Okta User Repository (`repositories/okta_user_repository.py`)
```python
class OktaUserRepository:
    def create_user(user_data) -> OktaUser
    def upsert_user(user_data) -> OktaUser
    def bulk_upsert_users(users_data) -> Dict
    def get_user_by_okta_id(okta_id) -> OktaUser
    def get_user_by_email(email) -> OktaUser
    def get_active_users() -> List[OktaUser]
    def get_deprovisioned_users(days) -> List[OktaUser]
    def get_user_count_by_status() -> Dict[str, int]
```

#### C. Reconciliation Repository (`repositories/user_reconciliation_repository.py`)
```python
class UserReconciliationRepository:
    def create_reconciliation(recon_data) -> UserReconciliation
    def get_orphaned_users(risk_level) -> List
    def get_high_risk_discrepancies() -> List
    def get_reconciliations_requiring_action() -> List
    def get_reconciliation_summary(scan_id) -> Dict
    def bulk_create_reconciliations(data) -> Dict
```

#### D. Deactivation Repositories
```python
class DeactivationApprovalRepository:
    def create_approval_request(request_data) -> DeactivationApproval
    def get_pending_approvals() -> List
    def approve_request(request_id, approved_by) -> DeactivationApproval
    def reject_request(request_id, rejected_by, reason) -> DeactivationApproval
    def start_execution(request_id, method) -> DeactivationApproval
    def complete_execution(request_id, stats) -> DeactivationApproval

class DeactivationLogRepository:
    def create_log(log_data) -> DeactivationLog
    def get_logs_by_email(email) -> List
    def get_logs_by_approval(approval_id) -> List
    def get_failed_deactivations(hours) -> List
    def get_deactivation_statistics(days) -> Dict
    def get_audit_report(start_date, end_date) -> Dict
```

### 3. NetSuite Scripts

#### A. User Deactivation RESTlet
**File**: `netsuite_scripts/user_deactivation_restlet.js`
**Type**: RESTlet (SuiteScript 2.1)
**Purpose**: Single/small batch deactivation (≤10 users)

**Endpoints**:
- `POST /restlet` - Deactivate users
- `GET /restlet?user_ids=1,2,3` - Get user status

**Request Format**:
```javascript
{
  "user_ids": ["123", "456"],
  "dry_run": false,
  "reason": "Terminated in Okta",
  "requested_by": "admin@company.com"
}
```

**Response Format**:
```javascript
{
  "success": true,
  "dry_run": false,
  "total": 2,
  "deactivated": 2,
  "failed": 0,
  "errors": [],
  "details": [...]
}
```

#### B. User Deactivation Map/Reduce
**File**: `netsuite_scripts/user_deactivation_mapreduce.js`
**Type**: Map/Reduce (SuiteScript 2.1)
**Purpose**: Bulk deactivation (>10 users)

**Script Parameters**:
- `custscript_user_ids_to_deactivate` - Comma-separated IDs
- `custscript_deactivation_reason` - Reason text
- `custscript_requested_by` - Requestor email
- `custscript_dry_run` - Preview mode

**Stages**:
1. **getInputData**: Parse user IDs from parameter
2. **map**: Process each user (load, deactivate, save)
3. **reduce**: Aggregate results by status
4. **summarize**: Generate final report

### 4. Agent Specifications

#### Data Collection Agent
- **Purpose**: Fetch user data from NetSuite and Okta
- **Methods**:
  - `fetch_users_from_netsuite(emails)`
  - `fetch_users_from_okta(status)`
  - `sync_users_to_database()`
- **Performance**: 2 seconds per NetSuite user, 200 users/sec from Okta

#### SOD Analyzer Agent
- **Purpose**: Detect SOD violations with context-aware exemptions
- **Methods**:
  - `analyze_user(user_id)`
  - `analyze_all_users()`
  - `_check_rule_violation(user, roles, rule)`
  - `_is_it_systems_user(user) -> bool`
  - `_is_financial_rule(rule) -> bool`
- **Performance**: 0.009 seconds per user, 185 users/sec
- **Accuracy**: 95% with context-aware logic (67% false positive reduction)

#### Risk Assessor Agent
- **Purpose**: Calculate risk scores for users and organization
- **Methods**:
  - `calculate_user_risk_score(user_id)`
  - `assess_organization_risk()`
  - `get_high_risk_users(threshold)`
- **Algorithm**: Multi-factor scoring (0-100 scale)

#### Reconciliation Agent (New - Phase 2)
- **Purpose**: Compare Okta and NetSuite user states
- **Methods**:
  - `reconcile_users()`
  - `identify_orphaned_users()`
  - `calculate_discrepancy_risk()`
  - `generate_reconciliation_report()`
- **Status**: Planned (Phase 2)

#### Deactivation Agent (New - Phase 2)
- **Purpose**: Manage user deactivation with approval workflow
- **Methods**:
  - `create_deactivation_request(user_ids)`
  - `execute_deactivation(approval_id)`
  - `_deactivate_via_restlet(user_ids)`
  - `_deactivate_via_mapreduce(user_ids)`
- **Status**: Planned (Phase 2)

#### Knowledge Base Agent
- **Purpose**: Semantic search over SOD rules and historical data
- **Methods**:
  - `search_similar_rules(query, top_k)` - Find similar rules via vector search
  - `find_similar_violations(violation_id)` - Find related past violations
  - `get_knowledge_base_stats()` - Get embedding statistics
  - `initialize_rules_from_json()` - Generate embeddings for rules
- **Technology**: HuggingFace embeddings (384-dim) + pgvector cosine similarity
- **Performance**: <100ms for top-k vector search queries
- **Status**: ✅ Fully operational with all 18 rules embedded

#### Notifier Agent
- **Purpose**: Multi-channel notifications with AI-powered insights
- **Methods**:
  - `send_violation_alert(violation_id)`
  - `send_compliance_report(scan_summary)`
  - `generate_user_comparison_table(user_emails)`
  - `_generate_ai_analysis(user, violations, roles)` **← Uses LLM Abstraction**
- **Channels**: Email (SendGrid), Slack, Console
- **LLM Integration**: ✅ Migrated to LLM abstraction layer

### 5. Vector Search Implementation (pgvector)

**Architecture**:
```
┌──────────────────────────────────────────────────────┐
│           Knowledge Base Agent (pgvector)            │
├──────────────────────────────────────────────────────┤
│                                                       │
│  ┌────────────────────────────────────────────┐     │
│  │        Embedding Service                   │     │
│  │  • HuggingFace sentence-transformers       │     │
│  │  • Model: all-MiniLM-L6-v2                 │     │
│  │  • Dimension: 384                          │     │
│  │  • Caching: Optional                       │     │
│  └────────────────┬───────────────────────────┘     │
│                   │                                  │
│                   ▼                                  │
│  ┌────────────────────────────────────────────┐     │
│  │        Vector Search Service               │     │
│  │  • Distance metric: Cosine similarity      │     │
│  │  • Operator: <=> (pgvector)                │     │
│  │  • SQL casting: CAST(:vector AS vector)    │     │
│  │  • Min similarity threshold: 0.3           │     │
│  └────────────────┬───────────────────────────┘     │
│                   │                                  │
│                   ▼                                  │
│  ┌────────────────────────────────────────────┐     │
│  │        PostgreSQL 17 + pgvector            │     │
│  │                                            │     │
│  │  sod_rules:                                │     │
│  │    • embedding vector(384)                 │     │
│  │    • 18 rules embedded                     │     │
│  │                                            │     │
│  │  roles:                                    │     │
│  │    • embedding vector(384)                 │     │
│  │                                            │     │
│  │  violations:                               │     │
│  │    • embedding vector(384)                 │     │
│  └────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────┘
```

**Implementation Details**:

**Embedding Generation**:
```python
from services.embedding_service import EmbeddingService

# Initialize
embedding_service = EmbeddingService(
    provider="huggingface",
    dimension=384,
    cache_embeddings=True
)

# Generate rule embedding
rule_text = f"{rule_name} {description} {category}"
embedding = embedding_service.embed_rule(rule_data)
# Returns: numpy array of shape (384,)
```

**Vector Search Query**:
```sql
SELECT
    *,
    1 - (embedding <=> CAST(:query_vector AS vector)) AS similarity
FROM sod_rules
WHERE is_active = true
  AND (1 - (embedding <=> CAST(:query_vector AS vector))) >= 0.3
ORDER BY embedding <=> CAST(:query_vector AS vector)
LIMIT 3
```

**Performance Characteristics**:
- **Embedding generation**: 10-50ms per text
- **Vector search**: <100ms for top-k=10 queries
- **Storage overhead**: 1.5KB per 384-dim vector
- **Similarity accuracy**: 85%+ for related SOD rules

**Key Features**:
1. ✅ Automatic embedding generation on rule creation
2. ✅ Lazy loading - embeddings generated on first search if missing
3. ✅ Cosine similarity for semantic matching
4. ✅ Configurable similarity threshold (default: 0.3)
5. ✅ Support for multiple tables (rules, roles, violations)
6. ✅ Type-safe SQL casting for pgvector compatibility

**Example Search Results**:
```
Query: "financial approval conflicts"

Results:
1. AP Entry vs. Approval Separation (Similarity: 0.55)
   - Matches: "approve", "financial", "bills"

2. Journal Entry Creation vs. Approval (Similarity: 0.55)
   - Matches: "approve", "journal", "entries"

3. Budget Creation vs. Budget Approval (Similarity: 0.50)
   - Matches: "approve", "budgets"
```

**Migration Notes**:
- PostgreSQL 16 → 17 required for pgvector 0.8.1 compatibility
- Schema updates: `ALTER COLUMN embedding TYPE vector(384)`
- Dimension change: 1536 → 384 for HuggingFace compatibility
- SQL casting: Added `CAST(:param AS vector)` to avoid syntax errors

---

## Integration Points

### 1. NetSuite Integration

**Protocol**: OAuth 1.0a with Token-Based Authentication
**Endpoint**: RESTlet hosted in NetSuite SuiteScripts
**Data Transfer**: JSON over HTTPS

**Search RESTlet (v5)**:
- **Script ID**: 3685
- **Performance**: 2 seconds per targeted search
- **Returned Fields**: user_id, name, email, status, roles[], permissions[], job_function, business_unit, supervisor, location, hire_date

**Deactivation RESTlet**:
- **Purpose**: Deactivate single/small batch (≤10 users)
- **Authentication**: Same OAuth 1.0a
- **Governance**: 10 usage units per user

**Map/Reduce Script**:
- **Purpose**: Bulk deactivation (>10 users)
- **Execution**: Asynchronous, scheduled
- **Governance**: Parallel processing across multiple queues

### 2. Okta Integration

**Protocol**: REST API with SSWS Token
**Base URL**: `https://{domain}.okta.com/api/v1`
**Authentication**: `Authorization: SSWS {api_token}`

**Endpoints Used**:
- `GET /users` - List users with filters
- `GET /users/{id}` - Get user by ID
- `GET /users/{id}/groups` - Get user groups

**Rate Limits**:
- Standard: 1,000 requests/minute
- Pagination: 200 users per page

### 3. LLM Provider Integration

**Supported Providers**:
- **Anthropic**: Claude API (Messages API)
- **OpenAI**: Chat Completions API
- **Google**: Generative AI API
- **Cohere**: Chat API
- **Azure**: Azure OpenAI Service
- **Local**: Ollama (localhost:11434), vLLM (OpenAI-compatible)

**Common Interface**:
```python
response = llm.generate(
    messages=[LLMMessage(role="user", content="...")],
    temperature=0.0,
    max_tokens=4096
)
```

**Response Format**:
```python
LLMResponse(
    content="...",
    provider="anthropic",
    model="claude-sonnet-4-5",
    usage={'input_tokens': 100, 'output_tokens': 50},
    cost=0.0005,
    latency_ms=1234.56
)
```

### 4. Database Integration

**PostgreSQL 17**:
- **Connection**: psycopg2 via SQLAlchemy ORM
- **Pooling**: SQLAlchemy connection pool (size=5-20)
- **Extensions**:
  - pgvector 0.8.1 for vector embeddings
  - uuid-ossp for UUID generation
- **Vector Operations**:
  - Cosine similarity search using `<=>` operator
  - 384-dimension embeddings (HuggingFace MiniLM)
  - Automatic type casting in SQL queries

**Redis 7**:
- **Purpose**: LLM response and analysis result caching
- **Status**: ✅ Fully implemented and operational
- **Use Cases**:
  - AI analysis caching (primary)
  - Violation detection results
  - Risk score calculations
  - User compliance summaries
- **Connection**: redis-py client
- **Performance**:
  - Cache HIT: <10ms
  - Cache MISS + LLM: 1-3 seconds
  - Cost reduction: 50-90%
  - Hit rate: 50-70% typical

### 5. MCP (Model Context Protocol) Integration 🆕

**Protocol**: JSON-RPC 2.0 over HTTP
**Transport**: stdio (Claude Desktop), HTTP (Claude Web API)
**Port**: 8080 (configurable via MCP_SERVER_PORT)
**Authentication**: API Key in X-API-Key header

**MCP Server** (`mcp/mcp_server.py`):
- FastAPI + Uvicorn ASGI server
- 20 registered MCP tools
- Async tool execution
- Health monitoring endpoint
- Tool discovery via `/tools` endpoint
- Request logging and error handling

**Tool Categories**:
1. **System Management (5 tools)**: list_systems, get_user_violations, remediate_violation, schedule_review, get_violation_stats
2. **Data Synchronization (5 tools)**: start_collection_agent, stop_collection_agent, get_collection_agent_status, trigger_manual_sync, list_all_users
3. **SOD Analysis (8 tools)**: analyze_access_request, query_sod_rules, get_compensating_controls, validate_job_role, check_permission_conflict, get_permission_categories, search_permissions, **analyze_role_permissions** 🔥
4. **Knowledge Base (2 tools)**: query_knowledge_base, perform_access_review

**NEW TOOL: analyze_role_permissions** 🔥

**Purpose**: Internal role conflict analysis - identifies SOD violations within a single role

**Pattern**: Agent Response with Attachments
- Agent performs comprehensive analysis with database access
- Agent generates detailed professional markdown report
- Agent saves report to `output/role_analysis/{role_name}_{timestamp}.md`
- Agent returns concise summary for LLM to present
- User receives both: conversational response + detailed attachment
- Benefits: No context window limits, shareable reports, audit trail

**Parameters**:
```json
{
  "role_name": "string (required)",
  "include_remediation_plan": "boolean (optional, default: true)",
  "output_format": "markdown|json|both (optional, default: markdown)"
}
```

**Process**:
1. Query database for role permissions with levels (View/Create/Edit/Full)
2. Load permission mapping (341 NetSuite permissions)
3. Categorize permissions (transaction_entry, transaction_payment, etc.)
4. Apply 5×5 conflict matrices per SOD rule
5. Detect conflicts using category pairs + level severity
6. Group conflicts by severity (CRITICAL, HIGH, MEDIUM)
7. Generate comprehensive markdown report with:
   - Executive summary with risk assessment
   - All conflicts with permission pairs and levels
   - Permission breakdown by category
   - Three remediation options (split role, reduce permissions, add controls)
   - Level modification recommendations table
   - Testing plan and audit compliance
8. Save report to filesystem
9. Return formatted summary

**Response Format**:
```
Internal Role Conflict Analysis: {role_name}

📊 EXECUTIVE SUMMARY
• Total Permissions: {count}
• Internal Conflicts Found: {count}
• Risk Assessment: 🔴 CRITICAL / 🟠 HIGH / 🟡 MEDIUM

🔥 TOP 5 CRITICAL CONFLICTS
1. 🔴 CRIT - {permission1} + {permission2}
   Conflict: {category1} ({level1}) ↔ {category2} ({level2})
   Inherent Risk: {score}/100
...

💾 DETAILED REPORT SAVED
File: output/role_analysis/{role_name}_{timestamp}.md

🎯 RECOMMENDED NEXT STEPS
1. Review detailed report for complete analysis
2. Consider role split or permission reduction
3. Implement compensating controls if role must remain as-is
```

**Example Usage** (Claude Desktop):
```
User: "Analyze the Fivetran - Cash Accountant role for conflicts"

Claude calls: analyze_role_permissions({
  "role_name": "Fivetran - Cash Accountant",
  "include_remediation_plan": true
})

Response:
- Summary with 181 conflicts found
- Top 5 critical conflicts shown inline
- File path to full 50-page detailed report
- Recommended next steps
```

**Performance**:
- Analysis time: ~2 seconds for 160 permissions
- Report generation: ~500ms
- File write: <100ms
- Total latency: <3 seconds

**Use Cases**:
- Pre-deployment role design review
- Existing role audit and cleanup
- Regulatory compliance assessments (SOX, PCI-DSS)
- Risk reduction initiatives
- Role consolidation projects

**Report Format** (Markdown):
- Executive Summary (risk level, conflict counts)
- Detailed Conflict Analysis (all conflicts by severity)
- Permission Breakdown (grouped by category with counts)
- Remediation Recommendations (3 options with cost/timeline)
- Level Modification Table (specific downgrades)
- Testing Plan (validation steps)
- Audit Compliance (regulatory alignment)

**Integration**:
- MCP tool handler: `mcp/mcp_tools.py::analyze_role_permissions_handler()`
- Database queries: PostgreSQL via SQLAlchemy
- File output: `output/role_analysis/` directory
- Report naming: `{role_name}_{YYYYMMDD}_{HHMMSS}.md`

---

## Semantic Tool Router

**Added**: Mar 2026 | **File**: `utils/semantic_router.py`

Replaces the regex router as the primary tool-selection mechanism for the Slack bot dispatch turn. Uses dense vector similarity rather than keyword pattern matching so that novel query phrasings continue to surface the correct tools.

### Architecture

```
User Query (string)
       │
       ▼
┌─────────────────────────────────────────────────────┐
│              SemanticToolRouter                      │
│                                                      │
│  At startup (_build_index):                          │
│  ┌──────────────────────────────────────────────┐   │
│  │  TOOL_EXEMPLARS dict                         │   │
│  │  tool_name → description + 3–5 sample queries│   │
│  │  (query-to-query similarity > query-to-desc) │   │
│  └──────────────────┬───────────────────────────┘   │
│                     │                                │
│                     ▼                                │
│  ┌──────────────────────────────────────────────┐   │
│  │  SentenceTransformer.encode(all tool texts)  │   │
│  │  → float32 numpy array, unit-normalised      │   │
│  │  shape: n_tools × 384                        │   │
│  │  ~200ms one-time cost at startup             │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  Per query (select):                                 │
│  ┌──────────────────────────────────────────────┐   │
│  │  encode(query)  →  vector [384]              │   │
│  │  dot_product(query_vec, tool_matrix)         │   │
│  │  = cosine similarity (vectors are normalised)│   │
│  │  argsort(desc) → top-k tool names           │   │
│  │  append always_include tools at end          │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
       │
       ▼
  Top-k tool names (default k=8)
```

### Model

| Property | Value |
|----------|-------|
| Model ID | `sentence-transformers/all-MiniLM-L6-v2` |
| Embedding dimension | 384 |
| Inference | Local — no API key, no network call |
| Normalisation | Unit-normalised float32 (enables dot product as cosine sim) |

### Key Design Decisions

**TOOL_EXEMPLARS rather than raw descriptions**: Each entry in `TOOL_EXEMPLARS` concatenates the tool's description with 3–5 representative example queries. Because the encoder was trained on sentence pairs, query-to-query similarity is measurably higher than query-to-description similarity, which directly improves recall on novel phrasings.

**always_include list**: Tools that must always appear in the Haiku dispatch context (e.g., `list_systems`) are appended after the top-k results rather than inserted at position 0. This preserves the semantic ranking of the primary tools and avoids pushing relevant results off the end of the shortlist.

**Singleton via `get_router()`**: The index is built once at process start. `update_tools(tools)` rebuilds the index after a `/tools/refresh` call so the gateway and router stay in sync without a restart.

**Fallback**: If `sentence-transformers` is unavailable at import time, `semantic_select_tools()` transparently falls back to the keyword router (`select_tools_for_intent` in `utils/tool_router.py`). No calling-code change is required.

### Class Interface

```python
class SemanticToolRouter:
    def __init__(self, tools: list[dict], always_include: list[str] = None)
    def _build_index(self) -> None
        # Encodes all tool texts; stores unit-normalised float32 matrix
    def select(self, query: str, k: int = 8) -> list[str]
        # Returns top-k tool names + always_include appended at end
    def update_tools(self, tools: list[dict]) -> None
        # Rebuilds index; called after /tools/refresh

# Module-level helpers (drop-in replacements for select_tools_for_intent)
def get_router() -> SemanticToolRouter          # singleton accessor
def semantic_select_tools(query, tools, k=8, always_include=None) -> list[str]
    # Falls back to keyword router if model unavailable
```

### Performance Characteristics

| Operation | Latency | Notes |
|-----------|---------|-------|
| Index build (37 tools) | ~200ms | One-time at startup, MPS-accelerated on Apple Silicon |
| Per-query select | ~2ms | Single encode + matrix multiply |
| Token savings vs full schema | ~8K tokens/request | Same as keyword router — only top-k schemas sent to Haiku |

---

## Evaluation Suite

**Added**: Mar 2026 | **Directory**: `eval/`

Systematic offline evaluation of tool-selection routers, integrated with LangSmith for experiment tracking and side-by-side comparison.

### File Inventory

| File | Purpose |
|------|---------|
| `eval/golden_set.py` | Dataset definitions + `push_to_langsmith()` |
| `eval/evaluators.py` | Five metric evaluators (LangSmith 0.4.x signature) |
| `eval/run_eval.py` | CLI runner — selects router, suite, and live/stub mode |
| `eval/__init__.py` | Package marker |

### Datasets (`eval/golden_set.py`)

Two datasets are defined and pushed to LangSmith:

**`compliance-tool-selection-v1`** — 32 queries for router evaluation.
Each example contains:
- `input`: natural-language query string
- `expected_tool`: single primary correct tool name
- `relevant_tools`: dict mapping tool names to graded relevance scores (0 = irrelevant, 1 = acceptable, 2 = ideal) used for NDCG

**`compliance-answer-quality-v1`** — 10 queries for end-to-end faithfulness evaluation.
Each example contains:
- `input`: query string
- `expected_facts`: list of strings that must appear in the final Opus answer

### Evaluators (`eval/evaluators.py`)

All evaluators follow the LangSmith 0.4.x function signature:

```python
fn(outputs: dict, reference_outputs: dict) -> dict
# Returns: {"key": metric_name, "score": float}
```

| Evaluator | Factory / Name | Description |
|-----------|---------------|-------------|
| `hit_rate_at_k(k)` | Factory, returns evaluator fn | Binary: 1.0 if `expected_tool` appears in the top-k returned tools, else 0.0 |
| `mrr_evaluator` | Direct fn | 1 / rank of the first relevant tool (reciprocal rank). 0.0 if not found in results. |
| `ndcg_at_k(k)` | Factory, returns evaluator fn | Normalised Discounted Cumulative Gain using graded `relevant_tools` scores. Rewards placing highly-relevant tools at lower rank positions. |
| `precision_at_k(k)` | Factory, returns evaluator fn | Fraction of the top-k returned tools that have a graded relevance score > 0 |
| `faithfulness_evaluator` | Direct fn | LLM-as-judge (Claude Haiku 4.5): does the answer contain the facts listed in `expected_facts`? Returns float 0.0–1.0. |

### CLI Runner (`eval/run_eval.py`)

```bash
# Evaluate keyword router on tool-selection dataset
python -m eval.run_eval --router=keyword

# Evaluate semantic router
python -m eval.run_eval --router=semantic

# Compare both back-to-back (two LangSmith experiments)
python -m eval.run_eval --suite=compare

# Answer quality (faithfulness) — requires live MCP at :8080
python -m eval.run_eval --suite=answer_quality --live

# Use live tool schemas instead of stubs
python -m eval.run_eval --router=semantic --live
```

**`--router`**: `keyword` | `semantic` — selects the router under test.
**`--suite`**: `compare` runs both routers back-to-back; `answer_quality` runs faithfulness eval.
**`--live`**: fetches tool schemas from the running MCP server at `:8080` instead of embedded stubs.

### LangSmith Integration

```python
from langsmith import evaluate

evaluate(
    target,                          # callable: input → outputs dict
    data=dataset_name,               # "compliance-tool-selection-v1"
    evaluators=[hit_rate_at_k(10), mrr_evaluator, ndcg_at_k(10)],
    experiment_prefix="semantic-router-v1"
)
```

Results appear in **smith.langchain.com → project `compliance-agent` → Datasets → Experiments**. Each run is a separate named experiment, enabling side-by-side metric comparison across router versions.

Required environment variable: `LANGSMITH_API_KEY` (add to `compliance-agent/.env`).

### Metric Results (Mar 2026 Benchmark)

Evaluated on `compliance-tool-selection-v1` (32 queries):

| Metric | Baseline (regex) | Fixed regex | Semantic |
|--------|-----------------|-------------|----------|
| hit_rate_at_10 | 0.72 | 0.78 | **1.00** |
| hit_rate_at_5 | 0.56 | 0.72 | **0.97** |
| mrr | 0.18 | 0.41 | **0.91** |
| ndcg_at_10 | 0.37 | 0.60 | **0.89** |
| precision_at_5 | 0.24 | 0.33 | **0.39** |

**Key observations**:
- The semantic router achieves perfect hit_rate_at_10 (1.00) — the correct tool appears in the top 10 for every query in the golden set.
- MRR improvement from 0.18 → 0.91 indicates the correct tool is now consistently ranked first or second rather than being buried in the shortlist.
- The regex fixes (plural/singular patterns, added `remediation` and `role_analysis` patterns) provided a meaningful intermediate improvement, confirming the baseline gap was partly a pattern maintenance problem. The semantic router eliminates that maintenance burden entirely.
- precision_at_5 remains modest (0.39) because the 37-tool corpus contains many thematically related tools; the top 5 will always include some borderline relevance. This is expected and acceptable — Haiku's dispatch turn handles the final selection.

---

## Security & Encryption

### 1. API Key Encryption

**Algorithm**: Fernet (symmetric encryption)
**Key Derivation**: PBKDF2 with SHA256
**Key Storage**: Environment variable `MASTER_ENCRYPTION_KEY`

**Encryption Process**:
```python
from cryptography.fernet import Fernet

# Generate key (one time)
key = Fernet.generate_key()  # Store in MASTER_ENCRYPTION_KEY

# Encrypt API key
cipher = Fernet(key)
encrypted = cipher.encrypt(b"sk-ant-api03-...")

# Store encrypted key in config
```

**Decryption Process**:
```python
# At runtime
cipher = Fernet(os.getenv('MASTER_ENCRYPTION_KEY'))
api_key = cipher.decrypt(encrypted_key).decode()

# Use decrypted key
llm = create_llm(provider="anthropic", api_key=api_key)
```

### 2. Configuration Security

**Best Practices**:
1. ✅ Use environment variables for API keys
2. ✅ Encrypt keys in config files
3. ✅ Store master key in vault (AWS Secrets Manager, HashiCorp Vault)
4. ✅ Rotate keys quarterly
5. ✅ Separate keys by environment (dev/staging/prod)
6. ✅ Never commit `.env` or config with real keys to git

**Config File Security**:
```yaml
# Option 1: Environment variable (recommended)
api_key_env: ANTHROPIC_API_KEY

# Option 2: Encrypted key (for config files)
api_key: gAAAAABk...encrypted...
encrypted: true

# Option 3: Direct (NEVER for production!)
# api_key: sk-ant-...  ← DON'T DO THIS
```

### 3. Database Security

**Connection Security**:
- SSL/TLS encryption for all connections
- Password authentication
- Connection pooling with timeout

**Data Security**:
- Sensitive fields encrypted at rest (future)
- API keys never stored in database
- Audit trail for all changes

**Access Control**:
- Principle of least privilege
- Separate read/write credentials
- Database user per environment

### 4. NetSuite Security

**OAuth 1.0a**:
- Consumer key + consumer secret
- Token ID + token secret
- Signature method: HMAC-SHA256
- Nonce + timestamp for replay protection

**RESTlet Security**:
- HTTPS only
- Token-based authentication
- Script deployment restrictions
- Audit logging enabled

### 5. Okta Security

**SSWS Token**:
- Long-lived API token
- Scoped permissions
- Rotated quarterly
- Stored encrypted

**API Security**:
- HTTPS only
- Rate limiting enforced
- IP whitelisting (optional)
- Audit logs enabled

---

## Performance Metrics

### Current Performance (Verified 2026-02-09)

| Metric | Value | Status |
|--------|-------|--------|
| **NetSuite User Search** | 2 sec/user | ✅ 55x faster |
| **SOD Analysis** | 0.009 sec/user | ✅ Optimized |
| **Throughput** | 185 users/sec | ✅ Production-ready |
| **Full Population Scan** | 10.5 sec (24 users) | ✅ Scales linearly |
| **Database Queries** | <10ms average | ✅ Indexed |
| **LLM Response** | 1-3 sec | ✅ Normal |
| **Cost per User Analysis** | $0.0005 | ✅ Cost-effective |

### Performance Targets

| Component | Target | Current | Status |
|-----------|--------|---------|--------|
| User Search (NetSuite) | <5 sec | 2 sec | ✅ Exceeds |
| SOD Analysis | <0.1 sec/user | 0.009 sec | ✅ Exceeds |
| Risk Assessment | <1 sec/org | 0.5 sec | ✅ Exceeds |
| AI Analysis | <5 sec | 1-3 sec | ✅ Meets |
| Database Query | <100ms | <10ms | ✅ Exceeds |
| Full Scan (1000 users) | <10 min | ~5.4 min | ✅ Exceeds |

### Scalability

**Linear Scaling**:
- Analysis time = 0.009 × N users
- 1,000 users = 9 seconds
- 10,000 users = 90 seconds
- 100,000 users = 15 minutes

**Bottlenecks Identified**:
1. NetSuite API rate limits (10 req/sec)
2. LLM API latency (1-3 sec per call)
3. Database write throughput (1000 writes/sec)

**Optimization Strategies**:
1. ✅ Batch processing for NetSuite
2. ✅ Caching for repeated queries
3. ✅ Parallel agent execution
4. ⏳ Connection pooling (planned)
5. ⏳ Read replicas (planned)

---

## Deployment

### System Requirements

**Hardware**:
- **CPU**: 4+ cores recommended
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 50GB SSD minimum
- **Network**: 100 Mbps+ for API calls

**Software**:
- **OS**: macOS, Linux, Windows (with WSL)
- **Python**: 3.9+
- **PostgreSQL**: 17+ with pgvector 0.8.1
- **Redis**: 8.0+ (optional, for caching)

### Environment Setup

**1. Install Dependencies**:
```bash
# Core dependencies
pip install anthropic sqlalchemy psycopg2-binary pyyaml cryptography

# Vector search dependencies
pip install sentence-transformers numpy

# Optional LLM providers
pip install openai tiktoken google-generativeai cohere

# Database (PostgreSQL 17 required for pgvector 0.8.1)
brew install postgresql@17 pgvector
brew install redis

# Start services
brew services start postgresql@17
brew services start redis
```

**2. Database Setup**:
```bash
# Install PostgreSQL 17
brew install postgresql@17
brew services start postgresql@17

# Create database
/opt/homebrew/opt/postgresql@17/bin/createdb compliance_db

# Enable pgvector extension (as superuser)
/opt/homebrew/opt/postgresql@17/bin/psql compliance_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
/opt/homebrew/opt/postgresql@17/bin/psql compliance_db -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"

# Initialize schema
python3 scripts/init_database.py

# Verify vector setup
/opt/homebrew/opt/postgresql@17/bin/psql compliance_db -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```

**3. Configuration**:
```bash
# Copy config templates
cp config/llm_config.example.yaml config/llm_config.yaml
cp .env.example .env

# Set environment variables
export ANTHROPIC_API_KEY="sk-ant-..."
export NETSUITE_ACCOUNT_ID="..."
export NETSUITE_CONSUMER_KEY="..."
export DATABASE_URL="postgresql://user:pass@localhost/compliance_db"
```

**4. Verify Setup**:
```bash
# Test LLM connection
python3 -c "from services.llm import get_llm_from_config; llm = get_llm_from_config(); print(llm.test_connection())"

# Test database
python3 -c "from models.database_config import DatabaseConfig; db = DatabaseConfig(); print(db.test_connection())"

# Run smoke test
python3 demos/demo_end_to_end.py
```

### Production Deployment

**Docker Setup** (Recommended):
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY . .

# Run application
CMD ["python", "main.py"]
```

**Docker Compose**:
```yaml
version: '3.8'

services:
  app:
    build: .
    environment:
      - DATABASE_URL=postgresql://db:5432/compliance
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      - db
      - redis

  db:
    image: postgres:16
    environment:
      - POSTGRES_DB=compliance_db
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:8-alpine
    volumes:
      - redis_data:/data
```

**Kubernetes** (Enterprise):
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: compliance-system
spec:
  replicas: 3
  selector:
    matchLabels:
      app: compliance
  template:
    metadata:
      labels:
        app: compliance
    spec:
      containers:
      - name: app
        image: compliance-system:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: llm-credentials
              key: anthropic_key
```

### Monitoring & Logging

**Logging Configuration**:
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/compliance.log'),
        logging.StreamHandler()
    ]
)
```

**Metrics to Monitor**:
- API call latency (NetSuite, Okta, LLM)
- Database query performance
- Agent execution time
- Error rates
- Cost tracking
- User violation counts
- System resource usage

**Alerting**:
- Critical violations detected
- API failures
- Database connection issues
- High cost operations
- Failed deactivations

---

## Appendix

### A. Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Language** | Python | 3.9+ |
| **Database** | PostgreSQL + pgvector | 17.7 + 0.8.1 |
| **Cache** | Redis | 8.4.1 |
| **ORM** | SQLAlchemy | 2.0+ |
| **Agents** | LangChain + LangGraph | Latest |
| **Embeddings** | HuggingFace (sentence-transformers) | 384-dim MiniLM |
| **Vector Search** | pgvector cosine similarity | 0.8.1 |
| **Semantic Router** | sentence-transformers/all-MiniLM-L6-v2 | Local, 384-dim, no API key |
| **Eval Framework** | LangSmith | 0.4.x — experiment tracking + datasets |
| **LLM** | Claude, GPT, Gemini | Latest |
| **NetSuite** | SuiteScript 2.1 | Latest |
| **Okta** | REST API | v1 |
| **Encryption** | cryptography (Fernet) | Latest |

### B. File Structure

```
compliance-agent/
├── agents/                          # Agent implementations
│   ├── analyzer.py                  # SOD analysis (context-aware)
│   ├── data_collector.py            # NetSuite/Okta data fetching
│   ├── risk_assessor.py             # Risk scoring
│   ├── knowledge_base.py            # Semantic search
│   ├── notifier.py                  # Notifications (LLM abstraction)
│   ├── orchestrator.py              # LangGraph workflow
│   └── [NEW] reconciliation.py      # Okta-NS reconciliation (Phase 2)
│   └── [NEW] deactivation.py        # User deactivation (Phase 2)
│
├── services/                        # Service layer
│   ├── netsuite_client.py           # NetSuite OAuth client
│   ├── okta_client.py               # Okta API client (NEW)
│   └── llm/                         # LLM abstraction layer (NEW)
│       ├── __init__.py
│       ├── base.py                  # Abstract interface
│       ├── factory.py               # Provider factory
│       ├── config_manager.py        # Config + encryption
│       └── providers/               # Provider implementations
│           ├── anthropic_provider.py
│           ├── openai_provider.py
│           ├── google_provider.py
│           ├── cohere_provider.py
│           ├── azure_provider.py
│           └── local_provider.py
│
├── repositories/                    # Data access layer
│   ├── user_repository.py
│   ├── role_repository.py
│   ├── violation_repository.py
│   ├── sod_rule_repository.py
│   ├── okta_user_repository.py      # NEW
│   ├── user_reconciliation_repository.py  # NEW
│   ├── deactivation_approval_repository.py  # NEW
│   └── deactivation_log_repository.py  # NEW
│
├── models/                          # Database models
│   ├── database.py                  # SQLAlchemy models (17 tables)
│   └── database_config.py           # DB connection config
│
├── netsuite_scripts/                # SuiteScript files
│   ├── user_search_restlet_v5_hybrid.js  # Search RESTlet
│   ├── user_deactivation_restlet.js       # Deactivation RESTlet (NEW)
│   └── user_deactivation_mapreduce.js     # Map/Reduce script (NEW)
│
├── migrations/                      # Database migrations
│   ├── 001_initial_schema.sql
│   ├── 002_context_fields.sql
│   └── 003_okta_reconciliation.sql  # NEW
│
├── config/                          # Configuration files
│   ├── llm_config.yaml              # LLM provider config (NEW)
│   └── llm_config.example.yaml      # Config template (NEW)
│
├── utils/                           # Shared utilities
│   ├── tool_router.py               # Regex/keyword router (fallback)
│   └── semantic_router.py           # Semantic router — primary selector (NEW Mar 2026)
│
├── eval/                            # Offline evaluation suite (NEW Mar 2026)
│   ├── __init__.py
│   ├── golden_set.py                # 32-query tool-selection dataset + 10-query answer quality dataset
│   ├── evaluators.py                # hit_rate, MRR, NDCG, precision, faithfulness evaluators
│   └── run_eval.py                  # CLI runner — --router, --suite, --live flags
│
├── tests/                           # Test suites
│   ├── test_all_agents.py           # Agent tests (23 tests)
│   ├── test_context_aware_sod.py    # Context-aware logic tests
│   └── test_end_to_end_stress.py    # Stress test
│
├── demos/                           # Demo scripts
│   ├── demo_end_to_end.py           # Full system demo
│   └── demo_llm_abstraction.py      # LLM abstraction demo (NEW)
│
├── examples/                        # Example scripts
│   └── demo_llm_abstraction.py      # LLM usage examples (NEW)
│
├── docs/                            # Documentation
│   ├── TECHNICAL_SPECIFICATION_V3.md  # This document
│   ├── LLM_ABSTRACTION_GUIDE.md       # LLM abstraction guide (NEW)
│   ├── LLM_ABSTRACTION_SUMMARY.md     # Quick reference (NEW)
│   ├── OKTA_NETSUITE_RECONCILIATION_PLAN.md  # Okta integration (NEW)
│   └── PHASE_1_COMPLETION.md          # Phase 1 summary (NEW)
│
├── .env.example                     # Environment variables template
├── requirements.txt                 # Python dependencies
└── README.md                        # Project overview
```

### C. Version History

| Version | Date | Changes |
|---------|------|---------|
| **1.0.0** | 2026-01-15 | Initial system with 6 agents |
| **2.0.0** | 2026-02-05 | Context-aware SOD analysis |
| **2.1.0** | 2026-02-11 | User comparison tables + AI insights |
| **3.0.0** | 2026-02-09 | LLM abstraction + Okta integration (Phase 1) |
| **3.1.0** | 2026-02-12 | pgvector integration complete - vector search operational |
| **3.2.0** | 2026-02-12 | Redis caching layer - 90% cost reduction for LLM calls |
| **3.3.0** | 2026-02-12 | Agent response pattern + analyze_role_permissions tool |
| **3.4.0** | 2026-03-15 | Semantic tool router (utils/semantic_router.py) + eval suite (eval/) — hit_rate_at_10 1.00, MRR 0.91 |

### D. Future Enhancements

**Phase 2** (Okta Reconciliation - 2 weeks):
- ✅ Foundation complete (database, repositories, Okta client, NS scripts)
- ⏳ Implement Reconciliation Agent
- ⏳ Implement Deactivation Agent
- ⏳ Build approval workflow UI
- ⏳ Integration testing

**Phase 3** (Advanced Features - 4 weeks):
- [ ] Machine learning for anomaly detection
- [ ] Predictive risk scoring
- [ ] Advanced dashboards (web UI)
- [ ] Mobile notifications
- [ ] Integration with more systems (Workday, SAP, etc.)

**Phase 4** (Enterprise Features - 6 weeks):
- [ ] Multi-tenancy support
- [ ] Role-based access control (RBAC)
- [ ] Advanced reporting (BI integration)
- [ ] Compliance audit export (SOC 2, ISO 27001)
- [ ] API for external integrations

---

## Summary

This technical specification documents a comprehensive, production-ready SOD compliance system with:

✅ **Multi-Agent Architecture** - 8 specialized agents (6 operational, 2 in development)
✅ **LLM-Agnostic Design** - Switch between any LLM provider via configuration
✅ **Context-Aware Analysis** - 67% false positive reduction for IT staff
✅ **Vector Search** - Semantic rule matching with pgvector (384-dim embeddings)
✅ **Redis Caching** - 90% cost reduction, 10-500x faster repeated queries
✅ **Okta Integration** - User lifecycle reconciliation with approval workflow
✅ **High Performance** - 185 users/sec analysis throughput
✅ **Enterprise Security** - Encrypted API keys, OAuth, audit trails
✅ **Scalable Architecture** - Linear scaling to 100K+ users
✅ **Comprehensive Testing** - 100% agent test pass rate
✅ **Semantic Tool Router** - Dense vector tool selection, hit_rate_at_10 1.00, MRR 0.91 (utils/semantic_router.py)
✅ **Eval Suite** - LangSmith-integrated offline evaluation, 5 metrics, 2 datasets (eval/)

**Current Status**: v3.4.0 - Production Ready with Semantic Router + Eval Suite
**Next Milestone**: Phase 2 - Okta Reconciliation Agents (2 weeks)

---

**Document End**
