"""
AR Collection Agent — multi-agent system on Vertex AI Agent Engine.

Architecture:
    router_agent (gemini-2.5-flash)
        ├── synthesizer  (gemini-2.5-pro)   — NetSuite MCP tools
        └── escalator    (gemini-2.5-flash) — Atlassian MCP tools

The router dispatches all queries; it never answers directly.
Synthesizer signals INSUFFICIENT_KNOWLEDGE to trigger escalation.
"""
from google.adk.agents import LlmAgent

from tools import atlassian_toolset, netsuite_toolset

# ── Specialist: NetSuite operations ──────────────────────────────────────────

synthesizer = LlmAgent(
    name="synthesizer",
    model="gemini-2.5-pro",
    description=(
        "Handles technical AR queries: look up invoices, customer accounts, "
        "and perform NetSuite record operations (create, update, search)."
    ),
    instruction="""You are a technical AR specialist with access to NetSuite.

Use the available NetSuite tools to resolve queries about invoices, customer
accounts, payment statuses, and AR records.

If you cannot resolve the query — because the situation requires human
judgment, is outside your authority, or the data is insufficient — respond
with ONLY the exact text:

    INSUFFICIENT_KNOWLEDGE

Do not add any explanation when returning INSUFFICIENT_KNOWLEDGE.
""",
    tools=[netsuite_toolset],
)

# ── Specialist: Jira escalation ───────────────────────────────────────────────

escalator = LlmAgent(
    name="escalator",
    model="gemini-2.5-flash",
    description=(
        "Creates Jira issues for AR cases that require human follow-up "
        "or cannot be resolved automatically."
    ),
    instruction="""You are an escalation specialist. Your only job is to create
Jira issues for AR collection cases that need human intervention.

When creating an issue always include:
- Customer name and account ID
- Invoice number(s) and total amount overdue
- Number of days overdue
- Brief summary of why it requires escalation
- Suggested priority (Critical / High / Medium / Low)

After creating the issue, respond with the Jira issue key and URL.
""",
    tools=[atlassian_toolset],
)

# ── Router (root agent) ───────────────────────────────────────────────────────

root_agent = LlmAgent(
    name="router_agent",
    model="gemini-2.5-flash",
    description="Dispatcher — routes AR queries to the correct specialist agent.",
    instruction="""You are a router. You never answer questions yourself.

Routing rules (apply in order):
1. Technical questions about invoices, NetSuite records, or AR data
   → transfer to synthesizer.
2. If synthesizer responds with exactly "INSUFFICIENT_KNOWLEDGE"
   → transfer to escalator.
3. Explicit escalation requests (e.g. "escalate this", "create a ticket")
   → transfer directly to escalator.

After a specialist finishes, relay their response verbatim to the user.
Never add commentary or answer on your own.
""",
    sub_agents=[synthesizer, escalator],
)
