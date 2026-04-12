"""
Token Usage and Cost Tracking Utility

Tracks API token usage and calculates costs for Claude models
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


# Claude API Pricing (as of 2026-02)
# https://www.anthropic.com/pricing
PRICING = {
    'claude-opus-4.6': {
        'input': 15.00 / 1_000_000,   # $15 per million input tokens
        'output': 75.00 / 1_000_000,  # $75 per million output tokens
        'cache_write': 18.75 / 1_000_000,  # $18.75 per million cache write tokens
        'cache_read': 1.50 / 1_000_000,    # $1.50 per million cache read tokens
    },
    'claude-sonnet-4.5': {
        'input': 3.00 / 1_000_000,    # $3 per million input tokens
        'output': 15.00 / 1_000_000,  # $15 per million output tokens
        'cache_write': 3.75 / 1_000_000,   # $3.75 per million cache write tokens
        'cache_read': 0.30 / 1_000_000,    # $0.30 per million cache read tokens
    },
    'claude-haiku-4.5': {
        'input': 1.00 / 1_000_000,    # $1 per million input tokens
        'output': 5.00 / 1_000_000,   # $5 per million output tokens
        'cache_write': 1.25 / 1_000_000,   # $1.25 per million cache write tokens
        'cache_read': 0.10 / 1_000_000,    # $0.10 per million cache read tokens
    },
    # Legacy model names
    'claude-opus-4': {
        'input': 15.00 / 1_000_000,
        'output': 75.00 / 1_000_000,
        'cache_write': 18.75 / 1_000_000,
        'cache_read': 1.50 / 1_000_000,
    },
    'claude-sonnet-4': {
        'input': 3.00 / 1_000_000,
        'output': 15.00 / 1_000_000,
        'cache_write': 3.75 / 1_000_000,
        'cache_read': 0.30 / 1_000_000,
    },
}


@dataclass
class TokenUsage:
    """Token usage for a single API call"""
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    agent_name: str | None = None
    operation: str | None = None

    @property
    def total_tokens(self) -> int:
        """Total tokens used"""
        return (
            self.input_tokens +
            self.output_tokens +
            self.cache_creation_tokens +
            self.cache_read_tokens
        )

    @property
    def cost(self) -> float:
        """Calculate cost for this usage"""
        return calculate_cost(
            model=self.model,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            cache_creation_tokens=self.cache_creation_tokens,
            cache_read_tokens=self.cache_read_tokens
        )

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'model': self.model,
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'cache_creation_tokens': self.cache_creation_tokens,
            'cache_read_tokens': self.cache_read_tokens,
            'total_tokens': self.total_tokens,
            'cost': self.cost,
            'agent_name': self.agent_name,
            'operation': self.operation,
            'timestamp': self.timestamp.isoformat()
        }


class TokenTracker:
    """Track token usage and costs across multiple API calls"""

    def __init__(self):
        self.usages: list[TokenUsage] = []
        self._agent_totals: dict[str, dict] = {}

    def track(
        self,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
        agent_name: str | None = None,
        operation: str | None = None
    ) -> TokenUsage:
        """
        Track a single API call

        Args:
            model: Claude model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cache_creation_tokens: Tokens written to cache
            cache_read_tokens: Tokens read from cache
            agent_name: Name of the agent making the call
            operation: Description of the operation

        Returns:
            TokenUsage object
        """
        usage = TokenUsage(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_tokens=cache_creation_tokens,
            cache_read_tokens=cache_read_tokens,
            agent_name=agent_name,
            operation=operation
        )

        self.usages.append(usage)

        # Update agent totals
        if agent_name:
            if agent_name not in self._agent_totals:
                self._agent_totals[agent_name] = {
                    'calls': 0,
                    'input_tokens': 0,
                    'output_tokens': 0,
                    'cache_creation_tokens': 0,
                    'cache_read_tokens': 0,
                    'total_tokens': 0,
                    'cost': 0.0
                }

            self._agent_totals[agent_name]['calls'] += 1
            self._agent_totals[agent_name]['input_tokens'] += input_tokens
            self._agent_totals[agent_name]['output_tokens'] += output_tokens
            self._agent_totals[agent_name]['cache_creation_tokens'] += cache_creation_tokens
            self._agent_totals[agent_name]['cache_read_tokens'] += cache_read_tokens
            self._agent_totals[agent_name]['total_tokens'] += usage.total_tokens
            self._agent_totals[agent_name]['cost'] += usage.cost

        logger.debug(
            f"Token usage tracked: {agent_name or 'unknown'} - "
            f"{usage.total_tokens} tokens, ${usage.cost:.6f}"
        )

        return usage

    def track_from_response(
        self,
        response: dict,
        agent_name: str | None = None,
        operation: str | None = None
    ) -> TokenUsage | None:
        """
        Track usage from Claude API response

        Args:
            response: Claude API response dictionary
            agent_name: Name of the agent
            operation: Description of operation

        Returns:
            TokenUsage object or None if no usage data
        """
        # Extract usage from response
        usage_data = response.get('usage', {})

        if not usage_data:
            logger.warning("No usage data in API response")
            return None

        model = response.get('model', 'unknown')

        return self.track(
            model=model,
            input_tokens=usage_data.get('input_tokens', 0),
            output_tokens=usage_data.get('output_tokens', 0),
            cache_creation_tokens=usage_data.get('cache_creation_input_tokens', 0),
            cache_read_tokens=usage_data.get('cache_read_input_tokens', 0),
            agent_name=agent_name,
            operation=operation
        )

    @property
    def total_tokens(self) -> int:
        """Total tokens across all calls"""
        return sum(u.total_tokens for u in self.usages)

    @property
    def total_cost(self) -> float:
        """Total cost across all calls"""
        return sum(u.cost for u in self.usages)

    @property
    def total_calls(self) -> int:
        """Total number of API calls"""
        return len(self.usages)

    def get_agent_stats(self, agent_name: str) -> dict | None:
        """Get statistics for a specific agent"""
        return self._agent_totals.get(agent_name)

    def get_all_agent_stats(self) -> dict[str, dict]:
        """Get statistics for all agents"""
        return self._agent_totals.copy()

    def get_summary(self) -> dict:
        """Get overall summary"""
        return {
            'total_calls': self.total_calls,
            'total_tokens': self.total_tokens,
            'total_cost': self.total_cost,
            'agents': self._agent_totals,
            'average_tokens_per_call': (
                self.total_tokens / self.total_calls if self.total_calls > 0 else 0
            ),
            'average_cost_per_call': (
                self.total_cost / self.total_calls if self.total_calls > 0 else 0
            )
        }

    def print_summary(self):
        """Print formatted summary"""
        summary = self.get_summary()

        print("\n" + "="*80)
        print("  TOKEN USAGE & COST SUMMARY")
        print("="*80)

        print("\n📊 Overall Statistics:")
        print(f"   Total API Calls:       {summary['total_calls']}")
        print(f"   Total Tokens Used:     {summary['total_tokens']:,}")
        print(f"   Total Cost:            ${summary['total_cost']:.4f}")
        print(f"   Avg Tokens/Call:       {summary['average_tokens_per_call']:.0f}")
        print(f"   Avg Cost/Call:         ${summary['average_cost_per_call']:.4f}")

        if summary['agents']:
            print("\n🤖 Per-Agent Breakdown:")
            print(f"   {'Agent':<25} {'Calls':<8} {'Tokens':<12} {'Cost':<12}")
            print(f"   {'-'*25} {'-'*8} {'-'*12} {'-'*12}")

            # Sort by cost descending
            sorted_agents = sorted(
                summary['agents'].items(),
                key=lambda x: x[1]['cost'],
                reverse=True
            )

            for agent_name, stats in sorted_agents:
                print(
                    f"   {agent_name:<25} "
                    f"{stats['calls']:<8} "
                    f"{stats['total_tokens']:<12,} "
                    f"${stats['cost']:<11.4f}"
                )

        print("\n" + "="*80)

    def reset(self):
        """Reset all tracking data"""
        self.usages.clear()
        self._agent_totals.clear()


def calculate_cost(
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0
) -> float:
    """
    Calculate cost for token usage

    Args:
        model: Claude model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cache_creation_tokens: Cache write tokens
        cache_read_tokens: Cache read tokens

    Returns:
        Cost in USD
    """
    # Get pricing for model
    pricing = PRICING.get(model)

    if not pricing:
        logger.warning(f"Unknown model: {model}, using Sonnet pricing")
        pricing = PRICING['claude-sonnet-4.5']

    cost = (
        (input_tokens * pricing['input']) +
        (output_tokens * pricing['output']) +
        (cache_creation_tokens * pricing['cache_write']) +
        (cache_read_tokens * pricing['cache_read'])
    )

    return cost


def format_tokens(tokens: int) -> str:
    """Format token count with thousands separator"""
    return f"{tokens:,}"


def format_cost(cost: float) -> str:
    """Format cost as USD with appropriate precision"""
    if cost < 0.01:
        return f"${cost:.6f}"
    elif cost < 1.0:
        return f"${cost:.4f}"
    else:
        return f"${cost:.2f}"


# Global tracker instance
_global_tracker = TokenTracker()


def get_global_tracker() -> TokenTracker:
    """Get the global token tracker instance"""
    return _global_tracker


def reset_global_tracker():
    """Reset the global tracker"""
    _global_tracker.reset()
