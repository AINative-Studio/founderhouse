"""
Comprehensive Tests for KPI Sync Background Task
Tests KPI data synchronization from Granola
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from uuid import uuid4

from app.tasks.kpi_sync import KPISyncJob


@pytest.fixture
def mock_supabase():
    """Mock Supabase client"""
    mock = Mock()
    mock.table = Mock(return_value=mock)
    mock.select = Mock(return_value=mock)
    mock.eq = Mock(return_value=mock)
    mock.insert = Mock(return_value=mock)
    mock.execute = Mock(return_value=Mock(data=[]))
    return mock


@pytest.fixture
def mock_kpi_service():
    """Mock KPIIngestionService"""
    service = Mock()
    service.sync_kpis_from_granola = AsyncMock(
        return_value=Mock(
            status="success",
            metrics_synced=10,
            errors=[]
        )
    )
    return service


@pytest.fixture
def sync_job(mock_supabase, mock_kpi_service):
    """Create KPISyncJob with mocked dependencies"""
    with patch('app.tasks.kpi_sync.get_supabase_client', return_value=mock_supabase):
        with patch('app.tasks.kpi_sync.KPIIngestionService', return_value=mock_kpi_service):
            job = KPISyncJob()
            return job


@pytest.fixture
def mock_workspaces():
    """Mock workspace integrations"""
    return [
        {
            "workspace_id": str(uuid4()),
            "credentials": {
                "api_key": "test_key_1",
                "api_secret": "test_secret_1"
            }
        },
        {
            "workspace_id": str(uuid4()),
            "credentials": {
                "api_key": "test_key_2",
                "api_secret": "test_secret_2"
            }
        }
    ]


# ==================== Sync All Workspaces Tests ====================

@pytest.mark.asyncio
async def test_sync_all_workspaces_success(sync_job, mock_workspaces):
    """Test successful KPI sync for all workspaces"""
    sync_job.supabase.execute.return_value = Mock(data=mock_workspaces)

    await sync_job.sync_all_workspaces()

    # Verify service called for each workspace
    assert sync_job.kpi_service.sync_kpis_from_granola.call_count == 2

    # Verify correct parameters
    calls = sync_job.kpi_service.sync_kpis_from_granola.call_args_list
    for i, call_args in enumerate(calls):
        assert call_args[1]["workspace_id"] == mock_workspaces[i]["workspace_id"]
        assert call_args[1]["credentials"] == mock_workspaces[i]["credentials"]


@pytest.mark.asyncio
async def test_sync_all_workspaces_no_integrations(sync_job):
    """Test sync when no Granola integrations exist"""
    sync_job.supabase.execute.return_value = Mock(data=[])

    await sync_job.sync_all_workspaces()

    # Should not sync any workspaces
    sync_job.kpi_service.sync_kpis_from_granola.assert_not_called()


@pytest.mark.asyncio
async def test_sync_all_workspaces_partial_success(sync_job, mock_workspaces):
    """Test sync with some workspaces succeeding and others failing"""
    sync_job.supabase.execute.return_value = Mock(data=mock_workspaces)

    # First succeeds, second fails
    sync_job.kpi_service.sync_kpis_from_granola.side_effect = [
        Mock(status="success", metrics_synced=10, errors=[]),
        Exception("Sync failed")
    ]

    await sync_job.sync_all_workspaces()

    # Should attempt sync for both
    assert sync_job.kpi_service.sync_kpis_from_granola.call_count == 2


@pytest.mark.asyncio
async def test_sync_all_workspaces_with_sync_errors(sync_job, mock_workspaces):
    """Test handling sync that completes with errors"""
    sync_job.supabase.execute.return_value = Mock(data=mock_workspaces)

    # Sync completes but with errors
    sync_job.kpi_service.sync_kpis_from_granola.return_value = Mock(
        status="partial",
        metrics_synced=5,
        errors=["Failed to fetch metric A", "Failed to fetch metric B"]
    )

    await sync_job.sync_all_workspaces()

    # Should still log the event
    sync_job.kpi_service.sync_kpis_from_granola.assert_called()


@pytest.mark.asyncio
async def test_sync_all_workspaces_database_error(sync_job):
    """Test handling database error when fetching integrations"""
    sync_job.supabase.execute.side_effect = Exception("Database error")

    # Should not raise exception
    await sync_job.sync_all_workspaces()


# ==================== Event Logging Tests ====================

@pytest.mark.asyncio
async def test_log_sync_event_success(sync_job):
    """Test logging successful sync event"""
    workspace_id = uuid4()
    sync_status = Mock(
        status="success",
        metrics_synced=15,
        errors=[]
    )

    with patch('app.tasks.kpi_sync.datetime') as mock_datetime:
        mock_datetime.utcnow.return_value = datetime(2025, 11, 10, 12, 0, 0)

        await sync_job._log_sync_event(workspace_id, sync_status)

    # Verify event inserted
    sync_job.supabase.table.assert_called_with("events")
    sync_job.supabase.insert.assert_called_once()

    # Verify event data
    call_args = sync_job.supabase.insert.call_args[0][0]
    assert call_args["workspace_id"] == str(workspace_id)
    assert call_args["event_type"] == "kpi_sync"
    assert call_args["event_data"]["status"] == "success"
    assert call_args["event_data"]["metrics_synced"] == 15


@pytest.mark.asyncio
async def test_log_sync_event_with_errors(sync_job):
    """Test logging sync event with errors"""
    workspace_id = uuid4()
    sync_status = Mock(
        status="partial",
        metrics_synced=5,
        errors=["Error 1", "Error 2"]
    )

    await sync_job._log_sync_event(workspace_id, sync_status)

    # Verify errors logged
    call_args = sync_job.supabase.insert.call_args[0][0]
    assert len(call_args["event_data"]["errors"]) == 2


@pytest.mark.asyncio
async def test_log_sync_event_database_error(sync_job):
    """Test handling database error when logging event"""
    workspace_id = uuid4()
    sync_status = Mock(status="success", metrics_synced=10, errors=[])

    sync_job.supabase.execute.side_effect = Exception("Database error")

    # Should not raise exception
    await sync_job._log_sync_event(workspace_id, sync_status)


# ==================== Scheduler Control Tests ====================

def test_start_sync_job():
    """Test KPI sync job startup"""
    with patch('app.tasks.kpi_sync.get_supabase_client'), \
         patch('app.tasks.kpi_sync.KPIIngestionService'), \
         patch('app.tasks.kpi_sync.AsyncIOScheduler') as mock_scheduler_class:

        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler

        job = KPISyncJob()
        job.start()

        # Verify jobs added
        assert mock_scheduler.add_job.call_count == 2

        # Verify recurring job
        recurring_call = mock_scheduler.add_job.call_args_list[0]
        assert recurring_call[1]["id"] == "kpi_sync"

        # Verify startup job
        startup_call = mock_scheduler.add_job.call_args_list[1]
        assert startup_call[1]["id"] == "kpi_sync_startup"

        # Verify scheduler started
        mock_scheduler.start.assert_called_once()


def test_stop_sync_job():
    """Test KPI sync job shutdown"""
    with patch('app.tasks.kpi_sync.get_supabase_client'), \
         patch('app.tasks.kpi_sync.KPIIngestionService'), \
         patch('app.tasks.kpi_sync.AsyncIOScheduler') as mock_scheduler_class:

        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler

        job = KPISyncJob()
        job.stop()

        # Verify scheduler stopped
        mock_scheduler.shutdown.assert_called_once()


# ==================== Integration Tests ====================

@pytest.mark.asyncio
async def test_sync_multiple_workspaces_concurrent(sync_job):
    """Test syncing multiple workspaces"""
    workspaces = [
        {"workspace_id": str(uuid4()), "credentials": {"api_key": f"key_{i}"}}
        for i in range(5)
    ]
    sync_job.supabase.execute.return_value = Mock(data=workspaces)

    await sync_job.sync_all_workspaces()

    # All workspaces should be synced
    assert sync_job.kpi_service.sync_kpis_from_granola.call_count == 5


@pytest.mark.asyncio
async def test_sync_filters_active_granola_integrations(sync_job, mock_workspaces):
    """Test that sync only processes active Granola integrations"""
    sync_job.supabase.execute.return_value = Mock(data=mock_workspaces)

    await sync_job.sync_all_workspaces()

    # Verify query filters
    sync_job.supabase.eq.assert_any_call("platform", "granola")
    sync_job.supabase.eq.assert_any_call("status", "active")


# ==================== Edge Cases ====================

@pytest.mark.asyncio
async def test_sync_missing_credentials(sync_job):
    """Test handling workspace with missing credentials"""
    workspace = {
        "workspace_id": str(uuid4()),
        "credentials": None  # Missing credentials
    }
    sync_job.supabase.execute.return_value = Mock(data=[workspace])

    await sync_job.sync_all_workspaces()

    # Should still attempt sync (service will handle error)
    sync_job.kpi_service.sync_kpis_from_granola.assert_called_once()


@pytest.mark.asyncio
async def test_sync_invalid_workspace_id(sync_job):
    """Test handling invalid workspace ID"""
    workspace = {
        "workspace_id": "invalid-uuid",
        "credentials": {"api_key": "test"}
    }
    sync_job.supabase.execute.return_value = Mock(data=[workspace])

    # Should handle gracefully
    await sync_job.sync_all_workspaces()


@pytest.mark.asyncio
async def test_sync_zero_metrics_synced(sync_job, mock_workspaces):
    """Test handling sync that returns zero metrics"""
    sync_job.supabase.execute.return_value = Mock(data=mock_workspaces[:1])

    sync_job.kpi_service.sync_kpis_from_granola.return_value = Mock(
        status="success",
        metrics_synced=0,
        errors=[]
    )

    await sync_job.sync_all_workspaces()

    # Should still complete successfully
    sync_job.kpi_service.sync_kpis_from_granola.assert_called_once()
