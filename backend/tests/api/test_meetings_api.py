"""
Integration tests for Meeting API endpoints
Tests CRUD operations, summarization, and task creation from meetings
"""
import pytest
from uuid import uuid4
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import status

from app.models.meeting import MeetingSource, MeetingStatus
from app.models.meeting_summary import SummaryGenerationRequest


@pytest.fixture
def mock_meeting_ingestion_service():
    """Mock for MeetingIngestionService"""
    with patch('app.api.v1.meetings.MeetingIngestionService') as mock:
        service_instance = MagicMock()

        # Mock meeting object
        mock_meeting = MagicMock()
        mock_meeting.id = uuid4()
        mock_meeting.workspace_id = uuid4()
        mock_meeting.founder_id = uuid4()
        mock_meeting.status = MeetingStatus.COMPLETED
        mock_meeting.transcript = "Test transcript"

        service_instance.ingest_from_zoom = AsyncMock(return_value=(mock_meeting, False))
        service_instance.ingest_from_fireflies = AsyncMock(return_value=(mock_meeting, False))
        service_instance.ingest_from_otter = AsyncMock(return_value=(mock_meeting, False))
        service_instance.update_meeting_status = AsyncMock()

        mock.return_value = service_instance
        yield service_instance


@pytest.fixture
def mock_summarization_service():
    """Mock for SummarizationService"""
    with patch('app.api.v1.meetings.SummarizationService') as mock:
        service_instance = MagicMock()

        # Mock summary result
        mock_summary = MagicMock()
        mock_summary.id = uuid4()
        mock_summary.action_items_count = 5
        mock_summary.cost_usd = 0.15

        service_instance.summarize_meeting = AsyncMock(return_value={
            "summary": mock_summary,
            "action_items": [],
            "decisions": [],
            "sentiment": {}
        })

        mock.return_value = service_instance
        yield service_instance


@pytest.fixture
def mock_task_routing_service():
    """Mock for TaskRoutingService"""
    with patch('app.api.v1.meetings.TaskRoutingService') as mock:
        service_instance = MagicMock()

        service_instance.create_tasks_from_meeting = AsyncMock(return_value=[
            {"status": "success", "task_id": "task-1"},
            {"status": "success", "task_id": "task-2"}
        ])

        mock.return_value = service_instance
        yield service_instance


@pytest.fixture
def mock_supabase():
    """Mock Supabase client"""
    with patch('app.api.v1.meetings.get_supabase_client') as mock:
        client = MagicMock()

        # Mock meeting query
        meeting_data = {
            "id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "transcript": "This is a test transcript",
            "status": "completed",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        # Mock table operations
        table_mock = MagicMock()
        select_mock = MagicMock()
        select_mock.eq.return_value.execute.return_value.data = [meeting_data]
        table_mock.select.return_value = select_mock
        client.table.return_value = table_mock

        mock.return_value = client
        yield client


class TestIngestMeeting:
    """Tests for POST /meetings/ingest endpoint"""

    @pytest.mark.asyncio
    async def test_ingest_zoom_meeting_success(self, client, mock_meeting_ingestion_service, mock_supabase):
        """Test successful Zoom meeting ingestion"""
        # Arrange
        workspace_id = str(uuid4())
        founder_id = str(uuid4())
        platform_id = "123456789"

        request_data = {
            "workspace_id": workspace_id,
            "founder_id": founder_id,
            "source": "zoom",
            "platform_id": platform_id,
            "force_refresh": False
        }

        # Act
        response = client.post("/api/v1/meetings/ingest", json=request_data)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "meeting_id" in data
        assert data["status"] == MeetingStatus.COMPLETED.value
        assert data["message"] == f"Meeting ingested successfully from {MeetingSource.ZOOM.value}"
        assert data["duplicate"] == False
        assert "ingestion_time_ms" in data

    @pytest.mark.asyncio
    async def test_ingest_fireflies_meeting_success(self, client, mock_meeting_ingestion_service, mock_supabase):
        """Test successful Fireflies transcript ingestion"""
        # Arrange
        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "source": "fireflies",
            "platform_id": "fireflies-123",
            "force_refresh": False
        }

        # Act
        response = client.post("/api/v1/meetings/ingest", json=request_data)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == f"Meeting ingested successfully from {MeetingSource.FIREFLIES.value}"

    @pytest.mark.asyncio
    async def test_ingest_otter_meeting_success(self, client, mock_meeting_ingestion_service, mock_supabase):
        """Test successful Otter speech ingestion"""
        # Arrange
        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "source": "otter",
            "platform_id": "otter-456",
            "force_refresh": False
        }

        # Act
        response = client.post("/api/v1/meetings/ingest", json=request_data)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == f"Meeting ingested successfully from {MeetingSource.OTTER.value}"

    @pytest.mark.asyncio
    async def test_ingest_duplicate_meeting(self, client, mock_meeting_ingestion_service, mock_supabase):
        """Test ingesting a duplicate meeting"""
        # Arrange
        mock_meeting = MagicMock()
        mock_meeting.id = uuid4()
        mock_meeting.status = MeetingStatus.COMPLETED
        mock_meeting_ingestion_service.ingest_from_zoom = AsyncMock(return_value=(mock_meeting, True))

        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "source": "zoom",
            "platform_id": "duplicate-123",
            "force_refresh": False
        }

        # Act
        response = client.post("/api/v1/meetings/ingest", json=request_data)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["duplicate"] == True

    @pytest.mark.asyncio
    async def test_ingest_unsupported_source(self, client, mock_supabase):
        """Test ingesting from unsupported source"""
        # Arrange
        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "source": "unsupported_platform",
            "platform_id": "123",
            "force_refresh": False
        }

        # Act
        response = client.post("/api/v1/meetings/ingest", json=request_data)

        # Assert - should fail validation or return error
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]

    @pytest.mark.asyncio
    async def test_ingest_meeting_service_error(self, client, mock_meeting_ingestion_service, mock_supabase):
        """Test meeting ingestion when service throws error"""
        # Arrange
        mock_meeting_ingestion_service.ingest_from_zoom = AsyncMock(
            side_effect=Exception("Zoom API error")
        )

        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "source": "zoom",
            "platform_id": "123",
            "force_refresh": False
        }

        # Act
        response = client.post("/api/v1/meetings/ingest", json=request_data)

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestSummarizeMeeting:
    """Tests for POST /meetings/{meeting_id}/summarize endpoint"""

    @pytest.mark.asyncio
    async def test_summarize_meeting_success(self, client, mock_summarization_service, mock_supabase):
        """Test successful meeting summarization"""
        # Arrange
        meeting_id = str(uuid4())

        # Act
        response = client.post(f"/api/v1/meetings/{meeting_id}/summarize")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "summary_id" in data
        assert data["meeting_id"] == meeting_id
        assert data["status"] == "completed"
        assert "processing_time_ms" in data
        assert "cost_usd" in data

    @pytest.mark.asyncio
    async def test_summarize_with_options(self, client, mock_summarization_service, mock_supabase):
        """Test summarization with custom options"""
        # Arrange
        meeting_id = str(uuid4())
        request_data = {
            "extract_action_items": True,
            "extract_decisions": True,
            "include_sentiment": True
        }

        # Act
        response = client.post(
            f"/api/v1/meetings/{meeting_id}/summarize",
            json=request_data
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        mock_summarization_service.summarize_meeting.assert_called_once()

    @pytest.mark.asyncio
    async def test_summarize_meeting_not_found(self, client, mock_summarization_service, mock_supabase):
        """Test summarization when meeting doesn't exist"""
        # Arrange
        meeting_id = str(uuid4())
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        # Act
        response = client.post(f"/api/v1/meetings/{meeting_id}/summarize")

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_summarize_meeting_no_transcript(self, client, mock_summarization_service, mock_supabase):
        """Test summarization when meeting has no transcript"""
        # Arrange
        meeting_id = str(uuid4())
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{
            "id": meeting_id,
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "transcript": None
        }]

        # Act
        response = client.post(f"/api/v1/meetings/{meeting_id}/summarize")

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestGetMeetingSummary:
    """Tests for GET /meetings/{meeting_id}/summary endpoint"""

    def test_get_summary_success(self, client, mock_supabase):
        """Test retrieving meeting summary"""
        # Arrange
        meeting_id = str(uuid4())
        summary_data = {
            "id": str(uuid4()),
            "meeting_id": meeting_id,
            "executive_summary": "Test summary",
            "key_points": ["point 1", "point 2"]
        }
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [summary_data]

        # Act
        response = client.get(f"/api/v1/meetings/{meeting_id}/summary")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["meeting_id"] == meeting_id

    def test_get_summary_not_found(self, client, mock_supabase):
        """Test retrieving non-existent summary"""
        # Arrange
        meeting_id = str(uuid4())
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        # Act
        response = client.get(f"/api/v1/meetings/{meeting_id}/summary")

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestGetActionItems:
    """Tests for GET /meetings/{meeting_id}/action-items endpoint"""

    def test_get_action_items_success(self, client, mock_supabase):
        """Test retrieving meeting action items"""
        # Arrange
        meeting_id = str(uuid4())
        action_items = [
            {
                "id": str(uuid4()),
                "meeting_id": meeting_id,
                "description": "Follow up on proposal",
                "assignee_name": "John Doe",
                "priority": "high"
            }
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = action_items

        # Act
        response = client.get(f"/api/v1/meetings/{meeting_id}/action-items")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) > 0

    def test_get_action_items_empty(self, client, mock_supabase):
        """Test retrieving action items when none exist"""
        # Arrange
        meeting_id = str(uuid4())
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        # Act
        response = client.get(f"/api/v1/meetings/{meeting_id}/action-items")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 0


class TestGetDecisions:
    """Tests for GET /meetings/{meeting_id}/decisions endpoint"""

    def test_get_decisions_success(self, client, mock_supabase):
        """Test retrieving meeting decisions"""
        # Arrange
        meeting_id = str(uuid4())
        decisions = [
            {
                "id": str(uuid4()),
                "meeting_id": meeting_id,
                "title": "Decided to proceed with option A",
                "impact": "high",
                "decision_type": "strategic"
            }
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = decisions

        # Act
        response = client.get(f"/api/v1/meetings/{meeting_id}/decisions")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) > 0


class TestCreateTasksFromMeeting:
    """Tests for POST /meetings/{meeting_id}/create-tasks endpoint"""

    @pytest.mark.asyncio
    async def test_create_tasks_success(self, client, mock_task_routing_service, mock_supabase):
        """Test creating tasks from meeting action items"""
        # Arrange
        meeting_id = str(uuid4())

        # Act
        response = client.post(
            f"/api/v1/meetings/{meeting_id}/create-tasks",
            params={"platform": "monday", "min_confidence": 0.7}
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2
        assert data["success"] == 2
        assert data["failed"] == 0

    @pytest.mark.asyncio
    async def test_create_tasks_with_board_id(self, client, mock_task_routing_service, mock_supabase):
        """Test creating tasks with specific board ID"""
        # Arrange
        meeting_id = str(uuid4())
        board_id = "board-123"

        # Act
        response = client.post(
            f"/api/v1/meetings/{meeting_id}/create-tasks",
            params={"platform": "monday", "board_id": board_id}
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        mock_task_routing_service.create_tasks_from_meeting.assert_called_once()


class TestBatchSummarize:
    """Tests for POST /meetings/batch-summarize endpoint"""

    @pytest.mark.asyncio
    async def test_batch_summarize_success(self, client, mock_summarization_service, mock_supabase):
        """Test batch summarizing multiple meetings"""
        # Arrange
        meeting_ids = [str(uuid4()), str(uuid4()), str(uuid4())]
        request_data = {
            "meeting_ids": meeting_ids,
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4())
        }

        # Act
        response = client.post("/api/v1/meetings/batch-summarize", json=request_data)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "processing"
        assert data["meeting_count"] == 3


class TestGetMeetingStatus:
    """Tests for GET /meetings/{meeting_id}/status endpoint"""

    def test_get_status_success(self, client, mock_supabase):
        """Test retrieving meeting processing status"""
        # Arrange
        meeting_id = str(uuid4())
        meeting_data = {
            "id": meeting_id,
            "status": "completed",
            "ingestion_completed_at": datetime.utcnow().isoformat(),
            "summarization_completed_at": datetime.utcnow().isoformat(),
            "error_message": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [meeting_data]

        # Act
        response = client.get(f"/api/v1/meetings/{meeting_id}/status")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["meeting_id"] == meeting_id
        assert data["status"] == "completed"
        assert data["ingestion_completed"] == True
        assert data["summarization_completed"] == True

    def test_get_status_not_found(self, client, mock_supabase):
        """Test status for non-existent meeting"""
        # Arrange
        meeting_id = str(uuid4())
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        # Act
        response = client.get(f"/api/v1/meetings/{meeting_id}/status")

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
