"""
Model Configuration — Maps each agent step to the right Claude model.

Cost rationale (per million tokens, input/output):
  claude-opus-4.6:    $15 / $75  — deepest reasoning, complex compliance analysis
  claude-sonnet-4.6:   $3 / $15  — structured tasks, report generation, scoring
  claude-haiku-4.5:    $1 /  $5  — classification, routing, summarization

Use the cheapest model whose quality is sufficient for the task.
"""

import os

# ---------------------------------------------------------------------------
# Canonical model IDs
# ---------------------------------------------------------------------------
OPUS   = "claude-opus-4.6"
SONNET = "claude-sonnet-4-5"   # langchain-anthropic model name
HAIKU  = "claude-haiku-4-5-20251001"

# ---------------------------------------------------------------------------
# Per-step model assignments
# Override individual steps via environment variables, e.g.:
#   STEP_MODEL_SOD_ANALYSIS=claude-sonnet-4-5
# ---------------------------------------------------------------------------
STEP_MODEL_MAP: dict[str, str] = {
    # Core compliance reasoning — needs Opus depth
    "sod_analysis":              os.getenv("STEP_MODEL_SOD_ANALYSIS",    OPUS),
    "ai_reasoning_per_user":     os.getenv("STEP_MODEL_AI_REASONING",    OPUS),

    # Structured scoring / report generation — Sonnet is sufficient
    "risk_score_calculation":    os.getenv("STEP_MODEL_RISK_SCORE",      SONNET),
    "report_generation":         os.getenv("STEP_MODEL_REPORT_GEN",      SONNET),
    "judge_agent":               os.getenv("STEP_MODEL_JUDGE",           SONNET),

    # Classification / routing / summarization — use Haiku
    "slack_intent_detection":    os.getenv("STEP_MODEL_SLACK_INTENT",    HAIKU),
    "tool_routing":              os.getenv("STEP_MODEL_TOOL_ROUTING",     HAIKU),
    "tool_output_compression":   os.getenv("STEP_MODEL_TOOL_COMPRESS",   HAIKU),
    "turn_context_compression":  os.getenv("STEP_MODEL_TURN_COMPRESS",   HAIKU),
}

# Only trigger AI reasoning per user for violations at or above this severity
AI_REASONING_MIN_SEVERITY: str = os.getenv("AI_REASONING_MIN_SEVERITY", "HIGH")


def get_model(step: str) -> str:
    """
    Return the configured model for a pipeline step.

    Args:
        step: Key from STEP_MODEL_MAP (e.g., 'sod_analysis')

    Returns:
        Model identifier string
    """
    return STEP_MODEL_MAP.get(step, OPUS)
