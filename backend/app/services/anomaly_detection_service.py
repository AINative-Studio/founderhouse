"""
Anomaly Detection Service
Service for detecting anomalies and analyzing trends in KPI data
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.algorithms.zscore_detector import ZScoreDetector
from app.algorithms.iqr_detector import IQRDetector
from app.algorithms.trend_analyzer import TrendAnalyzer
from app.algorithms.seasonal_decomposition import SeasonalDecomposer
from app.models.anomaly import (
    AnomalyCreate,
    AnomalyResponse,
    TrendCreate,
    TrendResponse,
    DetectionMethod,
    MetricAnalysis
)
from app.models.kpi_metric import AggregationPeriod
from app.database import get_supabase_client


logger = logging.getLogger(__name__)


class AnomalyDetectionService:
    """Service for detecting anomalies and trends in time-series data"""

    def __init__(self):
        self.supabase = get_supabase_client()
        self.logger = logging.getLogger(__name__)

        # Initialize detectors
        self.zscore_detector = ZScoreDetector(threshold=3.0)
        self.iqr_detector = IQRDetector(multiplier=1.5)
        self.trend_analyzer = TrendAnalyzer(significance_threshold=0.10)
        self.seasonal_decomposer = SeasonalDecomposer(seasonal_period=7)

    async def analyze_metric(
        self,
        metric_id: UUID,
        workspace_id: UUID,
        days_back: int = 30,
        detection_methods: Optional[List[DetectionMethod]] = None
    ) -> MetricAnalysis:
        """
        Comprehensive analysis of a metric

        Args:
            metric_id: Metric ID to analyze
            workspace_id: Workspace ID
            days_back: Number of days of historical data to analyze
            detection_methods: Methods to use (default: all)

        Returns:
            MetricAnalysis with anomalies, trends, and insights
        """
        try:
            # Get metric metadata
            metric_result = self.supabase.table("kpi_metrics").select("*").eq(
                "id", str(metric_id)
            ).single().execute()

            if not metric_result.data:
                raise ValueError(f"Metric {metric_id} not found")

            metric = metric_result.data

            # Get historical data
            start_date = datetime.utcnow() - timedelta(days=days_back)
            data_points = await self._get_metric_data(metric_id, workspace_id, start_date)

            if len(data_points) < 2:
                return self._empty_analysis(metric_id, metric["name"])

            values = [dp["value"] for dp in data_points]
            timestamps = [datetime.fromisoformat(dp["timestamp"].replace("Z", "+00:00"))
                         for dp in data_points]

            # Detect anomalies
            anomalies = await self.detect_anomalies(
                metric_id=metric_id,
                workspace_id=workspace_id,
                values=values,
                timestamps=timestamps,
                data_point_ids=[UUID(dp["id"]) for dp in data_points],
                methods=detection_methods or [DetectionMethod.ZSCORE, DetectionMethod.IQR]
            )

            # Analyze trends
            trends = await self.analyze_trends(
                metric_id=metric_id,
                workspace_id=workspace_id,
                values=values,
                timestamps=timestamps
            )

            # Calculate statistics
            statistics = self.zscore_detector.get_statistics(values)

            # Get current and previous values
            current_value = values[-1] if values else 0.0
            previous_value = values[-2] if len(values) >= 2 else current_value

            # Calculate change
            absolute_change = current_value - previous_value
            percentage_change = (
                (absolute_change / abs(previous_value)) * 100
                if previous_value != 0 else 0.0
            )

            # Generate insights
            insights = self._generate_insights(
                metric,
                values,
                anomalies,
                trends,
                statistics
            )

            return MetricAnalysis(
                metric_id=metric_id,
                metric_name=metric["name"],
                time_range={
                    "start": timestamps[0],
                    "end": timestamps[-1]
                },
                current_value=current_value,
                previous_value=previous_value,
                change={
                    "absolute": absolute_change,
                    "percentage": percentage_change,
                    "direction": "up" if absolute_change > 0 else "down" if absolute_change < 0 else "stable"
                },
                anomalies=anomalies,
                trends=trends,
                statistics=statistics,
                insights=insights
            )

        except Exception as e:
            self.logger.error(f"Error analyzing metric {metric_id}: {str(e)}")
            raise

    async def detect_anomalies(
        self,
        metric_id: UUID,
        workspace_id: UUID,
        values: List[float],
        timestamps: List[datetime],
        data_point_ids: List[UUID],
        methods: List[DetectionMethod] = None,
        auto_save: bool = True
    ) -> List[AnomalyResponse]:
        """
        Detect anomalies using specified methods

        Args:
            metric_id: Metric ID
            workspace_id: Workspace ID
            values: List of values
            timestamps: List of timestamps
            data_point_ids: List of data point IDs
            methods: Detection methods to use
            auto_save: Whether to save detected anomalies

        Returns:
            List of detected anomalies
        """
        if methods is None:
            methods = [DetectionMethod.ZSCORE, DetectionMethod.IQR]

        all_anomalies = []

        try:
            # Z-Score detection
            if DetectionMethod.ZSCORE in methods:
                zscore_anomalies = self.zscore_detector.detect(values, timestamps)
                for idx, z_score, anomaly_type, severity in zscore_anomalies:
                    anomaly = await self._create_anomaly(
                        metric_id=metric_id,
                        workspace_id=workspace_id,
                        data_point_id=data_point_ids[idx],
                        anomaly_type=anomaly_type,
                        severity=severity,
                        detection_method=DetectionMethod.ZSCORE,
                        expected_value=self.zscore_detector.calculate_expected_value(values, idx),
                        actual_value=values[idx],
                        deviation=z_score,
                        confidence=self.zscore_detector.calculate_confidence(values, z_score),
                        auto_save=auto_save
                    )
                    if anomaly:
                        all_anomalies.append(anomaly)

            # IQR detection
            if DetectionMethod.IQR in methods:
                iqr_anomalies = self.iqr_detector.detect(values, timestamps)
                for idx, deviation, anomaly_type, severity in iqr_anomalies:
                    # Check if anomaly already detected by another method
                    if not any(a.data_point_id == data_point_ids[idx] for a in all_anomalies):
                        lower_bound, upper_bound = self.iqr_detector.calculate_expected_range(values)
                        expected = (lower_bound + upper_bound) / 2

                        anomaly = await self._create_anomaly(
                            metric_id=metric_id,
                            workspace_id=workspace_id,
                            data_point_id=data_point_ids[idx],
                            anomaly_type=anomaly_type,
                            severity=severity,
                            detection_method=DetectionMethod.IQR,
                            expected_value=expected,
                            actual_value=values[idx],
                            deviation=deviation,
                            confidence=self.iqr_detector.calculate_confidence(values, deviation),
                            auto_save=auto_save
                        )
                        if anomaly:
                            all_anomalies.append(anomaly)

            # Seasonal anomaly detection
            if DetectionMethod.SEASONAL_DECOMPOSITION in methods:
                seasonal_anomalies = self.seasonal_decomposer.detect_seasonal_anomalies(
                    values, timestamps, threshold=2.0
                )
                for idx, residual in seasonal_anomalies:
                    if not any(a.data_point_id == data_point_ids[idx] for a in all_anomalies):
                        anomaly = await self._create_anomaly(
                            metric_id=metric_id,
                            workspace_id=workspace_id,
                            data_point_id=data_point_ids[idx],
                            anomaly_type=anomaly_type if residual > 0 else anomaly_type,
                            severity=severity,
                            detection_method=DetectionMethod.SEASONAL_DECOMPOSITION,
                            expected_value=values[idx] - residual,
                            actual_value=values[idx],
                            deviation=abs(residual),
                            confidence=0.8,
                            auto_save=auto_save
                        )
                        if anomaly:
                            all_anomalies.append(anomaly)

            self.logger.info(
                f"Detected {len(all_anomalies)} anomalies for metric {metric_id} "
                f"using methods: {[m.value for m in methods]}"
            )

        except Exception as e:
            self.logger.error(f"Error detecting anomalies: {str(e)}")

        return all_anomalies

    async def analyze_trends(
        self,
        metric_id: UUID,
        workspace_id: UUID,
        values: List[float],
        timestamps: List[datetime],
        periods: List[str] = None,
        auto_save: bool = True
    ) -> List[TrendResponse]:
        """
        Analyze trends for different time periods

        Args:
            metric_id: Metric ID
            workspace_id: Workspace ID
            values: List of values
            timestamps: List of timestamps
            periods: Periods to analyze (WoW, MoM, etc.)
            auto_save: Whether to save detected trends

        Returns:
            List of trends
        """
        if periods is None:
            periods = ["WoW", "MoM"]

        trends = []

        try:
            for period in periods:
                trend_analysis = self.trend_analyzer.analyze_trend(values, timestamps, period)

                if trend_analysis["is_significant"]:
                    # Determine time range for trend
                    period_days = {"WoW": 7, "MoM": 30, "QoQ": 90, "YoY": 365}
                    days = period_days.get(period, 7)

                    start_date = timestamps[-1] - timedelta(days=days)
                    end_date = timestamps[-1]

                    # Get start and end values
                    start_idx = 0
                    for i, ts in enumerate(timestamps):
                        if ts >= start_date:
                            start_idx = i
                            break

                    start_value = values[start_idx] if start_idx < len(values) else values[0]
                    end_value = values[-1]

                    trend = await self._create_trend(
                        metric_id=metric_id,
                        workspace_id=workspace_id,
                        direction=trend_analysis["direction"],
                        period=period,
                        start_date=start_date,
                        end_date=end_date,
                        start_value=start_value,
                        end_value=end_value,
                        percentage_change=trend_analysis["percentage_change"],
                        absolute_change=trend_analysis["absolute_change"],
                        confidence=trend_analysis["confidence_score"],
                        is_significant=trend_analysis["is_significant"],
                        auto_save=auto_save
                    )

                    if trend:
                        trends.append(trend)

        except Exception as e:
            self.logger.error(f"Error analyzing trends: {str(e)}")

        return trends

    async def _create_anomaly(
        self,
        metric_id: UUID,
        workspace_id: UUID,
        data_point_id: UUID,
        anomaly_type,
        severity,
        detection_method: DetectionMethod,
        expected_value: float,
        actual_value: float,
        deviation: float,
        confidence: float,
        auto_save: bool = True
    ) -> Optional[AnomalyResponse]:
        """Create and optionally save an anomaly"""
        try:
            anomaly_data = AnomalyCreate(
                metric_id=metric_id,
                workspace_id=workspace_id,
                data_point_id=data_point_id,
                anomaly_type=anomaly_type,
                severity=severity,
                detection_method=detection_method,
                expected_value=expected_value,
                actual_value=actual_value,
                deviation=deviation,
                confidence_score=confidence,
                context={
                    "method": detection_method.value,
                    "detected_at": datetime.utcnow().isoformat()
                }
            )

            if auto_save:
                result = self.supabase.table("anomalies").insert(
                    anomaly_data.model_dump(mode="json")
                ).execute()

                if result.data:
                    return AnomalyResponse(**result.data[0])

            return AnomalyResponse(
                id=UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
                detected_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
                **anomaly_data.model_dump()
            )

        except Exception as e:
            self.logger.error(f"Error creating anomaly: {str(e)}")
            return None

    async def _create_trend(
        self,
        metric_id: UUID,
        workspace_id: UUID,
        direction,
        period: str,
        start_date: datetime,
        end_date: datetime,
        start_value: float,
        end_value: float,
        percentage_change: float,
        absolute_change: float,
        confidence: float,
        is_significant: bool,
        auto_save: bool = True
    ) -> Optional[TrendResponse]:
        """Create and optionally save a trend"""
        try:
            trend_data = TrendCreate(
                metric_id=metric_id,
                workspace_id=workspace_id,
                direction=direction,
                period=period,
                start_date=start_date,
                end_date=end_date,
                start_value=start_value,
                end_value=end_value,
                percentage_change=percentage_change,
                absolute_change=absolute_change,
                confidence_score=confidence,
                is_significant=is_significant
            )

            if auto_save:
                result = self.supabase.table("trends").insert(
                    trend_data.model_dump(mode="json")
                ).execute()

                if result.data:
                    return TrendResponse(**result.data[0])

            return TrendResponse(
                id=UUID("00000000-0000-0000-0000-000000000000"),
                created_at=datetime.utcnow(),
                **trend_data.model_dump()
            )

        except Exception as e:
            self.logger.error(f"Error creating trend: {str(e)}")
            return None

    async def _get_metric_data(
        self,
        metric_id: UUID,
        workspace_id: UUID,
        start_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get metric data points"""
        try:
            result = self.supabase.table("kpi_data_points").select("*").eq(
                "metric_id", str(metric_id)
            ).eq("workspace_id", str(workspace_id)).gte(
                "timestamp", start_date.isoformat()
            ).order("timestamp").execute()

            return result.data

        except Exception as e:
            self.logger.error(f"Error getting metric data: {str(e)}")
            return []

    def _empty_analysis(self, metric_id: UUID, metric_name: str) -> MetricAnalysis:
        """Return empty analysis when insufficient data"""
        return MetricAnalysis(
            metric_id=metric_id,
            metric_name=metric_name,
            time_range={"start": datetime.utcnow(), "end": datetime.utcnow()},
            current_value=0.0,
            previous_value=0.0,
            change={"absolute": 0.0, "percentage": 0.0, "direction": "stable"},
            anomalies=[],
            trends=[],
            statistics={},
            insights=["Insufficient data for analysis"]
        )

    def _generate_insights(
        self,
        metric: Dict[str, Any],
        values: List[float],
        anomalies: List[AnomalyResponse],
        trends: List[TrendResponse],
        statistics: Dict[str, float]
    ) -> List[str]:
        """Generate human-readable insights"""
        insights = []

        try:
            metric_name = metric["display_name"]

            # Anomaly insights
            if anomalies:
                critical_anomalies = [a for a in anomalies if a.severity.value == "critical"]
                if critical_anomalies:
                    insights.append(
                        f"{len(critical_anomalies)} critical anomalies detected in {metric_name}"
                    )

            # Trend insights
            for trend in trends:
                if trend.is_significant:
                    direction = "increased" if trend.direction.value == "up" else "decreased"
                    insights.append(
                        f"{metric_name} {direction} by {abs(trend.percentage_change):.1f}% {trend.period}"
                    )

            # Statistical insights
            if "std" in statistics and "mean" in statistics:
                cv = (statistics["std"] / statistics["mean"]) * 100 if statistics["mean"] != 0 else 0
                if cv > 20:
                    insights.append(f"{metric_name} shows high volatility (CV: {cv:.1f}%)")

        except Exception as e:
            self.logger.error(f"Error generating insights: {str(e)}")

        return insights
