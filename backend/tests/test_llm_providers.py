"""
Tests for LLM Providers
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.llm.llm_provider import LLMConfig, LLMProviderType, select_best_provider, LLMModelTier
from app.llm.openai_provider import OpenAIProvider
from app.llm.anthropic_provider import AnthropicProvider


def test_provider_selection_premium():
    """Test provider selection for premium tier"""
    api_keys = {
        "anthropic": "test_key",
        "openai": "test_key"
    }

    config = select_best_provider(
        task_type="general",
        budget_tier=LLMModelTier.PREMIUM,
        api_keys=api_keys
    )

    assert config.provider == LLMProviderType.ANTHROPIC
    assert "claude" in config.model_name.lower()


def test_provider_selection_standard():
    """Test provider selection for standard tier"""
    api_keys = {
        "openai": "test_key"
    }

    config = select_best_provider(
        task_type="general",
        budget_tier=LLMModelTier.STANDARD,
        api_keys=api_keys
    )

    assert config.provider == LLMProviderType.OPENAI
    assert config.model_name == "gpt-3.5-turbo"


def test_provider_selection_local():
    """Test provider selection for local tier"""
    config = select_best_provider(
        task_type="general",
        budget_tier=LLMModelTier.LOCAL,
        api_keys={}
    )

    assert config.provider == LLMProviderType.OLLAMA


def test_openai_token_counting():
    """Test OpenAI token counting"""
    config = LLMConfig(
        provider=LLMProviderType.OPENAI,
        model_name="gpt-3.5-turbo",
        api_key="test_key"
    )

    provider = OpenAIProvider(config)

    text = "This is a test sentence."
    token_count = provider.count_tokens(text)

    assert token_count > 0
    assert token_count < 100  # Should be a small number


def test_openai_cost_calculation():
    """Test OpenAI cost calculation"""
    config = LLMConfig(
        provider=LLMProviderType.OPENAI,
        model_name="gpt-3.5-turbo",
        api_key="test_key"
    )

    provider = OpenAIProvider(config)

    cost = provider.calculate_cost(
        prompt_tokens=1000,
        completion_tokens=500
    )

    assert cost > 0
    assert cost < 1.0  # Should be less than a dollar


def test_anthropic_cost_calculation():
    """Test Anthropic cost calculation"""
    config = LLMConfig(
        provider=LLMProviderType.ANTHROPIC,
        model_name="claude-3-haiku-20240307",
        api_key="test_key"
    )

    provider = AnthropicProvider(config)

    cost = provider.calculate_cost(
        prompt_tokens=1000,
        completion_tokens=500
    )

    assert cost > 0


@pytest.mark.asyncio
async def test_openai_complete_mock():
    """Test OpenAI completion with mocked API"""
    config = LLMConfig(
        provider=LLMProviderType.OPENAI,
        model_name="gpt-3.5-turbo",
        api_key="test_key"
    )

    provider = OpenAIProvider(config)

    # Mock the OpenAI client
    with patch.object(provider.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Test response"), finish_reason="stop")]
        mock_response.usage = Mock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        mock_response.id = "test_id"
        mock_response.created = 1234567890

        mock_create.return_value = mock_response

        response = await provider.complete("Test prompt")

        assert response.content == "Test response"
        assert response.total_tokens == 30
        assert response.cost_usd is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
