"""
Comprehensive tests for LLM Providers
Tests OpenAI, Anthropic, and base provider functionality
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.llm.llm_provider import (
    LLMProvider, LLMConfig, LLMProviderType, LLMResponse,
    LLMModelTier, get_provider, select_best_provider
)
from app.llm.openai_provider import OpenAIProvider
from app.llm.anthropic_provider import AnthropicProvider


@pytest.fixture
def openai_config():
    """OpenAI provider configuration"""
    return LLMConfig(
        provider=LLMProviderType.OPENAI,
        model_name="gpt-3.5-turbo",
        temperature=0.7,
        max_tokens=2000,
        api_key="test-api-key"
    )


@pytest.fixture
def anthropic_config():
    """Anthropic provider configuration"""
    return LLMConfig(
        provider=LLMProviderType.ANTHROPIC,
        model_name="claude-3-haiku-20240307",
        temperature=0.7,
        max_tokens=2000,
        api_key="test-api-key"
    )


class TestOpenAIProvider:
    """Tests for OpenAIProvider"""

    @pytest.mark.asyncio
    async def test_complete_success(self, openai_config):
        """Test successful completion request"""
        # Arrange
        provider = OpenAIProvider(openai_config)

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "id": "chatcmpl-123",
                "object": "chat.completion",
                "created": 1677652288,
                "model": "gpt-3.5-turbo",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "This is a test response"
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30
                }
            }
            mock_post.return_value = mock_response

            # Act
            result = await provider.complete("Test prompt")

        # Assert
        assert isinstance(result, LLMResponse)
        assert result.content == "This is a test response"
        assert result.provider == LLMProviderType.OPENAI
        assert result.total_tokens == 30
        assert result.prompt_tokens == 10
        assert result.completion_tokens == 20
        assert result.cost_usd is not None

    @pytest.mark.asyncio
    async def test_complete_with_system_message(self, openai_config):
        """Test completion with system message"""
        # Arrange
        provider = OpenAIProvider(openai_config)

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Response"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 15, "completion_tokens": 25, "total_tokens": 40}
            }
            mock_post.return_value = mock_response

            # Act
            result = await provider.complete(
                "User prompt",
                system_message="You are a helpful assistant"
            )

        # Assert
        assert result.content == "Response"
        # Verify system message was included in request
        call_args = mock_post.call_args
        messages = call_args[1]["json"]["messages"]
        assert any(msg["role"] == "system" for msg in messages)

    @pytest.mark.asyncio
    async def test_stream_completion(self, openai_config):
        """Test streaming completion"""
        # Arrange
        provider = OpenAIProvider(openai_config)

        async def mock_stream():
            chunks = [
                'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n',
                'data: {"choices":[{"delta":{"content":" world"}}]}\n\n',
                'data: [DONE]\n\n'
            ]
            for chunk in chunks:
                yield chunk.encode()

        with patch('httpx.AsyncClient.stream') as mock_stream_ctx:
            mock_response = MagicMock()
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock()
            mock_response.aiter_bytes = mock_stream

            mock_stream_ctx.return_value = mock_response

            # Act
            chunks_received = []
            async for chunk in provider.stream("Test prompt"):
                chunks_received.append(chunk)

        # Assert
        assert len(chunks_received) > 0

    @pytest.mark.asyncio
    async def test_api_error_handling(self, openai_config):
        """Test API error handling"""
        # Arrange
        provider = OpenAIProvider(openai_config)

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.json.return_value = {
                "error": {
                    "message": "Rate limit exceeded",
                    "type": "rate_limit_error"
                }
            }
            mock_post.return_value = mock_response

            # Act & Assert
            with pytest.raises(Exception):
                await provider.complete("Test prompt")

    @pytest.mark.asyncio
    async def test_retry_on_failure(self, openai_config):
        """Test retry logic on transient failures"""
        # Arrange
        provider = OpenAIProvider(openai_config)

        with patch('httpx.AsyncClient.post') as mock_post:
            # First call fails, second succeeds
            mock_post.side_effect = [
                httpx.ConnectError("Connection failed"),
                MagicMock(status_code=200, json=lambda: {
                    "choices": [{"message": {"content": "Success"}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
                })
            ]

            # Act
            result = await provider.complete("Test prompt")

        # Assert
        assert result.content == "Success"
        assert mock_post.call_count >= 1

    def test_count_tokens(self, openai_config):
        """Test token counting"""
        # Arrange
        provider = OpenAIProvider(openai_config)
        text = "This is a test message for token counting"

        # Act
        token_count = provider.count_tokens(text)

        # Assert
        assert token_count > 0
        assert isinstance(token_count, int)

    def test_calculate_cost(self, openai_config):
        """Test cost calculation"""
        # Arrange
        provider = OpenAIProvider(openai_config)

        # Act
        cost = provider.calculate_cost(prompt_tokens=1000, completion_tokens=500)

        # Assert
        assert cost > 0
        assert isinstance(cost, float)

    def test_calculate_cost_different_models(self):
        """Test cost calculation varies by model"""
        # Arrange
        config_35 = LLMConfig(
            provider=LLMProviderType.OPENAI,
            model_name="gpt-3.5-turbo",
            api_key="test"
        )
        config_4 = LLMConfig(
            provider=LLMProviderType.OPENAI,
            model_name="gpt-4",
            api_key="test"
        )

        provider_35 = OpenAIProvider(config_35)
        provider_4 = OpenAIProvider(config_4)

        # Act
        cost_35 = provider_35.calculate_cost(1000, 500)
        cost_4 = provider_4.calculate_cost(1000, 500)

        # Assert
        assert cost_4 > cost_35  # GPT-4 should be more expensive


class TestAnthropicProvider:
    """Tests for AnthropicProvider"""

    @pytest.mark.asyncio
    async def test_complete_success(self, anthropic_config):
        """Test successful completion request"""
        # Arrange
        provider = AnthropicProvider(anthropic_config)

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "id": "msg_123",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": "This is Claude's response"}],
                "model": "claude-3-haiku-20240307",
                "stop_reason": "end_turn",
                "usage": {
                    "input_tokens": 15,
                    "output_tokens": 25
                }
            }
            mock_post.return_value = mock_response

            # Act
            result = await provider.complete("Test prompt")

        # Assert
        assert isinstance(result, LLMResponse)
        assert result.content == "This is Claude's response"
        assert result.provider == LLMProviderType.ANTHROPIC
        assert result.prompt_tokens == 15
        assert result.completion_tokens == 25

    @pytest.mark.asyncio
    async def test_stream_completion(self, anthropic_config):
        """Test streaming completion"""
        # Arrange
        provider = AnthropicProvider(anthropic_config)

        async def mock_stream():
            events = [
                'event: content_block_delta\ndata: {"delta":{"type":"text_delta","text":"Hello"}}\n\n',
                'event: content_block_delta\ndata: {"delta":{"type":"text_delta","text":" world"}}\n\n',
                'event: message_stop\ndata: {}\n\n'
            ]
            for event in events:
                yield event.encode()

        with patch('httpx.AsyncClient.stream') as mock_stream_ctx:
            mock_response = MagicMock()
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock()
            mock_response.aiter_bytes = mock_stream

            mock_stream_ctx.return_value = mock_response

            # Act
            chunks_received = []
            async for chunk in provider.stream("Test prompt"):
                chunks_received.append(chunk)

        # Assert
        assert len(chunks_received) > 0

    def test_count_tokens(self, anthropic_config):
        """Test token counting for Anthropic"""
        # Arrange
        provider = AnthropicProvider(anthropic_config)
        text = "This is a test message"

        # Act
        token_count = provider.count_tokens(text)

        # Assert
        assert token_count > 0
        assert isinstance(token_count, int)

    def test_calculate_cost(self, anthropic_config):
        """Test cost calculation for Anthropic"""
        # Arrange
        provider = AnthropicProvider(anthropic_config)

        # Act
        cost = provider.calculate_cost(prompt_tokens=1000, completion_tokens=500)

        # Assert
        assert cost > 0
        assert isinstance(cost, float)


class TestProviderFactory:
    """Tests for provider factory functions"""

    def test_get_provider_openai(self):
        """Test getting OpenAI provider"""
        # Arrange
        config = LLMConfig(
            provider=LLMProviderType.OPENAI,
            model_name="gpt-3.5-turbo",
            api_key="test"
        )

        # Act
        provider = get_provider(config)

        # Assert
        assert isinstance(provider, OpenAIProvider)
        assert provider.config == config

    def test_get_provider_anthropic(self):
        """Test getting Anthropic provider"""
        # Arrange
        config = LLMConfig(
            provider=LLMProviderType.ANTHROPIC,
            model_name="claude-3-haiku-20240307",
            api_key="test"
        )

        # Act
        provider = get_provider(config)

        # Assert
        assert isinstance(provider, AnthropicProvider)

    def test_select_best_provider_for_summarization(self):
        """Test provider selection for summarization task"""
        # Arrange
        api_keys = {
            "openai": "test-openai-key",
            "anthropic": "test-anthropic-key"
        }

        # Act
        config = select_best_provider(
            task_type="summarization",
            budget_tier=LLMModelTier.STANDARD,
            api_keys=api_keys
        )

        # Assert
        assert config is not None
        assert config.provider in [LLMProviderType.OPENAI, LLMProviderType.ANTHROPIC]

    def test_select_best_provider_premium_tier(self):
        """Test provider selection for premium tier"""
        # Arrange
        api_keys = {"openai": "test-key"}

        # Act
        config = select_best_provider(
            task_type="complex_analysis",
            budget_tier=LLMModelTier.PREMIUM,
            api_keys=api_keys
        )

        # Assert
        assert config is not None
        # Premium tier should select advanced models
        assert "gpt-4" in config.model_name or "claude-3" in config.model_name

    def test_select_best_provider_budget_tier(self):
        """Test provider selection for budget tier"""
        # Arrange
        api_keys = {"openai": "test-key"}

        # Act
        config = select_best_provider(
            task_type="simple_task",
            budget_tier=LLMModelTier.BUDGET,
            api_keys=api_keys
        )

        # Assert
        assert config is not None
        # Budget tier should select cheaper models

    def test_select_best_provider_no_api_keys(self):
        """Test provider selection with no API keys"""
        # Act
        config = select_best_provider(
            task_type="test",
            budget_tier=LLMModelTier.STANDARD,
            api_keys={}
        )

        # Assert - should fallback to local or raise error
        assert config is None or config.provider == LLMProviderType.OLLAMA


class TestLLMResponse:
    """Tests for LLMResponse model"""

    def test_llm_response_creation(self):
        """Test creating LLM response"""
        # Act
        response = LLMResponse(
            content="Test content",
            provider=LLMProviderType.OPENAI,
            model="gpt-3.5-turbo",
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            cost_usd=0.001,
            finish_reason="stop"
        )

        # Assert
        assert response.content == "Test content"
        assert response.total_tokens == 30
        assert response.cost_usd == 0.001

    def test_llm_response_defaults(self):
        """Test LLM response with default values"""
        # Act
        response = LLMResponse(
            content="Test",
            provider=LLMProviderType.OPENAI,
            model="gpt-3.5-turbo"
        )

        # Assert
        assert response.prompt_tokens == 0
        assert response.completion_tokens == 0
        assert response.total_tokens == 0
        assert response.cost_usd is None
        assert response.metadata == {}


class TestErrorHandling:
    """Tests for error handling across providers"""

    @pytest.mark.asyncio
    async def test_network_error(self, openai_config):
        """Test handling of network errors"""
        # Arrange
        provider = OpenAIProvider(openai_config)

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.side_effect = httpx.ConnectError("Network error")

            # Act & Assert
            with pytest.raises(Exception):
                await provider.complete("Test prompt")

    @pytest.mark.asyncio
    async def test_timeout_error(self, openai_config):
        """Test handling of timeout errors"""
        # Arrange
        provider = OpenAIProvider(openai_config)

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timeout")

            # Act & Assert
            with pytest.raises(Exception):
                await provider.complete("Test prompt")

    @pytest.mark.asyncio
    async def test_invalid_api_key(self, openai_config):
        """Test handling of invalid API key"""
        # Arrange
        provider = OpenAIProvider(openai_config)

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.json.return_value = {
                "error": {"message": "Invalid API key", "type": "invalid_request_error"}
            }
            mock_post.return_value = mock_response

            # Act & Assert
            with pytest.raises(Exception):
                await provider.complete("Test prompt")

    @pytest.mark.asyncio
    async def test_malformed_response(self, openai_config):
        """Test handling of malformed API response"""
        # Arrange
        provider = OpenAIProvider(openai_config)

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {}  # Missing expected fields

            mock_post.return_value = mock_response

            # Act & Assert
            with pytest.raises(Exception):
                await provider.complete("Test prompt")


class TestPerformanceMetrics:
    """Tests for performance tracking"""

    @pytest.mark.asyncio
    async def test_latency_tracking(self, openai_config):
        """Test that latency is tracked"""
        # Arrange
        provider = OpenAIProvider(openai_config)

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Response"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
            }
            mock_post.return_value = mock_response

            # Act
            result = await provider.complete("Test prompt")

        # Assert
        assert result.latency_ms is not None
        assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_metadata_tracking(self, openai_config):
        """Test that metadata is tracked"""
        # Arrange
        provider = OpenAIProvider(openai_config)

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "id": "chatcmpl-123",
                "choices": [{"message": {"content": "Response"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
            }
            mock_post.return_value = mock_response

            # Act
            result = await provider.complete("Test prompt")

        # Assert
        assert isinstance(result.metadata, dict)


class TestConfigValidation:
    """Tests for configuration validation"""

    def test_missing_api_key(self):
        """Test that missing API key is handled"""
        # Arrange
        config = LLMConfig(
            provider=LLMProviderType.OPENAI,
            model_name="gpt-3.5-turbo",
            api_key=None
        )

        # Act & Assert - Should raise error or use environment variable
        provider = OpenAIProvider(config)
        assert provider is not None

    def test_invalid_temperature(self):
        """Test that invalid temperature is validated"""
        # Act & Assert
        with pytest.raises(Exception):
            LLMConfig(
                provider=LLMProviderType.OPENAI,
                model_name="gpt-3.5-turbo",
                temperature=2.5,  # Invalid: should be 0-2
                api_key="test"
            )

    def test_invalid_max_tokens(self):
        """Test that invalid max_tokens is validated"""
        # Act & Assert
        with pytest.raises(Exception):
            LLMConfig(
                provider=LLMProviderType.OPENAI,
                model_name="gpt-3.5-turbo",
                max_tokens=-1,  # Invalid: should be positive
                api_key="test"
            )
