# Knowledge Base Guardrails for Role Recommendations

**Version:** 1.0
**Last Updated:** 2026-02-12
**Purpose:** Prevent hallucination and ensure database-first approach for role assignments

---

## CRITICAL RULES - ALWAYS FOLLOW

### Rule 1: Database is Ground Truth

**ALWAYS** use database tools to get role information. **NEVER** assume, guess, or make up role assignments.

✅ **CORRECT:**
```
User asks: "What roles should Revenue Director have?"
1. Call: recommend_roles_for_job_title("Revenue Director")
2. Get actual roles from database (e.g., Erin MacLean's roles)
3. Show those specific roles
4. Check for SOD conflicts with analyze_access_request
5. Present findings with conflict warnings
```

❌ **INCORRECT:**
```
User asks: "What roles should Revenue Director have?"
Response: "Revenue Directors typically have Revenue Manager,
Revenue Approver, and Controller roles..."
[This is hallucination - Controller may not be in actual peer data]
```

### Rule 2: Never Infer from Job Title Alone

Do NOT make assumptions about roles based on job title semantics.

❌ **Wrong:** "Since they're a Revenue Director, they need Revenue Manager + Controller"
✅ **Right:** "Let me check what existing Revenue Directors have: [calls database tool]"

### Rule 3: Always Check for Conflicts

Even if peers have certain roles, those roles may have SOD conflicts.

**Required workflow:**
1. Get peer roles (recommend_roles_for_job_title)
2. Analyze conflicts (analyze_access_request)
3. Present both: "Peers have X, Y, Z BUT they have N conflicts"

### Rule 4: Distinguish Ground Truth from Examples

**Ground Truth (Database):**
- Actual role assignments (from users table + user_roles)
- Actual SOD conflicts (from analysis tools)
- Actual permission levels (from roles table)
- Job role mappings (from job_role_mappings table)

**Examples/Documentation (NOT Ground Truth):**
- Generic role descriptions in markdown files
- Example configurations in docs
- Historical recommendations in knowledge base

**When in doubt:** Query the database, don't rely on documentation.

---

## Available Tools for Ground Truth

### Primary Tools (Always Use These First)

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `recommend_roles_for_job_title` | Find what peers with similar job titles have | "What roles should [job title] have?" |
| `analyze_access_request` | Check SOD conflicts in role combination | After getting peer roles, before recommending |
| `list_all_users` | Find users by job title/department | "Who are our Revenue Directors?" |
| `get_user_violations` | Check specific user's violations | "Does [person] have violations?" |

### Secondary Tools (For Detailed Analysis)

| Tool | Purpose |
|------|---------|
| `validate_job_role` | Check if role combo is acceptable for job title |
| `check_permission_conflict` | Check specific permission conflicts |
| `get_compensating_controls` | Get controls for specific risk level |
| `query_knowledge_base` | Search documentation (use AFTER database tools) |

---

## Workflow Examples

### Example 1: New Revenue Director Onboarding

**User asks:** "What roles should we assign to a new Revenue Director?"

**CORRECT workflow:**
```
Step 1: Check database for existing Revenue Directors
Tool: recommend_roles_for_job_title("Revenue Director")
Result: 5 peers found, Erin MacLean has:
  - Fivetran - Revenue Manager
  - Fivetran - Revenue Approver
  - Fivetran - Dunning Director

Step 2: Check if these roles have conflicts
Tool: analyze_access_request(
  job_title="Revenue Director",
  requested_roles=["Fivetran - Revenue Manager",
                   "Fivetran - Revenue Approver",
                   "Fivetran - Dunning Director"]
)
Result: 102 SOD conflicts detected (HIGH risk)

Step 3: Present findings
Response: "Based on existing Revenue Directors (Erin MacLean),
typical roles are Revenue Manager + Revenue Approver + Dunning Director.
However, these roles have 102 SOD conflicts (HIGH risk).
Recommend implementing compensating controls:
[list controls from analysis]"
```

**INCORRECT workflow:**
```
Response: "Revenue Directors typically need Revenue Manager,
Revenue Approver, and Controller roles..."
[No database check - hallucinated Controller role]
```

### Example 2: Validating Existing Assignment

**User asks:** "Does Erin MacLean have the right roles?"

**CORRECT workflow:**
```
Step 1: Get Erin's actual roles
Tool: get_user_violations(system="netsuite", email="erin.maclean@fivetran.com")
Result: Has 3 roles, 0 violations recorded

Step 2: Validate against job title
Tool: validate_job_role(job_title="Director, Revenue Accounting & Operations")
Result: Check if role combo is acceptable

Step 3: Present with context
Response: "Erin has [list actual roles]. No violations currently recorded.
However, recommend periodic review..."
```

---

## Common Pitfalls to Avoid

### Pitfall 1: Knowledge Base as Source of Truth

❌ **Wrong:** "According to our documentation, Revenue Directors have..."
✅ **Right:** "Checking database... Revenue Directors in your organization have..."

### Pitfall 2: Generic Industry Standards

❌ **Wrong:** "Industry best practice is to separate revenue creation from approval..."
✅ **Right:** "Your existing Revenue Directors have both Manager and Approver roles, which creates 102 conflicts..."

### Pitfall 3: Assuming Peer Roles are Correct

❌ **Wrong:** "Erin has these roles, so assign the same to the new hire"
✅ **Right:** "Erin has these roles, BUT they have 102 conflicts. Recommend with compensating controls..."

### Pitfall 4: Not Checking Conflicts

❌ **Wrong:** "Recommend Revenue Manager + Revenue Approver"
✅ **Right:** "Recommend Revenue Manager + Revenue Approver (47 conflicts, needs dual approval workflow)"

---

## Response Templates

### Template 1: Role Recommendation with Conflicts

```
Based on database analysis:

**Current Practice:**
• 5 employees with "Revenue Director" title
• Example: Erin MacLean has:
  - Fivetran - Revenue Manager
  - Fivetran - Revenue Approver
  - Fivetran - Dunning Director

**SOD Conflict Analysis:**
• 102 conflicts detected (HIGH risk)
• Key issues: Maker-checker violations in revenue transactions

**Recommendation:**
Assign these roles WITH compensating controls:
[list specific controls from analyze_access_request]

NOT recommended without controls.
```

### Template 2: No Peers Found

```
Based on database analysis:

**Current Practice:**
• No existing employees found with similar job title
• Cannot base recommendation on peer analysis

**Recommendation:**
1. Define required responsibilities for this role
2. Use analyze_access_request to test role combinations
3. Choose minimal necessary permissions
4. Implement compensating controls for any conflicts
```

### Template 3: Peers Have No Roles

```
Based on database analysis:

**Current Practice:**
• 3 employees with "Revenue Director" title
• None have NetSuite roles assigned yet

**Recommendation:**
Cannot base recommendation on peers (they have no roles).
Suggest starting with minimal permissions:
1. Revenue Manager only (start here)
2. Add Revenue Approver if needed (check conflicts)
3. Validate after 30-day trial period
```

---

## Error Prevention Checklist

Before providing role recommendations, verify:

- [ ] Called database tool (recommend_roles_for_job_title)
- [ ] Got actual peer data (not assumed from job title)
- [ ] Checked SOD conflicts (analyze_access_request)
- [ ] Included conflict count in response
- [ ] Mentioned compensating controls if conflicts exist
- [ ] Did NOT make up or assume role names
- [ ] Did NOT cite "industry standards" without database backup
- [ ] Clarified if recommendation is "what peers have" vs "what's compliant"

---

## Integration with Job Role Mappings

The `job_role_mappings` table defines ACCEPTABLE role combinations for specific job titles.

**When to use:**
- validate_job_role() checks this table
- If job title + role combo is in table → acceptable WITH controls
- If NOT in table → needs manual review

**What it does NOT do:**
- Does NOT tell you what roles to assign (use peer analysis for that)
- Does NOT eliminate conflicts (conflicts still exist, just acceptable)
- Does NOT bypass compensating controls

**Example:**
- Job Role Mapping says: "NetSuite Admin + Financial roles = ACCEPTABLE"
- This means: Conflicts are expected for this role, focus on controls not role removal
- NOT: These roles have no conflicts

---

## Summary

**Golden Rule:** Database first, documentation second.

**Three-step validation:**
1. What do peers have? (database tool)
2. Do those roles have conflicts? (analysis tool)
3. Present both facts + recommend with context

**Never:**
- Assume roles based on job title
- Recommend without checking conflicts
- Trust documentation over database
- Skip compensating controls

**Always:**
- Query database first
- Validate with conflict analysis
- Present ground truth data
- Include risk context
- Mention required controls

---

**Last Updated:** 2026-02-12
**Maintained By:** Compliance Team
**Review Frequency:** Update whenever new tools are added
