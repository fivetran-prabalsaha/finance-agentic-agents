# 🏗️ SOD Compliance System - Architecture Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Layers](#architecture-layers)
3. [Component Details](#component-details)
4. [Data Flow - User Query Processing](#data-flow---user-query-processing)
5. [Natural Language Understanding](#natural-language-understanding)
6. [Component Communication](#component-communication)
7. [Autonomous Collection Agent](#autonomous-collection-agent)
8. [Database Schema](#database-schema)
9. [Deployment Architecture](#deployment-architecture)

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE LAYER                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐     │
│  │ Claude Desktop   │  │  Claude Web API  │  │   Web Dashboard  │     │
│  │   (MCP stdio)    │  │  (Direct API)    │  │   (FastAPI UI)   │     │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘     │
└───────────┼────────────────────┼────────────────────┼─────────────────┘
            │                    │                    │
            └────────────────────┼────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         MCP (Model Context Protocol) LAYER              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  MCP Server (mcp_server.py) - JSON-RPC 2.0                      │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐    │   │
│  │  │ Tool: list  │  │ Tool: get   │  │ Tool: perform_access │    │   │
│  │  │ _systems    │  │ _violations │  │ _review              │    │   │
│  │  └─────────────┘  └─────────────┘  └──────────────────────┘    │   │
│  └──────────────────────────┬──────────────────────────────────────┘   │
└─────────────────────────────┼─────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATION LAYER                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  ComplianceOrchestrator (Singleton with @lru_cache)             │   │
│  │  • Coordinates all agents and connectors                        │   │
│  │  • Implements caching (@timed_cache)                            │   │
│  │  • Routes requests to appropriate components                    │   │
│  │  • Aggregates results from multiple sources                     │   │
│  └──────────────┬────────────────────┬─────────────────┬────────────┘   │
└─────────────────┼────────────────────┼─────────────────┼────────────────┘
                  │                    │                 │
        ┌─────────┴──────┐   ┌────────┴─────────┐  ┌───┴──────────┐
        ▼                ▼   ▼                  ▼  ▼              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           AGENT LAYER                                   │
│  ┌──────────────────┐  ┌─────────────────┐  ┌──────────────────────┐  │
│  │ SODAnalysisAgent │  │ NotificationAgent│ │ KnowledgeBaseAgent   │  │
│  │ • Detect SOD     │  │ • AI Analysis    │ │ • Semantic Search    │  │
│  │   violations     │  │ • Risk scoring   │ │ • Rule matching      │  │
│  │ • Rule matching  │  │ • Generate recs  │ │ • Vector embeddings  │  │
│  └────────┬─────────┘  └────────┬────────┘  └──────────┬───────────┘  │
└───────────┼────────────────────┼───────────────────────┼──────────────┘
            │                    │                       │
            └────────────────────┼───────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        CONNECTOR LAYER                                  │
│  ┌─────────────────────────┐      ┌─────────────────────────┐          │
│  │  NetSuiteConnector      │      │  OktaConnector (future) │          │
│  │  • fetch_users()        │      │  • fetch_users()        │          │
│  │  • sync_to_database()   │      │  • sync_to_database()   │          │
│  │  • search_user()        │      │  • search_user()        │          │
│  └───────────┬─────────────┘      └───────────┬─────────────┘          │
└───────────────┼────────────────────────────────┼────────────────────────┘
                │                                │
                ▼                                ▼
    ┌───────────────────┐          ┌──────────────────────┐
    │ NetSuite RESTlet  │          │  Okta API            │
    │ (External System) │          │  (External System)   │
    └───────────────────┘          └──────────────────────┘
                │                                │
                └────────────┬───────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        REPOSITORY LAYER                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │
│  │ UserRepository  │  │ RoleRepository  │  │ViolationRepo    │        │
│  │ • CRUD users    │  │ • CRUD roles    │  │• CRUD violations│        │
│  │ • Assign roles  │  │ • Upsert roles  │  │• Query by user  │        │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘        │
└───────────┼───────────────────┼───────────────────┼────────────────────┘
            │                   │                   │
            └───────────────────┼───────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                DATABASE LAYER (PostgreSQL + pgvector)                   │
│                                                                         │
│  Core Identity & Access:                                               │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐                                 │
│  │  users  │ │  roles  │ │user_roles│                                 │
│  └─────────┘ └─────────┘ └──────────┘                                 │
│                                                                         │
│  SOD Compliance:                                                        │
│  ┌─────────┐ ┌──────────┐ ┌─────────────────┐ ┌──────────────────┐   │
│  │sod_rules│ │violations│ │violation_exempts│ │compliance_scans  │   │
│  └─────────┘ └──────────┘ └─────────────────┘ └──────────────────┘   │
│                                                                         │
│  Role Analysis & Intelligence:                                         │
│  ┌──────────────────────┐ ┌─────────────────┐ ┌────────────────────┐ │
│  │role_internal_conflicts│ │job_role_mappings│ │access_request_     │ │
│  │     (NEW - 2026)      │ │                 │ │  analyses          │ │
│  └──────────────────────┘ └─────────────────┘ └────────────────────┘ │
│                                                                         │
│  Knowledge Base (Vector Search):                                       │
│  ┌─────────────────────────┐ ┌──────────────────┐                     │
│  │knowledge_base_documents │ │compensating_     │                     │
│  │   (NEW - 2026)          │ │  controls        │                     │
│  └─────────────────────────┘ └──────────────────┘                     │
│                                                                         │
│  System & Audit:                                                       │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────┐                │
│  │ agent_logs   │  │ notifications │  │ audit_trail │                │
│  └──────────────┘  └───────────────┘  └─────────────┘                │
│                                                                         │
│  Total: 23 tables | 5 with vector embeddings | See docs/DATABASE_UML.md │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture Layers

### 1. **User Interface Layer**
- **Claude Desktop**: Uses MCP stdio protocol to communicate with the MCP server
- **Claude Web API**: Direct API integration with Anthropic Claude
- **Web Dashboard**: Custom FastAPI web interface for direct access

### 2. **MCP Layer (Model Context Protocol)**
- **Purpose**: Expose compliance tools to Claude AI
- **Protocol**: JSON-RPC 2.0 over HTTP/stdio
- **Tools Exposed**:
  - `list_systems` - List available systems for review
  - `get_user_violations` - Get violations for a specific user
  - `get_violation_stats` - Get aggregated violation statistics
  - `perform_access_review` - Full system-wide SOD analysis
  - `remediate_violation` - Generate remediation plans

### 3. **Orchestration Layer**
- **ComplianceOrchestrator** (Singleton)
  - Central coordination point for all operations
  - Implements caching for performance
  - Routes requests to appropriate agents/connectors
  - Aggregates and formats results

### 4. **Agent Layer**
- **SODAnalysisAgent**: Detects segregation of duties violations
- **NotificationAgent**: Generates AI-powered risk analysis
- **KnowledgeBaseAgent**: Semantic search over SOD rules

### 5. **Connector Layer**
- **NetSuiteConnector**: Interfaces with NetSuite RESTlet API
- **OktaConnector** (future): Interfaces with Okta API
- Handles data fetching, transformation, and syncing

### 6. **Repository Layer**
- **Purpose**: Database abstraction using Repository pattern
- **Components**: UserRepository, RoleRepository, ViolationRepository, etc.
- **Benefits**: Decouples business logic from database implementation

### 7. **Database Layer**
- **PostgreSQL** with pgvector extension
- Stores users, roles, violations, SOD rules, compliance scans

---

## Component Details

### MCP Server (`mcp/mcp_server.py`)

```python
"""
MCP Server - JSON-RPC 2.0 endpoint for Claude integration

Responsibilities:
1. Receive tool call requests from Claude
2. Validate and parse JSON-RPC requests
3. Route to appropriate tool handlers
4. Return formatted responses
5. Handle errors gracefully
"""

Key Methods:
- handle_tools_list() - Returns available tools
- handle_tools_call() - Executes tool with parameters
- handle_notifications() - Handles notification messages

Example Tool Call:
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "get_user_violations",
    "arguments": {
      "system_name": "netsuite",
      "user_identifier": "chase.roles@fivetran.com"
    }
  },
  "id": 1
}
```

### MCP Tools (`mcp/mcp_tools.py`)

```python
"""
MCP Tool Handlers - Business logic for each tool

Each handler:
1. Receives parsed arguments
2. Calls orchestrator methods
3. Formats results for Claude
4. Returns human-readable text
"""

Tool: get_user_violations
├─ Input: system_name, user_identifier, include_ai_analysis
├─ Process:
│  ├─ orchestrator.get_user_violations_sync()
│  │  ├─ user_repo.get_user_by_email() [Check DB first]
│  │  ├─ If not found: Auto-sync from NetSuite
│  │  ├─ violation_repo.get_violations_by_user()
│  │  └─ notifier_agent.generate_ai_analysis() [Optional]
│  └─ Format as markdown report
└─ Output: Formatted violation report
```

### ComplianceOrchestrator (`mcp/orchestrator.py`)

```python
"""
Central Orchestrator - Coordinates all system components

Singleton Pattern:
- Single instance shared across all requests
- Initialized once at startup
- Cached with @lru_cache for performance

Caching Strategy:
- @timed_cache(seconds=60) for user lookups
- @timed_cache(seconds=300) for access reviews
- Cache key includes all parameters for proper isolation
"""

Key Methods:
1. list_available_systems_sync()
   └─ Returns configured connectors and their status

2. get_user_violations_sync(system_name, user_identifier)
   ├─ Check database for user
   ├─ If not found: Auto-sync from source system
   ├─ Fetch violations from database
   ├─ Generate AI analysis (optional)
   └─ Return formatted results

3. perform_access_review_sync(system_name, analysis_type)
   ├─ Fetch ALL users from source system (NetSuite)
   ├─ Sync users, roles, permissions to database
   ├─ Run SOD analysis on all users
   ├─ Calculate statistics
   ├─ Identify top violators
   └─ Return comprehensive report

4. get_violation_stats_sync(systems, time_range)
   ├─ Query violations by time range
   ├─ Aggregate by severity, system, user
   ├─ Calculate trends
   └─ Return statistics
```

### SODAnalysisAgent (`agents/analyzer.py`)

```python
"""
SOD Analysis Agent - Core violation detection engine

Responsibilities:
1. Load SOD rules from JSON and database
2. Analyze user role combinations
3. Detect conflicting permissions
4. Calculate risk scores
5. Generate violation records
"""

Key Methods:
1. analyze_all_users(scan_id)
   ├─ Get all users with roles from database
   ├─ For each user:
   │  ├─ Get user's roles and permissions
   │  ├─ Check against all SOD rules
   │  ├─ Calculate risk scores
   │  └─ Create violation records
   └─ Return aggregated results

2. _analyze_user(user, scan_id)
   ├─ Extract user's roles and permissions
   ├─ For each SOD rule:
   │  ├─ Check if rule applies to user
   │  ├─ Check for conflicting permissions
   │  ├─ Apply business justifications
   │  └─ Create violation if conflict found
   └─ Return user's violations

3. _check_rule_violation(user, rule)
   ├─ Parse rule conditions (role conflicts, permission conflicts)
   ├─ Check if user has conflicting items
   ├─ Calculate risk score based on:
   │  ├─ Rule severity
   │  ├─ User's department/job function
   │  ├─ Permission sensitivity
   │  └─ Business context
   └─ Return violation details or None

Rule Matching Logic:
- Role-based: Check if user has multiple conflicting roles
- Permission-based: Check if user has conflicting permissions
- Context-aware: Apply business justifications (IT users, etc.)
```

### NetSuiteConnector (`connectors/netsuite_connector.py`)

```python
"""
NetSuite Connector - Interface to NetSuite RESTlet API

Responsibilities:
1. Authenticate via OAuth 1.0a
2. Fetch users, roles, permissions from NetSuite
3. Transform NetSuite data to internal format
4. Sync data to database
"""

Key Methods:
1. fetch_users_with_roles_sync(include_permissions, include_inactive)
   ├─ Call NetSuite RESTlet: get_all_users_paginated()
   ├─ Handle pagination (1000 users per page)
   ├─ Transform NetSuite format to internal format
   └─ Return list of user dictionaries

2. sync_to_database_sync(users_data, user_repo, role_repo)
   ├─ For each user:
   │  ├─ Upsert user record
   │  ├─ For each role:
   │  │  ├─ Upsert role record
   │  │  └─ Assign role to user
   └─ Return synced User objects

3. search_user_sync(search_value, search_type, include_permissions)
   ├─ Call NetSuite RESTlet with search criteria
   ├─ Transform single user result
   └─ Return user dictionary with roles/permissions

Data Transformation:
NetSuite Format → Internal Format
{                   {
  id: "123",         user_id: "123",
  name: "John",      name: "John",
  email: "...",      email: "...",
  isActive: true, →  status: "ACTIVE",
  roles: [...]       roles: [...]
}                   }
```

### UserRepository (`repositories/user_repository.py`)

```python
"""
User Repository - Database operations for users

Implements Repository Pattern:
- Abstracts database operations
- Provides clean interface for business logic
- Handles SQLAlchemy ORM details
"""

Key Methods:
1. create_user(user_data: Dict) → User
   ├─ Create User ORM object
   ├─ Insert into database
   ├─ Commit transaction
   └─ Return User object

2. upsert_user(user_data: Dict) → User
   ├─ Check if user exists (by email or user_id)
   ├─ If exists: Update fields
   ├─ If not exists: Create new user
   ├─ Commit transaction
   └─ Return User object

3. get_user_by_email(email: str) → Optional[User]
   ├─ Query database (case-insensitive via .ilike())
   └─ Return User object or None

4. assign_role_to_user(user_id: UUID, role_id: UUID) → UserRole
   ├─ Check if assignment already exists
   ├─ If not: Create UserRole record
   ├─ Commit transaction
   └─ Return UserRole object

5. get_users_with_roles() → List[User]
   ├─ Query users with eager-loaded roles
   ├─ Use joinedload for performance
   └─ Return list of User objects with roles populated
```

---

## Data Flow - User Query Processing

### Example 1: "Is Chase Roles compliant?"

```
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 1: User Input                                                   │
│ User types: "Is Chase Roles compliant?"                             │
│ Interface: Claude Desktop / Web / Dashboard                          │
└────────────────────────────┬─────────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 2: Claude AI Processing (by Anthropic)                         │
│ Claude analyzes the question and determines:                        │
│ • Intent: Check user compliance status                              │
│ • Tool needed: get_user_violations                                  │
│ • Parameters:                                                        │
│   - system_name: "netsuite" (inferred)                             │
│   - user_identifier: "chase.roles" or "chase.roles@fivetran.com"  │
│   - include_ai_analysis: true (for comprehensive answer)           │
└────────────────────────────┬─────────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 3: MCP Tool Call                                               │
│ JSON-RPC Request:                                                    │
│ {                                                                    │
│   "jsonrpc": "2.0",                                                 │
│   "method": "tools/call",                                           │
│   "params": {                                                        │
│     "name": "get_user_violations",                                  │
│     "arguments": {                                                   │
│       "system_name": "netsuite",                                    │
│       "user_identifier": "chase.roles@fivetran.com",               │
│       "include_ai_analysis": true                                   │
│     }                                                                │
│   },                                                                 │
│   "id": 1                                                            │
│ }                                                                    │
└────────────────────────────┬─────────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 4: MCP Server Routing                                          │
│ mcp_server.py receives request                                      │
│ • Validates JSON-RPC format                                         │
│ • Extracts tool name: "get_user_violations"                        │
│ • Routes to: get_user_violations_handler()                         │
└────────────────────────────┬─────────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 5: Tool Handler (mcp_tools.py)                                │
│ get_user_violations_handler():                                      │
│ • Parse arguments                                                    │
│ • Get orchestrator instance: get_orchestrator()                    │
│ • Call: orchestrator.get_user_violations_sync(...)                 │
└────────────────────────────┬─────────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 6: Orchestrator Processing                                     │
│ orchestrator.get_user_violations_sync():                            │
│                                                                      │
│ A. Check Cache (60s TTL)                                            │
│    • Cache key: "orchestrator_id_get_user_violations_sync_          │
│                  netsuite_chase.roles@fivetran.com_True"           │
│    • If hit: Return cached result (instant)                        │
│    • If miss: Continue to step B                                   │
│                                                                      │
│ B. Look up User in Database                                         │
│    user_repo.get_user_by_email("chase.roles@fivetran.com")        │
│    • Query: SELECT * FROM users WHERE email ILIKE 'chase.roles...' │
│    • Result: User object or None                                   │
│                                                                      │
│ C. If User Not Found: Auto-Sync from NetSuite                      │
│    connector = self.connectors['netsuite']                         │
│    users_data = connector.fetch_users_with_roles_sync()           │
│    • Find user in results                                          │
│    • Create user in database via user_repo.create_user()          │
│    • Sync roles via role_repo.upsert_role()                       │
│    • Assign roles via user_repo.assign_role_to_user()             │
│                                                                      │
│ D. Fetch Violations                                                │
│    violations = violation_repo.get_violations_by_user(user.id)    │
│    • Query: SELECT * FROM violations WHERE user_id = ?            │
│    • Join with sod_rules table                                    │
│    • Return list of Violation objects                             │
│                                                                      │
│ E. Get User Roles                                                   │
│    roles = [ur.role.role_name for ur in user.user_roles]          │
│                                                                      │
│ F. Generate AI Analysis (if requested)                             │
│    ai_analysis = notifier_agent._generate_ai_analysis(...)        │
│    • Calls Anthropic Claude API                                    │
│    • Provides context: user, violations, roles                    │
│    • Returns natural language risk assessment                     │
│                                                                      │
│ G. Format Result                                                    │
│    return {                                                         │
│      "user_name": "Chase Roles",                                   │
│      "email": "chase.roles@fivetran.com",                         │
│      "roles": ["Administrator", "Fivetran - Controller"],         │
│      "violation_count": 12,                                        │
│      "violations": [...],                                          │
│      "ai_analysis": "...",                                         │
│      "is_active": true                                             │
│    }                                                                │
└────────────────────────────┬─────────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 7: Format Response for Claude                                  │
│ get_user_violations_handler() formats result:                      │
│                                                                      │
│ **Chase Roles - Violation Report**                                 │
│                                                                      │
│ 📧 Email: chase.roles@fivetran.com                                 │
│ 🏢 System: netsuite                                                │
│ 🎭 Roles (2): Administrator, Fivetran - Controller                │
│ ⚠️  Total Violations: 12                                           │
│                                                                      │
│ **Violations:**                                                     │
│ 1. 🟢 CRITICAL: AP Entry vs. Approval Separation                  │
│    • Risk Score: 94.0/100                                          │
│    • Description: ...                                              │
│ ...                                                                 │
└────────────────────────────┬─────────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 8: Return to Claude                                            │
│ MCP Server returns JSON-RPC response:                               │
│ {                                                                    │
│   "jsonrpc": "2.0",                                                 │
│   "id": 1,                                                           │
│   "result": {                                                        │
│     "content": [{                                                    │
│       "type": "text",                                               │
│       "text": "**Chase Roles - Violation Report**\n\n..."          │
│     }]                                                               │
│   }                                                                  │
│ }                                                                    │
└────────────────────────────┬─────────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 9: Claude AI Response Generation                               │
│ Claude receives tool result and generates natural response:        │
│                                                                      │
│ "Chase Roles is NOT compliant. He has 12 SOD violations,          │
│  including 3 CRITICAL issues. The most serious is that he can     │
│  both create and approve vendor bills, which violates financial   │
│  controls. As Director of Corporate Accounting with both          │
│  Administrator and Controller roles, this is a high-risk          │
│  combination..."                                                    │
└────────────────────────────┬─────────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 10: Display to User                                            │
│ Claude's response is displayed in:                                 │
│ • Claude Desktop chat interface                                    │
│ • Web dashboard                                                     │
│ • API response                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Example 2: "Show me violation stats"

```
User Query: "Show me violation stats"
      ↓
Claude AI determines:
  - Tool: get_violation_stats
  - Parameters: {time_range: "month"}
      ↓
MCP Tool Call → orchestrator.get_violation_stats_sync()
      ↓
Orchestrator:
  1. Check cache (120s TTL)
  2. Query violations from database
  3. Filter by time range (last month)
  4. Aggregate by severity, system, status
  5. Calculate trends
  6. Return statistics
      ↓
Format as markdown table:
  | Severity | Count | % of Total |
  |----------|-------|------------|
  | CRITICAL | 3     | 10.7%      |
  | HIGH     | 10    | 35.7%      |
  | MEDIUM   | 15    | 53.6%      |
      ↓
Return to Claude → Natural language response
```

### Example 3: "Perform access review of NetSuite"

```
User Query: "Perform access review of NetSuite"
      ↓
Claude AI determines:
  - Tool: perform_access_review
  - Parameters: {
      system_name: "netsuite",
      analysis_type: "sod_violations",
      include_recommendations: false
    }
      ↓
MCP Tool Call → orchestrator.perform_access_review_sync()
      ↓
Orchestrator:
  1. Test NetSuite connection
  2. Fetch ALL users from NetSuite (paginated)
     - 1933 users across multiple pages
     - Include roles and permissions
  3. Sync to database
     - Upsert 1933 users
     - Upsert roles
     - Assign roles to users
  4. Run SOD analysis on all users
     - analyzer.analyze_all_users()
     - Creates violation records
  5. Calculate statistics
     - Total violations
     - Breakdown by severity
     - Top violators
  6. Generate recommendations (optional)
  7. Return comprehensive report
      ↓
Format results (4-5 minutes processing):
  **Access Review - NETSUITE**
  Users Analyzed: 1933
  Total Violations: 28
  High-Risk: 10
  Medium-Risk: 12
  Low-Risk: 6

  Top Violators:
  1. Robin Turner - 12 violations
  2. Chase Roles - 12 violations
  3. Jessica Wu - 4 violations
      ↓
Return to Claude → Natural language summary
```

---

## Natural Language Understanding

### How the System Parses User Questions

The system uses **Claude AI's natural language understanding** combined with **structured MCP tools**. Here's how different questions are parsed:

#### Question Type: User Compliance Check

**User asks:**
- "Is Chase Roles compliant?"
- "Check if chase.roles@fivetran.com has violations"
- "What's the compliance status of Chase?"
- "Does Chase Roles have any SOD issues?"

**Claude's Intent Recognition:**
```
Intent: Check user compliance
Entity: User (Chase Roles / chase.roles@fivetran.com)
Action: Query violations
System: netsuite (inferred from context)

→ Tool: get_user_violations
→ Parameters:
  - system_name: "netsuite"
  - user_identifier: "chase.roles@fivetran.com"
  - include_ai_analysis: true
```

#### Question Type: Statistics Query

**User asks:**
- "Show me violation stats"
- "How many violations do we have?"
- "What's the compliance breakdown?"
- "Give me monthly statistics"

**Claude's Intent Recognition:**
```
Intent: Get aggregate statistics
Time Range: month (default or extracted from query)
Action: Query and aggregate violations

→ Tool: get_violation_stats
→ Parameters:
  - time_range: "month"
  - systems: ["netsuite"] (optional)
```

#### Question Type: Full System Review

**User asks:**
- "Perform access review"
- "Analyze all NetSuite users"
- "Run compliance check on the system"
- "Show me all violations in NetSuite"

**Claude's Intent Recognition:**
```
Intent: Comprehensive system analysis
Scope: All users
System: netsuite
Action: Full SOD analysis

→ Tool: perform_access_review
→ Parameters:
  - system_name: "netsuite"
  - analysis_type: "sod_violations"
  - include_recommendations: false
```

#### Question Type: User Search

**User asks:**
- "Find chase.roles@fivetran.com in NetSuite"
- "Does Chase Roles exist in the system?"
- "Look up chase.roles"

**Claude's Intent Recognition:**
```
Intent: Search for user
Entity: User identifier
Action: Search and return basic info

→ Tool: get_user_violations (checks existence)
→ Parameters:
  - system_name: "netsuite"
  - user_identifier: "chase.roles@fivetran.com"
  - include_ai_analysis: false
```

#### Question Type: Comparative Analysis

**User asks:**
- "Compare Jessica Wu and Chase Roles"
- "Who has more violations, Robin or Chase?"
- "Show me the top 3 violators"

**Claude's Intent Recognition:**
```
Intent: Comparative analysis
Action: Multiple queries + comparison

→ Tool calls (multiple):
  1. get_user_violations for Jessica Wu
  2. get_user_violations for Chase Roles
  3. Compare results
  4. Generate comparative summary
```

### Context-Aware Understanding

The system maintains **conversation context** through Claude's memory:

```
User: "What systems can you review?"
  → Tool: list_systems
  → Response: NetSuite, Okta (planned)

User: "Review NetSuite"
  → Claude remembers: systems = [NetSuite]
  → Tool: perform_access_review
  → Parameters: system_name = "netsuite"

User: "Show me the top violator"
  → Claude remembers: Just did access review
  → Knows: Top violator is Robin Turner
  → Tool: get_user_violations
  → Parameters: user_identifier = "robin.turner@fivetran.com"
```

### Ambiguity Resolution

**Ambiguous query:** "Check Chase"

Claude's resolution process:
1. Extract entity: "Chase" (incomplete)
2. Check context: Previous messages mention "chase.roles@fivetran.com"
3. Make assumption: User means Chase Roles
4. Add domain: @fivetran.com (from context)
5. Call tool with: "chase.roles@fivetran.com"

If no context available:
- Claude asks clarifying question
- "Do you mean chase.roles@fivetran.com?"

---

## Component Communication

### Synchronous Flow (Request-Response)

```
User Query
    ↓
  Claude AI
    ↓
MCP Server (HTTP/stdio)
    ↓
MCP Tools Handler
    ↓
ComplianceOrchestrator
    ↓
┌─────────┬─────────┬─────────┐
│         │         │         │
Agents  Connectors Repos
│         │         │         │
└─────────┴─────────┴─────────┘
    ↓
Database / External APIs
    ↓
Results bubble back up
    ↓
Formatted response to Claude
    ↓
Natural language answer to user
```

### Caching Strategy

```
Layer 1: Orchestrator Method Cache (@timed_cache)
├─ list_systems: 60s TTL
├─ get_user_violations: 60s TTL
├─ perform_access_review: 300s TTL (5 min)
└─ get_violation_stats: 120s TTL (2 min)

Layer 2: Database Query Cache (PostgreSQL)
└─ Native PostgreSQL query caching

Layer 3: Connector Data Cache
├─ NetSuite API responses cached per session
└─ Pagination results cached temporarily

Cache Invalidation:
- Time-based expiration (TTL)
- Manual invalidation on data updates
- Cache key includes all parameters for isolation
```

### Error Handling Flow

```
Error occurs at any layer
    ↓
Exception raised
    ↓
Caught by orchestrator
    ↓
Logged with context
    ↓
Formatted error message
    ↓
Returned to Claude
    ↓
Claude generates user-friendly explanation
    ↓
User sees: "I encountered an error while checking..."
```

---

## Autonomous Collection Agent

### Architecture Addition

```
┌─────────────────────────────────────────────────────────────┐
│          Autonomous Data Collection Agent                   │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Scheduler (APScheduler / Celery)                  │    │
│  │  ┌──────────────┐  ┌──────────────┐               │    │
│  │  │ Full Sync    │  │ Incremental  │               │    │
│  │  │ Daily 2 AM   │  │ Hourly       │               │    │
│  │  └──────┬───────┘  └──────┬───────┘               │    │
│  └─────────┼──────────────────┼────────────────────────┘    │
│            └──────────┬───────┘                             │
│                       ▼                                     │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Sync Orchestrator                                 │    │
│  │  1. Fetch from NetSuite (paginated)                │    │
│  │  2. Transform data                                 │    │
│  │  3. Upsert to PostgreSQL                          │    │
│  │  4. Run SOD analysis                              │    │
│  │  5. Record sync metadata                          │    │
│  └─────────────────────┬──────────────────────────────┘    │
└────────────────────────┼─────────────────────────────────┘
                         ▼
            [PostgreSQL Database]
            Always up-to-date
                         ▼
            User Queries → Instant (DB only)
```

### Collection Agent Flow

```
Trigger: Scheduled time or manual
    ↓
1. Check Last Sync Status
   └─ Query sync_metadata table
    ↓
2. Determine Sync Type
   ├─ Full sync if: first run, daily schedule, or >24h since last
   └─ Incremental if: hourly schedule and <24h since last
    ↓
3. Fetch Data from NetSuite
   ├─ Full: Get all users (status='ALL')
   └─ Incremental: Get users modified since last_sync_time
    ↓
4. Sync to Database
   ├─ Upsert users (user_repo.upsert_user)
   ├─ Upsert roles (role_repo.upsert_role)
   └─ Assign roles (user_repo.assign_role_to_user)
    ↓
5. Run SOD Analysis
   └─ analyzer.analyze_all_users()
    ↓
6. Record Sync Metadata
   ├─ Sync time
   ├─ Records synced
   ├─ Duration
   ├─ Status (success/failed)
   └─ Error details (if any)
    ↓
7. Send Alerts (if configured)
   ├─ Success: Slack notification with stats
   └─ Failure: PagerDuty alert
```

### Sync Metadata Schema

```sql
CREATE TABLE sync_metadata (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sync_type VARCHAR(50) NOT NULL, -- 'full', 'incremental'
    status VARCHAR(50) NOT NULL,     -- 'running', 'success', 'failed'
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    users_synced INTEGER,
    roles_synced INTEGER,
    violations_detected INTEGER,
    duration_seconds FLOAT,
    error_message TEXT,
    metadata JSONB,                  -- Additional context
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for querying last sync
CREATE INDEX idx_sync_metadata_completed
ON sync_metadata(completed_at DESC, status);
```

---

## Database Schema

> 📊 **Full Database UML Diagram**: See [docs/DATABASE_UML.md](docs/DATABASE_UML.md) for comprehensive entity relationship diagram with all tables and relationships.

### Database Overview

The compliance system uses **PostgreSQL 14+** with **pgvector** extension for semantic search capabilities. The schema includes 23 tables organized into functional categories:

#### Core Identity & Access (3 tables)
- **users** - Employee accounts from NetSuite/Okta with contextual attributes
- **roles** - NetSuite roles with permissions and embeddings
- **user_roles** - Many-to-many role assignments

#### SOD Compliance & Violations (4 tables)
- **sod_rules** - Segregation of duties conflict rules with risk scoring
- **violations** - Detected SOD violations with status tracking
- **violation_exemptions** - Approved exceptions with compensating controls
- **compliance_scans** - Historical compliance scan metadata

#### Role Analysis & Intelligence (3 tables)
- **role_internal_conflicts** - Internal SOD conflicts within single roles (NEW)
- **access_request_analyses** - Pre-hire access request analysis results
- **job_role_mappings** - Job title to NetSuite role mappings with business context

#### Knowledge Base & AI (1 table)
- **knowledge_base_documents** - Vector-searchable compliance knowledge base (NEW)
  - SOD rule explanations
  - Role conflict patterns
  - Resolution strategies
  - Historical violation patterns

#### Controls & Audit (2 tables)
- **compensating_controls** - Catalog of available compensating controls
- **audit_trail** - Complete audit log of system actions

#### System & Metadata (10 tables)
- **agent_logs** - Autonomous agent activity logs
- **notifications** - User notification queue
- **sync_metadata** - Data synchronization tracking
- **permission_categories** - Permission taxonomy
- **permission_levels** - Permission level definitions
- **okta_users** - Okta user data cache
- **user_reconciliations** - User identity reconciliation
- **deactivation_logs** - User deactivation history
- **deactivation_approvals** - Approval workflow for deactivations
- **control_packages** - Pre-packaged control templates

### Key Database Features

#### 1. Vector Embeddings (pgvector)
Five tables use semantic embeddings for intelligent search:
```
roles.embedding           → Role similarity matching
sod_rules.embedding      → Rule semantic search
violations.embedding     → Violation pattern detection
exemptions.embedding     → Exemption similarity
kb_documents.embedding   → Knowledge base RAG queries
```

#### 2. JSONB for Flexibility
Extensive use of JSONB for semi-structured data:
- `roles.permissions` - Dynamic permission arrays
- `sod_rules.level_conflict_matrix` - Permission level conflicts
- `job_role_mappings.acceptable_role_combinations` - Business logic
- `knowledge_base_documents.metadata` - Document attributes

#### 3. Custom PostgreSQL Types
```sql
CREATE TYPE violationseverity AS ENUM ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW');
CREATE TYPE violationstatus AS ENUM ('OPEN', 'IN_REVIEW', 'RESOLVED', 'EXEMPTED');
CREATE TYPE userstatus AS ENUM ('ACTIVE', 'INACTIVE', 'DISABLED');
CREATE TYPE scanstatus AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED');
CREATE TYPE exemptionstatus AS ENUM ('PENDING', 'APPROVED', 'REJECTED', 'EXPIRED');
```

### Entity Relationships (Simplified)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CORE IDENTITY & ACCESS                           │
│                                                                     │
│  users (1) ────< user_roles (M) >──── (1) roles                   │
│    │                                      │                         │
│    │                                      │                         │
│    │                                      └──< role_internal_       │
│    │                                           conflicts (M)        │
└────┼─────────────────────────────────────────────────────────────┘
     │
     │  ┌─────────────────────────────────────────────────────────┐
     │  │              SOD COMPLIANCE                             │
     │  │                                                         │
     ├──┤  users (1) ────< violations (M) >──── (1) sod_rules   │
     │  │                     │                                   │
     │  │                     │                                   │
     │  │                     └──< (0..1) violation_exemptions   │
     │  │                                                         │
     │  │  compliance_scans (1) ────< violations (M)             │
     │  └─────────────────────────────────────────────────────────┘
     │
     │  ┌─────────────────────────────────────────────────────────┐
     │  │           KNOWLEDGE BASE & INTELLIGENCE                 │
     │  │                                                         │
     └──┤  users → access_request_analyses                       │
        │                                                         │
        │  roles → role_internal_conflicts                       │
        │       → knowledge_base_documents (semantic search)     │
        │                                                         │
        │  job_role_mappings → access_request_analyses           │
        └─────────────────────────────────────────────────────────┘
```

### Recent Schema Enhancements (2026-02)

#### Role Internal Conflicts Table
Stores detected internal SOD conflicts within single roles:
```sql
CREATE TABLE role_internal_conflicts (
    id SERIAL PRIMARY KEY,
    role_id VARCHAR(100) REFERENCES roles(role_id),
    conflict_category VARCHAR(100),  -- maker_checker, three_way_match, etc.
    conflict_name VARCHAR(255),
    severity VARCHAR(50),            -- CRITICAL, HIGH
    pattern_description TEXT,
    permissions_involved JSONB,
    analysis_timestamp TIMESTAMP
);
```

**Purpose**: Identify roles that violate SOD principles internally (e.g., can both create and approve transactions)

**Data**: 27 conflicts across 16 roles (48% of total roles)

#### Knowledge Base Documents Table
Vector-searchable knowledge base for RAG queries:
```sql
CREATE TABLE knowledge_base_documents (
    id UUID PRIMARY KEY,
    doc_id VARCHAR(100) UNIQUE,
    doc_type VARCHAR(50),           -- role_conflict_analysis, conflict_pattern, etc.
    title VARCHAR(500),
    content TEXT,
    embedding VECTOR(384),          -- Semantic search
    metadata JSONB,
    category VARCHAR(100),
    created_at TIMESTAMP
);

CREATE INDEX ON knowledge_base_documents
USING ivfflat (embedding vector_cosine_ops);
```

**Purpose**: Enable Claude Desktop to query compliance knowledge using natural language

**Data**: 24 documents (16 role analyses + 7 patterns + 1 summary)

---

## Deployment Architecture

### Local Development

```
┌──────────────────────────────────────────────────────────┐
│ Developer Machine                                        │
│                                                          │
│  ┌─────────────────┐      ┌─────────────────┐          │
│  │ Claude Desktop  │      │  PostgreSQL     │          │
│  │ (MCP stdio)     │      │  localhost:5432 │          │
│  └────────┬────────┘      └────────┬────────┘          │
│           │                        │                    │
│           │  ┌─────────────────────┼──────────────┐    │
│           └─→│ MCP Server          │              │    │
│              │ localhost:8080      │              │    │
│              │ • Python FastAPI    │              │    │
│              │ • Orchestrator      │              │    │
│              │ • Agents            │              │    │
│              │ • Connectors        │              │    │
│              └─────────────────────┴──────────────┘    │
│                                                          │
└──────────────────────────────────────────────────────────┘
                      │
                      ▼
              [NetSuite API]
              (External)
```

### Production Deployment

```
┌──────────────────────────────────────────────────────────────┐
│                         Load Balancer                        │
└───────────────────────────┬──────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ MCP Server 1 │    │ MCP Server 2 │    │ MCP Server 3 │
│ (Container)  │    │ (Container)  │    │ (Container)  │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────┐
│                          ▼                               │
│              ┌─────────────────────┐                    │
│              │ PostgreSQL Primary  │                    │
│              │ (Master)            │                    │
│              └──────────┬──────────┘                    │
│                         │                               │
│              ┌──────────┴──────────┐                    │
│              ▼                     ▼                    │
│    ┌─────────────────┐   ┌─────────────────┐          │
│    │ PostgreSQL      │   │ PostgreSQL      │          │
│    │ Read Replica 1  │   │ Read Replica 2  │          │
│    └─────────────────┘   └─────────────────┘          │
└──────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌──────────────┐    ┌──────────────┐  ┌──────────────┐
│ Collection   │    │ NetSuite API │  │ Anthropic    │
│ Agent        │    │ (External)   │  │ API          │
│ (Cron/K8s)   │    │              │  │ (External)   │
└──────────────┘    └──────────────┘  └──────────────┘
```

---

## Performance Characteristics

### Query Performance

```
Operation                  | Without Cache | With Cache | Database Only
---------------------------|---------------|------------|---------------
list_systems              | 5.56s         | 0.007s     | N/A
get_user_violations       | 2-5s          | 0.05s      | 0.01s
get_violation_stats       | 0.5-1s        | 0.03s      | 0.02s
perform_access_review     | 4-5 min       | N/A        | N/A
(1933 users)              |               |            |

With Autonomous Collection:
get_user_violations       | 0.01s (always hits DB)
perform_access_review     | Not needed (data always fresh)
```

### Scalability

```
Current (On-Demand):
- Concurrent users: ~10-20
- Rate limit: NetSuite API (5 req/s)
- Bottleneck: External API calls

With Autonomous Collection:
- Concurrent users: 1000+
- Rate limit: PostgreSQL capacity
- Bottleneck: Database queries (easily optimized)
```

---

## Summary

This architecture provides:

1. **Flexibility**: Multiple interfaces (CLI, Desktop, Web, API)
2. **Performance**: Multi-layer caching + autonomous collection
3. **Scalability**: Database-first queries with scheduled syncs
4. **Maintainability**: Clean separation of concerns, repository pattern
5. **Reliability**: Error handling, retry logic, monitoring
6. **Extensibility**: Easy to add new connectors, agents, tools
7. **Intelligence**: AI-powered analysis and natural language understanding

The key insight from the Chase Roles incident:
- **On-demand sync** is reactive and incomplete
- **Autonomous collection** is proactive and comprehensive
- **Database-first queries** provide consistent, fast results

Next steps:
1. Implement autonomous collection agent
2. Add monitoring and alerting
3. Optimize database queries with indexes
4. Add incremental sync support
5. Implement change data capture (CDC) for real-time updates
