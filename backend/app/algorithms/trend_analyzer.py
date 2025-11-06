"""
Trend Analysis
Calculate and analyze trends in time-series data
"""
import logging
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, timedelta
import numpy as np

from app.models.anomaly import TrendDirection, AnomalySeverity


logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """
    Trend analysis for time-series data

    Analyzes trends using linear regression and percentage changes
    """

    def __init__(
        self,
        significance_threshold: float = 0.10,  # 10% change threshold
        min_samples: int = 7
    ):
        """
        Initialize trend analyzer

        Args:
            significance_threshold: Minimum percentage change for significant trend
            min_samples: Minimum number of samples required
        """
        self.significance_threshold = significance_threshold
        self.min_samples = min_samples
        self.logger = logging.getLogger(__name__)

    def analyze_trend(
        self,
        values: List[float],
        timestamps: List[datetime],
        period: str = "WoW"
    ) -> Dict[str, Any]:
        """
        Analyze trend in time-series data

        Args:
            values: List of metric values
            timestamps: List of timestamps
            period: Comparison period (WoW, MoM, QoQ, YoY)

        Returns:
            Dictionary with trend analysis results
        """
        if len(values) < self.min_samples:
            self.logger.warning(
                f"Insufficient samples for trend analysis: {len(values)} < {self.min_samples}"
            )
            return {
                "direction": TrendDirection.STABLE,
                "percentage_change": 0.0,
                "is_significant": False
            }

        try:
            # Calculate linear regression trend
            trend_slope, trend_r_squared = self._calculate_linear_trend(values, timestamps)

            # Calculate period-over-period change
            percentage_change = self._calculate_period_change(values, timestamps, period)

            # Determine trend direction
            direction = self._determine_direction(percentage_change, trend_slope)

            # Check if trend is significant
            is_significant = abs(percentage_change) >= self.significance_threshold

            # Calculate volatility
            volatility = self._calculate_volatility(values)

            # Determine severity of trend change
            severity = self._calculate_severity(percentage_change)

            return {
                "direction": direction,
                "percentage_change": float(percentage_change),
                "absolute_change": float(values[-1] - values[0]) if len(values) > 0 else 0.0,
                "is_significant": is_significant,
                "trend_slope": float(trend_slope),
                "trend_strength": float(trend_r_squared),
                "volatility": float(volatility),
                "severity": severity,
                "confidence_score": self._calculate_confidence(
                    percentage_change,
                    trend_r_squared,
                    len(values)
                )
            }

        except Exception as e:
            self.logger.error(f"Error in trend analysis: {str(e)}")
            return {
                "direction": TrendDirection.STABLE,
                "percentage_change": 0.0,
                "is_significant": False,
                "error": str(e)
            }

    def _calculate_linear_trend(
        self,
        values: List[float],
        timestamps: List[datetime]
    ) -> Tuple[float, float]:
        """
        Calculate linear trend using least squares regression

        Args:
            values: List of metric values
            timestamps: List of timestamps

        Returns:
            Tuple of (slope, r_squared)
        """
        try:
            # Convert timestamps to numeric values (days from first timestamp)
            t0 = timestamps[0]
            x = np.array([(t - t0).total_seconds() / 86400 for t in timestamps])
            y = np.array(values, dtype=float)

            # Calculate linear regression
            coefficients = np.polyfit(x, y, 1)
            slope = coefficients[0]

            # Calculate R-squared
            y_pred = np.polyval(coefficients, x)
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

            return slope, r_squared

        except Exception as e:
            self.logger.error(f"Error calculating linear trend: {str(e)}")
            return 0.0, 0.0

    def _calculate_period_change(
        self,
        values: List[float],
        timestamps: List[datetime],
        period: str
    ) -> float:
        """
        Calculate percentage change over specified period

        Args:
            values: List of metric values
            timestamps: List of timestamps
            period: Period type (WoW, MoM, QoQ, YoY)

        Returns:
            Percentage change
        """
        try:
            # Define period durations
            period_days = {
                "WoW": 7,
                "MoM": 30,
                "QoQ": 90,
                "YoY": 365
            }

            days = period_days.get(period, 7)
            cutoff_date = timestamps[-1] - timedelta(days=days)

            # Find values before and after cutoff
            recent_values = []
            old_values = []

            for i, ts in enumerate(timestamps):
                if ts >= cutoff_date:
                    recent_values.append(values[i])
                else:
                    old_values.append(values[i])

            if not recent_values or not old_values:
                # Fall back to first vs last comparison
                if len(values) >= 2:
                    old_value = values[0]
                    new_value = values[-1]
                else:
                    return 0.0
            else:
                old_value = np.mean(old_values)
                new_value = np.mean(recent_values)

            # Calculate percentage change
            if old_value == 0:
                return 0.0

            percentage_change = ((new_value - old_value) / abs(old_value)) * 100

            return percentage_change

        except Exception as e:
            self.logger.error(f"Error calculating period change: {str(e)}")
            return 0.0

    def _determine_direction(
        self,
        percentage_change: float,
        slope: float
    ) -> TrendDirection:
        """
        Determine trend direction

        Args:
            percentage_change: Percentage change
            slope: Linear trend slope

        Returns:
            TrendDirection
        """
        # Use percentage change as primary indicator
        if abs(percentage_change) < 2.0:  # Less than 2% change
            return TrendDirection.STABLE
        elif percentage_change > 0:
            return TrendDirection.UP
        else:
            return TrendDirection.DOWN

    def _calculate_volatility(self, values: List[float]) -> float:
        """
        Calculate volatility (coefficient of variation)

        Args:
            values: List of metric values

        Returns:
            Volatility score
        """
        try:
            data = np.array(values, dtype=float)
            mean = np.mean(data)
            std = np.std(data)

            if mean == 0:
                return 0.0

            # Coefficient of variation
            cv = (std / abs(mean)) * 100

            return cv

        except Exception as e:
            self.logger.error(f"Error calculating volatility: {str(e)}")
            return 0.0

    def _calculate_severity(self, percentage_change: float) -> AnomalySeverity:
        """
        Calculate severity based on percentage change

        Args:
            percentage_change: Percentage change value

        Returns:
            AnomalySeverity level
        """
        abs_change = abs(percentage_change)

        if abs_change >= 50.0:
            return AnomalySeverity.CRITICAL
        elif abs_change >= 30.0:
            return AnomalySeverity.HIGH
        elif abs_change >= 15.0:
            return AnomalySeverity.MEDIUM
        elif abs_change >= 10.0:
            return AnomalySeverity.LOW
        else:
            return AnomalySeverity.INFO

    def _calculate_confidence(
        self,
        percentage_change: float,
        r_squared: float,
        sample_size: int
    ) -> float:
        """
        Calculate confidence in trend detection

        Args:
            percentage_change: Percentage change
            r_squared: R-squared from linear regression
            sample_size: Number of samples

        Returns:
            Confidence score between 0 and 1
        """
        # Higher R-squared = more confident in trend
        trend_confidence = r_squared

        # More samples = more confident
        sample_confidence = min(sample_size / 30.0, 1.0)

        # Larger change = more confident
        change_confidence = min(abs(percentage_change) / 50.0, 1.0)

        # Weighted average
        confidence = (
            trend_confidence * 0.4 +
            sample_confidence * 0.3 +
            change_confidence * 0.3
        )

        return min(max(confidence, 0.0), 1.0)

    def detect_trend_changes(
        self,
        values: List[float],
        timestamps: List[datetime],
        window_size: int = 14
    ) -> List[Dict[str, Any]]:
        """
        Detect significant trend changes (inflection points)

        Args:
            values: List of metric values
            timestamps: List of timestamps
            window_size: Window size for trend comparison

        Returns:
            List of detected trend changes
        """
        changes = []

        try:
            if len(values) < window_size * 2:
                return changes

            # Analyze trend in sliding windows
            for i in range(window_size, len(values) - window_size):
                # Previous window
                prev_values = values[i - window_size:i]
                prev_timestamps = timestamps[i - window_size:i]
                prev_slope, _ = self._calculate_linear_trend(prev_values, prev_timestamps)

                # Next window
                next_values = values[i:i + window_size]
                next_timestamps = timestamps[i:i + window_size]
                next_slope, _ = self._calculate_linear_trend(next_values, next_timestamps)

                # Check for significant slope change
                if prev_slope * next_slope < 0:  # Sign change
                    changes.append({
                        "index": i,
                        "timestamp": timestamps[i],
                        "value": values[i],
                        "previous_slope": float(prev_slope),
                        "next_slope": float(next_slope),
                        "change_type": "reversal"
                    })

        except Exception as e:
            self.logger.error(f"Error detecting trend changes: {str(e)}")

        return changes

    def forecast_next_value(
        self,
        values: List[float],
        timestamps: List[datetime],
        periods_ahead: int = 1
    ) -> float:
        """
        Simple linear forecast for next value(s)

        Args:
            values: List of metric values
            timestamps: List of timestamps
            periods_ahead: Number of periods to forecast

        Returns:
            Forecasted value
        """
        try:
            slope, _ = self._calculate_linear_trend(values, timestamps)

            # Assume periods are daily
            last_value = values[-1]
            forecast = last_value + (slope * periods_ahead)

            return float(forecast)

        except Exception as e:
            self.logger.error(f"Error forecasting: {str(e)}")
            return values[-1] if values else 0.0
