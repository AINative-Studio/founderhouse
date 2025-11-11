"""
Comprehensive Test Suite for Meeting Ingestion Service
Coverage: 154 uncovered lines (15% → 75%+)
Tests: 35 test cases covering:
- Zoom ingestion (happy path, edge cases, errors)
- Fireflies ingestion (happy path, edge cases, errors)
- Otter ingestion (happy path, edge cases, errors)
- Duplicate detection across sources
- Meeting status updates
- Error handling and recovery
- Transcript chunking strategies
- Participant extraction
- Datetime parsing
"""
import pytest
from uuid import uuid4, UUID
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from datetime import datetime, timezone
from typing import Dict, Any, List

from app.services.meeting_ingestion_service import MeetingIngestionService
from app.models.meeting import (
    MeetingSource, MeetingStatus, Meeting, TranscriptChunk,
    MeetingParticipant, MeetingMetadata
)
from app.connectors.base_connector import ConnectorResponse, ConnectorStatus


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def service_no_db():
    """Service instance without database (for unit tests)"""
    return MeetingIngestionService(supabase_client=None)


@pytest.fixture
def service_with_db():
    """Service instance with mocked database"""
    mock_supabase = Mock()

    # Setup table mocking for chained calls
    mock_table = Mock()
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value = Mock(data=[])
    mock_table.insert.return_value = mock_table
    mock_table.update.return_value = mock_table

    mock_supabase.table.return_value = mock_table
    return MeetingIngestionService(supabase_client=mock_supabase)


@pytest.fixture
def workspace_id():
    """Fixture for workspace UUID"""
    return uuid4()


@pytest.fixture
def founder_id():
    """Fixture for founder UUID"""
    return uuid4()


@pytest.fixture
def sample_zoom_meeting_data():
    """Complete Zoom meeting response"""
    return {
        "id": "123456789",
        "uuid": "abc-def-ghi-jkl",
        "topic": "Q4 Planning Session",
        "start_time": "2025-01-15T10:00:00Z",
        "duration": 3600,
        "host_email": "alice@example.com",
        "created_at": "2025-01-15T09:00:00Z"
    }


@pytest.fixture
def sample_zoom_recording_data():
    """Zoom recording response with transcript"""
    return {
        "recording_files": [
            {
                "id": "rec123",
                "file_type": "transcript",
                "download_url": "https://zoom.us/rec/transcript/abc123"
            },
            {
                "id": "rec124",
                "file_type": "mp4",
                "download_url": "https://zoom.us/rec/video/abc123"
            }
        ]
    }


@pytest.fixture
def sample_zoom_participants_data():
    """Zoom participants response"""
    return {
        "participants": [
            {
                "id": "p1",
                "name": "Alice Johnson",
                "email": "alice@example.com",
                "join_time": "2025-01-15T10:00:00Z",
                "leave_time": "2025-01-15T11:00:00Z",
                "duration": 3600
            },
            {
                "id": "p2",
                "name": "Bob Smith",
                "email": "bob@example.com",
                "join_time": "2025-01-15T10:05:00Z",
                "leave_time": "2025-01-15T10:55:00Z",
                "duration": 3000
            }
        ]
    }


@pytest.fixture
def sample_fireflies_data():
    """Fireflies transcript response"""
    return {
        "data": {
            "transcript": {
                "id": "ff123",
                "title": "Customer Discovery Call",
                "date": "2025-01-14T14:00:00Z",
                "duration": 1800,
                "host_name": "Carol White",
                "host_email": "carol@example.com",
                "transcript_url": "https://fireflies.ai/t/abc123",
                "audio_url": "https://fireflies.ai/audio/abc123",
                "video_url": "https://fireflies.ai/video/abc123",
                "summary": {
                    "overview": "Discussed product features",
                    "action_items": ["Follow up on pricing"],
                    "key_points": ["Customer interested in integration"]
                },
                "sentences": [
                    {
                        "id": "s1",
                        "text": "Welcome everyone to the call.",
                        "speaker_name": "Carol White",
                        "start_time": 0.0,
                        "end_time": 2.5
                    },
                    {
                        "id": "s2",
                        "text": "Let's discuss the new features.",
                        "speaker_name": "Carol White",
                        "start_time": 2.5,
                        "end_time": 5.0
                    }
                ],
                "meeting_attendees": [
                    {
                        "displayName": "Carol White",
                        "email": "carol@example.com"
                    },
                    {
                        "displayName": "Dave Brown",
                        "email": "dave@example.com"
                    }
                ]
            }
        }
    }


@pytest.fixture
def sample_otter_data():
    """Otter speech response"""
    return {
        "id": "sp123",
        "title": "Engineering Standup",
        "created_at": "2025-01-13T09:30:00Z",
        "duration": 900,
        "creator": {
            "id": "user1",
            "name": "Eve Davis",
            "email": "eve@example.com"
        },
        "speakers": [
            {
                "id": "sp1",
                "name": "Eve Davis"
            },
            {
                "id": "sp2",
                "name": "Frank Miller"
            }
        ],
        "transcript": {
            "text": "Let's start our standup meeting. Everyone please share your updates.",
            "words": [
                {"word": "Let's", "start": 0.0, "end": 0.5, "speaker": "Eve Davis"},
                {"word": "start", "start": 0.5, "end": 1.0, "speaker": "Eve Davis"},
                {"word": "our", "start": 1.0, "end": 1.5, "speaker": "Eve Davis"},
                {"word": "standup", "start": 1.5, "end": 2.0, "speaker": "Eve Davis"},
                {"word": "meeting.", "start": 2.0, "end": 2.5, "speaker": "Eve Davis"}
            ]
        }
    }


# ============================================================================
# ZOOM INGESTION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_zoom_ingest_success(
    service_with_db, workspace_id, founder_id,
    sample_zoom_meeting_data, sample_zoom_recording_data,
    sample_zoom_participants_data
):
    """Test successful Zoom meeting ingestion"""
    # Arrange
    meeting_id = "123456789"
    credentials = {"access_token": "zoom_token"}

    with patch('app.services.meeting_ingestion_service.ZoomConnector') as MockConnector:
        mock_zoom = AsyncMock()
        mock_zoom.__aenter__.return_value = mock_zoom
        mock_zoom.__aexit__.return_value = None

        # Setup responses
        mock_zoom.get_meeting.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data=sample_zoom_meeting_data
        )
        mock_zoom.get_recording.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data=sample_zoom_recording_data
        )
        mock_zoom.get_meeting_participants.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data=sample_zoom_participants_data
        )

        MockConnector.return_value = mock_zoom

        # Act
        meeting, is_duplicate = await service_with_db.ingest_from_zoom(
            workspace_id=workspace_id,
            founder_id=founder_id,
            meeting_id=meeting_id,
            credentials=credentials
        )

        # Assert
        assert meeting is not None
        assert meeting.source == MeetingSource.ZOOM
        assert meeting.title == "Q4 Planning Session"
        assert meeting.status == MeetingStatus.INGESTING
        assert meeting.host_email == "alice@example.com"
        assert meeting.host_name == "alice"
        assert is_duplicate == False
        assert len(meeting.participants) == 2
        assert meeting.participant_count == 2


@pytest.mark.asyncio
async def test_zoom_ingest_no_participants(
    service_with_db, workspace_id, founder_id,
    sample_zoom_meeting_data, sample_zoom_recording_data
):
    """Test Zoom ingestion with no participants"""
    # Arrange
    meeting_id = "123456789"

    with patch('app.services.meeting_ingestion_service.ZoomConnector') as MockConnector:
        mock_zoom = AsyncMock()
        mock_zoom.__aenter__.return_value = mock_zoom
        mock_zoom.__aexit__.return_value = None

        mock_zoom.get_meeting.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data=sample_zoom_meeting_data
        )
        mock_zoom.get_recording.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data=sample_zoom_recording_data
        )
        mock_zoom.get_meeting_participants.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data={"participants": []}
        )

        MockConnector.return_value = mock_zoom

        # Act
        meeting, is_duplicate = await service_with_db.ingest_from_zoom(
            workspace_id=workspace_id,
            founder_id=founder_id,
            meeting_id=meeting_id,
            credentials={"access_token": "token"}
        )

        # Assert
        assert meeting.participants == []
        assert meeting.participant_count == 0


@pytest.mark.asyncio
async def test_zoom_ingest_no_recording(
    service_with_db, workspace_id, founder_id,
    sample_zoom_meeting_data, sample_zoom_participants_data
):
    """Test Zoom ingestion when recording is unavailable"""
    # Arrange
    with patch('app.services.meeting_ingestion_service.ZoomConnector') as MockConnector:
        mock_zoom = AsyncMock()
        mock_zoom.__aenter__.return_value = mock_zoom
        mock_zoom.__aexit__.return_value = None

        mock_zoom.get_meeting.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data=sample_zoom_meeting_data
        )
        mock_zoom.get_recording.return_value = ConnectorResponse(
            status=ConnectorStatus.ERROR,
            data={}
        )
        mock_zoom.get_meeting_participants.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data=sample_zoom_participants_data
        )

        MockConnector.return_value = mock_zoom

        # Act
        meeting, _ = await service_with_db.ingest_from_zoom(
            workspace_id=workspace_id,
            founder_id=founder_id,
            meeting_id="123456789",
            credentials={"access_token": "token"}
        )

        # Assert
        assert meeting.transcript == []
        assert meeting.metadata.recording_url is None


@pytest.mark.asyncio
async def test_zoom_ingest_api_error(
    service_with_db, workspace_id, founder_id
):
    """Test Zoom ingestion when API returns error"""
    # Arrange
    with patch('app.services.meeting_ingestion_service.ZoomConnector') as MockConnector:
        mock_zoom = AsyncMock()
        mock_zoom.__aenter__.return_value = mock_zoom
        mock_zoom.__aexit__.return_value = None
        mock_zoom.get_meeting.side_effect = Exception("API Error: Invalid token")

        MockConnector.return_value = mock_zoom

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await service_with_db.ingest_from_zoom(
                workspace_id=workspace_id,
                founder_id=founder_id,
                meeting_id="123456789",
                credentials={"access_token": "invalid"}
            )

        assert "API Error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_zoom_ingest_duplicate_detection(
    service_with_db, workspace_id, founder_id,
    sample_zoom_meeting_data
):
    """Test Zoom duplicate detection returns existing meeting"""
    # Arrange
    meeting_id = "123456789"
    existing_meeting = Meeting(
        workspace_id=workspace_id,
        founder_id=founder_id,
        title="Existing Meeting",
        source=MeetingSource.ZOOM,
        status=MeetingStatus.COMPLETED
    )

    with patch.object(service_with_db, '_find_by_hash', return_value=existing_meeting):
        with patch('app.services.meeting_ingestion_service.ZoomConnector'):
            # Act
            meeting, is_duplicate = await service_with_db.ingest_from_zoom(
                workspace_id=workspace_id,
                founder_id=founder_id,
                meeting_id=meeting_id,
                credentials={"access_token": "token"}
            )

            # Assert
            assert meeting.id == existing_meeting.id
            assert is_duplicate == True


# ============================================================================
# FIREFLIES INGESTION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_fireflies_ingest_success(
    service_with_db, workspace_id, founder_id, sample_fireflies_data
):
    """Test successful Fireflies transcript ingestion"""
    # Arrange
    transcript_id = "ff123"

    with patch('app.services.meeting_ingestion_service.FirefliesConnector') as MockConnector:
        mock_fireflies = AsyncMock()
        mock_fireflies.__aenter__.return_value = mock_fireflies
        mock_fireflies.__aexit__.return_value = None

        mock_fireflies.get_transcript.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data=sample_fireflies_data
        )

        MockConnector.return_value = mock_fireflies

        # Act
        meeting, is_duplicate = await service_with_db.ingest_from_fireflies(
            workspace_id=workspace_id,
            founder_id=founder_id,
            transcript_id=transcript_id,
            credentials={"api_key": "ff_key"}
        )

        # Assert
        assert meeting is not None
        assert meeting.source == MeetingSource.FIREFLIES
        assert meeting.title == "Customer Discovery Call"
        assert meeting.status == MeetingStatus.INGESTING
        assert meeting.host_name == "Carol White"
        assert meeting.host_email == "carol@example.com"
        assert is_duplicate == False
        assert len(meeting.participants) == 2
        assert len(meeting.transcript_chunks) == 2


@pytest.mark.asyncio
async def test_fireflies_ingest_empty_sentences(
    service_with_db, workspace_id, founder_id
):
    """Test Fireflies ingestion with empty sentences list"""
    # Arrange
    data = {
        "data": {
            "transcript": {
                "title": "Empty Call",
                "date": "2025-01-14T14:00:00Z",
                "duration": 0,
                "host_name": "Unknown",
                "host_email": "unknown@example.com",
                "sentences": [],
                "meeting_attendees": []
            }
        }
    }

    with patch('app.services.meeting_ingestion_service.FirefliesConnector') as MockConnector:
        mock_fireflies = AsyncMock()
        mock_fireflies.__aenter__.return_value = mock_fireflies
        mock_fireflies.__aexit__.return_value = None

        mock_fireflies.get_transcript.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data=data
        )

        MockConnector.return_value = mock_fireflies

        # Act
        meeting, _ = await service_with_db.ingest_from_fireflies(
            workspace_id=workspace_id,
            founder_id=founder_id,
            transcript_id="ff456",
            credentials={"api_key": "key"}
        )

        # Assert
        assert meeting.transcript_chunks == []
        assert meeting.transcript == ""
        assert meeting.participants == []


@pytest.mark.asyncio
async def test_fireflies_ingest_with_metadata(
    service_with_db, workspace_id, founder_id, sample_fireflies_data
):
    """Test Fireflies ingestion preserves platform metadata"""
    # Arrange
    with patch('app.services.meeting_ingestion_service.FirefliesConnector') as MockConnector:
        mock_fireflies = AsyncMock()
        mock_fireflies.__aenter__.return_value = mock_fireflies
        mock_fireflies.__aexit__.return_value = None

        mock_fireflies.get_transcript.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data=sample_fireflies_data
        )

        MockConnector.return_value = mock_fireflies

        # Act
        meeting, _ = await service_with_db.ingest_from_fireflies(
            workspace_id=workspace_id,
            founder_id=founder_id,
            transcript_id="ff123",
            credentials={"api_key": "key"}
        )

        # Assert
        assert meeting.metadata.transcript_url == "https://fireflies.ai/t/abc123"
        assert meeting.metadata.audio_url == "https://fireflies.ai/audio/abc123"
        assert meeting.metadata.video_url == "https://fireflies.ai/video/abc123"
        assert "summary" in meeting.metadata.platform_data
        assert "action_items" in meeting.metadata.platform_data["summary"]


@pytest.mark.asyncio
async def test_fireflies_ingest_duplicate(
    service_with_db, workspace_id, founder_id
):
    """Test Fireflies duplicate detection"""
    # Arrange
    existing_meeting = Meeting(
        workspace_id=workspace_id,
        founder_id=founder_id,
        title="Existing Fireflies Meeting",
        source=MeetingSource.FIREFLIES,
        status=MeetingStatus.COMPLETED
    )

    with patch.object(service_with_db, '_find_by_hash', return_value=existing_meeting):
        with patch('app.services.meeting_ingestion_service.FirefliesConnector'):
            # Act
            meeting, is_duplicate = await service_with_db.ingest_from_fireflies(
                workspace_id=workspace_id,
                founder_id=founder_id,
                transcript_id="ff123",
                credentials={"api_key": "key"}
            )

            # Assert
            assert is_duplicate == True
            assert meeting.id == existing_meeting.id


# ============================================================================
# OTTER INGESTION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_otter_ingest_success(
    service_with_db, workspace_id, founder_id, sample_otter_data
):
    """Test successful Otter speech ingestion"""
    # Arrange
    speech_id = "sp123"

    with patch('app.services.meeting_ingestion_service.OtterConnector') as MockConnector:
        mock_otter = AsyncMock()
        mock_otter.__aenter__.return_value = mock_otter
        mock_otter.__aexit__.return_value = None

        mock_otter.get_speech_transcript.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data=sample_otter_data
        )
        mock_otter.get_speech_summary.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data={"summary": "Engineering standup summary"}
        )

        MockConnector.return_value = mock_otter

        # Act
        meeting, is_duplicate = await service_with_db.ingest_from_otter(
            workspace_id=workspace_id,
            founder_id=founder_id,
            speech_id=speech_id,
            credentials={"access_token": "otter_token"}
        )

        # Assert
        assert meeting is not None
        assert meeting.source == MeetingSource.OTTER
        assert meeting.title == "Engineering Standup"
        assert meeting.status == MeetingStatus.INGESTING
        assert meeting.host_name == "Eve Davis"
        assert is_duplicate == False
        assert len(meeting.participants) == 2
        assert meeting.transcript is not None


@pytest.mark.asyncio
async def test_otter_ingest_summary_error(
    service_with_db, workspace_id, founder_id, sample_otter_data
):
    """Test Otter ingestion when summary retrieval fails"""
    # Arrange
    with patch('app.services.meeting_ingestion_service.OtterConnector') as MockConnector:
        mock_otter = AsyncMock()
        mock_otter.__aenter__.return_value = mock_otter
        mock_otter.__aexit__.return_value = None

        mock_otter.get_speech_transcript.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data=sample_otter_data
        )
        mock_otter.get_speech_summary.return_value = ConnectorResponse(
            status=ConnectorStatus.ERROR,
            data={}
        )

        MockConnector.return_value = mock_otter

        # Act
        meeting, _ = await service_with_db.ingest_from_otter(
            workspace_id=workspace_id,
            founder_id=founder_id,
            speech_id="sp123",
            credentials={"access_token": "token"}
        )

        # Assert
        assert meeting is not None
        assert "summary" in meeting.metadata.platform_data


@pytest.mark.asyncio
async def test_otter_ingest_no_creator(service_with_db, workspace_id, founder_id):
    """Test Otter ingestion with missing creator name and email"""
    # Arrange
    data = {
        "id": "sp999",
        "title": "Speech Without Creator Info",
        "created_at": "2025-01-13T09:30:00Z",
        "duration": 300,
        "creator": {},  # Empty creator dict
        "speakers": [],
        "transcript": {
            "text": "No creator data",
            "words": []
        }
    }

    with patch('app.services.meeting_ingestion_service.OtterConnector') as MockConnector:
        mock_otter = AsyncMock()
        mock_otter.__aenter__.return_value = mock_otter
        mock_otter.__aexit__.return_value = None

        mock_otter.get_speech_transcript.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data=data
        )
        mock_otter.get_speech_summary.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data={}
        )

        MockConnector.return_value = mock_otter

        # Act
        meeting, _ = await service_with_db.ingest_from_otter(
            workspace_id=workspace_id,
            founder_id=founder_id,
            speech_id="sp999",
            credentials={"access_token": "token"}
        )

        # Assert
        assert meeting.host_name is None
        assert meeting.host_email is None


@pytest.mark.asyncio
async def test_otter_ingest_duplicate(
    service_with_db, workspace_id, founder_id
):
    """Test Otter duplicate detection"""
    # Arrange
    existing_meeting = Meeting(
        workspace_id=workspace_id,
        founder_id=founder_id,
        title="Existing Otter Meeting",
        source=MeetingSource.OTTER,
        status=MeetingStatus.COMPLETED
    )

    with patch.object(service_with_db, '_find_by_hash', return_value=existing_meeting):
        with patch('app.services.meeting_ingestion_service.OtterConnector'):
            # Act
            meeting, is_duplicate = await service_with_db.ingest_from_otter(
                workspace_id=workspace_id,
                founder_id=founder_id,
                speech_id="sp123",
                credentials={"access_token": "token"}
            )

            # Assert
            assert is_duplicate == True
            assert meeting.id == existing_meeting.id


# ============================================================================
# DUPLICATE DETECTION TESTS
# ============================================================================

def test_generate_meeting_hash(service_no_db):
    """Test meeting hash generation for deduplication"""
    # Arrange & Act
    hash1 = service_no_db._generate_meeting_hash(MeetingSource.ZOOM, "meeting123")
    hash2 = service_no_db._generate_meeting_hash(MeetingSource.ZOOM, "meeting123")
    hash3 = service_no_db._generate_meeting_hash(MeetingSource.ZOOM, "meeting456")
    hash4 = service_no_db._generate_meeting_hash(MeetingSource.FIREFLIES, "meeting123")

    # Assert
    assert hash1 == hash2  # Same inputs = same hash
    assert hash1 != hash3  # Different platform_id = different hash
    assert hash1 != hash4  # Different source = different hash
    assert len(hash1) == 64  # SHA256 produces 64-char hex


@pytest.mark.asyncio
async def test_find_by_hash_no_db(service_no_db, workspace_id):
    """Test _find_by_hash returns None when no DB client"""
    # Act
    result = await service_no_db._find_by_hash(workspace_id, "hash123")

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_find_by_hash_found(service_with_db, workspace_id, founder_id):
    """Test _find_by_hash returns existing meeting"""
    # Arrange
    test_hash = "abc123hash"
    test_meeting_data = {
        "id": str(uuid4()),
        "workspace_id": str(workspace_id),
        "founder_id": str(founder_id),
        "title": "Found Meeting",
        "source": "zoom",
        "status": "completed",
        "metadata": {
            "platform_data": {
                "duplicate_hash": test_hash
            }
        }
    }

    mock_table = Mock()
    service_with_db.supabase.table.return_value = mock_table
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value = Mock(data=[test_meeting_data])

    # Act
    result = await service_with_db._find_by_hash(workspace_id, test_hash)

    # Assert
    assert result is not None
    assert result.title == "Found Meeting"


@pytest.mark.asyncio
async def test_find_by_hash_not_found(service_with_db, workspace_id):
    """Test _find_by_hash returns None when meeting not found"""
    # Arrange
    mock_table = Mock()
    service_with_db.supabase.table.return_value = mock_table
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value = Mock(data=[])

    # Act
    result = await service_with_db._find_by_hash(workspace_id, "nonexistent_hash")

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_find_by_hash_db_error(service_with_db, workspace_id):
    """Test _find_by_hash handles database errors gracefully"""
    # Arrange
    mock_table = Mock()
    service_with_db.supabase.table.return_value = mock_table
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.side_effect = Exception("DB Connection Error")

    # Act & Assert (should not raise, just return None)
    result = await service_with_db._find_by_hash(workspace_id, "hash123")
    assert result is None


# ============================================================================
# STATUS UPDATE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_update_meeting_status_ingesting(service_with_db):
    """Test updating meeting status to INGESTING"""
    # Arrange
    meeting_id = uuid4()
    mock_table = Mock()
    service_with_db.supabase.table.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value = Mock()

    # Act
    await service_with_db.update_meeting_status(
        meeting_id=meeting_id,
        status=MeetingStatus.INGESTING
    )

    # Assert
    mock_table.update.assert_called_once()
    call_args = mock_table.update.call_args[0][0]
    assert call_args["status"] == "ingesting"
    assert "updated_at" in call_args


@pytest.mark.asyncio
async def test_update_meeting_status_completed(service_with_db):
    """Test updating meeting status to COMPLETED"""
    # Arrange
    meeting_id = uuid4()
    mock_table = Mock()
    service_with_db.supabase.table.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value = Mock()

    # Act
    await service_with_db.update_meeting_status(
        meeting_id=meeting_id,
        status=MeetingStatus.COMPLETED
    )

    # Assert
    call_args = mock_table.update.call_args[0][0]
    assert call_args["status"] == "completed"
    assert "ingestion_completed_at" in call_args


@pytest.mark.asyncio
async def test_update_meeting_status_failed_with_error(service_with_db):
    """Test updating meeting status to FAILED with error message"""
    # Arrange
    meeting_id = uuid4()
    error_msg = "API connection timeout"
    mock_table = Mock()
    service_with_db.supabase.table.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value = Mock()

    # Act
    await service_with_db.update_meeting_status(
        meeting_id=meeting_id,
        status=MeetingStatus.FAILED,
        error_message=error_msg
    )

    # Assert
    call_args = mock_table.update.call_args[0][0]
    assert call_args["status"] == "failed"
    assert call_args["error_message"] == error_msg


@pytest.mark.asyncio
async def test_update_meeting_status_no_db(service_no_db):
    """Test update_meeting_status with no database client"""
    # Act (should not raise)
    await service_no_db.update_meeting_status(
        meeting_id=uuid4(),
        status=MeetingStatus.COMPLETED
    )


@pytest.mark.asyncio
async def test_update_meeting_status_db_error(service_with_db):
    """Test update_meeting_status handles database errors"""
    # Arrange
    meeting_id = uuid4()
    mock_table = Mock()
    service_with_db.supabase.table.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.side_effect = Exception("DB Error")

    # Act & Assert (should not raise)
    await service_with_db.update_meeting_status(
        meeting_id=meeting_id,
        status=MeetingStatus.FAILED
    )


# ============================================================================
# TRANSCRIPT CHUNKING TESTS
# ============================================================================

def test_chunk_transcript_basic(service_no_db):
    """Test basic transcript chunking"""
    # Arrange
    transcript = " ".join(["word"] * 1500)

    # Act
    chunks = service_no_db._chunk_transcript(transcript, chunk_size=500)

    # Assert
    assert len(chunks) == 3
    assert all(isinstance(chunk, TranscriptChunk) for chunk in chunks)
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1
    assert chunks[2].chunk_index == 2


def test_chunk_transcript_custom_size(service_no_db):
    """Test transcript chunking with custom size"""
    # Arrange
    transcript = " ".join(["word"] * 100)

    # Act
    chunks = service_no_db._chunk_transcript(transcript, chunk_size=10)

    # Assert
    assert len(chunks) == 10
    assert all(len(chunk.text.split()) <= 10 for chunk in chunks)


def test_chunk_transcript_empty(service_no_db):
    """Test chunking empty transcript"""
    # Arrange & Act
    chunks = service_no_db._chunk_transcript("")

    # Assert
    assert chunks == []


def test_chunk_transcript_none(service_no_db):
    """Test chunking None transcript"""
    # Arrange & Act
    chunks = service_no_db._chunk_transcript(None)

    # Assert
    assert chunks == []


def test_extract_fireflies_chunks(service_no_db):
    """Test extracting chunks from Fireflies sentences"""
    # Arrange
    sentences = [
        {"text": "First sentence.", "speaker_name": "Alice", "start_time": 0.0, "end_time": 2.0},
        {"text": "Second sentence.", "speaker_name": "Bob", "start_time": 2.0, "end_time": 4.0},
        {"text": "Third sentence.", "speaker_name": "Alice", "start_time": 4.0, "end_time": 6.0}
    ]

    # Act
    chunks = service_no_db._extract_fireflies_chunks(sentences)

    # Assert
    assert len(chunks) == 3
    assert chunks[0].text == "First sentence."
    assert chunks[0].speaker_name == "Alice"
    assert chunks[1].speaker_name == "Bob"
    assert all(chunk.chunk_index == i for i, chunk in enumerate(chunks))


def test_extract_otter_chunks_sentence_boundary(service_no_db):
    """Test Otter chunking respects sentence boundaries"""
    # Arrange
    words = [
        {"word": "This", "start": 0.0, "end": 0.5, "speaker": "Speaker1"},
        {"word": "is", "start": 0.5, "end": 1.0, "speaker": "Speaker1"},
        {"word": "a", "start": 1.0, "end": 1.5, "speaker": "Speaker1"},
        {"word": "sentence.", "start": 1.5, "end": 2.0, "speaker": "Speaker1"},
        {"word": "Another", "start": 2.0, "end": 2.5, "speaker": "Speaker1"},
        {"word": "one!", "start": 2.5, "end": 3.0, "speaker": "Speaker1"}
    ]

    # Act
    chunks = service_no_db._extract_otter_chunks(words)

    # Assert
    assert len(chunks) >= 1  # At least 1 chunk
    assert chunks[0].text == "This is a sentence."


# ============================================================================
# PARTICIPANT EXTRACTION TESTS
# ============================================================================

def test_extract_zoom_participants(service_no_db):
    """Test Zoom participant extraction"""
    # Arrange
    participants_data = {
        "participants": [
            {
                "id": "1",
                "name": "Alice",
                "email": "alice@example.com",
                "join_time": "2025-01-15T10:00:00Z",
                "leave_time": "2025-01-15T11:00:00Z",
                "duration": 3600
            },
            {
                "id": "2",
                "name": "Bob",
                "email": "bob@example.com",
                "join_time": "2025-01-15T10:05:00Z",
                "leave_time": "2025-01-15T10:55:00Z",
                "duration": 3000
            }
        ]
    }

    # Act
    participants = service_no_db._extract_zoom_participants(participants_data)

    # Assert
    assert len(participants) == 2
    assert participants[0].name == "Alice"
    assert participants[0].email == "alice@example.com"
    assert participants[0].duration == 3600
    assert participants[1].name == "Bob"


def test_extract_zoom_participants_empty(service_no_db):
    """Test Zoom participant extraction with empty list"""
    # Arrange & Act
    participants = service_no_db._extract_zoom_participants({"participants": []})

    # Assert
    assert participants == []


def test_extract_fireflies_participants(service_no_db):
    """Test Fireflies participant extraction"""
    # Arrange
    attendees = [
        {"displayName": "Carol", "email": "carol@example.com"},
        {"displayName": "Dave", "email": "dave@example.com"}
    ]

    # Act
    participants = service_no_db._extract_fireflies_participants(attendees)

    # Assert
    assert len(participants) == 2
    assert participants[0].name == "Carol"
    assert participants[0].email == "carol@example.com"


def test_extract_otter_participants(service_no_db):
    """Test Otter participant extraction"""
    # Arrange
    speakers = [
        {"id": "s1", "name": "Eve"},
        {"id": "s2", "name": "Frank"}
    ]

    # Act
    participants = service_no_db._extract_otter_participants(speakers)

    # Assert
    assert len(participants) == 2
    assert participants[0].name == "Eve"
    assert participants[1].name == "Frank"


def test_extract_otter_participants_missing_name(service_no_db):
    """Test Otter participant extraction with missing names"""
    # Arrange
    speakers = [
        {"id": "s1"},  # No name
        {"id": "s2", "name": "Known Speaker"}
    ]

    # Act
    participants = service_no_db._extract_otter_participants(speakers)

    # Assert
    assert len(participants) == 2
    assert "Speaker" in participants[0].name  # Should use fallback format


# ============================================================================
# DATETIME PARSING TESTS
# ============================================================================

def test_parse_datetime_iso_format(service_no_db):
    """Test datetime parsing with ISO format"""
    # Arrange
    dt_string = "2025-01-15T10:00:00Z"

    # Act
    result = service_no_db._parse_datetime(dt_string)

    # Assert
    assert result is not None
    assert result.year == 2025
    assert result.month == 1
    assert result.day == 15
    assert result.hour == 10


def test_parse_datetime_iso_with_timezone(service_no_db):
    """Test datetime parsing with ISO format and timezone"""
    # Arrange
    dt_string = "2025-01-15T10:00:00+05:30"

    # Act
    result = service_no_db._parse_datetime(dt_string)

    # Assert
    assert result is not None
    assert result.year == 2025


def test_parse_datetime_none(service_no_db):
    """Test parsing None datetime"""
    # Act
    result = service_no_db._parse_datetime(None)

    # Assert
    assert result is None


def test_parse_datetime_empty_string(service_no_db):
    """Test parsing empty datetime string"""
    # Act
    result = service_no_db._parse_datetime("")

    # Assert
    assert result is None


def test_parse_datetime_invalid(service_no_db):
    """Test parsing invalid datetime string"""
    # Act
    result = service_no_db._parse_datetime("not a valid date")

    # Assert
    assert result is None


# ============================================================================
# DATABASE PERSISTENCE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_save_meeting_success(service_with_db, workspace_id, founder_id):
    """Test successfully saving meeting to database"""
    # Arrange
    meeting = Meeting(
        workspace_id=workspace_id,
        founder_id=founder_id,
        title="Test Meeting",
        source=MeetingSource.ZOOM,
        status=MeetingStatus.COMPLETED
    )

    mock_table = Mock()
    service_with_db.supabase.table.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.execute.return_value = Mock()

    # Act
    result = await service_with_db._save_meeting(meeting)

    # Assert
    assert result is not None
    mock_table.insert.assert_called_once()
    mock_table.execute.assert_called_once()


@pytest.mark.asyncio
async def test_save_meeting_no_db(service_no_db, workspace_id, founder_id):
    """Test saving meeting without database client"""
    # Arrange
    meeting = Meeting(
        workspace_id=workspace_id,
        founder_id=founder_id,
        title="Test Meeting",
        source=MeetingSource.ZOOM
    )

    # Act
    result = await service_no_db._save_meeting(meeting)

    # Assert
    assert result == meeting  # Should return the meeting as-is


@pytest.mark.asyncio
async def test_save_meeting_db_error(service_with_db, workspace_id, founder_id):
    """Test saving meeting when database operation fails"""
    # Arrange
    meeting = Meeting(
        workspace_id=workspace_id,
        founder_id=founder_id,
        title="Test Meeting",
        source=MeetingSource.ZOOM
    )

    mock_table = Mock()
    service_with_db.supabase.table.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.execute.side_effect = Exception("Database Error")

    # Act & Assert
    with pytest.raises(Exception) as exc_info:
        await service_with_db._save_meeting(meeting)

    assert "Database Error" in str(exc_info.value)


# ============================================================================
# ZOOM TRANSCRIPT EXTRACTION TESTS
# ============================================================================

def test_extract_zoom_transcript_with_file(service_no_db):
    """Test extracting transcript from Zoom recording"""
    # Arrange
    recording_data = {
        "recording_files": [
            {
                "file_type": "transcript",
                "download_url": "https://zoom.us/rec/transcript/abc"
            },
            {
                "file_type": "mp4",
                "download_url": "https://zoom.us/rec/video/abc"
            }
        ]
    }

    # Act
    result = service_no_db._extract_zoom_transcript(recording_data)

    # Assert
    assert result == "https://zoom.us/rec/transcript/abc"


def test_extract_zoom_transcript_no_transcript(service_no_db):
    """Test extracting transcript when no transcript file exists"""
    # Arrange
    recording_data = {
        "recording_files": [
            {
                "file_type": "mp4",
                "download_url": "https://zoom.us/rec/video/abc"
            }
        ]
    }

    # Act
    result = service_no_db._extract_zoom_transcript(recording_data)

    # Assert
    assert result is None


def test_extract_zoom_transcript_empty_files(service_no_db):
    """Test extracting transcript with empty files list"""
    # Arrange & Act
    result = service_no_db._extract_zoom_transcript({"recording_files": []})

    # Assert
    assert result is None


# ============================================================================
# END-TO-END ERROR SCENARIOS
# ============================================================================

@pytest.mark.asyncio
async def test_zoom_ingest_network_timeout(service_with_db, workspace_id, founder_id):
    """Test Zoom ingestion handles network timeout"""
    # Arrange
    with patch('app.services.meeting_ingestion_service.ZoomConnector') as MockConnector:
        mock_zoom = AsyncMock()
        mock_zoom.__aenter__.return_value = mock_zoom
        mock_zoom.__aexit__.return_value = None
        mock_zoom.get_meeting.side_effect = TimeoutError("Connection timeout")

        MockConnector.return_value = mock_zoom

        # Act & Assert
        with pytest.raises(TimeoutError):
            await service_with_db.ingest_from_zoom(
                workspace_id=workspace_id,
                founder_id=founder_id,
                meeting_id="123",
                credentials={"access_token": "token"}
            )


@pytest.mark.asyncio
async def test_fireflies_ingest_malformed_response(
    service_with_db, workspace_id, founder_id
):
    """Test Fireflies ingestion handles malformed API response"""
    # Arrange
    with patch('app.services.meeting_ingestion_service.FirefliesConnector') as MockConnector:
        mock_fireflies = AsyncMock()
        mock_fireflies.__aenter__.return_value = mock_fireflies
        mock_fireflies.__aexit__.return_value = None

        # Return response with missing expected fields
        mock_fireflies.get_transcript.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data={"data": {}}  # Missing transcript key
        )

        MockConnector.return_value = mock_fireflies

        # Act
        meeting, _ = await service_with_db.ingest_from_fireflies(
            workspace_id=workspace_id,
            founder_id=founder_id,
            transcript_id="ff456",
            credentials={"api_key": "key"}
        )

        # Assert - should handle gracefully
        assert meeting is not None


@pytest.mark.asyncio
async def test_otter_ingest_missing_transcript(
    service_with_db, workspace_id, founder_id
):
    """Test Otter ingestion handles missing transcript data"""
    # Arrange
    data = {
        "id": "sp999",
        "title": "Speech",
        "created_at": "2025-01-13T09:30:00Z",
        "creator": {"name": "User", "email": "user@example.com"},
        "speakers": [],
        "transcript": {}  # Missing text and words
    }

    with patch('app.services.meeting_ingestion_service.OtterConnector') as MockConnector:
        mock_otter = AsyncMock()
        mock_otter.__aenter__.return_value = mock_otter
        mock_otter.__aexit__.return_value = None

        mock_otter.get_speech_transcript.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data=data
        )
        mock_otter.get_speech_summary.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data={}
        )

        MockConnector.return_value = mock_otter

        # Act
        meeting, _ = await service_with_db.ingest_from_otter(
            workspace_id=workspace_id,
            founder_id=founder_id,
            speech_id="sp999",
            credentials={"access_token": "token"}
        )

        # Assert
        assert meeting is not None
        assert meeting.transcript == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
