"""
LangSmith evaluators for the compliance agent.

All evaluators follow the LangSmith 0.4.x signature:
    fn(outputs: dict, reference_outputs: dict) -> dict | list[dict]

Metrics implemented:
  - hit_rate_at_k     : was the expected tool in the top-K returned? (binary)
  - mrr               : 1 / rank of the first correct tool
  - ndcg_at_k         : normalised discounted cumulative gain (graded relevance)
  - precision_at_k    : fraction of top-K tools that are relevant
  - faithfulness      : LLM-as-judge (Haiku) — does the answer contain expected facts?
"""

import math
import json
import logging
import os
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Hit Rate @ K
# ---------------------------------------------------------------------------

def hit_rate_at_k(k: int = 10):
    """
    Factory: returns an evaluator that checks whether `expected_tool` appears
    in the top-K tool names returned by the target.

    outputs must contain:    selected_tool_names: list[str]
    reference_outputs must contain: expected_tool: str
    """
    def evaluator(outputs: Dict[str, Any], reference_outputs: Dict[str, Any]) -> Dict:
        selected: List[str] = outputs.get("selected_tool_names", [])[:k]
        expected: str = reference_outputs.get("expected_tool", "")
        score = 1.0 if expected in selected else 0.0
        return {"key": f"hit_rate_at_{k}", "score": score}

    evaluator.__name__ = f"hit_rate_at_{k}"
    return evaluator


# ---------------------------------------------------------------------------
# MRR — Mean Reciprocal Rank
# ---------------------------------------------------------------------------

def mrr_evaluator(outputs: Dict[str, Any], reference_outputs: Dict[str, Any]) -> Dict:
    """
    Score = 1 / rank of the first occurrence of `expected_tool` in the returned list.
    Score = 0.0 if the tool is absent.

    outputs must contain:    selected_tool_names: list[str]
    reference_outputs must contain: expected_tool: str
    """
    selected: List[str] = outputs.get("selected_tool_names", [])
    expected: str = reference_outputs.get("expected_tool", "")
    try:
        rank = selected.index(expected) + 1  # 1-indexed
        score = 1.0 / rank
    except ValueError:
        score = 0.0
    return {"key": "mrr", "score": score}


# ---------------------------------------------------------------------------
# NDCG @ K — Normalised Discounted Cumulative Gain
# ---------------------------------------------------------------------------

def ndcg_at_k(k: int = 10):
    """
    Factory: returns an NDCG@K evaluator using the graded relevance map.

    outputs must contain:    selected_tool_names: list[str]
    reference_outputs must contain:
        relevant_tools: dict[str, int]  # tool_name → relevance score (0/1/2)
    """
    def evaluator(outputs: Dict[str, Any], reference_outputs: Dict[str, Any]) -> Dict:
        selected: List[str] = outputs.get("selected_tool_names", [])[:k]
        relevance: Dict[str, int] = reference_outputs.get("relevant_tools", {})

        # DCG: sum of (relevance / log2(rank + 1)) for each position
        dcg = sum(
            relevance.get(tool, 0) / math.log2(i + 2)
            for i, tool in enumerate(selected)
        )

        # IDCG: ideal ordering of all known relevant tools
        ideal_scores = sorted(relevance.values(), reverse=True)[:k]
        idcg = sum(
            score / math.log2(i + 2)
            for i, score in enumerate(ideal_scores)
        )

        score = (dcg / idcg) if idcg > 0 else 0.0
        return {"key": f"ndcg_at_{k}", "score": round(score, 4)}

    evaluator.__name__ = f"ndcg_at_{k}"
    return evaluator


# ---------------------------------------------------------------------------
# Precision @ K
# ---------------------------------------------------------------------------

def precision_at_k(k: int = 5):
    """
    Factory: returns a Precision@K evaluator.
    A tool is "relevant" if its score in `relevant_tools` is > 0.

    outputs must contain:    selected_tool_names: list[str]
    reference_outputs must contain:
        relevant_tools: dict[str, int]
    """
    def evaluator(outputs: Dict[str, Any], reference_outputs: Dict[str, Any]) -> Dict:
        selected: List[str] = outputs.get("selected_tool_names", [])[:k]
        relevance: Dict[str, int] = reference_outputs.get("relevant_tools", {})
        hits = sum(1 for tool in selected if relevance.get(tool, 0) > 0)
        score = hits / k if k > 0 else 0.0
        return {"key": f"precision_at_{k}", "score": round(score, 4)}

    evaluator.__name__ = f"precision_at_{k}"
    return evaluator


# ---------------------------------------------------------------------------
# Faithfulness — LLM-as-judge (Haiku)
# ---------------------------------------------------------------------------

def faithfulness_evaluator(outputs: Dict[str, Any], reference_outputs: Dict[str, Any]) -> Dict:
    """
    Uses Claude Haiku to score whether the agent's answer contains each
    expected fact. Returns a float 0.0–1.0.

    outputs must contain:    answer: str
    reference_outputs must contain: expected_facts: list[str]
    """
    import anthropic

    answer: str = outputs.get("answer", "").strip()
    expected_facts: List[str] = reference_outputs.get("expected_facts", [])

    if not answer or not expected_facts:
        return {"key": "faithfulness", "score": 0.0}

    facts_str = "\n".join(f"{i+1}. {f}" for i, f in enumerate(expected_facts))
    prompt = (
        "You are a strict evaluator. Read the ANSWER and check how many of the "
        "EXPECTED FACTS it satisfies. A fact is satisfied if the answer clearly "
        "addresses or confirms it.\n\n"
        f"EXPECTED FACTS:\n{facts_str}\n\n"
        f"ANSWER:\n{answer}\n\n"
        "Reply with ONLY valid JSON in this exact format: "
        '{"score": <float 0.0 to 1.0>, "satisfied": <int>, "total": <int>}'
    )

    try:
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=64,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        result = json.loads(raw)
        score = float(result.get("score", 0.0))
        logger.info(
            f"Faithfulness: {result.get('satisfied')}/{result.get('total')} facts satisfied → {score}"
        )
    except Exception as e:
        logger.warning(f"faithfulness_evaluator failed: {e}")
        score = 0.0

    return {"key": "faithfulness", "score": score}
