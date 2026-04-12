# SOD Access Review - Executive Summary Template

**Use this template for consistent reporting across all access reviews**

---

## Report Header

```
🔍 SOD ACCESS REVIEW: {Scope Name}
═══════════════════════════════════════════════════════════════

📅 Review Date:     {YYYY-MM-DD}
👤 Reviewed By:     {Reviewer Name/Role}
🎯 Scope:           {Department / Role / User}
📊 Coverage:        {X users analyzed}
⚙️  System:          {NetSuite / Okta / Salesforce}
```

---

## Executive Summary

```
### Overview

This review analyzed {X} users {in [department] / with [role] / named [user]}
for Segregation of Duties (SOD) violations. The analysis identified {Y} users
with violations requiring attention, with {Z} users requiring immediate action.

### Key Findings

- **{X%}** of users have at least one SOD violation
- **{N}** CRITICAL violations require immediate remediation (this week)
- **{N}** HIGH violations require urgent attention (this month)
- **Common Pattern:** {Most frequent conflict type across users}

### Risk Level: {LOW / MEDIUM / HIGH / CRITICAL}

{Brief explanation of overall risk level determination}
```

---

## Summary Statistics

```
| Metric                   | Value        | Benchmark    | Status |
|--------------------------|--------------|--------------|--------|
| Total Users              | {count}      | -            | ℹ️      |
| Users with Violations    | {count} ({pct}%) | <20% target | {🔴/🟡/🟢} |
| 🔴 CRITICAL Violations   | {count}      | 0 target     | {🔴/🟡/🟢} |
| 🟠 HIGH Violations       | {count}      | <10 target   | {🔴/🟡/🟢} |
| 🟡 MEDIUM Violations     | {count}      | <50 target   | {🔴/🟡/🟢} |
| 🟢 LOW Violations        | {count}      | Monitor only | ℹ️      |
| Avg Violations per User  | {average}    | <5 target    | {🔴/🟡/🟢} |
```

**Status Legend:**
- 🔴 Exceeds threshold, immediate action required
- 🟡 Approaching threshold, monitor closely
- 🟢 Within acceptable range
- ℹ️ Informational, no action needed

---

## Top Violators Requiring Action

```
### Priority 1: Immediate Action Required (This Week)

| Rank | User Name       | Email                    | CRIT | HIGH | MED | Total | Primary Risk             |
|------|-----------------|--------------------------|------|------|-----|-------|--------------------------|
| 1    | {Name}          | {email}                  | {N}  | {N}  | {N} | {N}   | {Conflict Type}          |
| 2    | {Name}          | {email}                  | {N}  | {N}  | {N} | {N}   | {Conflict Type}          |
| 3    | {Name}          | {email}                  | {N}  | {N}  | {N} | {N}   | {Conflict Type}          |
| ...  | ...             | ...                      | ...  | ...  | ... | ...   | ...                      |

### Priority 2: Urgent Attention (This Month)

| Rank | User Name       | Email                    | CRIT | HIGH | MED | Total | Primary Risk             |
|------|-----------------|--------------------------|------|------|-----|-------|--------------------------|
| {N}  | {Name}          | {email}                  | {N}  | {N}  | {N} | {N}   | {Conflict Type}          |
| ...  | ...             | ...                      | ...  | ...  | ... | ...   | ...                      |

### Priority 3: Important (This Quarter)

| Rank | User Name       | Email                    | CRIT | HIGH | MED | Total | Primary Risk             |
|------|-----------------|--------------------------|------|------|-----|-------|--------------------------|
| {N}  | {Name}          | {email}                  | {N}  | {N}  | {N} | {N}   | {Conflict Type}          |
| ...  | ...             | ...                      | ...  | ...  | ... | ...   | ...                      |
```

---

## Common Violation Patterns

```
### Pattern Analysis

The following patterns were identified across multiple users:

1. **{Conflict Type}** - {N} users affected
   - **Conflicting Roles:** {Role A} + {Role B}
   - **Business Risk:** {Description of fraud/error risk}
   - **Recommendation:** {Organization-wide remediation approach}

2. **{Conflict Type}** - {N} users affected
   - **Conflicting Roles:** {Role A} + {Role B}
   - **Business Risk:** {Description of fraud/error risk}
   - **Recommendation:** {Organization-wide remediation approach}

3. **{Conflict Type}** - {N} users affected
   ...

### Comparison to Organization

| Metric                     | This Scope | Company Avg | Variance |
|----------------------------|------------|-------------|----------|
| Violation Rate             | {pct}%     | {pct}%      | {+/- N%} |
| Avg Violations per User    | {avg}      | {avg}       | {+/- N}  |
| CRITICAL per User          | {avg}      | {avg}       | {+/- N}  |

**Analysis:** {Interpretation of comparison - is this scope higher/lower risk than average?}
```

---

## Detailed Recommendations

```
### Immediate Actions (Complete by: {Date, +7 days})

#### 1. {User Name} - {Primary Conflict}

**Current State:**
- Email: {email}
- Department: {department}
- Job Title: {title}
- Roles: {Role 1}, {Role 2}, {Role 3}
- Violations: {N} CRITICAL, {N} HIGH, {N} MEDIUM

**Issue:**
{Specific description of SOD conflict and why it's a risk}

**Recommended Solution:**
- **Option A (Preferred):** Remove "{Role Name}" role
  - Impact: User loses {list of permissions}
  - User retains: {remaining permissions from other roles}
  - Implementation time: 5 minutes
  - Violations resolved: {N} CRITICAL, {N} HIGH

- **Option B (Alternative):** Implement compensating control
  - Control: {Description of control, e.g., "Dual approval for invoices >$10K"}
  - Implementation time: {timeframe}
  - Ongoing monitoring required: {frequency}
  - Approval required from: {role/person}

**Business Justification:**
{Why this user needs/doesn't need these permissions}

**Assigned To:** {Manager Name}
**Target Date:** {YYYY-MM-DD}
**Follow-Up:** {Date for verification}

---

#### 2. {User Name} - {Primary Conflict}
{Repeat structure above}

---

### Short-Term Actions (Complete by: {Date, +30 days})

{Similar structure for Priority 2 users, condensed}

---

### Long-Term Actions (Complete by: {Date, +90 days})

- **Quarterly Access Review:** Schedule recurring review for this scope
- **Policy Updates:** {Any policy changes needed based on patterns}
- **Role Redesign:** {If systematic issues identified}
- **Training:** {If user education needed}
```

---

## Risk Assessment

```
### Overall Risk Level: {CRITICAL / HIGH / MEDIUM / LOW}

**Risk Factors:**
- [ ] Number of CRITICAL violations: {N} ({status})
- [ ] Percentage of users with violations: {pct}% ({status})
- [ ] Executive-level users affected: {Yes/No}
- [ ] Payment processing conflicts: {count} ({status})
- [ ] Financial reporting conflicts: {count} ({status})
- [ ] Systematic issues identified: {Yes/No}

**Risk Score:** {calculated score, e.g., 8.5/10}

**Risk Trend:** {Increasing / Stable / Decreasing}
{Include comparison to previous review if available}

### Audit Exposure

**If audited today:**
- [ ] CRITICAL violations would be audit findings: {Yes/No}
- [ ] Documentation sufficient: {Yes/No}
- [ ] Compensating controls in place: {Yes/No}
- [ ] Management awareness documented: {Yes/No}

**Audit Readiness:** {Ready / Needs Work / Not Ready}
```

---

## Implementation Plan

```
### Timeline

**Week 1 ({Date} - {Date}):**
- [ ] Review findings with {Department Head / Role Owner}
- [ ] Obtain approval for remediation actions
- [ ] Communicate with affected users (Priority 1)
- [ ] Begin role removals for Priority 1 users

**Week 2-4 ({Date} - {Date}):**
- [ ] Complete Priority 1 remediation
- [ ] Verify violation resolution
- [ ] Begin Priority 2 remediation
- [ ] Document exceptions as needed

**Month 2-3 ({Date} - {Date}):**
- [ ] Complete Priority 2 remediation
- [ ] Address Priority 3 users
- [ ] Implement organization-wide recommendations
- [ ] Update policies/procedures

**Ongoing:**
- [ ] Monthly check-ins on remediation progress
- [ ] Quarterly access reviews
- [ ] Annual comprehensive audit

### Resource Requirements

**Time Investment:**
- Remediation implementation: {X hours}
- Management approvals: {X hours}
- User communication: {X hours}
- Follow-up verification: {X hours}
- **Total:** {X hours}

**Approvals Needed:**
- [ ] {Role/Person} - Priority 1 remediations
- [ ] {Role/Person} - Policy changes
- [ ] {Role/Person} - Budget (if compensating controls have cost)

### Success Metrics

Track these metrics over 90 days:

| Metric | Baseline | Target | Actual |
|--------|----------|--------|--------|
| CRITICAL violations | {N} | 0 | {TBD} |
| HIGH violations | {N} | <{target} | {TBD} |
| Users with violations | {N} ({pct}%) | <{target}% | {TBD} |
| Remediation completion | 0% | 100% | {TBD}% |
| Re-occurrence rate | N/A | <5% | {TBD}% |
```

---

## Appendices

```
### Appendix A: SOD Rules Applied

This review applied the following SOD rules:

| Rule Code | Rule Name | Severity | Description |
|-----------|-----------|----------|-------------|
| {CODE}    | {Name}    | CRITICAL | {Description} |
| {CODE}    | {Name}    | HIGH     | {Description} |
| ...       | ...       | ...      | ... |

Total Rules: {N} CRITICAL, {N} HIGH, {N} MEDIUM, {N} LOW

### Appendix B: Methodology

**Data Source:** {NetSuite / Okta / Salesforce}
**Data Date:** {YYYY-MM-DD HH:MM}
**Analysis Tool:** Compliance Agent - SOD Access Review Skill
**Analyst:** {Name/Role}

**Scope Definition:**
{How scope was determined}

**Data Collection:**
{Tools used, filters applied}

**Analysis Approach:**
{Prioritization logic, thresholds used}

### Appendix C: Definitions

**Segregation of Duties (SOD):** Security principle that no single person should have permissions enabling fraud

**CRITICAL Violation:** SOD conflict that directly enables fraud or material error

**HIGH Violation:** Significant SOD conflict requiring timely remediation

**MEDIUM Violation:** Moderate SOD conflict, address in normal course

**LOW Violation:** Minor overlap, monitor only

**Compensating Control:** Process/procedure that mitigates risk when role separation not feasible

### Appendix D: Contact Information

**Questions about this review:**
- Compliance Team: {email}
- SOD Specialist: {name, email}

**Questions about remediation:**
- IT Access Management: {email}
- {Department} Manager: {name, email}

**Questions about exceptions:**
- Compliance Officer: {name, email}
- CFO: {name, email} (for executive-level exceptions)
```

---

## Sign-Off

```
### Review Completed By

**Analyst:**
- Name: {Name}
- Role: {Role}
- Date: {YYYY-MM-DD}
- Signature: ________________

### Approval

**Reviewed and Approved By:**

**Department Head:**
- Name: {Name}
- Role: {Role}
- Date: {YYYY-MM-DD}
- Signature: ________________

**Compliance Officer:**
- Name: {Name}
- Role: {Role}
- Date: {YYYY-MM-DD}
- Signature: ________________

**Next Review Date:** {YYYY-MM-DD} (quarterly)
```

---

## Usage Instructions

### How to Use This Template

1. **Copy this template** for each access review
2. **Fill in all {placeholders}** with actual data
3. **Delete unused sections** if not applicable
4. **Customize recommendations** based on specific context
5. **Save with naming convention:** `SOD_Review_{Scope}_{YYYYMMDD}.md`

### Export Options

**For Stakeholders:**
- PDF: Best for executive distribution
- Excel: Best for tracking remediation
- Markdown: Best for version control

**For Audit:**
- Include Appendices A-D
- Attach raw data export
- Document all approvals

---

**Template Version:** 1.0.0
**Last Updated:** 2026-02-14
**Related Skill:** sod-access-review
