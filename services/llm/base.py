"""
Abstract Base Class for LLM Providers

Defines a unified interface for interacting with different LLM providers
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class LLMProvider(StrEnum):
    """Supported LLM providers"""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    COHERE = "cohere"
    AZURE = "azure"
    OLLAMA = "ollama"
    VLLM = "vllm"
    HUGGINGFACE = "huggingface"


@dataclass
class LLMMessage:
    """Unified message format"""
    role: str  # system, user, assistant
    content: str
    name: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class LLMResponse:
    """Unified response format"""
    content: str
    provider: str
    model: str
    finish_reason: str
    usage: dict[str, int]  # {input_tokens, output_tokens, total_tokens}
    cost: float | None = None
    latency_ms: float | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class LLMConfig:
    """LLM configuration"""
    provider: str
    model: str
    api_key: str
    api_base: str | None = None
    temperature: float = 0.0
    max_tokens: int = 4096
    timeout: int = 120
    max_retries: int = 3
    streaming: bool = False
    extra_params: dict[str, Any] | None = None


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers

    All concrete provider implementations must inherit from this class
    and implement the required methods.
    """

    def __init__(self, config: LLMConfig):
        """
        Initialize LLM provider

        Args:
            config: LLM configuration
        """
        self.config = config
        self.provider_name = config.provider
        self.model_name = config.model
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens
        self.timeout = config.timeout
        self.max_retries = config.max_retries

        logger.info(f"Initialized {self.provider_name} provider with model {self.model_name}")

    @abstractmethod
    def generate(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate completion from messages

        Args:
            messages: List of messages in conversation
            temperature: Sampling temperature (overrides config)
            max_tokens: Maximum tokens to generate (overrides config)
            **kwargs: Provider-specific parameters

        Returns:
            LLMResponse with generated content and metadata
        """
        pass

    @abstractmethod
    def generate_stream(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs
    ):
        """
        Generate completion with streaming

        Args:
            messages: List of messages in conversation
            temperature: Sampling temperature (overrides config)
            max_tokens: Maximum tokens to generate (overrides config)
            **kwargs: Provider-specific parameters

        Yields:
            Chunks of generated text
        """
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text

        Args:
            text: Input text

        Returns:
            Number of tokens
        """
        pass

    @abstractmethod
    def get_model_info(self) -> dict[str, Any]:
        """
        Get model information

        Returns:
            Dict with model details (context_length, pricing, etc.)
        """
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test provider connection

        Returns:
            True if connection successful
        """
        pass

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost for token usage

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        model_info = self.get_model_info()
        pricing = model_info.get('pricing', {})

        input_cost = (input_tokens / 1_000_000) * pricing.get('input_per_million', 0)
        output_cost = (output_tokens / 1_000_000) * pricing.get('output_per_million', 0)

        return input_cost + output_cost

    def format_messages(self, messages: list[LLMMessage]) -> list[dict[str, str]]:
        """
        Format messages to standard dict format

        Args:
            messages: List of LLMMessage objects

        Returns:
            List of message dicts
        """
        return [
            {
                'role': msg.role,
                'content': msg.content,
                **({'name': msg.name} if msg.name else {})
            }
            for msg in messages
        ]

    def validate_messages(self, messages: list[LLMMessage]) -> None:
        """
        Validate message format

        Args:
            messages: List of messages to validate

        Raises:
            ValueError: If messages are invalid
        """
        if not messages:
            raise ValueError("Messages list cannot be empty")

        valid_roles = {'system', 'user', 'assistant'}
        for msg in messages:
            if msg.role not in valid_roles:
                raise ValueError(f"Invalid role: {msg.role}. Must be one of {valid_roles}")
            if not msg.content:
                raise ValueError("Message content cannot be empty")

    def get_provider_name(self) -> str:
        """Get provider name"""
        return self.provider_name

    def get_model_name(self) -> str:
        """Get model name"""
        return self.model_name

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(provider='{self.provider_name}', model='{self.model_name}')>"


class LLMError(Exception):
    """Base exception for LLM errors"""
    pass


class LLMConnectionError(LLMError):
    """Connection error"""
    pass


class LLMAuthenticationError(LLMError):
    """Authentication error"""
    pass


class LLMRateLimitError(LLMError):
    """Rate limit error"""
    pass


class LLMTimeoutError(LLMError):
    """Timeout error"""
    pass


class LLMInvalidRequestError(LLMError):
    """Invalid request error"""
    pass
