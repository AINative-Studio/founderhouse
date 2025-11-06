"""
IQR (Interquartile Range) Anomaly Detection
Robust outlier detection using quartiles
"""
import logging
from typing import List, Tuple, Optional
from datetime import datetime
import numpy as np

from app.models.anomaly import AnomalyType, AnomalySeverity


logger = logging.getLogger(__name__)


class IQRDetector:
    """
    IQR (Interquartile Range) based anomaly detection

    Uses the interquartile range to identify outliers.
    More robust to existing outliers compared to z-score.
    """

    def __init__(
        self,
        multiplier: float = 1.5,
        min_samples: int = 10
    ):
        """
        Initialize IQR detector

        Args:
            multiplier: IQR multiplier for outlier bounds (default: 1.5)
                       1.5 = moderate outliers, 3.0 = extreme outliers
            min_samples: Minimum number of samples required
        """
        self.multiplier = multiplier
        self.min_samples = min_samples
        self.logger = logging.getLogger(__name__)

    def detect(
        self,
        values: List[float],
        timestamps: Optional[List[datetime]] = None
    ) -> List[Tuple[int, float, AnomalyType, AnomalySeverity]]:
        """
        Detect anomalies using IQR method

        Args:
            values: List of metric values
            timestamps: Optional list of timestamps

        Returns:
            List of tuples (index, deviation, anomaly_type, severity)
        """
        if len(values) < self.min_samples:
            self.logger.warning(
                f"Insufficient samples for IQR detection: {len(values)} < {self.min_samples}"
            )
            return []

        anomalies = []

        try:
            # Convert to numpy array
            data = np.array(values, dtype=float)

            # Calculate quartiles
            q1 = np.percentile(data, 25)
            q3 = np.percentile(data, 75)
            iqr = q3 - q1

            # Calculate bounds
            lower_bound = q1 - (self.multiplier * iqr)
            upper_bound = q3 + (self.multiplier * iqr)

            # Find outliers
            for idx, value in enumerate(data):
                if value < lower_bound or value > upper_bound:
                    # Calculate deviation from nearest bound
                    if value < lower_bound:
                        deviation = abs(value - lower_bound) / iqr if iqr > 0 else 0
                        anomaly_type = AnomalyType.DROP
                    else:
                        deviation = abs(value - upper_bound) / iqr if iqr > 0 else 0
                        anomaly_type = AnomalyType.SPIKE

                    # Determine severity
                    severity = self._calculate_severity(deviation)

                    anomalies.append((idx, float(deviation), anomaly_type, severity))

            self.logger.info(
                f"IQR detection found {len(anomalies)} anomalies "
                f"(Q1={q1:.2f}, Q3={q3:.2f}, IQR={iqr:.2f}, "
                f"bounds=[{lower_bound:.2f}, {upper_bound:.2f}])"
            )

        except Exception as e:
            self.logger.error(f"Error in IQR detection: {str(e)}")

        return anomalies

    def _calculate_severity(self, deviation: float) -> AnomalySeverity:
        """
        Calculate anomaly severity based on deviation from IQR bounds

        Args:
            deviation: Deviation in IQR units

        Returns:
            AnomalySeverity level
        """
        if deviation >= 3.0:
            return AnomalySeverity.CRITICAL
        elif deviation >= 2.0:
            return AnomalySeverity.HIGH
        elif deviation >= 1.0:
            return AnomalySeverity.MEDIUM
        elif deviation >= 0.5:
            return AnomalySeverity.LOW
        else:
            return AnomalySeverity.INFO

    def calculate_expected_range(
        self,
        values: List[float]
    ) -> Tuple[float, float]:
        """
        Calculate expected value range using IQR

        Args:
            values: List of metric values

        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        try:
            data = np.array(values, dtype=float)

            q1 = np.percentile(data, 25)
            q3 = np.percentile(data, 75)
            iqr = q3 - q1

            lower_bound = q1 - (self.multiplier * iqr)
            upper_bound = q3 + (self.multiplier * iqr)

            return (float(lower_bound), float(upper_bound))

        except Exception as e:
            self.logger.error(f"Error calculating expected range: {str(e)}")
            return (0.0, 0.0)

    def calculate_confidence(
        self,
        values: List[float],
        deviation: float
    ) -> float:
        """
        Calculate confidence score for anomaly detection

        Args:
            values: List of metric values
            deviation: Deviation from IQR bounds

        Returns:
            Confidence score between 0 and 1
        """
        # Higher deviation = higher confidence
        # More samples = higher confidence

        sample_size_factor = min(len(values) / 100.0, 1.0)
        deviation_factor = min(deviation / 3.0, 1.0)

        confidence = (sample_size_factor * 0.3) + (deviation_factor * 0.7)

        return min(max(confidence, 0.0), 1.0)

    def get_statistics(self, values: List[float]) -> dict:
        """
        Get statistical measures for the data

        Args:
            values: List of metric values

        Returns:
            Dictionary with statistical measures
        """
        try:
            data = np.array(values, dtype=float)

            q1 = np.percentile(data, 25)
            q2 = np.percentile(data, 50)  # median
            q3 = np.percentile(data, 75)
            iqr = q3 - q1

            lower_bound = q1 - (self.multiplier * iqr)
            upper_bound = q3 + (self.multiplier * iqr)

            return {
                "q1": float(q1),
                "median": float(q2),
                "q3": float(q3),
                "iqr": float(iqr),
                "lower_bound": float(lower_bound),
                "upper_bound": float(upper_bound),
                "min": float(np.min(data)),
                "max": float(np.max(data)),
                "count": len(data)
            }
        except Exception as e:
            self.logger.error(f"Error calculating statistics: {str(e)}")
            return {}

    def is_outlier(self, value: float, values: List[float]) -> bool:
        """
        Check if a single value is an outlier

        Args:
            value: Value to check
            values: Historical values for comparison

        Returns:
            True if value is an outlier
        """
        try:
            lower_bound, upper_bound = self.calculate_expected_range(values)
            return value < lower_bound or value > upper_bound
        except Exception as e:
            self.logger.error(f"Error checking outlier: {str(e)}")
            return False
