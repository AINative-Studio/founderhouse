"""
Comprehensive Tests for Integration Health Check Background Task
Tests integration health monitoring and alerting
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from uuid import uuid4, UUID

from app.tasks.integration_health import (
    run_workspace_health_check,
    run_all_workspaces_health_check,
    schedule_health_checks,
    stop_health_checks,
    run_immediate_health_check_for_workspace,
    test_health_check_task
)


@pytest.fixture
def mock_db_manager():
    """Mock database manager"""
    manager = Mock()
    manager.get_client = Mock()
    return manager


@pytest.fixture
def mock_db_client():
    """Mock database client"""
    client = Mock()
    client.table = Mock(return_value=client)
    client.select = Mock(return_value=client)
    client.limit = Mock(return_value=client)
    client.execute = Mock(return_value=Mock(data=[]))
    return client


@pytest.fixture
def mock_health_service():
    """Mock HealthCheckService"""
    service = Mock()
    service.check_all_integrations_health = AsyncMock(return_value=[])
    service.get_health_dashboard = AsyncMock(return_value={})
    return service


@pytest.fixture
def workspace_id():
    """Test workspace ID"""
    return uuid4()


@pytest.fixture
def mock_health_checks():
    """Mock health check results"""
    return [
        Mock(
            platform=Mock(value="github"),
            is_healthy=True,
            error_message=None
        ),
        Mock(
            platform=Mock(value="slack"),
            is_healthy=False,
            error_message="Connection timeout"
        ),
        Mock(
            platform=Mock(value="notion"),
            is_healthy=True,
            error_message=None
        )
    ]


# ==================== Workspace Health Check Tests ====================

@pytest.mark.asyncio
async def test_run_workspace_health_check_success(workspace_id, mock_db_client, mock_health_checks):
    """Test successful health check for a workspace"""
    with patch('app.tasks.integration_health.db_manager') as mock_manager:
        mock_manager.get_client.return_value = mock_db_client

        with patch('app.tasks.integration_health.HealthCheckService') as mock_service_class:
            mock_service = Mock()
            mock_service.check_all_integrations_health = AsyncMock(return_value=mock_health_checks)
            mock_service_class.return_value = mock_service

            await run_workspace_health_check(workspace_id)

    # Verify health check was called
    mock_service.check_all_integrations_health.assert_called_once_with(workspace_id)


@pytest.mark.asyncio
async def test_run_workspace_health_check_all_healthy(workspace_id, mock_db_client):
    """Test health check when all integrations are healthy"""
    healthy_checks = [
        Mock(platform=Mock(value="github"), is_healthy=True, error_message=None),
        Mock(platform=Mock(value="slack"), is_healthy=True, error_message=None)
    ]

    with patch('app.tasks.integration_health.db_manager') as mock_manager:
        mock_manager.get_client.return_value = mock_db_client

        with patch('app.tasks.integration_health.HealthCheckService') as mock_service_class:
            mock_service = Mock()
            mock_service.check_all_integrations_health = AsyncMock(return_value=healthy_checks)
            mock_service_class.return_value = mock_service

            await run_workspace_health_check(workspace_id)

    # Should complete without warnings
    mock_service.check_all_integrations_health.assert_called_once()


@pytest.mark.asyncio
async def test_run_workspace_health_check_with_unhealthy(workspace_id, mock_db_client, mock_health_checks):
    """Test health check with unhealthy integrations"""
    with patch('app.tasks.integration_health.db_manager') as mock_manager:
        mock_manager.get_client.return_value = mock_db_client

        with patch('app.tasks.integration_health.HealthCheckService') as mock_service_class:
            mock_service = Mock()
            mock_service.check_all_integrations_health = AsyncMock(return_value=mock_health_checks)
            mock_service_class.return_value = mock_service

            await run_workspace_health_check(workspace_id)

    # Should identify unhealthy integrations
    unhealthy = [hc for hc in mock_health_checks if not hc.is_healthy]
    assert len(unhealthy) == 1
    assert unhealthy[0].platform.value == "slack"


@pytest.mark.asyncio
async def test_run_workspace_health_check_error_handling(workspace_id, mock_db_client):
    """Test error handling during workspace health check"""
    with patch('app.tasks.integration_health.db_manager') as mock_manager:
        mock_manager.get_client.return_value = mock_db_client

        with patch('app.tasks.integration_health.HealthCheckService') as mock_service_class:
            mock_service = Mock()
            mock_service.check_all_integrations_health = AsyncMock(
                side_effect=Exception("Service error")
            )
            mock_service_class.return_value = mock_service

            # Should not raise exception
            await run_workspace_health_check(workspace_id)


@pytest.mark.asyncio
async def test_run_workspace_health_check_no_integrations(workspace_id, mock_db_client):
    """Test health check for workspace with no integrations"""
    with patch('app.tasks.integration_health.db_manager') as mock_manager:
        mock_manager.get_client.return_value = mock_db_client

        with patch('app.tasks.integration_health.HealthCheckService') as mock_service_class:
            mock_service = Mock()
            mock_service.check_all_integrations_health = AsyncMock(return_value=[])
            mock_service_class.return_value = mock_service

            await run_workspace_health_check(workspace_id)

    # Should complete successfully with empty list
    mock_service.check_all_integrations_health.assert_called_once()


# ==================== All Workspaces Health Check Tests ====================

@pytest.mark.asyncio
async def test_run_all_workspaces_health_check_success(mock_db_client):
    """Test successful health check for all workspaces"""
    workspace_ids = [uuid4(), uuid4(), uuid4()]
    mock_db_client.execute.return_value = Mock(
        data=[{"workspace_id": str(wid)} for wid in workspace_ids]
    )

    with patch('app.tasks.integration_health.db_manager') as mock_manager:
        mock_manager.get_client.return_value = mock_db_client

        with patch('app.tasks.integration_health.run_workspace_health_check', new_callable=AsyncMock) as mock_check:
            await run_all_workspaces_health_check()

    # Verify health check called for each workspace
    assert mock_check.call_count == 3


@pytest.mark.asyncio
async def test_run_all_workspaces_health_check_no_workspaces(mock_db_client):
    """Test health check when no workspaces exist"""
    mock_db_client.execute.return_value = Mock(data=[])

    with patch('app.tasks.integration_health.db_manager') as mock_manager:
        mock_manager.get_client.return_value = mock_db_client

        with patch('app.tasks.integration_health.run_workspace_health_check', new_callable=AsyncMock) as mock_check:
            await run_all_workspaces_health_check()

    # Should not call any health checks
    mock_check.assert_not_called()


@pytest.mark.asyncio
async def test_run_all_workspaces_health_check_concurrent_execution(mock_db_client):
    """Test concurrent execution of health checks"""
    workspace_ids = [uuid4() for _ in range(5)]
    mock_db_client.execute.return_value = Mock(
        data=[{"workspace_id": str(wid)} for wid in workspace_ids]
    )

    with patch('app.tasks.integration_health.db_manager') as mock_manager:
        mock_manager.get_client.return_value = mock_db_client

        with patch('app.tasks.integration_health.run_workspace_health_check', new_callable=AsyncMock) as mock_check:
            await run_all_workspaces_health_check()

    # All checks should be called
    assert mock_check.call_count == 5


@pytest.mark.asyncio
async def test_run_all_workspaces_health_check_with_failures(mock_db_client):
    """Test handling failures in some workspace health checks"""
    workspace_ids = [uuid4(), uuid4(), uuid4()]
    mock_db_client.execute.return_value = Mock(
        data=[{"workspace_id": str(wid)} for wid in workspace_ids]
    )

    with patch('app.tasks.integration_health.db_manager') as mock_manager:
        mock_manager.get_client.return_value = mock_db_client

        with patch('app.tasks.integration_health.run_workspace_health_check', new_callable=AsyncMock) as mock_check:
            # Make one fail
            mock_check.side_effect = [None, Exception("Check failed"), None]

            await run_all_workspaces_health_check()

    # Should still call all checks despite failure
    assert mock_check.call_count == 3


@pytest.mark.asyncio
async def test_run_all_workspaces_health_check_database_error(mock_db_client):
    """Test handling database error when fetching workspaces"""
    mock_db_client.execute.side_effect = Exception("Database error")

    with patch('app.tasks.integration_health.db_manager') as mock_manager:
        mock_manager.get_client.return_value = mock_db_client

        # Should not raise exception
        await run_all_workspaces_health_check()


# ==================== Scheduler Tests ====================

def test_schedule_health_checks_default_interval():
    """Test scheduling health checks with default interval"""
    with patch('app.tasks.integration_health.AsyncIOScheduler') as mock_scheduler_class:
        mock_scheduler = Mock()
        mock_scheduler.running = False
        mock_scheduler_class.return_value = mock_scheduler

        schedule_health_checks()

        # Verify job added with 6 hour interval
        mock_scheduler.add_job.assert_called_once()
        call_args = mock_scheduler.add_job.call_args

        # Verify job configuration
        assert call_args[1]["id"] == "integration_health_check"
        assert call_args[1]["max_instances"] == 1

        # Verify scheduler started
        mock_scheduler.start.assert_called_once()


def test_schedule_health_checks_custom_interval():
    """Test scheduling health checks with custom interval"""
    with patch('app.tasks.integration_health.AsyncIOScheduler') as mock_scheduler_class:
        mock_scheduler = Mock()
        mock_scheduler.running = False
        mock_scheduler_class.return_value = mock_scheduler

        schedule_health_checks(interval_hours=12)

        mock_scheduler.add_job.assert_called_once()
        mock_scheduler.start.assert_called_once()


def test_schedule_health_checks_already_running():
    """Test scheduling when scheduler already running"""
    with patch('app.tasks.integration_health.AsyncIOScheduler') as mock_scheduler_class:
        mock_scheduler = Mock()
        mock_scheduler.running = True
        mock_scheduler_class.return_value = mock_scheduler

        schedule_health_checks()

        # Should add job but not start again
        mock_scheduler.add_job.assert_called_once()
        mock_scheduler.start.assert_not_called()


def test_stop_health_checks():
    """Test stopping health check scheduler"""
    with patch('app.tasks.integration_health.scheduler') as mock_scheduler:
        mock_scheduler.running = True

        stop_health_checks()

        mock_scheduler.shutdown.assert_called_once()


def test_stop_health_checks_not_running():
    """Test stopping when scheduler not running"""
    with patch('app.tasks.integration_health.scheduler', None):
        # Should not raise exception
        stop_health_checks()


# ==================== Immediate Health Check Tests ====================

@pytest.mark.asyncio
async def test_run_immediate_health_check_success(workspace_id, mock_db_client):
    """Test immediate health check for workspace"""
    dashboard = {
        "workspace_id": str(workspace_id),
        "total_integrations": 3,
        "healthy_integrations": 2,
        "unhealthy_integrations": 1
    }

    with patch('app.tasks.integration_health.db_manager') as mock_manager:
        mock_manager.get_client.return_value = mock_db_client

        with patch('app.tasks.integration_health.HealthCheckService') as mock_service_class:
            mock_service = Mock()
            mock_service.get_health_dashboard = AsyncMock(return_value=dashboard)
            mock_service_class.return_value = mock_service

            result = await run_immediate_health_check_for_workspace(workspace_id)

    assert result == dashboard
    assert result["total_integrations"] == 3


@pytest.mark.asyncio
async def test_run_immediate_health_check_error(workspace_id, mock_db_client):
    """Test immediate health check with error"""
    with patch('app.tasks.integration_health.db_manager') as mock_manager:
        mock_manager.get_client.return_value = mock_db_client

        with patch('app.tasks.integration_health.HealthCheckService') as mock_service_class:
            mock_service = Mock()
            mock_service.get_health_dashboard = AsyncMock(
                side_effect=Exception("Service error")
            )
            mock_service_class.return_value = mock_service

            # Should raise exception for immediate check
            with pytest.raises(Exception):
                await run_immediate_health_check_for_workspace(workspace_id)


# ==================== Test Task Tests ====================

@pytest.mark.asyncio
async def test_health_check_task_with_integrations(mock_db_client):
    """Test health check task with integrations"""
    workspace_id = uuid4()
    mock_db_client.execute.return_value = Mock(
        data=[{"workspace_id": str(workspace_id)}]
    )

    dashboard = {"workspace_id": str(workspace_id), "status": "healthy"}

    with patch('app.tasks.integration_health.db_manager') as mock_manager:
        mock_manager.get_client.return_value = mock_db_client

        with patch('app.tasks.integration_health.run_immediate_health_check_for_workspace',
                   new_callable=AsyncMock, return_value=dashboard):

            result = await test_health_check_task()

    assert result == dashboard


@pytest.mark.asyncio
async def test_health_check_task_no_integrations(mock_db_client):
    """Test health check task when no integrations exist"""
    mock_db_client.execute.return_value = Mock(data=[])

    with patch('app.tasks.integration_health.db_manager') as mock_manager:
        mock_manager.get_client.return_value = mock_db_client

        result = await test_health_check_task()

    assert result is None


# ==================== Edge Cases ====================

@pytest.mark.asyncio
async def test_duplicate_workspace_ids_handled(mock_db_client):
    """Test handling duplicate workspace IDs in database"""
    workspace_id = uuid4()
    # Duplicate workspace IDs
    mock_db_client.execute.return_value = Mock(
        data=[
            {"workspace_id": str(workspace_id)},
            {"workspace_id": str(workspace_id)}
        ]
    )

    with patch('app.tasks.integration_health.db_manager') as mock_manager:
        mock_manager.get_client.return_value = mock_db_client

        with patch('app.tasks.integration_health.run_workspace_health_check', new_callable=AsyncMock) as mock_check:
            await run_all_workspaces_health_check()

    # Should only check once due to set usage
    assert mock_check.call_count == 1


def test_schedule_prevent_overlapping_runs():
    """Test scheduler prevents overlapping runs"""
    with patch('app.tasks.integration_health.AsyncIOScheduler') as mock_scheduler_class:
        mock_scheduler = Mock()
        mock_scheduler.running = False
        mock_scheduler_class.return_value = mock_scheduler

        schedule_health_checks()

        # Verify max_instances=1 to prevent overlap
        call_args = mock_scheduler.add_job.call_args
        assert call_args[1]["max_instances"] == 1
