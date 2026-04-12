# SOD Access Review - Detailed Checklist

**Purpose:** Step-by-step methodology for systematic SOD access reviews

---

## Pre-Review Checklist

### Data Verification
- [ ] Check data freshness: `get_collection_agent_status()`
- [ ] Last sync within 24 hours
- [ ] No sync errors in recent history
- [ ] If stale: Trigger `trigger_manual_sync(sync_type="incremental")`

### Scope Clarification
- [ ] Confirm review scope with requestor
- [ ] Department? Role? Individual?
- [ ] Active users only, or include inactive?
- [ ] Any specific focus areas? (e.g., "Focus on payment processing")

### Expected Coverage
- [ ] Department: Typically 20-100 users
- [ ] Role: Typically 5-50 users
- [ ] Individual: 1 user

---

## Review Execution Checklist

### Step 1: Scope Definition ✅

- [ ] Identify review type (department/role/individual)
- [ ] Confirm exact name/identifier
- [ ] Set limit appropriately (50-100 for departments, 500 for roles)

### Step 2: Data Collection ✅

#### For Department Reviews:
- [ ] Call `list_all_users` with `filter_by_department`
- [ ] Verify user count matches expectations
- [ ] Note: Department filter uses partial matching
- [ ] Record total users found
- [ ] Record active vs inactive breakdown

#### For Role Reviews:
- [ ] Call `list_all_users` (may need high limit)
- [ ] Filter results to users with specified role
- [ ] Count users with role
- [ ] Optional: Analyze role itself with `analyze_role_permissions`

#### For Individual Reviews:
- [ ] Call `get_user_violations` directly
- [ ] Use format="table" for overview
- [ ] Record user details (name, email, department, roles)

### Step 3: Violation Analysis ✅

#### For Each User (or Top 20):
- [ ] Call `get_user_violations` with format="table"
- [ ] Record violation counts by severity:
  - [ ] CRITICAL count
  - [ ] HIGH count
  - [ ] MEDIUM count
  - [ ] LOW count
  - [ ] Total count
- [ ] Note primary conflict types
- [ ] Identify users with >10 CRITICAL violations

#### Aggregate Statistics:
- [ ] Calculate total violations across all users
- [ ] Calculate average violations per user
- [ ] Identify most common violation types
- [ ] Count users with zero violations (good performers)

#### Prioritization:
- [ ] Sort users by CRITICAL violations (descending)
- [ ] Secondary sort by HIGH violations
- [ ] Tertiary sort by total violations
- [ ] Flag top 5-10 users for immediate action

### Step 4: Risk Prioritization ✅

#### Immediate Actions (Priority 1):
- [ ] Identify users with >10 CRITICAL violations
- [ ] Flag AP Entry + Approval conflicts
- [ ] Flag Journal Entry + Approval conflicts
- [ ] Flag Admin + Regular User combinations
- [ ] List users requiring action THIS WEEK

#### Short-Term Actions (Priority 2):
- [ ] Identify users with >20 HIGH violations
- [ ] Flag payment processing + payment approval
- [ ] Flag vendor master + invoice processing
- [ ] List users requiring action THIS MONTH

#### Long-Term Actions (Priority 3):
- [ ] Identify users with >50 MEDIUM violations
- [ ] Note other SOD conflicts
- [ ] Plan for quarterly review
- [ ] Document for next audit cycle

### Step 5: Executive Summary ✅

#### Overview Section:
- [ ] Review title (department/role/user name)
- [ ] Review date
- [ ] Scope description
- [ ] Coverage (X users analyzed)

#### Summary Statistics Table:
- [ ] Total users
- [ ] Users with violations (count + percentage)
- [ ] CRITICAL violations (total)
- [ ] HIGH violations (total)
- [ ] MEDIUM violations (total)
- [ ] LOW violations (total)
- [ ] Average violations per user

#### Top Violators Table:
- [ ] Include top 5-10 users
- [ ] Columns: Rank, Name, Email, CRITICAL, HIGH, MEDIUM, Total, Primary Risk
- [ ] Sort by CRITICAL then HIGH then Total

#### Common Patterns Section:
- [ ] Most frequent conflict type
- [ ] Most common problematic role combination
- [ ] Departments/roles at highest risk
- [ ] Comparison to company average (if available)

### Step 6: Remediation Recommendations ✅

#### For Each High-Priority User:
- [ ] Specific conflict identified
- [ ] Current roles listed
- [ ] Recommended action (role removal or control)
- [ ] Impact assessment (permissions lost)
- [ ] Alternative solution provided
- [ ] Timeline assigned (week/month/quarter)

#### Organization-Wide Recommendations:
- [ ] Policy changes needed?
- [ ] Role redesign opportunities?
- [ ] Training requirements?
- [ ] Process improvements?

### Step 7: Next Steps ✅

- [ ] Offer Excel export for distribution
- [ ] Suggest remediation skill for implementation
- [ ] Offer recurring review scheduling
- [ ] Provide deep-dive options if needed

---

## Post-Review Checklist

### Documentation
- [ ] Executive summary saved
- [ ] Excel report generated (if requested)
- [ ] Findings shared with stakeholders
- [ ] Remediation timeline established

### Follow-Up Planning
- [ ] Schedule remediation meetings for Priority 1 users
- [ ] Assign ownership for remediation actions
- [ ] Set up tracking mechanism (spreadsheet/tickets)
- [ ] Schedule follow-up review (30/60/90 days)

### Metrics Tracking
- [ ] Record baseline violation counts
- [ ] Set reduction targets
- [ ] Track remediation completion rate
- [ ] Monitor re-occurrence rate

### Communication
- [ ] Brief executives (risk summary + timeline)
- [ ] Inform managers (specific users + actions)
- [ ] Notify users (why it matters + process)
- [ ] Update compliance team (audit documentation)

---

## Quality Checks

### Before Finalizing Report

#### Data Quality:
- [ ] All user counts verified
- [ ] Violation counts match detail records
- [ ] No duplicate users in top violators list
- [ ] Primary risks accurately identified

#### Analysis Quality:
- [ ] Prioritization makes business sense
- [ ] Recommendations are actionable
- [ ] Timeline is realistic
- [ ] Impact assessments are accurate

#### Report Quality:
- [ ] No typos or formatting errors
- [ ] Tables display correctly
- [ ] Numbers add up correctly
- [ ] Recommendations are clear and specific

---

## Common Mistakes to Avoid

### ❌ Don't:
- Query all users when only department is needed (slow)
- Use detailed format for initial overview (overwhelming)
- Recommend generic "fix violations" (not actionable)
- Ignore business context (some conflicts are justified)
- Skip verification after sync (data may be stale)
- Forget to document exceptions (audit trail critical)
- Overwhelm executives with 100 users (show top 10)

### ✅ Do:
- Use partial department matching ("Finance" not "Fivetran : G&A : Finance")
- Start with table format, switch to detailed only when needed
- Provide specific remediation actions ("Remove AP Clerk role")
- Consider compensating controls as alternative
- Always verify data currency before analysis
- Document all exceptions with business justification
- Focus executive attention on highest priority (top 5-10)

---

## Review Types Comparison

### Department Review
**When:** Compliance audit, organizational risk assessment
**Scope:** 20-100 users typically
**Duration:** 10-15 minutes
**Output:** Organizational trends, systemic issues
**Best For:** Executive briefings, policy decisions

### Role Review
**When:** Role redesign, access certification
**Scope:** 5-50 users typically
**Duration:** 5-10 minutes
**Output:** Role-specific risks, assignment patterns
**Best For:** Access management, role governance

### Individual Review
**When:** User onboarding/offboarding, incident investigation
**Scope:** 1 user
**Duration:** 2-3 minutes
**Output:** User-specific violations, remediation plan
**Best For:** Remediation, access requests

---

## Escalation Criteria

### Escalate to Management If:
- [ ] >50% of department has CRITICAL violations
- [ ] Same conflict affects >10 users (systemic issue)
- [ ] Executive-level users have high-risk conflicts
- [ ] Violations indicate potential fraud pattern
- [ ] Required remediation impacts business operations

### Escalate to Compliance If:
- [ ] CRITICAL violations not remediated in 30 days
- [ ] Repeated exceptions without controls
- [ ] Users refusing to cooperate with remediation
- [ ] External audit finding related to violations
- [ ] Regulatory requirement at risk

---

## Templates & Tools

### Quick Reference: MCP Tools

| Task | Tool | Parameters |
|------|------|------------|
| List department users | `list_all_users` | `filter_by_department` |
| Get user violations | `get_user_violations` | `user_identifier`, `format="table"` |
| Analyze role | `analyze_role_permissions` | `role_name` |
| Export report | `generate_violation_report` | `format="excel"` |
| Find precedents | `find_similar_exceptions` | `role_names`, `job_title` |

### Quick Reference: Severity Levels

| Level | Action Required | Timeline | Example Conflicts |
|-------|----------------|----------|-------------------|
| CRITICAL | Immediate | This week | AP Entry + Approval |
| HIGH | Urgent | This month | Payment Processing + Approval |
| MEDIUM | Important | This quarter | Related but separated duties |
| LOW | Monitor | Annual review | Minimal risk overlap |

---

## Version History

- **v1.0.0** (2026-02-14): Initial checklist for SOD Access Review skill
- Aligned with SKILL.md instructions
- Based on 18 SOD rules in production
- Tested with Finance department review (76 users)

---

**Related Documents:**
- `../SKILL.md` - Main skill instructions
- `../assets/report-template.md` - Report format
- `../../README.md` - Skills overview
