"""
Comprehensive tests for RecommendationChain
Tests recommendation generation, context formatting, and LangChain integration
"""
import pytest
import os
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from app.chains.recommendation_chain import RecommendationChain
from app.models.recommendation import RecommendationContext, RecommendationType, RecommendationPriority, ImpactLevel


@pytest.fixture
def recommendation_chain():
    """RecommendationChain instance"""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        return RecommendationChain(model_name="gpt-4o", temperature=0.7)


@pytest.fixture
def sample_context():
    """Sample recommendation context"""
    return RecommendationContext(
        kpi_data={
            "revenue": {"value": 50000, "change": "-15%"},
            "customer_count": {"value": 120, "change": "+5%"},
            "burn_rate": {"value": 80000, "change": "+20%"}
        },
        anomalies=[
            {
                "metric_name": "revenue",
                "type": "drop",
                "severity": "high",
                "deviation": -15.0
            },
            {
                "metric_name": "burn_rate",
                "type": "spike",
                "severity": "critical",
                "deviation": 20.0
            }
        ],
        trends=[
            {
                "metric_name": "customer_count",
                "direction": "up",
                "percentage_change": 5.0,
                "period": "last 30 days"
            }
        ],
        recent_meetings=[
            {
                "title": "Q4 Planning",
                "summary": "Discussed strategy for enterprise pivot and cost reduction"
            }
        ],
        sentiment_analysis={
            "overall": "concerned"
        }
    )


@pytest.fixture
def empty_context():
    """Empty recommendation context"""
    return RecommendationContext()


# ===== Context Formatting Tests =====

def test_format_context_with_data(recommendation_chain):
    """Test formatting context with data"""
    context = RecommendationContext(
        industry_benchmarks={"avg_revenue": 100000},
        historical_recommendations=[{"title": "Previous rec"}]
    )

    formatted = recommendation_chain._format_context(context)

    assert "Industry Benchmarks" in formatted
    assert "Historical Recommendations" in formatted


def test_format_context_empty(recommendation_chain):
    """Test formatting empty context"""
    context = RecommendationContext()

    formatted = recommendation_chain._format_context(context)

    assert formatted == "No additional context"


def test_format_kpi_data_complete(recommendation_chain):
    """Test formatting complete KPI data"""
    kpi_data = {
        "revenue": {"value": 50000, "change": "-15%"},
        "users": {"value": 1000, "change": "+10%"}
    }

    formatted = recommendation_chain._format_kpi_data(kpi_data)

    assert "revenue: 50000 (Change: -15%)" in formatted
    assert "users: 1000 (Change: +10%)" in formatted


def test_format_kpi_data_simple_values(recommendation_chain):
    """Test formatting simple KPI values"""
    kpi_data = {
        "revenue": 50000,
        "users": 1000
    }

    formatted = recommendation_chain._format_kpi_data(kpi_data)

    assert "revenue: 50000" in formatted
    assert "users: 1000" in formatted


def test_format_kpi_data_empty(recommendation_chain):
    """Test formatting empty KPI data"""
    formatted = recommendation_chain._format_kpi_data({})

    assert formatted == "No KPI data available"


def test_format_anomalies_with_data(recommendation_chain):
    """Test formatting anomalies"""
    anomalies = [
        {
            "metric_name": "revenue",
            "type": "drop",
            "severity": "high",
            "deviation": -15.0
        },
        {
            "metric_name": "burn_rate",
            "type": "spike",
            "severity": "critical",
            "deviation": 20.0
        }
    ]

    formatted = recommendation_chain._format_anomalies(anomalies)

    assert "revenue: drop (high severity, -15.0% deviation)" in formatted
    assert "burn_rate: spike (critical severity, 20.0% deviation)" in formatted


def test_format_anomalies_empty(recommendation_chain):
    """Test formatting empty anomalies"""
    formatted = recommendation_chain._format_anomalies([])

    assert formatted == "No anomalies detected"


def test_format_anomalies_limits_to_ten(recommendation_chain):
    """Test that anomalies are limited to top 10"""
    anomalies = [{"metric_name": f"metric_{i}", "type": "drop", "severity": "low", "deviation": -5.0} for i in range(20)]

    formatted = recommendation_chain._format_anomalies(anomalies)

    # Should only include 10
    line_count = len(formatted.split("\n"))
    assert line_count <= 10


def test_format_trends_with_data(recommendation_chain):
    """Test formatting trends"""
    trends = [
        {
            "metric_name": "revenue",
            "direction": "up",
            "percentage_change": 15.0,
            "period": "last 30 days"
        },
        {
            "metric_name": "users",
            "direction": "down",
            "percentage_change": -5.0,
            "period": "last week"
        }
    ]

    formatted = recommendation_chain._format_trends(trends)

    assert "revenue: up 15.0% last 30 days" in formatted
    assert "users: down 5.0% last week" in formatted


def test_format_trends_empty(recommendation_chain):
    """Test formatting empty trends"""
    formatted = recommendation_chain._format_trends([])

    assert formatted == "No significant trends detected"


def test_format_trends_limits_to_ten(recommendation_chain):
    """Test that trends are limited to top 10"""
    trends = [{"metric_name": f"metric_{i}", "direction": "up", "percentage_change": 5.0, "period": "week"} for i in range(20)]

    formatted = recommendation_chain._format_trends(trends)

    line_count = len(formatted.split("\n"))
    assert line_count <= 10


def test_format_recent_context_with_meetings(recommendation_chain):
    """Test formatting recent context with meetings"""
    meetings = [
        {"title": "Q4 Planning", "summary": "Discussed strategy for growth"},
        {"title": "Budget Review", "summary": "Reviewed expenses and identified savings"}
    ]
    sentiment = {"overall": "positive"}

    formatted = recommendation_chain._format_recent_context(meetings, sentiment)

    assert "Recent Meetings: 2 meetings" in formatted
    assert "Q4 Planning" in formatted
    assert "Overall Sentiment: positive" in formatted


def test_format_recent_context_empty(recommendation_chain):
    """Test formatting empty recent context"""
    formatted = recommendation_chain._format_recent_context([], None)

    assert formatted == "No recent context"


def test_format_recent_context_truncates_summaries(recommendation_chain):
    """Test that long summaries are truncated"""
    meetings = [
        {"title": "Long Meeting", "summary": "A" * 200}
    ]

    formatted = recommendation_chain._format_recent_context(meetings)

    # Should truncate to ~100 chars
    assert len(formatted) < 300


def test_format_recent_context_limits_meetings(recommendation_chain):
    """Test that meetings are limited to 5"""
    meetings = [{"title": f"Meeting {i}", "summary": f"Summary {i}"} for i in range(10)]

    formatted = recommendation_chain._format_recent_context(meetings)

    # Should only include 5 meetings (plus header)
    meeting_count = formatted.count("Meeting")
    assert meeting_count <= 6  # 5 meetings + "Recent Meetings" text


# ===== Recommendation Generation Tests =====

@pytest.mark.asyncio
async def test_generate_recommendations_basic(recommendation_chain, sample_context):
    """Test basic recommendation generation"""
    with patch.object(recommendation_chain.chain, 'invoke', return_value={
            "recommendations": [
                {
                    "title": "Reduce operational costs",
                    "type": "operational",
                    "priority": "urgent",
                    "description": "Implement cost-cutting measures to reduce burn rate",
                    "confidence": 0.85,
                    "expected_impact": "high",
                    "actionable_steps": ["Audit expenses", "Renegotiate contracts"],
                    "success_metrics": ["20% cost reduction", "Extended runway"],
                    "estimated_effort": "2 weeks",
                    "estimated_cost": None
                }
            ]
        }):
        result = await recommendation_chain.generate_recommendations(sample_context)

        assert len(result) == 1
        assert result[0]["title"] == "Reduce operational costs"
        assert result[0]["type"] == "operational"
        assert result[0]["priority"] == "urgent"
        mock_invoke.assert_called_once()


@pytest.mark.asyncio
async def test_generate_recommendations_multiple(recommendation_chain, sample_context):
    """Test generating multiple recommendations"""
    with patch.object(recommendation_chain.chain, 'ainvoke', new_callable=AsyncMock) as mock_invoke:
        mock_invoke.return_value = {
            "recommendations": [
                {
                    "title": "Pivot to B2B",
                    "type": "strategic",
                    "priority": "high",
                    "description": "Focus on enterprise customers",
                    "confidence": 0.8,
                    "expected_impact": "transformational",
                    "actionable_steps": ["Market research", "Update positioning"],
                    "success_metrics": ["ARR growth"],
                    "estimated_effort": "3 months",
                    "estimated_cost": 50000
                },
                {
                    "title": "Optimize pricing",
                    "type": "financial",
                    "priority": "medium",
                    "description": "Increase prices for premium features",
                    "confidence": 0.75,
                    "expected_impact": "high",
                    "actionable_steps": ["Analyze pricing", "Test changes"],
                    "success_metrics": ["15% revenue increase"],
                    "estimated_effort": "1 month",
                    "estimated_cost": None
                }
            ]
        }

        result = await recommendation_chain.generate_recommendations(sample_context, max_recommendations=5)

        assert len(result) == 2
        assert result[0]["type"] == "strategic"
        assert result[1]["type"] == "financial"


@pytest.mark.asyncio
async def test_generate_recommendations_limits_count(recommendation_chain, sample_context):
    """Test that recommendations are limited to max_recommendations"""
    with patch.object(recommendation_chain.chain, 'ainvoke', new_callable=AsyncMock) as mock_invoke:
        mock_invoke.return_value = {
            "recommendations": [
                {"title": f"Rec {i}", "type": "strategic", "priority": "medium", "description": "desc",
                 "confidence": 0.8, "expected_impact": "high", "actionable_steps": [],
                 "success_metrics": [], "estimated_effort": "1 week", "estimated_cost": None}
                for i in range(10)
            ]
        }

        result = await recommendation_chain.generate_recommendations(sample_context, max_recommendations=3)

        assert len(result) == 3


@pytest.mark.asyncio
async def test_generate_recommendations_empty_context(recommendation_chain, empty_context):
    """Test generating recommendations with empty context"""
    with patch.object(recommendation_chain.chain, 'ainvoke', new_callable=AsyncMock) as mock_invoke:
        mock_invoke.return_value = {"recommendations": []}

        result = await recommendation_chain.generate_recommendations(empty_context)

        assert result == []


@pytest.mark.asyncio
async def test_generate_recommendations_chain_failure(recommendation_chain, sample_context):
    """Test handling of chain failure"""
    with patch.object(recommendation_chain.chain, 'ainvoke', new_callable=AsyncMock) as mock_invoke:
        mock_invoke.side_effect = Exception("LLM API error")

        result = await recommendation_chain.generate_recommendations(sample_context)

        # Should return empty list on error
        assert result == []


@pytest.mark.asyncio
async def test_generate_recommendations_malformed_response(recommendation_chain, sample_context):
    """Test handling of malformed response"""
    with patch.object(recommendation_chain.chain, 'ainvoke', new_callable=AsyncMock) as mock_invoke:
        mock_invoke.return_value = {"not_recommendations": "invalid"}

        result = await recommendation_chain.generate_recommendations(sample_context)

        # Should handle gracefully
        assert result == []


# ===== Integration-style Tests =====

@pytest.mark.asyncio
async def test_full_recommendation_pipeline(recommendation_chain, sample_context):
    """Test complete recommendation generation pipeline"""
    with patch.object(recommendation_chain.chain, 'ainvoke', new_callable=AsyncMock) as mock_invoke:
        mock_invoke.return_value = {
            "recommendations": [
                {
                    "title": "Reduce burn rate urgently",
                    "type": "financial",
                    "priority": "urgent",
                    "description": "Burn rate has spiked 20% while revenue dropped 15%. Implement immediate cost controls.",
                    "confidence": 0.9,
                    "expected_impact": "high",
                    "actionable_steps": [
                        "Audit all recurring expenses",
                        "Renegotiate vendor contracts",
                        "Implement hiring freeze",
                        "Cut non-essential subscriptions"
                    ],
                    "success_metrics": [
                        "Reduce monthly burn by $20k",
                        "Extend runway by 3 months",
                        "Maintain team productivity"
                    ],
                    "estimated_effort": "2 weeks",
                    "estimated_cost": None
                },
                {
                    "title": "Accelerate customer acquisition",
                    "type": "sales",
                    "priority": "high",
                    "description": "Customer count is growing slowly at +5%. Need to accelerate acquisition to offset revenue decline.",
                    "confidence": 0.8,
                    "expected_impact": "high",
                    "actionable_steps": [
                        "Launch referral program",
                        "Increase paid advertising budget",
                        "Partner with complementary services"
                    ],
                    "success_metrics": [
                        "Double customer acquisition rate",
                        "Reduce CAC by 20%",
                        "Increase LTV"
                    ],
                    "estimated_effort": "1 month",
                    "estimated_cost": 15000
                },
                {
                    "title": "Pivot to enterprise customers",
                    "type": "strategic",
                    "priority": "high",
                    "description": "Based on Q4 planning discussion, focus on enterprise segment for better unit economics.",
                    "confidence": 0.75,
                    "expected_impact": "transformational",
                    "actionable_steps": [
                        "Develop enterprise features (SSO, RBAC)",
                        "Hire enterprise sales team",
                        "Create enterprise pricing tier"
                    ],
                    "success_metrics": [
                        "Sign 5 enterprise customers",
                        "Increase ARPU by 3x",
                        "Improve retention to 95%"
                    ],
                    "estimated_effort": "3 months",
                    "estimated_cost": 80000
                }
            ]
        }

        result = await recommendation_chain.generate_recommendations(sample_context, max_recommendations=5)

        # Verify structure
        assert len(result) == 3
        assert all("title" in r for r in result)
        assert all("type" in r for r in result)
        assert all("priority" in r for r in result)
        assert all("confidence" in r for r in result)

        # Verify priorities
        priorities = [r["priority"] for r in result]
        assert "urgent" in priorities or "high" in priorities

        # Verify actionable steps
        assert all(len(r["actionable_steps"]) > 0 for r in result)

        # Verify success metrics
        assert all(len(r["success_metrics"]) > 0 for r in result)

        # Verify the chain was called with properly formatted context
        call_args = mock_invoke.call_args[0][0]
        assert "kpi_data" in call_args
        assert "anomalies" in call_args
        assert "trends" in call_args
        assert "recent_context" in call_args


@pytest.mark.asyncio
async def test_recommendation_types_coverage(recommendation_chain):
    """Test that various recommendation types are supported"""
    context = RecommendationContext(
        kpi_data={"metric": 100},
        anomalies=[{"metric_name": "test", "type": "spike", "severity": "high", "deviation": 10.0}]
    )

    recommendation_types = [
        "strategic", "operational", "financial", "marketing", "sales", "product"
    ]

    with patch.object(recommendation_chain.chain, 'ainvoke', new_callable=AsyncMock) as mock_invoke:
        for rec_type in recommendation_types:
            mock_invoke.return_value = {
                "recommendations": [{
                    "title": f"{rec_type} recommendation",
                    "type": rec_type,
                    "priority": "medium",
                    "description": "test",
                    "confidence": 0.8,
                    "expected_impact": "medium",
                    "actionable_steps": ["step"],
                    "success_metrics": ["metric"],
                    "estimated_effort": "1 week",
                    "estimated_cost": None
                }]
            }

            result = await recommendation_chain.generate_recommendations(context)
            assert result[0]["type"] == rec_type


# ===== Constructor Tests =====

def test_recommendation_chain_initialization_default():
    """Test chain initialization with defaults"""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        chain = RecommendationChain()

        assert chain.llm is not None
        assert hasattr(chain, 'prompt')
        assert hasattr(chain, 'chain')


def test_recommendation_chain_initialization_custom():
    """Test chain initialization with custom parameters"""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        chain = RecommendationChain(model_name="gpt-3.5-turbo", temperature=0.5)

        assert chain.llm.model_name == "gpt-3.5-turbo"
        assert chain.llm.temperature == 0.5


# ===== Edge Cases =====

@pytest.mark.asyncio
async def test_generate_recommendations_with_all_context_types(recommendation_chain):
    """Test with comprehensive context"""
    context = RecommendationContext(
        kpi_data={"revenue": 50000, "users": 1000},
        anomalies=[{"metric_name": "revenue", "type": "drop", "severity": "high", "deviation": -15.0}],
        trends=[{"metric_name": "users", "direction": "up", "percentage_change": 10.0, "period": "month"}],
        recent_meetings=[{"title": "Strategy", "summary": "Discussed growth"}],
        sentiment_analysis={"overall": "optimistic"},
        industry_benchmarks={"avg_revenue": 75000},
        historical_recommendations=[{"title": "Previous rec"}]
    )

    with patch.object(recommendation_chain.chain, 'ainvoke', new_callable=AsyncMock) as mock_invoke:
        mock_invoke.return_value = {
            "recommendations": [{
                "title": "Test",
                "type": "strategic",
                "priority": "high",
                "description": "desc",
                "confidence": 0.8,
                "expected_impact": "high",
                "actionable_steps": ["step"],
                "success_metrics": ["metric"],
                "estimated_effort": "1 week",
                "estimated_cost": None
            }]
        }

        result = await recommendation_chain.generate_recommendations(context)

        assert len(result) == 1
        # Verify all context was formatted
        call_args = mock_invoke.call_args[0][0]
        assert "Industry Benchmarks" in call_args["context"]
        assert "revenue: 50000" in call_args["kpi_data"]
        assert "revenue: drop" in call_args["anomalies"]
        assert "users: up" in call_args["trends"]
        assert "Strategy" in call_args["recent_context"]
