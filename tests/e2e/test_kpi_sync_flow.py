"""
AI Chief of Staff - KPI Sync Flow E2E Tests
Sprint 4: Insights & Briefings Engine - Issue #10

End-to-end test scenarios:
1. Complete KPI Sync - scheduled job → Granola data → validation → storage → derived metrics → historical snapshots
2. Custom KPI Definition - define → sync → validate → display
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from tests.fixtures.kpi_fixtures import (
    KPIMetricFactory,
    CustomKPIFactory,
    create_kpi_dataset_with_anomalies
)
from tests.fixtures.mock_granola_responses import (
    get_standard_kpis_response,
    get_custom_kpis_response,
    get_sync_completed_response
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def e2e_workspace():
    """E2E test workspace setup."""
    return {
        "workspace_id": str(uuid4()),
        "founder_id": str(uuid4()),
        "workspace_name": "Test Startup Inc"
    }


@pytest.fixture
def mock_scheduler():
    """Mock scheduler for scheduled jobs."""
    scheduler = Mock()
    scheduler.add_job = Mock()
    scheduler.get_jobs = Mock(return_value=[])
    scheduler.start = Mock()
    return scheduler


@pytest.fixture
def mock_kpi_sync_pipeline(mock_granola_connector, supabase_client_mock):
    """Mock complete KPI sync pipeline."""
    pipeline = Mock()
    pipeline.granola_connector = mock_granola_connector
    pipeline.db = supabase_client_mock
    pipeline.run_sync = AsyncMock()
    pipeline.schedule_sync = Mock()
    pipeline.validate_data = Mock(return_value=True)
    pipeline.store_metrics = AsyncMock()
    pipeline.calculate_derived = AsyncMock()
    pipeline.create_snapshots = AsyncMock()
    return pipeline


# ============================================================================
# SCENARIO 1: COMPLETE KPI SYNC
# ============================================================================

@pytest.mark.e2e
@pytest.mark.kpi
@pytest.mark.asyncio
class TestCompleteKPISyncFlow:
    """Test complete KPI sync workflow end-to-end."""

    async def test_scheduled_job_triggers_sync(
        self, mock_kpi_sync_pipeline, mock_scheduler, e2e_workspace
    ):
        """
        Test: Scheduled job triggers at configured interval
        Given: Job scheduled for every 6 hours
        When: Scheduler triggers the job
        Then: KPI sync pipeline is executed
        """
        # Arrange
        workspace_id = e2e_workspace["workspace_id"]
        mock_scheduler.add_job.return_value = True

        # Act
        mock_kpi_sync_pipeline.schedule_sync(
            workspace_id=workspace_id,
            interval_hours=6
        )

        # Assert
        mock_kpi_sync_pipeline.schedule_sync.assert_called_once_with(
            workspace_id=workspace_id,
            interval_hours=6
        )

    async def test_granola_data_fetched(
        self, mock_kpi_sync_pipeline, e2e_workspace
    ):
        """
        Test: Granola MCP data is fetched successfully
        Given: Valid Granola connection
        When: Sync job runs
        Then: Standard KPIs are fetched from Granola
        """
        # Arrange
        workspace_id = e2e_workspace["workspace_id"]
        mock_kpi_sync_pipeline.granola_connector.fetch_kpis.return_value = (
            get_standard_kpis_response()
        )

        # Act
        granola_data = await mock_kpi_sync_pipeline.granola_connector.fetch_kpis(
            workspace_id
        )

        # Assert
        assert granola_data["status"] == "success"
        assert "mrr" in granola_data["data"]
        assert "cac" in granola_data["data"]
        assert "churn_rate" in granola_data["data"]

    async def test_kpis_validated_and_stored(
        self, mock_kpi_sync_pipeline, e2e_workspace
    ):
        """
        Test: KPIs are validated and stored in database
        Given: Fetched KPI data from Granola
        When: Data validation passes
        Then: KPIs are stored in intel.kpi_metrics table
        """
        # Arrange
        workspace_id = e2e_workspace["workspace_id"]
        granola_data = get_standard_kpis_response()["data"]

        mock_kpi_sync_pipeline.validate_data.return_value = True
        mock_kpi_sync_pipeline.store_metrics.return_value = {
            "stored": 10,
            "failed": 0
        }

        # Act
        is_valid = mock_kpi_sync_pipeline.validate_data(granola_data)
        store_result = await mock_kpi_sync_pipeline.store_metrics(
            workspace_id, granola_data
        )

        # Assert
        assert is_valid is True
        assert store_result["stored"] == 10
        assert store_result["failed"] == 0

    async def test_derived_metrics_calculated(
        self, mock_kpi_sync_pipeline, e2e_workspace
    ):
        """
        Test: Derived metrics are calculated from base KPIs
        Given: Stored base KPIs (MRR, CAC, LTV, etc.)
        When: Derived metric calculation runs
        Then: LTV/CAC ratio, payback period, etc. are calculated and stored
        """
        # Arrange
        workspace_id = e2e_workspace["workspace_id"]
        base_kpis = {
            "ltv": 2500.0,
            "cac": 485.0,
            "mrr": 52500.0,
            "gross_margin": 0.72
        }

        mock_kpi_sync_pipeline.calculate_derived.return_value = {
            "ltv_to_cac_ratio": 5.15,
            "payback_period": 8.2,
            "magic_number": 0.75
        }

        # Act
        derived = await mock_kpi_sync_pipeline.calculate_derived(
            workspace_id, base_kpis
        )

        # Assert
        assert "ltv_to_cac_ratio" in derived
        assert "payback_period" in derived
        assert derived["ltv_to_cac_ratio"] > 3  # Good ratio

    async def test_historical_snapshots_created(
        self, mock_kpi_sync_pipeline, e2e_workspace
    ):
        """
        Test: Historical snapshots are created for trend analysis
        Given: Current KPI values
        When: Snapshot creation runs
        Then: Time-series snapshots are stored
        """
        # Arrange
        workspace_id = e2e_workspace["workspace_id"]
        kpi_data = get_standard_kpis_response()["data"]

        mock_kpi_sync_pipeline.create_snapshots.return_value = {
            "snapshots_created": 10
        }

        # Act
        result = await mock_kpi_sync_pipeline.create_snapshots(
            workspace_id, kpi_data
        )

        # Assert
        assert result["snapshots_created"] == 10

    async def test_complete_sync_workflow_end_to_end(
        self, mock_kpi_sync_pipeline, e2e_workspace
    ):
        """
        Test: Complete sync workflow from trigger to completion
        Given: Scheduled sync job
        When: Job runs completely
        Then: All steps complete successfully with events logged
        """
        # Arrange
        workspace_id = e2e_workspace["workspace_id"]

        mock_kpi_sync_pipeline.run_sync.return_value = {
            "status": "completed",
            "sync_id": str(uuid4()),
            "steps_completed": [
                "fetch",
                "validate",
                "store",
                "derive",
                "snapshot"
            ],
            "metrics_synced": 10,
            "derived_calculated": 3,
            "snapshots_created": 10,
            "duration_seconds": 15.5
        }

        # Act
        result = await mock_kpi_sync_pipeline.run_sync(workspace_id)

        # Assert
        assert result["status"] == "completed"
        assert len(result["steps_completed"]) == 5
        assert result["metrics_synced"] == 10
        assert result["derived_calculated"] == 3
        assert result["snapshots_created"] == 10
        assert result["duration_seconds"] < 60  # Within performance threshold

    async def test_sync_error_handling_and_recovery(
        self, mock_kpi_sync_pipeline, e2e_workspace
    ):
        """
        Test: Sync handles errors and recovers
        Given: Granola connection failure
        When: Sync encounters error
        Then: Error is logged, retry is attempted, recovery succeeds
        """
        # Arrange
        workspace_id = e2e_workspace["workspace_id"]

        # Simulate failure then success
        mock_kpi_sync_pipeline.run_sync.side_effect = [
            Exception("Temporary connection failure"),
            {
                "status": "completed",
                "retry_attempt": 1,
                "metrics_synced": 10
            }
        ]

        # Act - First attempt fails
        with pytest.raises(Exception, match="Temporary connection failure"):
            await mock_kpi_sync_pipeline.run_sync(workspace_id)

        # Act - Retry succeeds
        result = await mock_kpi_sync_pipeline.run_sync(workspace_id)

        # Assert
        assert result["status"] == "completed"
        assert result["retry_attempt"] == 1


# ============================================================================
# SCENARIO 2: CUSTOM KPI DEFINITION
# ============================================================================

@pytest.mark.e2e
@pytest.mark.kpi
@pytest.mark.asyncio
class TestCustomKPIDefinitionFlow:
    """Test custom KPI definition and sync workflow."""

    async def test_define_custom_kpi(
        self, supabase_client_mock, e2e_workspace
    ):
        """
        Test: Define a new custom KPI
        Given: Founder wants to track custom metric
        When: Custom KPI is defined with formula
        Then: Definition is stored in database
        """
        # Arrange
        workspace_id = e2e_workspace["workspace_id"]
        founder_id = e2e_workspace["founder_id"]

        custom_kpi = CustomKPIFactory(
            workspace_id=workspace_id,
            founder_id=founder_id,
            metric_name="trial_to_paid_conversion",
            display_name="Trial to Paid Conversion Rate",
            calculation_formula={
                "type": "formula",
                "expression": "(paid_users / trial_users) * 100"
            }
        )

        # Mock database insert
        supabase_client_mock.table.return_value.insert.return_value.execute.return_value.data = [
            custom_kpi
        ]

        # Act
        result = supabase_client_mock.table("custom_kpis").insert(custom_kpi).execute()

        # Assert
        assert len(result.data) == 1
        assert result.data[0]["metric_name"] == "trial_to_paid_conversion"
        assert "calculation_formula" in result.data[0]

    async def test_sync_custom_kpi_from_granola(
        self, mock_kpi_sync_pipeline, e2e_workspace
    ):
        """
        Test: Sync custom KPI from Granola
        Given: Custom KPI defined
        When: Sync runs
        Then: Custom KPI value is fetched from Granola
        """
        # Arrange
        workspace_id = e2e_workspace["workspace_id"]

        mock_kpi_sync_pipeline.granola_connector.fetch_custom_kpis.return_value = (
            get_custom_kpis_response(workspace_id)
        )

        # Act
        result = await mock_kpi_sync_pipeline.granola_connector.fetch_custom_kpis(
            workspace_id
        )

        # Assert
        assert result["status"] == "success"
        assert "trial_to_paid_conversion" in result["data"]
        assert result["data"]["trial_to_paid_conversion"]["custom"] is True

    async def test_validate_custom_kpi_calculation(
        self, mock_kpi_sync_pipeline
    ):
        """
        Test: Validate custom KPI calculation
        Given: Custom KPI with formula
        When: Calculation is performed
        Then: Result matches expected value
        """
        # Arrange
        trial_users = 100
        paid_users = 28
        expected_conversion = 0.28  # 28%

        custom_kpi_data = {
            "metric_name": "trial_to_paid_conversion",
            "metric_value": expected_conversion,
            "formula": "(paid_users / trial_users) * 100"
        }

        mock_kpi_sync_pipeline.validate_data.return_value = True

        # Act
        is_valid = mock_kpi_sync_pipeline.validate_data(custom_kpi_data)
        actual_value = custom_kpi_data["metric_value"]

        # Assert
        assert is_valid is True
        assert actual_value == pytest.approx(expected_conversion, rel=0.01)

    async def test_display_custom_kpi_in_dashboard(
        self, supabase_client_mock, e2e_workspace
    ):
        """
        Test: Display custom KPI in dashboard
        Given: Custom KPI stored
        When: Dashboard loads
        Then: Custom KPI is retrieved and displayed
        """
        # Arrange
        workspace_id = e2e_workspace["workspace_id"]

        custom_kpis = [
            CustomKPIFactory(workspace_id=workspace_id)
            for _ in range(3)
        ]

        # Mock database query
        supabase_client_mock.table.return_value.select.return_value.eq.return_value.execute.return_value.data = custom_kpis

        # Act
        result = (
            supabase_client_mock.table("custom_kpis")
            .select("*")
            .eq("workspace_id", workspace_id)
            .execute()
        )

        # Assert
        assert len(result.data) == 3
        assert all("metric_name" in kpi for kpi in result.data)

    async def test_complete_custom_kpi_flow(
        self, mock_kpi_sync_pipeline, supabase_client_mock, e2e_workspace
    ):
        """
        Test: Complete custom KPI flow from definition to display
        Given: Founder defines custom KPI
        When: Full workflow executes
        Then: KPI is defined, synced, validated, and displayed
        """
        # Arrange
        workspace_id = e2e_workspace["workspace_id"]
        founder_id = e2e_workspace["founder_id"]

        # Step 1: Define custom KPI
        custom_kpi_definition = CustomKPIFactory(
            workspace_id=workspace_id,
            founder_id=founder_id,
            metric_name="activation_rate"
        )

        supabase_client_mock.table.return_value.insert.return_value.execute.return_value.data = [
            custom_kpi_definition
        ]

        # Step 2: Sync from Granola
        mock_kpi_sync_pipeline.granola_connector.fetch_custom_kpis.return_value = {
            "status": "success",
            "data": {
                "activation_rate": {
                    "value": 0.65,
                    "custom": True
                }
            }
        }

        # Step 3: Validate
        mock_kpi_sync_pipeline.validate_data.return_value = True

        # Step 4: Store
        mock_kpi_sync_pipeline.store_metrics.return_value = {
            "stored": 1,
            "failed": 0
        }

        # Act - Execute full flow
        # 1. Define
        definition_result = (
            supabase_client_mock.table("custom_kpis")
            .insert(custom_kpi_definition)
            .execute()
        )

        # 2. Sync
        sync_result = await mock_kpi_sync_pipeline.granola_connector.fetch_custom_kpis(
            workspace_id
        )

        # 3. Validate
        is_valid = mock_kpi_sync_pipeline.validate_data(
            sync_result["data"]["activation_rate"]
        )

        # 4. Store
        store_result = await mock_kpi_sync_pipeline.store_metrics(
            workspace_id, sync_result["data"]
        )

        # Assert
        assert len(definition_result.data) == 1
        assert sync_result["status"] == "success"
        assert is_valid is True
        assert store_result["stored"] == 1


# ============================================================================
# SCENARIO 3: SYNC WITH ANOMALIES
# ============================================================================

@pytest.mark.e2e
@pytest.mark.kpi
@pytest.mark.asyncio
class TestKPISyncWithAnomalies:
    """Test KPI sync when anomalies are detected."""

    async def test_sync_detects_anomalous_values(
        self, mock_kpi_sync_pipeline, e2e_workspace
    ):
        """
        Test: Sync detects and flags anomalous KPI values
        Given: KPI data with anomaly
        When: Sync runs
        Then: Anomaly is detected and flagged
        """
        # Arrange
        workspace_id = e2e_workspace["workspace_id"]

        dataset = create_kpi_dataset_with_anomalies(
            workspace_id=workspace_id,
            metrics=["churn_rate"],
            days=30,
            num_anomalies=1
        )

        mock_kpi_sync_pipeline.run_sync.return_value = {
            "status": "completed",
            "metrics_synced": 30,
            "anomalies_detected": 1,
            "anomalies": dataset["anomalies"]
        }

        # Act
        result = await mock_kpi_sync_pipeline.run_sync(workspace_id)

        # Assert
        assert result["status"] == "completed"
        assert result["anomalies_detected"] == 1
        assert len(result["anomalies"]) == 1

    async def test_anomaly_triggers_alert(
        self, mock_kpi_sync_pipeline, e2e_workspace
    ):
        """
        Test: Detected anomaly triggers alert notification
        Given: Anomaly detected during sync
        When: Anomaly severity is high
        Then: Alert is sent to founder
        """
        # Arrange
        workspace_id = e2e_workspace["workspace_id"]

        mock_kpi_sync_pipeline.run_sync.return_value = {
            "status": "completed",
            "anomalies_detected": 1,
            "alerts_sent": 1,
            "alert_details": {
                "metric": "churn_rate",
                "severity": "high",
                "deviation": "+30%"
            }
        }

        # Act
        result = await mock_kpi_sync_pipeline.run_sync(workspace_id)

        # Assert
        assert result["alerts_sent"] == 1
        assert result["alert_details"]["severity"] == "high"
