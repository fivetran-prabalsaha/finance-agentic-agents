"""
Golden dataset definitions for the compliance agent evaluation suite.

Two datasets:
  - compliance-tool-selection-v1  : 30 queries, each labelled with the primary
                                    expected tool and a graded relevance map for NDCG.
  - compliance-answer-quality-v1  : 10 queries with expected factual ground truth
                                    for the faithfulness (LLM-as-judge) evaluator.

Usage:
    python -m eval.golden_set            # push / refresh both datasets to LangSmith
    python -m eval.golden_set --dry-run  # print examples, don't push
"""

import json
import sys
from typing import Any

# ---------------------------------------------------------------------------
# Tool-selection golden set
# Each entry:
#   query          : raw user message (as it would arrive in Slack)
#   expected_tool  : single primary tool we expect to appear in the shortlist
#   relevant_tools : graded relevance {tool_name: score}
#                    2 = primary match, 1 = useful secondary, 0 = irrelevant
# ---------------------------------------------------------------------------

TOOL_SELECTION_EXAMPLES: list[dict[str, Any]] = [
    # ── Violation queries ──────────────────────────────────────────────────
    {
        "query": "does alice@fivetran.com have any SOD violations?",
        "expected_tool": "get_user_violations",
        "relevant_tools": {"get_user_violations": 2, "list_violations": 1, "get_violation_history": 1},
    },
    {
        "query": "show me all active violations right now",
        "expected_tool": "list_violations",
        "relevant_tools": {"list_violations": 2, "get_violation_stats": 1, "get_user_violations": 1},
    },
    {
        "query": "how many total violations do we have?",
        "expected_tool": "get_violation_stats",
        "relevant_tools": {"get_violation_stats": 2, "list_violations": 1},
    },
    {
        "query": "give me the details on violation VIO-1234",
        "expected_tool": "get_violation_details",
        "relevant_tools": {"get_violation_details": 2, "get_user_violations": 1},
    },
    {
        "query": "what violations has bob had historically?",
        "expected_tool": "get_violation_history",
        "relevant_tools": {"get_violation_history": 2, "get_user_violations": 1, "list_violations": 1},
    },

    # ── Access review ──────────────────────────────────────────────────────
    {
        "query": "can we assign the AP Manager role to carol?",
        "expected_tool": "analyze_access_request",
        "relevant_tools": {"analyze_access_request": 2, "get_role_conflicts": 1, "validate_job_role": 1},
    },
    {
        "query": "should john get the AR Clerk role?",
        "expected_tool": "analyze_access_request",
        "relevant_tools": {"analyze_access_request": 2, "get_role_conflicts": 1},
    },
    {
        "query": "is the CFO role appropriate for alice given her current access?",
        "expected_tool": "validate_job_role",
        "relevant_tools": {"validate_job_role": 2, "analyze_access_request": 1, "get_role_conflicts": 1},
    },
    {
        "query": "what roles conflict with AP Manager?",
        "expected_tool": "get_role_conflicts",
        "relevant_tools": {"get_role_conflicts": 2, "analyze_role_permissions": 1, "query_sod_rules": 1},
    },
    {
        "query": "what roles should a controller typically have?",
        "expected_tool": "recommend_roles_for_job_title",
        "relevant_tools": {"recommend_roles_for_job_title": 2, "validate_job_role": 1},
    },

    # ── Exception management ───────────────────────────────────────────────
    {
        "query": "I need to request an exception for john's AP and AR access",
        "expected_tool": "request_exception_approval",
        "relevant_tools": {"request_exception_approval": 2, "check_my_approval_authority": 1},
    },
    {
        "query": "do I have the authority to approve this exception?",
        "expected_tool": "check_my_approval_authority",
        "relevant_tools": {"check_my_approval_authority": 2, "request_exception_approval": 1},
    },
    {
        "query": "show me the details for exception EXC-456",
        "expected_tool": "get_exception_details",
        "relevant_tools": {"get_exception_details": 2, "list_active_exceptions": 1},
    },
    {
        "query": "list all active exceptions currently in place",
        "expected_tool": "list_active_exceptions",
        "relevant_tools": {"list_active_exceptions": 2, "get_exception_details": 1},
    },
    {
        "query": "approve exception EXC-789 for dave",
        "expected_tool": "approve_exception",
        "relevant_tools": {"approve_exception": 2, "check_my_approval_authority": 1},
    },

    # ── SOD rules ──────────────────────────────────────────────────────────
    {
        "query": "what SOD rules exist around AP and AR?",
        "expected_tool": "query_sod_rules",
        "relevant_tools": {"query_sod_rules": 2, "get_sod_rule_details": 1, "list_sod_rules": 1},
    },
    {
        "query": "explain the AP/AR segregation of duties rule",
        "expected_tool": "get_sod_rule_details",
        "relevant_tools": {"get_sod_rule_details": 2, "query_sod_rules": 1},
    },
    {
        "query": "list all the SOD rules we have configured",
        "expected_tool": "list_sod_rules",
        "relevant_tools": {"list_sod_rules": 2, "query_sod_rules": 1},
    },

    # ── Knowledge base ─────────────────────────────────────────────────────
    {
        "query": "what compensating controls exist for AP and AR violations?",
        "expected_tool": "get_compensating_controls",
        "relevant_tools": {"get_compensating_controls": 2, "query_knowledge_base": 1},
    },
    {
        "query": "what is the best practice for remediating a payment access violation?",
        "expected_tool": "query_knowledge_base",
        "relevant_tools": {"query_knowledge_base": 2, "get_compensating_controls": 1},
    },

    # ── Role analysis ──────────────────────────────────────────────────────
    {
        "query": "what permissions does the AP Manager role include?",
        "expected_tool": "analyze_role_permissions",
        "relevant_tools": {"analyze_role_permissions": 2, "get_role_conflicts": 1},
    },
    {
        "query": "analyze the CFO role for potential conflicts",
        "expected_tool": "get_role_conflicts",
        "relevant_tools": {"get_role_conflicts": 2, "analyze_role_permissions": 1},
    },

    # ── Role risk ──────────────────────────────────────────────────────────
    {
        "query": "show me the role risk matrix",
        "expected_tool": "get_role_risk_matrix",
        "relevant_tools": {"get_role_risk_matrix": 2, "get_role_conflicts": 1},
    },
    {
        "query": "give me an overall observation on all roles and their risk",
        "expected_tool": "get_role_risk_matrix",
        "relevant_tools": {"get_role_risk_matrix": 2, "list_violations": 1},
    },

    # ── Reporting ──────────────────────────────────────────────────────────
    {
        "query": "generate a full compliance report",
        "expected_tool": "generate_compliance_report",
        "relevant_tools": {"generate_compliance_report": 2, "get_violation_stats": 1, "get_org_risk_assessment": 1},
    },
    {
        "query": "give me an overview of our current compliance posture",
        "expected_tool": "get_org_risk_assessment",
        "relevant_tools": {"get_org_risk_assessment": 2, "generate_compliance_report": 1, "get_violation_stats": 1},
    },
    {
        "query": "export the violation summary report",
        "expected_tool": "export_report",
        "relevant_tools": {"export_report": 2, "generate_compliance_report": 1},
    },

    # ── Remediation ────────────────────────────────────────────────────────
    {
        "query": "how do I remediate alice's violation?",
        "expected_tool": "remediate_violation",
        "relevant_tools": {"remediate_violation": 2, "create_remediation_ticket": 1, "notify_manager": 1},
    },
    {
        "query": "create a ticket to fix bob's AP/AR access conflict",
        "expected_tool": "create_remediation_ticket",
        "relevant_tools": {"create_remediation_ticket": 2, "remediate_violation": 1},
    },
    {
        "query": "notify alice's manager about the open violation",
        "expected_tool": "notify_manager",
        "relevant_tools": {"notify_manager": 2, "create_remediation_ticket": 1},
    },

    # ── System ─────────────────────────────────────────────────────────────
    {
        "query": "what systems are currently connected?",
        "expected_tool": "list_systems",
        "relevant_tools": {"list_systems": 2, "get_system_status": 1},
    },
    {
        "query": "sync the latest user data from NetSuite",
        "expected_tool": "trigger_manual_sync",
        "relevant_tools": {"trigger_manual_sync": 2, "get_sync_status": 1},
    },
]


# ---------------------------------------------------------------------------
# Answer quality golden set
# Each entry:
#   query          : Slack message sent to the bot
#   expected_facts : list of facts the answer MUST contain (for faithfulness eval)
# ---------------------------------------------------------------------------

ANSWER_QUALITY_EXAMPLES: list[dict[str, Any]] = [
    {
        "query": "how many total violations do we have?",
        "expected_facts": [
            "violation count is a number",
            "answer references NetSuite or compliance data",
        ],
    },
    {
        "query": "what is the AP/AR segregation of duties rule?",
        "expected_facts": [
            "AP and AR should not be held by the same person",
            "reason is to prevent fraud or unauthorized payments",
        ],
    },
    {
        "query": "what compensating controls exist for AP and AR violations?",
        "expected_facts": [
            "compensating controls are mentioned",
            "at least one specific control is named",
        ],
    },
    {
        "query": "can we assign AP Manager to someone who already has AR Clerk?",
        "expected_facts": [
            "this would create an SOD violation",
            "AP and AR roles conflict",
        ],
    },
    {
        "query": "what systems are connected?",
        "expected_facts": [
            "NetSuite is mentioned",
            "answer lists at least one system",
        ],
    },
    {
        "query": "show me the role risk matrix",
        "expected_facts": [
            "roles are ranked or scored by risk",
            "at least one high-risk role is mentioned",
        ],
    },
    {
        "query": "give me an overview of our compliance posture",
        "expected_facts": [
            "violation count or risk level is mentioned",
            "answer provides an actionable summary",
        ],
    },
    {
        "query": "what SOD rules exist around payment processing?",
        "expected_facts": [
            "at least one rule involving payment roles is described",
            "rule explains why the separation is required",
        ],
    },
    {
        "query": "list all active exceptions currently in place",
        "expected_facts": [
            "answer mentions exceptions or states none exist",
            "response is specific, not generic",
        ],
    },
    {
        "query": "what roles should a controller typically have in NetSuite?",
        "expected_facts": [
            "at least one role recommendation is given",
            "recommendation is specific to a controller job function",
        ],
    },
]


def push_to_langsmith(dry_run: bool = False) -> None:
    """Create or refresh both datasets in LangSmith."""
    from langsmith import Client

    client = Client()

    datasets = {
        "compliance-tool-selection-v1": {
            "description": "30 labelled queries for evaluating select_tools_for_intent() — Hit Rate@K, MRR, NDCG, Precision@K",
            "examples": [
                {"inputs": {"query": ex["query"]},
                 "outputs": {"expected_tool": ex["expected_tool"], "relevant_tools": ex["relevant_tools"]}}
                for ex in TOOL_SELECTION_EXAMPLES
            ],
        },
        "compliance-answer-quality-v1": {
            "description": "10 queries with expected facts for faithfulness (LLM-as-judge) evaluation",
            "examples": [
                {"inputs": {"query": ex["query"]},
                 "outputs": {"expected_facts": ex["expected_facts"]}}
                for ex in ANSWER_QUALITY_EXAMPLES
            ],
        },
    }

    for name, config in datasets.items():
        print(f"\nDataset: {name}  ({len(config['examples'])} examples)")
        if dry_run:
            print(json.dumps(config["examples"][0], indent=2))
            print("  ... (dry-run, not pushed)")
            continue

        # Delete existing dataset to allow full refresh
        existing = [d for d in client.list_datasets() if d.name == name]
        if existing:
            client.delete_dataset(dataset_id=existing[0].id)
            print("  Deleted existing dataset.")

        dataset = client.create_dataset(name, description=config["description"])
        client.create_examples(
            inputs=[ex["inputs"] for ex in config["examples"]],
            outputs=[ex["outputs"] for ex in config["examples"]],
            dataset_id=dataset.id,
        )
        print(f"  Pushed {len(config['examples'])} examples → dataset ID: {dataset.id}")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    push_to_langsmith(dry_run=dry_run)
