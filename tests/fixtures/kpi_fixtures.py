"""
AI Chief of Staff - KPI Test Fixtures
Sprint 4: Insights & Briefings Engine

Factory classes for generating KPI-related test data including:
- KPI metrics
- Anomalies
- Recommendations
- Briefings
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

import factory
from faker import Faker

fake = Faker()


# ============================================================================
# KPI METRIC FACTORIES
# ============================================================================

class KPIMetricFactory(factory.Factory):
    """Factory for generating KPI metric test data."""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid4()))
    workspace_id = factory.LazyFunction(lambda: str(uuid4()))
    founder_id = factory.LazyFunction(lambda: str(uuid4()))
    metric_name = factory.Iterator([
        "mrr", "arr", "cac", "ltv", "churn_rate", "conversion_rate",
        "runway_months", "burn_rate", "gross_margin", "net_revenue_retention"
    ])
    metric_value = factory.LazyFunction(lambda: round(fake.pyfloat(min_value=0, max_value=100000), 2))
    metric_unit = factory.Iterator(["usd", "percent", "months", "count", "ratio"])
    source = factory.Iterator(["granola", "zerobooks", "manual"])
    timestamp = factory.LazyFunction(lambda: datetime.utcnow().isoformat())
    metadata = factory.LazyFunction(lambda: {
        "data_quality": "high",
        "confidence": 0.95,
        "calculation_method": "automated"
    })
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())

    @classmethod
    def with_trend(cls, workspace_id: str, metric_name: str, days: int = 30, trend: str = "growing") -> List[dict]:
        """
        Generate a time-series of KPI metrics with a specific trend.

        Args:
            workspace_id: Workspace ID
            metric_name: Name of the metric
            days: Number of days of data
            trend: "growing", "declining", "flat", or "volatile"

        Returns:
            List of KPI metric dictionaries
        """
        metrics = []
        base_value = 10000.0

        for i in range(days):
            timestamp = datetime.utcnow() - timedelta(days=days - i)

            if trend == "growing":
                value = base_value * (1 + 0.05 * i / days)  # 5% growth over period
            elif trend == "declining":
                value = base_value * (1 - 0.05 * i / days)  # 5% decline over period
            elif trend == "volatile":
                value = base_value * (1 + 0.1 * ((-1) ** i) * (i / days))  # Oscillating
            else:  # flat
                value = base_value * (1 + fake.pyfloat(min_value=-0.01, max_value=0.01))  # Small noise

            metrics.append(cls(
                workspace_id=workspace_id,
                metric_name=metric_name,
                metric_value=round(value, 2),
                timestamp=timestamp.isoformat()
            ))

        return metrics

    @classmethod
    def with_anomaly(cls, workspace_id: str, metric_name: str, days: int = 30, anomaly_day: int = 15) -> List[dict]:
        """
        Generate a time-series with an anomaly at a specific day.

        Args:
            workspace_id: Workspace ID
            metric_name: Name of the metric
            days: Number of days of data
            anomaly_day: Day where anomaly occurs

        Returns:
            List of KPI metric dictionaries with anomaly
        """
        metrics = []
        base_value = 10000.0

        for i in range(days):
            timestamp = datetime.utcnow() - timedelta(days=days - i)

            if i == anomaly_day:
                # Introduce significant spike or drop
                value = base_value * (1 + fake.pyfloat(min_value=0.15, max_value=0.30))
            else:
                # Normal variation
                value = base_value * (1 + fake.pyfloat(min_value=-0.02, max_value=0.02))

            metrics.append(cls(
                workspace_id=workspace_id,
                metric_name=metric_name,
                metric_value=round(value, 2),
                timestamp=timestamp.isoformat()
            ))

        return metrics

    @classmethod
    def with_seasonal_pattern(cls, workspace_id: str, metric_name: str, days: int = 90) -> List[dict]:
        """
        Generate a time-series with seasonal patterns (weekly/monthly).

        Args:
            workspace_id: Workspace ID
            metric_name: Name of the metric
            days: Number of days of data

        Returns:
            List of KPI metric dictionaries with seasonal pattern
        """
        import math
        metrics = []
        base_value = 10000.0

        for i in range(days):
            timestamp = datetime.utcnow() - timedelta(days=days - i)

            # Weekly seasonality (7-day cycle)
            weekly_factor = 1 + 0.1 * math.sin(2 * math.pi * i / 7)

            # Monthly seasonality (30-day cycle)
            monthly_factor = 1 + 0.05 * math.cos(2 * math.pi * i / 30)

            value = base_value * weekly_factor * monthly_factor

            metrics.append(cls(
                workspace_id=workspace_id,
                metric_name=metric_name,
                metric_value=round(value, 2),
                timestamp=timestamp.isoformat()
            ))

        return metrics


class CustomKPIFactory(factory.Factory):
    """Factory for custom KPI definitions."""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid4()))
    workspace_id = factory.LazyFunction(lambda: str(uuid4()))
    founder_id = factory.LazyFunction(lambda: str(uuid4()))
    metric_name = factory.LazyAttribute(lambda _: fake.word() + "_metric")
    display_name = factory.LazyAttribute(lambda _: fake.catch_phrase())
    description = factory.LazyAttribute(lambda _: fake.sentence())
    calculation_formula = factory.LazyFunction(lambda: {
        "type": "formula",
        "expression": "(revenue - costs) / customers"
    })
    metric_unit = factory.Iterator(["usd", "percent", "count", "ratio"])
    is_active = True
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())


# ============================================================================
# ANOMALY FACTORIES
# ============================================================================

class AnomalyFactory(factory.Factory):
    """Factory for generating anomaly detection results."""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid4()))
    workspace_id = factory.LazyFunction(lambda: str(uuid4()))
    metric_id = factory.LazyFunction(lambda: str(uuid4()))
    metric_name = factory.Iterator(["mrr", "cac", "churn_rate", "conversion_rate"])
    anomaly_type = factory.Iterator(["spike", "drop", "trend_change", "volatility"])
    detection_method = factory.Iterator(["zscore", "iqr", "threshold"])
    severity = factory.Iterator(["low", "medium", "high", "critical"])
    confidence_score = factory.LazyFunction(lambda: round(fake.pyfloat(min_value=0.7, max_value=1.0), 3))
    expected_value = factory.LazyFunction(lambda: round(fake.pyfloat(min_value=5000, max_value=15000), 2))
    actual_value = factory.LazyFunction(lambda: round(fake.pyfloat(min_value=1000, max_value=20000), 2))
    deviation_percentage = factory.LazyAttribute(
        lambda obj: round(((obj.actual_value - obj.expected_value) / obj.expected_value) * 100, 2)
    )
    detected_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())
    context = factory.LazyFunction(lambda: {
        "historical_mean": 10000,
        "historical_std": 500,
        "z_score": 2.5,
        "threshold": 0.1
    })
    is_false_positive = False
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())

    @classmethod
    def critical_spike(cls, workspace_id: str, metric_name: str) -> dict:
        """Create a critical spike anomaly."""
        return cls(
            workspace_id=workspace_id,
            metric_name=metric_name,
            anomaly_type="spike",
            severity="critical",
            confidence_score=0.95,
            expected_value=10000,
            actual_value=13000,
            deviation_percentage=30.0
        )

    @classmethod
    def critical_drop(cls, workspace_id: str, metric_name: str) -> dict:
        """Create a critical drop anomaly."""
        return cls(
            workspace_id=workspace_id,
            metric_name=metric_name,
            anomaly_type="drop",
            severity="critical",
            confidence_score=0.92,
            expected_value=10000,
            actual_value=7000,
            deviation_percentage=-30.0
        )


# ============================================================================
# RECOMMENDATION FACTORIES
# ============================================================================

class RecommendationFactory(factory.Factory):
    """Factory for generating strategic recommendations."""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid4()))
    workspace_id = factory.LazyFunction(lambda: str(uuid4()))
    founder_id = factory.LazyFunction(lambda: str(uuid4()))
    title = factory.LazyAttribute(lambda _: fake.catch_phrase())
    description = factory.LazyAttribute(lambda _: fake.paragraph(nb_sentences=3))
    recommendation_type = factory.Iterator([
        "optimization", "risk_mitigation", "growth_opportunity", "cost_reduction"
    ])
    priority = factory.Iterator(["urgent", "high", "medium", "low"])
    confidence_score = factory.LazyFunction(lambda: round(fake.pyfloat(min_value=0.6, max_value=1.0), 3))
    impact_score = factory.LazyFunction(lambda: round(fake.pyfloat(min_value=0.5, max_value=1.0), 3))
    actionability_score = factory.LazyFunction(lambda: round(fake.pyfloat(min_value=0.6, max_value=1.0), 3))
    data_sources = factory.LazyFunction(lambda: ["granola", "meetings", "communications"])
    context = factory.LazyFunction(lambda: {
        "triggered_by": "anomaly_detection",
        "related_metrics": ["mrr", "churn_rate"],
        "time_window": "last_7_days"
    })
    suggested_actions = factory.LazyFunction(lambda: [
        {"action": fake.sentence(), "expected_impact": "high"},
        {"action": fake.sentence(), "expected_impact": "medium"}
    ])
    status = factory.Iterator(["pending", "in_review", "accepted", "rejected", "completed"])
    user_feedback = None
    generated_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())

    @classmethod
    def high_impact(cls, workspace_id: str) -> dict:
        """Create a high-impact recommendation."""
        return cls(
            workspace_id=workspace_id,
            priority="urgent",
            confidence_score=0.9,
            impact_score=0.95,
            actionability_score=0.85,
            recommendation_type="growth_opportunity"
        )


# ============================================================================
# BRIEFING FACTORIES
# ============================================================================

class BriefingFactory(factory.Factory):
    """Factory for generating briefing data."""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid4()))
    workspace_id = factory.LazyFunction(lambda: str(uuid4()))
    founder_id = factory.LazyFunction(lambda: str(uuid4()))
    briefing_type = factory.Iterator(["morning", "evening", "investor_weekly"])
    title = factory.LazyAttribute(lambda obj: f"{obj.briefing_type.title()} Brief - {fake.date()}")
    content = factory.LazyFunction(lambda: {
        "summary": fake.paragraph(nb_sentences=5),
        "key_metrics": [
            {"metric": "MRR", "value": 10000, "change": "+5%"},
            {"metric": "CAC", "value": 500, "change": "-2%"}
        ],
        "highlights": [fake.sentence() for _ in range(3)],
        "action_items": [fake.sentence() for _ in range(2)],
        "upcoming": [fake.sentence() for _ in range(2)]
    })
    data_sources = factory.LazyFunction(lambda: {
        "kpis": 5,
        "meetings": 2,
        "communications": 10,
        "insights": 3
    })
    factual_accuracy_score = factory.LazyFunction(lambda: round(fake.pyfloat(min_value=0.85, max_value=1.0), 3))
    completeness_score = factory.LazyFunction(lambda: round(fake.pyfloat(min_value=0.80, max_value=1.0), 3))
    personalization_applied = True
    delivered_at = None
    delivery_channels = factory.LazyFunction(lambda: ["slack", "email"])
    read_status = factory.Iterator(["unread", "read", "archived"])
    user_feedback = None
    generated_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())

    @classmethod
    def morning_brief(cls, workspace_id: str, founder_id: str) -> dict:
        """Create a morning brief."""
        return cls(
            workspace_id=workspace_id,
            founder_id=founder_id,
            briefing_type="morning",
            title=f"Morning Brief - {datetime.utcnow().strftime('%Y-%m-%d')}"
        )

    @classmethod
    def evening_wrap(cls, workspace_id: str, founder_id: str) -> dict:
        """Create an evening wrap."""
        return cls(
            workspace_id=workspace_id,
            founder_id=founder_id,
            briefing_type="evening",
            title=f"Evening Wrap - {datetime.utcnow().strftime('%Y-%m-%d')}"
        )

    @classmethod
    def investor_summary(cls, workspace_id: str, founder_id: str) -> dict:
        """Create an investor weekly summary."""
        return cls(
            workspace_id=workspace_id,
            founder_id=founder_id,
            briefing_type="investor_weekly",
            title=f"Weekly Investor Update - Week of {datetime.utcnow().strftime('%Y-%m-%d')}"
        )


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_kpi_dataset_with_anomalies(
    workspace_id: str,
    metrics: List[str] = None,
    days: int = 30,
    num_anomalies: int = 2
) -> Dict[str, Any]:
    """
    Create a complete KPI dataset with anomalies for testing.

    Args:
        workspace_id: Workspace ID
        metrics: List of metric names (default: ["mrr", "cac", "churn_rate"])
        days: Number of days of data
        num_anomalies: Number of anomalies to inject

    Returns:
        Dictionary containing metrics and anomalies
    """
    if metrics is None:
        metrics = ["mrr", "cac", "churn_rate"]

    kpi_data = {}
    anomalies = []

    for metric in metrics:
        # Create mostly normal data with some anomalies
        kpi_data[metric] = KPIMetricFactory.with_anomaly(
            workspace_id=workspace_id,
            metric_name=metric,
            days=days,
            anomaly_day=days // 2
        )

        # Create anomaly records
        for _ in range(num_anomalies):
            anomalies.append(AnomalyFactory(
                workspace_id=workspace_id,
                metric_name=metric
            ))

    return {
        "kpi_data": kpi_data,
        "anomalies": anomalies
    }


def create_complete_briefing_dataset(workspace_id: str, founder_id: str) -> Dict[str, Any]:
    """
    Create a complete dataset for briefing generation testing.

    Args:
        workspace_id: Workspace ID
        founder_id: Founder ID

    Returns:
        Dictionary containing all data needed for briefing generation
    """
    # KPI data
    kpi_metrics = []
    for metric in ["mrr", "cac", "churn_rate", "conversion_rate"]:
        kpi_metrics.extend(KPIMetricFactory.with_trend(
            workspace_id=workspace_id,
            metric_name=metric,
            days=7,
            trend="growing"
        ))

    # Anomalies
    anomalies = [
        AnomalyFactory(workspace_id=workspace_id, metric_name="churn_rate")
    ]

    # Recommendations
    recommendations = [
        RecommendationFactory.high_impact(workspace_id=workspace_id)
        for _ in range(3)
    ]

    # Briefing
    briefing = BriefingFactory.morning_brief(
        workspace_id=workspace_id,
        founder_id=founder_id
    )

    return {
        "kpi_metrics": kpi_metrics,
        "anomalies": anomalies,
        "recommendations": recommendations,
        "briefing": briefing
    }
