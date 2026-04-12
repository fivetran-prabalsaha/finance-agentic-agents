# Compliance Agent Skills

**Skills** provide workflow guidance on top of our 34 MCP tools, enabling consistent compliance methodologies and reducing user learning curve.

---

## What Are Skills?

According to Anthropic's guide:

> "MCP provides the professional kitchen: access to tools, ingredients, and equipment.
> Skills provide the recipes: step-by-step instructions on how to create something valuable."

For the Compliance Agent:
- **MCP Tools** = 34 specialized compliance tools (data access, analysis, reporting)
- **Skills** = Compliance workflows (access review, remediation, demo prep)

---

## Available Skills

### 🔍 SOD Access Review

**Status:** ✅ Ready
**Category:** Workflow Automation
**Purpose:** Systematic department/role/user access reviews

**Use When:**
- "Review Finance department"
- "Audit Controller role"
- "Check access for [user]"

**What It Does:**
1. Scopes the review (department/role/user)
2. Collects relevant user data
3. Analyzes violations and prioritizes by severity
4. Generates executive summary with findings
5. Recommends specific remediation actions

**Expected Impact:**
- Time: 30-45 min → 10-15 min (67% faster)
- Interactions: 15-20 → 3-5 (80% fewer)
- Consistency: 90%+ same methodology

**Directory:** `sod-access-review/`

---

### 🔧 SOD Violation Remediation

**Status:** ✅ Ready
**Category:** Workflow Automation
**Purpose:** Proper violation remediation with audit trail

**Use When:**
- "Fix Robin's AP conflict"
- "Remediate critical violations"
- "Remove conflicting role"

**What It Does:**
1. Selects violation to remediate
2. Analyzes impact (permissions affected)
3. Plans remediation (role removal vs compensating control vs exception)
4. Documents approval and justification
5. Implements change with verification
6. Creates complete audit trail

**Expected Impact:**
- Compliance: 100% audit trail (vs ~60% current)
- Quality: Zero missed verification steps
- Efficiency: 60% faster remediation

**Directory:** `sod-violation-remediation/`

---

### 🎭 Demo Data Manager

**Status:** ✅ Ready
**Category:** Document & Asset Creation
**Purpose:** Automated data sanitization for external demos

**Use When:**
- "Create demo user"
- "Remove Fivetran branding"
- "Prepare for external presentation"

**What It Does:**
1. Identifies use case (internal vs external demo)
2. Selects source user (e.g., robin.turner@fivetran.com)
3. Automatically sanitizes all branding:
   - "Fivetran" → "Company"
   - "fivetran.com" → "xyz.com"
   - Role prefix removal
4. Verifies no sensitive data exposed
5. Generates demo script and sample queries
6. Provides cleanup instructions

**Expected Impact:**
- Security: Zero data leakage
- Time: 30 min manual → 5 min automated
- Professional: Consistent, clean demo data

**Directory:** `demo-data-manager/`

---

## How to Use Skills

### Option 1: Claude.ai (Web)

1. **Download Skill:**
   ```bash
   cd compliance-agent/skills
   zip -r sod-access-review.zip sod-access-review/
   ```

2. **Upload to Claude:**
   - Open Claude.ai
   - Go to Settings > Capabilities > Skills
   - Click "Upload skill"
   - Select the .zip file
   - Enable the skill

3. **Use Skill:**
   Simply describe what you want:
   - "Review Finance department access"
   - "Fix violation for robin.turner@fivetran.com"
   - "Create demo user for external presentation"

### Option 2: Claude Code (CLI)

1. **Place Skills in Directory:**
   ```bash
   # Skills are already in the correct location
   ls compliance-agent/skills/
   ```

2. **Claude Code Auto-Discovers:**
   - Skills are automatically available
   - No manual loading required

3. **Use Skill:**
   Same natural language queries as Claude.ai

### Option 3: API (Programmatic)

See Anthropic's Skills API documentation:
- `/v1/skills` endpoint for management
- `container.skills` parameter in Messages API
- Agent SDK integration

---

## Skill Comparison: With vs Without

### Example: Finance Department Review

#### ❌ Without Skills (Current)
```
User: "Review Finance department access"
→ 15-20 manual tool calls
→ 30-45 minutes
→ Inconsistent approach
→ User must know 34 tools
→ Risk of missing steps
```

#### ✅ With Skills (New)
```
User: "Review Finance department access"
→ 1 skill activation
→ 5-10 minutes
→ Consistent best practices
→ User describes outcome
→ All steps automated
```

---

## Skills Architecture

```
User Request
     ↓
Skill Triggered (Progressive Disclosure)
     ↓
Step 1: Scope Definition
     ↓
Step 2-N: Orchestrated MCP Tool Calls
     ↓
Final Output: Executive Summary + Recommendations
```

**Progressive Disclosure:**
- **Level 1 (YAML):** Skill name + description (always loaded)
- **Level 2 (SKILL.md):** Full workflow (loaded when relevant)
- **Level 3 (references/):** Detailed docs (loaded on-demand)

---

## Creating New Skills

### Template Structure

```
your-skill-name/
├── SKILL.md              # Required: Main skill file
├── references/           # Optional: Detailed docs
│   └── methodology.md
└── assets/              # Optional: Templates, examples
    └── template.md
```

### SKILL.md Format

```markdown
---
name: your-skill-name
description: What it does and when to use it. Include trigger phrases.
license: MIT
metadata:
  author: Prabal Saha
  version: 1.0.0
  mcp-server: compliance-system
---

# Your Skill Name

## Instructions

### Step 1: [First Major Step]
Clear explanation...

### Step 2: [Second Major Step]
...

## Examples

### Example 1: Common Scenario
...

## Troubleshooting

### Error: Common Issue
**Cause:** Why it happens
**Solution:** How to fix

## Best Practices
- Guideline 1
- Guideline 2
```

---

## Testing Skills

### Manual Testing

1. Test triggering on relevant queries
2. Test NOT triggering on irrelevant queries
3. Verify workflow completion
4. Check output quality

### Automated Testing

```bash
# Test skill triggering
python3 -m pytest tests/test_skills.py::test_skill_triggering

# Test workflow execution
python3 -m pytest tests/test_skills.py::test_skill_workflow
```

---

## Success Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Interactions/task | 15-20 | 3-5 | Tool call logs |
| Time per review | 30-45 min | 10-15 min | User sessions |
| Support tickets | Baseline | -50% | Slack questions |
| Consistency | Variable | >90% | Audit workflows |

---

## Troubleshooting

### Skill Doesn't Trigger

**Symptoms:** Skill never loads automatically

**Fix:**
1. Check description has trigger phrases
2. Ask Claude: "When would you use [skill name]?"
3. Verify skill is enabled (Claude.ai: Settings > Skills)

### Skill Triggers Too Often

**Symptoms:** Skill loads for unrelated queries

**Fix:**
1. Add negative triggers to description
2. Be more specific about scope
3. Clarify when NOT to use

### Instructions Not Followed

**Symptoms:** Skill loads but doesn't complete workflow

**Fix:**
1. Check instructions are concise
2. Use numbered lists for steps
3. Put critical instructions at top
4. Add "CRITICAL:" or "IMPORTANT:" headers

---

## Best Practices

### For Skill Creators

- **Start Simple:** One workflow at a time
- **Test Thoroughly:** 10+ test queries before shipping
- **Document Examples:** Real use cases, not hypotheticals
- **Include Troubleshooting:** Common errors + solutions
- **Keep It Current:** Update when MCP tools change

### For Skill Users

- **Be Natural:** Describe what you want, not how
- **Trust the Workflow:** Let skill orchestrate tools
- **Provide Feedback:** Report issues to improve skills
- **Combine Skills:** Use Access Review → Remediation

---

## Related Documentation

- **Full Review:** `docs/SKILLS_BEST_PRACTICES_REVIEW.md` (30 pages)
- **Executive Summary:** `SKILLS_REVIEW_SUMMARY.md`
- **MCP Integration:** `docs/MCP_INTEGRATION_SPEC.md`
- **Anthropic Guide:** "Complete Guide to Building Skills for Claude"

---

## Support

- **Questions:** See individual skill's SKILL.md
- **Issues:** `docs/LESSONS_LEARNED.md`
- **Feedback:** Open GitHub issue or Slack #compliance-agent

---

**Last Updated:** 2026-02-14
**Phase:** Phase 7 - Skills Layer
**Status:** ✅ Active Development
