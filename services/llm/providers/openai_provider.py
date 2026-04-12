"""
OpenAI Provider Implementation
"""

import logging
import time
from typing import Any

try:
    import tiktoken
    from openai import APIConnectionError, APIError, APITimeoutError, OpenAI, RateLimitError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("OpenAI package not installed. Run: pip install openai tiktoken")

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


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider implementation"""

    # Model pricing (per million tokens)
    MODEL_PRICING = {
        'gpt-4': {'input_per_million': 30.00, 'output_per_million': 60.00},
        'gpt-4-turbo': {'input_per_million': 10.00, 'output_per_million': 30.00},
        'gpt-4-turbo-2024-04-09': {'input_per_million': 10.00, 'output_per_million': 30.00},
        'gpt-4o': {'input_per_million': 5.00, 'output_per_million': 15.00},
        'gpt-4o-mini': {'input_per_million': 0.15, 'output_per_million': 0.60},
        'gpt-3.5-turbo': {'input_per_million': 0.50, 'output_per_million': 1.50},
        'gpt-3.5-turbo-16k': {'input_per_million': 3.00, 'output_per_million': 4.00},
    }

    # Model context windows
    MODEL_CONTEXT = {
        'gpt-4': 8192,
        'gpt-4-turbo': 128000,
        'gpt-4-turbo-2024-04-09': 128000,
        'gpt-4o': 128000,
        'gpt-4o-mini': 128000,
        'gpt-3.5-turbo': 4096,
        'gpt-3.5-turbo-16k': 16384,
    }

    def __init__(self, config: LLMConfig):
        """Initialize OpenAI provider"""
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI package not installed. Run: pip install openai tiktoken")

        super().__init__(config)

        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.api_base,
            timeout=config.timeout,
            max_retries=config.max_retries
        )

        # Initialize tokenizer for the model
        try:
            self.tokenizer = tiktoken.encoding_for_model(self.model_name)
        except KeyError:
            # Fallback to cl100k_base for unknown models
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def generate(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs
    ) -> LLMResponse:
        """Generate completion using OpenAI"""
        self.validate_messages(messages)

        start_time = time.time()

        # Format messages
        formatted_messages = self.format_messages(messages)

        # Prepare request parameters
        params = {
            'model': self.model_name,
            'messages': formatted_messages,
            'temperature': temperature if temperature is not None else self.temperature,
            'max_tokens': max_tokens if max_tokens is not None else self.max_tokens,
        }

        # Add any extra parameters
        if self.config.extra_params:
            params.update(self.config.extra_params)

        # Override with kwargs
        params.update(kwargs)

        try:
            response = self.client.chat.completions.create(**params)

            latency_ms = (time.time() - start_time) * 1000

            # Extract usage
            usage = {
                'input_tokens': response.usage.prompt_tokens,
                'output_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            }

            # Calculate cost
            cost = self.calculate_cost(usage['input_tokens'], usage['output_tokens'])

            # Extract content
            content = response.choices[0].message.content or ""

            return LLMResponse(
                content=content,
                provider=self.provider_name,
                model=response.model,
                finish_reason=response.choices[0].finish_reason,
                usage=usage,
                cost=cost,
                latency_ms=latency_ms,
                metadata={
                    'id': response.id,
                    'created': response.created,
                    'system_fingerprint': response.system_fingerprint
                }
            )

        except APIConnectionError as e:
            logger.error(f"OpenAI connection error: {str(e)}")
            raise LLMConnectionError(f"Failed to connect to OpenAI: {str(e)}")
        except RateLimitError as e:
            logger.error(f"OpenAI rate limit error: {str(e)}")
            raise LLMRateLimitError(f"Rate limit exceeded: {str(e)}")
        except APITimeoutError as e:
            logger.error(f"OpenAI timeout error: {str(e)}")
            raise LLMTimeoutError(f"Request timed out: {str(e)}")
        except APIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            if "authentication" in str(e).lower() or "api key" in str(e).lower():
                raise LLMAuthenticationError(f"Authentication failed: {str(e)}")
            raise

    def generate_stream(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs
    ):
        """Generate completion with streaming"""
        self.validate_messages(messages)

        formatted_messages = self.format_messages(messages)

        params = {
            'model': self.model_name,
            'messages': formatted_messages,
            'temperature': temperature if temperature is not None else self.temperature,
            'max_tokens': max_tokens if max_tokens is not None else self.max_tokens,
            'stream': True
        }

        if self.config.extra_params:
            params.update(self.config.extra_params)

        params.update(kwargs)

        try:
            stream = self.client.chat.completions.create(**params)

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"OpenAI streaming error: {str(e)}")
            raise

    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken"""
        try:
            return len(self.tokenizer.encode(text))
        except Exception as e:
            logger.warning(f"Token counting failed: {str(e)}. Using approximation.")
            # Fallback approximation
            return len(text) // 4

    def get_model_info(self) -> dict[str, Any]:
        """Get model information"""
        return {
            'provider': self.provider_name,
            'model': self.model_name,
            'context_length': self.MODEL_CONTEXT.get(self.model_name, 4096),
            'pricing': self.MODEL_PRICING.get(self.model_name, {
                'input_per_million': 5.00,
                'output_per_million': 15.00
            }),
            'supports_streaming': True,
            'supports_functions': True,
            'supports_vision': 'gpt-4' in self.model_name.lower() and 'vision' in self.model_name.lower() or 'gpt-4o' in self.model_name.lower(),
            'max_tokens': self.max_tokens
        }

    def test_connection(self) -> bool:
        """Test OpenAI API connection"""
        try:
            test_messages = [
                LLMMessage(role='user', content='Hello')
            ]

            self.generate(
                messages=test_messages,
                max_tokens=10
            )

            logger.info("OpenAI connection test successful")
            return True

        except Exception as e:
            logger.error(f"OpenAI connection test failed: {str(e)}")
            return False
