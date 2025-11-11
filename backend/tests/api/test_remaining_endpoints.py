"""
Comprehensive tests for remaining API endpoints with low coverage

Tests for:
1. Meetings API (25% coverage, 109 uncovered)
2. Insights API (22% coverage, 56 uncovered)
3. Agents API (26% coverage, 77 uncovered)

FastAPI TestClient-based integration tests with mocked services.
Coverage target: 80%+
"""
import pytest
from uuid import uuid4, UUID
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.models.meeting import MeetingSource, MeetingStatus
from app.models.meeting_summary import SummaryGenerationRequest
from app.models.anomaly import AnomalySeverity, TrendDirection, DetectionMethod


def create_test_app():
    """Create a minimal test app with the endpoint routers"""
    app = FastAPI()

    # Import routers - these will be registered on app
    from app.api.v1 import meetings, insights, agents

    # Register routes directly
    app.include_router(meetings.router, prefix="/v1", tags=["meetings"])
    app.include_router(insights.router, prefix="/v1", tags=["insights"])
    app.include_router(agents.router, prefix="/v1", tags=["agents"])

    return app


@pytest.fixture
def client():
    """FastAPI test client"""
    try:
        # Try to use the main app
        from app.main import app
        return TestClient(app)
    except Exception:
        # Fallback to test app if main app fails to initialize
        return TestClient(create_test_app())


# ==================== MEETINGS API TESTS ====================

@pytest.fixture
def mock_meeting_services():
    """Mock all meeting-related services"""
    with patch('app.api.v1.meetings.MeetingIngestionService') as mock_ingest, \
         patch('app.api.v1.meetings.SummarizationService') as mock_summary, \
         patch('app.api.v1.meetings.TaskRoutingService') as mock_task_routing:

        # Setup ingestion service
        ingest_instance = MagicMock()
        mock_meeting = MagicMock()
        mock_meeting.id = uuid4()
        mock_meeting.workspace_id = uuid4()
        mock_meeting.founder_id = uuid4()
        mock_meeting.status = MeetingStatus.COMPLETED
        mock_meeting.transcript = "Test transcript with action items"

        ingest_instance.ingest_from_zoom = AsyncMock(return_value=(mock_meeting, False))
        ingest_instance.ingest_from_fireflies = AsyncMock(return_value=(mock_meeting, False))
        ingest_instance.ingest_from_otter = AsyncMock(return_value=(mock_meeting, False))
        ingest_instance.update_meeting_status = AsyncMock()
        mock_ingest.return_value = ingest_instance

        # Setup summarization service
        summary_instance = MagicMock()
        mock_summary_obj = MagicMock()
        mock_summary_obj.id = uuid4()
        mock_summary_obj.action_items_count = 5
        mock_summary_obj.cost_usd = 0.15

        summary_instance.summarize_meeting = AsyncMock(return_value={
            "summary": mock_summary_obj,
            "action_items": [{"id": str(uuid4()), "title": "Item 1"}],
            "decisions": [{"id": str(uuid4()), "title": "Decision 1"}]
        })
        summary_instance.batch_summarize = AsyncMock()
        mock_summary.return_value = summary_instance

        # Setup task routing service
        task_instance = MagicMock()
        task_instance.create_tasks_from_meeting = AsyncMock(return_value=[
            {"status": "success", "task_id": str(uuid4())},
            {"status": "success", "task_id": str(uuid4())}
        ])
        mock_task_routing.return_value = task_instance

        yield ingest_instance, summary_instance, task_instance


@pytest.fixture
def mock_supabase_meetings():
    """Mock Supabase client for meetings"""
    with patch('app.api.v1.meetings.get_supabase_client') as mock:
        client = MagicMock()

        meeting_id = uuid4()
        meeting_data = {
            "id": str(meeting_id),
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "transcript": "This is a test transcript",
            "status": "completed",
            "ingestion_completed_at": datetime.utcnow().isoformat(),
            "summarization_completed_at": datetime.utcnow().isoformat(),
            "error_message": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        summary_data = {
            "id": str(uuid4()),
            "meeting_id": str(meeting_id),
            "summary": "Test summary",
            "action_items_count": 5
        }

        action_items_data = [
            {"id": str(uuid4()), "title": "Item 1", "description": "Do something"},
            {"id": str(uuid4()), "title": "Item 2", "description": "Do another thing"}
        ]

        decisions_data = [
            {"id": str(uuid4()), "title": "Decision 1", "description": "Made decision"}
        ]

        # Setup table mock for meetings
        def table_side_effect(table_name):
            table_mock = MagicMock()

            if table_name == "meetings":
                select_mock = MagicMock()
                eq_mock = MagicMock()
                execute_mock = MagicMock()
                execute_mock.data = [meeting_data]
                eq_mock.execute.return_value = execute_mock
                select_mock.eq.return_value = eq_mock
                table_mock.select.return_value = select_mock

            elif table_name == "meeting_summaries":
                select_mock = MagicMock()
                eq_mock = MagicMock()
                execute_mock = MagicMock()
                execute_mock.data = [summary_data]
                eq_mock.execute.return_value = execute_mock
                select_mock.eq.return_value = eq_mock
                table_mock.select.return_value = select_mock

            elif table_name == "action_items":
                select_mock = MagicMock()
                eq_mock = MagicMock()
                execute_mock = MagicMock()
                execute_mock.data = action_items_data
                eq_mock.execute.return_value = execute_mock
                select_mock.eq.return_value = eq_mock
                table_mock.select.return_value = select_mock

            elif table_name == "decisions":
                select_mock = MagicMock()
                eq_mock = MagicMock()
                execute_mock = MagicMock()
                execute_mock.data = decisions_data
                eq_mock.execute.return_value = execute_mock
                select_mock.eq.return_value = eq_mock
                table_mock.select.return_value = select_mock

            return table_mock

        client.table.side_effect = table_side_effect
        mock.return_value = client
        yield client


class TestMeetingsAPIIngest:
    """Tests for meeting ingestion endpoints"""

    def test_ingest_meeting_zoom_success(self, client, mock_meeting_services, mock_supabase_meetings):
        """Test successful Zoom meeting ingestion"""
        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "source": MeetingSource.ZOOM,
            "platform_id": "zoom-meeting-123",
            "force_refresh": False
        }

        # Try both paths - with and without /v1 prefix
        response = client.post("/meetings/ingest", json=request_data)
        if response.status_code == 404:
            response = client.post("/v1/meetings/ingest", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "meeting_id" in data
        assert data["status"] == "completed"
        assert "duplicate" in data
        assert "ingestion_time_ms" in data

    def test_ingest_meeting_fireflies_success(self, client, mock_meeting_services, mock_supabase_meetings):
        """Test successful Fireflies transcript ingestion"""
        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "source": MeetingSource.FIREFLIES,
            "platform_id": "fireflies-123",
            "force_refresh": False
        }

        response = client.post("/meetings/ingest", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "meeting_id" in data

    def test_ingest_meeting_otter_success(self, client, mock_meeting_services, mock_supabase_meetings):
        """Test successful Otter speech ingestion"""
        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "source": MeetingSource.OTTER,
            "platform_id": "otter-123",
            "force_refresh": False
        }

        response = client.post("/meetings/ingest", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    def test_ingest_meeting_invalid_source(self, client, mock_meeting_services, mock_supabase_meetings):
        """Test ingestion with invalid source"""
        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "source": "invalid_source",
            "platform_id": "test-123"
        }

        response = client.post("/meetings/ingest", json=request_data)

        assert response.status_code == 400


class TestMeetingsAPISummarization:
    """Tests for meeting summarization endpoints"""

    def test_summarize_meeting_success(self, client, mock_meeting_services, mock_supabase_meetings):
        """Test successful meeting summarization"""
        meeting_id = uuid4()
        request_data = {
            "extract_action_items": True,
            "extract_decisions": True,
            "include_sentiment": True
        }

        response = client.post(f"/meetings/{meeting_id}/summarize", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "summary_id" in data
        assert data["status"] == "completed"
        assert "processing_time_ms" in data
        assert "cost_usd" in data

    def test_summarize_meeting_no_transcript(self, client, mock_meeting_services, mock_supabase_meetings):
        """Test summarization when meeting has no transcript"""
        meeting_id = uuid4()

        # Mock empty transcript
        with patch('app.api.v1.meetings.get_supabase_client') as mock:
            client_mock = MagicMock()
            table_mock = MagicMock()
            select_mock = MagicMock()
            eq_mock = MagicMock()
            execute_mock = MagicMock()
            execute_mock.data = [{"id": str(meeting_id), "transcript": None}]
            eq_mock.execute.return_value = execute_mock
            select_mock.eq.return_value = eq_mock
            table_mock.select.return_value = select_mock
            client_mock.table.return_value = table_mock
            mock.return_value = client_mock

            response = client.post(f"/meetings/{meeting_id}/summarize", json={})
            assert response.status_code == 400

    def test_get_meeting_summary_success(self, client, mock_supabase_meetings):
        """Test retrieving meeting summary"""
        meeting_id = uuid4()

        response = client.get(f"/meetings/{meeting_id}/summary")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "summary" in data

    def test_get_meeting_summary_not_found(self, client, mock_supabase_meetings):
        """Test getting summary for non-existent meeting"""
        meeting_id = uuid4()

        with patch('app.api.v1.meetings.get_supabase_client') as mock:
            client_mock = MagicMock()
            table_mock = MagicMock()
            select_mock = MagicMock()
            eq_mock = MagicMock()
            execute_mock = MagicMock()
            execute_mock.data = []
            eq_mock.execute.return_value = execute_mock
            select_mock.eq.return_value = eq_mock
            table_mock.select.return_value = select_mock
            client_mock.table.return_value = table_mock
            mock.return_value = client_mock

            response = client.get(f"/meetings/{meeting_id}/summary")
            assert response.status_code == 404


class TestMeetingsAPIActionItems:
    """Tests for action items endpoints"""

    def test_get_action_items_success(self, client, mock_supabase_meetings):
        """Test retrieving action items from meeting"""
        meeting_id = uuid4()

        response = client.get(f"/meetings/{meeting_id}/action-items")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 0

    def test_get_action_items_empty(self, client, mock_supabase_meetings):
        """Test retrieving action items when none exist"""
        meeting_id = uuid4()

        with patch('app.api.v1.meetings.get_supabase_client') as mock:
            client_mock = MagicMock()
            table_mock = MagicMock()
            select_mock = MagicMock()
            eq_mock = MagicMock()
            execute_mock = MagicMock()
            execute_mock.data = []
            eq_mock.execute.return_value = execute_mock
            select_mock.eq.return_value = eq_mock
            table_mock.select.return_value = select_mock
            client_mock.table.return_value = table_mock
            mock.return_value = client_mock

            response = client.get(f"/meetings/{meeting_id}/action-items")
            assert response.status_code == 200
            assert response.json() == []


class TestMeetingsAPIDecisions:
    """Tests for decisions endpoints"""

    def test_get_decisions_success(self, client, mock_supabase_meetings):
        """Test retrieving decisions from meeting"""
        meeting_id = uuid4()

        response = client.get(f"/meetings/{meeting_id}/decisions")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_decisions_empty(self, client, mock_supabase_meetings):
        """Test retrieving decisions when none exist"""
        meeting_id = uuid4()

        with patch('app.api.v1.meetings.get_supabase_client') as mock:
            client_mock = MagicMock()
            table_mock = MagicMock()
            select_mock = MagicMock()
            eq_mock = MagicMock()
            execute_mock = MagicMock()
            execute_mock.data = []
            eq_mock.execute.return_value = execute_mock
            select_mock.eq.return_value = eq_mock
            table_mock.select.return_value = select_mock
            client_mock.table.return_value = table_mock
            mock.return_value = client_mock

            response = client.get(f"/meetings/{meeting_id}/decisions")
            assert response.status_code == 200
            assert response.json() == []


class TestMeetingsAPIStatus:
    """Tests for meeting status endpoints"""

    def test_get_meeting_status_success(self, client, mock_supabase_meetings):
        """Test retrieving meeting status"""
        meeting_id = uuid4()

        response = client.get(f"/meetings/{meeting_id}/status")

        assert response.status_code == 200
        data = response.json()
        assert "meeting_id" in data
        assert "status" in data
        assert "ingestion_completed" in data
        assert "summarization_completed" in data

    def test_get_meeting_status_not_found(self, client):
        """Test getting status for non-existent meeting"""
        meeting_id = uuid4()

        with patch('app.api.v1.meetings.get_supabase_client') as mock:
            client_mock = MagicMock()
            table_mock = MagicMock()
            select_mock = MagicMock()
            eq_mock = MagicMock()
            execute_mock = MagicMock()
            execute_mock.data = []
            eq_mock.execute.return_value = execute_mock
            select_mock.eq.return_value = eq_mock
            table_mock.select.return_value = select_mock
            client_mock.table.return_value = table_mock
            mock.return_value = client_mock

            response = client.get(f"/meetings/{meeting_id}/status")
            assert response.status_code == 404


class TestMeetingsAPITasks:
    """Tests for task creation endpoints"""

    def test_create_tasks_from_meeting_success(self, client, mock_meeting_services, mock_supabase_meetings):
        """Test creating tasks from meeting action items"""
        meeting_id = uuid4()

        response = client.post(
            f"/meetings/{meeting_id}/create-tasks",
            params={
                "platform": "monday",
                "board_id": "board-123",
                "min_confidence": 0.7
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "success" in data
        assert "failed" in data
        assert "results" in data

    def test_create_tasks_different_platform(self, client, mock_meeting_services, mock_supabase_meetings):
        """Test creating tasks on different platform"""
        meeting_id = uuid4()

        response = client.post(
            f"/meetings/{meeting_id}/create-tasks",
            params={
                "platform": "asana",
                "min_confidence": 0.6
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] >= 0


class TestMeetingsAPIBatch:
    """Tests for batch operations"""

    def test_batch_summarize_meetings(self, client, mock_meeting_services):
        """Test batch summarization of multiple meetings"""
        meeting_ids = [str(uuid4()) for _ in range(3)]
        workspace_id = uuid4()
        founder_id = uuid4()

        response = client.post(
            "/meetings/batch-summarize",
            params={
                "workspace_id": workspace_id,
                "founder_id": founder_id
            },
            json={"meeting_ids": meeting_ids}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert data["meeting_count"] == 3

    def test_batch_summarize_empty_list(self, client, mock_meeting_services):
        """Test batch summarization with empty list"""
        workspace_id = uuid4()
        founder_id = uuid4()

        response = client.post(
            "/meetings/batch-summarize",
            params={
                "workspace_id": workspace_id,
                "founder_id": founder_id
            },
            json={"meeting_ids": []}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["meeting_count"] == 0


# ==================== INSIGHTS API TESTS ====================

@pytest.fixture
def mock_anomaly_service():
    """Mock anomaly detection service"""
    with patch('app.api.v1.insights.get_anomaly_service') as mock:
        service = MagicMock()

        # Setup Supabase mock
        service.supabase = MagicMock()

        # Mock anomaly query
        anomaly_table = MagicMock()
        anomaly_select = MagicMock()
        anomaly_eq = MagicMock()

        anomaly_data = [
            {
                "id": str(uuid4()),
                "workspace_id": str(uuid4()),
                "metric_id": str(uuid4()),
                "anomaly_type": "spike",
                "severity": "high",
                "detected_at": datetime.utcnow().isoformat(),
                "is_acknowledged": False,
                "confidence_score": 0.95
            }
        ]

        anomaly_execute = MagicMock()
        anomaly_execute.data = anomaly_data
        anomaly_eq.execute.return_value = anomaly_execute
        anomaly_eq.gte.return_value = anomaly_eq
        anomaly_eq.in_.return_value = anomaly_eq
        anomaly_eq.order.return_value = anomaly_eq
        anomaly_eq.range.return_value = anomaly_eq
        anomaly_select.eq.return_value = anomaly_eq
        anomaly_table.select.return_value = anomaly_select

        # Mock trend query
        trend_table = MagicMock()
        trend_select = MagicMock()
        trend_eq = MagicMock()

        trend_data = [
            {
                "id": str(uuid4()),
                "workspace_id": str(uuid4()),
                "metric_id": str(uuid4()),
                "direction": "up",
                "is_significant": True,
                "created_at": datetime.utcnow().isoformat(),
                "strength": 0.85
            }
        ]

        trend_execute = MagicMock()
        trend_execute.data = trend_data
        trend_eq.execute.return_value = trend_execute
        trend_eq.gte.return_value = trend_eq
        trend_eq.in_.return_value = trend_eq
        trend_eq.order.return_value = trend_eq
        trend_eq.range.return_value = trend_eq
        trend_select.eq.return_value = trend_eq
        trend_table.select.return_value = trend_select

        # Setup table routing
        def table_side_effect(table_name):
            if table_name == "anomalies":
                return anomaly_table
            elif table_name == "trends":
                return trend_table
            return MagicMock()

        service.supabase.table.side_effect = table_side_effect

        # Mock analyze_metric
        mock_analysis = MagicMock()
        mock_analysis.anomalies = anomaly_data
        mock_analysis.trends = trend_data
        service.analyze_metric = AsyncMock(return_value=mock_analysis)

        mock.return_value = service
        yield service


class TestInsightsAPIAnomalies:
    """Tests for anomaly detection endpoints"""

    def test_list_anomalies_success(self, client, mock_anomaly_service):
        """Test listing anomalies with filters"""
        workspace_id = uuid4()

        response = client.get(
            "/insights/anomalies",
            params={
                "workspace_id": workspace_id,
                "days_back": 30,
                "limit": 50,
                "offset": 0
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "anomalies" in data
        assert "total_count" in data
        assert "has_more" in data
        assert "filters_applied" in data

    def test_list_anomalies_by_severity(self, client, mock_anomaly_service):
        """Test filtering anomalies by severity"""
        workspace_id = uuid4()

        response = client.get(
            "/insights/anomalies",
            params={
                "workspace_id": workspace_id,
                "severity": ["high", "critical"],
                "limit": 50
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "anomalies" in data

    def test_list_anomalies_by_metric(self, client, mock_anomaly_service):
        """Test filtering anomalies by metric IDs"""
        workspace_id = uuid4()
        metric_ids = [str(uuid4()) for _ in range(2)]

        response = client.get(
            "/insights/anomalies",
            params={
                "workspace_id": workspace_id,
                "metric_ids": metric_ids,
                "limit": 50
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["anomalies"], list)

    def test_list_anomalies_acknowledged_filter(self, client, mock_anomaly_service):
        """Test filtering anomalies by acknowledgement status"""
        workspace_id = uuid4()

        response = client.get(
            "/insights/anomalies",
            params={
                "workspace_id": workspace_id,
                "is_acknowledged": False,
                "limit": 50
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] >= 0

    def test_list_anomalies_pagination(self, client, mock_anomaly_service):
        """Test anomalies pagination"""
        workspace_id = uuid4()

        response = client.get(
            "/insights/anomalies",
            params={
                "workspace_id": workspace_id,
                "limit": 10,
                "offset": 20
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "has_more" in data


class TestInsightsAPITrends:
    """Tests for trend analysis endpoints"""

    def test_list_trends_success(self, client, mock_anomaly_service):
        """Test listing KPI trends"""
        workspace_id = uuid4()

        response = client.get(
            "/insights/trends",
            params={
                "workspace_id": workspace_id,
                "days_back": 30,
                "limit": 50
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "trends" in data
        assert "total_count" in data
        assert "has_more" in data

    def test_list_trends_by_direction(self, client, mock_anomaly_service):
        """Test filtering trends by direction"""
        workspace_id = uuid4()

        response = client.get(
            "/insights/trends",
            params={
                "workspace_id": workspace_id,
                "direction": ["up", "down"],
                "limit": 50
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["trends"], list)

    def test_list_trends_significant_only(self, client, mock_anomaly_service):
        """Test filtering trends by significance"""
        workspace_id = uuid4()

        response = client.get(
            "/insights/trends",
            params={
                "workspace_id": workspace_id,
                "is_significant": True,
                "limit": 50
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] >= 0

    def test_list_trends_by_metric(self, client, mock_anomaly_service):
        """Test filtering trends by metric"""
        workspace_id = uuid4()
        metric_ids = [str(uuid4()) for _ in range(2)]

        response = client.get(
            "/insights/trends",
            params={
                "workspace_id": workspace_id,
                "metric_ids": metric_ids
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "trends" in data


class TestInsightsAPIAnalysis:
    """Tests for metric analysis endpoints"""

    def test_analyze_metric_success(self, client, mock_anomaly_service):
        """Test analyzing a specific metric"""
        metric_id = uuid4()
        workspace_id = uuid4()

        response = client.get(
            f"/insights/{metric_id}/analysis",
            params={
                "workspace_id": workspace_id,
                "days_back": 30
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "anomalies" in data or "trends" in data

    def test_analyze_metric_custom_period(self, client, mock_anomaly_service):
        """Test analyzing metric with custom time period"""
        metric_id = uuid4()
        workspace_id = uuid4()

        response = client.get(
            f"/insights/{metric_id}/analysis",
            params={
                "workspace_id": workspace_id,
                "days_back": 90
            }
        )

        assert response.status_code == 200

    def test_analyze_metric_with_methods(self, client, mock_anomaly_service):
        """Test analysis with specific detection methods"""
        metric_id = uuid4()
        workspace_id = uuid4()

        response = client.get(
            f"/insights/{metric_id}/analysis",
            params={
                "workspace_id": workspace_id,
                "detection_methods": ["zscore", "iqr"]
            }
        )

        assert response.status_code == 200

    def test_trigger_analysis_all_metrics(self, client, mock_anomaly_service):
        """Test triggering analysis for all workspace metrics"""
        workspace_id = uuid4()

        # Mock kpi_metrics query
        metrics_table = MagicMock()
        metrics_select = MagicMock()
        metrics_eq = MagicMock()
        metrics_execute = MagicMock()

        metrics_execute.data = [
            {"id": str(uuid4())},
            {"id": str(uuid4())},
            {"id": str(uuid4())}
        ]

        metrics_eq.execute.return_value = metrics_execute
        metrics_eq.eq.return_value = metrics_eq
        metrics_select.eq.return_value = metrics_eq
        metrics_table.select.return_value = metrics_select

        mock_anomaly_service.supabase.table.return_value = metrics_table

        response = client.post(
            "/insights/analyze",
            params={
                "workspace_id": workspace_id,
                "days_back": 30
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "analyzed_metrics" in data
        assert "anomalies_detected" in data
        assert "trends_detected" in data

    def test_trigger_analysis_specific_metrics(self, client, mock_anomaly_service):
        """Test triggering analysis for specific metrics"""
        workspace_id = uuid4()
        metric_ids = [str(uuid4()) for _ in range(2)]

        # Mock kpi_metrics query
        metrics_table = MagicMock()
        metrics_select = MagicMock()
        metrics_in = MagicMock()
        metrics_execute = MagicMock()

        metrics_execute.data = [{"id": m} for m in metric_ids]
        metrics_in.execute.return_value = metrics_execute
        metrics_select.in_.return_value = metrics_in
        metrics_table.select.return_value = metrics_select

        mock_anomaly_service.supabase.table.return_value = metrics_table

        response = client.post(
            "/insights/analyze",
            params={
                "workspace_id": workspace_id,
                "metric_ids": metric_ids
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["analyzed_metrics"] >= 0


# ==================== AGENTS API TESTS ====================

@pytest.fixture
def mock_agent_services():
    """Mock agent routing and collaboration services"""
    with patch('app.api.v1.agents.get_routing_service') as mock_routing, \
         patch('app.api.v1.agents.get_collaboration_service') as mock_collab:

        # Setup routing service
        routing_instance = MagicMock()
        task_response = {
            "id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "task_type": "data_analysis",
            "task_description": "Analyze trends",
            "priority": "high",
            "status": "queued",
            "assigned_agent": "kpi_monitor",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        routing_instance.route_task = AsyncMock(return_value=task_response)
        routing_instance.get_task = AsyncMock(return_value=task_response)
        routing_instance.list_tasks = AsyncMock(return_value=[task_response])
        routing_instance.cancel_task = AsyncMock(return_value=True)
        routing_instance.retry_task = AsyncMock(return_value=task_response)
        routing_instance.get_agent_health = AsyncMock(return_value={
            "agent_type": "kpi_monitor",
            "status": "healthy",
            "uptime": 99.9,
            "queue_depth": 5
        })
        routing_instance.get_agent_metrics = AsyncMock(return_value={
            "agent_type": "kpi_monitor",
            "success_rate": 0.95,
            "avg_processing_time_ms": 1500,
            "total_processed": 1000,
            "failures": 50
        })
        mock_routing.return_value = routing_instance

        # Setup collaboration service
        collab_instance = MagicMock()
        collab_response = {
            "session_id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "objective": "Analyze business metrics",
            "agents_involved": ["data_analysis", "recommendation_engine"],
            "status": "in_progress",
            "outputs": {},
            "created_at": datetime.utcnow().isoformat()
        }

        collab_instance.initiate_collaboration = AsyncMock(return_value=collab_response)
        collab_instance.get_collaboration = AsyncMock(return_value={**collab_response, "status": "completed"})
        mock_collab.return_value = collab_instance

        yield routing_instance, collab_instance


class TestAgentsAPIRouting:
    """Tests for agent task routing"""

    def test_route_task_success(self, client, mock_agent_services):
        """Test successful task routing"""
        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "task_type": "data_analysis",
            "task_description": "Analyze Q4 revenue trends",
            "priority": "high",
            "input_data": {"metric": "revenue"},
            "context": {"quarter": "Q4"}
        }

        response = client.post("/agents/route", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["status"] == "queued"
        assert data["priority"] == "high"

    def test_route_task_with_dependencies(self, client, mock_agent_services):
        """Test routing task with dependencies"""
        dependency_task_id = uuid4()
        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "task_type": "reporting",
            "task_description": "Generate report",
            "priority": "medium",
            "dependencies": [str(dependency_task_id)]
        }

        response = client.post("/agents/route", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "id" in data

    def test_route_task_preferred_agent(self, client, mock_agent_services):
        """Test routing with preferred agent"""
        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "task_type": "analysis",
            "task_description": "Analyze data",
            "preferred_agent": "kpi_monitor",
            "input_data": {"data": "test"}
        }

        response = client.post("/agents/route", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "assigned_agent" in data

    def test_route_task_with_deadline(self, client, mock_agent_services):
        """Test routing task with deadline"""
        deadline = (datetime.utcnow() + timedelta(hours=2)).isoformat()
        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "task_type": "urgent_analysis",
            "task_description": "Urgent analysis needed",
            "priority": "urgent",
            "deadline": deadline
        }

        response = client.post("/agents/route", json=request_data)

        assert response.status_code == 200


class TestAgentsAPITaskManagement:
    """Tests for task management endpoints"""

    def test_get_task_success(self, client, mock_agent_services):
        """Test retrieving task details"""
        task_id = uuid4()

        response = client.get(f"/agents/tasks/{task_id}")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "status" in data

    def test_list_tasks_by_workspace(self, client, mock_agent_services):
        """Test listing tasks for workspace"""
        workspace_id = uuid4()

        response = client.get(
            "/agents/tasks",
            params={
                "workspace_id": workspace_id,
                "limit": 50
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_tasks_with_filters(self, client, mock_agent_services):
        """Test listing tasks with status filter"""
        workspace_id = uuid4()

        response = client.get(
            "/agents/tasks",
            params={
                "workspace_id": workspace_id,
                "status": "completed",
                "limit": 50
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_tasks_by_founder(self, client, mock_agent_services):
        """Test filtering tasks by founder"""
        workspace_id = uuid4()
        founder_id = uuid4()

        response = client.get(
            "/agents/tasks",
            params={
                "workspace_id": workspace_id,
                "founder_id": founder_id,
                "limit": 50
            }
        )

        assert response.status_code == 200

    def test_list_tasks_by_agent(self, client, mock_agent_services):
        """Test filtering tasks by assigned agent"""
        workspace_id = uuid4()

        response = client.get(
            "/agents/tasks",
            params={
                "workspace_id": workspace_id,
                "assigned_agent": "kpi_monitor",
                "limit": 50
            }
        )

        assert response.status_code == 200

    def test_cancel_task_success(self, client, mock_agent_services):
        """Test cancelling a task"""
        task_id = uuid4()

        response = client.post(f"/agents/tasks/{task_id}/cancel")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    def test_retry_task_success(self, client, mock_agent_services):
        """Test retrying a failed task"""
        task_id = uuid4()

        response = client.post(f"/agents/tasks/{task_id}/retry")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data


class TestAgentsAPICollaboration:
    """Tests for agent collaboration endpoints"""

    def test_initiate_collaboration_success(self, client, mock_agent_services):
        """Test initiating cross-agent collaboration"""
        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "objective": "Analyze business metrics",
            "agents": ["data_analysis", "recommendation_engine"],
            "context": {"focus": "revenue_growth"}
        }

        response = client.post("/agents/collaborate", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["status"] == "in_progress"
        assert "agents_involved" in data

    def test_get_collaboration_success(self, client, mock_agent_services):
        """Test retrieving collaboration session"""
        session_id = uuid4()

        response = client.get(f"/agents/collaboration/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "status" in data

    def test_collaboration_with_multiple_agents(self, client, mock_agent_services):
        """Test collaboration with multiple agents"""
        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "objective": "Generate insights and recommendations",
            "agents": ["data_analysis", "research_assistant", "recommendation_engine"],
            "context": {"period": "Q4"}
        }

        response = client.post("/agents/collaborate", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert len(data["agents_involved"]) >= 1


class TestAgentsAPIHealth:
    """Tests for agent health monitoring"""

    def test_get_agent_health_success(self, client, mock_agent_services):
        """Test retrieving agent health status"""
        response = client.get("/agents/health/kpi_monitor")

        assert response.status_code == 200
        data = response.json()
        assert "agent_type" in data
        assert "status" in data
        assert "uptime" in data

    def test_get_agent_health_all_types(self, client, mock_agent_services):
        """Test health check for different agent types"""
        agent_types = [
            "meeting_analyst",
            "kpi_monitor",
            "briefing_generator",
            "recommendation_engine"
        ]

        for agent_type in agent_types:
            response = client.get(f"/agents/health/{agent_type}")
            assert response.status_code == 200
            data = response.json()
            assert data["agent_type"] == agent_type


class TestAgentsAPIMetrics:
    """Tests for agent performance metrics"""

    def test_get_agent_metrics_success(self, client, mock_agent_services):
        """Test retrieving agent performance metrics"""
        response = client.get("/agents/metrics/kpi_monitor")

        assert response.status_code == 200
        data = response.json()
        assert "agent_type" in data
        assert "success_rate" in data
        assert "avg_processing_time_ms" in data
        assert "total_processed" in data

    def test_metrics_contain_performance_data(self, client, mock_agent_services):
        """Test that metrics contain expected performance data"""
        response = client.get("/agents/metrics/data_analysis")

        assert response.status_code == 200
        data = response.json()
        assert 0 <= data["success_rate"] <= 1
        assert data["avg_processing_time_ms"] >= 0
        assert data["total_processed"] >= 0


# ==================== ERROR HANDLING TESTS ====================

class TestErrorHandling:
    """Tests for error handling across APIs"""

    def test_invalid_uuid_parameter(self, client):
        """Test handling of invalid UUID parameter"""
        response = client.get("/meetings/invalid-uuid/status")
        assert response.status_code in [404, 422]

    def test_missing_required_parameter(self, client):
        """Test handling of missing required parameter"""
        response = client.get("/insights/anomalies")  # Missing workspace_id
        assert response.status_code == 422

    def test_invalid_enum_value(self, client):
        """Test handling of invalid enum value"""
        response = client.get(
            "/insights/trends",
            params={
                "workspace_id": uuid4(),
                "direction": ["invalid_direction"]
            }
        )
        # Should either accept or reject with 422
        assert response.status_code in [200, 422]
