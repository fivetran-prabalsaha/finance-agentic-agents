"""
Google Gemini Provider Implementation
"""

import logging
import time
from typing import Any

try:
    import google.generativeai as genai
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Google AI package not installed. Run: pip install google-generativeai")

from ..base import (
    BaseLLMProvider,
    LLMAuthenticationError,
    LLMConfig,
    LLMConnectionError,
    LLMMessage,
    LLMResponse,
)

logger = logging.getLogger(__name__)


class GoogleProvider(BaseLLMProvider):
    """Google Gemini provider implementation"""

    MODEL_PRICING = {
        'gemini-pro': {'input_per_million': 0.50, 'output_per_million': 1.50},
        'gemini-pro-vision': {'input_per_million': 0.50, 'output_per_million': 1.50},
        'gemini-1.5-pro': {'input_per_million': 3.50, 'output_per_million': 10.50},
        'gemini-1.5-flash': {'input_per_million': 0.35, 'output_per_million': 1.05},
    }

    MODEL_CONTEXT = {
        'gemini-pro': 30720,
        'gemini-pro-vision': 16384,
        'gemini-1.5-pro': 1000000,
        'gemini-1.5-flash': 1000000,
    }

    def __init__(self, config: LLMConfig):
        """Initialize Google provider"""
        if not GOOGLE_AVAILABLE:
            raise ImportError("Google AI package not installed. Run: pip install google-generativeai")

        super().__init__(config)

        genai.configure(api_key=config.api_key)
        self.model = genai.GenerativeModel(self.model_name)

    def generate(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs
    ) -> LLMResponse:
        """Generate completion using Gemini"""
        self.validate_messages(messages)

        start_time = time.time()

        # Convert messages to Gemini format
        prompt_parts = []
        for msg in messages:
            if msg.role == 'system':
                prompt_parts.insert(0, f"System: {msg.content}\n")
            elif msg.role == 'user':
                prompt_parts.append(f"User: {msg.content}")
            elif msg.role == 'assistant':
                prompt_parts.append(f"Assistant: {msg.content}")

        prompt = "\n".join(prompt_parts)

        # Generation config
        generation_config = {
            'temperature': temperature if temperature is not None else self.temperature,
            'max_output_tokens': max_tokens if max_tokens is not None else self.max_tokens,
        }

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )

            latency_ms = (time.time() - start_time) * 1000

            # Approximate token counts
            input_tokens = self.count_tokens(prompt)
            output_tokens = self.count_tokens(response.text)

            usage = {
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': input_tokens + output_tokens
            }

            cost = self.calculate_cost(usage['input_tokens'], usage['output_tokens'])

            return LLMResponse(
                content=response.text,
                provider=self.provider_name,
                model=self.model_name,
                finish_reason="complete",
                usage=usage,
                cost=cost,
                latency_ms=latency_ms,
                metadata={}
            )

        except Exception as e:
            logger.error(f"Google API error: {str(e)}")
            if "authentication" in str(e).lower() or "api key" in str(e).lower():
                raise LLMAuthenticationError(f"Authentication failed: {str(e)}")
            raise LLMConnectionError(f"Google API error: {str(e)}")

    def generate_stream(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs
    ):
        """Generate completion with streaming"""
        # Convert messages to prompt
        prompt_parts = []
        for msg in messages:
            if msg.role != 'system':
                prompt_parts.append(f"{msg.role.capitalize()}: {msg.content}")

        prompt = "\n".join(prompt_parts)

        generation_config = {
            'temperature': temperature if temperature is not None else self.temperature,
            'max_output_tokens': max_tokens if max_tokens is not None else self.max_tokens,
        }

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config,
                stream=True
            )

            for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"Google streaming error: {str(e)}")
            raise

    def count_tokens(self, text: str) -> int:
        """Count tokens (approximation)"""
        return len(text) // 4

    def get_model_info(self) -> dict[str, Any]:
        """Get model information"""
        return {
            'provider': self.provider_name,
            'model': self.model_name,
            'context_length': self.MODEL_CONTEXT.get(self.model_name, 30720),
            'pricing': self.MODEL_PRICING.get(self.model_name, {
                'input_per_million': 0.50,
                'output_per_million': 1.50
            }),
            'supports_streaming': True,
            'supports_functions': False,
            'supports_vision': 'vision' in self.model_name.lower(),
            'max_tokens': self.max_tokens
        }

    def test_connection(self) -> bool:
        """Test Google API connection"""
        try:
            test_messages = [
                LLMMessage(role='user', content='Hello')
            ]

            self.generate(
                messages=test_messages,
                max_tokens=10
            )

            logger.info("Google connection test successful")
            return True

        except Exception as e:
            logger.error(f"Google connection test failed: {str(e)}")
            return False
