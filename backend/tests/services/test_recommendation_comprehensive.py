"""
Comprehensive tests for Recommendation Service
Covers all major code paths, edge cases, and error scenarios
Target: 100% coverage of recommendation_service.py
"""
import pytest
from uuid import uuid4, UUID
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from app.services.recommendation_service import RecommendationService
from app.models.recommendation import (
    GenerateRecommendationRequest,
    RecommendationType,
    RecommendationPriority,
    RecommendationStatus,
    ImpactLevel,
    RecommendationContext
)


@pytest.fixture
def service():
    """Create service with mocked dependencies"""
    mock_supabase = Mock()
    mock_supabase.table = Mock()

    with patch('app.services.recommendation_service.RecommendationService.__init__', lambda self: None):
        service = RecommendationService()
        service.supabase = mock_supabase
        service.logger = Mock()
        service.recommendation_chain = Mock()
        return service


@pytest.fixture
def workspace_id():
    return uuid4()


@pytest.fixture
def founder_id():
    return uuid4()


@pytest.fixture
def generate_request(workspace_id, founder_id):
    """Standard recommendation generation request"""
    return GenerateRecommendationRequest(
        workspace_id=workspace_id,
        founder_id=founder_id,
        time_range_days=30,
        max_recommendations=5,
        min_confidence=0.7,
        include_metrics=None,
        include_anomalies=None,
        focus_areas=[RecommendationType.STRATEGIC, RecommendationType.OPERATIONAL]
    )


@pytest.fixture
def mock_kpi_data():
    """Sample KPI data"""
    return {
        "MRR": {"value": 50000, "timestamp": "2025-01-15T10:00:00Z"},
        "CAC": {"value": 250, "timestamp": "2025-01-15T10:00:00Z"},
        "Churn Rate": {"value": 0.05, "timestamp": "2025-01-15T10:00:00Z"}
    }


@pytest.fixture
def mock_anomalies():
    """Sample anomalies"""
    return [
        {
            "id": str(uuid4()),
            "metric_id": str(uuid4()),
            "anomaly_type": "spike",
            "severity": "high",
            "detected_at": "2025-01-14T10:00:00Z",
            "expected_value": 100,
            "actual_value": 200
        },
        {
            "id": str(uuid4()),
            "metric_id": str(uuid4()),
            "anomaly_type": "drop",
            "severity": "medium",
            "detected_at": "2025-01-13T10:00:00Z",
            "expected_value": 50,
            "actual_value": 30
        }
    ]


@pytest.fixture
def mock_trends():
    """Sample trends"""
    return [
        {
            "id": str(uuid4()),
            "metric_id": str(uuid4()),
            "direction": "up",
            "period": "MoM",
            "percentage_change": 15.5,
            "is_significant": True
        },
        {
            "id": str(uuid4()),
            "metric_id": str(uuid4()),
            "direction": "down",
            "period": "WoW",
            "percentage_change": -8.2,
            "is_significant": True
        }
    ]


@pytest.fixture
def mock_llm_recommendations():
    """Sample LLM-generated recommendations"""
    return [
        {
            "title": "Optimize customer acquisition strategy",
            "type": "strategic",
            "priority": "high",
            "description": "CAC has increased 20% over the past month. Consider focusing on higher-converting channels.",
            "confidence": 0.85,
            "expected_impact": "high",
            "actionable_steps": [
                "Analyze channel performance",
                "Reallocate budget to top performers",
                "Implement A/B testing"
            ],
            "success_metrics": ["CAC reduction by 15%", "Conversion rate improvement"],
            "estimated_effort": "2-3 weeks",
            "estimated_cost": "$5,000"
        },
        {
            "title": "Address churn rate increase",
            "type": "operational",
            "priority": "high",
            "description": "Churn rate anomaly detected. Immediate action needed to retain customers.",
            "confidence": 0.92,
            "expected_impact": "critical",
            "actionable_steps": [
                "Conduct customer interviews",
                "Identify common churn reasons",
                "Implement retention program"
            ],
            "success_metrics": ["Reduce churn by 20%", "Increase NPS by 10 points"],
            "estimated_effort": "1-2 months"
        },
        {
            "title": "Scale successful marketing initiatives",
            "type": "growth",
            "priority": "medium",
            "description": "MRR growth trending positively. Capitalize on momentum by scaling what's working.",
            "confidence": 0.78,
            "expected_impact": "medium",
            "actionable_steps": [
                "Identify top growth drivers",
                "Increase investment in successful channels",
                "Expand target market"
            ],
            "success_metrics": ["30% MRR growth in Q2"],
            "estimated_effort": "4-6 weeks",
            "estimated_cost": "$10,000"
        },
        {
            "title": "Improve product engagement metrics",
            "type": "product",
            "priority": "low",
            "description": "User engagement stable but could be optimized for better retention.",
            "confidence": 0.65,  # Below threshold
            "expected_impact": "low",
            "actionable_steps": ["Add new features", "Improve UX"],
            "success_metrics": ["10% engagement increase"]
        }
    ]


# ==================== MAIN RECOMMENDATION GENERATION TESTS ====================

@pytest.mark.asyncio
async def test_generate_recommendations_success(
    service,
    generate_request,
    mock_kpi_data,
    mock_anomalies,
    mock_trends,
    mock_llm_recommendations
):
    """Test successful recommendation generation"""
    # Mock context building
    with patch.object(service, '_build_context', new_callable=AsyncMock) as mock_build:
        mock_context = RecommendationContext(
            kpi_data=mock_kpi_data,
            anomalies=mock_anomalies,
            trends=mock_trends,
            recent_meetings=[],
            sentiment_analysis={},
            historical_recommendations=[]
        )
        mock_build.return_value = mock_context

        # Mock recommendation chain
        service.recommendation_chain.generate_recommendations = AsyncMock(
            return_value=mock_llm_recommendations
        )

        # Mock database insert
        service.supabase.table.return_value.insert.return_value.execute.return_value = Mock(
            data=[{"id": str(uuid4()), **mock_llm_recommendations[0]}]
        )

        recommendations = await service.generate_recommendations(generate_request)

        # Should filter out low confidence and wrong focus areas
        assert len(recommendations) > 0
        assert all(r.confidence_score >= 0.7 for r in recommendations)
        # Should filter by focus areas
        assert all(
            r.recommendation_type in [RecommendationType.STRATEGIC, RecommendationType.OPERATIONAL]
            for r in recommendations
        )


@pytest.mark.asyncio
async def test_generate_recommendations_filters_by_confidence(
    service,
    generate_request,
    mock_llm_recommendations
):
    """Test that recommendations below confidence threshold are filtered"""
    generate_request.min_confidence = 0.8

    with patch.object(service, '_build_context', new_callable=AsyncMock) as mock_build:
        mock_build.return_value = RecommendationContext()

        service.recommendation_chain.generate_recommendations = AsyncMock(
            return_value=mock_llm_recommendations
        )

        service.supabase.table.return_value.insert.return_value.execute.return_value = Mock(
            data=[{"id": str(uuid4())}]
        )

        recommendations = await service.generate_recommendations(generate_request)

        # Only recommendations with confidence >= 0.8 should be included
        assert all(r.confidence_score >= 0.8 for r in recommendations)


@pytest.mark.asyncio
async def test_generate_recommendations_filters_by_focus_areas(
    service,
    workspace_id,
    founder_id,
    mock_llm_recommendations
):
    """Test filtering recommendations by focus areas"""
    request = GenerateRecommendationRequest(
        workspace_id=workspace_id,
        founder_id=founder_id,
        focus_areas=[RecommendationType.STRATEGIC]  # Only strategic
    )

    with patch.object(service, '_build_context', new_callable=AsyncMock) as mock_build:
        mock_build.return_value = RecommendationContext()

        service.recommendation_chain.generate_recommendations = AsyncMock(
            return_value=mock_llm_recommendations
        )

        service.supabase.table.return_value.insert.return_value.execute.return_value = Mock(
            data=[{"id": str(uuid4())}]
        )

        recommendations = await service.generate_recommendations(request)

        # Should only have strategic recommendations
        assert all(r.recommendation_type == RecommendationType.STRATEGIC for r in recommendations)


@pytest.mark.asyncio
async def test_generate_recommendations_no_focus_areas(
    service,
    workspace_id,
    founder_id,
    mock_llm_recommendations
):
    """Test generating recommendations without focus area filter"""
    request = GenerateRecommendationRequest(
        workspace_id=workspace_id,
        founder_id=founder_id,
        focus_areas=None  # No filter
    )

    with patch.object(service, '_build_context', new_callable=AsyncMock) as mock_build:
        mock_build.return_value = RecommendationContext()

        service.recommendation_chain.generate_recommendations = AsyncMock(
            return_value=mock_llm_recommendations
        )

        service.supabase.table.return_value.insert.return_value.execute.return_value = Mock(
            data=[{"id": str(uuid4())}]
        )

        recommendations = await service.generate_recommendations(request)

        # Should include all types that meet confidence threshold
        assert len(recommendations) > 0


@pytest.mark.asyncio
async def test_generate_recommendations_handles_errors(
    service,
    generate_request
):
    """Test error handling during recommendation generation"""
    with patch.object(service, '_build_context', new_callable=AsyncMock) as mock_build:
        mock_build.side_effect = Exception("Context building failed")

        recommendations = await service.generate_recommendations(generate_request)

        # Should return empty list on error
        assert recommendations == []


@pytest.mark.asyncio
async def test_generate_recommendations_llm_error(
    service,
    generate_request
):
    """Test handling LLM provider error"""
    with patch.object(service, '_build_context', new_callable=AsyncMock) as mock_build:
        mock_build.return_value = RecommendationContext()

        service.recommendation_chain.generate_recommendations = AsyncMock(
            side_effect=Exception("LLM API error")
        )

        recommendations = await service.generate_recommendations(generate_request)

        # Should return empty list on LLM error
        assert recommendations == []


# ==================== CONTEXT BUILDING TESTS ====================

@pytest.mark.asyncio
async def test_build_context_complete(
    service,
    workspace_id,
    founder_id,
    mock_kpi_data,
    mock_anomalies,
    mock_trends
):
    """Test building complete recommendation context"""
    with patch.object(service, '_get_kpi_data', new_callable=AsyncMock) as mock_kpi:
        with patch.object(service, '_get_anomalies', new_callable=AsyncMock) as mock_anom:
            with patch.object(service, '_get_trends', new_callable=AsyncMock) as mock_trend:
                with patch.object(service, '_get_recent_meetings', new_callable=AsyncMock) as mock_meetings:
                    with patch.object(service, '_get_sentiment_analysis', new_callable=AsyncMock) as mock_sentiment:
                        with patch.object(service, '_get_historical_recommendations', new_callable=AsyncMock) as mock_hist:
                            mock_kpi.return_value = mock_kpi_data
                            mock_anom.return_value = mock_anomalies
                            mock_trend.return_value = mock_trends
                            mock_meetings.return_value = []
                            mock_sentiment.return_value = {"overall": "positive"}
                            mock_hist.return_value = []

                            context = await service._build_context(
                                workspace_id=workspace_id,
                                founder_id=founder_id,
                                time_range_days=30
                            )

                            assert context.kpi_data == mock_kpi_data
                            assert context.anomalies == mock_anomalies
                            assert context.trends == mock_trends
                            assert context.sentiment_analysis == {"overall": "positive"}


@pytest.mark.asyncio
async def test_build_context_with_specific_metrics(
    service,
    workspace_id,
    founder_id
):
    """Test building context with specific metric IDs"""
    metric_ids = [uuid4(), uuid4()]

    with patch.object(service, '_get_kpi_data', new_callable=AsyncMock) as mock_kpi:
        with patch.object(service, '_get_anomalies', new_callable=AsyncMock) as mock_anom:
            with patch.object(service, '_get_trends', new_callable=AsyncMock) as mock_trend:
                with patch.object(service, '_get_recent_meetings', new_callable=AsyncMock) as mock_meetings:
                    with patch.object(service, '_get_sentiment_analysis', new_callable=AsyncMock) as mock_sentiment:
                        with patch.object(service, '_get_historical_recommendations', new_callable=AsyncMock) as mock_hist:
                            mock_kpi.return_value = {}
                            mock_anom.return_value = []
                            mock_trend.return_value = []
                            mock_meetings.return_value = []
                            mock_sentiment.return_value = {}
                            mock_hist.return_value = []

                            await service._build_context(
                                workspace_id=workspace_id,
                                founder_id=founder_id,
                                time_range_days=30,
                                include_metrics=metric_ids
                            )

                            # Verify metrics were passed to _get_kpi_data
                            mock_kpi.assert_called_once_with(workspace_id, metric_ids)


@pytest.mark.asyncio
async def test_build_context_handles_errors(
    service,
    workspace_id,
    founder_id
):
    """Test that context building handles individual component errors"""
    with patch.object(service, '_get_kpi_data', new_callable=AsyncMock) as mock_kpi:
        mock_kpi.side_effect = Exception("KPI fetch failed")

        with patch.object(service, '_get_anomalies', new_callable=AsyncMock) as mock_anom:
            with patch.object(service, '_get_trends', new_callable=AsyncMock) as mock_trend:
                with patch.object(service, '_get_recent_meetings', new_callable=AsyncMock) as mock_meetings:
                    with patch.object(service, '_get_sentiment_analysis', new_callable=AsyncMock) as mock_sentiment:
                        with patch.object(service, '_get_historical_recommendations', new_callable=AsyncMock) as mock_hist:
                            mock_anom.return_value = []
                            mock_trend.return_value = []
                            mock_meetings.return_value = []
                            mock_sentiment.return_value = {}
                            mock_hist.return_value = []

                            # Should return empty context on error
                            context = await service._build_context(
                                workspace_id=workspace_id,
                                founder_id=founder_id,
                                time_range_days=30
                            )

                            assert isinstance(context, RecommendationContext)


# ==================== DATA FETCHING TESTS ====================

@pytest.mark.asyncio
async def test_get_kpi_data_success(service, workspace_id):
    """Test successful KPI data fetching"""
    mock_metrics = [
        {"id": str(uuid4()), "name": "MRR", "is_active": True},
        {"id": str(uuid4()), "name": "CAC", "is_active": True}
    ]

    service.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
        data=mock_metrics
    )

    # Mock latest value queries
    def mock_latest_value(metric_id):
        return Mock(data=[{"value": 1000, "timestamp": "2025-01-15T10:00:00Z"}])

    service.supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.side_effect = [
        mock_latest_value(m["id"]) for m in mock_metrics
    ]

    result = await service._get_kpi_data(workspace_id)

    assert "MRR" in result
    assert "CAC" in result


@pytest.mark.asyncio
async def test_get_kpi_data_with_metric_ids(service, workspace_id):
    """Test fetching specific metrics by ID"""
    metric_ids = [uuid4(), uuid4()]

    service.supabase.table.return_value.select.return_value.eq.return_value.in_.return_value.execute.return_value = Mock(
        data=[]
    )

    await service._get_kpi_data(workspace_id, metric_ids)

    # Verify in_ was called with metric IDs
    service.supabase.table.return_value.select.return_value.eq.return_value.in_.assert_called_once()


@pytest.mark.asyncio
async def test_get_kpi_data_error_handling(service, workspace_id):
    """Test KPI data fetch error handling"""
    service.supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception(
        "Database error"
    )

    result = await service._get_kpi_data(workspace_id)

    assert result == {}


@pytest.mark.asyncio
async def test_get_anomalies_success(service, workspace_id):
    """Test successful anomaly fetching"""
    start_date = datetime.utcnow() - timedelta(days=7)
    mock_anomalies = [
        {"id": str(uuid4()), "severity": "high"},
        {"id": str(uuid4()), "severity": "medium"}
    ]

    service.supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = Mock(
        data=mock_anomalies
    )

    result = await service._get_anomalies(workspace_id, start_date)

    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_anomalies_with_ids(service, workspace_id):
    """Test fetching specific anomalies by ID"""
    start_date = datetime.utcnow() - timedelta(days=7)
    anomaly_ids = [uuid4(), uuid4()]

    service.supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.in_.return_value.execute.return_value = Mock(
        data=[]
    )

    await service._get_anomalies(workspace_id, start_date, anomaly_ids)


@pytest.mark.asyncio
async def test_get_anomalies_error_handling(service, workspace_id):
    """Test anomaly fetch error handling"""
    start_date = datetime.utcnow() - timedelta(days=7)

    service.supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.side_effect = Exception(
        "Database error"
    )

    result = await service._get_anomalies(workspace_id, start_date)

    assert result == []


@pytest.mark.asyncio
async def test_get_trends_success(service, workspace_id):
    """Test successful trend fetching"""
    start_date = datetime.utcnow() - timedelta(days=30)
    mock_trends = [
        {"id": str(uuid4()), "direction": "up", "is_significant": True},
        {"id": str(uuid4()), "direction": "down", "is_significant": True}
    ]

    service.supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.eq.return_value.execute.return_value = Mock(
        data=mock_trends
    )

    result = await service._get_trends(workspace_id, start_date)

    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_trends_error_handling(service, workspace_id):
    """Test trend fetch error handling"""
    start_date = datetime.utcnow() - timedelta(days=30)

    service.supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.eq.return_value.execute.side_effect = Exception(
        "Database error"
    )

    result = await service._get_trends(workspace_id, start_date)

    assert result == []


@pytest.mark.asyncio
async def test_get_recent_meetings_success(service, workspace_id, founder_id):
    """Test successful meeting fetching"""
    mock_meetings = [
        {"id": str(uuid4()), "title": "Sprint Planning"},
        {"id": str(uuid4()), "title": "Product Review"}
    ]

    service.supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = Mock(
        data=mock_meetings
    )

    result = await service._get_recent_meetings(workspace_id, founder_id, days=7)

    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_recent_meetings_error_handling(service, workspace_id, founder_id):
    """Test meeting fetch error handling"""
    service.supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.side_effect = Exception(
        "Database error"
    )

    result = await service._get_recent_meetings(workspace_id, founder_id)

    assert result == []


@pytest.mark.asyncio
async def test_get_sentiment_analysis(service, workspace_id, founder_id):
    """Test sentiment analysis retrieval"""
    result = await service._get_sentiment_analysis(workspace_id, founder_id)

    # Currently returns placeholder
    assert result == {"overall": "neutral"}


@pytest.mark.asyncio
async def test_get_historical_recommendations_success(service, workspace_id, founder_id):
    """Test successful historical recommendations fetching"""
    mock_recs = [
        {"id": str(uuid4()), "title": "Old recommendation 1"},
        {"id": str(uuid4()), "title": "Old recommendation 2"}
    ]

    service.supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.execute.return_value = Mock(
        data=mock_recs
    )

    result = await service._get_historical_recommendations(workspace_id, founder_id, days=90)

    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_historical_recommendations_error_handling(service, workspace_id, founder_id):
    """Test historical recommendations fetch error handling"""
    service.supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.execute.side_effect = Exception(
        "Database error"
    )

    result = await service._get_historical_recommendations(workspace_id, founder_id)

    assert result == []


# ==================== RECOMMENDATION CREATION TESTS ====================

@pytest.mark.asyncio
async def test_create_recommendation_success(service, workspace_id, founder_id):
    """Test successful recommendation creation"""
    rec_data = {
        "title": "Test Recommendation",
        "type": "strategic",
        "priority": "high",
        "description": "Test description",
        "confidence": 0.85,
        "expected_impact": "high",
        "actionable_steps": ["Step 1", "Step 2"],
        "success_metrics": ["Metric 1"]
    }

    context = RecommendationContext()

    service.supabase.table.return_value.insert.return_value.execute.return_value = Mock(
        data=[{"id": str(uuid4()), **rec_data}]
    )

    result = await service._create_recommendation(
        workspace_id=workspace_id,
        founder_id=founder_id,
        rec_data=rec_data,
        context=context
    )

    assert result is not None


@pytest.mark.asyncio
async def test_create_recommendation_database_error(service, workspace_id, founder_id):
    """Test recommendation creation with database error"""
    rec_data = {
        "title": "Test",
        "type": "strategic",
        "priority": "high",
        "description": "Test",
        "confidence": 0.85,
        "expected_impact": "high",
        "actionable_steps": [],
        "success_metrics": []
    }

    context = RecommendationContext()

    service.supabase.table.return_value.insert.return_value.execute.side_effect = Exception(
        "Insert failed"
    )

    result = await service._create_recommendation(
        workspace_id=workspace_id,
        founder_id=founder_id,
        rec_data=rec_data,
        context=context
    )

    assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
