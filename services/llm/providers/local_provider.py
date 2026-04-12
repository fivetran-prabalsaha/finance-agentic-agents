"""
Local LLM Provider Implementation (Ollama, vLLM, etc.)
"""

import logging
import time
from typing import Any

import requests

from ..base import (
    BaseLLMProvider,
    LLMConfig,
    LLMConnectionError,
    LLMMessage,
    LLMResponse,
    LLMTimeoutError,
)

logger = logging.getLogger(__name__)


class LocalProvider(BaseLLMProvider):
    """
    Local LLM provider implementation

    Supports:
    - Ollama (http://localhost:11434)
    - vLLM (OpenAI-compatible API)
    - LM Studio
    - Other OpenAI-compatible local servers
    """

    def __init__(self, config: LLMConfig):
        """
        Initialize Local provider

        Config should include:
        - api_base: Local server endpoint (e.g., http://localhost:11434)
        - model: Model name (e.g., llama2, mistral, etc.)
        - api_key: Usually not needed for local, but can be set to "local"
        """
        if not config.api_base:
            config.api_base = "http://localhost:11434"  # Default Ollama endpoint

        if not config.api_key:
            config.api_key = "local"  # Not needed for local models

        super().__init__(config)

        self.api_base = config.api_base.rstrip('/')

        # Detect server type based on endpoint
        if 'ollama' in self.api_base or ':11434' in self.api_base:
            self.server_type = 'ollama'
        else:
            self.server_type = 'openai_compatible'

        logger.info(f"Initialized Local provider ({self.server_type}) with endpoint {self.api_base}")

    def generate(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs
    ) -> LLMResponse:
        """Generate completion using local LLM"""
        self.validate_messages(messages)

        time.time()

        if self.server_type == 'ollama':
            return self._generate_ollama(messages, temperature, max_tokens, **kwargs)
        else:
            return self._generate_openai_compatible(messages, temperature, max_tokens, **kwargs)

    def _generate_ollama(
        self,
        messages: list[LLMMessage],
        temperature: float | None,
        max_tokens: int | None,
        **kwargs
    ) -> LLMResponse:
        """Generate using Ollama API"""
        start_time = time.time()

        # Convert messages to Ollama format
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                'role': msg.role,
                'content': msg.content
            })

        payload = {
            'model': self.model_name,
            'messages': formatted_messages,
            'stream': False,
            'options': {
                'temperature': temperature if temperature is not None else self.temperature,
                'num_predict': max_tokens if max_tokens is not None else self.max_tokens
            }
        }

        try:
            response = requests.post(
                f"{self.api_base}/api/chat",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            result = response.json()

            latency_ms = (time.time() - start_time) * 1000

            # Ollama provides token counts in response
            input_tokens = result.get('prompt_eval_count', 0)
            output_tokens = result.get('eval_count', 0)

            usage = {
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': input_tokens + output_tokens
            }

            # Local models have no cost
            cost = 0.0

            return LLMResponse(
                content=result['message']['content'],
                provider=self.provider_name,
                model=self.model_name,
                finish_reason=result.get('done_reason', 'complete'),
                usage=usage,
                cost=cost,
                latency_ms=latency_ms,
                metadata={
                    'total_duration': result.get('total_duration'),
                    'load_duration': result.get('load_duration'),
                    'eval_duration': result.get('eval_duration')
                }
            )

        except requests.Timeout as e:
            logger.error(f"Ollama timeout error: {str(e)}")
            raise LLMTimeoutError(f"Request timed out: {str(e)}")
        except requests.RequestException as e:
            logger.error(f"Ollama connection error: {str(e)}")
            raise LLMConnectionError(f"Failed to connect to Ollama: {str(e)}")

    def _generate_openai_compatible(
        self,
        messages: list[LLMMessage],
        temperature: float | None,
        max_tokens: int | None,
        **kwargs
    ) -> LLMResponse:
        """Generate using OpenAI-compatible API"""
        start_time = time.time()

        formatted_messages = self.format_messages(messages)

        payload = {
            'model': self.model_name,
            'messages': formatted_messages,
            'temperature': temperature if temperature is not None else self.temperature,
            'max_tokens': max_tokens if max_tokens is not None else self.max_tokens
        }

        headers = {'Content-Type': 'application/json'}
        if self.config.api_key and self.config.api_key != "local":
            headers['Authorization'] = f'Bearer {self.config.api_key}'

        try:
            response = requests.post(
                f"{self.api_base}/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()

            result = response.json()

            latency_ms = (time.time() - start_time) * 1000

            usage = result.get('usage', {})
            input_tokens = usage.get('prompt_tokens', 0)
            output_tokens = usage.get('completion_tokens', 0)

            return LLMResponse(
                content=result['choices'][0]['message']['content'],
                provider=self.provider_name,
                model=self.model_name,
                finish_reason=result['choices'][0].get('finish_reason', 'complete'),
                usage={
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'total_tokens': input_tokens + output_tokens
                },
                cost=0.0,  # Local models have no cost
                latency_ms=latency_ms,
                metadata={'id': result.get('id')}
            )

        except requests.RequestException as e:
            logger.error(f"Local API connection error: {str(e)}")
            raise LLMConnectionError(f"Failed to connect to local API: {str(e)}")

    def generate_stream(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs
    ):
        """Generate completion with streaming"""
        formatted_messages = self.format_messages(messages)

        if self.server_type == 'ollama':
            payload = {
                'model': self.model_name,
                'messages': formatted_messages,
                'stream': True,
                'options': {
                    'temperature': temperature if temperature is not None else self.temperature,
                    'num_predict': max_tokens if max_tokens is not None else self.max_tokens
                }
            }

            try:
                with requests.post(
                    f"{self.api_base}/api/chat",
                    json=payload,
                    stream=True,
                    timeout=self.timeout
                ) as response:
                    response.raise_for_status()

                    for line in response.iter_lines():
                        if line:
                            import json
                            chunk = json.loads(line)
                            if 'message' in chunk and 'content' in chunk['message']:
                                yield chunk['message']['content']

            except Exception as e:
                logger.error(f"Ollama streaming error: {str(e)}")
                raise

    def count_tokens(self, text: str) -> int:
        """Count tokens (approximation for local models)"""
        # Rough approximation
        return len(text) // 4

    def get_model_info(self) -> dict[str, Any]:
        """Get model information"""
        return {
            'provider': self.provider_name,
            'model': self.model_name,
            'context_length': 4096,  # Default, varies by model
            'pricing': {'input_per_million': 0.0, 'output_per_million': 0.0},
            'supports_streaming': True,
            'supports_functions': False,
            'max_tokens': self.max_tokens,
            'server_type': self.server_type,
            'endpoint': self.api_base
        }

    def test_connection(self) -> bool:
        """Test local LLM connection"""
        try:
            test_messages = [
                LLMMessage(role='user', content='Hello')
            ]

            self.generate(
                messages=test_messages,
                max_tokens=10
            )

            logger.info(f"Local {self.server_type} connection test successful")
            return True

        except Exception as e:
            logger.error(f"Local connection test failed: {str(e)}")
            return False
