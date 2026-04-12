# LinkedIn Posts — Compliance Agent Journey

---

## Post 1 — Ideation (plan.md)

Before writing a single line of code, I audited the codebase and found 31 problems.

That's where the Compliance Agent started — not with building, but with understanding what was already broken.

**What I learned:**
- Audit before you build. A codebase can look complete and be nowhere near production-ready
- Prioritize ruthlessly: P0 crashes → P1 security → P2 silent failures → P3 missing infrastructure
- AI-assisted code review finds what human review misses — hardcoded credentials, SQL injection, methods called that don't exist

---

## Post 2 — Design (skill.md)

MCP gives Claude the tools. Skills teach it how to use them.

We had 35 live compliance tools but users still had to figure out the workflow every time — so I packaged the expertise into a Claude Skill.

**What I learned:**
- Encode domain knowledge once, benefit every time — the skill embeds the critical flags, the right tool order, the edge cases
- Progressive disclosure matters: keep the main file focused, move heavy reference data to a references/ folder
- The difference between "0 conflicts" and "249 conflicts, HIGH risk" was one parameter — expertise in the system beats relying on users to know it

---

## Post 3 — Execution (claude.md)

We shipped an AI compliance officer monitoring 1,928 NetSuite users 24/7 against 18 SOD rules.

The numbers look clean. Getting there wasn't.

**What I learned:**
- Token costs compound fast — routing 35 tool schemas per request was 10K tokens before the model said a word; intent-based selection cut that 85%
- Context engineering is not optional — multi-turn conversations bloat without rolling summaries; the model ends up reading JSON blobs instead of facts
- UX is adoption — Claude outputs Markdown, Slack renders symbols; rebuilding the output layer with Block Kit doubled usability overnight

---

## Post 4 — Token Economics: Why we route 35 tools down to 5 per request

Every time our compliance Slack bot gets a message, it needs to tell Claude which tools are available.

We have 35 tools. Sending all 35 on every request was costing us ~10,500 tokens — before the model said a single word.

Here's what we did instead:

```
User message
     │
     ▼
┌─────────────────────┐
│  Intent Classifier  │  ← Haiku  (~100 tokens, $0.001)
│  "access review"    │
└─────────────────────┘
     │
     ▼
┌─────────────────────┐
│   Tool Router       │  35 tools → 5 relevant tools
│                     │  access_review group selected
└─────────────────────┘
     │
     ▼
┌─────────────────────┐
│   Claude Opus       │  ← Only sees 5 tools (~1,500 tokens)
│   (reasoning)       │  Does the actual compliance work
└─────────────────────┘
```

The result:

→ 10,500 tokens → 1,500 tokens per request (85% reduction)
→ Intent classification costs ~$0.001 with Haiku
→ Opus only handles what needs Opus-level reasoning
→ Right model, right job, right cost

The key insight: not every step needs your most powerful model.

Haiku classifies intent → cheap, fast, accurate enough
Haiku compresses tool outputs → keeps context clean
Opus reasons about SOD violations → where quality actually matters

We grouped all 35 tools into 9 intent buckets:
• access_review → 5 tools
• violation_query → 5 tools
• exception_mgmt → 6 tools
• reporting → 4 tools
• remediation → 4 tools
...and so on

When someone asks "can we give John the Controller role?" — the router picks access_review. Opus never sees the reporting tools, the sync tools, or the knowledge base tools. It gets exactly what it needs.

This is context engineering. Not prompt engineering. The difference is architectural.

If you're building production AI systems and sending your full tool schema on every request — you're leaving 85% of your token budget on the table.
