"""
Comprehensive tests for Loom, Feedback, and Voice Command Services
Tests video ingestion, feedback management, and voice command processing
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from uuid import uuid4, UUID

from app.services.loom_service import LoomService
from app.services.feedback_service import FeedbackService
from app.services.voice_command_service import VoiceCommandService
from app.models.loom_video import (
    LoomVideoIngestRequest,
    LoomVideoStatus,
    LoomVideoType,
    LoomSummarizeRequest
)
from app.models.feedback import (
    FeedbackSubmitRequest,
    FeedbackType,
    FeedbackCategory,
    FeedbackStatus,
    FeedbackSentiment
)
from app.models.voice_command import (
    VoiceCommandRequest,
    VoiceTranscriptionRequest,
    VoiceCommandIntent,
    VoiceCommandStatus
)


# ==================== LOOM SERVICE TESTS ====================

class TestLoomService:
    """Test suite for LoomService"""

    @pytest.fixture
    def service(self):
        return LoomService()

    @pytest.fixture
    def workspace_id(self):
        return uuid4()

    @pytest.fixture
    def founder_id(self):
        return uuid4()

    @pytest.fixture
    def mock_video_row(self, workspace_id, founder_id):
        row = MagicMock()
        row.id = uuid4()
        row.workspace_id = str(workspace_id)
        row.founder_id = str(founder_id)
        row.video_id = "test_video_123"
        row.video_url = "https://www.loom.com/share/test_video_123"
        row.title = "Product Demo"
        row.description = "Demo of new feature"
        row.video_type = "product_demo"
        row.status = "pending"
        row.thumbnail_url = None
        row.duration_seconds = None
        row.transcript = None
        row.summary = None
        row.metadata = {}
        row.error_message = None
        row.created_at = datetime.utcnow()
        row.updated_at = datetime.utcnow()
        row.completed_at = None
        return row

    def test_extract_video_id_share_url(self, service):
        """Test extracting video ID from share URL"""
        url = "https://www.loom.com/share/abc123xyz"
        video_id = service._extract_video_id(url)
        assert video_id == "abc123xyz"

    def test_extract_video_id_embed_url(self, service):
        """Test extracting video ID from embed URL"""
        url = "https://www.loom.com/embed/def456uvw"
        video_id = service._extract_video_id(url)
        assert video_id == "def456uvw"

    def test_extract_video_id_invalid_url(self, service):
        """Test invalid URL returns None"""
        url = "https://example.com/video"
        video_id = service._extract_video_id(url)
        assert video_id is None

    @pytest.mark.asyncio
    async def test_ingest_video_success(self, service, workspace_id, founder_id, mock_video_row):
        """Test successful video ingestion"""
        request = LoomVideoIngestRequest(
            workspace_id=workspace_id,
            founder_id=founder_id,
            video_url="https://www.loom.com/share/test_video_123",
            title="Product Demo",
            video_type=LoomVideoType.PRODUCT_DEMO,
            auto_summarize=False
        )

        with patch('app.services.loom_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.side_effect = [None, mock_video_row]  # Not exists, then created
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            video = await service.ingest_video(request)

            assert video is not None
            assert video.video_id == "test_video_123"
            assert video.status == LoomVideoStatus.PENDING

    @pytest.mark.asyncio
    async def test_ingest_video_already_exists(self, service, workspace_id, founder_id, mock_video_row):
        """Test ingesting existing video"""
        request = LoomVideoIngestRequest(
            workspace_id=workspace_id,
            founder_id=founder_id,
            video_url="https://www.loom.com/share/test_video_123"
        )

        with patch('app.services.loom_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = mock_video_row
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_db.return_value.__aenter__.return_value = mock_context

            video = await service.ingest_video(request)

            assert video is not None

    @pytest.mark.asyncio
    async def test_ingest_video_with_auto_summarize(self, service, workspace_id, founder_id, mock_video_row):
        """Test video ingestion with auto-summarize"""
        request = LoomVideoIngestRequest(
            workspace_id=workspace_id,
            founder_id=founder_id,
            video_url="https://www.loom.com/share/test_video_123",
            auto_summarize=True
        )

        with patch('app.services.loom_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.side_effect = [None, mock_video_row]
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            with patch.object(service, '_process_video') as mock_process:
                video = await service.ingest_video(request)

                mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_summarize_video_success(self, service, mock_video_row):
        """Test video summarization"""
        video_id = uuid4()
        mock_video_row.transcript = "This is a test transcript about product features"

        request = LoomSummarizeRequest(
            include_action_items=True,
            include_topics=True
        )

        with patch('app.services.loom_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = mock_video_row
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            video = await service.summarize_video(video_id, request)

            assert video is not None

    @pytest.mark.asyncio
    async def test_summarize_video_no_transcript(self, service, mock_video_row):
        """Test summarization without transcript"""
        video_id = uuid4()
        mock_video_row.transcript = None

        request = LoomSummarizeRequest()

        with patch('app.services.loom_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = mock_video_row
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            with patch.object(service, '_get_transcript', return_value="Mocked transcript"):
                video = await service.summarize_video(video_id, request)

                assert video is not None

    @pytest.mark.asyncio
    async def test_list_videos_with_filters(self, service, workspace_id, founder_id, mock_video_row):
        """Test listing videos with filters"""
        with patch('app.services.loom_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [mock_video_row, mock_video_row]
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_db.return_value.__aenter__.return_value = mock_context

            videos = await service.list_videos(
                workspace_id=workspace_id,
                founder_id=founder_id,
                video_type=LoomVideoType.PRODUCT_DEMO,
                status=LoomVideoStatus.COMPLETED
            )

            assert len(videos) == 2


# ==================== FEEDBACK SERVICE TESTS ====================

class TestFeedbackService:
    """Test suite for FeedbackService"""

    @pytest.fixture
    def service(self):
        return FeedbackService()

    @pytest.fixture
    def workspace_id(self):
        return uuid4()

    @pytest.fixture
    def founder_id(self):
        return uuid4()

    @pytest.fixture
    def mock_feedback_row(self, workspace_id, founder_id):
        row = MagicMock()
        row.id = uuid4()
        row.workspace_id = str(workspace_id)
        row.founder_id = str(founder_id)
        row.feedback_type = "bug_report"
        row.category = "platform"
        row.title = "Bug in dashboard"
        row.description = "The dashboard is showing incorrect data"
        row.status = "new"
        row.sentiment = "negative"
        row.context = {}
        row.rating = 2
        row.attachments = []
        row.contact_for_followup = True
        row.admin_notes = None
        row.priority_score = 0.8
        row.related_tasks = []
        row.upvotes = 0
        row.created_at = datetime.utcnow()
        row.updated_at = datetime.utcnow()
        row.resolved_at = None
        return row

    def test_analyze_sentiment_positive(self, service):
        """Test positive sentiment analysis"""
        text = "This is great and awesome! I love this feature."
        sentiment = service._analyze_sentiment(text)
        assert sentiment == FeedbackSentiment.POSITIVE

    def test_analyze_sentiment_negative(self, service):
        """Test negative sentiment analysis"""
        text = "This is terrible and broken. Major bug in the system."
        sentiment = service._analyze_sentiment(text)
        assert sentiment == FeedbackSentiment.NEGATIVE

    def test_analyze_sentiment_neutral(self, service):
        """Test neutral sentiment analysis"""
        text = "This is a feature request for better documentation."
        sentiment = service._analyze_sentiment(text)
        assert sentiment == FeedbackSentiment.NEUTRAL

    def test_calculate_priority_bug_report(self, service):
        """Test priority calculation for bug report"""
        score = service._calculate_priority(
            feedback_type=FeedbackType.BUG_REPORT,
            sentiment=FeedbackSentiment.NEGATIVE,
            rating=1
        )
        assert score > 0.7  # High priority

    def test_calculate_priority_praise(self, service):
        """Test priority calculation for praise"""
        score = service._calculate_priority(
            feedback_type=FeedbackType.PRAISE,
            sentiment=FeedbackSentiment.POSITIVE,
            rating=5
        )
        assert score < 0.5  # Low priority

    @pytest.mark.asyncio
    async def test_submit_feedback_success(self, service, workspace_id, founder_id, mock_feedback_row):
        """Test successful feedback submission"""
        request = FeedbackSubmitRequest(
            workspace_id=workspace_id,
            founder_id=founder_id,
            feedback_type=FeedbackType.BUG_REPORT,
            category=FeedbackCategory.INTEGRATIONS,
            title="Bug in dashboard",
            description="Dashboard showing incorrect data",
            rating=2
        )

        with patch('app.services.feedback_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = mock_feedback_row
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            with patch.object(service, '_notify_high_priority_feedback'):
                feedback = await service.submit_feedback(request)

                assert feedback is not None
                assert feedback.feedback_type == FeedbackType.BUG_REPORT

    @pytest.mark.asyncio
    async def test_submit_high_priority_feedback(self, service, workspace_id, founder_id, mock_feedback_row):
        """Test high priority feedback triggers notification"""
        request = FeedbackSubmitRequest(
            workspace_id=workspace_id,
            founder_id=founder_id,
            feedback_type=FeedbackType.COMPLAINT,
            category=FeedbackCategory.INTEGRATIONS,
            title="Critical issue",
            description="System is completely broken and unusable",
            rating=1
        )

        with patch('app.services.feedback_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = mock_feedback_row
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            with patch.object(service, '_notify_high_priority_feedback') as mock_notify:
                feedback = await service.submit_feedback(request)

                mock_notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_feedback_status(self, service, mock_feedback_row):
        """Test updating feedback status"""
        feedback_id = uuid4()

        with patch('app.services.feedback_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = mock_feedback_row
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            feedback = await service.update_feedback_status(
                feedback_id,
                FeedbackStatus.IN_PROGRESS,
                admin_notes="Investigating the issue"
            )

            assert feedback is not None

    @pytest.mark.asyncio
    async def test_upvote_feedback(self, service):
        """Test upvoting feedback"""
        feedback_id = uuid4()

        with patch('app.services.feedback_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_context.execute = AsyncMock()
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            result = await service.upvote_feedback(feedback_id)

            assert result is True

    @pytest.mark.asyncio
    async def test_get_analytics(self, service, workspace_id):
        """Test getting feedback analytics"""
        with patch('app.services.feedback_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()

            # Mock various query results
            mock_result.fetchone.side_effect = [
                (100,),  # Total count
                (4.2,)   # Average rating
            ]
            mock_result.fetchall.side_effect = [
                [("bug_report", 30), ("feature_request", 70)],  # By type
                [("platform", 50), ("api", 50)],  # By category
                [("new", 20), ("in_progress", 80)],  # By status
                [("positive", 60), ("negative", 40)]  # By sentiment
            ]

            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_db.return_value.__aenter__.return_value = mock_context

            analytics = await service.get_analytics(workspace_id, days=30)

            assert analytics.total_feedback == 100
            assert analytics.average_rating == 4.2


# ==================== VOICE COMMAND SERVICE TESTS ====================

class TestVoiceCommandService:
    """Test suite for VoiceCommandService"""

    @pytest.fixture
    def service(self):
        return VoiceCommandService()

    @pytest.fixture
    def workspace_id(self):
        return uuid4()

    @pytest.fixture
    def founder_id(self):
        return uuid4()

    def test_recognize_intent_create_task(self, service):
        """Test recognizing create task intent"""
        transcript = "Create a task to follow up with investors by Friday"
        intent, confidence = service._recognize_intent(transcript)

        assert intent == VoiceCommandIntent.CREATE_TASK
        assert confidence > 0.6

    def test_recognize_intent_schedule_meeting(self, service):
        """Test recognizing schedule meeting intent"""
        transcript = "Schedule a meeting with the team tomorrow at 2pm"
        intent, confidence = service._recognize_intent(transcript)

        assert intent == VoiceCommandIntent.SCHEDULE_MEETING
        assert confidence > 0.6

    def test_recognize_intent_get_summary(self, service):
        """Test recognizing get summary intent"""
        transcript = "Summarize what happened today"
        intent, confidence = service._recognize_intent(transcript)

        assert intent == VoiceCommandIntent.GET_SUMMARY
        assert confidence > 0.6

    def test_recognize_intent_check_metrics(self, service):
        """Test recognizing check metrics intent"""
        transcript = "Show me the latest KPIs and metrics"
        intent, confidence = service._recognize_intent(transcript)

        assert intent == VoiceCommandIntent.CHECK_METRICS
        assert confidence > 0.6

    def test_recognize_intent_unknown(self, service):
        """Test unknown intent"""
        transcript = "This is some random text without clear intent"
        intent, confidence = service._recognize_intent(transcript)

        assert intent == VoiceCommandIntent.UNKNOWN
        assert confidence < 0.5

    def test_extract_entities_create_task(self, service):
        """Test entity extraction for create task"""
        transcript = "Create a task to review Q1 budget"
        intent = VoiceCommandIntent.CREATE_TASK
        entities = service._extract_entities(transcript, intent)

        assert "task" in entities
        assert "review q1 budget" in entities["task"]

    def test_extract_entities_send_message(self, service):
        """Test entity extraction for send message"""
        transcript = "Send message about the new feature launch"
        intent = VoiceCommandIntent.SEND_MESSAGE
        entities = service._extract_entities(transcript, intent)

        assert "message" in entities

    @pytest.mark.asyncio
    async def test_transcribe_audio_success(self, service, workspace_id, founder_id):
        """Test audio transcription"""
        request = VoiceTranscriptionRequest(
            workspace_id=workspace_id,
            founder_id=founder_id,
            audio_base64="fake_audio_data"
        )

        result = await service.transcribe_audio(request)

        assert result is not None
        assert result.transcript is not None
        assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_process_command_with_transcript(self, service, workspace_id, founder_id):
        """Test processing command with existing transcript"""
        request = VoiceCommandRequest(
            workspace_id=workspace_id,
            founder_id=founder_id,
            transcript="Create a task to prepare investor update"
        )

        with patch('app.services.voice_command_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            command_id = uuid4()
            mock_result.fetchone.return_value = (command_id, datetime.utcnow())
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            response = await service.process_command(request)

            assert response is not None
            assert response.intent == VoiceCommandIntent.CREATE_TASK
            assert response.status == VoiceCommandStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_process_command_with_audio(self, service, workspace_id, founder_id):
        """Test processing command from audio"""
        request = VoiceCommandRequest(
            workspace_id=workspace_id,
            founder_id=founder_id,
            audio_base64="fake_audio_data"
        )

        with patch('app.services.voice_command_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()
            command_id = uuid4()
            mock_result.fetchone.return_value = (command_id, datetime.utcnow())
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_context.commit = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_context

            with patch.object(service, 'transcribe_audio') as mock_transcribe:
                from app.models.voice_command import VoiceTranscriptionResponse
                mock_transcribe.return_value = VoiceTranscriptionResponse(
                    workspace_id=workspace_id,
                    founder_id=founder_id,
                    transcript="Check metrics",
                    confidence=0.9,
                    language="en",
                    duration_seconds=2.5
                )

                response = await service.process_command(request)

                assert response is not None
                mock_transcribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_command_create_task(self, service, workspace_id, founder_id):
        """Test executing create task command"""
        action, result = await service._execute_command(
            command_id=uuid4(),
            intent=VoiceCommandIntent.CREATE_TASK,
            entities={"task": "Review budget"},
            workspace_id=workspace_id,
            founder_id=founder_id
        )

        assert "Created task" in action
        assert "task_id" in result

    @pytest.mark.asyncio
    async def test_execute_command_get_summary(self, service, workspace_id, founder_id):
        """Test executing get summary command"""
        action, result = await service._execute_command(
            command_id=uuid4(),
            intent=VoiceCommandIntent.GET_SUMMARY,
            entities={},
            workspace_id=workspace_id,
            founder_id=founder_id
        )

        assert "briefing" in action.lower()

    @pytest.mark.asyncio
    async def test_get_command_history(self, service, workspace_id, founder_id):
        """Test getting command history"""
        with patch('app.services.voice_command_service.get_db_context') as mock_db:
            mock_context = AsyncMock()
            mock_result = MagicMock()

            # Mock command row
            row = MagicMock()
            row.id = uuid4()
            row.workspace_id = str(workspace_id)
            row.founder_id = str(founder_id)
            row.transcript = "Check metrics"
            row.intent = "check_metrics"
            row.confidence = 0.9
            row.status = "completed"
            row.extracted_entities = {}
            row.action_taken = "Retrieved KPI metrics"
            row.result = {}
            row.processing_time_ms = 500
            row.created_at = datetime.utcnow()
            row.updated_at = datetime.utcnow()

            mock_result.fetchall.return_value = [row]
            mock_context.execute = AsyncMock(return_value=mock_result)
            mock_db.return_value.__aenter__.return_value = mock_context

            commands = await service.get_command_history(workspace_id, founder_id, limit=10)

            assert len(commands) == 1
            assert commands[0].intent == VoiceCommandIntent.CHECK_METRICS
