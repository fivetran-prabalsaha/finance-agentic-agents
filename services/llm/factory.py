"""
LLM Provider Factory

Creates LLM provider instances based on configuration
"""

import logging

from .base import BaseLLMProvider, LLMConfig
from .base import LLMProvider as LLMProviderEnum
from .providers.anthropic_provider import AnthropicProvider
from .providers.azure_provider import AzureProvider
from .providers.cohere_provider import CohereProvider
from .providers.google_provider import GoogleProvider
from .providers.local_provider import LocalProvider
from .providers.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)


class LLMProviderFactory:
    """
    Factory for creating LLM provider instances

    Registers and instantiates provider implementations based on configuration
    """

    # Registry of available providers
    _providers: dict[str, type[BaseLLMProvider]] = {
        LLMProviderEnum.ANTHROPIC.value: AnthropicProvider,
        LLMProviderEnum.OPENAI.value: OpenAIProvider,
        LLMProviderEnum.GOOGLE.value: GoogleProvider,
        LLMProviderEnum.COHERE.value: CohereProvider,
        LLMProviderEnum.AZURE.value: AzureProvider,
        LLMProviderEnum.OLLAMA.value: LocalProvider,
        LLMProviderEnum.VLLM.value: LocalProvider,
        LLMProviderEnum.HUGGINGFACE.value: LocalProvider,
    }

    @classmethod
    def create_provider(cls, config: LLMConfig) -> BaseLLMProvider:
        """
        Create LLM provider instance from configuration

        Args:
            config: LLM configuration

        Returns:
            Instantiated provider

        Raises:
            ValueError: If provider not found or invalid
        """
        provider_name = config.provider.lower()

        if provider_name not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ValueError(
                f"Unknown LLM provider: {provider_name}. "
                f"Available providers: {available}"
            )

        provider_class = cls._providers[provider_name]

        try:
            provider = provider_class(config)
            logger.info(f"Created {provider_name} provider with model {config.model}")
            return provider

        except Exception as e:
            logger.error(f"Failed to create {provider_name} provider: {str(e)}")
            raise

    @classmethod
    def register_provider(
        cls,
        name: str,
        provider_class: type[BaseLLMProvider]
    ) -> None:
        """
        Register a custom provider

        Args:
            name: Provider name
            provider_class: Provider class (must inherit from BaseLLMProvider)
        """
        if not issubclass(provider_class, BaseLLMProvider):
            raise ValueError(
                f"Provider class must inherit from BaseLLMProvider. "
                f"Got: {provider_class}"
            )

        cls._providers[name.lower()] = provider_class
        logger.info(f"Registered custom provider: {name}")

    @classmethod
    def list_providers(cls) -> list:
        """
        List all registered providers

        Returns:
            List of provider names
        """
        return list(cls._providers.keys())

    @classmethod
    def get_provider_class(cls, provider_name: str) -> type[BaseLLMProvider] | None:
        """
        Get provider class by name

        Args:
            provider_name: Name of provider

        Returns:
            Provider class or None if not found
        """
        return cls._providers.get(provider_name.lower())


def create_llm(
    provider: str,
    model: str,
    api_key: str,
    **kwargs
) -> BaseLLMProvider:
    """
    Convenience function to create LLM provider

    Args:
        provider: Provider name (anthropic, openai, google, etc.)
        model: Model name
        api_key: API key
        **kwargs: Additional config parameters

    Returns:
        Instantiated provider

    Example:
        >>> llm = create_llm(
        ...     provider="anthropic",
        ...     model="claude-sonnet-4-5",
        ...     api_key="sk-ant-...",
        ...     temperature=0.7,
        ...     max_tokens=2048
        ... )
    """
    config = LLMConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        **kwargs
    )

    return LLMProviderFactory.create_provider(config)
