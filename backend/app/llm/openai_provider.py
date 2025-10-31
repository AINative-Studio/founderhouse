"""
OpenAI Provider
GPT-4 and GPT-3.5-Turbo integration
"""
import time
from typing import Optional, List

from openai import AsyncOpenAI
import tiktoken

from app.llm.llm_provider import LLMProvider, LLMResponse, LLMConfig, LLMProviderType


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider implementation"""

    # Pricing per 1M tokens (as of Jan 2025)
    PRICING = {
        "gpt-4-turbo-preview": {"input": 10.0, "output": 30.0},
        "gpt-4": {"input": 30.0, "output": 60.0},
        "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
        "gpt-3.5-turbo-16k": {"input": 3.0, "output": 4.0},
    }

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = AsyncOpenAI(api_key=config.api_key)
        self.validate_config()

    @property
    def provider_type(self) -> LLMProviderType:
        return LLMProviderType.OPENAI

    @property
    def supported_models(self) -> List[str]:
        return [
            "gpt-4-turbo-preview",
            "gpt-4",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k"
        ]

    @property
    def default_model(self) -> str:
        return "gpt-3.5-turbo"

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate completion using OpenAI"""
        try:
            start_time = time.time()

            # Build messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=self.config.model_name,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                top_p=self.config.top_p,
                frequency_penalty=self.config.frequency_penalty,
                presence_penalty=self.config.presence_penalty,
                **kwargs
            )

            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)

            # Extract usage
            usage = response.usage
            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens

            # Calculate cost
            cost = self.calculate_cost(prompt_tokens, completion_tokens)

            return LLMResponse(
                content=response.choices[0].message.content,
                provider=self.provider_type,
                model=self.config.model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost,
                latency_ms=latency_ms,
                finish_reason=response.choices[0].finish_reason,
                metadata={
                    "response_id": response.id,
                    "created": response.created
                }
            )

        except Exception as e:
            self.logger.error(f"OpenAI completion failed: {str(e)}")
            raise

    async def stream_complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ):
        """Stream completion from OpenAI"""
        try:
            # Build messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # Call OpenAI streaming API
            stream = await self.client.chat.completions.create(
                model=self.config.model_name,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                stream=True,
                **kwargs
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            self.logger.error(f"OpenAI streaming failed: {str(e)}")
            raise

    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken"""
        try:
            # Get encoding for model
            encoding_name = "cl100k_base"  # Used by gpt-4 and gpt-3.5-turbo
            if "gpt-3.5" in self.config.model_name or "gpt-4" in self.config.model_name:
                encoding = tiktoken.get_encoding(encoding_name)
            else:
                encoding = tiktoken.encoding_for_model(self.config.model_name)

            return len(encoding.encode(text))
        except Exception as e:
            self.logger.warning(f"Token counting failed, using estimation: {str(e)}")
            # Fallback: rough estimation (1 token ~= 4 characters)
            return len(text) // 4

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost in USD"""
        pricing = self.PRICING.get(self.config.model_name)
        if not pricing:
            self.logger.warning(f"No pricing data for {self.config.model_name}, returning 0")
            return 0.0

        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]

        return round(input_cost + output_cost, 6)
