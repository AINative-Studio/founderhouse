"""
Voice Command Service Tests
Comprehensive TDD tests for voice command processing service
Tests voice → intent → action flow and latency requirements
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4, UUID
from datetime import datetime

from app.services.voice_command_service import VoiceCommandService
from app.models.voice_command import (
    VoiceCommandRequest,
    VoiceCommandResponse,
    VoiceCommandStatus,
    VoiceCommandIntent,
    VoiceTranscriptionRequest,
    VoiceTranscriptionResponse
)


@pytest.fixture
def mock_zerovoice_client():
    """Mock ZeroVoice MCP client"""
    client = AsyncMock()
    return client


@pytest.fixture
def voice_service(mock_zerovoice_client):
    """Create voice command service with mocked MCP client"""
    return VoiceCommandService(zerovoice_client=mock_zerovoice_client)


@pytest.fixture
def sample_workspace_id():
    """Sample workspace UUID"""
    return uuid4()


@pytest.fixture
def sample_founder_id():
    """Sample founder UUID"""
    return uuid4()


class TestVoiceCommandServiceInitialization:
    """Test service initialization"""

    def test_service_initializes_with_zerovoice_client(self, voice_service, mock_zerovoice_client):
        """Test that service initializes with ZeroVoice client"""
        assert voice_service.zerovoice == mock_zerovoice_client
        assert voice_service.intent_mapping is not None
        assert len(voice_service.intent_mapping) > 0

    def test_service_has_intent_mapping(self, voice_service):
        """Test that service has complete intent mapping"""
        assert "create_task" in voice_service.intent_mapping
        assert "schedule_meeting" in voice_service.intent_mapping
        assert "check_metrics" in voice_service.intent_mapping
        assert "unknown" in voice_service.intent_mapping


class TestTranscribeAudio:
    """Test audio transcription"""

    @pytest.mark.asyncio
    async def test_transcribe_audio_success(
        self, voice_service, mock_zerovoice_client, sample_workspace_id, sample_founder_id
    ):
        """Test successful audio transcription"""
        # Mock ZeroVoice response
        mock_zerovoice_client.transcribe_audio.return_value = {
            "transcript": "Create a task to prepare Q4 presentation",
            "confidence": 0.96,
            "timestamps": None
        }

        request = VoiceTranscriptionRequest(
            workspace_id=sample_workspace_id,
            founder_id=sample_founder_id,
            audio_url="https://example.com/audio.mp3",
            language="en-US"
        )

        result = await voice_service.transcribe_audio(request)

        assert result is not None
        assert isinstance(result, VoiceTranscriptionResponse)
        assert result.transcript == "Create a task to prepare Q4 presentation"
        assert result.confidence == 0.96
        assert result.workspace_id == sample_workspace_id
        assert result.founder_id == sample_founder_id

        # Verify MCP client was called correctly
        mock_zerovoice_client.transcribe_audio.assert_called_once_with(
            audio_url="https://example.com/audio.mp3",
            audio_base64=None,
            language="en-US",
            include_timestamps=False
        )

    @pytest.mark.asyncio
    async def test_transcribe_audio_with_base64(
        self, voice_service, mock_zerovoice_client, sample_workspace_id, sample_founder_id
    ):
        """Test transcription with base64 audio"""
        mock_zerovoice_client.transcribe_audio.return_value = {
            "transcript": "Check metrics",
            "confidence": 0.92
        }

        request = VoiceTranscriptionRequest(
            workspace_id=sample_workspace_id,
            founder_id=sample_founder_id,
            audio_base64="base64encodeddata",
            language="en-US"
        )

        result = await voice_service.transcribe_audio(request)

        assert result is not None
        assert result.transcript == "Check metrics"
        mock_zerovoice_client.transcribe_audio.assert_called_once()

    @pytest.mark.asyncio
    async def test_transcribe_audio_with_timestamps(
        self, voice_service, mock_zerovoice_client, sample_workspace_id, sample_founder_id
    ):
        """Test transcription with word timestamps"""
        mock_zerovoice_client.transcribe_audio.return_value = {
            "transcript": "Schedule meeting",
            "confidence": 0.94,
            "timestamps": [
                {"word": "Schedule", "start": 0.0, "end": 0.5},
                {"word": "meeting", "start": 0.6, "end": 1.0}
            ]
        }

        request = VoiceTranscriptionRequest(
            workspace_id=sample_workspace_id,
            founder_id=sample_founder_id,
            audio_url="https://example.com/audio.mp3",
            include_timestamps=True
        )

        result = await voice_service.transcribe_audio(request)

        assert result.word_timestamps is not None
        assert len(result.word_timestamps) == 2

    @pytest.mark.asyncio
    async def test_transcribe_audio_handles_error(
        self, voice_service, mock_zerovoice_client, sample_workspace_id, sample_founder_id
    ):
        """Test error handling in transcription"""
        mock_zerovoice_client.transcribe_audio.side_effect = Exception("Transcription failed")

        request = VoiceTranscriptionRequest(
            workspace_id=sample_workspace_id,
            founder_id=sample_founder_id,
            audio_url="https://example.com/audio.mp3"
        )

        result = await voice_service.transcribe_audio(request)

        assert result is None


class TestProcessCommand:
    """Test voice command processing"""

    @pytest.mark.asyncio
    @patch('app.services.voice_command_service.get_db_context')
    async def test_process_command_with_transcript(
        self, mock_db_context, voice_service, mock_zerovoice_client,
        sample_workspace_id, sample_founder_id
    ):
        """Test processing command with pre-transcribed text"""
        # Mock ZeroVoice MCP response
        mock_zerovoice_client.process_voice_command.return_value = {
            "transcript": "Create a task to follow up with investors",
            "intent": "create_task",
            "confidence": 0.95,
            "entities": {"task": "follow up with investors"},
            "processing_time_ms": 1200,
            "transcription_time_ms": 0,
            "intent_parsing_time_ms": 1200
        }

        # Mock database
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.fetchone.return_value = (uuid4(), datetime.utcnow())
        mock_db.execute.return_value = mock_result
        mock_db_context.return_value.__aenter__.return_value = mock_db
        mock_db_context.return_value.__aexit__.return_value = None

        request = VoiceCommandRequest(
            workspace_id=sample_workspace_id,
            founder_id=sample_founder_id,
            transcript="Create a task to follow up with investors"
        )

        result = await voice_service.process_command(request)

        assert result is not None
        assert isinstance(result, VoiceCommandResponse)
        assert result.transcript == "Create a task to follow up with investors"
        assert result.intent == VoiceCommandIntent.CREATE_TASK
        assert result.confidence == 0.95
        assert result.status == VoiceCommandStatus.COMPLETED
        assert result.extracted_entities["task"] == "follow up with investors"

        # Verify MCP was called
        mock_zerovoice_client.process_voice_command.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.services.voice_command_service.get_db_context')
    async def test_process_command_with_audio(
        self, mock_db_context, voice_service, mock_zerovoice_client,
        sample_workspace_id, sample_founder_id
    ):
        """Test processing command with audio input"""
        # Mock complete pipeline response
        mock_zerovoice_client.process_voice_command.return_value = {
            "transcript": "Schedule a meeting for tomorrow",
            "intent": "schedule_meeting",
            "confidence": 0.92,
            "entities": {"time": "tomorrow"},
            "processing_time_ms": 2100,
            "transcription_time_ms": 800,
            "intent_parsing_time_ms": 1300
        }

        # Mock database
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.fetchone.return_value = (uuid4(), datetime.utcnow())
        mock_db.execute.return_value = mock_result
        mock_db_context.return_value.__aenter__.return_value = mock_db
        mock_db_context.return_value.__aexit__.return_value = None

        request = VoiceCommandRequest(
            workspace_id=sample_workspace_id,
            founder_id=sample_founder_id,
            audio_url="https://example.com/audio.mp3"
        )

        result = await voice_service.process_command(request)

        assert result is not None
        assert result.intent == VoiceCommandIntent.SCHEDULE_MEETING
        assert "time" in result.extracted_entities

    @pytest.mark.asyncio
    @patch('app.services.voice_command_service.get_db_context')
    async def test_process_command_latency_requirement(
        self, mock_db_context, voice_service, mock_zerovoice_client,
        sample_workspace_id, sample_founder_id
    ):
        """Test that command processing meets < 2.5s latency requirement (PRD)"""
        import time

        # Mock fast response
        mock_zerovoice_client.process_voice_command.return_value = {
            "transcript": "Get my briefing",
            "intent": "get_briefing",
            "confidence": 0.93,
            "entities": {},
            "processing_time_ms": 1500,
            "transcription_time_ms": 0,
            "intent_parsing_time_ms": 1500
        }

        # Mock database
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.fetchone.return_value = (uuid4(), datetime.utcnow())
        mock_db.execute.return_value = mock_result
        mock_db_context.return_value.__aenter__.return_value = mock_db
        mock_db_context.return_value.__aexit__.return_value = None

        request = VoiceCommandRequest(
            workspace_id=sample_workspace_id,
            founder_id=sample_founder_id,
            transcript="Get my briefing"
        )

        start = time.time()
        result = await voice_service.process_command(request)
        elapsed_ms = (time.time() - start) * 1000

        # Verify PRD requirement: < 2.5s end-to-end
        assert result.processing_time_ms < 2500, \
            f"Processing took {result.processing_time_ms}ms, exceeds 2.5s requirement"
        assert elapsed_ms < 3000  # Allow buffer for test overhead

    @pytest.mark.asyncio
    @patch('app.services.voice_command_service.get_db_context')
    async def test_process_command_with_context(
        self, mock_db_context, voice_service, mock_zerovoice_client,
        sample_workspace_id, sample_founder_id
    ):
        """Test processing with contextual information"""
        mock_zerovoice_client.process_voice_command.return_value = {
            "transcript": "Send message to team",
            "intent": "send_message",
            "confidence": 0.89,
            "entities": {"recipient": "team", "message": "Great work"},
            "processing_time_ms": 1400,
            "transcription_time_ms": 0,
            "intent_parsing_time_ms": 1400
        }

        # Mock database
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.fetchone.return_value = (uuid4(), datetime.utcnow())
        mock_db.execute.return_value = mock_result
        mock_db_context.return_value.__aenter__.return_value = mock_db
        mock_db_context.return_value.__aexit__.return_value = None

        context = {"recent_channels": ["#general", "#team"], "timezone": "PST"}

        request = VoiceCommandRequest(
            workspace_id=sample_workspace_id,
            founder_id=sample_founder_id,
            transcript="Send message to team",
            context=context
        )

        result = await voice_service.process_command(request)

        assert result is not None
        assert result.intent == VoiceCommandIntent.SEND_MESSAGE

        # Verify context was passed to MCP
        call_args = mock_zerovoice_client.process_voice_command.call_args
        assert call_args[1]["context"] == context

    @pytest.mark.asyncio
    @patch('app.services.voice_command_service.get_db_context')
    async def test_process_command_unknown_intent(
        self, mock_db_context, voice_service, mock_zerovoice_client,
        sample_workspace_id, sample_founder_id
    ):
        """Test handling of unknown intent"""
        mock_zerovoice_client.process_voice_command.return_value = {
            "transcript": "gibberish nonsense words",
            "intent": "unknown",
            "confidence": 0.25,
            "entities": {},
            "processing_time_ms": 1100,
            "transcription_time_ms": 0,
            "intent_parsing_time_ms": 1100
        }

        # Mock database
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.fetchone.return_value = (uuid4(), datetime.utcnow())
        mock_db.execute.return_value = mock_result
        mock_db_context.return_value.__aenter__.return_value = mock_db
        mock_db_context.return_value.__aexit__.return_value = None

        request = VoiceCommandRequest(
            workspace_id=sample_workspace_id,
            founder_id=sample_founder_id,
            transcript="gibberish nonsense words"
        )

        result = await voice_service.process_command(request)

        assert result is not None
        assert result.intent == VoiceCommandIntent.UNKNOWN
        assert result.confidence < 0.5

    @pytest.mark.asyncio
    async def test_process_command_handles_error(
        self, voice_service, mock_zerovoice_client, sample_workspace_id, sample_founder_id
    ):
        """Test error handling in command processing"""
        mock_zerovoice_client.process_voice_command.side_effect = Exception("Processing failed")

        request = VoiceCommandRequest(
            workspace_id=sample_workspace_id,
            founder_id=sample_founder_id,
            transcript="Test command"
        )

        result = await voice_service.process_command(request)

        assert result is None


class TestExecuteCommand:
    """Test command execution (action routing)"""

    @pytest.mark.asyncio
    async def test_execute_create_task(self, voice_service):
        """Test executing create task action"""
        command_id = uuid4()
        workspace_id = uuid4()
        founder_id = uuid4()

        action, result = await voice_service._execute_command(
            command_id,
            VoiceCommandIntent.CREATE_TASK,
            {"task": "prepare Q4 presentation"},
            workspace_id,
            founder_id
        )

        assert "Created task" in action
        assert "task_id" in result
        assert result["description"] == "prepare Q4 presentation"

    @pytest.mark.asyncio
    async def test_execute_get_summary(self, voice_service):
        """Test executing get summary action"""
        command_id = uuid4()
        workspace_id = uuid4()
        founder_id = uuid4()

        action, result = await voice_service._execute_command(
            command_id,
            VoiceCommandIntent.GET_SUMMARY,
            {},
            workspace_id,
            founder_id
        )

        assert "briefing" in action.lower()
        assert "status" in result

    @pytest.mark.asyncio
    async def test_execute_check_metrics(self, voice_service):
        """Test executing check metrics action"""
        command_id = uuid4()
        workspace_id = uuid4()
        founder_id = uuid4()

        action, result = await voice_service._execute_command(
            command_id,
            VoiceCommandIntent.CHECK_METRICS,
            {},
            workspace_id,
            founder_id
        )

        assert "metrics" in action.lower() or "KPI" in action
        assert "status" in result

    @pytest.mark.asyncio
    async def test_execute_send_message(self, voice_service):
        """Test executing send message action"""
        command_id = uuid4()
        workspace_id = uuid4()
        founder_id = uuid4()

        action, result = await voice_service._execute_command(
            command_id,
            VoiceCommandIntent.SEND_MESSAGE,
            {"message": "Great work team"},
            workspace_id,
            founder_id
        )

        assert "message" in action.lower()
        assert result["message"] == "Great work team"


class TestGetCommandHistory:
    """Test command history retrieval"""

    @pytest.mark.asyncio
    @patch('app.services.voice_command_service.get_db_context')
    async def test_get_command_history(
        self, mock_db_context, voice_service, sample_workspace_id, sample_founder_id
    ):
        """Test retrieving command history"""
        # Mock database results
        mock_db = AsyncMock()
        mock_result = Mock()

        # Create mock rows
        mock_rows = [
            Mock(
                id=uuid4(),
                workspace_id=str(sample_workspace_id),
                founder_id=str(sample_founder_id),
                transcript="Create task",
                intent="create_task",
                confidence=0.95,
                status="completed",
                extracted_entities={"task": "test"},
                action_taken="Created task",
                result={"task_id": "123"},
                processing_time_ms=1500,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        ]

        mock_result.fetchall.return_value = mock_rows
        mock_db.execute.return_value = mock_result
        mock_db_context.return_value.__aenter__.return_value = mock_db
        mock_db_context.return_value.__aexit__.return_value = None

        commands = await voice_service.get_command_history(
            workspace_id=sample_workspace_id,
            founder_id=sample_founder_id,
            limit=20
        )

        assert len(commands) == 1
        assert commands[0].transcript == "Create task"

    @pytest.mark.asyncio
    @patch('app.services.voice_command_service.get_db_context')
    async def test_get_command_history_handles_error(
        self, mock_db_context, voice_service, sample_workspace_id, sample_founder_id
    ):
        """Test error handling in history retrieval"""
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("Database error")
        mock_db_context.return_value.__aenter__.return_value = mock_db
        mock_db_context.return_value.__aexit__.return_value = None

        commands = await voice_service.get_command_history(
            workspace_id=sample_workspace_id,
            founder_id=sample_founder_id
        )

        assert commands == []


class TestIntentMapping:
    """Test intent mapping functionality"""

    def test_intent_mapping_covers_all_intents(self, voice_service):
        """Test that all intents are mapped"""
        expected_intents = [
            "create_task", "schedule_meeting", "get_summary",
            "check_metrics", "send_message", "create_note",
            "get_briefing", "update_status", "unknown"
        ]

        for intent in expected_intents:
            assert intent in voice_service.intent_mapping

    def test_intent_mapping_to_enum(self, voice_service):
        """Test mapping from string to enum"""
        assert voice_service.intent_mapping["create_task"] == VoiceCommandIntent.CREATE_TASK
        assert voice_service.intent_mapping["unknown"] == VoiceCommandIntent.UNKNOWN


class TestIntegration:
    """Integration tests for complete workflows"""

    @pytest.mark.asyncio
    @patch('app.services.voice_command_service.get_db_context')
    async def test_complete_voice_to_action_flow(
        self, mock_db_context, voice_service, mock_zerovoice_client,
        sample_workspace_id, sample_founder_id
    ):
        """Test complete voice → intent → action flow (PRD requirement)"""
        # Mock complete MCP pipeline
        mock_zerovoice_client.process_voice_command.return_value = {
            "transcript": "Create a task to review investor deck",
            "intent": "create_task",
            "confidence": 0.96,
            "entities": {"task": "review investor deck"},
            "processing_time_ms": 1850,
            "transcription_time_ms": 750,
            "intent_parsing_time_ms": 1100
        }

        # Mock database
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.fetchone.return_value = (uuid4(), datetime.utcnow())
        mock_db.execute.return_value = mock_result
        mock_db_context.return_value.__aenter__.return_value = mock_db
        mock_db_context.return_value.__aexit__.return_value = None

        request = VoiceCommandRequest(
            workspace_id=sample_workspace_id,
            founder_id=sample_founder_id,
            audio_url="https://example.com/command.mp3"
        )

        result = await voice_service.process_command(request)

        # Verify complete pipeline
        assert result is not None
        assert result.transcript == "Create a task to review investor deck"
        assert result.intent == VoiceCommandIntent.CREATE_TASK
        assert result.confidence > 0.9
        assert result.status == VoiceCommandStatus.COMPLETED
        assert "task" in result.extracted_entities
        assert result.action_taken is not None
        assert result.result is not None
        assert result.processing_time_ms < 2500  # PRD requirement
