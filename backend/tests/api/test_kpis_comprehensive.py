"""
Comprehensive API tests for KPI endpoints
Covers all endpoints with success and error scenarios
Target: 100% coverage of app/api/v1/kpis.py
"""
import pytest
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.models.kpi_metric import AggregationPeriod


@pytest.fixture
def client():
    """Test client"""
    return TestClient(app)


@pytest.fixture
def workspace_id():
    return uuid4()


@pytest.fixture
def metric_id():
    return uuid4()


# ==================== LIST KPIs TESTS ====================

def test_list_kpis_success(client, workspace_id):
    """Test successful KPI listing"""
    mock_kpis = [
        {
            "id": str(uuid4()),
            "workspace_id": str(workspace_id),
            "name": "mrr",
            "display_name": "Monthly Recurring Revenue",
            "category": "financial",
            "is_active": True
        },
        {
            "id": str(uuid4()),
            "workspace_id": str(workspace_id),
            "name": "cac",
            "display_name": "Customer Acquisition Cost",
            "category": "sales",
            "is_active": True
        }
    ]

    with patch('app.services.kpi_ingestion_service.get_supabase_client') as mock_get_client:
        mock_supabase = Mock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = Mock(
            data=mock_kpis
        )
        mock_get_client.return_value = mock_supabase

        response = client.get(
            "/api/v1/kpis",
            params={"workspace_id": str(workspace_id)}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


def test_list_kpis_with_category_filter(client, workspace_id):
    """Test listing KPIs filtered by category"""
    mock_kpis = [
        {
            "id": str(uuid4()),
            "workspace_id": str(workspace_id),
            "name": "mrr",
            "display_name": "MRR",
            "category": "financial",
            "is_active": True
        }
    ]

    with patch('app.services.kpi_ingestion_service.get_supabase_client') as mock_get_client:
        mock_supabase = Mock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = Mock(
            data=mock_kpis
        )
        mock_get_client.return_value = mock_supabase

        response = client.get(
            "/api/v1/kpis",
            params={
                "workspace_id": str(workspace_id),
                "category": "financial"
            }
        )

        assert response.status_code == 200


def test_list_kpis_inactive(client, workspace_id):
    """Test listing inactive KPIs"""
    with patch('app.services.kpi_ingestion_service.get_supabase_client') as mock_get_client:
        mock_supabase = Mock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = Mock(
            data=[]
        )
        mock_get_client.return_value = mock_supabase

        response = client.get(
            "/api/v1/kpis",
            params={
                "workspace_id": str(workspace_id),
                "is_active": False
            }
        )

        assert response.status_code == 200


# ==================== GET METRIC HISTORY TESTS ====================

@pytest.mark.asyncio
async def test_get_metric_history_success(client, workspace_id, metric_id):
    """Test successful metric history retrieval"""
    mock_metric = {
        "id": str(metric_id),
        "workspace_id": str(workspace_id),
        "name": "mrr",
        "display_name": "MRR",
        "category": "financial",
        "unit": "USD"
    }

    mock_data_points = [
        {
            "id": str(uuid4()),
            "value": 10000 + i * 100,
            "timestamp": (datetime.utcnow() - timedelta(days=30-i)).isoformat()
        }
        for i in range(30)
    ]

    with patch('app.services.kpi_ingestion_service.get_supabase_client') as mock_get_client:
        mock_supabase = Mock()

        # Mock metric retrieval
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data=mock_metric
        )

        mock_get_client.return_value = mock_supabase

        with patch('app.services.kpi_ingestion_service.KPIIngestionService.get_metric_history', new_callable=AsyncMock) as mock_history:
            from app.models.kpi_metric import KPIDataPoint
            mock_history.return_value = [
                KPIDataPoint(
                    id=uuid4(),
                    metric_id=metric_id,
                    workspace_id=workspace_id,
                    value=dp["value"],
                    timestamp=datetime.fromisoformat(dp["timestamp"])
                )
                for dp in mock_data_points
            ]

            response = client.get(
                f"/api/v1/kpis/{metric_id}/history",
                params={"workspace_id": str(workspace_id)}
            )

            assert response.status_code == 200
            data = response.json()
            assert "data_points" in data
            assert "statistics" in data
            assert "trend" in data


def test_get_metric_history_not_found(client, workspace_id, metric_id):
    """Test metric history for non-existent metric"""
    with patch('app.services.kpi_ingestion_service.get_supabase_client') as mock_get_client:
        mock_supabase = Mock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data=None
        )
        mock_get_client.return_value = mock_supabase

        response = client.get(
            f"/api/v1/kpis/{metric_id}/history",
            params={"workspace_id": str(workspace_id)}
        )

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_metric_history_with_date_range(client, workspace_id, metric_id):
    """Test metric history with date range"""
    mock_metric = {
        "id": str(metric_id),
        "workspace_id": str(workspace_id),
        "name": "cac",
        "display_name": "CAC",
        "category": "sales",
        "unit": "USD"
    }

    with patch('app.services.kpi_ingestion_service.get_supabase_client') as mock_get_client:
        mock_supabase = Mock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data=mock_metric
        )
        mock_get_client.return_value = mock_supabase

        with patch('app.services.kpi_ingestion_service.KPIIngestionService.get_metric_history', new_callable=AsyncMock) as mock_history:
            mock_history.return_value = []

            start_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
            end_date = datetime.utcnow().isoformat()

            response = client.get(
                f"/api/v1/kpis/{metric_id}/history",
                params={
                    "workspace_id": str(workspace_id),
                    "start_date": start_date,
                    "end_date": end_date,
                    "period": "daily"
                }
            )

            assert response.status_code == 200


# ==================== GET CURRENT SNAPSHOT TESTS ====================

@pytest.mark.asyncio
async def test_get_current_snapshot_success(client, workspace_id):
    """Test successful KPI snapshot retrieval"""
    from app.models.kpi_metric import KPISnapshot

    mock_snapshot = KPISnapshot(
        workspace_id=workspace_id,
        timestamp=datetime.utcnow(),
        metrics={
            "MRR": 50000,
            "CAC": 250,
            "Churn Rate": 0.05
        }
    )

    with patch('app.services.kpi_ingestion_service.get_supabase_client') as mock_get_client:
        mock_get_client.return_value = Mock()

        with patch('app.services.kpi_ingestion_service.KPIIngestionService.get_current_snapshot', new_callable=AsyncMock) as mock_snapshot_func:
            mock_snapshot_func.return_value = mock_snapshot

            response = client.get(
                "/api/v1/kpis/current",
                params={"workspace_id": str(workspace_id)}
            )

            assert response.status_code == 200
            data = response.json()
            assert "metrics" in data


# ==================== TRIGGER SYNC TESTS ====================

@pytest.mark.asyncio
async def test_trigger_manual_sync_success(client, workspace_id):
    """Test successful manual sync trigger"""
    from app.models.kpi_metric import SyncStatus

    mock_integration = {
        "workspace_id": str(workspace_id),
        "platform": "granola",
        "credentials": {"api_key": "test_key"}
    }

    mock_sync_status = SyncStatus(
        workspace_id=workspace_id,
        status="completed",
        metrics_synced=5,
        errors=[],
        last_sync_at=datetime.utcnow()
    )

    with patch('app.services.kpi_ingestion_service.get_supabase_client') as mock_get_client:
        mock_supabase = Mock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data=mock_integration
        )
        mock_get_client.return_value = mock_supabase

        with patch('app.services.kpi_ingestion_service.KPIIngestionService.sync_kpis_from_granola', new_callable=AsyncMock) as mock_sync:
            mock_sync.return_value = mock_sync_status

            response = client.post(
                "/api/v1/kpis/sync",
                params={"workspace_id": str(workspace_id)}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["metrics_synced"] == 5


def test_trigger_manual_sync_no_integration(client, workspace_id):
    """Test sync trigger when integration not found"""
    with patch('app.services.kpi_ingestion_service.get_supabase_client') as mock_get_client:
        mock_supabase = Mock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data=None
        )
        mock_get_client.return_value = mock_supabase

        response = client.post(
            "/api/v1/kpis/sync",
            params={"workspace_id": str(workspace_id)}
        )

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_trigger_manual_sync_with_specific_metrics(client, workspace_id):
    """Test sync trigger with specific metrics"""
    mock_integration = {
        "credentials": {"api_key": "test_key"}
    }

    from app.models.kpi_metric import SyncStatus
    mock_sync_status = SyncStatus(
        workspace_id=workspace_id,
        status="completed",
        metrics_synced=2,
        errors=[],
        last_sync_at=datetime.utcnow()
    )

    with patch('app.services.kpi_ingestion_service.get_supabase_client') as mock_get_client:
        mock_supabase = Mock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data=mock_integration
        )
        mock_get_client.return_value = mock_supabase

        with patch('app.services.kpi_ingestion_service.KPIIngestionService.sync_kpis_from_granola', new_callable=AsyncMock) as mock_sync:
            mock_sync.return_value = mock_sync_status

            response = client.post(
                "/api/v1/kpis/sync",
                params={
                    "workspace_id": str(workspace_id),
                    "metrics_to_sync": ["mrr", "cac"]
                }
            )

            assert response.status_code == 200


# ==================== GET SYNC STATUS TESTS ====================

def test_get_sync_status_success(client, workspace_id):
    """Test successful sync status retrieval"""
    mock_status = {
        "id": str(uuid4()),
        "workspace_id": str(workspace_id),
        "status": "completed",
        "metrics_synced": 5,
        "errors": [],
        "last_sync_at": datetime.utcnow().isoformat()
    }

    with patch('app.services.kpi_ingestion_service.get_supabase_client') as mock_get_client:
        mock_supabase = Mock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = Mock(
            data=[mock_status]
        )
        mock_get_client.return_value = mock_supabase

        response = client.get(
            "/api/v1/kpis/sync-status",
            params={"workspace_id": str(workspace_id)}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"


def test_get_sync_status_not_found(client, workspace_id):
    """Test sync status when no status found"""
    with patch('app.services.kpi_ingestion_service.get_supabase_client') as mock_get_client:
        mock_supabase = Mock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = Mock(
            data=[]
        )
        mock_get_client.return_value = mock_supabase

        response = client.get(
            "/api/v1/kpis/sync-status",
            params={"workspace_id": str(workspace_id)}
        )

        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
