"""
Anthropic Claude Provider Implementation
"""

import logging
import time
from typing import Any

from anthropic import Anthropic, APIConnectionError, APIError, APITimeoutError, RateLimitError
from langsmith import traceable

from ..base import (
    BaseLLMProvider,
    LLMAuthenticationError,
    LLMConfig,
    LLMConnectionError,
    LLMMessage,
    LLMRateLimitError,
    LLMResponse,
    LLMTimeoutError,
)

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider implementation"""

    # Model pricing (per million tokens)
    MODEL_PRICING = {
        'claude-opus-4': {'input_per_million': 15.00, 'output_per_million': 75.00},
        'claude-opus-4-6': {'input_per_million': 15.00, 'output_per_million': 75.00},
        'claude-sonnet-4': {'input_per_million': 3.00, 'output_per_million': 15.00},
        'claude-sonnet-4-5': {'input_per_million': 3.00, 'output_per_million': 15.00},
        'claude-sonnet-4-5-20250929': {'input_per_million': 3.00, 'output_per_million': 15.00},
        'claude-haiku-4': {'input_per_million': 0.80, 'output_per_million': 4.00},
        'claude-haiku-4-5': {'input_per_million': 0.80, 'output_per_million': 4.00},
        'claude-3-opus-20240229': {'input_per_million': 15.00, 'output_per_million': 75.00},
        'claude-3-sonnet-20240229': {'input_per_million': 3.00, 'output_per_million': 15.00},
        'claude-3-haiku-20240307': {'input_per_million': 0.25, 'output_per_million': 1.25},
    }

    # Model context windows
    MODEL_CONTEXT = {
        'claude-opus-4': 200000,
        'claude-opus-4-6': 200000,
        'claude-sonnet-4': 200000,
        'claude-sonnet-4-5': 200000,
        'claude-sonnet-4-5-20250929': 200000,
        'claude-haiku-4': 200000,
        'claude-haiku-4-5': 200000,
        'claude-3-opus-20240229': 200000,
        'claude-3-sonnet-20240229': 200000,
        'claude-3-haiku-20240307': 200000,
    }

    def __init__(self, config: LLMConfig):
        """Initialize Anthropic provider"""
        super().__init__(config)

        self.client = Anthropic(
            api_key=config.api_key,
            timeout=config.timeout,
            max_retries=config.max_retries
        )

    @traceable(run_type="llm", name="anthropic_provider.generate")
    def generate(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs
    ) -> LLMResponse:
        """Generate completion using Claude"""
        self.validate_messages(messages)

        start_time = time.time()

        # Extract system message if present
        system_message = None
        user_messages = []

        for msg in messages:
            if msg.role == 'system':
                system_message = msg.content
            else:
                user_messages.append({
                    'role': msg.role,
                    'content': msg.content
                })

        # Prepare request parameters
        params = {
            'model': self.model_name,
            'messages': user_messages,
            'temperature': temperature if temperature is not None else self.temperature,
            'max_tokens': max_tokens if max_tokens is not None else self.max_tokens,
        }

        if system_message:
            params['system'] = system_message

        # Add any extra parameters
        if self.config.extra_params:
            params.update(self.config.extra_params)

        # Override with kwargs
        params.update(kwargs)

        try:
            response = self.client.messages.create(**params)

            latency_ms = (time.time() - start_time) * 1000

            # Extract usage
            usage = {
                'input_tokens': response.usage.input_tokens,
                'output_tokens': response.usage.output_tokens,
                'total_tokens': response.usage.input_tokens + response.usage.output_tokens
            }

            # Calculate cost
            cost = self.calculate_cost(usage['input_tokens'], usage['output_tokens'])

            # Extract content
            content = ""
            if response.content:
                # Handle both text and other content types
                for block in response.content:
                    if hasattr(block, 'text'):
                        content += block.text
                    elif isinstance(block, dict) and 'text' in block:
                        content += block['text']

            return LLMResponse(
                content=content,
                provider=self.provider_name,
                model=response.model,
                finish_reason=response.stop_reason or "complete",
                usage=usage,
                cost=cost,
                latency_ms=latency_ms,
                metadata={
                    'id': response.id,
                    'type': response.type,
                    'role': response.role
                }
            )

        except APIConnectionError as e:
            logger.error(f"Anthropic connection error: {str(e)}")
            raise LLMConnectionError(f"Failed to connect to Anthropic: {str(e)}")
        except RateLimitError as e:
            logger.error(f"Anthropic rate limit error: {str(e)}")
            raise LLMRateLimitError(f"Rate limit exceeded: {str(e)}")
        except APITimeoutError as e:
            logger.error(f"Anthropic timeout error: {str(e)}")
            raise LLMTimeoutError(f"Request timed out: {str(e)}")
        except APIError as e:
            logger.error(f"Anthropic API error: {str(e)}")
            if "authentication" in str(e).lower():
                raise LLMAuthenticationError(f"Authentication failed: {str(e)}")
            raise

    @traceable(run_type="llm", name="anthropic_provider.stream")
    def generate_stream(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs
    ):
        """Generate completion with streaming"""
        self.validate_messages(messages)

        # Extract system message
        system_message = None
        user_messages = []

        for msg in messages:
            if msg.role == 'system':
                system_message = msg.content
            else:
                user_messages.append({
                    'role': msg.role,
                    'content': msg.content
                })

        # Prepare request parameters
        params = {
            'model': self.model_name,
            'messages': user_messages,
            'temperature': temperature if temperature is not None else self.temperature,
            'max_tokens': max_tokens if max_tokens is not None else self.max_tokens,
            'stream': True
        }

        if system_message:
            params['system'] = system_message

        if self.config.extra_params:
            params.update(self.config.extra_params)

        params.update(kwargs)

        try:
            with self.client.messages.stream(**params) as stream:
                yield from stream.text_stream

        except Exception as e:
            logger.error(f"Anthropic streaming error: {str(e)}")
            raise

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text

        Note: Anthropic doesn't provide a public tokenizer,
        so we use an approximation (4 chars ≈ 1 token)
        """
        # Rough approximation: 4 characters per token
        return len(text) // 4

    def get_model_info(self) -> dict[str, Any]:
        """Get model information"""
        return {
            'provider': self.provider_name,
            'model': self.model_name,
            'context_length': self.MODEL_CONTEXT.get(self.model_name, 200000),
            'pricing': self.MODEL_PRICING.get(self.model_name, {
                'input_per_million': 3.00,
                'output_per_million': 15.00
            }),
            'supports_streaming': True,
            'supports_functions': True,
            'supports_vision': 'opus' in self.model_name.lower() or 'sonnet' in self.model_name.lower(),
            'max_tokens': self.max_tokens
        }

    def test_connection(self) -> bool:
        """Test Anthropic API connection"""
        try:
            # Simple test message
            test_messages = [
                LLMMessage(role='user', content='Hello')
            ]

            self.generate(
                messages=test_messages,
                max_tokens=10
            )

            logger.info("Anthropic connection test successful")
            return True

        except Exception as e:
            logger.error(f"Anthropic connection test failed: {str(e)}")
            return False
