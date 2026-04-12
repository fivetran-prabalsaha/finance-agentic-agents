"""
LLM Abstraction Layer

Provides a unified interface for interacting with different LLM providers
"""

from .base import (
    BaseLLMProvider,
    LLMAuthenticationError,
    LLMConfig,
    LLMConnectionError,
    LLMError,
    LLMInvalidRequestError,
    LLMMessage,
    LLMProvider,
    LLMRateLimitError,
    LLMResponse,
    LLMTimeoutError,
)
from .config_manager import ConfigEncryption, LLMConfigManager, get_llm_from_config
from .factory import LLMProviderFactory, create_llm
from .providers import (
    AnthropicProvider,
    AzureProvider,
    CohereProvider,
    GoogleProvider,
    LocalProvider,
    OpenAIProvider,
)

__all__ = [
    # Base classes
    'BaseLLMProvider',
    'LLMMessage',
    'LLMResponse',
    'LLMConfig',
    'LLMProvider',

    # Errors
    'LLMError',
    'LLMConnectionError',
    'LLMAuthenticationError',
    'LLMRateLimitError',
    'LLMTimeoutError',
    'LLMInvalidRequestError',

    # Factory
    'LLMProviderFactory',
    'create_llm',

    # Config management
    'LLMConfigManager',
    'ConfigEncryption',
    'get_llm_from_config',

    # Providers
    'AnthropicProvider',
    'OpenAIProvider',
    'GoogleProvider',
    'CohereProvider',
    'AzureProvider',
    'LocalProvider',
]

__version__ = '1.0.0'
