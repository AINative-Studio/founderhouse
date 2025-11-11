"""
Comprehensive API tests for Meetings endpoints
Covers all endpoints with success and error scenarios
Target: 100% coverage of app/api/v1/meetings.py
"""
import pytest
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.meeting import MeetingSource, MeetingStatus, Meeting
from app.models.meeting_summary import MeetingSummary, SummarizationMethod


@pytest.fixture
def client():
    """Test client"""
    return TestClient(app)


@pytest.fixture
def workspace_id():
    return uuid4()


@pytest.fixture
def founder_id():
    return uuid4()


@pytest.fixture
def meeting_id():
    return uuid4()


# ==================== INGEST MEETING TESTS ====================

@pytest.mark.asyncio
async def test_ingest_meeting_zoom_success(client, workspace_id, founder_id):
    """Test successful Zoom meeting ingestion"""
    with patch('app.api.v1.meetings.MeetingIngestionService') as MockService:
        with patch('app.api.v1.meetings._get_platform_credentials', new_callable=AsyncMock):
            mock_service = Mock()
            mock_meeting = Meeting(
                id=uuid4(),
                workspace_id=workspace_id,
                founder_id=founder_id,
                title="Test Meeting",
                source=MeetingSource.ZOOM,
                status=MeetingStatus.COMPLETED,
                transcript="Sample transcript"
            )

            mock_service.ingest_from_zoom = AsyncMock(return_value=(mock_meeting, False))
            mock_service.update_meeting_status = AsyncMock()
            MockService.return_value = mock_service

            response = client.post(
                "/api/v1/meetings/ingest",
                json={
                    "workspace_id": str(workspace_id),
                    "founder_id": str(founder_id),
                    "source": "zoom",
                    "platform_id": "123456789"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert "meeting_id" in data
            assert data["status"] == "completed"
            assert data["duplicate"] is False


@pytest.mark.asyncio
async def test_ingest_meeting_fireflies_success(client, workspace_id, founder_id):
    """Test successful Fireflies transcript ingestion"""
    with patch('app.api.v1.meetings.MeetingIngestionService') as MockService:
        with patch('app.api.v1.meetings._get_platform_credentials', new_callable=AsyncMock):
            mock_service = Mock()
            mock_meeting = Meeting(
                id=uuid4(),
                workspace_id=workspace_id,
                founder_id=founder_id,
                title="Test Meeting",
                source=MeetingSource.FIREFLIES,
                status=MeetingStatus.COMPLETED
            )

            mock_service.ingest_from_fireflies = AsyncMock(return_value=(mock_meeting, False))
            mock_service.update_meeting_status = AsyncMock()
            MockService.return_value = mock_service

            response = client.post(
                "/api/v1/meetings/ingest",
                json={
                    "workspace_id": str(workspace_id),
                    "founder_id": str(founder_id),
                    "source": "fireflies",
                    "platform_id": "ff-123"
                }
            )

            assert response.status_code == 200


@pytest.mark.asyncio
async def test_ingest_meeting_otter_success(client, workspace_id, founder_id):
    """Test successful Otter speech ingestion"""
    with patch('app.api.v1.meetings.MeetingIngestionService') as MockService:
        with patch('app.api.v1.meetings._get_platform_credentials', new_callable=AsyncMock):
            mock_service = Mock()
            mock_meeting = Meeting(
                id=uuid4(),
                workspace_id=workspace_id,
                founder_id=founder_id,
                title="Test Speech",
                source=MeetingSource.OTTER,
                status=MeetingStatus.COMPLETED
            )

            mock_service.ingest_from_otter = AsyncMock(return_value=(mock_meeting, False))
            mock_service.update_meeting_status = AsyncMock()
            MockService.return_value = mock_service

            response = client.post(
                "/api/v1/meetings/ingest",
                json={
                    "workspace_id": str(workspace_id),
                    "founder_id": str(founder_id),
                    "source": "otter",
                    "platform_id": "otter-456"
                }
            )

            assert response.status_code == 200


def test_ingest_meeting_unsupported_source(client, workspace_id, founder_id):
    """Test ingestion with unsupported source"""
    response = client.post(
        "/api/v1/meetings/ingest",
        json={
            "workspace_id": str(workspace_id),
            "founder_id": str(founder_id),
            "source": "unsupported",
            "platform_id": "123"
        }
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_ingest_meeting_duplicate(client, workspace_id, founder_id):
    """Test ingesting duplicate meeting"""
    with patch('app.api.v1.meetings.MeetingIngestionService') as MockService:
        with patch('app.api.v1.meetings._get_platform_credentials', new_callable=AsyncMock):
            mock_service = Mock()
            mock_meeting = Meeting(
                id=uuid4(),
                workspace_id=workspace_id,
                founder_id=founder_id,
                title="Existing Meeting",
                source=MeetingSource.ZOOM,
                status=MeetingStatus.COMPLETED
            )

            mock_service.ingest_from_zoom = AsyncMock(return_value=(mock_meeting, True))
            mock_service.update_meeting_status = AsyncMock()
            MockService.return_value = mock_service

            response = client.post(
                "/api/v1/meetings/ingest",
                json={
                    "workspace_id": str(workspace_id),
                    "founder_id": str(founder_id),
                    "source": "zoom",
                    "platform_id": "123456789"
                }
            )

            assert response.status_code == 200
            assert response.json()["duplicate"] is True


# ==================== SUMMARIZE MEETING TESTS ====================

@pytest.mark.asyncio
async def test_summarize_meeting_success(client, meeting_id, workspace_id, founder_id):
    """Test successful meeting summarization"""
    mock_meeting = {
        "id": str(meeting_id),
        "workspace_id": str(workspace_id),
        "founder_id": str(founder_id),
        "transcript": "This is a test transcript for summarization."
    }

    mock_summary = MeetingSummary(
        id=uuid4(),
        workspace_id=workspace_id,
        founder_id=founder_id,
        meeting_id=meeting_id,
        executive_summary="Test summary",
        detailed_summary="Detailed summary",
        key_points=["Point 1"],
        topics_discussed=["Topic 1"],
        summarization_method=SummarizationMethod.MULTI_STAGE,
        llm_provider="openai",
        llm_model="gpt-4",
        action_items_count=2,
        cost_usd=0.05
    )

    with patch('app.api.v1.meetings._get_meeting', new_callable=AsyncMock) as mock_get:
        with patch('app.api.v1.meetings.SummarizationService') as MockService:
            mock_get.return_value = mock_meeting

            mock_service = Mock()
            mock_service.summarize_meeting = AsyncMock(return_value={
                "summary": mock_summary,
                "action_items": [],
                "decisions": [],
                "sentiment": {}
            })
            MockService.return_value = mock_service

            response = client.post(f"/api/v1/meetings/{meeting_id}/summarize")

            assert response.status_code == 200
            data = response.json()
            assert "summary_id" in data
            assert data["status"] == "completed"


def test_summarize_meeting_not_found(client, meeting_id):
    """Test summarizing non-existent meeting"""
    with patch('app.api.v1.meetings._get_meeting', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None

        response = client.post(f"/api/v1/meetings/{meeting_id}/summarize")

        assert response.status_code == 404


def test_summarize_meeting_no_transcript(client, meeting_id):
    """Test summarizing meeting without transcript"""
    mock_meeting = {
        "id": str(meeting_id),
        "transcript": None
    }

    with patch('app.api.v1.meetings._get_meeting', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_meeting

        response = client.post(f"/api/v1/meetings/{meeting_id}/summarize")

        assert response.status_code == 400


# ==================== GET SUMMARY TESTS ====================

def test_get_meeting_summary_success(client, meeting_id):
    """Test retrieving meeting summary"""
    mock_summary = {
        "id": str(uuid4()),
        "meeting_id": str(meeting_id),
        "executive_summary": "Test summary"
    }

    with patch('app.api.v1.meetings.get_supabase_client') as mock_get_client:
        mock_supabase = Mock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[mock_summary]
        )
        mock_get_client.return_value = mock_supabase

        response = client.get(f"/api/v1/meetings/{meeting_id}/summary")

        assert response.status_code == 200


def test_get_meeting_summary_not_found(client, meeting_id):
    """Test retrieving non-existent summary"""
    with patch('app.api.v1.meetings.get_supabase_client') as mock_get_client:
        mock_supabase = Mock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=[]
        )
        mock_get_client.return_value = mock_supabase

        response = client.get(f"/api/v1/meetings/{meeting_id}/summary")

        assert response.status_code == 404


def test_get_meeting_summary_no_database(client, meeting_id):
    """Test retrieving summary when database unavailable"""
    with patch('app.api.v1.meetings.get_supabase_client') as mock_get_client:
        mock_get_client.return_value = None

        response = client.get(f"/api/v1/meetings/{meeting_id}/summary")

        assert response.status_code == 503


# ==================== GET ACTION ITEMS TESTS ====================

def test_get_meeting_action_items_success(client, meeting_id):
    """Test retrieving action items"""
    mock_items = [
        {
            "id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "meeting_id": str(meeting_id),
            "description": "Action 1",
            "confidence_score": 0.9
        }
    ]

    with patch('app.api.v1.meetings.get_supabase_client') as mock_get_client:
        mock_supabase = Mock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=mock_items
        )
        mock_get_client.return_value = mock_supabase

        response = client.get(f"/api/v1/meetings/{meeting_id}/action-items")

        assert response.status_code == 200
        assert len(response.json()) > 0


def test_get_meeting_action_items_no_database(client, meeting_id):
    """Test retrieving action items when database unavailable"""
    with patch('app.api.v1.meetings.get_supabase_client') as mock_get_client:
        mock_get_client.return_value = None

        response = client.get(f"/api/v1/meetings/{meeting_id}/action-items")

        assert response.status_code == 200
        assert response.json() == []


# ==================== GET DECISIONS TESTS ====================

def test_get_meeting_decisions_success(client, meeting_id):
    """Test retrieving decisions"""
    mock_decisions = [
        {
            "id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "meeting_id": str(meeting_id),
            "title": "Decision 1",
            "description": "Description",
            "confidence_score": 0.85
        }
    ]

    with patch('app.api.v1.meetings.get_supabase_client') as mock_get_client:
        mock_supabase = Mock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
            data=mock_decisions
        )
        mock_get_client.return_value = mock_supabase

        response = client.get(f"/api/v1/meetings/{meeting_id}/decisions")

        assert response.status_code == 200
        assert len(response.json()) > 0


# ==================== GET STATUS TESTS ====================

@pytest.mark.asyncio
async def test_get_meeting_status_success(client, meeting_id):
    """Test retrieving meeting status"""
    mock_meeting = {
        "id": str(meeting_id),
        "status": "completed",
        "ingestion_completed_at": "2025-01-15T10:00:00Z",
        "summarization_completed_at": "2025-01-15T10:05:00Z",
        "error_message": None,
        "created_at": "2025-01-15T09:00:00Z",
        "updated_at": "2025-01-15T10:05:00Z"
    }

    with patch('app.api.v1.meetings._get_meeting', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_meeting

        response = client.get(f"/api/v1/meetings/{meeting_id}/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["ingestion_completed"] is True
        assert data["summarization_completed"] is True


@pytest.mark.asyncio
async def test_get_meeting_status_not_found(client, meeting_id):
    """Test retrieving status for non-existent meeting"""
    with patch('app.api.v1.meetings._get_meeting', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None

        response = client.get(f"/api/v1/meetings/{meeting_id}/status")

        assert response.status_code == 404


# ==================== CREATE TASKS TESTS ====================

@pytest.mark.asyncio
async def test_create_tasks_from_meeting_success(client, meeting_id):
    """Test creating tasks from action items"""
    with patch('app.api.v1.meetings._get_platform_credentials', new_callable=AsyncMock):
        with patch('app.api.v1.meetings.TaskRoutingService') as MockService:
            mock_service = Mock()
            mock_service.create_tasks_from_meeting = AsyncMock(return_value=[
                {"status": "success", "task_id": "task-1"},
                {"status": "success", "task_id": "task-2"}
            ])
            MockService.return_value = mock_service

            response = client.post(
                f"/api/v1/meetings/{meeting_id}/create-tasks",
                params={"platform": "monday"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2
            assert data["success"] == 2


# ==================== BATCH SUMMARIZE TESTS ====================

def test_batch_summarize_meetings_success(client, workspace_id, founder_id):
    """Test batch summarization"""
    meeting_ids = [str(uuid4()), str(uuid4())]

    response = client.post(
        "/api/v1/meetings/batch-summarize",
        params={
            "workspace_id": str(workspace_id),
            "founder_id": str(founder_id)
        },
        json=meeting_ids
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"
    assert data["meeting_count"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
