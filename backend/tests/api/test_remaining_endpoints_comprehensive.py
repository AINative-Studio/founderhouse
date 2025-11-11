"""
Comprehensive tests for remaining low-coverage API endpoints

This test suite targets endpoints with <80% coverage to bring them above 80%.
Focus areas:
- Briefings API (18% -> 80%+)
- Insights API (22% -> 80%+)
- Feedback API (27% -> 80%+)
- Voice API (27% -> 80%+)
- Recommendations API (28% -> 80%+)
- Loom API (30% -> 80%+)

Test Strategy:
- Mock all service dependencies
- Test all HTTP methods (GET, POST, PUT, PATCH, DELETE)
- Test success cases, error cases, edge cases
- Test query parameter filtering and validation
- Test malformed requests and database errors
"""
import pytest
from uuid import uuid4, UUID
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


# ============================================================================
# BRIEFINGS API TESTS (18% coverage -> 80%+)
# ============================================================================

@pytest.fixture
def mock_briefing_service():
    """Mock briefing service for all briefing tests"""
    with patch('app.api.v1.briefings.get_briefing_service') as mock:
        service = MagicMock()

        # Mock supabase queries
        mock_table = MagicMock()
        mock_query = MagicMock()

        # Setup chainable query methods
        mock_query.eq.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.gte.return_value = mock_query
        mock_query.lte.return_value = mock_query
        mock_query.in_.return_value = mock_query
        mock_query.range.return_value = mock_query

        mock_table.select.return_value = mock_query
        mock_table.upsert.return_value = mock_query

        service.supabase.table.return_value = mock_table

        # Mock service methods
        service.generate_briefing = AsyncMock(return_value={
            "id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "briefing_type": "morning",
            "status": "completed",
            "content": {"summary": "Test briefing"},
            "created_at": datetime.utcnow().isoformat()
        })

        mock.return_value = service
        yield service, mock_query


class TestBriefingsAPI:
    """Comprehensive tests for Briefings API"""

    def test_get_latest_briefing_success(self, client, mock_briefing_service):
        """Test getting latest briefing successfully"""
        service, mock_query = mock_briefing_service

        briefing_id = uuid4()
        workspace_id = uuid4()
        founder_id = uuid4()

        mock_query.execute.return_value = MagicMock(data=[{
            "id": str(briefing_id),
            "workspace_id": str(workspace_id),
            "founder_id": str(founder_id),
            "briefing_type": "morning",
            "status": "completed",
            "content": {"summary": "Daily briefing"},
            "created_at": datetime.utcnow().isoformat()
        }])

        response = client.get(
            f"/api/v1/briefings/{founder_id}",
            params={"workspace_id": str(workspace_id)}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["briefing_type"] == "morning"
        assert data["status"] == "completed"

    def test_get_latest_briefing_with_type_filter(self, client, mock_briefing_service):
        """Test getting latest briefing with type filter"""
        service, mock_query = mock_briefing_service

        mock_query.execute.return_value = MagicMock(data=[{
            "id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "briefing_type": "evening",
            "status": "completed",
            "content": {},
            "created_at": datetime.utcnow().isoformat()
        }])

        response = client.get(
            f"/api/v1/briefings/{uuid4()}",
            params={"workspace_id": str(uuid4()), "briefing_type": "evening"}
        )

        assert response.status_code == 200
        assert response.json()["briefing_type"] == "evening"

    def test_get_latest_briefing_not_found(self, client, mock_briefing_service):
        """Test getting briefing when none exists"""
        service, mock_query = mock_briefing_service
        mock_query.execute.return_value = MagicMock(data=[])

        response = client.get(
            f"/api/v1/briefings/{uuid4()}",
            params={"workspace_id": str(uuid4())}
        )

        assert response.status_code == 404
        assert "No briefing found" in response.json()["detail"]

    def test_get_latest_briefing_db_error(self, client, mock_briefing_service):
        """Test database error when fetching briefing"""
        service, mock_query = mock_briefing_service
        mock_query.execute.side_effect = Exception("Database connection failed")

        response = client.get(
            f"/api/v1/briefings/{uuid4()}",
            params={"workspace_id": str(uuid4())}
        )

        assert response.status_code == 500
        assert "Error fetching briefing" in response.json()["detail"]

    def test_generate_briefing_success(self, client, mock_briefing_service):
        """Test generating a new briefing"""
        service, mock_query = mock_briefing_service

        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "briefing_type": "morning"
        }

        response = client.post("/api/v1/briefings/generate", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["briefing_type"] == "morning"
        assert data["status"] == "completed"

    def test_generate_briefing_with_date_range(self, client, mock_briefing_service):
        """Test generating briefing with custom date range"""
        service, mock_query = mock_briefing_service

        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()

        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "briefing_type": "investor",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }

        response = client.post("/api/v1/briefings/generate", json=request_data)

        assert response.status_code == 200
        service.generate_briefing.assert_called_once()

    def test_generate_briefing_failure(self, client, mock_briefing_service):
        """Test briefing generation failure"""
        service, mock_query = mock_briefing_service
        service.generate_briefing = AsyncMock(return_value=None)

        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "briefing_type": "morning"
        }

        response = client.post("/api/v1/briefings/generate", json=request_data)

        assert response.status_code == 500
        assert "Failed to generate briefing" in response.json()["detail"]

    def test_generate_briefing_service_error(self, client, mock_briefing_service):
        """Test service error during briefing generation"""
        service, mock_query = mock_briefing_service
        service.generate_briefing = AsyncMock(side_effect=Exception("AI service unavailable"))

        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "briefing_type": "morning"
        }

        response = client.post("/api/v1/briefings/generate", json=request_data)

        assert response.status_code == 500
        assert "Error generating briefing" in response.json()["detail"]

    def test_get_morning_brief_existing(self, client, mock_briefing_service):
        """Test getting existing morning brief"""
        service, mock_query = mock_briefing_service

        mock_query.execute.return_value = MagicMock(data=[{
            "id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "briefing_type": "morning",
            "status": "completed",
            "content": {"summary": "Good morning!"},
            "created_at": datetime.utcnow().isoformat()
        }])

        response = client.get(
            "/api/v1/briefings/morning",
            params={"workspace_id": str(uuid4()), "founder_id": str(uuid4())}
        )

        assert response.status_code == 200
        assert response.json()["briefing_type"] == "morning"

    def test_get_morning_brief_generate_new(self, client, mock_briefing_service):
        """Test generating new morning brief when none exists"""
        service, mock_query = mock_briefing_service

        # First query returns empty (no existing briefing)
        mock_query.execute.return_value = MagicMock(data=[])

        response = client.get(
            "/api/v1/briefings/morning",
            params={"workspace_id": str(uuid4()), "founder_id": str(uuid4())}
        )

        assert response.status_code == 200
        service.generate_briefing.assert_called_once()

    def test_get_morning_brief_generation_failure(self, client, mock_briefing_service):
        """Test morning brief generation failure"""
        service, mock_query = mock_briefing_service
        mock_query.execute.return_value = MagicMock(data=[])
        service.generate_briefing = AsyncMock(return_value=None)

        response = client.get(
            "/api/v1/briefings/morning",
            params={"workspace_id": str(uuid4()), "founder_id": str(uuid4())}
        )

        assert response.status_code == 500
        assert "Failed to generate morning brief" in response.json()["detail"]

    def test_get_morning_brief_with_custom_date(self, client, mock_briefing_service):
        """Test getting morning brief for specific date"""
        service, mock_query = mock_briefing_service

        mock_query.execute.return_value = MagicMock(data=[{
            "id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "briefing_type": "morning",
            "status": "completed",
            "content": {},
            "created_at": datetime.utcnow().isoformat()
        }])

        custom_date = datetime.utcnow() - timedelta(days=1)
        response = client.get(
            "/api/v1/briefings/morning",
            params={
                "workspace_id": str(uuid4()),
                "founder_id": str(uuid4()),
                "date": custom_date.isoformat()
            }
        )

        assert response.status_code == 200

    def test_get_evening_wrap_existing(self, client, mock_briefing_service):
        """Test getting existing evening wrap"""
        service, mock_query = mock_briefing_service

        mock_query.execute.return_value = MagicMock(data=[{
            "id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "briefing_type": "evening",
            "status": "completed",
            "content": {"summary": "Evening wrap"},
            "created_at": datetime.utcnow().isoformat()
        }])

        response = client.get(
            "/api/v1/briefings/evening",
            params={"workspace_id": str(uuid4()), "founder_id": str(uuid4())}
        )

        assert response.status_code == 200
        assert response.json()["briefing_type"] == "evening"

    def test_get_evening_wrap_generate_new(self, client, mock_briefing_service):
        """Test generating new evening wrap"""
        service, mock_query = mock_briefing_service
        mock_query.execute.return_value = MagicMock(data=[])

        response = client.get(
            "/api/v1/briefings/evening",
            params={"workspace_id": str(uuid4()), "founder_id": str(uuid4())}
        )

        assert response.status_code == 200
        service.generate_briefing.assert_called_once()

    def test_get_evening_wrap_generation_failure(self, client, mock_briefing_service):
        """Test evening wrap generation failure"""
        service, mock_query = mock_briefing_service
        mock_query.execute.return_value = MagicMock(data=[])
        service.generate_briefing = AsyncMock(return_value=None)

        response = client.get(
            "/api/v1/briefings/evening",
            params={"workspace_id": str(uuid4()), "founder_id": str(uuid4())}
        )

        assert response.status_code == 500
        assert "Failed to generate evening wrap" in response.json()["detail"]

    def test_get_investor_summary_existing(self, client, mock_briefing_service):
        """Test getting existing investor summary"""
        service, mock_query = mock_briefing_service

        mock_query.execute.return_value = MagicMock(data=[{
            "id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "briefing_type": "investor",
            "status": "completed",
            "content": {"weekly_summary": "Great week!"},
            "start_date": datetime.utcnow().isoformat(),
            "end_date": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat()
        }])

        response = client.get(
            "/api/v1/briefings/investor-weekly",
            params={"workspace_id": str(uuid4()), "founder_id": str(uuid4())}
        )

        assert response.status_code == 200
        assert response.json()["briefing_type"] == "investor"

    def test_get_investor_summary_generate_new(self, client, mock_briefing_service):
        """Test generating new investor summary"""
        service, mock_query = mock_briefing_service
        mock_query.execute.return_value = MagicMock(data=[])

        response = client.get(
            "/api/v1/briefings/investor-weekly",
            params={"workspace_id": str(uuid4()), "founder_id": str(uuid4())}
        )

        assert response.status_code == 200
        service.generate_briefing.assert_called_once()

    def test_get_investor_summary_with_week_start(self, client, mock_briefing_service):
        """Test getting investor summary with custom week start"""
        service, mock_query = mock_briefing_service

        mock_query.execute.return_value = MagicMock(data=[{
            "id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "briefing_type": "investor",
            "status": "completed",
            "content": {},
            "start_date": datetime.utcnow().isoformat(),
            "end_date": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat()
        }])

        week_start = datetime.utcnow() - timedelta(days=7)
        response = client.get(
            "/api/v1/briefings/investor-weekly",
            params={
                "workspace_id": str(uuid4()),
                "founder_id": str(uuid4()),
                "week_start": week_start.isoformat()
            }
        )

        assert response.status_code == 200

    def test_get_investor_summary_generation_failure(self, client, mock_briefing_service):
        """Test investor summary generation failure"""
        service, mock_query = mock_briefing_service
        mock_query.execute.return_value = MagicMock(data=[])
        service.generate_briefing = AsyncMock(return_value=None)

        response = client.get(
            "/api/v1/briefings/investor-weekly",
            params={"workspace_id": str(uuid4()), "founder_id": str(uuid4())}
        )

        assert response.status_code == 500
        assert "Failed to generate investor summary" in response.json()["detail"]

    def test_schedule_briefing_success(self, client, mock_briefing_service):
        """Test scheduling automated briefing"""
        service, mock_query = mock_briefing_service

        mock_query.execute.return_value = MagicMock(data=[{
            "id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "briefing_type": "morning",
            "schedule_time": "08:00",
            "timezone": "UTC",
            "delivery_channels": ["email", "discord"],
            "is_active": True,
            "created_at": datetime.utcnow().isoformat()
        }])

        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "briefing_type": "morning",
            "schedule_time": "08:00",
            "timezone": "UTC",
            "delivery_channels": ["email"],
            "is_active": True
        }

        response = client.post("/api/v1/briefings/schedule", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True

    def test_schedule_briefing_db_failure(self, client, mock_briefing_service):
        """Test schedule creation database failure"""
        service, mock_query = mock_briefing_service
        mock_query.execute.return_value = MagicMock(data=[])

        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "briefing_type": "morning",
            "schedule_time": "08:00",
            "timezone": "UTC",
            "delivery_channels": ["email"],
            "is_active": True
        }

        response = client.post("/api/v1/briefings/schedule", json=request_data)

        assert response.status_code == 500
        assert "Failed to create schedule" in response.json()["detail"]

    def test_schedule_briefing_error(self, client, mock_briefing_service):
        """Test schedule creation error"""
        service, mock_query = mock_briefing_service
        mock_query.execute.side_effect = Exception("Database error")

        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "briefing_type": "morning",
            "schedule_time": "08:00",
            "timezone": "UTC",
            "delivery_channels": ["email"],
            "is_active": True
        }

        response = client.post("/api/v1/briefings/schedule", json=request_data)

        assert response.status_code == 500
        assert "Error scheduling briefing" in response.json()["detail"]

    def test_list_briefings_all(self, client, mock_briefing_service):
        """Test listing all briefings"""
        service, mock_query = mock_briefing_service

        briefings_data = [
            {
                "id": str(uuid4()),
                "workspace_id": str(uuid4()),
                "founder_id": str(uuid4()),
                "briefing_type": "morning",
                "status": "completed",
                "content": {},
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": str(uuid4()),
                "workspace_id": str(uuid4()),
                "founder_id": str(uuid4()),
                "briefing_type": "evening",
                "status": "completed",
                "content": {},
                "created_at": datetime.utcnow().isoformat()
            }
        ]

        mock_query.execute.return_value = MagicMock(data=briefings_data)

        response = client.get(
            "/api/v1/briefings/list",
            params={"workspace_id": str(uuid4())}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["briefings"]) == 2
        assert data["total_count"] == 2

    def test_list_briefings_with_filters(self, client, mock_briefing_service):
        """Test listing briefings with multiple filters"""
        service, mock_query = mock_briefing_service

        mock_query.execute.return_value = MagicMock(data=[{
            "id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "briefing_type": "morning",
            "status": "completed",
            "content": {},
            "created_at": datetime.utcnow().isoformat()
        }])

        response = client.get(
            "/api/v1/briefings/list",
            params={
                "workspace_id": str(uuid4()),
                "founder_id": str(uuid4()),
                "briefing_type": ["morning"],
                "status": ["completed"],
                "limit": 10,
                "offset": 0
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "briefings" in data
        assert "total_count" in data

    def test_list_briefings_with_date_range(self, client, mock_briefing_service):
        """Test listing briefings with date range filter"""
        service, mock_query = mock_briefing_service

        mock_query.execute.return_value = MagicMock(data=[])

        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()

        response = client.get(
            "/api/v1/briefings/list",
            params={
                "workspace_id": str(uuid4()),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        )

        assert response.status_code == 200

    def test_list_briefings_pagination(self, client, mock_briefing_service):
        """Test briefing list pagination"""
        service, mock_query = mock_briefing_service

        # Create 60 briefings to test pagination
        briefings_data = [
            {
                "id": str(uuid4()),
                "workspace_id": str(uuid4()),
                "founder_id": str(uuid4()),
                "briefing_type": "morning",
                "status": "completed",
                "content": {},
                "created_at": datetime.utcnow().isoformat()
            }
            for _ in range(60)
        ]

        mock_query.execute.return_value = MagicMock(data=briefings_data)

        response = client.get(
            "/api/v1/briefings/list",
            params={"workspace_id": str(uuid4()), "limit": 50, "offset": 0}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["has_more"] is True
        assert data["total_count"] == 60

    def test_list_briefings_error(self, client, mock_briefing_service):
        """Test list briefings database error"""
        service, mock_query = mock_briefing_service
        mock_query.execute.side_effect = Exception("Database connection lost")

        response = client.get(
            "/api/v1/briefings/list",
            params={"workspace_id": str(uuid4())}
        )

        assert response.status_code == 500
        assert "Error listing briefings" in response.json()["detail"]


# ============================================================================
# INSIGHTS API TESTS (22% coverage -> 80%+)
# ============================================================================

@pytest.fixture
def mock_anomaly_service():
    """Mock anomaly detection service for insights tests"""
    with patch('app.api.v1.insights.get_anomaly_service') as mock:
        service = MagicMock()

        # Mock supabase queries
        mock_table = MagicMock()
        mock_query = MagicMock()

        mock_query.eq.return_value = mock_query
        mock_query.gte.return_value = mock_query
        mock_query.in_.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.range.return_value = mock_query

        mock_table.select.return_value = mock_query
        service.supabase.table.return_value = mock_table

        # Mock service methods
        service.analyze_metric = AsyncMock(return_value={
            "metric_id": str(uuid4()),
            "anomalies": [],
            "trends": [],
            "statistics": {"mean": 100, "std": 10}
        })

        mock.return_value = service
        yield service, mock_query


class TestInsightsAPI:
    """Comprehensive tests for Insights API"""

    def test_list_anomalies_success(self, client, mock_anomaly_service):
        """Test listing anomalies successfully"""
        service, mock_query = mock_anomaly_service

        anomalies_data = [
            {
                "id": str(uuid4()),
                "workspace_id": str(uuid4()),
                "metric_id": str(uuid4()),
                "severity": "high",
                "detected_at": datetime.utcnow().isoformat(),
                "is_acknowledged": False,
                "value": 150,
                "expected_range": [80, 120]
            }
        ]

        mock_query.execute.return_value = MagicMock(data=anomalies_data)

        response = client.get(
            "/api/v1/insights/anomalies",
            params={"workspace_id": str(uuid4())}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["anomalies"]) == 1
        assert data["anomalies"][0]["severity"] == "high"

    def test_list_anomalies_with_filters(self, client, mock_anomaly_service):
        """Test listing anomalies with multiple filters"""
        service, mock_query = mock_anomaly_service

        mock_query.execute.return_value = MagicMock(data=[])

        metric_ids = [uuid4(), uuid4()]
        response = client.get(
            "/api/v1/insights/anomalies",
            params={
                "workspace_id": str(uuid4()),
                "metric_ids": [str(mid) for mid in metric_ids],
                "severity": ["high", "critical"],
                "is_acknowledged": False,
                "days_back": 7,
                "limit": 20,
                "offset": 0
            }
        )

        assert response.status_code == 200

    def test_list_anomalies_pagination(self, client, mock_anomaly_service):
        """Test anomaly list pagination"""
        service, mock_query = mock_anomaly_service

        # Create 60 anomalies
        anomalies_data = [
            {
                "id": str(uuid4()),
                "workspace_id": str(uuid4()),
                "metric_id": str(uuid4()),
                "severity": "medium",
                "detected_at": datetime.utcnow().isoformat(),
                "is_acknowledged": False
            }
            for _ in range(60)
        ]

        mock_query.execute.return_value = MagicMock(data=anomalies_data)

        response = client.get(
            "/api/v1/insights/anomalies",
            params={"workspace_id": str(uuid4()), "limit": 50}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["has_more"] is True

    def test_list_anomalies_error(self, client, mock_anomaly_service):
        """Test anomaly listing error"""
        service, mock_query = mock_anomaly_service
        mock_query.execute.side_effect = Exception("Database error")

        response = client.get(
            "/api/v1/insights/anomalies",
            params={"workspace_id": str(uuid4())}
        )

        assert response.status_code == 500
        assert "Error fetching anomalies" in response.json()["detail"]

    def test_list_trends_success(self, client, mock_anomaly_service):
        """Test listing trends successfully"""
        service, mock_query = mock_anomaly_service

        trends_data = [
            {
                "id": str(uuid4()),
                "workspace_id": str(uuid4()),
                "metric_id": str(uuid4()),
                "direction": "upward",
                "is_significant": True,
                "slope": 0.15,
                "created_at": datetime.utcnow().isoformat()
            }
        ]

        mock_query.execute.return_value = MagicMock(data=trends_data)

        response = client.get(
            "/api/v1/insights/trends",
            params={"workspace_id": str(uuid4())}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["trends"]) == 1
        assert data["trends"][0]["direction"] == "upward"

    def test_list_trends_with_filters(self, client, mock_anomaly_service):
        """Test listing trends with filters"""
        service, mock_query = mock_anomaly_service

        mock_query.execute.return_value = MagicMock(data=[])

        response = client.get(
            "/api/v1/insights/trends",
            params={
                "workspace_id": str(uuid4()),
                "direction": ["upward"],
                "is_significant": True,
                "days_back": 30
            }
        )

        assert response.status_code == 200

    def test_list_trends_pagination(self, client, mock_anomaly_service):
        """Test trends list pagination"""
        service, mock_query = mock_anomaly_service

        trends_data = [
            {
                "id": str(uuid4()),
                "workspace_id": str(uuid4()),
                "metric_id": str(uuid4()),
                "direction": "upward",
                "is_significant": True,
                "created_at": datetime.utcnow().isoformat()
            }
            for _ in range(60)
        ]

        mock_query.execute.return_value = MagicMock(data=trends_data)

        response = client.get(
            "/api/v1/insights/trends",
            params={"workspace_id": str(uuid4()), "limit": 50}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["has_more"] is True

    def test_list_trends_error(self, client, mock_anomaly_service):
        """Test trends listing error"""
        service, mock_query = mock_anomaly_service
        mock_query.execute.side_effect = Exception("Query failed")

        response = client.get(
            "/api/v1/insights/trends",
            params={"workspace_id": str(uuid4())}
        )

        assert response.status_code == 500
        assert "Error fetching trends" in response.json()["detail"]

    def test_analyze_metric_success(self, client, mock_anomaly_service):
        """Test deep metric analysis"""
        service, mock_query = mock_anomaly_service

        metric_id = uuid4()
        workspace_id = uuid4()

        response = client.get(
            f"/api/v1/insights/{metric_id}/analysis",
            params={"workspace_id": str(workspace_id), "days_back": 30}
        )

        assert response.status_code == 200
        data = response.json()
        assert "metric_id" in data
        assert "statistics" in data
        service.analyze_metric.assert_called_once()

    def test_analyze_metric_with_detection_methods(self, client, mock_anomaly_service):
        """Test metric analysis with specific detection methods"""
        service, mock_query = mock_anomaly_service

        metric_id = uuid4()
        response = client.get(
            f"/api/v1/insights/{metric_id}/analysis",
            params={
                "workspace_id": str(uuid4()),
                "days_back": 60,
                "detection_methods": ["z_score", "moving_average"]
            }
        )

        assert response.status_code == 200

    def test_analyze_metric_error(self, client, mock_anomaly_service):
        """Test metric analysis error"""
        service, mock_query = mock_anomaly_service
        service.analyze_metric = AsyncMock(side_effect=Exception("Analysis failed"))

        response = client.get(
            f"/api/v1/insights/{uuid4()}/analysis",
            params={"workspace_id": str(uuid4())}
        )

        assert response.status_code == 500
        assert "Error analyzing metric" in response.json()["detail"]

    def test_trigger_analysis_all_metrics(self, client, mock_anomaly_service):
        """Test triggering analysis for all metrics"""
        service, mock_query = mock_anomaly_service

        metrics_data = [
            {"id": str(uuid4())},
            {"id": str(uuid4())},
            {"id": str(uuid4())}
        ]

        mock_query.execute.return_value = MagicMock(data=metrics_data)

        service.analyze_metric = AsyncMock(return_value={
            "metric_id": str(uuid4()),
            "anomalies": [{"id": str(uuid4())}],
            "trends": [{"id": str(uuid4())}]
        })

        response = client.post(
            "/api/v1/insights/analyze",
            params={"workspace_id": str(uuid4()), "days_back": 30}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["analyzed_metrics"] == 3
        assert data["anomalies_detected"] == 3
        assert data["trends_detected"] == 3

    def test_trigger_analysis_specific_metrics(self, client, mock_anomaly_service):
        """Test triggering analysis for specific metrics"""
        service, mock_query = mock_anomaly_service

        metric_ids = [uuid4(), uuid4()]
        metrics_data = [{"id": str(mid)} for mid in metric_ids]

        mock_query.execute.return_value = MagicMock(data=metrics_data)

        service.analyze_metric = AsyncMock(return_value={
            "metric_id": str(uuid4()),
            "anomalies": [],
            "trends": []
        })

        response = client.post(
            "/api/v1/insights/analyze",
            params={
                "workspace_id": str(uuid4()),
                "metric_ids": [str(mid) for mid in metric_ids]
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["analyzed_metrics"] == 2

    def test_trigger_analysis_with_errors(self, client, mock_anomaly_service):
        """Test analysis with partial errors"""
        service, mock_query = mock_anomaly_service

        metrics_data = [
            {"id": str(uuid4())},
            {"id": str(uuid4())}
        ]

        mock_query.execute.return_value = MagicMock(data=metrics_data)

        # First metric succeeds, second fails
        service.analyze_metric = AsyncMock(side_effect=[
            {"metric_id": str(uuid4()), "anomalies": [], "trends": []},
            Exception("Analysis failed")
        ])

        response = client.post(
            "/api/v1/insights/analyze",
            params={"workspace_id": str(uuid4())}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["analyzed_metrics"] == 1
        assert len(data["errors"]) == 1

    def test_trigger_analysis_error(self, client, mock_anomaly_service):
        """Test analysis trigger error"""
        service, mock_query = mock_anomaly_service
        mock_query.execute.side_effect = Exception("Database error")

        response = client.post(
            "/api/v1/insights/analyze",
            params={"workspace_id": str(uuid4())}
        )

        assert response.status_code == 500
        assert "Error triggering analysis" in response.json()["detail"]


# ============================================================================
# FEEDBACK API TESTS (27% coverage -> 80%+)
# ============================================================================

@pytest.fixture
def mock_feedback_service():
    """Mock feedback service"""
    with patch('app.api.v1.feedback.get_feedback_service') as mock:
        service = MagicMock()

        # Mock service methods
        service.submit_feedback = AsyncMock(return_value={
            "id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "feedback_type": "bug",
            "category": "performance",
            "status": "new",
            "sentiment": "negative",
            "content": "App is slow",
            "created_at": datetime.utcnow().isoformat()
        })

        service.get_feedback = AsyncMock(return_value={
            "id": str(uuid4()),
            "feedback_type": "feature_request",
            "status": "new"
        })

        service.list_feedback = AsyncMock(return_value=[])

        service.update_feedback_status = AsyncMock(return_value={
            "id": str(uuid4()),
            "status": "in_progress"
        })

        service.upvote_feedback = AsyncMock(return_value=True)

        service.get_analytics = AsyncMock(return_value={
            "total_feedback": 100,
            "by_type": {"bug": 30, "feature_request": 50},
            "sentiment_distribution": {"positive": 40, "negative": 20, "neutral": 40}
        })

        mock.return_value = service
        yield service


class TestFeedbackAPI:
    """Comprehensive tests for Feedback API"""

    def test_submit_feedback_success(self, client, mock_feedback_service):
        """Test submitting feedback successfully"""
        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "feedback_type": "bug",
            "category": "performance",
            "content": "The app crashes on startup",
            "metadata": {"device": "iPhone 12"}
        }

        response = client.post("/api/v1/feedback", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["feedback_type"] == "bug"

    def test_submit_feedback_failure(self, client, mock_feedback_service):
        """Test feedback submission failure"""
        mock_feedback_service.submit_feedback = AsyncMock(return_value=None)

        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "feedback_type": "suggestion",
            "category": "ui",
            "content": "Improve dashboard layout"
        }

        response = client.post("/api/v1/feedback", json=request_data)

        assert response.status_code == 500
        assert "Failed to submit feedback" in response.json()["detail"]

    def test_submit_feedback_error(self, client, mock_feedback_service):
        """Test feedback submission error"""
        mock_feedback_service.submit_feedback = AsyncMock(
            side_effect=Exception("Database error")
        )

        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "feedback_type": "bug",
            "category": "functionality",
            "content": "Login not working"
        }

        response = client.post("/api/v1/feedback", json=request_data)

        assert response.status_code == 500
        assert "Error submitting feedback" in response.json()["detail"]

    def test_get_feedback_success(self, client, mock_feedback_service):
        """Test getting feedback by ID"""
        feedback_id = uuid4()

        response = client.get(f"/api/v1/feedback/{feedback_id}")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data

    def test_get_feedback_not_found(self, client, mock_feedback_service):
        """Test getting non-existent feedback"""
        mock_feedback_service.get_feedback = AsyncMock(return_value=None)

        response = client.get(f"/api/v1/feedback/{uuid4()}")

        assert response.status_code == 404
        assert "Feedback not found" in response.json()["detail"]

    def test_get_feedback_error(self, client, mock_feedback_service):
        """Test get feedback error"""
        mock_feedback_service.get_feedback = AsyncMock(
            side_effect=Exception("Database error")
        )

        response = client.get(f"/api/v1/feedback/{uuid4()}")

        assert response.status_code == 500
        assert "Error fetching feedback" in response.json()["detail"]

    def test_list_feedback_all(self, client, mock_feedback_service):
        """Test listing all feedback"""
        mock_feedback_service.list_feedback = AsyncMock(return_value=[
            {
                "id": str(uuid4()),
                "feedback_type": "bug",
                "status": "new"
            },
            {
                "id": str(uuid4()),
                "feedback_type": "feature_request",
                "status": "in_progress"
            }
        ])

        response = client.get(
            "/api/v1/feedback",
            params={"workspace_id": str(uuid4())}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["feedback_items"]) == 2

    def test_list_feedback_with_filters(self, client, mock_feedback_service):
        """Test listing feedback with filters"""
        mock_feedback_service.list_feedback = AsyncMock(return_value=[])

        response = client.get(
            "/api/v1/feedback",
            params={
                "workspace_id": str(uuid4()),
                "founder_id": str(uuid4()),
                "feedback_type": "bug",
                "category": "performance",
                "status": "new",
                "sentiment": "negative",
                "limit": 20
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "filters_applied" in data

    def test_list_feedback_error(self, client, mock_feedback_service):
        """Test list feedback error"""
        mock_feedback_service.list_feedback = AsyncMock(
            side_effect=Exception("Query failed")
        )

        response = client.get(
            "/api/v1/feedback",
            params={"workspace_id": str(uuid4())}
        )

        assert response.status_code == 500
        assert "Error listing feedback" in response.json()["detail"]

    def test_update_feedback_status_success(self, client, mock_feedback_service):
        """Test updating feedback status"""
        feedback_id = uuid4()

        response = client.patch(
            f"/api/v1/feedback/{feedback_id}/status",
            json={"status": "in_progress", "admin_notes": "Working on it"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"

    def test_update_feedback_status_not_found(self, client, mock_feedback_service):
        """Test updating non-existent feedback"""
        mock_feedback_service.update_feedback_status = AsyncMock(return_value=None)

        response = client.patch(
            f"/api/v1/feedback/{uuid4()}/status",
            json={"status": "resolved"}
        )

        assert response.status_code == 404
        assert "Feedback not found" in response.json()["detail"]

    def test_update_feedback_status_error(self, client, mock_feedback_service):
        """Test update feedback status error"""
        mock_feedback_service.update_feedback_status = AsyncMock(
            side_effect=Exception("Update failed")
        )

        response = client.patch(
            f"/api/v1/feedback/{uuid4()}/status",
            json={"status": "resolved"}
        )

        assert response.status_code == 500
        assert "Error updating feedback" in response.json()["detail"]

    def test_upvote_feedback_success(self, client, mock_feedback_service):
        """Test upvoting feedback"""
        feedback_id = uuid4()

        response = client.post(f"/api/v1/feedback/{feedback_id}/upvote")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "upvoted"
        assert data["feedback_id"] == str(feedback_id)

    def test_upvote_feedback_not_found(self, client, mock_feedback_service):
        """Test upvoting non-existent feedback"""
        mock_feedback_service.upvote_feedback = AsyncMock(return_value=False)

        response = client.post(f"/api/v1/feedback/{uuid4()}/upvote")

        assert response.status_code == 404
        assert "Feedback not found" in response.json()["detail"]

    def test_upvote_feedback_error(self, client, mock_feedback_service):
        """Test upvote feedback error"""
        mock_feedback_service.upvote_feedback = AsyncMock(
            side_effect=Exception("Database error")
        )

        response = client.post(f"/api/v1/feedback/{uuid4()}/upvote")

        assert response.status_code == 500
        assert "Error upvoting feedback" in response.json()["detail"]

    def test_get_feedback_analytics_success(self, client, mock_feedback_service):
        """Test getting feedback analytics"""
        response = client.get(
            "/api/v1/feedback/analytics/summary",
            params={"workspace_id": str(uuid4()), "days": 30}
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_feedback" in data
        assert "by_type" in data

    def test_get_feedback_analytics_custom_period(self, client, mock_feedback_service):
        """Test analytics with custom time period"""
        response = client.get(
            "/api/v1/feedback/analytics/summary",
            params={"workspace_id": str(uuid4()), "days": 90}
        )

        assert response.status_code == 200

    def test_get_feedback_analytics_error(self, client, mock_feedback_service):
        """Test analytics error"""
        mock_feedback_service.get_analytics = AsyncMock(
            side_effect=Exception("Analytics failed")
        )

        response = client.get(
            "/api/v1/feedback/analytics/summary",
            params={"workspace_id": str(uuid4())}
        )

        assert response.status_code == 500
        assert "Error fetching analytics" in response.json()["detail"]


# ============================================================================
# VOICE API TESTS (27% coverage -> 80%+)
# ============================================================================

@pytest.fixture
def mock_voice_service():
    """Mock voice command service"""
    with patch('app.api.v1.voice.get_voice_service') as mock:
        service = MagicMock()

        service.process_command = AsyncMock(return_value={
            "id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "transcript": "Show me Q4 revenue",
            "intent": "data_query",
            "entities": {"metric": "revenue", "period": "Q4"},
            "status": "completed",
            "result": {"revenue": 1000000}
        })

        service.transcribe_audio = AsyncMock(return_value={
            "transcript": "Show me Q4 revenue",
            "confidence": 0.95,
            "language": "en-US"
        })

        service.get_command_history = AsyncMock(return_value=[])

        mock.return_value = service
        yield service


class TestVoiceAPI:
    """Comprehensive tests for Voice API"""

    def test_process_voice_command_success(self, client, mock_voice_service):
        """Test processing voice command successfully"""
        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "audio_url": "https://example.com/audio.mp3"
        }

        response = client.post("/api/v1/voice/command", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["status"] == "completed"

    def test_process_voice_command_with_text(self, client, mock_voice_service):
        """Test processing voice command with pre-transcribed text"""
        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "text": "Show me Q4 revenue"
        }

        response = client.post("/api/v1/voice/command", json=request_data)

        assert response.status_code == 200

    def test_process_voice_command_failure(self, client, mock_voice_service):
        """Test voice command processing failure"""
        mock_voice_service.process_command = AsyncMock(return_value=None)

        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "text": "Invalid command"
        }

        response = client.post("/api/v1/voice/command", json=request_data)

        assert response.status_code == 500
        assert "Failed to process voice command" in response.json()["detail"]

    def test_process_voice_command_error(self, client, mock_voice_service):
        """Test voice command processing error"""
        mock_voice_service.process_command = AsyncMock(
            side_effect=Exception("Processing error")
        )

        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "text": "Show me revenue"
        }

        response = client.post("/api/v1/voice/command", json=request_data)

        assert response.status_code == 500
        assert "Error processing command" in response.json()["detail"]

    def test_transcribe_audio_success(self, client, mock_voice_service):
        """Test audio transcription successfully"""
        request_data = {
            "audio_url": "https://example.com/audio.mp3"
        }

        response = client.post("/api/v1/voice/transcribe", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "transcript" in data
        assert data["confidence"] == 0.95

    def test_transcribe_audio_base64(self, client, mock_voice_service):
        """Test transcribing base64-encoded audio"""
        request_data = {
            "audio_base64": "SGVsbG8gd29ybGQ="
        }

        response = client.post("/api/v1/voice/transcribe", json=request_data)

        assert response.status_code == 200

    def test_transcribe_audio_failure(self, client, mock_voice_service):
        """Test audio transcription failure"""
        mock_voice_service.transcribe_audio = AsyncMock(return_value=None)

        request_data = {
            "audio_url": "https://example.com/bad-audio.mp3"
        }

        response = client.post("/api/v1/voice/transcribe", json=request_data)

        assert response.status_code == 500
        assert "Failed to transcribe audio" in response.json()["detail"]

    def test_transcribe_audio_error(self, client, mock_voice_service):
        """Test audio transcription error"""
        mock_voice_service.transcribe_audio = AsyncMock(
            side_effect=Exception("Transcription service down")
        )

        request_data = {
            "audio_url": "https://example.com/audio.mp3"
        }

        response = client.post("/api/v1/voice/transcribe", json=request_data)

        assert response.status_code == 500
        assert "Error transcribing audio" in response.json()["detail"]

    def test_get_command_history_success(self, client, mock_voice_service):
        """Test getting command history"""
        founder_id = uuid4()
        workspace_id = uuid4()

        mock_voice_service.get_command_history = AsyncMock(return_value=[
            {
                "id": str(uuid4()),
                "transcript": "Show revenue",
                "status": "completed",
                "intent": "data_query"
            },
            {
                "id": str(uuid4()),
                "transcript": "Schedule meeting",
                "status": "completed",
                "intent": "scheduling"
            }
        ])

        response = client.get(
            f"/api/v1/voice/commands/{founder_id}",
            params={"workspace_id": str(workspace_id)}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["commands"]) == 2

    def test_get_command_history_with_filters(self, client, mock_voice_service):
        """Test command history with filters"""
        founder_id = uuid4()

        mock_voice_service.get_command_history = AsyncMock(return_value=[
            MagicMock(
                id=uuid4(),
                status="completed",
                intent="data_query",
                transcript="Show revenue"
            )
        ])

        response = client.get(
            f"/api/v1/voice/commands/{founder_id}",
            params={
                "workspace_id": str(uuid4()),
                "status": "completed",
                "intent": "data_query",
                "limit": 10
            }
        )

        assert response.status_code == 200

    def test_get_command_history_error(self, client, mock_voice_service):
        """Test command history error"""
        mock_voice_service.get_command_history = AsyncMock(
            side_effect=Exception("Database error")
        )

        response = client.get(
            f"/api/v1/voice/commands/{uuid4()}",
            params={"workspace_id": str(uuid4())}
        )

        assert response.status_code == 500
        assert "Error fetching command history" in response.json()["detail"]

    def test_get_command_detail_success(self, client, mock_voice_service):
        """Test getting command details"""
        command_id = uuid4()
        workspace_id = uuid4()

        mock_voice_service.get_command_history = AsyncMock(return_value=[
            MagicMock(
                id=command_id,
                transcript="Show revenue",
                status="completed"
            )
        ])

        response = client.get(
            f"/api/v1/voice/commands/{command_id}/detail",
            params={"workspace_id": str(workspace_id)}
        )

        assert response.status_code == 200

    def test_get_command_detail_not_found(self, client, mock_voice_service):
        """Test getting non-existent command"""
        mock_voice_service.get_command_history = AsyncMock(return_value=[])

        response = client.get(
            f"/api/v1/voice/commands/{uuid4()}/detail",
            params={"workspace_id": str(uuid4())}
        )

        assert response.status_code == 404
        assert "Command not found" in response.json()["detail"]

    def test_get_command_detail_error(self, client, mock_voice_service):
        """Test get command detail error"""
        mock_voice_service.get_command_history = AsyncMock(
            side_effect=Exception("Database error")
        )

        response = client.get(
            f"/api/v1/voice/commands/{uuid4()}/detail",
            params={"workspace_id": str(uuid4())}
        )

        assert response.status_code == 500
        assert "Error fetching command" in response.json()["detail"]


# ============================================================================
# RECOMMENDATIONS API TESTS (28% coverage -> 80%+)
# ============================================================================

@pytest.fixture
def mock_recommendation_service():
    """Mock recommendation service"""
    with patch('app.api.v1.recommendations.get_recommendation_service') as mock:
        service = MagicMock()

        # Mock supabase
        mock_table = MagicMock()
        mock_query = MagicMock()

        mock_query.eq.return_value = mock_query
        mock_query.in_.return_value = mock_query
        mock_query.gte.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.range.return_value = mock_query
        mock_query.update.return_value = mock_query

        mock_table.select.return_value = mock_query
        mock_table.insert.return_value = mock_query
        service.supabase.table.return_value = mock_table

        # Mock service methods
        service.generate_recommendations = AsyncMock(return_value=[
            {
                "id": str(uuid4()),
                "recommendation_type": "growth",
                "priority": "high",
                "confidence_score": 0.85,
                "title": "Focus on customer retention"
            }
        ])

        mock.return_value = service
        yield service, mock_query


class TestRecommendationsAPI:
    """Comprehensive tests for Recommendations API"""

    def test_list_recommendations_success(self, client, mock_recommendation_service):
        """Test listing recommendations"""
        service, mock_query = mock_recommendation_service

        recs_data = [
            {
                "id": str(uuid4()),
                "workspace_id": str(uuid4()),
                "founder_id": str(uuid4()),
                "recommendation_type": "growth",
                "priority": "high",
                "status": "active",
                "confidence_score": 0.85,
                "created_at": datetime.utcnow().isoformat()
            }
        ]

        mock_query.execute.return_value = MagicMock(data=recs_data)

        response = client.get(
            "/api/v1/recommendations",
            params={"workspace_id": str(uuid4())}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["recommendations"]) == 1

    def test_list_recommendations_with_filters(self, client, mock_recommendation_service):
        """Test listing recommendations with filters"""
        service, mock_query = mock_recommendation_service
        mock_query.execute.return_value = MagicMock(data=[])

        response = client.get(
            "/api/v1/recommendations",
            params={
                "workspace_id": str(uuid4()),
                "founder_id": str(uuid4()),
                "recommendation_type": ["growth", "efficiency"],
                "status": ["active"],
                "priority": ["high"],
                "min_confidence": 0.8,
                "limit": 20
            }
        )

        assert response.status_code == 200

    def test_list_recommendations_error(self, client, mock_recommendation_service):
        """Test recommendations list error"""
        service, mock_query = mock_recommendation_service
        mock_query.execute.side_effect = Exception("Database error")

        response = client.get(
            "/api/v1/recommendations",
            params={"workspace_id": str(uuid4())}
        )

        assert response.status_code == 500
        assert "Error fetching recommendations" in response.json()["detail"]

    def test_generate_recommendations_success(self, client, mock_recommendation_service):
        """Test generating new recommendations"""
        service, mock_query = mock_recommendation_service

        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "time_range_days": 30,
            "min_confidence": 0.7
        }

        response = client.post("/api/v1/recommendations/generate", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert len(data["recommendations"]) == 1

    def test_generate_recommendations_with_focus_areas(self, client, mock_recommendation_service):
        """Test generating recommendations with focus areas"""
        service, mock_query = mock_recommendation_service

        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "time_range_days": 60,
            "focus_areas": ["growth", "efficiency"],
            "min_confidence": 0.8
        }

        response = client.post("/api/v1/recommendations/generate", json=request_data)

        assert response.status_code == 200
        service.generate_recommendations.assert_called_once()

    def test_generate_recommendations_error(self, client, mock_recommendation_service):
        """Test recommendation generation error"""
        service, mock_query = mock_recommendation_service
        service.generate_recommendations = AsyncMock(
            side_effect=Exception("Generation failed")
        )

        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4())
        }

        response = client.post("/api/v1/recommendations/generate", json=request_data)

        assert response.status_code == 500
        assert "Error generating recommendations" in response.json()["detail"]

    def test_submit_feedback_success(self, client, mock_recommendation_service):
        """Test submitting recommendation feedback"""
        service, mock_query = mock_recommendation_service

        recommendation_id = uuid4()
        mock_query.execute.return_value = MagicMock(data=[{"id": str(uuid4())}])

        request_data = {
            "was_helpful": True,
            "was_implemented": False,
            "rating": 5,
            "comments": "Great suggestion!"
        }

        response = client.put(
            f"/api/v1/recommendations/{recommendation_id}/feedback",
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_submit_feedback_implemented(self, client, mock_recommendation_service):
        """Test submitting feedback for implemented recommendation"""
        service, mock_query = mock_recommendation_service

        recommendation_id = uuid4()
        mock_query.execute.return_value = MagicMock(data=[{"id": str(uuid4())}])

        request_data = {
            "was_helpful": True,
            "was_implemented": True,
            "rating": 5
        }

        response = client.put(
            f"/api/v1/recommendations/{recommendation_id}/feedback",
            json=request_data
        )

        assert response.status_code == 200

    def test_submit_feedback_error(self, client, mock_recommendation_service):
        """Test feedback submission error"""
        service, mock_query = mock_recommendation_service
        mock_query.execute.side_effect = Exception("Database error")

        request_data = {
            "was_helpful": True,
            "rating": 3
        }

        response = client.put(
            f"/api/v1/recommendations/{uuid4()}/feedback",
            json=request_data
        )

        assert response.status_code == 500
        assert "Error submitting feedback" in response.json()["detail"]

    def test_get_impact_tracking_success(self, client, mock_recommendation_service):
        """Test getting recommendation impact"""
        service, mock_query = mock_recommendation_service

        recommendation_id = uuid4()
        mock_query.execute.return_value = MagicMock(data=[{
            "id": str(uuid4()),
            "recommendation_id": str(recommendation_id),
            "metric_improvements": {"revenue": 15.5},
            "measurement_date": datetime.utcnow().isoformat()
        }])

        response = client.get(f"/api/v1/recommendations/{recommendation_id}/impact")

        assert response.status_code == 200
        data = response.json()
        assert "metric_improvements" in data

    def test_get_impact_tracking_not_found(self, client, mock_recommendation_service):
        """Test getting impact when none exists"""
        service, mock_query = mock_recommendation_service
        mock_query.execute.return_value = MagicMock(data=[])

        response = client.get(f"/api/v1/recommendations/{uuid4()}/impact")

        assert response.status_code == 404
        assert "No impact data found" in response.json()["detail"]

    def test_get_impact_tracking_error(self, client, mock_recommendation_service):
        """Test impact tracking error"""
        service, mock_query = mock_recommendation_service
        mock_query.execute.side_effect = Exception("Database error")

        response = client.get(f"/api/v1/recommendations/{uuid4()}/impact")

        assert response.status_code == 500
        assert "Error fetching impact data" in response.json()["detail"]


# ============================================================================
# LOOM API TESTS (30% coverage -> 80%+)
# ============================================================================

@pytest.fixture
def mock_loom_service():
    """Mock Loom service"""
    with patch('app.api.v1.loom.get_loom_service') as mock:
        service = MagicMock()

        service.ingest_video = AsyncMock(return_value={
            "id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "loom_url": "https://loom.com/video/123",
            "status": "processing",
            "video_type": "update"
        })

        service.summarize_video = AsyncMock(return_value={
            "id": str(uuid4()),
            "status": "completed",
            "summary": {"key_points": ["Point 1", "Point 2"]}
        })

        service.get_video = AsyncMock(return_value={
            "id": str(uuid4()),
            "status": "completed"
        })

        service.list_videos = AsyncMock(return_value=[])

        mock.return_value = service
        yield service


class TestLoomAPI:
    """Comprehensive tests for Loom API"""

    def test_ingest_video_success(self, client, mock_loom_service):
        """Test ingesting Loom video successfully"""
        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "loom_url": "https://loom.com/video/abc123",
            "video_type": "update",
            "auto_summarize": True
        }

        response = client.post("/api/v1/loom/ingest", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["status"] == "processing"

    def test_ingest_video_without_auto_summarize(self, client, mock_loom_service):
        """Test ingesting video without automatic summarization"""
        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "loom_url": "https://loom.com/video/xyz789",
            "video_type": "demo",
            "auto_summarize": False
        }

        response = client.post("/api/v1/loom/ingest", json=request_data)

        assert response.status_code == 200

    def test_ingest_video_failure(self, client, mock_loom_service):
        """Test video ingestion failure"""
        mock_loom_service.ingest_video = AsyncMock(return_value=None)

        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "loom_url": "https://loom.com/video/invalid"
        }

        response = client.post("/api/v1/loom/ingest", json=request_data)

        assert response.status_code == 500
        assert "Failed to ingest video" in response.json()["detail"]

    def test_ingest_video_error(self, client, mock_loom_service):
        """Test video ingestion error"""
        mock_loom_service.ingest_video = AsyncMock(
            side_effect=Exception("Download failed")
        )

        request_data = {
            "workspace_id": str(uuid4()),
            "founder_id": str(uuid4()),
            "loom_url": "https://loom.com/video/123"
        }

        response = client.post("/api/v1/loom/ingest", json=request_data)

        assert response.status_code == 500
        assert "Error ingesting video" in response.json()["detail"]

    def test_summarize_video_success(self, client, mock_loom_service):
        """Test summarizing video successfully"""
        video_id = uuid4()

        request_data = {
            "include_action_items": True,
            "include_topics": True
        }

        response = client.post(f"/api/v1/loom/{video_id}/summarize", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    def test_summarize_video_failure(self, client, mock_loom_service):
        """Test video summarization failure"""
        mock_loom_service.summarize_video = AsyncMock(return_value=None)

        request_data = {
            "include_action_items": False
        }

        response = client.post(f"/api/v1/loom/{uuid4()}/summarize", json=request_data)

        assert response.status_code == 500
        assert "Failed to summarize video" in response.json()["detail"]

    def test_summarize_video_error(self, client, mock_loom_service):
        """Test video summarization error"""
        mock_loom_service.summarize_video = AsyncMock(
            side_effect=Exception("AI service unavailable")
        )

        request_data = {
            "include_action_items": True
        }

        response = client.post(f"/api/v1/loom/{uuid4()}/summarize", json=request_data)

        assert response.status_code == 500
        assert "Error summarizing video" in response.json()["detail"]

    def test_get_video_success(self, client, mock_loom_service):
        """Test getting video details"""
        video_id = uuid4()

        response = client.get(f"/api/v1/loom/{video_id}")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data

    def test_get_video_not_found(self, client, mock_loom_service):
        """Test getting non-existent video"""
        mock_loom_service.get_video = AsyncMock(return_value=None)

        response = client.get(f"/api/v1/loom/{uuid4()}")

        assert response.status_code == 404
        assert "Video not found" in response.json()["detail"]

    def test_get_video_error(self, client, mock_loom_service):
        """Test get video error"""
        mock_loom_service.get_video = AsyncMock(
            side_effect=Exception("Database error")
        )

        response = client.get(f"/api/v1/loom/{uuid4()}")

        assert response.status_code == 500
        assert "Error fetching video" in response.json()["detail"]

    def test_list_videos_all(self, client, mock_loom_service):
        """Test listing all videos"""
        mock_loom_service.list_videos = AsyncMock(return_value=[
            {
                "id": str(uuid4()),
                "status": "completed",
                "video_type": "update"
            },
            {
                "id": str(uuid4()),
                "status": "processing",
                "video_type": "demo"
            }
        ])

        response = client.get(
            "/api/v1/loom/list",
            params={"workspace_id": str(uuid4())}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["videos"]) == 2

    def test_list_videos_with_filters(self, client, mock_loom_service):
        """Test listing videos with filters"""
        mock_loom_service.list_videos = AsyncMock(return_value=[])

        response = client.get(
            "/api/v1/loom/list",
            params={
                "workspace_id": str(uuid4()),
                "founder_id": str(uuid4()),
                "video_type": "update",
                "status": "completed",
                "limit": 20
            }
        )

        assert response.status_code == 200

    def test_list_videos_error(self, client, mock_loom_service):
        """Test list videos error"""
        mock_loom_service.list_videos = AsyncMock(
            side_effect=Exception("Query failed")
        )

        response = client.get(
            "/api/v1/loom/list",
            params={"workspace_id": str(uuid4())}
        )

        assert response.status_code == 500
        assert "Error listing videos" in response.json()["detail"]
