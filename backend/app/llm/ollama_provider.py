"""
Ollama Provider
Local LLM inference
"""
import time
from typing import Optional, List

import httpx

from app.llm.llm_provider import LLMProvider, LLMResponse, LLMConfig, LLMProviderType


class OllamaProvider(LLMProvider):
    """Ollama provider for local LLM inference"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.base_url or "http://localhost:11434"
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=config.timeout
        )
        self.validate_config()

    @property
    def provider_type(self) -> LLMProviderType:
        return LLMProviderType.OLLAMA

    @property
    def supported_models(self) -> List[str]:
        return [
            "llama2",
            "llama2:13b",
            "llama2:70b",
            "mistral",
            "mixtral",
            "codellama",
            "phi",
            "neural-chat"
        ]

    @property
    def default_model(self) -> str:
        return "llama2"

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate completion using Ollama"""
        try:
            start_time = time.time()

            # Build prompt with system message if provided
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"

            # Call Ollama API
            response = await self.client.post(
                "/api/generate",
                json={
                    "model": self.config.model_name,
                    "prompt": full_prompt,
                    "temperature": self.config.temperature,
                    "stream": False,
                    "options": {
                        "num_predict": self.config.max_tokens,
                        "top_p": self.config.top_p
                    },
                    **kwargs
                }
            )

            response.raise_for_status()
            data = response.json()

            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)

            # Extract content
            content = data.get("response", "")

            # Ollama doesn't provide token counts in the same way
            # Estimate based on text length
            prompt_tokens = self.count_tokens(full_prompt)
            completion_tokens = self.count_tokens(content)
            total_tokens = prompt_tokens + completion_tokens

            return LLMResponse(
                content=content,
                provider=self.provider_type,
                model=self.config.model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=0.0,  # Local inference is free
                latency_ms=latency_ms,
                finish_reason="stop",
                metadata={
                    "eval_count": data.get("eval_count"),
                    "eval_duration": data.get("eval_duration")
                }
            )

        except Exception as e:
            self.logger.error(f"Ollama completion failed: {str(e)}")
            raise

    async def stream_complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ):
        """Stream completion from Ollama"""
        try:
            # Build prompt with system message if provided
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"

            # Call Ollama streaming API
            async with self.client.stream(
                "POST",
                "/api/generate",
                json={
                    "model": self.config.model_name,
                    "prompt": full_prompt,
                    "temperature": self.config.temperature,
                    "stream": True,
                    "options": {
                        "num_predict": self.config.max_tokens,
                        "top_p": self.config.top_p
                    },
                    **kwargs
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        import json
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
                        if data.get("done"):
                            break

        except Exception as e:
            self.logger.error(f"Ollama streaming failed: {str(e)}")
            raise

    def count_tokens(self, text: str) -> int:
        """Count tokens (estimation for Ollama)"""
        # Rough estimation: 1 token ~= 4 characters
        return len(text) // 4

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost - Ollama is free (local)"""
        return 0.0

    async def list_models(self) -> List[str]:
        """List available models in local Ollama instance"""
        try:
            response = await self.client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            self.logger.error(f"Failed to list Ollama models: {str(e)}")
            return []

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
