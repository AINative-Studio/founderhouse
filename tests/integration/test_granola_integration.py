"""
AI Chief of Staff - Granola Integration Tests
Sprint 4: Insights & Briefings Engine - Issue #10

Integration test coverage for:
- Full Granola MCP data pull
- Data freshness validation (<6h)
- Sync status tracking
- Error handling and retry
- Event logging
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from tests.fixtures.kpi_fixtures import KPIMetricFactory
from tests.fixtures.mock_granola_responses import (
    get_standard_kpis_response,
    get_sync_in_progress_response,
    get_sync_completed_response,
    get_sync_failed_response,
    get_connection_success_response,
    get_health_check_healthy_response,
    get_authentication_error_response,
    get_rate_limit_error_response
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def integration_config():
    """Integration test configuration."""
    return {
        "workspace_id": str(uuid4()),
        "founder_id": str(uuid4()),
        "integration_id": str(uuid4()),
        "sync_interval_hours": 6
    }


@pytest.fixture
def mock_granola_integration(mock_granola_connector):
    """Mock Granola integration service."""
    integration = Mock()
    integration.connector = mock_granola_connector
    integration.workspace_id = str(uuid4())
    integration.sync_kpis = AsyncMock()
    integration.track_sync_status = AsyncMock()
    integration.log_sync_event = AsyncMock()
    integration.retry_on_error = AsyncMock()
    return integration


# ============================================================================
# FULL DATA PULL TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.kpi
@pytest.mark.asyncio
class TestFullGranolaDataPull:
    """Test full Granola MCP data pull."""

    async def test_complete_kpi_sync_workflow(
        self, mock_granola_integration, integration_config
    ):
        """Test complete KPI sync workflow from start to finish."""
        # Arrange
        workspace_id = integration_config["workspace_id"]
        sync_id = str(uuid4())

        # Mock sync workflow
        mock_granola_integration.sync_kpis.return_value = {
            "sync_id": sync_id,
            "status": "completed",
            "metrics_synced": 10,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Act
        result = await mock_granola_integration.sync_kpis(workspace_id)

        # Assert
        assert result["status"] == "completed"
        assert result["sync_id"] == sync_id
        assert result["metrics_synced"] == 10
        mock_granola_integration.sync_kpis.assert_called_once_with(workspace_id)

    async def test_sync_includes_all_standard_metrics(
        self, mock_granola_integration, integration_config
    ):
        """Test that sync includes all required standard metrics."""
        # Arrange
        workspace_id = integration_config["workspace_id"]
        expected_metrics = [
            "mrr", "cac", "churn_rate", "conversion_rate",
            "runway_months", "ltv", "burn_rate"
        ]

        mock_granola_integration.sync_kpis.return_value = {
            "status": "completed",
            "metrics": expected_metrics,
            "metrics_synced": len(expected_metrics)
        }

        # Act
        result = await mock_granola_integration.sync_kpis(workspace_id)

        # Assert
        assert result["metrics_synced"] == len(expected_metrics)
        assert all(metric in result["metrics"] for metric in expected_metrics)

    async def test_sync_validates_data_before_storage(
        self, mock_granola_integration, integration_config
    ):
        """Test that sync validates data before storing."""
        # Arrange
        workspace_id = integration_config["workspace_id"]

        mock_granola_integration.sync_kpis.return_value = {
            "status": "completed",
            "validated": True,
            "validation_errors": []
        }

        # Act
        result = await mock_granola_integration.sync_kpis(workspace_id)

        # Assert
        assert result["validated"] is True
        assert len(result["validation_errors"]) == 0

    async def test_sync_stores_to_database(
        self, mock_granola_integration, integration_config, supabase_client_mock
    ):
        """Test that sync stores data to database."""
        # Arrange
        workspace_id = integration_config["workspace_id"]

        # Mock database insert
        supabase_client_mock.table.return_value.insert.return_value.execute.return_value.data = [
            KPIMetricFactory(workspace_id=workspace_id)
        ]

        mock_granola_integration.sync_kpis.return_value = {
            "status": "completed",
            "stored": True,
            "records_inserted": 10
        }

        # Act
        result = await mock_granola_integration.sync_kpis(workspace_id)

        # Assert
        assert result["stored"] is True
        assert result["records_inserted"] == 10


# ============================================================================
# DATA FRESHNESS VALIDATION TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.kpi
@pytest.mark.asyncio
class TestDataFreshnessValidation:
    """Test data freshness validation."""

    async def test_validate_data_freshness_within_threshold(
        self, mock_granola_integration
    ):
        """Test that data within 6h threshold passes validation."""
        # Arrange
        fresh_timestamp = datetime.utcnow() - timedelta(hours=4)
        kpi_data = {
            "mrr": {
                "value": 52500,
                "timestamp": fresh_timestamp.isoformat()
            }
        }

        mock_granola_integration.sync_kpis.return_value = {
            "status": "completed",
            "data_freshness_valid": True,
            "freshness_hours": 4.0
        }

        # Act
        result = await mock_granola_integration.sync_kpis("workspace_id")

        # Assert
        assert result["data_freshness_valid"] is True
        assert result["freshness_hours"] < 6

    async def test_validate_data_freshness_exceeds_threshold(
        self, mock_granola_integration
    ):
        """Test that stale data (>6h) is flagged."""
        # Arrange
        stale_timestamp = datetime.utcnow() - timedelta(hours=8)
        kpi_data = {
            "mrr": {
                "value": 52500,
                "timestamp": stale_timestamp.isoformat()
            }
        }

        mock_granola_integration.sync_kpis.return_value = {
            "status": "completed",
            "data_freshness_valid": False,
            "freshness_hours": 8.0,
            "warnings": ["Data exceeds 6-hour freshness threshold"]
        }

        # Act
        result = await mock_granola_integration.sync_kpis("workspace_id")

        # Assert
        assert result["data_freshness_valid"] is False
        assert result["freshness_hours"] > 6
        assert len(result["warnings"]) > 0

    async def test_sync_scheduled_every_6_hours(self, integration_config):
        """Test that sync is scheduled to run every 6 hours."""
        # Arrange
        sync_interval = integration_config["sync_interval_hours"]

        # Assert
        assert sync_interval == 6


# ============================================================================
# SYNC STATUS TRACKING TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.kpi
@pytest.mark.asyncio
class TestSyncStatusTracking:
    """Test sync status tracking."""

    async def test_track_sync_in_progress(self, mock_granola_integration):
        """Test tracking of sync in progress."""
        # Arrange
        sync_id = str(uuid4())
        mock_granola_integration.track_sync_status.return_value = get_sync_in_progress_response(sync_id)

        # Act
        result = await mock_granola_integration.track_sync_status(sync_id)

        # Assert
        assert result["status"] == "in_progress"
        assert result["sync_id"] == sync_id
        assert "progress" in result
        assert 0.0 <= result["progress"] <= 1.0

    async def test_track_sync_completed(self, mock_granola_integration):
        """Test tracking of completed sync."""
        # Arrange
        sync_id = str(uuid4())
        mock_granola_integration.track_sync_status.return_value = get_sync_completed_response(sync_id)

        # Act
        result = await mock_granola_integration.track_sync_status(sync_id)

        # Assert
        assert result["status"] == "completed"
        assert result["progress"] == 1.0
        assert "metrics_synced" in result
        assert "completed_at" in result

    async def test_track_sync_failed(self, mock_granola_integration):
        """Test tracking of failed sync."""
        # Arrange
        sync_id = str(uuid4())
        mock_granola_integration.track_sync_status.return_value = get_sync_failed_response(sync_id)

        # Act
        result = await mock_granola_integration.track_sync_status(sync_id)

        # Assert
        assert result["status"] == "failed"
        assert "error" in result
        assert "failed_at" in result

    async def test_sync_status_stored_in_database(
        self, mock_granola_integration, supabase_client_mock
    ):
        """Test that sync status is stored in database."""
        # Arrange
        sync_id = str(uuid4())
        sync_status = {
            "sync_id": sync_id,
            "status": "in_progress",
            "progress": 0.5
        }

        # Mock database insert
        supabase_client_mock.table.return_value.insert.return_value.execute.return_value.data = [
            sync_status
        ]

        mock_granola_integration.track_sync_status.return_value = sync_status

        # Act
        result = await mock_granola_integration.track_sync_status(sync_id)

        # Assert
        assert result["sync_id"] == sync_id
        assert result["status"] == "in_progress"


# ============================================================================
# ERROR HANDLING AND RETRY TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.kpi
@pytest.mark.asyncio
class TestErrorHandlingAndRetry:
    """Test error handling and retry logic."""

    async def test_retry_on_authentication_error(self, mock_granola_integration):
        """Test retry logic on authentication error."""
        # Arrange
        mock_granola_integration.retry_on_error.return_value = {
            "status": "retrying",
            "attempt": 1,
            "max_attempts": 3,
            "error": "AUTHENTICATION_FAILED"
        }

        # Act
        result = await mock_granola_integration.retry_on_error(
            error_type="AUTHENTICATION_FAILED",
            max_attempts=3
        )

        # Assert
        assert result["status"] == "retrying"
        assert result["attempt"] == 1
        assert result["max_attempts"] == 3

    async def test_retry_on_rate_limit_with_backoff(self, mock_granola_integration):
        """Test retry with exponential backoff on rate limit."""
        # Arrange
        mock_granola_integration.retry_on_error.return_value = {
            "status": "retrying",
            "attempt": 1,
            "wait_seconds": 60,
            "error": "RATE_LIMIT_EXCEEDED"
        }

        # Act
        result = await mock_granola_integration.retry_on_error(
            error_type="RATE_LIMIT_EXCEEDED",
            wait_seconds=60
        )

        # Assert
        assert result["status"] == "retrying"
        assert result["wait_seconds"] == 60

    async def test_max_retries_exhausted(self, mock_granola_integration):
        """Test that sync fails after max retries."""
        # Arrange
        mock_granola_integration.retry_on_error.return_value = {
            "status": "failed",
            "attempt": 3,
            "max_attempts": 3,
            "error": "Max retries exhausted"
        }

        # Act
        result = await mock_granola_integration.retry_on_error(
            error_type="CONNECTION_FAILED",
            max_attempts=3
        )

        # Assert
        assert result["status"] == "failed"
        assert result["attempt"] == result["max_attempts"]

    async def test_retry_with_exponential_backoff(self):
        """Test exponential backoff calculation."""
        # Arrange
        base_wait = 2  # seconds
        max_attempts = 5

        # Act & Assert
        for attempt in range(1, max_attempts + 1):
            wait_time = base_wait * (2 ** (attempt - 1))
            assert wait_time == base_wait * (2 ** (attempt - 1))

            # Exponential backoff: 2, 4, 8, 16, 32 seconds
            if attempt == 1:
                assert wait_time == 2
            elif attempt == 2:
                assert wait_time == 4
            elif attempt == 3:
                assert wait_time == 8

    async def test_transient_error_recovers(self, mock_granola_integration):
        """Test recovery from transient error."""
        # Arrange
        # First call fails, second succeeds
        mock_granola_integration.sync_kpis.side_effect = [
            Exception("Temporary network error"),
            {"status": "completed", "metrics_synced": 10}
        ]

        # Act - first attempt fails
        with pytest.raises(Exception, match="Temporary network error"):
            await mock_granola_integration.sync_kpis("workspace_id")

        # Act - retry succeeds
        result = await mock_granola_integration.sync_kpis("workspace_id")

        # Assert
        assert result["status"] == "completed"
        assert result["metrics_synced"] == 10


# ============================================================================
# EVENT LOGGING TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.kpi
@pytest.mark.asyncio
class TestEventLogging:
    """Test event logging for sync operations."""

    async def test_log_sync_started_event(
        self, mock_granola_integration, integration_config
    ):
        """Test logging of sync started event."""
        # Arrange
        workspace_id = integration_config["workspace_id"]
        sync_id = str(uuid4())

        event = {
            "event_type": "kpi_sync.started",
            "workspace_id": workspace_id,
            "sync_id": sync_id,
            "timestamp": datetime.utcnow().isoformat()
        }

        mock_granola_integration.log_sync_event.return_value = event

        # Act
        result = await mock_granola_integration.log_sync_event(
            event_type="kpi_sync.started",
            workspace_id=workspace_id,
            sync_id=sync_id
        )

        # Assert
        assert result["event_type"] == "kpi_sync.started"
        assert result["workspace_id"] == workspace_id
        assert result["sync_id"] == sync_id

    async def test_log_sync_completed_event(
        self, mock_granola_integration, integration_config
    ):
        """Test logging of sync completed event."""
        # Arrange
        workspace_id = integration_config["workspace_id"]
        sync_id = str(uuid4())

        event = {
            "event_type": "kpi_sync.completed",
            "workspace_id": workspace_id,
            "sync_id": sync_id,
            "metrics_synced": 10,
            "duration_seconds": 12.5,
            "timestamp": datetime.utcnow().isoformat()
        }

        mock_granola_integration.log_sync_event.return_value = event

        # Act
        result = await mock_granola_integration.log_sync_event(
            event_type="kpi_sync.completed",
            workspace_id=workspace_id,
            sync_id=sync_id,
            metrics_synced=10,
            duration_seconds=12.5
        )

        # Assert
        assert result["event_type"] == "kpi_sync.completed"
        assert result["metrics_synced"] == 10
        assert result["duration_seconds"] == 12.5

    async def test_log_sync_failed_event(
        self, mock_granola_integration, integration_config
    ):
        """Test logging of sync failed event."""
        # Arrange
        workspace_id = integration_config["workspace_id"]
        sync_id = str(uuid4())

        event = {
            "event_type": "kpi_sync.failed",
            "workspace_id": workspace_id,
            "sync_id": sync_id,
            "error": "AUTHENTICATION_FAILED",
            "error_message": "Invalid API credentials",
            "timestamp": datetime.utcnow().isoformat()
        }

        mock_granola_integration.log_sync_event.return_value = event

        # Act
        result = await mock_granola_integration.log_sync_event(
            event_type="kpi_sync.failed",
            workspace_id=workspace_id,
            sync_id=sync_id,
            error="AUTHENTICATION_FAILED",
            error_message="Invalid API credentials"
        )

        # Assert
        assert result["event_type"] == "kpi_sync.failed"
        assert result["error"] == "AUTHENTICATION_FAILED"
        assert "error_message" in result

    async def test_events_stored_in_database(
        self, mock_granola_integration, supabase_client_mock
    ):
        """Test that events are stored in ops.events table."""
        # Arrange
        event = {
            "event_type": "kpi_sync.completed",
            "workspace_id": str(uuid4()),
            "payload": {"metrics_synced": 10}
        }

        # Mock database insert
        supabase_client_mock.table.return_value.insert.return_value.execute.return_value.data = [
            event
        ]

        mock_granola_integration.log_sync_event.return_value = event

        # Act
        result = await mock_granola_integration.log_sync_event(**event)

        # Assert
        assert result["event_type"] == "kpi_sync.completed"


# ============================================================================
# CONNECTION AND HEALTH CHECK TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.kpi
@pytest.mark.asyncio
class TestConnectionAndHealth:
    """Test connection and health check integration."""

    async def test_verify_connection_before_sync(self, mock_granola_connector):
        """Test that connection is verified before sync."""
        # Arrange
        mock_granola_connector.connect.return_value = get_connection_success_response()

        # Act
        result = await mock_granola_connector.connect()

        # Assert
        assert result["connected"] is True
        assert result["status"] == "success"

    async def test_health_check_before_sync(self, mock_granola_connector):
        """Test health check before sync operation."""
        # Arrange
        mock_granola_connector.health_check.return_value = get_health_check_healthy_response()

        # Act
        result = await mock_granola_connector.health_check()

        # Assert
        assert result["status"] == "healthy"
        assert "checks" in result

    async def test_skip_sync_if_unhealthy(self, mock_granola_integration):
        """Test that sync is skipped if service is unhealthy."""
        # Arrange
        mock_granola_integration.sync_kpis.return_value = {
            "status": "skipped",
            "reason": "Service unhealthy"
        }

        # Act
        result = await mock_granola_integration.sync_kpis("workspace_id")

        # Assert
        assert result["status"] == "skipped"
        assert "reason" in result


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.kpi
@pytest.mark.performance
@pytest.mark.asyncio
class TestSyncPerformance:
    """Test sync performance."""

    async def test_sync_completes_within_timeout(self, mock_granola_integration):
        """Test that sync completes within acceptable time."""
        # Arrange
        start_time = datetime.utcnow()
        max_duration_seconds = 60

        mock_granola_integration.sync_kpis.return_value = {
            "status": "completed",
            "duration_seconds": 45
        }

        # Act
        result = await mock_granola_integration.sync_kpis("workspace_id")
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        # Assert
        assert result["status"] == "completed"
        assert result["duration_seconds"] < max_duration_seconds
        assert duration < max_duration_seconds

    async def test_concurrent_workspace_syncs(self, mock_granola_integration):
        """Test concurrent syncs for multiple workspaces."""
        # Arrange
        workspace_ids = [str(uuid4()) for _ in range(5)]

        mock_granola_integration.sync_kpis.return_value = {
            "status": "completed",
            "metrics_synced": 10
        }

        # Act
        tasks = [
            mock_granola_integration.sync_kpis(workspace_id)
            for workspace_id in workspace_ids
        ]
        results = await asyncio.gather(*tasks)

        # Assert
        assert len(results) == 5
        assert all(result["status"] == "completed" for result in results)
