"""
Tests for Loom MCP Client
TDD approach - tests written first
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from uuid import uuid4

from app.mcp.loom_client import LoomMCPClient, LoomVideoData, LoomTranscriptData
from app.connectors.base_connector import ConnectorResponse, ConnectorStatus


@pytest.fixture
def loom_credentials():
    """Loom API credentials fixture"""
    return {
        "api_key": "test-loom-api-key",
        "client_id": "test-client-id",
        "client_secret": "test-client-secret"
    }


@pytest.fixture
def loom_client(loom_credentials):
    """Loom MCP client fixture"""
    return LoomMCPClient(credentials=loom_credentials)


@pytest.fixture
def sample_video_data():
    """Sample Loom video data"""
    return {
        "id": "abc123video",
        "title": "Product Demo Video",
        "description": "Demo of new features",
        "duration": 300,
        "thumbnail_url": "https://cdn.loom.com/thumbnails/abc123.jpg",
        "video_url": "https://www.loom.com/share/abc123video",
        "created_at": "2025-11-11T10:00:00Z",
        "owner": {
            "name": "John Doe",
            "email": "john@example.com"
        }
    }


@pytest.fixture
def sample_transcript_data():
    """Sample Loom transcript data"""
    return {
        "video_id": "abc123video",
        "transcript": "Hello everyone, this is a product demo. We've built some amazing features.",
        "words": [
            {"text": "Hello", "start": 0.0, "end": 0.5},
            {"text": "everyone", "start": 0.5, "end": 1.0},
            {"text": "this", "start": 1.0, "end": 1.2},
            {"text": "is", "start": 1.2, "end": 1.4},
            {"text": "a", "start": 1.4, "end": 1.5},
            {"text": "product", "start": 1.5, "end": 2.0},
            {"text": "demo", "start": 2.0, "end": 2.5}
        ],
        "language": "en"
    }


class TestLoomMCPClient:
    """Test suite for Loom MCP Client"""

    def test_client_initialization(self, loom_client, loom_credentials):
        """Test client initializes with correct credentials"""
        assert loom_client.credentials == loom_credentials
        assert loom_client.api_key == loom_credentials["api_key"]

    @pytest.mark.asyncio
    async def test_get_video_details_success(self, loom_client, sample_video_data):
        """Test fetching video details from Loom API"""
        video_id = "abc123video"

        with patch.object(loom_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data=sample_video_data
            )

            result = await loom_client.get_video_details(video_id)

            assert result is not None
            assert isinstance(result, LoomVideoData)
            assert result.video_id == video_id
            assert result.title == "Product Demo Video"
            assert result.duration_seconds == 300
            mock_request.assert_called_once_with("GET", f"/videos/{video_id}")

    @pytest.mark.asyncio
    async def test_get_video_details_not_found(self, loom_client):
        """Test handling of video not found"""
        video_id = "nonexistent"

        with patch.object(loom_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.ERROR,
                error="Video not found"
            )

            result = await loom_client.get_video_details(video_id)

            assert result is None

    @pytest.mark.asyncio
    async def test_get_video_transcript_success(self, loom_client, sample_transcript_data):
        """Test fetching video transcript from Loom API"""
        video_id = "abc123video"

        with patch.object(loom_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data=sample_transcript_data
            )

            result = await loom_client.get_video_transcript(video_id)

            assert result is not None
            assert isinstance(result, LoomTranscriptData)
            assert result.video_id == video_id
            assert result.transcript_text.startswith("Hello everyone")
            assert len(result.words) == 7
            mock_request.assert_called_once_with("GET", f"/videos/{video_id}/transcript")

    @pytest.mark.asyncio
    async def test_get_video_transcript_not_available(self, loom_client):
        """Test handling when transcript is not available"""
        video_id = "abc123video"

        with patch.object(loom_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.ERROR,
                error="Transcript not available"
            )

            result = await loom_client.get_video_transcript(video_id)

            assert result is None

    @pytest.mark.asyncio
    async def test_download_video_success(self, loom_client):
        """Test video download from Loom"""
        video_id = "abc123video"

        with patch.object(loom_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={
                    "download_url": "https://cdn.loom.com/videos/abc123video.mp4",
                    "expires_at": "2025-11-11T11:00:00Z"
                }
            )

            result = await loom_client.get_video_download_url(video_id)

            assert result is not None
            assert "https://cdn.loom.com/videos" in result
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_test(self, loom_client):
        """Test Loom API connection"""
        with patch.object(loom_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"user": {"id": "user123", "email": "test@example.com"}}
            )

            result = await loom_client.test_connection()

            assert result is True

    @pytest.mark.asyncio
    async def test_connection_test_failure(self, loom_client):
        """Test Loom API connection failure"""
        with patch.object(loom_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.ERROR,
                error="Invalid API key"
            )

            result = await loom_client.test_connection()

            assert result is False

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, loom_client):
        """Test handling of rate limit errors"""
        video_id = "abc123video"

        with patch.object(loom_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = ConnectorResponse(
                status=ConnectorStatus.ERROR,
                error="Rate limit exceeded",
                metadata={"retry_after": 60}
            )

            result = await loom_client.get_video_details(video_id)

            assert result is None

    def test_extract_video_id_from_url(self, loom_client):
        """Test extracting video ID from various Loom URL formats"""
        test_cases = [
            ("https://www.loom.com/share/abc123video", "abc123video"),
            ("https://www.loom.com/embed/def456video", "def456video"),
            ("https://loom.com/share/ghi789video", "ghi789video"),
            ("invalid-url", None)
        ]

        for url, expected_id in test_cases:
            result = loom_client.extract_video_id_from_url(url)
            assert result == expected_id

    @pytest.mark.asyncio
    async def test_error_handling_network_failure(self, loom_client):
        """Test handling of network failures"""
        video_id = "abc123video"

        with patch.object(loom_client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = Exception("Network timeout")

            with pytest.raises(Exception):
                await loom_client.get_video_details(video_id)
