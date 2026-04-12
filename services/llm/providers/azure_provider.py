"""
Azure OpenAI Provider Implementation
"""

import logging

from ..base import LLMConfig
from .openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)


class AzureProvider(OpenAIProvider):
    """
    Azure OpenAI provider implementation

    Inherits from OpenAIProvider since Azure uses the same API
    with different authentication and endpoint
    """

    def __init__(self, config: LLMConfig):
        """
        Initialize Azure OpenAI provider

        Config should include:
        - api_key: Azure API key
        - api_base: Azure endpoint (e.g., https://your-resource.openai.azure.com/)
        - extra_params: {
            'api_version': '2024-02-01',
            'azure_deployment': 'your-deployment-name'
          }
        """
        # Azure requires api_base to be set
        if not config.api_base:
            raise ValueError("Azure provider requires api_base (Azure endpoint URL)")

        # Azure requires api_version in extra_params
        if not config.extra_params or 'api_version' not in config.extra_params:
            raise ValueError("Azure provider requires api_version in extra_params")

        # Initialize parent OpenAI provider
        super().__init__(config)

        # Override provider name
        self.provider_name = "azure"

        logger.info(f"Initialized Azure OpenAI provider with endpoint {config.api_base}")
