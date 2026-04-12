# MCP Compliance System - Response Style Guide

**Purpose:** Ensure compliance analysis responses are concise, actionable, and executive-friendly.

---

## Response Principles

### 1. **Lead with Action**
Start with the recommendation: APPROVE ✅ | DENY ❌ | REVIEW ⚠️

### 2. **Be Concise**
- One paragraph for key findings
- 3-5 bullet points maximum for details
- Single line for costs/timelines

### 3. **Use Numbers**
- Show conflict counts
- Risk scores (X/100)
- Cost estimates ($X)

### 4. **Provide Options**
- List 2-3 alternatives
- Single line per option with cost/impact

---

## Template: Access Request Analysis

```markdown
[✅/❌/⚠️] [RECOMMENDATION]

**Analysis:** [1-2 sentence summary]
- Conflicts: [X] ([Y] CRITICAL)
- Risk Score: [X]/100
- Key Issue: [One sentence problem statement]

**Options:**
1. [Option 1] - $[cost], [impact]
2. [Option 2] - $[cost], [impact]
3. [Option 3] - $[cost], [impact]

**Recommendation:** [One sentence action]
```

---

## Example: GOOD ✅

```markdown
❌ DENY REQUEST

**Analysis:** Combining Tax Manager + Controller creates 31 SOD conflicts where user can create AND approve own transactions.
- Conflicts: 31 (29 CRITICAL)
- Risk Score: 77.5/100
- Key Issue: Violates maker-checker segregation

**Options:**
1. Deny - $0, eliminates all risk (recommended)
2. Split roles - $0, assign to 2 people
3. Approve with controls - $100K/year, requires CFO approval

**Recommendation:** Keep roles separate. Not standard for this job function.
```

**Length:** 9 lines, ~400 characters

---

## Example: BAD ❌

```markdown
💰 Cost of "Approving" This Combination
To make this even remotely acceptable, you'd need:
Minimum Control Package: $100,000+ annually

- Dual approval workflows for ALL transactions
- Real-time transaction monitoring
- Enhanced audit review frequency
- Quarterly audit committee oversight
- CEO/CFO approval for access grant
- Segregated approval processes

✅ My Recommendations

Option 1: Reject This Combination (STRONGLY RECOMMENDED)
- Assign ONLY "Fivetran - Tax" to the Tax Manager
- Keep Controller access with a separate individual
- This is the only compliant approach

Option 2: If Business Absolutely Requires (NOT RECOMMENDED)
Only consider if:
- This is the CFO or VP of Finance
- Company size is too small for separation (<10 person finance team)
- Board of Directors explicitly approves
- Full $100k+ control package is implemented
...
```

**Length:** 30+ lines, ~1500+ characters
**Problem:** Repetitive, verbose, hard to scan

---

## Control Information Format

### GOOD ✅
```
Controls needed: $100K/year (dual approval, monitoring, quarterly audits)
```

### BAD ❌
```
Minimum Control Package: $100,000+ annually

- Dual approval workflows for ALL transactions
- Real-time transaction monitoring
- Enhanced audit review frequency
- Quarterly audit committee oversight
- CEO/CFO approval for access grant
- Segregated approval processes
```

---

## When to Provide More Detail

Provide expanded information ONLY when:
1. User explicitly asks for details
2. User requests implementation steps
3. User asks "why" or "how"

Otherwise, keep responses tight and actionable.

---

## Key Metrics

**Target response length:**
- Summary: 5-10 lines
- With options: 10-15 lines
- Maximum: 20 lines

**Information density:**
- Every line should add new information
- No repetition across sections
- Assume reader is time-constrained executive

---

## Formatting Guidelines

### Use Tables for Options
```markdown
| Option | Cost | Risk | Impact |
|--------|------|------|--------|
| Deny | $0 | None | Low |
| Split | $0 | None | Medium |
| Controls | $100K | Low | Low |
```

### Use Emojis Sparingly
- ✅ ❌ ⚠️ for recommendations
- 🔴 🟡 🟢 for severity/status
- Avoid excessive decorative emojis

### Avoid These Phrases
- ❌ "To make this even remotely acceptable..."
- ❌ "Here's why:"
- ❌ "Let me explain..."
- ❌ "The following are required:"

### Use These Instead
- ✅ "If approved, requires:"
- ✅ "Key issues:"
- ✅ "Options:"
- ✅ Direct statements

---

## Summary

**Remember:** Executives need answers, not explanations. Provide:
- Clear recommendation
- Key numbers
- 2-3 alternatives
- One-line summary

**Default to brevity.** User can always ask for more detail.

---

**Version:** 1.0
**Last Updated:** 2026-02-13
