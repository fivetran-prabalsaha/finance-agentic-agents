# Exception Controls Storage and Recommendation Plan

**Feature:** Store and recommend mitigating controls for approved SOD exceptions
**Version:** 1.0
**Date:** 2026-02-13
**Status:** 📋 PLANNING
**Priority:** HIGH
**Estimated Effort:** 3-4 weeks

---

## Executive Summary

When compliance officers approve access requests that violate SOD rules, they often apply compensating controls to mitigate risk. Currently, each decision is made in isolation. This feature creates a **precedent database** that:

1. **Stores** approved exceptions with their controls
2. **Learns** from past decisions
3. **Recommends** similar controls for similar requests
4. **Ensures consistency** in control application
5. **Tracks effectiveness** of controls over time

**Business Value:**
- **Faster decisions:** Leverage past approvals instead of researching each time
- **Consistency:** Same risk → same controls across the organization
- **Audit defense:** "We've done this before with these controls"
- **Learning system:** Improves recommendations over time
- **Cost visibility:** Track total cost of exceptions across org

---

## Problem Statement

### Current State

**When approving an exception today:**
```
User: "Can Tax Manager have Controller role?"

System: ❌ DENY - 144 conflicts, risk 77.5/100

Options:
1. Deny
2. Split roles
3. Approve with controls - $100K/year

User: "What controls are needed?"

System: [Generic list of 12 possible controls]
```

**Problems:**
1. ❌ Controls suggested are generic (not tailored to this specific violation)
2. ❌ If we approved similar request before, that knowledge is lost
3. ❌ No way to say "We did this for Sarah last month with dual approval"
4. ❌ Inconsistent decisions (John gets different controls than Sarah for same roles)
5. ❌ Can't track which controls actually worked vs didn't

### Desired State

**With precedent database:**
```
User: "Can Tax Manager have Controller role?"

System: ❌ DENY - 144 conflicts, risk 77.5/100

💡 SIMILAR PRECEDENT FOUND:
Sarah Lee (Tax Manager) was approved for same combination 3 months ago.

Controls Applied:
✅ Dual approval workflow - $100K/year (80% risk reduction)
✅ Enhanced audit review - $50K/year (40% risk reduction)

Combined: $150K/year, 92% risk reduction
Status: Active, no violations detected since approval

Recommend: Apply same controls for this request?
```

**Benefits:**
1. ✅ Specific precedent cited (Sarah's approval)
2. ✅ Exact controls that worked before
3. ✅ Cost already known from implementation
4. ✅ Effectiveness validated (no violations in 3 months)
5. ✅ Consistency guaranteed

---

## User Stories

### Epic: Exception Control Management

**Story 1: Record Approved Exception**
- **As a** Compliance Officer
- **I want to** record when I approve an exception with controls
- **So that** future similar requests can reference my decision

**Acceptance Criteria:**
- [ ] Can record role combination + controls via MCP tool
- [ ] Stores: user, roles, controls, cost, rationale, approval date
- [ ] Links to actual compensating_controls records
- [ ] Assigns unique exception_id for tracking
- [ ] Cannot be modified after creation (append-only audit trail)

**Priority:** P0 (Must Have)

---

**Story 2: Find Similar Precedents**
- **As a** Compliance Officer
- **I want to** see if similar requests were approved before
- **So that** I can apply consistent controls

**Acceptance Criteria:**
- [ ] System automatically searches precedents when analyzing request
- [ ] Matches on: role combination, job title, violation type
- [ ] Shows top 3 most similar precedents
- [ ] Displays: who approved, when, what controls, outcome
- [ ] Can drill into full details of precedent

**Priority:** P0 (Must Have)

---

**Story 3: Auto-Recommend Controls**
- **As a** Compliance Officer
- **I want** system to recommend specific controls based on precedent
- **So that** I don't have to research the same decision again

**Acceptance Criteria:**
- [ ] If exact match found (same roles), auto-suggest same controls
- [ ] If similar match found (overlapping roles), suggest adapted controls
- [ ] Shows cost and risk reduction from precedent
- [ ] Can accept recommendation or customize
- [ ] Explanation of why these controls were chosen

**Priority:** P0 (Must Have)

---

**Story 4: Track Control Effectiveness**
- **As a** Compliance Officer
- **I want to** see if controls actually prevented violations
- **So that** I know which controls work vs don't

**Acceptance Criteria:**
- [ ] Dashboard shows all exceptions with their status
- [ ] Status: Active (no violations), Violated (controls failed), Remediated (access removed)
- [ ] For violated cases, see what went wrong
- [ ] Effectiveness score: % of exceptions still compliant after X months
- [ ] Can filter by control type to see which controls are most effective

**Priority:** P1 (Should Have)

---

**Story 5: Exception Approval Workflow**
- **As a** Compliance Officer
- **I want to** formally approve an exception request
- **So that** it's documented with all necessary details

**Acceptance Criteria:**
- [ ] Can approve request directly from analysis screen
- [ ] Must provide: business justification, controls selected, review date
- [ ] Optional: approver name, ticket reference, additional notes
- [ ] Generates approval document for audit
- [ ] Sends notification to requester

**Priority:** P1 (Should Have)

---

**Story 6: Browse Exception Library**
- **As an** Internal Auditor
- **I want to** browse all approved exceptions
- **So that** I can verify proper controls are in place

**Acceptance Criteria:**
- [ ] View all exceptions sorted by date, risk, cost
- [ ] Filter by: user, role, control type, status
- [ ] Export to CSV for audit
- [ ] See total cost of all exceptions organization-wide
- [ ] Drill into any exception for full details

**Priority:** P1 (Should Have)

---

## Data Model

### New Table: `approved_exceptions`

**Purpose:** Store all approved SOD exceptions with their controls

```sql
CREATE TABLE approved_exceptions (
    -- Identity
    exception_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exception_code VARCHAR(50) UNIQUE NOT NULL,  -- e.g., "EXC-2026-001"

    -- User/Request Info
    user_id INTEGER REFERENCES users(user_id),
    user_name VARCHAR(255) NOT NULL,
    user_email VARCHAR(255),
    job_title VARCHAR(255),
    department VARCHAR(255),

    -- Role Combination (stored as array for easy matching)
    role_ids INTEGER[] NOT NULL,
    role_names TEXT[] NOT NULL,

    -- Violation Details
    conflict_count INTEGER NOT NULL,
    critical_conflicts INTEGER,
    high_conflicts INTEGER,
    medium_conflicts INTEGER,
    low_conflicts INTEGER,
    risk_score DECIMAL(5,2),  -- 0-100

    -- Business Context
    business_justification TEXT NOT NULL,
    request_reason TEXT,
    ticket_reference VARCHAR(100),

    -- Approval Info
    approved_by VARCHAR(255) NOT NULL,
    approved_date TIMESTAMP NOT NULL DEFAULT NOW(),
    approval_authority VARCHAR(100),  -- e.g., "CFO", "Audit Committee"

    -- Review Schedule
    review_frequency VARCHAR(50),  -- e.g., "Monthly", "Quarterly", "Annual"
    next_review_date DATE,
    last_review_date DATE,

    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    -- Enum: ACTIVE, VIOLATED, REMEDIATED, EXPIRED, REVOKED
    status_reason TEXT,
    status_updated_date TIMESTAMP,

    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP,  -- Optional: auto-expire after N months

    -- Audit trail (JSONB for flexibility)
    audit_trail JSONB DEFAULT '[]'::jsonb,

    -- Search optimization
    searchable_text TEXT GENERATED ALWAYS AS (
        user_name || ' ' ||
        array_to_string(role_names, ' ') || ' ' ||
        business_justification
    ) STORED,

    CONSTRAINT valid_risk_score CHECK (risk_score >= 0 AND risk_score <= 100),
    CONSTRAINT valid_status CHECK (status IN ('ACTIVE', 'VIOLATED', 'REMEDIATED', 'EXPIRED', 'REVOKED'))
);

-- Indexes for fast lookup
CREATE INDEX idx_approved_exceptions_user ON approved_exceptions(user_id);
CREATE INDEX idx_approved_exceptions_roles ON approved_exceptions USING GIN(role_ids);
CREATE INDEX idx_approved_exceptions_status ON approved_exceptions(status);
CREATE INDEX idx_approved_exceptions_search ON approved_exceptions USING GIN(to_tsvector('english', searchable_text));
CREATE INDEX idx_approved_exceptions_date ON approved_exceptions(approved_date DESC);
```

---

### New Table: `exception_controls`

**Purpose:** Many-to-many relationship between exceptions and controls

```sql
CREATE TABLE exception_controls (
    exception_control_id SERIAL PRIMARY KEY,
    exception_id UUID NOT NULL REFERENCES approved_exceptions(exception_id) ON DELETE CASCADE,
    control_id INTEGER NOT NULL REFERENCES compensating_controls(control_id),

    -- Implementation Details
    implementation_date DATE,
    implementation_status VARCHAR(50) DEFAULT 'PLANNED',
    -- Enum: PLANNED, IN_PROGRESS, IMPLEMENTED, ACTIVE, FAILED, DEACTIVATED

    -- Cost Tracking (actual vs estimated)
    estimated_annual_cost DECIMAL(10,2),
    actual_annual_cost DECIMAL(10,2),
    implementation_cost DECIMAL(10,2),

    -- Effectiveness Tracking
    risk_reduction_percentage INTEGER,  -- From control definition
    effectiveness_score DECIMAL(5,2),  -- Actual effectiveness 0-100
    violations_prevented INTEGER DEFAULT 0,
    violations_occurred INTEGER DEFAULT 0,

    -- Notes
    implementation_notes TEXT,
    effectiveness_notes TEXT,

    -- Audit
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE(exception_id, control_id),
    CONSTRAINT valid_effectiveness CHECK (effectiveness_score IS NULL OR (effectiveness_score >= 0 AND effectiveness_score <= 100))
);

CREATE INDEX idx_exception_controls_exception ON exception_controls(exception_id);
CREATE INDEX idx_exception_controls_control ON exception_controls(control_id);
CREATE INDEX idx_exception_controls_status ON exception_controls(implementation_status);
```

---

### New Table: `exception_violations`

**Purpose:** Track when an approved exception is violated (control failure)

```sql
CREATE TABLE exception_violations (
    violation_id SERIAL PRIMARY KEY,
    exception_id UUID NOT NULL REFERENCES approved_exceptions(exception_id),

    -- Violation Details
    violation_date TIMESTAMP NOT NULL DEFAULT NOW(),
    violation_type VARCHAR(100),  -- What rule was violated
    severity VARCHAR(20),  -- CRITICAL, HIGH, MEDIUM, LOW

    -- Description
    description TEXT NOT NULL,
    root_cause TEXT,

    -- Which control failed?
    failed_control_id INTEGER REFERENCES compensating_controls(control_id),
    failure_reason TEXT,

    -- Detection
    detected_by VARCHAR(255),  -- System or person who detected
    detection_method VARCHAR(100),  -- e.g., "Audit", "Automated monitoring", "User report"

    -- Remediation
    remediation_action TEXT,
    remediation_status VARCHAR(50) DEFAULT 'OPEN',
    -- Enum: OPEN, IN_PROGRESS, RESOLVED, ACCEPTED_RISK
    remediated_date TIMESTAMP,
    remediated_by VARCHAR(255),

    -- Audit
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_exception_violations_exception ON exception_violations(exception_id);
CREATE INDEX idx_exception_violations_date ON exception_violations(violation_date DESC);
CREATE INDEX idx_exception_violations_status ON exception_violations(remediation_status);
```

---

### New Table: `exception_reviews`

**Purpose:** Track periodic reviews of approved exceptions

```sql
CREATE TABLE exception_reviews (
    review_id SERIAL PRIMARY KEY,
    exception_id UUID NOT NULL REFERENCES approved_exceptions(exception_id),

    -- Review Details
    review_date DATE NOT NULL,
    reviewer_name VARCHAR(255) NOT NULL,
    review_type VARCHAR(50),  -- e.g., "Scheduled", "Ad-hoc", "Audit-triggered"

    -- Review Outcome
    outcome VARCHAR(50) NOT NULL,
    -- Enum: APPROVED_CONTINUE, APPROVED_MODIFY, REVOKED, ESCALATED

    -- Findings
    controls_effective BOOLEAN,
    violations_found BOOLEAN,
    findings TEXT,
    recommendations TEXT,

    -- Next Review
    next_review_date DATE,

    -- Audit
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_exception_reviews_exception ON exception_reviews(exception_id);
CREATE INDEX idx_exception_reviews_date ON exception_reviews(review_date DESC);
```

---

## Features and MCP Tools

### Feature 1: Record Exception Approval

**MCP Tool:** `record_exception_approval`

**Description:** Record an approved SOD exception with its compensating controls

**Input:**
```json
{
  "user_id": 123,
  "role_names": ["Fivetran - Tax Manager", "Fivetran - Controller"],
  "control_ids": [1, 2, 5],  // Dual approval, monitoring, audit review
  "business_justification": "Sarah is senior tax manager covering for CFO vacation. Temporary 90-day access needed for quarterly close.",
  "ticket_reference": "IT-2024",
  "review_frequency": "Monthly",
  "expires_at": "2026-05-15"
}
```

**Output:**
```json
{
  "exception_id": "550e8400-e29b-41d4-a716-446655440000",
  "exception_code": "EXC-2026-001",
  "status": "ACTIVE",
  "controls_applied": [
    {
      "control_name": "Dual Approval Workflow",
      "annual_cost": 100000,
      "risk_reduction": 80
    },
    {
      "control_name": "Real-Time Monitoring",
      "annual_cost": 75000,
      "risk_reduction": 60
    },
    {
      "control_name": "Enhanced Audit Review",
      "annual_cost": 50000,
      "risk_reduction": 40
    }
  ],
  "total_annual_cost": 225000,
  "combined_risk_reduction": 94,
  "next_review_date": "2026-03-15",
  "message": "✅ Exception EXC-2026-001 approved and recorded"
}
```

**Implementation:**
```python
async def record_exception_approval(
    user_id: int,
    role_names: List[str],
    control_ids: List[int],
    business_justification: str,
    approved_by: str,
    ticket_reference: Optional[str] = None,
    review_frequency: str = "Quarterly",
    expires_at: Optional[str] = None
) -> str:
    """
    Record an approved SOD exception with compensating controls
    """
    # 1. Get user details
    user = session.query(User).filter_by(user_id=user_id).first()

    # 2. Get role IDs from names
    role_ids = get_role_ids_from_names(role_names)

    # 3. Calculate violation metrics (from existing analysis)
    analysis = analyze_access_request(role_names, {"job_title": user.job_title})

    # 4. Create exception record
    exception = ApprovedExceptionModel(
        user_id=user_id,
        user_name=user.name,
        user_email=user.email,
        job_title=user.job_title,
        department=user.department,
        role_ids=role_ids,
        role_names=role_names,
        conflict_count=analysis['total_conflicts'],
        critical_conflicts=analysis['critical_count'],
        risk_score=analysis['risk_score'],
        business_justification=business_justification,
        approved_by=approved_by,
        ticket_reference=ticket_reference,
        review_frequency=review_frequency,
        expires_at=expires_at
    )
    session.add(exception)
    session.flush()  # Get exception_id

    # 5. Link controls
    for control_id in control_ids:
        control = session.query(CompensatingControl).get(control_id)
        exception_control = ExceptionControlModel(
            exception_id=exception.exception_id,
            control_id=control_id,
            estimated_annual_cost=control.annual_cost_estimate,
            risk_reduction_percentage=control.risk_reduction_percentage
        )
        session.add(exception_control)

    # 6. Calculate next review date
    if review_frequency == "Monthly":
        exception.next_review_date = datetime.now() + timedelta(days=30)
    elif review_frequency == "Quarterly":
        exception.next_review_date = datetime.now() + timedelta(days=90)
    # ... etc

    session.commit()

    # 7. Return formatted response
    return format_exception_approval_response(exception)
```

---

### Feature 2: Find Similar Precedents

**MCP Tool:** `find_similar_exceptions`

**Description:** Search for previously approved exceptions similar to current request

**Input:**
```json
{
  "role_names": ["Fivetran - Tax Manager", "Fivetran - Controller"],
  "user_context": {
    "job_title": "Tax Manager",
    "department": "Finance"
  },
  "limit": 3
}
```

**Output:**
```markdown
🔍 SIMILAR PRECEDENTS FOUND (3 matches)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. EXACT MATCH (100% similarity)
   Exception: EXC-2026-001
   User: Sarah Lee (Tax Manager, Finance)
   Roles: Fivetran - Tax Manager + Fivetran - Controller
   Approved: 2025-12-15 (3 months ago)

   Controls Applied:
   ✅ Dual Approval Workflow ($100K/year) - 80% risk reduction
   ✅ Real-Time Monitoring ($75K/year) - 60% risk reduction
   ✅ Enhanced Audit Review ($50K/year) - 40% risk reduction

   Total Cost: $225K/year
   Risk Reduction: 94%
   Status: ✅ ACTIVE (no violations detected)
   Approved by: John Smith (Compliance Officer)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2. PARTIAL MATCH (75% similarity)
   Exception: EXC-2025-042
   User: Mike Chen (Senior Accountant, Finance)
   Roles: Fivetran - Accountant + Fivetran - Controller
   Approved: 2025-10-20 (5 months ago)

   Controls Applied:
   ✅ Dual Approval Workflow ($100K/year)
   ✅ Enhanced Audit Review ($50K/year)

   Total Cost: $150K/year
   Risk Reduction: 88%
   Status: ✅ ACTIVE (1 minor violation, remediated)
   Approved by: Jane Doe (CFO)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

3. SIMILAR RISK PROFILE (60% similarity)
   Exception: EXC-2025-028
   User: Lisa Wong (Controller, Finance)
   Roles: Fivetran - Controller + Fivetran - AP Approval
   Approved: 2025-08-10 (7 months ago)

   Controls Applied:
   ✅ Dual Approval Workflow ($100K/year)
   ✅ Transaction Limits ($25K/year)

   Total Cost: $125K/year
   Risk Reduction: 85%
   Status: ✅ ACTIVE (no violations)
   Approved by: John Smith (Compliance Officer)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 RECOMMENDATION:
Based on precedent EXC-2026-001 (exact match), recommend same controls:
- Dual Approval Workflow
- Real-Time Monitoring
- Enhanced Audit Review

Estimated cost: $225K/year
Expected risk reduction: 94%
```

**Implementation:**
```python
async def find_similar_exceptions(
    role_names: List[str],
    user_context: Dict[str, Any],
    limit: int = 3
) -> str:
    """
    Find previously approved exceptions similar to current request
    """
    # 1. Convert role names to IDs
    role_ids = get_role_ids_from_names(role_names)
    role_ids_set = set(role_ids)

    # 2. Query all active exceptions
    exceptions = session.query(ApprovedExceptionModel).filter(
        ApprovedExceptionModel.status == 'ACTIVE'
    ).all()

    # 3. Calculate similarity for each exception
    similarities = []
    for exception in exceptions:
        exception_role_ids = set(exception.role_ids)

        # Similarity based on role overlap
        intersection = len(role_ids_set & exception_role_ids)
        union = len(role_ids_set | exception_role_ids)
        role_similarity = intersection / union if union > 0 else 0

        # Bonus for matching job title
        job_title_match = 0.2 if exception.job_title == user_context.get('job_title') else 0

        # Bonus for matching department
        dept_match = 0.1 if exception.department == user_context.get('department') else 0

        # Total similarity (0-100%)
        total_similarity = (role_similarity * 0.7) + job_title_match + dept_match

        similarities.append({
            'exception': exception,
            'similarity': total_similarity
        })

    # 4. Sort by similarity and take top N
    similarities.sort(key=lambda x: x['similarity'], reverse=True)
    top_matches = similarities[:limit]

    # 5. Load controls for each match
    for match in top_matches:
        exception = match['exception']
        controls = session.query(ExceptionControlModel).filter(
            ExceptionControlModel.exception_id == exception.exception_id
        ).all()
        match['controls'] = controls

    # 6. Format response
    return format_similar_exceptions_response(top_matches)
```

---

### Feature 3: Get Exception Details

**MCP Tool:** `get_exception_details`

**Description:** Get full details of a specific exception

**Input:**
```json
{
  "exception_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Output:** Full exception details including controls, violations, reviews

---

### Feature 4: List All Exceptions

**MCP Tool:** `list_approved_exceptions`

**Description:** Browse all approved exceptions with filters

**Input:**
```json
{
  "status": "ACTIVE",  // Optional filter
  "user_id": 123,      // Optional filter
  "limit": 10,
  "offset": 0
}
```

**Output:** Paginated list of exceptions with summary info

---

### Feature 5: Record Exception Violation

**MCP Tool:** `record_exception_violation`

**Description:** Record when an approved exception is violated (control failure)

**Input:**
```json
{
  "exception_id": "550e8400-e29b-41d4-a716-446655440000",
  "violation_type": "Unauthorized Transaction",
  "severity": "CRITICAL",
  "description": "User approved $1M invoice without dual approval",
  "failed_control_id": 1,
  "failure_reason": "Dual approval workflow was bypassed"
}
```

**Output:** Violation recorded, exception status updated to VIOLATED

---

### Feature 6: Exception Effectiveness Dashboard

**MCP Tool:** `get_exception_effectiveness_stats`

**Description:** Summary statistics on exception effectiveness

**Output:**
```markdown
📊 EXCEPTION EFFECTIVENESS DASHBOARD

Total Active Exceptions: 47
Total Cost: $8.2M/year

By Status:
✅ Active (no violations): 42 (89%)
⚠️ Active (minor violations): 3 (6%)
❌ Violated (controls failed): 2 (4%)

Most Effective Controls:
1. Dual Approval Workflow: 98% effectiveness (1 failure in 50 uses)
2. Enhanced Audit Review: 96% effectiveness (2 failures in 50 uses)
3. Real-Time Monitoring: 94% effectiveness (3 failures in 50 uses)

Least Effective Controls:
1. Transaction Limits: 78% effectiveness (11 failures in 50 uses)
2. Management Review: 82% effectiveness (9 failures in 50 uses)

ROI Analysis:
- Total cost of controls: $8.2M/year
- Violations prevented: 186 (estimated)
- Potential fraud prevented: $45M (estimated)
- ROI: 5.5x

Recommendations:
⚠️ Review EXC-2025-015 (violated twice, controls ineffective)
💡 Consider replacing Transaction Limits with Dual Approval (higher effectiveness)
```

---

## Implementation Plan

### Phase 1: Data Model and Storage (Week 1)

**Tasks:**
1. Create database migration for new tables
2. Create SQLAlchemy models
3. Write repository classes
4. Add seed data (test exceptions)
5. Write unit tests for models

**Deliverables:**
- [ ] Migration: `database/migrations/versions/XXX_add_exception_tables.py`
- [ ] Models: `models/approved_exception.py`, `models/exception_control.py`, etc.
- [ ] Repos: `repositories/exception_repository.py`
- [ ] Tests: `tests/test_exception_models.py`

**Acceptance Criteria:**
- All tables created successfully
- Can insert/query exception records
- All relationships work (foreign keys, many-to-many)
- Unit tests pass (>90% coverage)

---

### Phase 2: Core Logic and MCP Tools (Week 2)

**Tasks:**
1. Implement similarity matching algorithm
2. Create MCP tool handlers
3. Add to mcp_tools.py tool registry
4. Integrate with existing analyze_access_request
5. Write integration tests

**Deliverables:**
- [ ] Tool: `record_exception_approval`
- [ ] Tool: `find_similar_exceptions`
- [ ] Tool: `get_exception_details`
- [ ] Tool: `list_approved_exceptions`
- [ ] Integration: Auto-suggest precedents in analyze_access_request

**Acceptance Criteria:**
- Can record exception via MCP tool
- Can find similar exceptions with >80% accuracy
- Auto-suggestion appears in analysis responses
- All tools tested with real scenarios

---

### Phase 3: Violation Tracking (Week 3)

**Tasks:**
1. Implement violation recording
2. Create effectiveness calculation logic
3. Add dashboard statistics
4. Integrate with existing violation detection
5. Write effectiveness reports

**Deliverables:**
- [ ] Tool: `record_exception_violation`
- [ ] Tool: `get_exception_effectiveness_stats`
- [ ] Logic: Automatic violation detection for exceptions
- [ ] Reports: Effectiveness dashboard

**Acceptance Criteria:**
- Can record violations and link to exceptions
- Effectiveness scores calculate correctly
- Dashboard shows meaningful insights
- Alerts sent when exception violated

---

### Phase 4: Polish and Documentation (Week 4)

**Tasks:**
1. Create user documentation
2. Add to PRD and architecture docs
3. Create demo scenarios
4. Performance testing
5. Security review

**Deliverables:**
- [ ] Doc: Updated PRD with exception features
- [ ] Doc: Exception management user guide
- [ ] Demo: Walkthrough video/script
- [ ] Tests: Performance benchmarks
- [ ] Review: Security assessment

**Acceptance Criteria:**
- Documentation complete and reviewed
- Demo shows end-to-end workflow
- Performance meets targets (<2s queries)
- Security review passed

---

## Integration Points

### 1. Analyze Access Request

**Current:**
```python
async def analyze_access_request(role_names, user_context):
    # Analyze conflicts
    # Calculate risk
    # Return recommendation
```

**Enhanced:**
```python
async def analyze_access_request(role_names, user_context):
    # Analyze conflicts
    # Calculate risk

    # NEW: Search for similar precedents
    precedents = await find_similar_exceptions(role_names, user_context, limit=3)

    # NEW: Add precedent section to response
    if precedents:
        response += "\n\n💡 SIMILAR PRECEDENTS FOUND:\n"
        response += format_precedents(precedents)

        # Auto-recommend controls from best match
        best_match = precedents[0]
        if best_match['similarity'] > 0.8:  # >80% similar
            response += f"\n\n✅ RECOMMENDED: Apply same controls as {best_match['exception_code']}"

    return response
```

---

### 2. Compensating Controls Tool

**Current:**
```python
async def get_compensating_controls(severity_level):
    # Return generic list of controls for severity
```

**Enhanced:**
```python
async def get_compensating_controls(severity_level, role_names=None):
    # Return generic list

    # NEW: If role_names provided, show which controls worked for similar roles
    if role_names:
        precedents = await find_similar_exceptions(role_names, {})
        if precedents:
            response += "\n\n📊 CONTROLS USED FOR SIMILAR ROLES:\n"
            response += format_control_usage_stats(precedents)
```

---

### 3. Violation Detection

**Current:**
```python
async def detect_violations():
    # Find all violations
    # Store in violations table
```

**Enhanced:**
```python
async def detect_violations():
    # Find all violations

    # NEW: Check if violation is from an approved exception
    for violation in violations:
        exception = find_active_exception_for_user(violation.user_id)
        if exception:
            # This user has approved exception, record as exception violation
            await record_exception_violation(
                exception_id=exception.exception_id,
                violation_type=violation.rule_name,
                severity=violation.severity
            )
            # Update exception status to VIOLATED
            exception.status = 'VIOLATED'
```

---

## UI/UX Examples

### Example 1: Recording Exception Approval

**User Flow:**
```
1. User: "Can Tax Manager have Controller role?"

2. System: ❌ DENY - 144 conflicts, 77.5/100 risk
   [Shows full analysis]

3. User: "We need to approve this for Sarah - she's covering CFO vacation.
         What controls do we need?"

4. System: Recommended controls for CRITICAL violations:
   1. Dual Approval ($100K/year) - 80% reduction
   2. Real-Time Monitoring ($75K/year) - 60% reduction
   3. Enhanced Audit Review ($50K/year) - 40% reduction
   Total: $225K/year, 94% combined reduction

5. User: "Approve with those controls. This is for ticket IT-2024,
         expires in 90 days, review monthly."

6. System calls: record_exception_approval(...)

7. System: ✅ Exception EXC-2026-001 approved

   Recorded:
   - User: Sarah Lee (Tax Manager)
   - Roles: Tax Manager + Controller
   - Controls: Dual Approval, Monitoring, Audit Review
   - Cost: $225K/year
   - Review: Monthly, next 2026-03-15
   - Expires: 2026-05-15

   Exception code EXC-2026-001 can be referenced in future similar requests.
```

---

### Example 2: Leveraging Precedent

**User Flow:**
```
1. User: "Can Tax Manager have Controller role for John Smith?"

2. System analyzes and finds precedent:

   ❌ DENY - 144 conflicts, 77.5/100 risk

   💡 SIMILAR PRECEDENT FOUND:
   Sarah Lee (Tax Manager) was approved for same combination 3 months ago.
   Exception: EXC-2026-001

   Controls Applied:
   ✅ Dual Approval Workflow ($100K/year)
   ✅ Real-Time Monitoring ($75K/year)
   ✅ Enhanced Audit Review ($50K/year)

   Total: $225K/year, 94% risk reduction
   Status: Active, no violations detected

   ✅ RECOMMENDED: Apply same controls for John Smith?

3. User: "Yes, approve with same controls, ticket IT-2049"

4. System: ✅ Exception EXC-2026-002 approved

   Applied controls from precedent EXC-2026-001:
   - Dual Approval Workflow
   - Real-Time Monitoring
   - Enhanced Audit Review

   Total cost: $225K/year (same as precedent)

   Consistency maintained: 2 Tax Managers now have same exception controls.
```

---

### Example 3: Tracking Effectiveness

**User Flow:**
```
1. User: "Show me exception effectiveness"

2. System: 📊 EXCEPTION EFFECTIVENESS DASHBOARD

   Total Active: 47 exceptions
   Total Cost: $8.2M/year

   Status:
   ✅ Active (no violations): 42 (89%)
   ⚠️ Active (minor violations): 3 (6%)
   ❌ Violated: 2 (4%)

   Most Effective Controls:
   1. Dual Approval: 98% effective (1 failure in 50 uses)
   2. Enhanced Audit: 96% effective
   3. Real-Time Monitoring: 94% effective

   ⚠️ ALERTS:
   - EXC-2025-015 violated twice (controls failed)
   - EXC-2025-032 approaching review date

3. User: "Show details on EXC-2025-015"

4. System: Exception EXC-2025-015

   User: Mike Chen (Accountant)
   Roles: Accountant + AP Approval
   Approved: 2025-08-15 (6 months ago)
   Controls: Transaction Limits ($25K/year)

   Violations:
   1. 2025-11-20: Approved $500K invoice (exceeded limit)
      Status: Remediated
   2. 2026-01-10: Approved $750K invoice (exceeded limit)
      Status: Open

   ⚠️ RECOMMENDATION:
   Transaction Limits control is ineffective for this user.
   Suggest: Replace with Dual Approval Workflow (98% effective)
```

---

## Success Metrics

### Functional Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| **Exception Recording** | <30 seconds | Time to complete record_exception_approval |
| **Precedent Search** | <2 seconds | find_similar_exceptions query time |
| **Match Accuracy** | >80% | % of precedents marked "relevant" by users |
| **Auto-Suggestion Rate** | >60% | % of analyses that find similar precedent |
| **Adoption Rate** | >50% | % of approvals that record exception |

### Business Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| **Consistency Improvement** | >70% | Same roles get same controls 70%+ of time |
| **Decision Time Reduction** | -50% | Time from request to approval decision |
| **Control Effectiveness** | >90% | % of exceptions with no violations |
| **Cost Visibility** | 100% | All exception costs tracked |
| **Audit Readiness** | 100% | All exceptions documented with rationale |

### Quality Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| **Data Completeness** | >95% | % of exceptions with all required fields |
| **Precedent Relevance** | >4.0/5.0 | User rating of precedent suggestions |
| **Control Success Rate** | >90% | % of controls that prevent violations |
| **False Match Rate** | <10% | % of precedents that are actually dissimilar |

---

## Security and Compliance

### Data Protection

**Sensitive Data:**
- Business justifications may contain confidential info
- User names and departments are PII
- Approval authorities may be sensitive

**Controls:**
- Encrypt business_justification field at rest
- Restrict exception viewing to compliance roles
- Audit all exception access (who viewed what when)
- Cannot modify exceptions after approval (append-only)

### Audit Trail

**What to Log:**
- All exception creations with full details
- All exception views (who accessed which exception)
- All modifications (status changes, reviews)
- All violation recordings
- All searches (what was searched, what was found)

**Retention:**
- Exception records: Permanent (SOX requirement)
- Audit logs: 7 years (SOX requirement)
- Violation records: Permanent

### Access Control

**Who Can:**
- **Record exceptions:** Compliance Officers, CFO, Audit Committee
- **View exceptions:** Compliance team, Internal Audit, Finance Leadership
- **Modify status:** Compliance Officers only (with approval)
- **Delete exceptions:** No one (append-only system)

---

## Risks and Mitigation

### Risk 1: Over-Reliance on Precedent

**Risk:** Users blindly follow precedent without considering current context

**Mitigation:**
- Always show full analysis first, precedent is supplemental
- Require business justification even when using precedent
- Flag if circumstances have changed (e.g., control failed before)
- Annual review of all exceptions

### Risk 2: Precedent Database Gaming

**Risk:** Users create fake exceptions to establish "precedent" for future use

**Mitigation:**
- Require approval authority (CFO, Audit Committee)
- Audit trail shows who approved each exception
- Effectiveness tracking exposes ineffective exceptions
- Annual review by external auditor

### Risk 3: Data Quality Degradation

**Risk:** Missing or incorrect data makes precedents unreliable

**Mitigation:**
- Required fields enforced by schema
- Validation rules on data entry
- Periodic data quality audits
- User feedback mechanism ("This precedent wasn't relevant")

### Risk 4: Performance Issues

**Risk:** Precedent search becomes slow as database grows

**Mitigation:**
- Indexes on key search fields (roles, job title, status)
- Cache common searches (same role combinations)
- Limit active precedents to last 2 years (archive older)
- Performance testing with 10K+ exceptions

---

## Testing Strategy

### Unit Tests

**Test Cases:**
1. Create exception with valid data → success
2. Create exception with missing required field → error
3. Find exact match precedent → returns correct exception
4. Find similar precedent → returns top 3 matches sorted by similarity
5. Calculate effectiveness score → correct percentage
6. Record violation → updates exception status
7. Expire old exceptions → status changes to EXPIRED

### Integration Tests

**Test Cases:**
1. End-to-end: Analyze request → Find precedent → Record exception
2. Precedent suggestion in analyze_access_request response
3. Violation detection updates exception status
4. Review reminder triggers at correct date
5. Dashboard statistics calculate correctly

### User Acceptance Tests

**Test Scenarios:**
1. Compliance officer approves exception with controls
2. Same officer approves similar request using precedent
3. Internal auditor reviews exception effectiveness dashboard
4. IT admin checks if precedent exists before submitting ticket
5. CFO reviews all active exceptions and total cost

---

## Open Questions

**Q1: Should we limit precedent age?**
- Only show precedents from last 2 years?
- Rationale: Business context changes, old precedents may not be relevant
- Decision: TBD with Compliance team

**Q2: How to handle expired exceptions?**
- Automatically revoke access when exception expires?
- Or just flag for review?
- Decision: TBD (integration with NetSuite needed for auto-revoke)

**Q3: Should precedent search be automatic or manual?**
- Current plan: Automatic (shows in all analyses)
- Alternative: Only show when user asks "any precedents?"
- Decision: TBD based on user feedback

**Q4: How to price control implementation?**
- Use estimated cost from control library?
- Track actual cost and update estimates?
- Decision: Start with estimates, track actuals, report variance

**Q5: Cross-system exceptions?**
- How to handle precedents when adding Salesforce, Coupa?
- Same user with NetSuite exception + new Salesforce request?
- Decision: Defer to v2.0 (multi-system)

---

## Next Steps

**Immediate Actions:**

1. **Stakeholder Review** (This Week)
   - [ ] Review plan with Compliance Officer (Sarah)
   - [ ] Review with Internal Audit (Mike)
   - [ ] Review with CFO for budget approval
   - [ ] Get sign-off on data model and features

2. **Technical Spike** (Next Week)
   - [ ] Prototype similarity matching algorithm
   - [ ] Test performance with 1000+ exceptions
   - [ ] Validate database design with DBA
   - [ ] Estimate exact effort (currently 3-4 weeks)

3. **Implementation Start** (Week 3)
   - [ ] Create feature branch: `feature/exception-controls`
   - [ ] Start Phase 1: Data model and storage
   - [ ] Daily standups to track progress

---

## Conclusion

This feature creates a **learning system** that improves over time:

1. **First approval:** Manual research, generic controls
2. **Second approval:** Precedent found, specific controls recommended
3. **Third approval:** Proven controls, faster decision
4. **N approvals:** Highly optimized control selection, consistency guaranteed

**Business Value:**
- Faster decisions (minutes vs hours)
- Consistent control application
- Lower total cost (avoid over-controlling)
- Better audit defense ("We've done this before")
- Continuous improvement (learn what works)

**Ready to proceed?** Awaiting stakeholder sign-off to begin implementation.

---

**Plan Version:** 1.0
**Last Updated:** 2026-02-13
**Status:** 📋 PLANNING - Pending Approval
**Next Review:** 2026-02-20
