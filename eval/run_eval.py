"""
Evaluation runner — pushes metric results to LangSmith.

Usage:
    # Push datasets first (one-time or when golden set changes)
    python -m eval.golden_set

    # Run all evaluations
    python -m eval.run_eval

    # Run only tool-selection eval
    python -m eval.run_eval --suite tool_selection

    # Run only answer-quality eval (requires live MCP server at :8080)
    python -m eval.run_eval --suite answer_quality

Results appear in LangSmith → Experiments tab under the project set by
LANGCHAIN_PROJECT in your .env (or default project if unset).
"""

import logging
import os
import sys
from typing import Any

from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_stub_tools() -> list[dict[str, Any]]:
    """
    Build a minimal tool list from TOOL_GROUPS so the tool-selection eval
    can run without a live MCP server.
    """
    from utils.tool_router import TOOL_GROUPS

    seen = set()
    tools = []
    for group_tools in TOOL_GROUPS.values():
        for name in group_tools:
            if name not in seen:
                seen.add(name)
                tools.append({"name": name, "description": f"Tool: {name}", "input_schema": {}})
    # Always include the 'always_include' tools even if not in any group
    for name in ("initialize_session", "check_my_approval_authority"):
        if name not in seen:
            tools.append({"name": name, "description": f"Tool: {name}", "input_schema": {}})
    return tools


def _fetch_live_tools() -> list[dict[str, Any]]:
    """Fetch tool schemas from the live MCP server at :8080."""
    import requests

    url = os.environ.get("MCP_SERVER_URL", "http://localhost:8080")
    api_key = os.environ.get("MCP_API_KEY", "dev-key-12345")
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    headers = {"Content-Type": "application/json", "X-API-Key": api_key}
    resp = requests.post(f"{url}/mcp", json=payload, headers=headers, timeout=5)
    resp.raise_for_status()
    return resp.json().get("result", {}).get("tools", [])


def _get_tools(live: bool = False) -> list[dict[str, Any]]:
    if live:
        try:
            tools = _fetch_live_tools()
            logger.info(f"Fetched {len(tools)} tools from live MCP server.")
            return tools
        except Exception as e:
            logger.warning(f"Live MCP fetch failed ({e}) — falling back to stubs.")
    tools = _build_stub_tools()
    logger.info(f"Using {len(tools)} stub tools (offline mode).")
    return tools


# ---------------------------------------------------------------------------
# Suite 1: Tool Selection
# Evaluates select_tools_for_intent() — no LLM, no server needed.
# ---------------------------------------------------------------------------

def run_tool_selection_eval(live_tools: bool = False, router: str = "keyword") -> Any:
    """
    router: "keyword" (regex-based) | "semantic" (embedding-based)
    """
    from langsmith import evaluate

    from eval.evaluators import hit_rate_at_k, mrr_evaluator, ndcg_at_k, precision_at_k

    tools = _get_tools(live=live_tools)

    if router == "semantic":
        from utils.semantic_router import SemanticToolRouter
        _router = SemanticToolRouter(tools)

        def target(inputs: dict[str, Any]) -> dict[str, Any]:
            selected = _router.select(inputs["query"], k=8)
            return {"selected_tool_names": [t["name"] for t in selected]}
    else:
        from utils.tool_router import select_tools_for_intent

        def target(inputs: dict[str, Any]) -> dict[str, Any]:
            selected = select_tools_for_intent(inputs["query"], tools)
            return {"selected_tool_names": [t["name"] for t in selected]}

    logger.info(f"Running tool-selection eval [{router}] against 'compliance-tool-selection-v1' …")
    results = evaluate(
        target,
        data="compliance-tool-selection-v1",
        evaluators=[
            hit_rate_at_k(k=10),
            hit_rate_at_k(k=5),
            mrr_evaluator,
            ndcg_at_k(k=10),
            precision_at_k(k=5),
        ],
        experiment_prefix=f"tool-selection-{router}",
        metadata={"router": router, "mode": "live" if live_tools else "stub"},
    )
    logger.info("Tool-selection eval complete. View results in LangSmith → Experiments.")
    return results


# ---------------------------------------------------------------------------
# Suite 2: Answer Quality (faithfulness)
# Runs the full process_with_claude() pipeline — requires live MCP at :8080.
# ---------------------------------------------------------------------------

def run_answer_quality_eval() -> Any:
    from langsmith import evaluate

    from eval.evaluators import faithfulness_evaluator

    # Import the production function directly so LangSmith traces it
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from slack_bot_local import fetch_mcp_tools, process_with_claude
    fetch_mcp_tools()   # populate global MCP_TOOLS

    def target(inputs: dict[str, Any]) -> dict[str, Any]:
        query = inputs["query"]
        answer = process_with_claude(
            user_message=query,
            user_email="eval-runner@fivetran.com",
        )
        return {"answer": answer}

    logger.info("Running answer-quality evaluation against 'compliance-answer-quality-v1' …")
    results = evaluate(
        target,
        data="compliance-answer-quality-v1",
        evaluators=[faithfulness_evaluator],
        experiment_prefix="answer-quality",
        metadata={"judge_model": "claude-haiku-4-5-20251001"},
    )
    logger.info("Answer-quality eval complete. View results in LangSmith → Experiments.")
    return results


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    suite = None
    live_tools = "--live" in sys.argv
    for arg in sys.argv[1:]:
        if arg.startswith("--suite="):
            suite = arg.split("=", 1)[1]
        elif arg == "--suite" and sys.argv.index(arg) + 1 < len(sys.argv):
            suite = sys.argv[sys.argv.index(arg) + 1]

    router = "keyword"
    for arg in sys.argv[1:]:
        if arg.startswith("--router="):
            router = arg.split("=", 1)[1]

    if suite == "tool_selection":
        run_tool_selection_eval(live_tools=live_tools, router=router)
    elif suite == "answer_quality":
        run_answer_quality_eval()
    elif suite == "compare":
        # Run both routers and print side-by-side
        run_tool_selection_eval(live_tools=live_tools, router="keyword")
        run_tool_selection_eval(live_tools=live_tools, router="semantic")
    else:
        run_tool_selection_eval(live_tools=live_tools, router=router)
        print(
            "\nSkipped answer_quality eval (requires live MCP server).\n"
            "Run with --suite=answer_quality to include it."
        )


if __name__ == "__main__":
    main()
