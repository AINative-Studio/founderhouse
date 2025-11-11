"""
Comprehensive tests for Anomaly Detection Service
Covers all major code paths, edge cases, and error scenarios
Target: 100% coverage of anomaly_detection_service.py
"""
import pytest
from uuid import uuid4, UUID
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from app.services.anomaly_detection_service import AnomalyDetectionService
from app.models.anomaly import DetectionMethod, MetricAnalysis


@pytest.fixture
def service():
    """Create service with mocked dependencies"""
    mock_supabase = Mock()
    mock_supabase.table = Mock()

    with patch('app.services.anomaly_detection_service.AnomalyDetectionService.__init__', lambda self: None):
        service = AnomalyDetectionService()
        service.supabase = mock_supabase
        service.logger = Mock()

        # Initialize detectors
        from app.algorithms.zscore_detector import ZScoreDetector
        from app.algorithms.iqr_detector import IQRDetector
        from app.algorithms.trend_analyzer import TrendAnalyzer
        from app.algorithms.seasonal_decomposition import SeasonalDecomposer

        service.zscore_detector = ZScoreDetector(threshold=3.0)
        service.iqr_detector = IQRDetector(multiplier=1.5)
        service.trend_analyzer = TrendAnalyzer(significance_threshold=0.10)
        service.seasonal_decomposer = SeasonalDecomposer(seasonal_period=7)
        return service


@pytest.fixture
def workspace_id():
    return uuid4()


@pytest.fixture
def metric_id():
    return uuid4()


@pytest.fixture
def sample_metric_data():
    """Sample metric metadata"""
    return {
        "id": str(uuid4()),
        "name": "Monthly Revenue",
        "display_name": "Monthly Recurring Revenue",
        "category": "financial",
        "unit": "USD"
    }


@pytest.fixture
def sample_data_points():
    """Sample time series data points"""
    base_time = datetime(2025, 1, 1)
    return [
        {
            "id": str(uuid4()),
            "value": 100 + i * 10,
            "timestamp": (base_time + timedelta(days=i)).isoformat()
        }
        for i in range(30)
    ]


@pytest.fixture
def sample_data_with_anomalies():
    """Sample data with clear anomalies"""
    base_time = datetime(2025, 1, 1)
    data = []
    for i in range(30):
        value = 100
        if i == 10:
            value = 300  # Spike anomaly
        elif i == 20:
            value = 20   # Drop anomaly
        data.append({
            "id": str(uuid4()),
            "value": value,
            "timestamp": (base_time + timedelta(days=i)).isoformat()
        })
    return data


# ==================== METRIC ANALYSIS TESTS ====================

@pytest.mark.asyncio
async def test_analyze_metric_success(
    service,
    metric_id,
    workspace_id,
    sample_metric_data,
    sample_data_points
):
    """Test successful metric analysis"""
    # Mock metric retrieval
    service.supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
        data=sample_metric_data
    )

    # Mock data points retrieval
    with patch.object(service, '_get_metric_data', new_callable=AsyncMock) as mock_get_data:
        mock_get_data.return_value = sample_data_points

        # Mock database saves
        service.supabase.table.return_value.insert.return_value.execute.return_value = Mock(
            data=[{"id": str(uuid4())}]
        )

        analysis = await service.analyze_metric(
            metric_id=metric_id,
            workspace_id=workspace_id,
            days_back=30
        )

        assert analysis.metric_id == metric_id
        assert analysis.metric_name == "Monthly Revenue"
        assert analysis.current_value > 0
        assert "statistics" in analysis.model_dump()


@pytest.mark.asyncio
async def test_analyze_metric_not_found(service, metric_id, workspace_id):
    """Test analysis when metric not found"""
    service.supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
        data=None
    )

    with pytest.raises(ValueError, match="not found"):
        await service.analyze_metric(
            metric_id=metric_id,
            workspace_id=workspace_id
        )


@pytest.mark.asyncio
async def test_analyze_metric_insufficient_data(
    service,
    metric_id,
    workspace_id,
    sample_metric_data
):
    """Test analysis with insufficient data points"""
    service.supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
        data=sample_metric_data
    )

    with patch.object(service, '_get_metric_data', new_callable=AsyncMock) as mock_get_data:
        mock_get_data.return_value = []  # No data

        analysis = await service.analyze_metric(
            metric_id=metric_id,
            workspace_id=workspace_id
        )

        assert len(analysis.anomalies) == 0
        assert len(analysis.trends) == 0
        assert "Insufficient data" in analysis.insights


@pytest.mark.asyncio
async def test_analyze_metric_with_custom_detection_methods(
    service,
    metric_id,
    workspace_id,
    sample_metric_data,
    sample_data_points
):
    """Test metric analysis with specific detection methods"""
    service.supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
        data=sample_metric_data
    )

    with patch.object(service, '_get_metric_data', new_callable=AsyncMock) as mock_get_data:
        mock_get_data.return_value = sample_data_points

        service.supabase.table.return_value.insert.return_value.execute.return_value = Mock(
            data=[{"id": str(uuid4())}]
        )

        analysis = await service.analyze_metric(
            metric_id=metric_id,
            workspace_id=workspace_id,
            detection_methods=[DetectionMethod.ZSCORE]
        )

        assert analysis is not None


# ==================== ANOMALY DETECTION TESTS ====================

@pytest.mark.asyncio
async def test_detect_anomalies_zscore(service, metric_id, workspace_id):
    """Test Z-Score anomaly detection"""
    values = [100, 105, 98, 102, 300, 103, 99]  # 300 is anomaly
    timestamps = [datetime.utcnow() + timedelta(days=i) for i in range(len(values))]
    data_point_ids = [uuid4() for _ in range(len(values))]

    service.supabase.table.return_value.insert.return_value.execute.return_value = Mock(
        data=[{"id": str(uuid4())}]
    )

    anomalies = await service.detect_anomalies(
        metric_id=metric_id,
        workspace_id=workspace_id,
        values=values,
        timestamps=timestamps,
        data_point_ids=data_point_ids,
        methods=[DetectionMethod.ZSCORE]
    )

    # Should detect the spike at value 300
    assert len(anomalies) > 0


@pytest.mark.asyncio
async def test_detect_anomalies_iqr(service, metric_id, workspace_id):
    """Test IQR anomaly detection"""
    values = [50, 52, 48, 51, 200, 49, 53]  # 200 is outlier
    timestamps = [datetime.utcnow() + timedelta(days=i) for i in range(len(values))]
    data_point_ids = [uuid4() for _ in range(len(values))]

    service.supabase.table.return_value.insert.return_value.execute.return_value = Mock(
        data=[{"id": str(uuid4())}]
    )

    anomalies = await service.detect_anomalies(
        metric_id=metric_id,
        workspace_id=workspace_id,
        values=values,
        timestamps=timestamps,
        data_point_ids=data_point_ids,
        methods=[DetectionMethod.IQR]
    )

    assert len(anomalies) > 0


@pytest.mark.asyncio
async def test_detect_anomalies_multiple_methods(service, metric_id, workspace_id):
    """Test detection using multiple methods"""
    values = [100] * 10 + [500] + [100] * 10  # Clear anomaly
    timestamps = [datetime.utcnow() + timedelta(days=i) for i in range(len(values))]
    data_point_ids = [uuid4() for _ in range(len(values))]

    service.supabase.table.return_value.insert.return_value.execute.return_value = Mock(
        data=[{"id": str(uuid4())}]
    )

    anomalies = await service.detect_anomalies(
        metric_id=metric_id,
        workspace_id=workspace_id,
        values=values,
        timestamps=timestamps,
        data_point_ids=data_point_ids,
        methods=[DetectionMethod.ZSCORE, DetectionMethod.IQR]
    )

    # Both methods should detect the anomaly, but should not duplicate
    assert len(anomalies) > 0


@pytest.mark.asyncio
async def test_detect_anomalies_no_auto_save(service, metric_id, workspace_id):
    """Test anomaly detection without auto-saving"""
    values = [100, 105, 300, 102]
    timestamps = [datetime.utcnow() + timedelta(days=i) for i in range(len(values))]
    data_point_ids = [uuid4() for _ in range(len(values))]

    anomalies = await service.detect_anomalies(
        metric_id=metric_id,
        workspace_id=workspace_id,
        values=values,
        timestamps=timestamps,
        data_point_ids=data_point_ids,
        auto_save=False
    )

    # Should still return anomalies, just not save them
    assert isinstance(anomalies, list)


@pytest.mark.asyncio
async def test_detect_anomalies_handles_errors(service, metric_id, workspace_id):
    """Test error handling during anomaly detection"""
    values = [100, 105, 102]
    timestamps = [datetime.utcnow() + timedelta(days=i) for i in range(len(values))]
    data_point_ids = [uuid4() for _ in range(len(values))]

    # Mock detector to raise error
    with patch.object(service.zscore_detector, 'detect', side_effect=Exception("Detection failed")):
        anomalies = await service.detect_anomalies(
            metric_id=metric_id,
            workspace_id=workspace_id,
            values=values,
            timestamps=timestamps,
            data_point_ids=data_point_ids,
            methods=[DetectionMethod.ZSCORE]
        )

        # Should return empty list on error
        assert anomalies == []


# ==================== TREND ANALYSIS TESTS ====================

@pytest.mark.asyncio
async def test_analyze_trends_success(service, metric_id, workspace_id):
    """Test successful trend analysis"""
    # Create upward trend
    values = [100 + i * 10 for i in range(30)]
    timestamps = [datetime.utcnow() + timedelta(days=i) for i in range(30)]

    service.supabase.table.return_value.insert.return_value.execute.return_value = Mock(
        data=[{"id": str(uuid4())}]
    )

    trends = await service.analyze_trends(
        metric_id=metric_id,
        workspace_id=workspace_id,
        values=values,
        timestamps=timestamps,
        periods=["WoW", "MoM"]
    )

    # Should detect upward trend
    assert len(trends) > 0


@pytest.mark.asyncio
async def test_analyze_trends_no_significant_trends(service, metric_id, workspace_id):
    """Test trend analysis with stable data"""
    # Stable values
    values = [100] * 30
    timestamps = [datetime.utcnow() + timedelta(days=i) for i in range(30)]

    trends = await service.analyze_trends(
        metric_id=metric_id,
        workspace_id=workspace_id,
        values=values,
        timestamps=timestamps
    )

    # May not detect significant trends in stable data
    assert isinstance(trends, list)


@pytest.mark.asyncio
async def test_analyze_trends_no_auto_save(service, metric_id, workspace_id):
    """Test trend analysis without auto-saving"""
    values = [100 + i * 10 for i in range(30)]
    timestamps = [datetime.utcnow() + timedelta(days=i) for i in range(30)]

    trends = await service.analyze_trends(
        metric_id=metric_id,
        workspace_id=workspace_id,
        values=values,
        timestamps=timestamps,
        auto_save=False
    )

    assert isinstance(trends, list)


@pytest.mark.asyncio
async def test_analyze_trends_handles_errors(service, metric_id, workspace_id):
    """Test error handling during trend analysis"""
    values = [100, 105, 110]
    timestamps = [datetime.utcnow() + timedelta(days=i) for i in range(3)]

    with patch.object(service.trend_analyzer, 'analyze_trend', side_effect=Exception("Analysis failed")):
        trends = await service.analyze_trends(
            metric_id=metric_id,
            workspace_id=workspace_id,
            values=values,
            timestamps=timestamps
        )

        # Should return empty list on error
        assert trends == []


# ==================== HELPER METHOD TESTS ====================

@pytest.mark.asyncio
async def test_create_anomaly_with_save(service, metric_id, workspace_id):
    """Test creating and saving anomaly"""
    service.supabase.table.return_value.insert.return_value.execute.return_value = Mock(
        data=[{
            "id": str(uuid4()),
            "detected_at": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat()
        }]
    )

    result = await service._create_anomaly(
        metric_id=metric_id,
        workspace_id=workspace_id,
        data_point_id=uuid4(),
        anomaly_type="spike",
        severity="high",
        detection_method=DetectionMethod.ZSCORE,
        expected_value=100.0,
        actual_value=200.0,
        deviation=3.5,
        confidence=0.95,
        auto_save=True
    )

    assert result is not None


@pytest.mark.asyncio
async def test_create_anomaly_without_save(service, metric_id, workspace_id):
    """Test creating anomaly without saving"""
    result = await service._create_anomaly(
        metric_id=metric_id,
        workspace_id=workspace_id,
        data_point_id=uuid4(),
        anomaly_type="spike",
        severity="high",
        detection_method=DetectionMethod.ZSCORE,
        expected_value=100.0,
        actual_value=200.0,
        deviation=3.5,
        confidence=0.95,
        auto_save=False
    )

    assert result is not None


@pytest.mark.asyncio
async def test_create_anomaly_database_error(service, metric_id, workspace_id):
    """Test anomaly creation with database error"""
    service.supabase.table.return_value.insert.return_value.execute.side_effect = Exception(
        "Insert failed"
    )

    result = await service._create_anomaly(
        metric_id=metric_id,
        workspace_id=workspace_id,
        data_point_id=uuid4(),
        anomaly_type="spike",
        severity="high",
        detection_method=DetectionMethod.ZSCORE,
        expected_value=100.0,
        actual_value=200.0,
        deviation=3.5,
        confidence=0.95,
        auto_save=True
    )

    assert result is None


@pytest.mark.asyncio
async def test_create_trend_with_save(service, metric_id, workspace_id):
    """Test creating and saving trend"""
    service.supabase.table.return_value.insert.return_value.execute.return_value = Mock(
        data=[{
            "id": str(uuid4()),
            "created_at": datetime.utcnow().isoformat()
        }]
    )

    result = await service._create_trend(
        metric_id=metric_id,
        workspace_id=workspace_id,
        direction="up",
        period="MoM",
        start_date=datetime.utcnow() - timedelta(days=30),
        end_date=datetime.utcnow(),
        start_value=100.0,
        end_value=150.0,
        percentage_change=50.0,
        absolute_change=50.0,
        confidence=0.92,
        is_significant=True,
        auto_save=True
    )

    assert result is not None


@pytest.mark.asyncio
async def test_create_trend_without_save(service, metric_id, workspace_id):
    """Test creating trend without saving"""
    result = await service._create_trend(
        metric_id=metric_id,
        workspace_id=workspace_id,
        direction="up",
        period="WoW",
        start_date=datetime.utcnow() - timedelta(days=7),
        end_date=datetime.utcnow(),
        start_value=100.0,
        end_value=110.0,
        percentage_change=10.0,
        absolute_change=10.0,
        confidence=0.85,
        is_significant=True,
        auto_save=False
    )

    assert result is not None


@pytest.mark.asyncio
async def test_create_trend_database_error(service, metric_id, workspace_id):
    """Test trend creation with database error"""
    service.supabase.table.return_value.insert.return_value.execute.side_effect = Exception(
        "Insert failed"
    )

    result = await service._create_trend(
        metric_id=metric_id,
        workspace_id=workspace_id,
        direction="up",
        period="MoM",
        start_date=datetime.utcnow() - timedelta(days=30),
        end_date=datetime.utcnow(),
        start_value=100.0,
        end_value=150.0,
        percentage_change=50.0,
        absolute_change=50.0,
        confidence=0.92,
        is_significant=True,
        auto_save=True
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_metric_data_success(service, metric_id, workspace_id):
    """Test successful metric data retrieval"""
    start_date = datetime.utcnow() - timedelta(days=30)
    mock_data = [
        {"id": str(uuid4()), "value": 100, "timestamp": datetime.utcnow().isoformat()}
        for _ in range(30)
    ]

    service.supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.order.return_value.execute.return_value = Mock(
        data=mock_data
    )

    result = await service._get_metric_data(metric_id, workspace_id, start_date)

    assert len(result) == 30


@pytest.mark.asyncio
async def test_get_metric_data_error_handling(service, metric_id, workspace_id):
    """Test metric data retrieval error handling"""
    start_date = datetime.utcnow() - timedelta(days=30)

    service.supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.order.return_value.execute.side_effect = Exception(
        "Query failed"
    )

    result = await service._get_metric_data(metric_id, workspace_id, start_date)

    assert result == []


def test_empty_analysis(service, metric_id):
    """Test empty analysis generation"""
    analysis = service._empty_analysis(metric_id, "Test Metric")

    assert analysis.metric_id == metric_id
    assert analysis.metric_name == "Test Metric"
    assert len(analysis.anomalies) == 0
    assert len(analysis.trends) == 0
    assert "Insufficient data" in analysis.insights


def test_generate_insights(service):
    """Test insight generation"""
    metric = {
        "display_name": "Monthly Revenue",
        "category": "financial"
    }

    values = [100, 105, 110, 115]

    anomalies = []
    trends = []
    statistics = {"mean": 107.5, "std": 6.45, "min": 100, "max": 115}

    insights = service._generate_insights(metric, values, anomalies, trends, statistics)

    assert isinstance(insights, list)


def test_generate_insights_with_critical_anomalies(service):
    """Test insight generation with critical anomalies"""
    from app.models.anomaly import AnomalyResponse

    metric = {"display_name": "User Signups"}
    values = [100, 105, 110]

    # Create mock critical anomaly
    anomaly = Mock(spec=AnomalyResponse)
    anomaly.severity = Mock()
    anomaly.severity.value = "critical"

    anomalies = [anomaly, anomaly]
    trends = []
    statistics = {}

    insights = service._generate_insights(metric, values, anomalies, trends, statistics)

    assert len(insights) > 0
    assert any("critical" in insight.lower() for insight in insights)


def test_generate_insights_with_significant_trends(service):
    """Test insight generation with significant trends"""
    from app.models.anomaly import TrendResponse

    metric = {"display_name": "Revenue"}
    values = [100, 110, 120]

    # Create mock trend
    trend = Mock(spec=TrendResponse)
    trend.is_significant = True
    trend.direction = Mock()
    trend.direction.value = "up"
    trend.percentage_change = 20.0
    trend.period = "MoM"

    anomalies = []
    trends = [trend]
    statistics = {}

    insights = service._generate_insights(metric, values, anomalies, trends, statistics)

    assert len(insights) > 0


def test_generate_insights_with_high_volatility(service):
    """Test insight generation with high volatility"""
    metric = {"display_name": "Daily Active Users"}
    values = [100, 200, 50, 180, 90]  # High variance

    anomalies = []
    trends = []
    statistics = {"mean": 124, "std": 60}  # High CV

    insights = service._generate_insights(metric, values, anomalies, trends, statistics)

    assert len(insights) > 0


def test_generate_insights_handles_errors(service):
    """Test insight generation error handling"""
    metric = {}  # Missing required fields
    values = []
    anomalies = []
    trends = []
    statistics = {}

    insights = service._generate_insights(metric, values, anomalies, trends, statistics)

    # Should return empty list on error
    assert insights == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
