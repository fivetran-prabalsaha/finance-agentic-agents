"""
LangChain Callback Handler for Token Tracking

Bridges LangChain ChatAnthropic LLM calls into the global TokenTracker so all
agents (analyzer, risk_assessor, report_generator) contribute to cost reporting
without being rewritten to use the raw Anthropic SDK.

Usage:
    from utils.langchain_callback import TokenTrackingCallback

    callback = TokenTrackingCallback(agent_name="analyzer")
    llm = ChatAnthropic(model="claude-opus-4.6", callbacks=[callback])
"""

import logging
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from utils.token_tracker import get_global_tracker

logger = logging.getLogger(__name__)


class TokenTrackingCallback(BaseCallbackHandler):
    """
    LangChain callback that records token usage from ChatAnthropic responses
    into the global TokenTracker.
    """

    def __init__(self, agent_name: str = "langchain_agent", operation: str | None = None):
        """
        Args:
            agent_name: Label used in token usage reports (e.g., 'analyzer', 'risk_assessor')
            operation: Optional operation description for per-call granularity
        """
        super().__init__()
        self.agent_name = agent_name
        self.operation = operation
        self.tracker = get_global_tracker()

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Called by LangChain after every LLM response."""
        try:
            for generations in response.generations:
                for gen in generations:
                    # LangChain stores usage metadata in generation_info
                    info = getattr(gen, "generation_info", None) or {}
                    usage = info.get("usage") or {}

                    # Some versions store it under response_metadata
                    if not usage and hasattr(gen, "message"):
                        usage = getattr(gen.message, "usage_metadata", None) or {}

                    if not usage:
                        continue

                    model = info.get("model", "claude-opus-4.6")

                    self.tracker.track(
                        model=model,
                        input_tokens=usage.get("input_tokens", 0),
                        output_tokens=usage.get("output_tokens", 0),
                        cache_creation_tokens=usage.get("cache_creation_input_tokens", 0),
                        cache_read_tokens=usage.get("cache_read_input_tokens", 0),
                        agent_name=self.agent_name,
                        operation=self.operation or "langchain_llm_call",
                    )

        except Exception as e:
            logger.warning(f"TokenTrackingCallback failed to record usage: {e}")

    def on_llm_error(self, error: Exception | KeyboardInterrupt, **kwargs: Any) -> None:
        logger.warning(f"LLM error in {self.agent_name}: {error}")
