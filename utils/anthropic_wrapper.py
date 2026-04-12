"""
Anthropic Client Wrapper with Token Tracking

Wraps the Anthropic API client to automatically track token usage and costs
"""

import logging

from anthropic import Anthropic
from langsmith import traceable
from langsmith.run_helpers import get_current_run_tree

from utils.token_tracker import get_global_tracker

logger = logging.getLogger(__name__)


class AnthropicClientWrapper:
    """
    Wrapper around Anthropic client that automatically tracks token usage

    Usage:
        client = AnthropicClientWrapper(agent_name="analyzer")
        response = client.messages.create(...)
        # Token usage automatically tracked!
    """

    def __init__(
        self,
        agent_name: str | None = None,
        api_key: str | None = None,
        track_tokens: bool = True
    ):
        """
        Initialize wrapped client

        Args:
            agent_name: Name of agent for tracking
            api_key: Anthropic API key (optional, uses env var if not provided)
            track_tokens: Whether to track token usage
        """
        self.agent_name = agent_name or "unknown"
        self.track_tokens = track_tokens
        self.token_tracker = get_global_tracker() if track_tokens else None

        # Initialize the actual Anthropic client
        if api_key:
            self.client = Anthropic(api_key=api_key)
        else:
            self.client = Anthropic()  # Uses ANTHROPIC_API_KEY env var

        # Wrap the messages interface
        self.messages = MessagesWrapper(
            client=self.client,
            agent_name=self.agent_name,
            token_tracker=self.token_tracker
        )


class MessagesWrapper:
    """Wrapper for messages.create() that tracks token usage"""

    def __init__(self, client: Anthropic, agent_name: str, token_tracker):
        self._client = client
        self.agent_name = agent_name
        self.token_tracker = token_tracker

    @traceable(run_type="llm", name="claude.messages.create")
    def create(
        self,
        model: str,
        max_tokens: int,
        messages: list,
        operation: str | None = None,
        **kwargs
    ):
        """
        Create a message and track token usage

        Args:
            model: Claude model name
            max_tokens: Maximum tokens to generate
            messages: List of message dictionaries
            operation: Description of the operation
            **kwargs: Additional arguments for messages.create()

        Returns:
            Message response from Claude API
        """
        # Make the actual API call
        response = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=messages,
            **kwargs
        )

        # Track token usage
        usage = response.usage if hasattr(response, 'usage') else None

        if usage:
            # Push token counts + cost into the LangSmith span
            rt = get_current_run_tree()
            if rt:
                input_tokens = usage.input_tokens
                output_tokens = usage.output_tokens
                rt.extra = rt.extra or {}
                # ls_model_name + ls_provider let LangSmith look up pricing
                # and populate Cost per Trace / Tokens per Trace charts
                # Map to LangSmith's known pricing model names so cost is computed.
                # claude-opus-4-6  → claude-3-opus-20240229  ($15/$75 per million)
                # claude-haiku-4-5 → claude-3-haiku-20240307 ($0.25/$1.25 per million)
                _PRICING_MAP = {
                    "claude-opus-4-6":          "claude-3-opus-20240229",
                    "claude-opus-4":            "claude-3-opus-20240229",
                    "claude-haiku-4-5-20251001": "claude-3-haiku-20240307",
                    "claude-haiku-4-5":          "claude-3-haiku-20240307",
                    "claude-sonnet-4-5-20250929": "claude-3-sonnet-20240229",
                    "claude-sonnet-4-5":          "claude-3-sonnet-20240229",
                }
                ls_model = _PRICING_MAP.get(response.model, response.model)
                rt.extra.setdefault("metadata", {}).update({
                    "ls_model_name": ls_model,
                    "ls_provider": "anthropic",
                    "actual_model": response.model,   # preserve real name for reference
                })
                rt.extra["usage_metadata"] = {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                }
                rt.patch()

            if self.token_tracker:
                self.token_tracker.track(
                    model=response.model,
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    cache_creation_tokens=getattr(usage, 'cache_creation_input_tokens', 0),
                    cache_read_tokens=getattr(usage, 'cache_read_input_tokens', 0),
                    agent_name=self.agent_name,
                    operation=operation or 'message_create'
                )

            logger.debug(
                f"Token usage: {self.agent_name} - "
                f"input={usage.input_tokens}, output={usage.output_tokens}"
            )
        else:
            logger.warning(f"No usage data in API response for {self.agent_name}")

        return response


def create_tracked_client(agent_name: str, api_key: str | None = None) -> AnthropicClientWrapper:
    """
    Convenience function to create a tracked Anthropic client

    Args:
        agent_name: Name of the agent for tracking
        api_key: Optional API key

    Returns:
        Wrapped Anthropic client with token tracking
    """
    return AnthropicClientWrapper(agent_name=agent_name, api_key=api_key)
