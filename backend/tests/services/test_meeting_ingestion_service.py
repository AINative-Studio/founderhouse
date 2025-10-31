"""
Tests for Meeting Ingestion Service
"""
import pytest
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch

from app.services.meeting_ingestion_service import MeetingIngestionService
from app.models.meeting import MeetingSource, MeetingStatus
from app.connectors.base_connector import ConnectorResponse, ConnectorStatus


@pytest.fixture
def mock_zoom_response():
    """Mock Zoom API response"""
    return {
        "id": "123456789",
        "uuid": "abc-def-ghi",
        "topic": "Test Meeting",
        "start_time": "2025-01-15T10:00:00Z",
        "duration": 3600,
        "host_email": "test@example.com"
    }


@pytest.fixture
def mock_recording_response():
    """Mock Zoom recording response"""
    return {
        "recording_files": [
            {
                "file_type": "transcript",
                "download_url": "https://zoom.us/rec/download/abc123"
            },
            {
                "file_type": "mp4",
                "download_url": "https://zoom.us/rec/download/video123"
            }
        ]
    }


@pytest.mark.asyncio
async def test_ingest_from_zoom(mock_zoom_response, mock_recording_response):
    """Test Zoom meeting ingestion"""
    service = MeetingIngestionService()

    # Mock Zoom connector
    with patch('app.services.meeting_ingestion_service.ZoomConnector') as MockConnector:
        mock_zoom = AsyncMock()
        mock_zoom.__aenter__.return_value = mock_zoom
        mock_zoom.__aexit__.return_value = None

        mock_zoom.get_meeting.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data=mock_zoom_response
        )
        mock_zoom.get_recording.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data=mock_recording_response
        )
        mock_zoom.get_meeting_participants.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data={"participants": []}
        )

        MockConnector.return_value = mock_zoom

        # Ingest meeting
        meeting, is_duplicate = await service.ingest_from_zoom(
            workspace_id=uuid4(),
            founder_id=uuid4(),
            meeting_id="123456789",
            credentials={"access_token": "test_token"}
        )

        # Assertions
        assert meeting is not None
        assert meeting.source == MeetingSource.ZOOM
        assert meeting.title == "Test Meeting"
        assert is_duplicate == False


@pytest.mark.asyncio
async def test_deduplication():
    """Test that duplicate meetings are detected"""
    service = MeetingIngestionService()

    # Mock finding existing meeting
    with patch.object(service, '_find_by_hash', return_value=Mock(id=uuid4())):
        with patch('app.services.meeting_ingestion_service.ZoomConnector'):
            result = await service.ingest_from_zoom(
                workspace_id=uuid4(),
                founder_id=uuid4(),
                meeting_id="123456789",
                credentials={"access_token": "test_token"}
            )

            meeting, is_duplicate = result
            assert is_duplicate == True


@pytest.mark.asyncio
async def test_transcript_chunking():
    """Test transcript is properly chunked"""
    service = MeetingIngestionService()

    # Create long transcript
    long_transcript = " ".join(["word"] * 2000)

    chunks = service._chunk_transcript(long_transcript, chunk_size=500)

    assert len(chunks) > 1
    assert all(chunk.chunk_index == i for i, chunk in enumerate(chunks))
    assert all(len(chunk.text.split()) <= 500 for chunk in chunks)


def test_meeting_hash_generation():
    """Test meeting hash generation"""
    service = MeetingIngestionService()

    hash1 = service._generate_meeting_hash(MeetingSource.ZOOM, "meeting123")
    hash2 = service._generate_meeting_hash(MeetingSource.ZOOM, "meeting123")
    hash3 = service._generate_meeting_hash(MeetingSource.ZOOM, "meeting456")

    # Same inputs should produce same hash
    assert hash1 == hash2

    # Different inputs should produce different hash
    assert hash1 != hash3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
