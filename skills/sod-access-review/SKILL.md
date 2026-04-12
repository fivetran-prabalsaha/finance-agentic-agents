---
name: sod-access-review
description: Performs systematic SOD user access reviews for departments, roles, or individuals. Use when user asks to 'review access', 'audit users', 'check Finance department', 'analyze Controller role', 'review [person]'s access', or 'compliance review for [group]'. Provides step-by-step guidance through data collection, violation analysis, risk prioritization, and reporting with actionable recommendations.
license: MIT
metadata:
  author: Prabal Saha
  version: 1.0.0
  mcp-server: compliance-system
  category: compliance-workflow
  use-case: workflow-automation
---

# SOD Access Review Skill

Systematic Segregation of Duties (SOD) access review workflow for departments, roles, and individual users.

---

## Instructions

### Step 1: Scope Definition

Ask user to specify the review scope:

**Option A: Department Review**
- Example: "Finance", "Accounting", "Operations"
- Use for: Reviewing all users in a business unit

**Option B: Role Review**
- Example: "Controller", "Administrator", "AP Clerk"
- Use for: Reviewing all users assigned a specific role

**Option C: Individual User Review**
- Example: "robin.turner@fivetran.com"
- Use for: Focused analysis on one person

If user's request is ambiguous, suggest the most appropriate scope based on context.

---

### Step 2: Data Collection

Based on scope, call appropriate MCP tools:

#### For Department Reviews:
```
list_all_users(
    system_name="netsuite",
    filter_by_department="{user_provided_department}",
    include_inactive=false,
    limit=100
)
```

**Note:** Department matching is hierarchical - "Finance" will match "Fivetran : G&A : Finance"

#### For Role Reviews:
```
list_all_users(
    system_name="netsuite",
    limit=500
)
```
Then filter results to users with the specified role.

**Alternative:** If analyze_role_permissions tool exists, use it first to understand the role's inherent risks.

#### For Individual User Reviews:
```
get_user_violations(
    system_name="netsuite",
    user_identifier="{email_address}",
    format="table"
)
```

**Collect:**
- Total users in scope
- Active vs inactive status
- Roles assigned per user
- Initial violation counts

---

### Step 3: Violation Analysis

For each user in scope (or top N by violation count):

1. **Get Detailed Violations:**
```
get_user_violations(
    system_name="netsuite",
    user_identifier="{email}",
    format="table",
    include_ai_analysis=true
)
```

2. **Track Key Metrics:**
- Total violations per user
- CRITICAL severity count (highest priority)
- HIGH severity count (next priority)
- MEDIUM severity count
- Common violation patterns across users

3. **Prioritize Users:**
Sort by:
1. CRITICAL violations (descending)
2. HIGH violations (descending)
3. Total violation count (descending)

**Optimization:** For large departments (>50 users), analyze only top 20 users by violation count to avoid overwhelming output.

---

### Step 4: Risk Prioritization

Identify users requiring immediate action:

**Priority 1 - Critical (This Week):**
- Users with >10 CRITICAL violations
- Users with AP Entry + AP Approval conflicts
- Users with Journal Entry + Journal Approval conflicts
- Users with Admin + Regular user role combinations

**Priority 2 - High (This Month):**
- Users with >20 HIGH violations
- Users with payment processing + payment approval
- Users with vendor master + invoice processing

**Priority 3 - Medium (This Quarter):**
- Users with >50 MEDIUM violations
- Other SOD conflicts requiring attention

Present top 5-10 users requiring immediate action.

---

### Step 5: Executive Summary Report

Generate comprehensive summary:

#### A. Overview Section
```
🔍 SOD ACCESS REVIEW: {Scope Name}

📅 Review Date: {current date}
🎯 Scope: {Department/Role/User}
📊 Coverage: {X users analyzed}
```

#### B. Summary Statistics Table
```
| Metric | Value |
|--------|-------|
| Total Users | {count} |
| Users with Violations | {count} ({percentage}%) |
| 🔴 CRITICAL Violations | {count} |
| 🟠 HIGH Violations | {count} |
| 🟡 MEDIUM Violations | {count} |
| Avg Violations/User | {average} |
```

#### C. Top Violators Table
```
| Rank | User | Email | CRITICAL | HIGH | MEDIUM | Total | Primary Risk |
|------|------|-------|----------|------|--------|-------|--------------|
| 1 | {name} | {email} | {count} | {count} | {count} | {total} | {conflict type} |
| 2 | ... | ... | ... | ... | ... | ... | ... |
| ... | ... | ... | ... | ... | ... | ... | ... |
```

#### D. Common Violation Patterns
Identify patterns appearing across multiple users:
- Most frequent conflict type
- Most common problematic role combination
- Departments/roles at highest risk

---

### Step 6: Remediation Recommendations

For each high-priority user, provide specific actions:

#### Immediate Actions (This Week):
1. **User: {name}**
   - **Issue:** {specific conflict, e.g., "AP Entry + Approval"}
   - **Current Roles:** {list of roles}
   - **Recommendation:** Remove "{role name}" OR implement compensating control
   - **Impact:** User loses {permissions list}
   - **Alternative:** Assign "{alternative role}" for needed access

2. **User: {name}**
   ...

#### Short-Term Actions (This Month):
- Complete review of top 5 users
- Generate formal remediation plans
- Schedule follow-up verification audit

#### Long-Term Actions (This Quarter):
- Quarterly access review for this scope
- Update SOD policy documentation
- Training for managers on SOD principles

---

### Step 7: Next Steps Prompt

Always end with actionable next steps:

```
📋 **NEXT STEPS**

Would you like me to:
1. 📊 Generate detailed Excel report for distribution?
   Use: generate_violation_report(user_email="...", format="excel")

2. 🔧 Create remediation plan for specific user?
   Use SOD Violation Remediation skill

3. 📅 Schedule recurring review?
   Use: schedule_review(system_name="netsuite", frequency="quarterly")

4. 🔍 Deep-dive into specific violation?
   Use: get_user_violations(user_identifier="...", format="detailed")
```

---

## Examples

### Example 1: Department Review

**User Query:** "Review Finance department access"

**Skill Actions:**

1. **Scope:** Department = Finance

2. **Data Collection:**
```
list_all_users(system_name="netsuite", filter_by_department="Finance", limit=100)
→ Found 76 active users
```

3. **Violation Analysis:**
Top 20 users analyzed:
- 45 users have violations (59%)
- 156 CRITICAL, 203 HIGH, 287 MEDIUM violations total

4. **Risk Prioritization:**
- Priority 1: 8 users require immediate action
- Top violator: robin.turner@fivetran.com (96 CRITICAL, 128 HIGH)

5. **Executive Summary:**
```
🔍 SOD ACCESS REVIEW: Finance Department

📅 Review Date: 2026-02-14
🎯 Scope: Finance Department
📊 Coverage: 76 users analyzed

| Metric | Value |
|--------|-------|
| Total Users | 76 |
| Users with Violations | 45 (59%) |
| 🔴 CRITICAL | 156 |
| 🟠 HIGH | 203 |
| 🟡 MEDIUM | 287 |
| Avg Violations/User | 8.5 |

⚠️ TOP 5 USERS REQUIRING ACTION

| Rank | User | CRITICAL | HIGH | MEDIUM | Total | Primary Risk |
|------|------|----------|------|--------|-------|--------------|
| 1 | Robin Turner | 96 | 128 | 160 | 384 | AP Entry + Approval |
| 2 | Jane Smith | 42 | 67 | 89 | 198 | Journal Entry + Approval |
| 3 | ... | ... | ... | ... | ... | ... |

🎯 COMMON PATTERNS
- 12 users have AP Entry + Approval conflict
- 8 users have Controller + AP Clerk role combination
- Finance department has 3x higher violation rate than company average
```

6. **Recommendations:**
```
📋 IMMEDIATE ACTIONS (This Week)

1. **Robin Turner** (robin.turner@fivetran.com)
   - Issue: Has both AP Entry and AP Approval permissions
   - Current Roles: Controller, AP Clerk, Administrator
   - Recommendation: Remove "AP Clerk" role (Controller covers needed permissions)
   - Alternative: Implement dual-approval control for invoices >$10K

2. **Jane Smith** (jane.smith@fivetran.com)
   - Issue: Journal Entry + Journal Approval conflict
   ...
```

**Result:** Complete department review in 5 minutes, comprehensive findings, prioritized action plan.

---

### Example 2: Role Review

**User Query:** "Audit all users with Controller role"

**Skill Actions:**

1. **Scope:** Role = Controller

2. **Data Collection:**
```
list_all_users(system_name="netsuite", limit=500)
→ Filter to users with "Controller" role
→ Found 12 users with Controller role
```

3. **Violation Analysis:**
All 12 users analyzed:
- 10 users have violations (83%)
- Controller role inherently has high permission overlap

4. **Executive Summary:**
```
🔍 SOD ACCESS REVIEW: Controller Role

📅 Review Date: 2026-02-14
🎯 Scope: Users with Controller role
📊 Coverage: 12 users analyzed

| Metric | Value |
|--------|-------|
| Total Users | 12 |
| Users with Violations | 10 (83%) |
| 🔴 CRITICAL | 48 |
| 🟠 HIGH | 92 |
| 🟡 MEDIUM | 145 |

🎯 KEY FINDINGS
- Controller role has inherent SOD conflicts when combined with:
  - AP Clerk (6 users affected)
  - Administrator (4 users affected)
  - Journal Manager (3 users affected)
```

5. **Recommendations:**
```
📋 RECOMMENDATIONS

Short-term:
- Remove AP Clerk role from Controllers (redundant permissions)
- Implement compensating control: Dual approval for journals >$50K

Long-term:
- Consider creating "Controller - Limited" custom role
- Document approved exceptions for Controllers requiring additional access
```

**Result:** Role-specific review highlighting systematic issues, organization-wide recommendations.

---

### Example 3: Individual User Review

**User Query:** "Check if robin.turner@fivetran.com has any SOD issues"

**Skill Actions:**

1. **Scope:** User = robin.turner@fivetran.com

2. **Data Collection:**
```
get_user_violations(
    system_name="netsuite",
    user_identifier="robin.turner@fivetran.com",
    format="table"
)
→ 384 total violations (96 CRITICAL, 128 HIGH, 160 MEDIUM)
```

3. **Analysis:**
```
🔍 SOD ANALYSIS: Robin Turner

📧 Email: robin.turner@fivetran.com
🏢 Department: Fivetran : G&A : Finance
🎭 Roles: 3 roles assigned

| Severity | Count |
|----------|-------|
| 🔴 CRITICAL | 96 |
| 🟠 HIGH | 128 |
| 🟡 MEDIUM | 160 |
| **Total** | **384** |

⚠️ TOP 3 CRITICAL CONFLICTS

| # | Violation | Conflicting Roles | Risk |
|---|-----------|-------------------|------|
| 1 | AP Entry + Approval | Controller + AP Clerk | Can create & approve invoices |
| 2 | Journal Entry + Approval | Controller + Administrator | Can manipulate financial records |
| 3 | Vendor Master + Invoice Processing | Controller + AP Clerk | Can create fake vendors & pay self |
```

4. **Recommendations:**
```
🔧 RECOMMENDED REMEDIATION

Option A: Remove AP Clerk Role
- Impact: Removes 96 CRITICAL violations
- User retains: Controller permissions (sufficient for job)
- Implementation: 5 minutes in NetSuite

Option B: Implement Compensating Controls
- Keep current roles
- Add control: Dual approval for invoices >$10K
- Add control: Quarterly manager review of AP activity
- Review frequency: Quarterly

Option C: Request Exception Approval
- Business justification required
- Approvals needed: CFO + Compliance Officer
- Review frequency: Quarterly
```

5. **Next Steps:**
```
📋 NEXT STEPS

To remediate:
- Use SOD Violation Remediation skill
- Creates formal remediation plan with audit trail

To export:
- generate_violation_report(user_email="robin.turner@fivetran.com", format="excel")
```

**Result:** Focused individual analysis with specific remediation options, ready for implementation.

---

## Troubleshooting

### Issue: Department filter returns 0 users

**Symptoms:** "No users found in [department]" despite knowing users exist

**Root Cause:** Department names are hierarchical (e.g., "Fivetran : G&A : Finance")

**Solution:**
1. Try partial name: "Finance" instead of full path
2. Tool uses partial matching - "Finance" will match "Fivetran : G&A : Finance"
3. If still not working, use `list_all_users` without filter and inspect actual department names

---

### Issue: User shows 0 violations but should have some

**Symptoms:** User is known to have conflicts but tool returns 0

**Root Cause:** Data sync may not have completed, or user was recently modified

**Solution:**
1. Check sync status: `get_collection_agent_status()`
2. If sync is stale, trigger manual sync: `trigger_manual_sync(sync_type="incremental")`
3. Wait 2-3 minutes for sync to complete
4. Re-query user violations

---

### Issue: Too many users to analyze (>100)

**Symptoms:** Department has 200+ users, output is overwhelming

**Solution:**
1. **Focus on high-risk users:** Analyze only users with >10 violations
2. **Batch approach:** Review top 20 first, then next 20, etc.
3. **Use Excel export:** Generate full report, analyze in spreadsheet
4. **Consider role-based review:** Instead of department, review specific high-risk roles

---

### Issue: Unclear which violation to prioritize

**Symptoms:** User has 50+ violations, unsure where to start

**Solution:**
1. **Always prioritize CRITICAL first:** These are direct fraud risks
2. **Focus on AP conflicts:** AP Entry + Approval is highest business risk
3. **Look for role removals:** Easier than compensating controls
4. **Check job title:** Does user actually need all assigned roles?

---

### Issue: Recommendations too generic

**Symptoms:** "Remove role" without specific guidance

**Solution:**
1. **Use detailed format:** `get_user_violations(format="detailed")` for more context
2. **Check role analysis:** `analyze_role_permissions(role_name="...")` to understand what role provides
3. **Query knowledge base:** `query_knowledge_base(query="remediation strategies for AP conflicts")`
4. **Find similar exceptions:** `find_similar_exceptions(role_names=[...])` to see what others have done

---

## Best Practices

### Before Starting Review

✅ **Verify data is current**
- Check sync status: `get_collection_agent_status()`
- Last sync should be <24 hours old
- If stale, trigger manual sync first

✅ **Understand the scope**
- Department review: Broad, for compliance audits
- Role review: Targeted, for role redesign
- Individual review: Focused, for remediation

✅ **Set expectations**
- Department (50+ users): 10-15 minutes
- Role (10-30 users): 5-10 minutes
- Individual: 2-3 minutes

### During Review

✅ **Always use table format first**
- Quick overview without overwhelming detail
- Identify top violators efficiently
- Switch to detailed format only for deep-dives

✅ **Focus on CRITICAL violations**
- These are direct fraud risks
- Must be addressed immediately
- MEDIUM/LOW can wait for quarterly review

✅ **Look for patterns**
- Same conflict across multiple users = systemic issue
- May need organization-wide policy change
- Document common patterns in summary

✅ **Consider business context**
- Some roles require exceptions (e.g., Controller)
- Compensating controls may be more practical than role removal
- Always check if similar exceptions exist

### After Review

✅ **Document findings**
- Generate Excel report for audit trail
- Save executive summary for stakeholders
- Track remediation progress

✅ **Schedule follow-ups**
- Critical violations: Weekly check-ins
- High violations: Monthly reviews
- Department reviews: Quarterly schedule

✅ **Communicate clearly**
- Executives want: Risk summary + remediation timeline
- Managers want: Specific users + action items
- Users want: Why it matters + minimal disruption

✅ **Track metrics**
- Violation reduction over time
- Time to remediate (goal: <30 days for CRITICAL)
- Exception approval rate
- Re-occurrence rate

---

## Performance Tips

### For Large Departments (>100 users)

1. **Batch processing:** Review top 20, then next 20
2. **Filter early:** Use `filter_by_department` instead of querying all users
3. **Limit detail:** Use table format, not detailed
4. **Export to Excel:** Better for large datasets than screen output

### For Frequent Reviews

1. **Cache results:** Don't re-query unchanged users
2. **Focus on deltas:** Review only users modified since last review
3. **Use scheduled reviews:** `schedule_review()` for automated quarterly reviews
4. **Track completion:** Mark reviewed users to avoid duplicates

### For Executive Summaries

1. **Top 10 only:** Executives don't need all 100 users
2. **Visual formatting:** Tables > bullet points
3. **Clear priorities:** CRITICAL vs HIGH vs MEDIUM
4. **Actionable recommendations:** "Remove AP Clerk role" not "Fix violations"

---

## Integration with Other Skills

### Chain with Remediation Skill

After identifying violators:
```
Use: sod-violation-remediation skill
Input: Specific user + violation from this review
Output: Formal remediation plan with audit trail
```

### Chain with Demo Manager Skill

Before external demo:
```
Use: demo-data-manager skill
Input: Source user from this review (e.g., high violator)
Output: Sanitized demo user for presentation
```

### Combine with Exception Management

For users requiring exceptions:
```
1. Find similar: find_similar_exceptions(role_names=[...])
2. Review precedent: Check what controls worked
3. Record new: record_exception_approval(...)
```

---

## Reference Documents

For detailed methodology, see:
- `references/review-checklist.md` - Step-by-step checklist
- `assets/report-template.md` - Executive summary template
- `docs/MCP_SOD_TOOLS.md` - All 34 available MCP tools
- `docs/LESSONS_LEARNED.md` - Issues #20 & #21 (department filtering, violation counts)

---

## Skill Metadata

**Created:** 2026-02-14
**Last Updated:** 2026-02-14
**Version:** 1.0.0
**Author:** Prabal Saha
**MCP Server:** compliance-system
**Category:** Workflow Automation
**Estimated Time:** 5-15 minutes per review
**Success Rate:** >90% on test queries

---

**Questions or Issues?**
- See `skills/README.md` for general skills guidance
- See `docs/SKILLS_BEST_PRACTICES_REVIEW.md` for design rationale
- Open GitHub issue for bugs or feature requests
