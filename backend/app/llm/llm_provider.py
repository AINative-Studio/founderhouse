"""
LLM Provider Base Class
Abstract interface for all LLM providers
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass

from pydantic import BaseModel, Field


class LLMProviderType(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    OLLAMA = "ollama"


class LLMModelTier(str, Enum):
    """Model quality/cost tiers"""
    PREMIUM = "premium"  # GPT-4, Claude 3.5 Sonnet
    STANDARD = "standard"  # GPT-3.5-Turbo, Claude 3 Haiku
    BUDGET = "budget"  # DeepSeek, Local Ollama
    LOCAL = "local"  # Ollama only


@dataclass
class LLMConfig:
    """Configuration for LLM provider"""
    provider: LLMProviderType
    model_name: str
    temperature: float = 0.7
    max_tokens: int = 2000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: int = 60


class LLMResponse(BaseModel):
    """Standardized response from any LLM provider"""
    content: str
    provider: LLMProviderType
    model: str

    # Token usage
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    # Cost tracking
    cost_usd: Optional[float] = None

    # Performance metrics
    latency_ms: Optional[int] = None

    # Metadata
    finish_reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers

    All providers must implement:
    - complete(): Generate text completion
    - count_tokens(): Count tokens in text
    - calculate_cost(): Calculate API cost
    """

    def __init__(self, config: LLMConfig):
        """
        Initialize provider

        Args:
            config: LLM configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @property
    @abstractmethod
    def provider_type(self) -> LLMProviderType:
        """Return provider type identifier"""
        pass

    @property
    @abstractmethod
    def supported_models(self) -> List[str]:
        """Return list of supported model names"""
        pass

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Return default model name"""
        pass

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate text completion

        Args:
            prompt: User prompt/message
            system_prompt: Optional system message
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse with generated text
        """
        pass

    @abstractmethod
    async def stream_complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ):
        """
        Stream text completion (generator)

        Args:
            prompt: User prompt/message
            system_prompt: Optional system message
            **kwargs: Additional provider-specific parameters

        Yields:
            Chunks of generated text
        """
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text

        Args:
            text: Input text

        Returns:
            Number of tokens
        """
        pass

    @abstractmethod
    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculate cost in USD for token usage

        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens

        Returns:
            Cost in USD
        """
        pass

    def validate_config(self) -> bool:
        """
        Validate provider configuration

        Returns:
            True if valid

        Raises:
            ValueError: If configuration is invalid
        """
        if self.config.model_name not in self.supported_models:
            raise ValueError(
                f"Model {self.config.model_name} not supported. "
                f"Supported models: {', '.join(self.supported_models)}"
            )

        if self.config.temperature < 0 or self.config.temperature > 2:
            raise ValueError("Temperature must be between 0 and 2")

        if self.config.max_tokens < 1:
            raise ValueError("max_tokens must be greater than 0")

        return True


def get_provider(config: LLMConfig) -> LLMProvider:
    """
    Factory function to get appropriate LLM provider

    Args:
        config: LLM configuration

    Returns:
        Configured LLM provider instance

    Raises:
        ValueError: If provider type is not supported
    """
    from app.llm.openai_provider import OpenAIProvider
    from app.llm.anthropic_provider import AnthropicProvider
    from app.llm.deepseek_provider import DeepSeekProvider
    from app.llm.ollama_provider import OllamaProvider

    provider_map = {
        LLMProviderType.OPENAI: OpenAIProvider,
        LLMProviderType.ANTHROPIC: AnthropicProvider,
        LLMProviderType.DEEPSEEK: DeepSeekProvider,
        LLMProviderType.OLLAMA: OllamaProvider
    }

    provider_class = provider_map.get(config.provider)
    if not provider_class:
        raise ValueError(f"Unsupported provider: {config.provider}")

    return provider_class(config)


def select_best_provider(
    task_type: str = "general",
    budget_tier: LLMModelTier = LLMModelTier.STANDARD,
    api_keys: Optional[Dict[str, str]] = None
) -> LLMConfig:
    """
    Select best LLM provider based on task and budget

    Args:
        task_type: Type of task (general, summarization, extraction, etc.)
        budget_tier: Budget tier for model selection
        api_keys: Available API keys

    Returns:
        Recommended LLM configuration
    """
    api_keys = api_keys or {}

    # Premium tier: Best quality
    if budget_tier == LLMModelTier.PREMIUM:
        if api_keys.get("anthropic"):
            return LLMConfig(
                provider=LLMProviderType.ANTHROPIC,
                model_name="claude-3-5-sonnet-20241022",
                temperature=0.7,
                max_tokens=4000,
                api_key=api_keys["anthropic"]
            )
        elif api_keys.get("openai"):
            return LLMConfig(
                provider=LLMProviderType.OPENAI,
                model_name="gpt-4-turbo-preview",
                temperature=0.7,
                max_tokens=4000,
                api_key=api_keys["openai"]
            )

    # Standard tier: Good balance
    elif budget_tier == LLMModelTier.STANDARD:
        if api_keys.get("openai"):
            return LLMConfig(
                provider=LLMProviderType.OPENAI,
                model_name="gpt-3.5-turbo",
                temperature=0.7,
                max_tokens=2000,
                api_key=api_keys["openai"]
            )
        elif api_keys.get("anthropic"):
            return LLMConfig(
                provider=LLMProviderType.ANTHROPIC,
                model_name="claude-3-haiku-20240307",
                temperature=0.7,
                max_tokens=2000,
                api_key=api_keys["anthropic"]
            )

    # Budget tier: Cost-effective
    elif budget_tier == LLMModelTier.BUDGET:
        if api_keys.get("deepseek"):
            return LLMConfig(
                provider=LLMProviderType.DEEPSEEK,
                model_name="deepseek-chat",
                temperature=0.7,
                max_tokens=2000,
                api_key=api_keys["deepseek"]
            )

    # Local tier: Free
    return LLMConfig(
        provider=LLMProviderType.OLLAMA,
        model_name="llama2",
        temperature=0.7,
        max_tokens=2000,
        base_url="http://localhost:11434"
    )
