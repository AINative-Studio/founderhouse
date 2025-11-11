"""
ZeroVoice MCP Client Tests
TDD tests for ZeroVoice client functionality
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import httpx

from app.mcp.zerovoice_client import ZeroVoiceClient, get_zerovoice


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    with patch('app.mcp.zerovoice_client.get_settings') as mock:
        mock.return_value = Mock(
            zerovoice_api_base_url="https://api.zerovoice.test",
            zerovoice_api_key="test-api-key"
        )
        yield mock


@pytest.fixture
def zerovoice_client(mock_settings):
    """Create ZeroVoice client instance for testing"""
    return ZeroVoiceClient()


@pytest.fixture
def mock_http_client():
    """Mock HTTP client for testing"""
    return AsyncMock(spec=httpx.AsyncClient)


class TestZeroVoiceClientInitialization:
    """Test client initialization"""

    def test_client_initializes_with_settings(self, zerovoice_client, mock_settings):
        """Test that client initializes correctly with settings"""
        assert zerovoice_client.base_url == "https://api.zerovoice.test"
        assert zerovoice_client.api_key == "test-api-key"
        assert zerovoice_client._access_token is None
        assert zerovoice_client._token_expires_at is None

    def test_get_zerovoice_returns_client(self):
        """Test dependency injection function"""
        client = get_zerovoice()
        assert isinstance(client, ZeroVoiceClient)


class TestAuthentication:
    """Test authentication mechanisms"""

    @pytest.mark.asyncio
    async def test_ensure_authenticated_gets_new_token(self, zerovoice_client, mock_http_client):
        """Test that authentication fetches new token"""
        # Mock the HTTP response
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "new-token-123",
            "expires_in": 3600
        }
        mock_response.raise_for_status = Mock()
        mock_http_client.post.return_value = mock_response

        zerovoice_client._client = mock_http_client

        token = await zerovoice_client._ensure_authenticated()

        assert token == "new-token-123"
        assert zerovoice_client._access_token == "new-token-123"
        assert zerovoice_client._token_expires_at is not None

        # Verify API call
        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args
        assert "/v1/auth/token" in str(call_args)

    @pytest.mark.asyncio
    async def test_ensure_authenticated_reuses_valid_token(self, zerovoice_client):
        """Test that valid token is reused"""
        # Set a valid token
        zerovoice_client._access_token = "existing-token"
        zerovoice_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        token = await zerovoice_client._ensure_authenticated()

        assert token == "existing-token"

    @pytest.mark.asyncio
    async def test_ensure_authenticated_refreshes_expired_token(self, zerovoice_client, mock_http_client):
        """Test that expired token is refreshed"""
        # Set an expired token
        zerovoice_client._access_token = "old-token"
        zerovoice_client._token_expires_at = datetime.utcnow() - timedelta(minutes=1)

        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "refreshed-token-456",
            "expires_in": 3600
        }
        mock_response.raise_for_status = Mock()
        mock_http_client.post.return_value = mock_response

        zerovoice_client._client = mock_http_client

        token = await zerovoice_client._ensure_authenticated()

        assert token == "refreshed-token-456"
        assert zerovoice_client._access_token == "refreshed-token-456"

    def test_get_headers_includes_auth_token(self, zerovoice_client):
        """Test that headers include authentication token"""
        headers = zerovoice_client._get_headers("test-token")

        assert headers["Authorization"] == "Bearer test-token"
        assert headers["Content-Type"] == "application/json"


class TestTranscribeAudio:
    """Test audio transcription functionality"""

    @pytest.mark.asyncio
    async def test_transcribe_audio_with_url(self, zerovoice_client, mock_http_client):
        """Test transcription with audio URL"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "transcript": "Create a task to follow up with investors",
            "confidence": 0.95,
            "duration_seconds": 3.5
        }
        mock_response.raise_for_status = Mock()
        mock_http_client.post.return_value = mock_response

        zerovoice_client._client = mock_http_client
        zerovoice_client._access_token = "test-token"
        zerovoice_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        result = await zerovoice_client.transcribe_audio(
            audio_url="https://example.com/audio.mp3",
            language="en-US"
        )

        assert result["transcript"] == "Create a task to follow up with investors"
        assert result["confidence"] == 0.95
        assert result["duration_seconds"] == 3.5

    @pytest.mark.asyncio
    async def test_transcribe_audio_with_base64(self, zerovoice_client, mock_http_client):
        """Test transcription with base64 audio data"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "transcript": "Schedule meeting for tomorrow",
            "confidence": 0.92
        }
        mock_response.raise_for_status = Mock()
        mock_http_client.post.return_value = mock_response

        zerovoice_client._client = mock_http_client
        zerovoice_client._access_token = "test-token"
        zerovoice_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        result = await zerovoice_client.transcribe_audio(
            audio_base64="base64encodeddata",
            language="en-US"
        )

        assert result["transcript"] == "Schedule meeting for tomorrow"
        assert result["confidence"] == 0.92

    @pytest.mark.asyncio
    async def test_transcribe_audio_requires_audio_input(self, zerovoice_client):
        """Test that transcription requires audio URL or base64"""
        with pytest.raises(ValueError, match="Either audio_url or audio_base64 must be provided"):
            await zerovoice_client.transcribe_audio()

    @pytest.mark.asyncio
    async def test_transcribe_audio_with_timestamps(self, zerovoice_client, mock_http_client):
        """Test transcription with word-level timestamps"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "transcript": "Hello world",
            "confidence": 0.98,
            "timestamps": [
                {"word": "Hello", "start": 0.0, "end": 0.5},
                {"word": "world", "start": 0.6, "end": 1.0}
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_http_client.post.return_value = mock_response

        zerovoice_client._client = mock_http_client
        zerovoice_client._access_token = "test-token"
        zerovoice_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        result = await zerovoice_client.transcribe_audio(
            audio_url="https://example.com/audio.mp3",
            include_timestamps=True
        )

        assert "timestamps" in result
        assert len(result["timestamps"]) == 2

    @pytest.mark.asyncio
    async def test_transcribe_audio_handles_api_error(self, zerovoice_client, mock_http_client):
        """Test that API errors are properly handled"""
        mock_http_client.post.side_effect = httpx.HTTPError("API error")

        zerovoice_client._client = mock_http_client
        zerovoice_client._access_token = "test-token"
        zerovoice_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        with pytest.raises(httpx.HTTPError):
            await zerovoice_client.transcribe_audio(audio_url="https://example.com/audio.mp3")


class TestParseIntent:
    """Test intent parsing functionality"""

    @pytest.mark.asyncio
    async def test_parse_intent_basic(self, zerovoice_client, mock_http_client):
        """Test basic intent parsing"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "intent": "create_task",
            "confidence": 0.95,
            "entities": {
                "task": "follow up with investors",
                "deadline": "Friday"
            }
        }
        mock_response.raise_for_status = Mock()
        mock_http_client.post.return_value = mock_response

        zerovoice_client._client = mock_http_client
        zerovoice_client._access_token = "test-token"
        zerovoice_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        result = await zerovoice_client.parse_intent(
            "Create a task to follow up with investors by Friday"
        )

        assert result["intent"] == "create_task"
        assert result["confidence"] == 0.95
        assert result["entities"]["task"] == "follow up with investors"
        assert result["entities"]["deadline"] == "Friday"

    @pytest.mark.asyncio
    async def test_parse_intent_with_context(self, zerovoice_client, mock_http_client):
        """Test intent parsing with context"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "intent": "schedule_meeting",
            "confidence": 0.92,
            "entities": {
                "subject": "Investor meeting",
                "time": "tomorrow at 2pm"
            }
        }
        mock_response.raise_for_status = Mock()
        mock_http_client.post.return_value = mock_response

        zerovoice_client._client = mock_http_client
        zerovoice_client._access_token = "test-token"
        zerovoice_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        result = await zerovoice_client.parse_intent(
            "Schedule a meeting",
            context={"workspace_id": "123", "recent_contacts": ["John", "Jane"]}
        )

        assert result["intent"] == "schedule_meeting"
        assert result["confidence"] == 0.92

    @pytest.mark.asyncio
    async def test_parse_intent_unknown(self, zerovoice_client, mock_http_client):
        """Test intent parsing for unknown intent"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "intent": "unknown",
            "confidence": 0.3,
            "entities": {}
        }
        mock_response.raise_for_status = Mock()
        mock_http_client.post.return_value = mock_response

        zerovoice_client._client = mock_http_client
        zerovoice_client._access_token = "test-token"
        zerovoice_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        result = await zerovoice_client.parse_intent("gibberish nonsense")

        assert result["intent"] == "unknown"
        assert result["confidence"] < 0.5


class TestProcessVoiceCommand:
    """Test complete voice command processing pipeline"""

    @pytest.mark.asyncio
    async def test_process_voice_command_with_transcript(self, zerovoice_client, mock_http_client):
        """Test processing with pre-transcribed text"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "intent": "create_task",
            "confidence": 0.95,
            "entities": {"task": "follow up with investors"}
        }
        mock_response.raise_for_status = Mock()
        mock_http_client.post.return_value = mock_response

        zerovoice_client._client = mock_http_client
        zerovoice_client._access_token = "test-token"
        zerovoice_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        result = await zerovoice_client.process_voice_command(
            transcript="Create a task to follow up with investors"
        )

        assert result["transcript"] == "Create a task to follow up with investors"
        assert result["intent"] == "create_task"
        assert result["confidence"] == 0.95
        assert "processing_time_ms" in result
        assert result["transcription_time_ms"] == 0  # No transcription needed

    @pytest.mark.asyncio
    async def test_process_voice_command_with_audio(self, zerovoice_client, mock_http_client):
        """Test processing with audio input"""
        # Mock responses for both transcription and intent parsing
        transcribe_response = Mock()
        transcribe_response.json.return_value = {
            "transcript": "Check my metrics",
            "confidence": 0.93
        }
        transcribe_response.raise_for_status = Mock()

        intent_response = Mock()
        intent_response.json.return_value = {
            "intent": "check_metrics",
            "confidence": 0.88,
            "entities": {}
        }
        intent_response.raise_for_status = Mock()

        mock_http_client.post.side_effect = [transcribe_response, intent_response]

        zerovoice_client._client = mock_http_client
        zerovoice_client._access_token = "test-token"
        zerovoice_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        result = await zerovoice_client.process_voice_command(
            audio_url="https://example.com/audio.mp3"
        )

        assert result["transcript"] == "Check my metrics"
        assert result["intent"] == "check_metrics"
        assert result["transcription_time_ms"] >= 0  # Can be 0 in fast mock execution
        assert result["intent_parsing_time_ms"] >= 0  # Can be 0 in fast mock execution
        assert result["processing_time_ms"] >= 0

    @pytest.mark.asyncio
    async def test_process_voice_command_performance(self, zerovoice_client, mock_http_client):
        """Test that processing completes within 2.5s (per PRD)"""
        import time

        mock_response = Mock()
        mock_response.json.return_value = {
            "intent": "get_briefing",
            "confidence": 0.91,
            "entities": {}
        }
        mock_response.raise_for_status = Mock()
        mock_http_client.post.return_value = mock_response

        zerovoice_client._client = mock_http_client
        zerovoice_client._access_token = "test-token"
        zerovoice_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        start = time.time()
        result = await zerovoice_client.process_voice_command(
            transcript="Get my morning briefing"
        )
        elapsed_ms = (time.time() - start) * 1000

        # Verify latency requirement from PRD
        assert result["processing_time_ms"] < 2500, f"Processing took {result['processing_time_ms']}ms, exceeds 2.5s limit"
        assert elapsed_ms < 3000  # Allow small buffer for test execution

    @pytest.mark.asyncio
    async def test_process_voice_command_requires_input(self, zerovoice_client):
        """Test that processing requires transcript or audio"""
        with pytest.raises(ValueError, match="Either transcript or audio must be provided"):
            await zerovoice_client.process_voice_command()

    @pytest.mark.asyncio
    async def test_process_voice_command_with_context(self, zerovoice_client, mock_http_client):
        """Test processing with contextual information"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "intent": "send_message",
            "confidence": 0.89,
            "entities": {"recipient": "team", "message": "great work"}
        }
        mock_response.raise_for_status = Mock()
        mock_http_client.post.return_value = mock_response

        zerovoice_client._client = mock_http_client
        zerovoice_client._access_token = "test-token"
        zerovoice_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        result = await zerovoice_client.process_voice_command(
            transcript="Tell the team great work",
            context={"workspace_id": "123", "founder_id": "456"}
        )

        assert result["intent"] == "send_message"
        assert result["entities"]["recipient"] == "team"


class TestHealthCheck:
    """Test health check functionality"""

    @pytest.mark.asyncio
    async def test_health_check_success(self, zerovoice_client, mock_http_client):
        """Test successful health check"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "healthy",
            "version": "1.0.0",
            "uptime": 3600
        }
        mock_response.raise_for_status = Mock()
        mock_http_client.get.return_value = mock_response

        zerovoice_client._client = mock_http_client

        result = await zerovoice_client.health_check()

        assert result["status"] == "healthy"
        assert "version" in result

    @pytest.mark.asyncio
    async def test_health_check_failure(self, zerovoice_client, mock_http_client):
        """Test health check failure handling"""
        mock_http_client.get.side_effect = Exception("Connection refused")

        zerovoice_client._client = mock_http_client

        result = await zerovoice_client.health_check()

        assert result["status"] == "unhealthy"
        assert "error" in result


class TestClientCleanup:
    """Test client cleanup"""

    @pytest.mark.asyncio
    async def test_close_client(self, zerovoice_client, mock_http_client):
        """Test that client closes properly"""
        zerovoice_client._client = mock_http_client

        await zerovoice_client.close()

        mock_http_client.aclose.assert_called_once()


class TestIntegration:
    """Integration tests for complete workflows"""

    @pytest.mark.asyncio
    async def test_complete_voice_to_action_flow(self, zerovoice_client, mock_http_client):
        """Test complete voice → intent → action flow"""
        # Mock transcription
        transcribe_response = Mock()
        transcribe_response.json.return_value = {
            "transcript": "Create a task to prepare Q4 presentation",
            "confidence": 0.96
        }
        transcribe_response.raise_for_status = Mock()

        # Mock intent parsing
        intent_response = Mock()
        intent_response.json.return_value = {
            "intent": "create_task",
            "confidence": 0.94,
            "entities": {
                "task": "prepare Q4 presentation"
            }
        }
        intent_response.raise_for_status = Mock()

        mock_http_client.post.side_effect = [transcribe_response, intent_response]

        zerovoice_client._client = mock_http_client
        zerovoice_client._access_token = "test-token"
        zerovoice_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        result = await zerovoice_client.process_voice_command(
            audio_url="https://example.com/command.mp3"
        )

        # Verify complete pipeline
        assert result["transcript"] == "Create a task to prepare Q4 presentation"
        assert result["intent"] == "create_task"
        assert result["confidence"] > 0.9
        assert result["entities"]["task"] == "prepare Q4 presentation"
        assert result["processing_time_ms"] < 2500  # PRD requirement
