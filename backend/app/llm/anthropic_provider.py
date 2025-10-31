"""
Anthropic Provider
Claude 3 and 3.5 integration
"""
import time
from typing import Optional, List

from anthropic import AsyncAnthropic

from app.llm.llm_provider import LLMProvider, LLMResponse, LLMConfig, LLMProviderType


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider implementation"""

    # Pricing per 1M tokens (as of Jan 2025)
    PRICING = {
        "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
        "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
        "claude-3-sonnet-20240229": {"input": 3.0, "output": 15.0},
        "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    }

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = AsyncAnthropic(api_key=config.api_key)
        self.validate_config()

    @property
    def provider_type(self) -> LLMProviderType:
        return LLMProviderType.ANTHROPIC

    @property
    def supported_models(self) -> List[str]:
        return [
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307"
        ]

    @property
    def default_model(self) -> str:
        return "claude-3-5-sonnet-20241022"

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate completion using Claude"""
        try:
            start_time = time.time()

            # Call Claude API
            response = await self.client.messages.create(
                model=self.config.model_name,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                system=system_prompt if system_prompt else "",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                **kwargs
            )

            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)

            # Extract usage
            prompt_tokens = response.usage.input_tokens
            completion_tokens = response.usage.output_tokens
            total_tokens = prompt_tokens + completion_tokens

            # Calculate cost
            cost = self.calculate_cost(prompt_tokens, completion_tokens)

            # Extract content
            content = ""
            for block in response.content:
                if hasattr(block, "text"):
                    content += block.text

            return LLMResponse(
                content=content,
                provider=self.provider_type,
                model=self.config.model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost,
                latency_ms=latency_ms,
                finish_reason=response.stop_reason,
                metadata={
                    "response_id": response.id,
                    "model": response.model
                }
            )

        except Exception as e:
            self.logger.error(f"Anthropic completion failed: {str(e)}")
            raise

    async def stream_complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ):
        """Stream completion from Claude"""
        try:
            async with self.client.messages.stream(
                model=self.config.model_name,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system_prompt if system_prompt else "",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                **kwargs
            ) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as e:
            self.logger.error(f"Anthropic streaming failed: {str(e)}")
            raise

    def count_tokens(self, text: str) -> int:
        """
        Count tokens for Claude

        Note: Anthropic uses a similar tokenizer to OpenAI's cl100k_base
        For accurate counting, use their tokenizer API
        """
        try:
            # Rough estimation for now (Claude uses ~4 chars per token)
            # In production, you might want to use Anthropic's count_tokens API
            return len(text) // 4
        except Exception as e:
            self.logger.warning(f"Token counting failed: {str(e)}")
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
