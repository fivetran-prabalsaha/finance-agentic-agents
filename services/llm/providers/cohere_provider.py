"""
Cohere Provider Implementation
"""

import logging
import time
from typing import Any

try:
    import cohere
    COHERE_AVAILABLE = True
except ImportError:
    COHERE_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Cohere package not installed. Run: pip install cohere")

from ..base import BaseLLMProvider, LLMConfig, LLMConnectionError, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class CohereProvider(BaseLLMProvider):
    """Cohere provider implementation"""

    MODEL_PRICING = {
        'command': {'input_per_million': 1.00, 'output_per_million': 2.00},
        'command-light': {'input_per_million': 0.30, 'output_per_million': 0.60},
        'command-r': {'input_per_million': 0.50, 'output_per_million': 1.50},
        'command-r-plus': {'input_per_million': 3.00, 'output_per_million': 15.00},
    }

    def __init__(self, config: LLMConfig):
        """Initialize Cohere provider"""
        if not COHERE_AVAILABLE:
            raise ImportError("Cohere package not installed. Run: pip install cohere")

        super().__init__(config)
        self.client = cohere.Client(api_key=config.api_key)

    def generate(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs
    ) -> LLMResponse:
        """Generate completion using Cohere"""
        self.validate_messages(messages)

        start_time = time.time()

        # Convert messages to Cohere chat format
        chat_history = []
        prompt = ""

        for msg in messages:
            if msg.role == 'system':
                prompt = msg.content + "\n\n"
            elif msg.role == 'user':
                if not prompt:
                    prompt = msg.content
                else:
                    chat_history.append({"role": "USER", "message": msg.content})
            elif msg.role == 'assistant':
                chat_history.append({"role": "CHATBOT", "message": msg.content})

        try:
            response = self.client.chat(
                message=prompt if not chat_history else chat_history[-1]["message"],
                chat_history=chat_history[:-1] if chat_history else [],
                model=self.model_name,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens if max_tokens is not None else self.max_tokens
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
                metadata={'generation_id': response.generation_id}
            )

        except Exception as e:
            logger.error(f"Cohere API error: {str(e)}")
            raise LLMConnectionError(f"Cohere API error: {str(e)}")

    def generate_stream(self, messages: list[LLMMessage], temperature: float | None = None, max_tokens: int | None = None, **kwargs):
        """Generate completion with streaming"""
        # Simplified - implement as needed
        response = self.generate(messages, temperature, max_tokens, **kwargs)
        yield response.content

    def count_tokens(self, text: str) -> int:
        """Count tokens (approximation)"""
        return len(text) // 4

    def get_model_info(self) -> dict[str, Any]:
        """Get model information"""
        return {
            'provider': self.provider_name,
            'model': self.model_name,
            'context_length': 128000,
            'pricing': self.MODEL_PRICING.get(self.model_name, {'input_per_million': 1.00, 'output_per_million': 2.00}),
            'supports_streaming': True,
            'supports_functions': False,
            'max_tokens': self.max_tokens
        }

    def test_connection(self) -> bool:
        """Test Cohere API connection"""
        try:
            test_messages = [LLMMessage(role='user', content='Hello')]
            self.generate(messages=test_messages, max_tokens=10)
            logger.info("Cohere connection test successful")
            return True
        except Exception as e:
            logger.error(f"Cohere connection test failed: {str(e)}")
            return False
