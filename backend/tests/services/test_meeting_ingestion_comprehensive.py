"""
Comprehensive tests for Meeting Ingestion Service
Covers all major code paths, edge cases, and error scenarios
Target: 100% coverage of meeting_ingestion_service.py
"""
import pytest
from uuid import uuid4, UUID
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from app.services.meeting_ingestion_service import MeetingIngestionService
from app.models.meeting import (
    MeetingSource, MeetingStatus, Meeting, TranscriptChunk, MeetingParticipant
)
from app.connectors.base_connector import ConnectorResponse, ConnectorStatus


@pytest.fixture
def service():
    """Create service instance without Supabase"""
    return MeetingIngestionService(supabase_client=None)


@pytest.fixture
def service_with_db():
    """Create service instance with mocked Supabase"""
    mock_supabase = Mock()
    mock_supabase.table = Mock()
    return MeetingIngestionService(supabase_client=mock_supabase)


@pytest.fixture
def workspace_id():
    return uuid4()


@pytest.fixture
def founder_id():
    return uuid4()


@pytest.fixture
def mock_zoom_meeting_data():
    """Complete Zoom meeting response"""
    return {
        "id": "123456789",
        "uuid": "abc-def-ghi-jkl",
        "topic": "Q4 Planning Meeting",
        "start_time": "2025-01-15T10:00:00Z",
        "duration": 3600,
        "host_email": "host@example.com",
        "host_name": "John Host"
    }


@pytest.fixture
def mock_zoom_recording_data():
    """Zoom recording with transcript"""
    return {
        "recording_files": [
            {
                "file_type": "transcript",
                "download_url": "https://zoom.us/rec/download/transcript123.vtt"
            },
            {
                "file_type": "mp4",
                "download_url": "https://zoom.us/rec/download/video123.mp4"
            }
        ]
    }


@pytest.fixture
def mock_zoom_participants_data():
    """Zoom participants list"""
    return {
        "participants": [
            {
                "name": "John Doe",
                "email": "john@example.com",
                "join_time": "2025-01-15T10:00:00Z",
                "leave_time": "2025-01-15T11:00:00Z",
                "duration": 3600
            },
            {
                "name": "Jane Smith",
                "email": "jane@example.com",
                "join_time": "2025-01-15T10:05:00Z",
                "leave_time": "2025-01-15T10:55:00Z",
                "duration": 3000
            }
        ]
    }


@pytest.fixture
def mock_fireflies_transcript_data():
    """Fireflies transcript response"""
    return {
        "data": {
            "transcript": {
                "id": "ff-transcript-123",
                "title": "Sales Sync Meeting",
                "date": "2025-01-15T14:00:00Z",
                "duration": 1800,
                "host_name": "Sales Manager",
                "host_email": "sales@example.com",
                "transcript_url": "https://app.fireflies.ai/transcript/123",
                "audio_url": "https://fireflies.ai/audio/123.mp3",
                "video_url": "https://fireflies.ai/video/123.mp4",
                "sentences": [
                    {
                        "text": "Welcome to the meeting everyone.",
                        "speaker_name": "John",
                        "start_time": 0.0,
                        "end_time": 2.5
                    },
                    {
                        "text": "Let's discuss the quarterly numbers.",
                        "speaker_name": "John",
                        "start_time": 2.5,
                        "end_time": 5.0
                    },
                    {
                        "text": "Revenue is up 20% this quarter.",
                        "speaker_name": "Jane",
                        "start_time": 5.0,
                        "end_time": 7.5
                    }
                ],
                "meeting_attendees": [
                    {"displayName": "John Doe", "email": "john@example.com"},
                    {"displayName": "Jane Smith", "email": "jane@example.com"}
                ],
                "summary": {
                    "overview": "Discussed quarterly revenue",
                    "action_items": ["Follow up on Q4 targets"]
                }
            }
        }
    }


@pytest.fixture
def mock_otter_speech_data():
    """Otter speech transcript response"""
    return {
        "id": "otter-speech-456",
        "title": "Product Review",
        "created_at": "2025-01-15T16:00:00Z",
        "duration": 2400,
        "creator": {
            "name": "Product Manager",
            "email": "pm@example.com"
        },
        "transcript": {
            "text": "This is the full transcript text from Otter.",
            "words": [
                {"word": "This", "start": 0.0, "end": 0.5, "speaker": "Speaker 1"},
                {"word": "is", "start": 0.5, "end": 0.8, "speaker": "Speaker 1"},
                {"word": "the", "start": 0.8, "end": 1.0, "speaker": "Speaker 1"},
                # Add more words to test chunking
            ] + [
                {"word": f"word{i}", "start": i, "end": i+0.5, "speaker": "Speaker 1"}
                for i in range(100)
            ]
        },
        "speakers": [
            {"id": "1", "name": "Speaker 1"},
            {"id": "2", "name": "Speaker 2"}
        ]
    }


# ==================== ZOOM INGESTION TESTS ====================

@pytest.mark.asyncio
async def test_ingest_from_zoom_success(
    service_with_db,
    workspace_id,
    founder_id,
    mock_zoom_meeting_data,
    mock_zoom_recording_data,
    mock_zoom_participants_data
):
    """Test successful Zoom meeting ingestion with all data"""
    with patch('app.services.meeting_ingestion_service.ZoomConnector') as MockConnector:
        mock_zoom = AsyncMock()
        mock_zoom.__aenter__.return_value = mock_zoom
        mock_zoom.__aexit__.return_value = None

        mock_zoom.get_meeting.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data=mock_zoom_meeting_data
        )
        mock_zoom.get_recording.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data=mock_zoom_recording_data
        )
        mock_zoom.get_meeting_participants.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data=mock_zoom_participants_data
        )

        MockConnector.return_value = mock_zoom

        # Mock database operations
        service_with_db.supabase.table.return_value.insert.return_value.execute.return_value = Mock(
            data=[{"id": str(uuid4())}]
        )

        meeting, is_duplicate = await service_with_db.ingest_from_zoom(
            workspace_id=workspace_id,
            founder_id=founder_id,
            meeting_id="123456789",
            credentials={"access_token": "test_token"}
        )

        assert meeting is not None
        assert meeting.source == MeetingSource.ZOOM
        assert meeting.title == "Q4 Planning Meeting"
        assert meeting.host_email == "host@example.com"
        assert meeting.participant_count == 2
        assert is_duplicate is False


@pytest.mark.asyncio
async def test_ingest_from_zoom_duplicate_detected(service, workspace_id, founder_id):
    """Test duplicate Zoom meeting detection"""
    existing_meeting = Meeting(
        workspace_id=workspace_id,
        founder_id=founder_id,
        title="Existing Meeting",
        source=MeetingSource.ZOOM,
        status=MeetingStatus.COMPLETED
    )

    with patch.object(service, '_find_by_hash', return_value=existing_meeting):
        meeting, is_duplicate = await service.ingest_from_zoom(
            workspace_id=workspace_id,
            founder_id=founder_id,
            meeting_id="123456789",
            credentials={"access_token": "test_token"}
        )

        assert meeting == existing_meeting
        assert is_duplicate is True


@pytest.mark.asyncio
async def test_ingest_from_zoom_no_recording(
    service,
    workspace_id,
    founder_id,
    mock_zoom_meeting_data,
    mock_zoom_participants_data
):
    """Test Zoom ingestion when recording is not available"""
    with patch('app.services.meeting_ingestion_service.ZoomConnector') as MockConnector:
        mock_zoom = AsyncMock()
        mock_zoom.__aenter__.return_value = mock_zoom
        mock_zoom.__aexit__.return_value = None

        mock_zoom.get_meeting.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data=mock_zoom_meeting_data
        )
        mock_zoom.get_recording.return_value = ConnectorResponse(
            status=ConnectorStatus.ERROR,
            data={},
            message="Recording not available"
        )
        mock_zoom.get_meeting_participants.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data=mock_zoom_participants_data
        )

        MockConnector.return_value = mock_zoom

        meeting, is_duplicate = await service.ingest_from_zoom(
            workspace_id=workspace_id,
            founder_id=founder_id,
            meeting_id="123456789",
            credentials={"access_token": "test_token"}
        )

        assert meeting is not None
        assert meeting.transcript is None
        assert len(meeting.transcript_chunks) == 0


@pytest.mark.asyncio
async def test_ingest_from_zoom_connection_error(service, workspace_id, founder_id):
    """Test Zoom ingestion with connection error"""
    with patch('app.services.meeting_ingestion_service.ZoomConnector') as MockConnector:
        MockConnector.side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Connection failed"):
            await service.ingest_from_zoom(
                workspace_id=workspace_id,
                founder_id=founder_id,
                meeting_id="123456789",
                credentials={"access_token": "test_token"}
            )


# ==================== FIREFLIES INGESTION TESTS ====================

@pytest.mark.asyncio
async def test_ingest_from_fireflies_success(
    service,
    workspace_id,
    founder_id,
    mock_fireflies_transcript_data
):
    """Test successful Fireflies transcript ingestion"""
    with patch('app.services.meeting_ingestion_service.FirefliesConnector') as MockConnector:
        mock_fireflies = AsyncMock()
        mock_fireflies.__aenter__.return_value = mock_fireflies
        mock_fireflies.__aexit__.return_value = None

        mock_fireflies.get_transcript.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data=mock_fireflies_transcript_data
        )

        MockConnector.return_value = mock_fireflies

        meeting, is_duplicate = await service.ingest_from_fireflies(
            workspace_id=workspace_id,
            founder_id=founder_id,
            transcript_id="ff-transcript-123",
            credentials={"api_key": "test_key"}
        )

        assert meeting is not None
        assert meeting.source == MeetingSource.FIREFLIES
        assert meeting.title == "Sales Sync Meeting"
        assert meeting.transcript is not None
        assert len(meeting.transcript_chunks) == 3
        assert meeting.participant_count == 2


@pytest.mark.asyncio
async def test_ingest_from_fireflies_duplicate(service, workspace_id, founder_id):
    """Test duplicate Fireflies transcript detection"""
    existing = Meeting(
        workspace_id=workspace_id,
        founder_id=founder_id,
        title="Existing",
        source=MeetingSource.FIREFLIES,
        status=MeetingStatus.COMPLETED
    )

    with patch.object(service, '_find_by_hash', return_value=existing):
        meeting, is_duplicate = await service.ingest_from_fireflies(
            workspace_id=workspace_id,
            founder_id=founder_id,
            transcript_id="ff-transcript-123",
            credentials={"api_key": "test_key"}
        )

        assert is_duplicate is True


@pytest.mark.asyncio
async def test_ingest_from_fireflies_api_error(service, workspace_id, founder_id):
    """Test Fireflies ingestion with API error"""
    with patch('app.services.meeting_ingestion_service.FirefliesConnector') as MockConnector:
        mock_fireflies = AsyncMock()
        mock_fireflies.__aenter__.return_value = mock_fireflies
        mock_fireflies.__aexit__.return_value = None
        mock_fireflies.get_transcript.side_effect = Exception("API error")

        MockConnector.return_value = mock_fireflies

        with pytest.raises(Exception, match="API error"):
            await service.ingest_from_fireflies(
                workspace_id=workspace_id,
                founder_id=founder_id,
                transcript_id="ff-transcript-123",
                credentials={"api_key": "test_key"}
            )


# ==================== OTTER INGESTION TESTS ====================

@pytest.mark.asyncio
async def test_ingest_from_otter_success(
    service,
    workspace_id,
    founder_id,
    mock_otter_speech_data
):
    """Test successful Otter speech ingestion"""
    with patch('app.services.meeting_ingestion_service.OtterConnector') as MockConnector:
        mock_otter = AsyncMock()
        mock_otter.__aenter__.return_value = mock_otter
        mock_otter.__aexit__.return_value = None

        mock_otter.get_speech_transcript.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data=mock_otter_speech_data
        )
        mock_otter.get_speech_summary.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data={"overview": "Product review summary"}
        )

        MockConnector.return_value = mock_otter

        meeting, is_duplicate = await service.ingest_from_otter(
            workspace_id=workspace_id,
            founder_id=founder_id,
            speech_id="otter-speech-456",
            credentials={"api_key": "test_key"}
        )

        assert meeting is not None
        assert meeting.source == MeetingSource.OTTER
        assert meeting.title == "Product Review"
        assert meeting.transcript is not None
        assert len(meeting.transcript_chunks) > 0
        assert meeting.participant_count == 2


@pytest.mark.asyncio
async def test_ingest_from_otter_no_summary(
    service,
    workspace_id,
    founder_id,
    mock_otter_speech_data
):
    """Test Otter ingestion when summary is not available"""
    with patch('app.services.meeting_ingestion_service.OtterConnector') as MockConnector:
        mock_otter = AsyncMock()
        mock_otter.__aenter__.return_value = mock_otter
        mock_otter.__aexit__.return_value = None

        mock_otter.get_speech_transcript.return_value = ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data=mock_otter_speech_data
        )
        mock_otter.get_speech_summary.return_value = ConnectorResponse(
            status=ConnectorStatus.ERROR,
            data={}
        )

        MockConnector.return_value = mock_otter

        meeting, is_duplicate = await service.ingest_from_otter(
            workspace_id=workspace_id,
            founder_id=founder_id,
            speech_id="otter-speech-456",
            credentials={"api_key": "test_key"}
        )

        assert meeting is not None
        assert meeting.metadata.platform_data.get("summary") == {}


@pytest.mark.asyncio
async def test_ingest_from_otter_duplicate(service, workspace_id, founder_id):
    """Test duplicate Otter speech detection"""
    existing = Meeting(
        workspace_id=workspace_id,
        founder_id=founder_id,
        title="Existing",
        source=MeetingSource.OTTER,
        status=MeetingStatus.COMPLETED
    )

    with patch.object(service, '_find_by_hash', return_value=existing):
        meeting, is_duplicate = await service.ingest_from_otter(
            workspace_id=workspace_id,
            founder_id=founder_id,
            speech_id="otter-speech-456",
            credentials={"api_key": "test_key"}
        )

        assert is_duplicate is True


# ==================== HELPER METHOD TESTS ====================

def test_generate_meeting_hash(service):
    """Test meeting hash generation"""
    hash1 = service._generate_meeting_hash(MeetingSource.ZOOM, "meeting123")
    hash2 = service._generate_meeting_hash(MeetingSource.ZOOM, "meeting123")
    hash3 = service._generate_meeting_hash(MeetingSource.ZOOM, "meeting456")
    hash4 = service._generate_meeting_hash(MeetingSource.FIREFLIES, "meeting123")

    # Same inputs produce same hash
    assert hash1 == hash2
    # Different IDs produce different hashes
    assert hash1 != hash3
    # Different sources produce different hashes
    assert hash1 != hash4
    # Hash is 64 characters (SHA256 hex)
    assert len(hash1) == 64


@pytest.mark.asyncio
async def test_find_by_hash_no_supabase(service, workspace_id):
    """Test finding meeting by hash without Supabase"""
    result = await service._find_by_hash(workspace_id, "test_hash")
    assert result is None


@pytest.mark.asyncio
async def test_find_by_hash_with_supabase(service_with_db, workspace_id, founder_id):
    """Test finding meeting by hash with Supabase"""
    meeting_data = {
        "id": str(uuid4()),
        "workspace_id": str(workspace_id),
        "founder_id": str(founder_id),
        "title": "Test Meeting",
        "source": "zoom",
        "status": "completed",
        "metadata": {
            "platform_data": {
                "duplicate_hash": "test_hash"
            }
        }
    }

    service_with_db.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
        data=[meeting_data]
    )

    result = await service_with_db._find_by_hash(workspace_id, "test_hash")
    assert result is not None


@pytest.mark.asyncio
async def test_find_by_hash_not_found(service_with_db, workspace_id):
    """Test finding non-existent hash"""
    service_with_db.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
        data=[]
    )

    result = await service_with_db._find_by_hash(workspace_id, "nonexistent_hash")
    assert result is None


@pytest.mark.asyncio
async def test_find_by_hash_database_error(service_with_db, workspace_id):
    """Test database error when finding hash"""
    service_with_db.supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception(
        "Database error"
    )

    result = await service_with_db._find_by_hash(workspace_id, "test_hash")
    assert result is None


@pytest.mark.asyncio
async def test_save_meeting_no_supabase(service):
    """Test saving meeting without Supabase returns meeting unchanged"""
    meeting = Meeting(
        workspace_id=uuid4(),
        founder_id=uuid4(),
        title="Test",
        source=MeetingSource.ZOOM,
        status=MeetingStatus.COMPLETED
    )

    result = await service._save_meeting(meeting)
    assert result == meeting


@pytest.mark.asyncio
async def test_save_meeting_with_supabase(service_with_db):
    """Test saving meeting to Supabase"""
    meeting = Meeting(
        workspace_id=uuid4(),
        founder_id=uuid4(),
        title="Test Meeting",
        source=MeetingSource.ZOOM,
        status=MeetingStatus.COMPLETED
    )

    service_with_db.supabase.table.return_value.insert.return_value.execute.return_value = Mock()

    result = await service_with_db._save_meeting(meeting)
    assert result == meeting
    service_with_db.supabase.table.assert_called_with("meetings")


@pytest.mark.asyncio
async def test_save_meeting_database_error(service_with_db):
    """Test handling database error when saving"""
    meeting = Meeting(
        workspace_id=uuid4(),
        founder_id=uuid4(),
        title="Test",
        source=MeetingSource.ZOOM,
        status=MeetingStatus.COMPLETED
    )

    service_with_db.supabase.table.return_value.insert.return_value.execute.side_effect = Exception(
        "Insert failed"
    )

    with pytest.raises(Exception, match="Insert failed"):
        await service_with_db._save_meeting(meeting)


def test_chunk_transcript_empty(service):
    """Test chunking empty transcript"""
    chunks = service._chunk_transcript("")
    assert len(chunks) == 0


def test_chunk_transcript_small(service):
    """Test chunking small transcript"""
    transcript = "This is a small transcript."
    chunks = service._chunk_transcript(transcript, chunk_size=10)
    assert len(chunks) == 1
    assert chunks[0].text == transcript
    assert chunks[0].chunk_index == 0


def test_chunk_transcript_large(service):
    """Test chunking large transcript"""
    # Create transcript with 2000 words
    words = [f"word{i}" for i in range(2000)]
    transcript = " ".join(words)

    chunks = service._chunk_transcript(transcript, chunk_size=500)

    assert len(chunks) == 4  # 2000 / 500 = 4 chunks
    assert all(chunk.chunk_index == i for i, chunk in enumerate(chunks))
    # Each chunk except possibly the last should have ~500 words
    assert all(len(chunk.text.split()) <= 500 for chunk in chunks)


def test_extract_zoom_transcript_no_files(service):
    """Test extracting Zoom transcript with no recording files"""
    recording_data = {"recording_files": []}
    result = service._extract_zoom_transcript(recording_data)
    assert result is None


def test_extract_zoom_transcript_no_transcript_file(service):
    """Test extracting Zoom transcript with no transcript file"""
    recording_data = {
        "recording_files": [
            {"file_type": "mp4", "download_url": "https://zoom.us/video.mp4"}
        ]
    }
    result = service._extract_zoom_transcript(recording_data)
    assert result is None


def test_extract_zoom_transcript_success(service):
    """Test successful Zoom transcript extraction"""
    recording_data = {
        "recording_files": [
            {"file_type": "transcript", "download_url": "https://zoom.us/transcript.vtt"},
            {"file_type": "mp4", "download_url": "https://zoom.us/video.mp4"}
        ]
    }
    result = service._extract_zoom_transcript(recording_data)
    assert result == "https://zoom.us/transcript.vtt"


def test_extract_zoom_participants_empty(service):
    """Test extracting Zoom participants from empty list"""
    participants_data = {"participants": []}
    result = service._extract_zoom_participants(participants_data)
    assert len(result) == 0


def test_extract_zoom_participants_success(service):
    """Test successful Zoom participants extraction"""
    participants_data = {
        "participants": [
            {
                "name": "John Doe",
                "email": "john@example.com",
                "join_time": "2025-01-15T10:00:00Z",
                "leave_time": "2025-01-15T11:00:00Z",
                "duration": 3600
            },
            {
                "name": "Jane Smith",
                "email": None,  # Test missing email
                "join_time": "2025-01-15T10:05:00Z",
                "leave_time": None,  # Test missing leave time
                "duration": None
            }
        ]
    }

    result = service._extract_zoom_participants(participants_data)
    assert len(result) == 2
    assert result[0].name == "John Doe"
    assert result[0].email == "john@example.com"
    assert result[1].name == "Jane Smith"
    assert result[1].email is None


def test_extract_fireflies_chunks_empty(service):
    """Test extracting Fireflies chunks from empty sentences"""
    result = service._extract_fireflies_chunks([])
    assert len(result) == 0


def test_extract_fireflies_chunks_success(service):
    """Test successful Fireflies chunks extraction"""
    sentences = [
        {
            "text": "Welcome everyone.",
            "speaker_name": "John",
            "start_time": 0.0,
            "end_time": 2.0
        },
        {
            "text": "Let's begin.",
            "speaker_name": "Jane",
            "start_time": 2.0,
            "end_time": 4.0
        }
    ]

    result = service._extract_fireflies_chunks(sentences)
    assert len(result) == 2
    assert result[0].text == "Welcome everyone."
    assert result[0].speaker_name == "John"
    assert result[0].chunk_index == 0
    assert result[1].chunk_index == 1


def test_extract_fireflies_participants_empty(service):
    """Test extracting Fireflies participants from empty list"""
    result = service._extract_fireflies_participants([])
    assert len(result) == 0


def test_extract_fireflies_participants_success(service):
    """Test successful Fireflies participants extraction"""
    attendees = [
        {"displayName": "John Doe", "email": "john@example.com"},
        {"displayName": "Jane Smith", "email": "jane@example.com"},
        {"email": "noname@example.com"}  # Test missing displayName
    ]

    result = service._extract_fireflies_participants(attendees)
    assert len(result) == 3
    assert result[0].name == "John Doe"
    assert result[2].name == "Unknown"


def test_extract_otter_chunks_empty(service):
    """Test extracting Otter chunks from empty words"""
    result = service._extract_otter_chunks([])
    assert len(result) == 0


def test_extract_otter_chunks_small(service):
    """Test extracting Otter chunks from few words"""
    words = [
        {"word": "Hello", "start": 0.0, "end": 0.5, "speaker": "Speaker 1"},
        {"word": "world", "start": 0.5, "end": 1.0, "speaker": "Speaker 1"}
    ]

    result = service._extract_otter_chunks(words)
    assert len(result) >= 1


def test_extract_otter_chunks_large(service):
    """Test extracting Otter chunks from many words"""
    # Create 100 words to test chunking
    words = [
        {"word": f"word{i}", "start": i, "end": i+0.5, "speaker": "Speaker 1"}
        for i in range(100)
    ]

    result = service._extract_otter_chunks(words)
    assert len(result) >= 2  # Should create multiple chunks


def test_extract_otter_chunks_with_sentence_end(service):
    """Test Otter chunking respects sentence endings"""
    words = [
        {"word": "This", "start": 0.0, "end": 0.5, "speaker": "Speaker 1"},
        {"word": "is", "start": 0.5, "end": 0.8, "speaker": "Speaker 1"},
        {"word": "sentence.", "start": 0.8, "end": 1.5, "speaker": "Speaker 1"},
        {"word": "Another", "start": 1.5, "end": 2.0, "speaker": "Speaker 1"},
        {"word": "sentence!", "start": 2.0, "end": 2.8, "speaker": "Speaker 1"}
    ]

    result = service._extract_otter_chunks(words)
    # Should chunk at sentence boundaries
    assert len(result) >= 2


def test_extract_otter_participants_empty(service):
    """Test extracting Otter participants from empty list"""
    result = service._extract_otter_participants([])
    assert len(result) == 0


def test_extract_otter_participants_success(service):
    """Test successful Otter participants extraction"""
    speakers = [
        {"id": "1", "name": "John Doe"},
        {"id": "2", "name": "Jane Smith"},
        {"id": "3"}  # Test missing name
    ]

    result = service._extract_otter_participants(speakers)
    assert len(result) == 3
    assert result[0].name == "John Doe"
    assert result[2].name == "Speaker 3"


def test_parse_datetime_none(service):
    """Test parsing None datetime"""
    result = service._parse_datetime(None)
    assert result is None


def test_parse_datetime_empty(service):
    """Test parsing empty string"""
    result = service._parse_datetime("")
    assert result is None


def test_parse_datetime_iso_format(service):
    """Test parsing ISO format datetime"""
    dt_string = "2025-01-15T10:00:00Z"
    result = service._parse_datetime(dt_string)
    assert result is not None
    assert isinstance(result, datetime)


def test_parse_datetime_iso_format_with_offset(service):
    """Test parsing ISO format with timezone offset"""
    dt_string = "2025-01-15T10:00:00+00:00"
    result = service._parse_datetime(dt_string)
    assert result is not None


def test_parse_datetime_invalid_format(service):
    """Test parsing invalid datetime format"""
    dt_string = "invalid-date"
    result = service._parse_datetime(dt_string)
    # Should return None on parse failure
    assert result is None


@pytest.mark.asyncio
async def test_update_meeting_status_no_supabase(service):
    """Test updating meeting status without Supabase"""
    await service.update_meeting_status(
        meeting_id=uuid4(),
        status=MeetingStatus.COMPLETED
    )
    # Should not raise error


@pytest.mark.asyncio
async def test_update_meeting_status_completed(service_with_db):
    """Test updating meeting status to completed"""
    meeting_id = uuid4()

    service_with_db.supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock()

    await service_with_db.update_meeting_status(
        meeting_id=meeting_id,
        status=MeetingStatus.COMPLETED
    )

    service_with_db.supabase.table.assert_called_with("meetings")


@pytest.mark.asyncio
async def test_update_meeting_status_with_error(service_with_db):
    """Test updating meeting status with error message"""
    meeting_id = uuid4()

    service_with_db.supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock()

    await service_with_db.update_meeting_status(
        meeting_id=meeting_id,
        status=MeetingStatus.FAILED,
        error_message="Something went wrong"
    )

    # Should not raise error


@pytest.mark.asyncio
async def test_update_meeting_status_database_error(service_with_db):
    """Test handling database error when updating status"""
    meeting_id = uuid4()

    service_with_db.supabase.table.return_value.update.return_value.eq.return_value.execute.side_effect = Exception(
        "Update failed"
    )

    # Should log error but not raise
    await service_with_db.update_meeting_status(
        meeting_id=meeting_id,
        status=MeetingStatus.COMPLETED
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
