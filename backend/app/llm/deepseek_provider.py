"""
DeepSeek Provider
Cost-effective alternative LLM
"""
import time
from typing import Optional, List

import httpx

from app.llm.llm_provider import LLMProvider, LLMResponse, LLMConfig, LLMProviderType


class DeepSeekProvider(LLMProvider):
    """DeepSeek provider implementation (OpenAI-compatible API)"""

    # Pricing per 1M tokens (significantly cheaper)
    PRICING = {
        "deepseek-chat": {"input": 0.14, "output": 0.28},
        "deepseek-coder": {"input": 0.14, "output": 0.28},
    }

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.base_url or "https://api.deepseek.com/v1"
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json"
            },
            timeout=config.timeout
        )
        self.validate_config()

    @property
    def provider_type(self) -> LLMProviderType:
        return LLMProviderType.DEEPSEEK

    @property
    def supported_models(self) -> List[str]:
        return [
            "deepseek-chat",
            "deepseek-coder"
        ]

    @property
    def default_model(self) -> str:
        return "deepseek-chat"

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate completion using DeepSeek"""
        try:
            start_time = time.time()

            # Build messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # Call DeepSeek API (OpenAI-compatible)
            response = await self.client.post(
                "/chat/completions",
                json={
                    "model": self.config.model_name,
                    "messages": messages,
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens,
                    "top_p": self.config.top_p,
                    **kwargs
                }
            )

            response.raise_for_status()
            data = response.json()

            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)

            # Extract usage
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)

            # Calculate cost
            cost = self.calculate_cost(prompt_tokens, completion_tokens)

            # Extract content
            content = data["choices"][0]["message"]["content"]

            return LLMResponse(
                content=content,
                provider=self.provider_type,
                model=self.config.model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost,
                latency_ms=latency_ms,
                finish_reason=data["choices"][0].get("finish_reason"),
                metadata={
                    "response_id": data.get("id"),
                    "created": data.get("created")
                }
            )

        except Exception as e:
            self.logger.error(f"DeepSeek completion failed: {str(e)}")
            raise

    async def stream_complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ):
        """Stream completion from DeepSeek"""
        try:
            # Build messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # Call DeepSeek streaming API
            async with self.client.stream(
                "POST",
                "/chat/completions",
                json={
                    "model": self.config.model_name,
                    "messages": messages,
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens,
                    "stream": True,
                    **kwargs
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break

                        import json
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]

        except Exception as e:
            self.logger.error(f"DeepSeek streaming failed: {str(e)}")
            raise

    def count_tokens(self, text: str) -> int:
        """Count tokens (estimation)"""
        # DeepSeek uses a similar tokenizer to GPT-3.5
        # Rough estimation: 1 token ~= 4 characters
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

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
