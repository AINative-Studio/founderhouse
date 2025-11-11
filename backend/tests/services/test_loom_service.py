"""
Tests for Loom Service with MCP Integration and Otter Fallback
TDD approach - tests written first
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from uuid import uuid4, UUID
import time

from app.services.loom_service import LoomService
from app.models.loom_video import (
    LoomVideoIngestRequest,
    LoomVideoResponse,
    LoomVideoStatus,
    LoomVideoType,
    LoomSummarizeRequest,
    LoomVideoSummary
)
from app.mcp.loom_client import LoomVideoData, LoomTranscriptData


@pytest.fixture
def loom_service():
    """Loom service fixture"""
    return LoomService()


@pytest.fixture
def sample_ingest_request():
    """Sample video ingest request"""
    return LoomVideoIngestRequest(
        workspace_id=uuid4(),
        founder_id=uuid4(),
        video_url="https://www.loom.com/share/abc123video",
        video_id="abc123video",
        title="Test Video",
        description="Test description",
        video_type=LoomVideoType.PRODUCT_DEMO,
        auto_summarize=True,
        notify_on_complete=False
    )


@pytest.fixture
def sample_loom_video_data():
    """Sample Loom video data from MCP"""
    return LoomVideoData(
        video_id="abc123video",
        title="Product Demo Video",
        description="Demo of new features",
        duration_seconds=300,
        thumbnail_url="https://cdn.loom.com/thumbnails/abc123.jpg",
        video_url="https://www.loom.com/share/abc123video",
        created_at=datetime.utcnow(),
        owner_name="John Doe",
        owner_email="john@example.com"
    )


@pytest.fixture
def sample_loom_transcript():
    """Sample Loom transcript data"""
    return LoomTranscriptData(
        video_id="abc123video",
        transcript_text="Hello everyone, this is a product demo. We've built some amazing features. "
                       "Action item: Test the new dashboard by Friday. Next steps: Roll out to beta users.",
        words=[
            {"text": "Hello", "start": 0.0, "end": 0.5},
            {"text": "everyone", "start": 0.5, "end": 1.0}
        ],
        language="en"
    )


@pytest.fixture
def sample_otter_transcript():
    """Sample Otter fallback transcript"""
    return {
        "transcript": {
            "text": "This is an Otter generated transcript for the Loom video. "
                   "It contains all the spoken content from the video.",
            "words": [{"word": "This", "start": 0.0, "end": 0.3}]
        }
    }


class TestLoomServiceMCPIntegration:
    """Test Loom service with MCP integration"""

    @pytest.mark.asyncio
    async def test_ingest_video_with_loom_mcp_success(
        self, loom_service, sample_ingest_request, sample_loom_video_data, sample_loom_transcript
    ):
        """Test successful video ingestion via Loom MCP"""
        with patch('app.services.loom_service.LoomMCPClient') as mock_client_class, \
             patch('app.services.loom_service.get_db_context') as mock_db:

            # Setup mock Loom MCP client
            mock_client = AsyncMock()
            mock_client.get_video_details.return_value = sample_loom_video_data
            mock_client.get_video_transcript.return_value = sample_loom_transcript
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Setup mock database
            mock_db_conn = AsyncMock()
            mock_db_conn.execute.return_value.fetchone.side_effect = [
                None,  # No existing video
                Mock(
                    id=uuid4(),
                    workspace_id=str(sample_ingest_request.workspace_id),
                    founder_id=str(sample_ingest_request.founder_id),
                    video_id="abc123video",
                    video_url=str(sample_ingest_request.video_url),
                    title=sample_loom_video_data.title,
                    description=sample_loom_video_data.description,
                    video_type=sample_ingest_request.video_type.value,
                    status=LoomVideoStatus.PENDING.value,
                    thumbnail_url=sample_loom_video_data.thumbnail_url,
                    duration_seconds=sample_loom_video_data.duration_seconds,
                    transcript=None,
                    summary=None,
                    metadata={},
                    error_message=None,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    completed_at=None
                )
            ]
            mock_db.return_value.__aenter__.return_value = mock_db_conn

            result = await loom_service.ingest_video(sample_ingest_request)

            assert result is not None
            assert isinstance(result, LoomVideoResponse)
            assert result.video_id == "abc123video"
            assert result.status in [LoomVideoStatus.PENDING, LoomVideoStatus.TRANSCRIBING]
            mock_client.get_video_details.assert_called_once_with("abc123video")

    @pytest.mark.asyncio
    async def test_ingest_video_loom_fails_otter_fallback_success(
        self, loom_service, sample_ingest_request, sample_otter_transcript
    ):
        """Test Otter fallback when Loom MCP fails"""
        with patch('app.services.loom_service.LoomMCPClient') as mock_loom_client, \
             patch('app.services.loom_service.OtterConnector') as mock_otter_client, \
             patch('app.services.loom_service.get_db_context') as mock_db:

            # Setup Loom MCP to fail
            mock_loom = AsyncMock()
            mock_loom.get_video_details.side_effect = Exception("Loom API unavailable")
            mock_loom_client.return_value.__aenter__.return_value = mock_loom

            # Setup Otter to succeed
            mock_otter = AsyncMock()
            mock_otter.get_speech_transcript.return_value = Mock(
                status=Mock(value="success"),
                data=sample_otter_transcript
            )
            mock_otter_client.return_value.__aenter__.return_value = mock_otter

            # Setup mock database
            mock_db_conn = AsyncMock()
            mock_db_conn.execute.return_value.fetchone.side_effect = [
                None,  # No existing video
                Mock(
                    id=uuid4(),
                    workspace_id=str(sample_ingest_request.workspace_id),
                    founder_id=str(sample_ingest_request.founder_id),
                    video_id="abc123video",
                    video_url=str(sample_ingest_request.video_url),
                    title="Test Video",
                    description="Test description",
                    video_type=sample_ingest_request.video_type.value,
                    status=LoomVideoStatus.TRANSCRIBING.value,
                    thumbnail_url=None,
                    duration_seconds=None,
                    transcript=sample_otter_transcript["transcript"]["text"],
                    summary=None,
                    metadata={"fallback_used": "otter"},
                    error_message=None,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    completed_at=None
                )
            ]
            mock_db.return_value.__aenter__.return_value = mock_db_conn

            result = await loom_service.ingest_video(sample_ingest_request)

            assert result is not None
            # Should have used Otter fallback
            assert result.metadata.get("fallback_used") == "otter"
            mock_loom.get_video_details.assert_called_once()
            mock_otter.get_speech_transcript.assert_called_once()

    @pytest.mark.asyncio
    async def test_transcript_extraction_loom_mcp(
        self, loom_service, sample_loom_transcript
    ):
        """Test transcript extraction via Loom MCP"""
        video_id = "abc123video"

        with patch('app.services.loom_service.LoomMCPClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_video_transcript.return_value = sample_loom_transcript
            mock_client_class.return_value.__aenter__.return_value = mock_client

            transcript = await loom_service._get_transcript_from_loom(video_id)

            assert transcript is not None
            assert "Hello everyone" in transcript
            assert len(transcript) > 0
            mock_client.get_video_transcript.assert_called_once_with(video_id)

    @pytest.mark.asyncio
    async def test_transcript_extraction_otter_fallback(self, loom_service, sample_otter_transcript):
        """Test transcript extraction via Otter fallback"""
        video_id = "abc123video"

        with patch('app.services.loom_service.OtterConnector') as mock_otter_client:
            mock_otter = AsyncMock()
            mock_otter.get_speech_transcript.return_value = Mock(
                status=Mock(value="success"),
                data=sample_otter_transcript
            )
            mock_otter_client.return_value.__aenter__.return_value = mock_otter

            transcript = await loom_service._get_transcript_from_otter(video_id)

            assert transcript is not None
            assert "Otter generated transcript" in transcript
            mock_otter.get_speech_transcript.assert_called_once()

    @pytest.mark.asyncio
    async def test_summarize_video_with_transcript(self, loom_service):
        """Test video summarization with existing transcript"""
        video_id = uuid4()
        request = LoomSummarizeRequest(
            include_action_items=True,
            include_topics=True,
            max_summary_length=500
        )

        with patch('app.services.loom_service.get_db_context') as mock_db, \
             patch.object(loom_service, '_generate_summary', new_callable=AsyncMock) as mock_summarize:

            # Setup mock database with video containing transcript
            mock_db_conn = AsyncMock()
            mock_video_data = Mock(
                id=video_id,
                workspace_id=str(uuid4()),
                founder_id=str(uuid4()),
                video_id="abc123video",
                video_url="https://www.loom.com/share/abc123video",
                title="Test Video",
                description="Test",
                video_type=LoomVideoType.PRODUCT_DEMO.value,
                status=LoomVideoStatus.TRANSCRIBING.value,
                transcript="This is a test transcript with action items. TODO: Complete testing.",
                summary=None,
                thumbnail_url=None,
                duration_seconds=300,
                metadata={},
                error_message=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                completed_at=None
            )
            mock_db_conn.execute.return_value.fetchone.side_effect = [
                mock_video_data,  # Initial fetch
                mock_video_data   # After update
            ]
            mock_db.return_value.__aenter__.return_value = mock_db_conn

            # Mock summary generation
            mock_summarize.return_value = LoomVideoSummary(
                executive_summary="Test summary",
                key_points=["Point 1", "Point 2"],
                action_items=["Complete testing"],
                topics=["Testing", "Product"],
                participants=["Team"],
                duration_minutes=5,
                transcript_length=100
            )

            result = await loom_service.summarize_video(video_id, request)

            assert result is not None
            assert result.status == LoomVideoStatus.COMPLETED
            assert result.summary is not None
            assert len(result.summary.key_points) > 0
            mock_summarize.assert_called_once()

    @pytest.mark.asyncio
    async def test_three_minute_sla_processing(self, loom_service, sample_ingest_request):
        """Test that video processing completes within 3 minutes"""
        start_time = time.time()

        with patch('app.services.loom_service.LoomMCPClient') as mock_loom_client, \
             patch('app.services.loom_service.get_db_context') as mock_db, \
             patch.object(loom_service, '_generate_summary', new_callable=AsyncMock) as mock_summarize:

            # Setup fast mock responses
            mock_client = AsyncMock()
            mock_client.get_video_details.return_value = LoomVideoData(
                video_id="abc123video",
                title="Test",
                description="Test",
                duration_seconds=60,
                thumbnail_url="http://example.com/thumb.jpg",
                video_url="https://www.loom.com/share/abc123video",
                created_at=datetime.utcnow(),
                owner_name="Test",
                owner_email="test@example.com"
            )
            mock_client.get_video_transcript.return_value = LoomTranscriptData(
                video_id="abc123video",
                transcript_text="Short test transcript",
                words=[],
                language="en"
            )
            mock_loom_client.return_value.__aenter__.return_value = mock_client

            # Setup mock database
            mock_db_conn = AsyncMock()
            video_id = uuid4()
            mock_db_conn.execute.return_value.fetchone.side_effect = [
                None,  # No existing
                Mock(id=video_id, video_id="abc123video", workspace_id=str(sample_ingest_request.workspace_id),
                     founder_id=str(sample_ingest_request.founder_id), video_url=str(sample_ingest_request.video_url),
                     title="Test", description="Test", video_type=LoomVideoType.PRODUCT_DEMO.value,
                     status=LoomVideoStatus.PENDING.value, transcript=None, summary=None, thumbnail_url=None,
                     duration_seconds=None, metadata={}, error_message=None, created_at=datetime.utcnow(),
                     updated_at=datetime.utcnow(), completed_at=None),
            ]
            mock_db.return_value.__aenter__.return_value = mock_db_conn

            mock_summarize.return_value = LoomVideoSummary(
                executive_summary="Quick summary",
                key_points=["Point"],
                action_items=[],
                topics=["Topic"],
                participants=[],
                duration_minutes=1,
                transcript_length=20
            )

            # Process video
            result = await loom_service.ingest_video(sample_ingest_request)

            processing_time = time.time() - start_time

            # Should complete within 3 minutes (180 seconds)
            assert processing_time < 180, f"Processing took {processing_time}s, exceeds 3-minute SLA"
            assert result is not None

    @pytest.mark.asyncio
    async def test_duplicate_video_detection(self, loom_service, sample_ingest_request):
        """Test that duplicate videos are detected and not re-ingested"""
        with patch('app.services.loom_service.get_db_context') as mock_db:

            # Setup mock database with existing video
            existing_video = Mock(
                id=uuid4(),
                workspace_id=str(sample_ingest_request.workspace_id),
                founder_id=str(sample_ingest_request.founder_id),
                video_id="abc123video",
                video_url=str(sample_ingest_request.video_url),
                title="Existing Video",
                description="Already ingested",
                video_type=LoomVideoType.PRODUCT_DEMO.value,
                status=LoomVideoStatus.COMPLETED.value,
                transcript="Existing transcript",
                summary=None,
                thumbnail_url=None,
                duration_seconds=300,
                metadata={},
                error_message=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )

            mock_db_conn = AsyncMock()
            mock_db_conn.execute.return_value.fetchone.return_value = existing_video
            mock_db.return_value.__aenter__.return_value = mock_db_conn

            result = await loom_service.ingest_video(sample_ingest_request)

            assert result is not None
            assert result.video_id == "abc123video"
            assert result.status == LoomVideoStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_error_handling_both_sources_fail(self, loom_service, sample_ingest_request):
        """Test error handling when both Loom MCP and Otter fail"""
        with patch('app.services.loom_service.LoomMCPClient') as mock_loom_client, \
             patch('app.services.loom_service.OtterConnector') as mock_otter_client, \
             patch('app.services.loom_service.get_db_context') as mock_db:

            # Both fail
            mock_loom = AsyncMock()
            mock_loom.get_video_details.side_effect = Exception("Loom API down")
            mock_loom_client.return_value.__aenter__.return_value = mock_loom

            mock_otter = AsyncMock()
            mock_otter.get_speech_transcript.side_effect = Exception("Otter API down")
            mock_otter_client.return_value.__aenter__.return_value = mock_otter

            # Setup mock database
            mock_db_conn = AsyncMock()
            mock_db_conn.execute.return_value.fetchone.return_value = None
            mock_db.return_value.__aenter__.return_value = mock_db_conn

            result = await loom_service.ingest_video(sample_ingest_request)

            # Should handle gracefully
            assert result is None or result.status == LoomVideoStatus.FAILED

    @pytest.mark.asyncio
    async def test_summarization_reuses_meeting_logic(self, loom_service):
        """Test that summarization reuses existing meeting summarization logic"""
        transcript = "This is a meeting transcript with action items. TODO: Complete the project by Friday."

        with patch('app.services.loom_service.SummarizationService') as mock_summ_service:
            mock_service = AsyncMock()
            mock_service.summarize_meeting.return_value = {
                "summary": Mock(
                    executive_summary="Project discussion",
                    key_points=["Project deadline", "Action items"],
                    topics_discussed=["Project", "Timeline"]
                ),
                "action_items": [
                    Mock(description="Complete the project by Friday")
                ]
            }
            mock_summ_service.return_value = mock_service

            summary = await loom_service._generate_summary(
                transcript,
                include_action_items=True,
                include_topics=True
            )

            assert summary is not None
            assert isinstance(summary, LoomVideoSummary)
            # Verify meeting summarization service was used
            mock_service.summarize_meeting.assert_called_once()
