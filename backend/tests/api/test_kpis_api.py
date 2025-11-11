"""
Comprehensive tests for KPIs API endpoints

Tests all KPI-related endpoints with proper mocking.
Coverage target: 74 statements, 0% -> 80%+
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def mock_kpi_service():
    """Mock KPI service"""
    with patch('app.api.v1.kpis.get_kpi_service') as mock:
        service = MagicMock()
        service.supabase = MagicMock()
        
        # Configure chained methods
        service.supabase.table.return_value = service.supabase
        service.supabase.select.return_value = service.supabase
        service.supabase.eq.return_value = service.supabase
        service.supabase.execute.return_value = MagicMock(data=[])
        service.supabase.single.return_value = service.supabase
        service.supabase.order.return_value = service.supabase
        service.supabase.limit.return_value = service.supabase
        
        service.get_metric_history = AsyncMock(return_value=[])
        service.get_current_snapshot = AsyncMock(return_value={})
        service.sync_kpis_from_granola = AsyncMock(return_value={})
        
        mock.return_value = service
        yield service


@pytest.fixture
def sample_kpi_metric():
    """Sample KPI metric data"""
    return {
        "id": str(uuid4()),
        "workspace_id": str(uuid4()),
        "name": "mrr",
        "display_name": "Monthly Recurring Revenue",
        "category": "revenue",
        "unit": "currency",
        "current_value": 50000.0,
        "is_active": True,
        "created_at": datetime.utcnow().isoformat()
    }


class TestListKPIs:
    """Tests for listing KPIs"""
    
    def test_list_kpis_success(self, client, mock_kpi_service, sample_kpi_metric):
        """Test successful KPI listing"""
        workspace_id = uuid4()
        
        mock_kpi_service.supabase.execute.return_value = MagicMock(
            data=[sample_kpi_metric, sample_kpi_metric]
        )
        
        response = client.get(
            "/kpis",
            params={"workspace_id": str(workspace_id)}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
    def test_list_kpis_with_category_filter(self, client, mock_kpi_service, sample_kpi_metric):
        """Test KPI listing with category filter"""
        workspace_id = uuid4()
        
        mock_kpi_service.supabase.execute.return_value = MagicMock(
            data=[sample_kpi_metric]
        )
        
        response = client.get(
            "/kpis",
            params={
                "workspace_id": str(workspace_id),
                "category": "revenue"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["category"] == "revenue"
        
    def test_list_kpis_active_only(self, client, mock_kpi_service, sample_kpi_metric):
        """Test listing only active KPIs"""
        workspace_id = uuid4()
        
        mock_kpi_service.supabase.execute.return_value = MagicMock(
            data=[sample_kpi_metric]
        )
        
        response = client.get(
            "/kpis",
            params={
                "workspace_id": str(workspace_id),
                "is_active": True
            }
        )
        
        assert response.status_code == 200
        
    def test_list_kpis_error(self, client, mock_kpi_service):
        """Test KPI listing with error"""
        workspace_id = uuid4()
        
        mock_kpi_service.supabase.execute.side_effect = Exception("Database error")
        
        response = client.get(
            "/kpis",
            params={"workspace_id": str(workspace_id)}
        )
        
        assert response.status_code == 500


class TestGetMetricHistory:
    """Tests for getting metric history"""
    
    def test_get_metric_history_success(self, client, mock_kpi_service, sample_kpi_metric):
        """Test successful metric history retrieval"""
        metric_id = uuid4()
        workspace_id = uuid4()
        
        mock_kpi_service.supabase.single.return_value.execute.return_value = MagicMock(
            data=sample_kpi_metric
        )
        
        data_points = [
            MagicMock(value=45000.0, timestamp=datetime.utcnow() - timedelta(days=30)),
            MagicMock(value=48000.0, timestamp=datetime.utcnow() - timedelta(days=15)),
            MagicMock(value=50000.0, timestamp=datetime.utcnow())
        ]
        
        mock_kpi_service.get_metric_history = AsyncMock(return_value=data_points)
        
        response = client.get(
            f"/kpis/{metric_id}/history",
            params={"workspace_id": str(workspace_id)}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "metric_id" in data
        assert "data_points" in data
        assert "statistics" in data
        assert "trend" in data
        
    def test_get_metric_history_with_date_range(self, client, mock_kpi_service, sample_kpi_metric):
        """Test metric history with date range"""
        metric_id = uuid4()
        workspace_id = uuid4()
        
        mock_kpi_service.supabase.single.return_value.execute.return_value = MagicMock(
            data=sample_kpi_metric
        )
        
        mock_kpi_service.get_metric_history = AsyncMock(return_value=[])
        
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        response = client.get(
            f"/kpis/{metric_id}/history",
            params={
                "workspace_id": str(workspace_id),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        )
        
        assert response.status_code == 200
        
    def test_get_metric_history_with_period(self, client, mock_kpi_service, sample_kpi_metric):
        """Test metric history with aggregation period"""
        metric_id = uuid4()
        workspace_id = uuid4()
        
        mock_kpi_service.supabase.single.return_value.execute.return_value = MagicMock(
            data=sample_kpi_metric
        )
        
        mock_kpi_service.get_metric_history = AsyncMock(return_value=[])
        
        response = client.get(
            f"/kpis/{metric_id}/history",
            params={
                "workspace_id": str(workspace_id),
                "period": "weekly"
            }
        )
        
        assert response.status_code == 200
        
    def test_get_metric_history_not_found(self, client, mock_kpi_service):
        """Test metric history when metric not found"""
        metric_id = uuid4()
        workspace_id = uuid4()
        
        mock_kpi_service.supabase.single.return_value.execute.return_value = MagicMock(
            data=None
        )
        
        response = client.get(
            f"/kpis/{metric_id}/history",
            params={"workspace_id": str(workspace_id)}
        )
        
        assert response.status_code == 404
        
    def test_get_metric_history_with_limit(self, client, mock_kpi_service, sample_kpi_metric):
        """Test metric history with limit parameter"""
        metric_id = uuid4()
        workspace_id = uuid4()
        
        mock_kpi_service.supabase.single.return_value.execute.return_value = MagicMock(
            data=sample_kpi_metric
        )
        
        mock_kpi_service.get_metric_history = AsyncMock(return_value=[])
        
        response = client.get(
            f"/kpis/{metric_id}/history",
            params={
                "workspace_id": str(workspace_id),
                "limit": 50
            }
        )
        
        assert response.status_code == 200


class TestGetCurrentSnapshot:
    """Tests for current KPI snapshot"""
    
    def test_get_current_snapshot_success(self, client, mock_kpi_service):
        """Test successful snapshot retrieval"""
        workspace_id = uuid4()
        
        snapshot_data = {
            "workspace_id": str(workspace_id),
            "snapshot_date": datetime.utcnow().isoformat(),
            "metrics": {
                "mrr": 50000.0,
                "arr": 600000.0,
                "active_users": 1250
            }
        }
        
        mock_kpi_service.get_current_snapshot = AsyncMock(return_value=snapshot_data)
        
        response = client.get(
            "/kpis/current",
            params={"workspace_id": str(workspace_id)}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        
    def test_get_current_snapshot_error(self, client, mock_kpi_service):
        """Test snapshot retrieval with error"""
        workspace_id = uuid4()
        
        mock_kpi_service.get_current_snapshot = AsyncMock(
            side_effect=Exception("Service error")
        )
        
        response = client.get(
            "/kpis/current",
            params={"workspace_id": str(workspace_id)}
        )
        
        assert response.status_code == 500


class TestTriggerManualSync:
    """Tests for manual KPI sync"""
    
    def test_trigger_sync_success(self, client, mock_kpi_service):
        """Test successful manual sync"""
        workspace_id = uuid4()
        
        sync_status = MagicMock()
        sync_status.status = "completed"
        sync_status.metrics_synced = 10
        sync_status.errors = []
        sync_status.last_sync_at = datetime.utcnow()
        
        mock_kpi_service.supabase.single.return_value.execute.return_value = MagicMock(
            data={"credentials": {"api_key": "test_key"}}
        )
        
        mock_kpi_service.sync_kpis_from_granola = AsyncMock(return_value=sync_status)
        
        response = client.post(
            "/kpis/sync",
            params={"workspace_id": str(workspace_id)}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["metrics_synced"] == 10
        
    def test_trigger_sync_with_specific_metrics(self, client, mock_kpi_service):
        """Test sync with specific metrics"""
        workspace_id = uuid4()
        
        sync_status = MagicMock()
        sync_status.status = "completed"
        sync_status.metrics_synced = 3
        sync_status.errors = []
        sync_status.last_sync_at = datetime.utcnow()
        
        mock_kpi_service.supabase.single.return_value.execute.return_value = MagicMock(
            data={"credentials": {"api_key": "test_key"}}
        )
        
        mock_kpi_service.sync_kpis_from_granola = AsyncMock(return_value=sync_status)
        
        response = client.post(
            "/kpis/sync",
            params={
                "workspace_id": str(workspace_id),
                "metrics_to_sync": ["mrr", "arr", "active_users"]
            }
        )
        
        assert response.status_code == 200
        
    def test_trigger_sync_no_integration(self, client, mock_kpi_service):
        """Test sync without Granola integration"""
        workspace_id = uuid4()
        
        mock_kpi_service.supabase.single.return_value.execute.return_value = MagicMock(
            data=None
        )
        
        response = client.post(
            "/kpis/sync",
            params={"workspace_id": str(workspace_id)}
        )
        
        assert response.status_code == 404
        assert "integration not found" in response.json()["detail"].lower()
        
    def test_trigger_sync_error(self, client, mock_kpi_service):
        """Test sync with service error"""
        workspace_id = uuid4()
        
        mock_kpi_service.supabase.single.return_value.execute.return_value = MagicMock(
            data={"credentials": {"api_key": "test_key"}}
        )
        
        mock_kpi_service.sync_kpis_from_granola = AsyncMock(
            side_effect=Exception("Granola API error")
        )
        
        response = client.post(
            "/kpis/sync",
            params={"workspace_id": str(workspace_id)}
        )
        
        assert response.status_code == 500


class TestGetSyncStatus:
    """Tests for sync status endpoint"""
    
    def test_get_sync_status_success(self, client, mock_kpi_service):
        """Test successful sync status retrieval"""
        workspace_id = uuid4()
        
        sync_status_data = {
            "workspace_id": str(workspace_id),
            "status": "completed",
            "metrics_synced": 10,
            "errors": [],
            "last_sync_at": datetime.utcnow().isoformat()
        }
        
        mock_kpi_service.supabase.execute.return_value = MagicMock(
            data=[sync_status_data]
        )
        
        response = client.get(
            "/kpis/sync-status",
            params={"workspace_id": str(workspace_id)}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["metrics_synced"] == 10
        
    def test_get_sync_status_not_found(self, client, mock_kpi_service):
        """Test sync status when no sync exists"""
        workspace_id = uuid4()
        
        mock_kpi_service.supabase.execute.return_value = MagicMock(data=[])
        
        response = client.get(
            "/kpis/sync-status",
            params={"workspace_id": str(workspace_id)}
        )
        
        assert response.status_code == 404
        
    def test_get_sync_status_error(self, client, mock_kpi_service):
        """Test sync status retrieval with error"""
        workspace_id = uuid4()
        
        mock_kpi_service.supabase.execute.side_effect = Exception("Database error")
        
        response = client.get(
            "/kpis/sync-status",
            params={"workspace_id": str(workspace_id)}
        )
        
        assert response.status_code == 500


# Summary comment
"""
Test Coverage Summary:
- List KPIs: 4 tests (success, filter by category, active only, error)
- Get metric history: 5 tests (success, date range, period, not found, limit)
- Get current snapshot: 2 tests (success, error)
- Trigger manual sync: 4 tests (success, specific metrics, no integration, error)
- Get sync status: 3 tests (success, not found, error)

Total: 18 tests covering kpis.py API (74 statements)
Expected coverage improvement: 0% -> 80%+ (~1% overall coverage gain)
"""
