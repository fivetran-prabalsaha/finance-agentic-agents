"""
Semantic Tool Router — replaces the regex-based select_tools_for_intent().

Instead of keyword/regex matching, each tool is represented by a rich text
document (description + example queries). At query time the user message is
embedded and tools are ranked by cosine similarity.

Why this beats regex:
  - Handles plurals, paraphrasing, word-order variations automatically
  - Ranking is continuous, not binary — the most relevant tool floats to rank 1
  - Adding a new tool only requires writing its description, not new patterns
  - Falls back to the keyword router if the model is unavailable

Usage:
    from utils.semantic_router import SemanticToolRouter

    router = SemanticToolRouter(mcp_tools)          # build once at startup
    shortlist = router.select(user_message, k=8)    # call per query
"""

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool exemplars
# Each entry: description + representative example queries.
# The combined text is what gets embedded — queries match queries better
# than queries match API-style descriptions.
# ---------------------------------------------------------------------------

TOOL_EXEMPLARS: dict[str, str] = {
    # ── Violations ──────────────────────────────────────────────────────────
    "get_user_violations": (
        "Get all SOD violations for a specific user. "
        "Examples: does alice have any violations? show violations for bob@fivetran.com "
        "what SOD conflicts does john have? check if user has compliance issues"
    ),
    "list_violations": (
        "List all active violations across all users in the system. "
        "Examples: show me all violations, list all active violations right now, "
        "what violations exist, give me a full violation list"
    ),
    "get_violation_stats": (
        "Get aggregate statistics and counts of violations. "
        "Examples: how many violations do we have in total, violation summary statistics, "
        "what is the overall violation count, how many compliance issues are there"
    ),
    "get_violation_details": (
        "Get detailed information about a specific violation by ID. "
        "Examples: give me details on violation VIO-1234, what is violation VIO-5678 about, "
        "show me the full details for this violation"
    ),
    "get_violation_history": (
        "Get historical violation records for a user over time. "
        "Examples: what violations has bob had historically, show violation history for alice, "
        "past violations for this user, has john had violations before"
    ),

    # ── Access review ────────────────────────────────────────────────────────
    "analyze_access_request": (
        "Analyze whether a role assignment is safe and SOD-compliant for a user. "
        "Examples: can we assign AP Manager to carol, should john get the AR Clerk role, "
        "is it safe to give alice this role, analyze this access request, "
        "will assigning this role create a violation"
    ),
    "validate_job_role": (
        "Validate whether a role is appropriate for a given job title or person. "
        "Examples: is the CFO role appropriate for alice, validate job role for this user, "
        "does this role fit alice's job function, is this the right role for their position"
    ),
    "get_role_conflicts": (
        "Get roles that conflict with a given role due to SOD rules. "
        "Examples: what roles conflict with AP Manager, which roles are incompatible with AR Clerk, "
        "what roles does CFO conflict with, find conflicting roles, "
        "analyze the CFO role for potential conflicts, role conflict analysis"
    ),
    "recommend_roles_for_job_title": (
        "Recommend appropriate roles for a job title. "
        "Examples: what roles should a controller have, recommend roles for CFO, "
        "what roles are typical for an accounts payable manager, suggest roles for this job title"
    ),

    # ── Exception management ─────────────────────────────────────────────────
    "request_exception_approval": (
        "Submit a request for an exception to an SOD violation. "
        "Examples: I need to request an exception for john's AP and AR access, "
        "request exception for this violation, submit exception request, apply for a waiver"
    ),
    "check_my_approval_authority": (
        "Check whether the current user has authority to approve a given exception. "
        "Examples: do I have authority to approve this exception, can I approve this, "
        "what is my approval level, am I authorized to approve exceptions"
    ),
    "get_exception_details": (
        "Get full details of a specific exception by ID. "
        "Examples: show me details for exception EXC-456, what is exception EXC-789 about, "
        "give me the full exception record"
    ),
    "list_active_exceptions": (
        "List all currently active exceptions across the system. "
        "Examples: list all active exceptions currently in place, show me all exceptions, "
        "what exceptions are active right now, show open waivers"
    ),
    "approve_exception": (
        "Approve a pending exception request. "
        "Examples: approve exception EXC-789 for dave, I want to approve this exception, "
        "grant the exception, authorize this waiver"
    ),
    "revoke_exception": (
        "Revoke or cancel an active exception. "
        "Examples: revoke exception EXC-123, cancel this exception, remove the waiver for alice"
    ),

    # ── SOD rules ────────────────────────────────────────────────────────────
    "query_sod_rules": (
        "Search for SOD rules matching a topic or role combination. "
        "Examples: what SOD rules exist around AP and AR, find rules for payment processing, "
        "are there rules about AP and GL access, search segregation of duties rules"
    ),
    "get_sod_rule_details": (
        "Get full details of a specific SOD rule. "
        "Examples: explain the AP/AR segregation of duties rule, tell me more about rule SOD-12, "
        "what does this SOD rule say, describe the payment processing rule"
    ),
    "list_sod_rules": (
        "List all configured SOD rules in the system. "
        "Examples: list all the SOD rules we have, show all configured rules, "
        "what rules are in the system, give me all segregation of duties rules"
    ),

    # ── Knowledge base ───────────────────────────────────────────────────────
    "query_knowledge_base": (
        "Search the compliance knowledge base for policies and guidance. "
        "Examples: what is the best practice for remediating a payment access violation, "
        "what does policy say about dual control, look up guidance on this violation, "
        "how should we handle this compliance situation"
    ),
    "get_compensating_controls": (
        "Get compensating controls that can mitigate an SOD violation. "
        "Examples: what compensating controls exist for AP and AR violations, "
        "what controls can offset this violation, compensating control for AP/AR conflict, "
        "mitigating controls for this SOD issue"
    ),
    "get_permission_categories": (
        "Get permission categories and how they are grouped. "
        "Examples: what permission categories exist, how are permissions organized, "
        "show permission groupings"
    ),
    "search_permissions": (
        "Search for specific permissions by keyword. "
        "Examples: search for permissions related to payments, find permissions for approvals, "
        "look up GL posting permissions"
    ),

    # ── Role analysis ────────────────────────────────────────────────────────
    "analyze_role_permissions": (
        "Analyze what permissions a role contains. "
        "Examples: what permissions does the AP Manager role include, "
        "analyze the CFO role permissions, what can the AR Clerk role do, "
        "show me all permissions inside this role"
    ),

    # ── Role risk ────────────────────────────────────────────────────────────
    "get_role_risk_matrix": (
        "Get the risk matrix showing risk scores for all roles. "
        "Examples: show me the role risk matrix, which roles are highest risk, "
        "give me an overall observation on all roles and their risk, "
        "what is the risk profile of our roles, role risk scores"
    ),

    # ── Reporting ────────────────────────────────────────────────────────────
    "get_violation_summary": (
        "Get a human-readable violation summary grouped by severity for reporting. "
        "Examples: violation summary for the report, how many violations by severity, "
        "compliance statistics overview"
    ),
    "generate_compliance_report": (
        "Generate a full compliance report. "
        "Examples: generate a full compliance report, create a compliance report, "
        "I need a compliance report, produce a SOD audit report"
    ),
    "get_org_risk_assessment": (
        "Get an organisation-wide risk assessment and compliance posture. "
        "Examples: give me an overview of our current compliance posture, "
        "what is our org risk level, overall risk assessment, compliance health check"
    ),
    "export_report": (
        "Export a report to a file format. "
        "Examples: export the violation summary report, download the compliance report, "
        "export report to CSV, generate export of violations"
    ),

    # ── Remediation ──────────────────────────────────────────────────────────
    "remediate_violation": (
        "Start the remediation process for a violation. "
        "Examples: how do I remediate alice's violation, remediate this SOD conflict, "
        "fix the violation for bob, resolve this compliance issue, begin remediation"
    ),
    "schedule_review": (
        "Schedule a periodic access review for a user or role. "
        "Examples: schedule an access review for alice, set up a periodic review, "
        "schedule review for this user"
    ),
    "create_remediation_ticket": (
        "Create a ticket to track remediation of a violation. "
        "Examples: create a ticket to fix bob's AP/AR access conflict, "
        "open a remediation ticket for this violation, create a Jira ticket to resolve this"
    ),
    "notify_manager": (
        "Send a notification to a user's manager about a violation. "
        "Examples: notify alice's manager about the open violation, "
        "alert john's manager about the access conflict, send manager notification"
    ),

    # ── System ───────────────────────────────────────────────────────────────
    "list_systems": (
        "List all external systems connected to the compliance platform. "
        "Examples: what systems are currently connected, show connected systems, "
        "which integrations are active, list all data sources"
    ),
    "get_system_status": (
        "Get health and connection status of connected systems. "
        "Examples: what is the system status, is NetSuite connected, check system health"
    ),
    "trigger_manual_sync": (
        "Trigger a manual data sync from a connected system. "
        "Examples: sync the latest user data from NetSuite, trigger a manual sync, "
        "refresh data from NetSuite, run a data sync now"
    ),
    "get_sync_status": (
        "Get the status of the last data sync. "
        "Examples: when was the last sync, what is the sync status, has data synced recently"
    ),
    "initialize_session": (
        "Initialize or restore a user session with context. "
        "Internal tool — used to set up session context at the start of a conversation."
    ),
}


# ---------------------------------------------------------------------------
# SemanticToolRouter
# ---------------------------------------------------------------------------

class SemanticToolRouter:
    """
    Ranks MCP tools by cosine similarity between the user query and
    pre-computed tool embeddings.

    Build once at startup (embed_tools is called in __init__), then call
    select() for every incoming message.
    """

    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

    def __init__(
        self,
        tools: list[dict[str, Any]],
        always_include: list[str] | None = None,
    ):
        self.tools = tools
        self.always_include = always_include or ["initialize_session", "check_my_approval_authority"]
        self._tool_index: dict[str, dict] = {t["name"]: t for t in tools if "name" in t}
        self._model = None
        self._tool_names: list[str] = []
        self._embeddings: np.ndarray | None = None  # shape (n_tools, dim)
        self._build_index()

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.MODEL_NAME)
            logger.info(f"SemanticToolRouter: loaded {self.MODEL_NAME}")
        return self._model

    def _tool_text(self, tool: dict[str, Any]) -> str:
        """
        Build the text document that represents a tool in embedding space.
        Combines the exemplar (if defined) with the live description from the schema.
        """
        name = tool.get("name", "")
        # Human-readable name from underscore format
        readable_name = name.replace("_", " ")

        # Prefer our curated exemplar; fall back to the live description
        exemplar = TOOL_EXEMPLARS.get(name, "")
        schema_desc = tool.get("description", "")

        if exemplar:
            return f"{readable_name}. {exemplar}"
        elif schema_desc:
            return f"{readable_name}. {schema_desc}"
        else:
            return readable_name

    def _build_index(self) -> None:
        """Embed all tools and store as a numpy matrix."""
        try:
            model = self._load_model()
            self._tool_names = [t["name"] for t in self.tools if "name" in t]
            texts = [self._tool_text(t) for t in self.tools if "name" in t]
            vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
            self._embeddings = np.array(vecs, dtype=np.float32)
            logger.info(
                f"SemanticToolRouter: indexed {len(self._tool_names)} tools "
                f"(dim={self._embeddings.shape[1]})"
            )
        except Exception as e:
            logger.error(f"SemanticToolRouter: index build failed — {e}")
            self._embeddings = None

    def select(
        self,
        query: str,
        k: int = 8,
    ) -> list[dict[str, Any]]:
        """
        Return the top-k most relevant tools for `query`.
        always_include tools are appended at the end if not already in the list.
        Falls back to an empty list (caller should fall back to keyword router).
        """
        if self._embeddings is None or not self._tool_names:
            logger.warning("SemanticToolRouter: embeddings unavailable, returning empty list")
            return []

        try:
            model = self._load_model()
            q_vec = model.encode([query], normalize_embeddings=True, show_progress_bar=False)
            q_vec = np.array(q_vec[0], dtype=np.float32)

            # Cosine similarity — embeddings are already unit-normalised
            scores = self._embeddings @ q_vec  # shape (n_tools,)

            # Always-include tools should not take up top-k slots
            always_set = set(self.always_include)
            scored = [
                (self._tool_names[i], float(scores[i]))
                for i in range(len(self._tool_names))
                if self._tool_names[i] not in always_set
            ]
            scored.sort(key=lambda x: x[1], reverse=True)

            # Take top-k intent tools, then append always_include
            selected_names = [name for name, _ in scored[:k]]
            for name in self.always_include:
                if name not in selected_names:
                    selected_names.append(name)

            result = [self._tool_index[n] for n in selected_names if n in self._tool_index]

            logger.info(
                f"SemanticToolRouter: '{query[:60]}' → "
                f"{[n for n, _ in scored[:3]]} (top-3 scores: "
                f"{[round(s,3) for _, s in scored[:3]]})"
            )
            return result

        except Exception as e:
            logger.error(f"SemanticToolRouter.select failed: {e}")
            return []

    def update_tools(self, tools: list[dict[str, Any]]) -> None:
        """Rebuild the index when the tool list changes (e.g. after /tools/refresh)."""
        self.tools = tools
        self._tool_index = {t["name"]: t for t in tools if "name" in t}
        self._build_index()


# ---------------------------------------------------------------------------
# Module-level singleton — built once when the bot starts
# ---------------------------------------------------------------------------

_router_instance: SemanticToolRouter | None = None


def get_router(tools: list[dict[str, Any]] | None = None) -> SemanticToolRouter | None:
    """
    Return the module-level SemanticToolRouter singleton.
    If tools is provided and no instance exists yet, build it now.
    """
    global _router_instance
    if tools and _router_instance is None:
        _router_instance = SemanticToolRouter(tools)
    return _router_instance


def semantic_select_tools(
    user_message: str,
    all_tools: list[dict[str, Any]],
    always_include: list[str] | None = None,
    max_tools: int = 8,
) -> list[dict[str, Any]]:
    """
    Drop-in replacement for select_tools_for_intent().

    Builds the router singleton on first call, then reuses it.
    Falls back to the keyword router on any error.
    """
    global _router_instance
    try:
        if _router_instance is None or {t["name"] for t in all_tools} != set(_router_instance._tool_index.keys()):
            _router_instance = SemanticToolRouter(all_tools, always_include=always_include)
        return _router_instance.select(user_message, k=max_tools)
    except Exception as e:
        logger.error(f"semantic_select_tools failed, falling back to keyword router: {e}")
        from utils.tool_router import select_tools_for_intent
        return select_tools_for_intent(user_message, all_tools, always_include, max_tools)
