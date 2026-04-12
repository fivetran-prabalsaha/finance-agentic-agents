# SOD Access Review Skill - Quick Start Guide

**Get started with guided compliance reviews in 5 minutes**

---

## What You'll Learn

By the end of this guide, you'll know how to:
1. Install the SOD Access Review skill
2. Run your first access review
3. Interpret the results
4. Take action on findings

**Time Required:** 5-10 minutes

---

## Step 1: Install the Skill (2 minutes)

### Option A: Claude.ai (Web)

1. **Download the skill:**
```bash
cd compliance-agent/skills
zip -r sod-access-review.zip sod-access-review/
```

2. **Upload to Claude:**
- Open https://claude.ai
- Go to Settings > Capabilities > Skills
- Click "Upload skill"
- Select `sod-access-review.zip`
- Toggle skill ON

3. **Verify installation:**
- Ask Claude: "What skills do I have?"
- Should see "sod-access-review" in the list

### Option B: Claude Code (CLI)

**Skills are automatically available** - no installation needed!

The skill is already in `compliance-agent/skills/sod-access-review/`

---

## Step 2: Run Your First Review (3 minutes)

### Try These Queries:

#### 📊 Department Review
```
"Review Finance department access"
```

**What happens:**
1. Skill activates automatically
2. Lists all Finance users
3. Analyzes violations
4. Generates executive summary
5. Provides remediation recommendations

**Expected output:**
```
🔍 SOD ACCESS REVIEW: Finance Department

📊 Summary Statistics
- Total Users: 76
- Users with Violations: 45 (59%)
- CRITICAL: 156 violations

⚠️ Top 5 Users Requiring Action
[Table with robin.turner@fivetran.com at top]

📋 Next Steps
1. Review Robin Turner's role combination...
```

---

#### 🎭 Role Review
```
"Audit all users with Controller role"
```

**What happens:**
- Lists users with Controller role
- Identifies common patterns across Controllers
- Highlights systematic issues

---

#### 👤 Individual Review
```
"Check if robin.turner@fivetran.com has any SOD issues"
```

**What happens:**
- Analyzes specific user
- Shows detailed violation breakdown
- Provides specific remediation options

---

## Step 3: Interpret Results (2 minutes)

### Understanding the Output

#### Summary Statistics Table
```
| Metric | Value | What It Means |
|--------|-------|---------------|
| Total Users | 76 | Scope of review |
| Users with Violations | 45 (59%) | 59% have at least 1 violation |
| CRITICAL | 156 | Immediate fraud risk |
| HIGH | 203 | Address within 30 days |
| MEDIUM | 287 | Address within 90 days |
```

#### Priority Levels

**🔴 CRITICAL = This Week**
- Direct fraud risk (AP Entry + Approval)
- Immediate remediation required
- Executive attention needed

**🟠 HIGH = This Month**
- Significant risk
- Remediate within 30 days
- Manager approval required

**🟡 MEDIUM = This Quarter**
- Moderate risk
- Address in normal course
- Document compensating controls

**🟢 LOW = Monitor**
- Minor overlap
- Annual review sufficient
- No immediate action

#### Top Violators Table
```
| Rank | User | CRIT | HIGH | Total |
|------|------|------|------|-------|
| 1    | Robin Turner | 96 | 128 | 384 |
```

**What this means:**
- Robin has 96 CRITICAL violations
- Highest priority for remediation
- Likely has Controller + AP Clerk roles

---

## Step 4: Take Action (5 minutes)

### Immediate Actions

Based on skill recommendations:

#### 1. Review Top Violator

Skill says:
```
Robin Turner (robin.turner@fivetran.com)
- Issue: AP Entry + Approval conflict
- Recommendation: Remove "AP Clerk" role
```

**Next step:**
```
"Create remediation plan for robin.turner@fivetran.com"
```

This activates the **SOD Violation Remediation** skill (coming in Phase 7b)

---

#### 2. Generate Report for Distribution

```
"Generate Excel report for Finance department violations"
```

or

```
generate_violation_report(
    user_email="robin.turner@fivetran.com",
    format="excel",
    export_path="/tmp/robin_violations.xlsx"
)
```

**Output:** Excel file with:
- All violations color-coded
- Metadata sheet with summary
- Ready to share with stakeholders

---

#### 3. Schedule Recurring Review

```
"Schedule quarterly Finance department review"
```

or

```
schedule_review(
    system_name="netsuite",
    frequency="quarterly"
)
```

---

## Common Scenarios

### Scenario 1: Compliance Audit Preparation

**Goal:** Prepare for external audit next month

**Query:**
```
"Review Finance and Accounting departments for SOD violations"
```

**Actions:**
1. Skill runs comprehensive review
2. Generate Excel report for auditors
3. Document remediation plan for findings
4. Schedule follow-up in 2 weeks to verify fixes

**Expected time:** 15 minutes

---

### Scenario 2: New Employee Onboarding

**Goal:** Verify new Controller's access is appropriate

**Query:**
```
"Check access for jane.smith@fivetran.com"
```

**Actions:**
1. Skill analyzes individual user
2. Reviews violation report
3. If violations found, adjust roles before first day
4. Document approved exceptions if needed

**Expected time:** 5 minutes

---

### Scenario 3: Quarterly Access Certification

**Goal:** Certify all Controller role assignments

**Query:**
```
"Audit all users with Controller role"
```

**Actions:**
1. Skill identifies all Controllers (12 users)
2. Highlights common patterns
3. Generate certification report
4. Managers approve or flag for change

**Expected time:** 10 minutes per quarter

---

## Troubleshooting

### Issue: Skill doesn't activate

**You say:** "Review Finance department"
**Claude responds:** "Let me use list_all_users..." (manual tool calls)

**Fix:**
1. Verify skill is enabled (Settings > Skills)
2. Be more specific: "Review Finance department access for SOD violations"
3. Restart Claude.ai browser tab

---

### Issue: No users found

**Error:** "No users found in Finance department"

**Fix:**
- Department names are hierarchical
- Try "Finance" instead of "Fivetran : G&A : Finance"
- Or ask: "List all departments in NetSuite"

---

### Issue: User shows 0 violations

**Output:** "Robin Turner: 0 violations"

**Fix:**
1. Check sync status: "What's the status of data collection?"
2. If stale: "Trigger manual sync"
3. Wait 2-3 minutes, try again

---

## Next Steps

### After Your First Review

1. **Explore other workflows:**
   - Try role reviews: "Audit Administrator role"
   - Try individual reviews: "Check [user]@[domain].com"

2. **Generate reports:**
   - Excel: "Export violations to Excel"
   - PDF: "Generate PDF report for [user]"

3. **Schedule recurring reviews:**
   - "Schedule monthly Finance review"
   - "Set up quarterly Controller audit"

4. **Learn remediation:**
   - See `../sod-violation-remediation/` (coming in Phase 7b)

### Learn More

- **Full Documentation:** See `SKILL.md` in this directory
- **Detailed Checklist:** See `references/review-checklist.md`
- **Report Template:** See `assets/report-template.md`
- **All Skills:** See `../README.md`

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│           SOD Access Review Quick Reference             │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Department Review:                                      │
│    "Review [Department] department"                      │
│    → 76 users, 10-15 min                                │
│                                                          │
│  Role Review:                                            │
│    "Audit [Role] role"                                   │
│    → 12 users, 5-10 min                                 │
│                                                          │
│  Individual Review:                                      │
│    "Check [email] for SOD issues"                        │
│    → 1 user, 2-3 min                                    │
│                                                          │
│  Generate Report:                                        │
│    "Export violations to Excel"                          │
│                                                          │
│  Schedule Review:                                        │
│    "Schedule quarterly [scope] review"                   │
│                                                          │
├─────────────────────────────────────────────────────────┤
│  Priority Levels:                                        │
│    🔴 CRITICAL  → This week                             │
│    🟠 HIGH      → This month                            │
│    🟡 MEDIUM    → This quarter                          │
│    🟢 LOW       → Annual review                         │
└─────────────────────────────────────────────────────────┘
```

---

## Success Checklist

After completing this guide, you should be able to:

- [ ] Install the SOD Access Review skill
- [ ] Run a department review successfully
- [ ] Interpret violation counts and priorities
- [ ] Understand what CRITICAL/HIGH/MEDIUM mean
- [ ] Know how to generate Excel reports
- [ ] Know where to find detailed documentation

**Time Invested:** 5-10 minutes
**Value Delivered:** 67% faster compliance reviews, consistent methodology

---

## Support

**Questions?**
- Full Skill Documentation: `SKILL.md`
- Skills Overview: `../README.md`
- GitHub Issues: https://github.com/[your-repo]/issues

**Feedback?**
Let us know how we can improve this skill!

---

**Version:** 1.0.0
**Last Updated:** 2026-02-14
**Skill:** sod-access-review
