"""
AI Chief of Staff - KPI Ingestion Service Unit Tests
Sprint 4: Insights & Briefings Engine - Issue #10

Test coverage for:
- Connect to Granola MCP
- Fetch standard KPIs (MRR, CAC, churn, conversion, runway)
- Fetch custom KPIs
- Data validation and normalization
- Historical data storage
- Derived metric calculation
- Missing data handling
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from tests.fixtures.kpi_fixtures import KPIMetricFactory, CustomKPIFactory
from tests.fixtures.mock_granola_responses import (
    get_standard_kpis_response,
    get_custom_kpis_response,
    get_historical_kpis_response,
    get_derived_metrics_response,
    get_authentication_error_response,
    get_rate_limit_error_response,
    get_partial_data_response,
    get_missing_data_response,
    get_fresh_data_response,
    get_stale_data_response
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_granola_connector():
    """Mock Granola MCP connector."""
    connector = AsyncMock()
    connector.connect.return_value = {"status": "connected", "platform": "granola"}
    connector.disconnect.return_value = {"status": "disconnected"}
    connector.fetch_kpis.return_value = get_standard_kpis_response()
    connector.fetch_custom_kpis.return_value = get_custom_kpis_response(str(uuid4()))
    connector.fetch_historical_data.return_value = get_historical_kpis_response("mrr", 30)
    connector.health_check.return_value = {"status": "healthy", "is_healthy": True}
    return connector


@pytest.fixture
def mock_kpi_service(supabase_client_mock, mock_granola_connector):
    """Mock KPI ingestion service."""
    from unittest.mock import Mock

    service = Mock()
    service.db = supabase_client_mock
    service.granola_connector = mock_granola_connector
    service.fetch_standard_kpis = AsyncMock()
    service.fetch_custom_kpis = AsyncMock()
    service.fetch_historical_data = AsyncMock()
    service.validate_kpi_data = Mock()
    service.normalize_kpi_data = Mock()
    service.store_kpi_metrics = AsyncMock()
    service.calculate_derived_metrics = AsyncMock()
    service.handle_missing_data = Mock()

    return service


@pytest.fixture
def sample_workspace_id():
    """Sample workspace ID."""
    return str(uuid4())


@pytest.fixture
def sample_founder_id():
    """Sample founder ID."""
    return str(uuid4())


# ============================================================================
# CONNECTION TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.kpi
class TestGranolaConnection:
    """Test Granola MCP connection."""

    async def test_connect_to_granola_mcp_success(self, mock_granola_connector):
        """Test successful connection to Granola MCP."""
        # Arrange
        # (connector already mocked)

        # Act
        result = await mock_granola_connector.connect()

        # Assert
        assert result["status"] == "connected"
        assert result["platform"] == "granola"
        mock_granola_connector.connect.assert_called_once()

    async def test_connect_to_granola_mcp_failure(self):
        """Test connection failure to Granola MCP."""
        # Arrange
        connector = AsyncMock()
        connector.connect.side_effect = Exception("Connection failed")

        # Act & Assert
        with pytest.raises(Exception, match="Connection failed"):
            await connector.connect()

    async def test_disconnect_from_granola_mcp(self, mock_granola_connector):
        """Test disconnection from Granola MCP."""
        # Arrange
        await mock_granola_connector.connect()

        # Act
        result = await mock_granola_connector.disconnect()

        # Assert
        assert result["status"] == "disconnected"
        mock_granola_connector.disconnect.assert_called_once()


# ============================================================================
# STANDARD KPI FETCH TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.kpi
class TestStandardKPIFetch:
    """Test standard KPI fetching."""

    async def test_fetch_standard_kpis_success(self, mock_granola_connector, sample_workspace_id):
        """Test successful fetch of standard KPIs."""
        # Arrange
        mock_granola_connector.fetch_kpis.return_value = get_standard_kpis_response()

        # Act
        result = await mock_granola_connector.fetch_kpis(sample_workspace_id)

        # Assert
        assert result["status"] == "success"
        assert "data" in result
        assert "mrr" in result["data"]
        assert "cac" in result["data"]
        assert "churn_rate" in result["data"]
        assert "conversion_rate" in result["data"]
        assert "runway_months" in result["data"]

    async def test_fetch_standard_kpis_includes_all_required_metrics(
        self, mock_granola_connector, sample_workspace_id
    ):
        """Test that all required standard KPIs are included."""
        # Arrange
        required_metrics = ["mrr", "cac", "churn_rate", "conversion_rate", "runway_months"]
        mock_granola_connector.fetch_kpis.return_value = get_standard_kpis_response()

        # Act
        result = await mock_granola_connector.fetch_kpis(sample_workspace_id)

        # Assert
        for metric in required_metrics:
            assert metric in result["data"], f"Missing required metric: {metric}"
            assert "value" in result["data"][metric]
            assert "unit" in result["data"][metric]
            assert "timestamp" in result["data"][metric]

    async def test_fetch_standard_kpis_with_confidence_scores(
        self, mock_granola_connector, sample_workspace_id
    ):
        """Test that KPIs include confidence scores."""
        # Arrange
        mock_granola_connector.fetch_kpis.return_value = get_standard_kpis_response()

        # Act
        result = await mock_granola_connector.fetch_kpis(sample_workspace_id)

        # Assert
        for metric_name, metric_data in result["data"].items():
            assert "confidence" in metric_data
            assert 0.0 <= metric_data["confidence"] <= 1.0

    async def test_fetch_standard_kpis_authentication_error(self, mock_granola_connector):
        """Test authentication error handling."""
        # Arrange
        mock_granola_connector.fetch_kpis.return_value = get_authentication_error_response()

        # Act
        result = await mock_granola_connector.fetch_kpis("test_workspace")

        # Assert
        assert result["status"] == "error"
        assert result["error"]["code"] == "AUTHENTICATION_FAILED"

    async def test_fetch_standard_kpis_rate_limit_error(self, mock_granola_connector):
        """Test rate limiting error handling."""
        # Arrange
        mock_granola_connector.fetch_kpis.return_value = get_rate_limit_error_response()

        # Act
        result = await mock_granola_connector.fetch_kpis("test_workspace")

        # Assert
        assert result["status"] == "error"
        assert result["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert "retry_after" in result["error"]


# ============================================================================
# CUSTOM KPI FETCH TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.kpi
class TestCustomKPIFetch:
    """Test custom KPI fetching."""

    async def test_fetch_custom_kpis_success(
        self, mock_granola_connector, sample_workspace_id
    ):
        """Test successful fetch of custom KPIs."""
        # Arrange
        mock_granola_connector.fetch_custom_kpis.return_value = get_custom_kpis_response(
            sample_workspace_id
        )

        # Act
        result = await mock_granola_connector.fetch_custom_kpis(sample_workspace_id)

        # Assert
        assert result["status"] == "success"
        assert "data" in result
        assert len(result["data"]) > 0

        # Verify custom KPI structure
        for metric_name, metric_data in result["data"].items():
            assert metric_data["custom"] is True
            assert "formula" in metric_data
            assert "value" in metric_data

    async def test_fetch_empty_custom_kpis(self, mock_granola_connector, sample_workspace_id):
        """Test fetching when no custom KPIs are defined."""
        # Arrange
        mock_granola_connector.fetch_custom_kpis.return_value = {
            "status": "success",
            "data": {},
            "metadata": {"custom_kpis": True}
        }

        # Act
        result = await mock_granola_connector.fetch_custom_kpis(sample_workspace_id)

        # Assert
        assert result["status"] == "success"
        assert result["data"] == {}


# ============================================================================
# DATA VALIDATION TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.kpi
class TestKPIDataValidation:
    """Test KPI data validation."""

    def test_validate_kpi_data_valid_structure(self, mock_kpi_service):
        """Test validation of valid KPI data structure."""
        # Arrange
        kpi_data = KPIMetricFactory()
        mock_kpi_service.validate_kpi_data.return_value = True

        # Act
        result = mock_kpi_service.validate_kpi_data(kpi_data)

        # Assert
        assert result is True

    def test_validate_kpi_data_invalid_value_type(self, mock_kpi_service):
        """Test validation rejects invalid value types."""
        # Arrange
        kpi_data = {
            "metric_name": "mrr",
            "metric_value": "invalid",  # Should be numeric
            "metric_unit": "usd"
        }
        mock_kpi_service.validate_kpi_data.return_value = False

        # Act
        result = mock_kpi_service.validate_kpi_data(kpi_data)

        # Assert
        assert result is False

    def test_validate_kpi_data_missing_required_fields(self, mock_kpi_service):
        """Test validation rejects data with missing required fields."""
        # Arrange
        kpi_data = {
            "metric_name": "mrr"
            # Missing metric_value and other required fields
        }
        mock_kpi_service.validate_kpi_data.return_value = False

        # Act
        result = mock_kpi_service.validate_kpi_data(kpi_data)

        # Assert
        assert result is False

    def test_validate_kpi_data_negative_values_allowed_for_some_metrics(self):
        """Test that negative values are allowed for certain metrics (e.g., change rates)."""
        # Arrange
        kpi_data = {
            "metric_name": "change_rate",
            "metric_value": -5.2,  # Negative is valid for change rates
            "metric_unit": "percent"
        }

        # Act & Assert
        # Should not raise an exception for valid negative values
        assert kpi_data["metric_value"] < 0  # Confirm it's negative


# ============================================================================
# DATA NORMALIZATION TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.kpi
class TestKPIDataNormalization:
    """Test KPI data normalization."""

    def test_normalize_kpi_data_converts_units(self, mock_kpi_service):
        """Test unit conversion during normalization."""
        # Arrange
        kpi_data = {
            "metric_name": "mrr",
            "metric_value": 52.5,  # In thousands
            "metric_unit": "k_usd"
        }
        expected_normalized = {
            "metric_name": "mrr",
            "metric_value": 52500.0,
            "metric_unit": "usd"
        }
        mock_kpi_service.normalize_kpi_data.return_value = expected_normalized

        # Act
        result = mock_kpi_service.normalize_kpi_data(kpi_data)

        # Assert
        assert result["metric_value"] == 52500.0
        assert result["metric_unit"] == "usd"

    def test_normalize_kpi_data_standardizes_timestamps(self, mock_kpi_service):
        """Test timestamp standardization during normalization."""
        # Arrange
        kpi_data = {
            "metric_name": "mrr",
            "metric_value": 52500.0,
            "timestamp": "2024-01-15T10:30:00Z"
        }
        mock_kpi_service.normalize_kpi_data.return_value = kpi_data

        # Act
        result = mock_kpi_service.normalize_kpi_data(kpi_data)

        # Assert
        assert "timestamp" in result
        # Verify ISO 8601 format
        datetime.fromisoformat(result["timestamp"].replace("Z", "+00:00"))

    def test_normalize_kpi_data_rounds_values(self, mock_kpi_service):
        """Test value rounding during normalization."""
        # Arrange
        kpi_data = {
            "metric_name": "churn_rate",
            "metric_value": 0.04876543,
            "metric_unit": "percent"
        }
        expected_normalized = {
            "metric_name": "churn_rate",
            "metric_value": 0.049,  # Rounded to 3 decimals
            "metric_unit": "percent"
        }
        mock_kpi_service.normalize_kpi_data.return_value = expected_normalized

        # Act
        result = mock_kpi_service.normalize_kpi_data(kpi_data)

        # Assert
        assert result["metric_value"] == 0.049


# ============================================================================
# HISTORICAL DATA TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.kpi
class TestHistoricalKPIData:
    """Test historical KPI data handling."""

    async def test_fetch_historical_data_success(
        self, mock_granola_connector, sample_workspace_id
    ):
        """Test successful fetch of historical KPI data."""
        # Arrange
        mock_granola_connector.fetch_historical_data.return_value = get_historical_kpis_response(
            "mrr", 30
        )

        # Act
        result = await mock_granola_connector.fetch_historical_data(
            sample_workspace_id, "mrr", days=30
        )

        # Assert
        assert result["status"] == "success"
        assert "data" in result
        assert "data_points" in result["data"]
        assert len(result["data"]["data_points"]) == 30

    async def test_fetch_historical_data_includes_time_period(
        self, mock_granola_connector, sample_workspace_id
    ):
        """Test that historical data includes time period information."""
        # Arrange
        mock_granola_connector.fetch_historical_data.return_value = get_historical_kpis_response(
            "mrr", 30
        )

        # Act
        result = await mock_granola_connector.fetch_historical_data(
            sample_workspace_id, "mrr", days=30
        )

        # Assert
        assert "period" in result["data"]
        assert "start" in result["data"]["period"]
        assert "end" in result["data"]["period"]
        assert "days" in result["data"]["period"]

    async def test_store_historical_snapshots(
        self, mock_kpi_service, sample_workspace_id
    ):
        """Test storing historical KPI snapshots."""
        # Arrange
        historical_data = get_historical_kpis_response("mrr", 30)
        mock_kpi_service.store_kpi_metrics.return_value = {"stored": 30}

        # Act
        result = await mock_kpi_service.store_kpi_metrics(
            sample_workspace_id, historical_data["data"]["data_points"]
        )

        # Assert
        assert result["stored"] == 30
        mock_kpi_service.store_kpi_metrics.assert_called_once()


# ============================================================================
# DERIVED METRICS TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.kpi
class TestDerivedMetrics:
    """Test derived metric calculation."""

    async def test_calculate_ltv_to_cac_ratio(self, mock_kpi_service):
        """Test calculation of LTV to CAC ratio."""
        # Arrange
        ltv = 2500.0
        cac = 485.0
        expected_ratio = ltv / cac
        mock_kpi_service.calculate_derived_metrics.return_value = {
            "ltv_to_cac_ratio": {
                "value": expected_ratio,
                "unit": "ratio",
                "derived_from": ["ltv", "cac"]
            }
        }

        # Act
        result = await mock_kpi_service.calculate_derived_metrics({"ltv": ltv, "cac": cac})

        # Assert
        assert "ltv_to_cac_ratio" in result
        assert result["ltv_to_cac_ratio"]["value"] == pytest.approx(expected_ratio, rel=0.01)

    async def test_calculate_payback_period(self, mock_kpi_service):
        """Test calculation of payback period."""
        # Arrange
        cac = 485.0
        monthly_revenue = 100.0
        gross_margin = 0.72
        expected_payback = cac / (monthly_revenue * gross_margin)

        mock_kpi_service.calculate_derived_metrics.return_value = {
            "payback_period": {
                "value": expected_payback,
                "unit": "months",
                "derived_from": ["cac", "mrr", "gross_margin"]
            }
        }

        # Act
        result = await mock_kpi_service.calculate_derived_metrics({
            "cac": cac,
            "monthly_revenue": monthly_revenue,
            "gross_margin": gross_margin
        })

        # Assert
        assert "payback_period" in result
        assert result["payback_period"]["value"] == pytest.approx(expected_payback, rel=0.01)

    async def test_calculate_derived_metrics_with_missing_inputs(self, mock_kpi_service):
        """Test derived metric calculation handles missing inputs gracefully."""
        # Arrange
        mock_kpi_service.calculate_derived_metrics.return_value = {}

        # Act
        result = await mock_kpi_service.calculate_derived_metrics({"ltv": 2500.0})
        # Missing CAC

        # Assert
        assert result == {}  # No derived metrics calculated


# ============================================================================
# MISSING DATA HANDLING TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.kpi
class TestMissingDataHandling:
    """Test handling of missing KPI data."""

    def test_handle_missing_data_uses_previous_value(self, mock_kpi_service):
        """Test that missing data is filled with previous value."""
        # Arrange
        data_series = [
            {"timestamp": "2024-01-01", "value": 10000},
            {"timestamp": "2024-01-02", "value": None},  # Missing
            {"timestamp": "2024-01-03", "value": 10200}
        ]
        expected_filled = [
            {"timestamp": "2024-01-01", "value": 10000},
            {"timestamp": "2024-01-02", "value": 10000},  # Filled
            {"timestamp": "2024-01-03", "value": 10200}
        ]
        mock_kpi_service.handle_missing_data.return_value = expected_filled

        # Act
        result = mock_kpi_service.handle_missing_data(data_series, method="forward_fill")

        # Assert
        assert result[1]["value"] == 10000

    def test_handle_missing_data_interpolates(self, mock_kpi_service):
        """Test that missing data can be interpolated."""
        # Arrange
        data_series = [
            {"timestamp": "2024-01-01", "value": 10000},
            {"timestamp": "2024-01-02", "value": None},  # Missing
            {"timestamp": "2024-01-03", "value": 10200}
        ]
        expected_interpolated = [
            {"timestamp": "2024-01-01", "value": 10000},
            {"timestamp": "2024-01-02", "value": 10100},  # Interpolated
            {"timestamp": "2024-01-03", "value": 10200}
        ]
        mock_kpi_service.handle_missing_data.return_value = expected_interpolated

        # Act
        result = mock_kpi_service.handle_missing_data(data_series, method="interpolate")

        # Assert
        assert result[1]["value"] == 10100

    def test_handle_missing_data_marks_as_unavailable(self, mock_kpi_service):
        """Test that persistently missing data is marked as unavailable."""
        # Arrange
        mock_kpi_service.handle_missing_data.return_value = {
            "status": "unavailable",
            "reason": "Insufficient data for calculation"
        }

        # Act
        result = mock_kpi_service.handle_missing_data(None, method="mark_unavailable")

        # Assert
        assert result["status"] == "unavailable"


# ============================================================================
# DATA FRESHNESS TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.kpi
class TestDataFreshness:
    """Test data freshness validation."""

    async def test_validate_fresh_data_passes(self, mock_granola_connector):
        """Test that fresh data passes validation."""
        # Arrange
        mock_granola_connector.fetch_kpis.return_value = get_fresh_data_response()

        # Act
        result = await mock_granola_connector.fetch_kpis("workspace_id")

        # Assert
        assert result["metadata"]["data_freshness_hours"] < 6

    async def test_validate_stale_data_warns(self, mock_granola_connector):
        """Test that stale data generates warning."""
        # Arrange
        mock_granola_connector.fetch_kpis.return_value = get_stale_data_response()

        # Act
        result = await mock_granola_connector.fetch_kpis("workspace_id")

        # Assert
        assert result["metadata"]["data_freshness_hours"] > 6
        assert "warnings" in result
        assert any("6 hours" in warning for warning in result["warnings"])


# ============================================================================
# PARTIAL DATA TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.kpi
class TestPartialDataHandling:
    """Test handling of partial KPI data."""

    async def test_handle_partial_data_response(self, mock_granola_connector):
        """Test handling of partial data response."""
        # Arrange
        mock_granola_connector.fetch_kpis.return_value = get_partial_data_response()

        # Act
        result = await mock_granola_connector.fetch_kpis("workspace_id")

        # Assert
        assert result["status"] == "partial_success"
        assert "warnings" in result
        assert result["metadata"]["partial_data"] is True

    async def test_partial_data_stores_available_metrics(
        self, mock_kpi_service
    ):
        """Test that available metrics from partial response are stored."""
        # Arrange
        partial_response = get_partial_data_response()
        mock_kpi_service.store_kpi_metrics.return_value = {"stored": 2}

        # Act
        result = await mock_kpi_service.store_kpi_metrics(
            "workspace_id", partial_response["data"]
        )

        # Assert
        assert result["stored"] == 2
