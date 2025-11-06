"""
Z-Score Anomaly Detection
Statistical outlier detection using z-score methodology
"""
import logging
from typing import List, Tuple, Optional
from datetime import datetime
import numpy as np

from app.models.anomaly import AnomalyType, AnomalySeverity


logger = logging.getLogger(__name__)


class ZScoreDetector:
    """
    Z-Score based anomaly detection

    Detects anomalies using standard deviation from mean.
    A z-score indicates how many standard deviations an element is from the mean.
    """

    def __init__(
        self,
        threshold: float = 3.0,
        min_samples: int = 10
    ):
        """
        Initialize Z-Score detector

        Args:
            threshold: Z-score threshold for anomaly detection (default: 3.0)
            min_samples: Minimum number of samples required for detection
        """
        self.threshold = threshold
        self.min_samples = min_samples
        self.logger = logging.getLogger(__name__)

    def detect(
        self,
        values: List[float],
        timestamps: Optional[List[datetime]] = None
    ) -> List[Tuple[int, float, AnomalyType, AnomalySeverity]]:
        """
        Detect anomalies using z-score method

        Args:
            values: List of metric values
            timestamps: Optional list of timestamps

        Returns:
            List of tuples (index, z_score, anomaly_type, severity)
        """
        if len(values) < self.min_samples:
            self.logger.warning(
                f"Insufficient samples for z-score detection: {len(values)} < {self.min_samples}"
            )
            return []

        anomalies = []

        try:
            # Convert to numpy array
            data = np.array(values, dtype=float)

            # Calculate mean and standard deviation
            mean = np.mean(data)
            std = np.std(data)

            # Handle case where std is 0 (all values identical)
            if std == 0:
                self.logger.warning("Standard deviation is 0, no anomalies detected")
                return []

            # Calculate z-scores
            z_scores = np.abs((data - mean) / std)

            # Find anomalies
            for idx, z_score in enumerate(z_scores):
                if z_score > self.threshold:
                    # Determine anomaly type
                    if data[idx] > mean:
                        anomaly_type = AnomalyType.SPIKE
                    else:
                        anomaly_type = AnomalyType.DROP

                    # Determine severity based on z-score magnitude
                    severity = self._calculate_severity(z_score)

                    anomalies.append((idx, float(z_score), anomaly_type, severity))

            self.logger.info(
                f"Z-score detection found {len(anomalies)} anomalies "
                f"(mean={mean:.2f}, std={std:.2f}, threshold={self.threshold})"
            )

        except Exception as e:
            self.logger.error(f"Error in z-score detection: {str(e)}")

        return anomalies

    def _calculate_severity(self, z_score: float) -> AnomalySeverity:
        """
        Calculate anomaly severity based on z-score magnitude

        Args:
            z_score: Z-score value

        Returns:
            AnomalySeverity level
        """
        if z_score >= 5.0:
            return AnomalySeverity.CRITICAL
        elif z_score >= 4.0:
            return AnomalySeverity.HIGH
        elif z_score >= 3.5:
            return AnomalySeverity.MEDIUM
        elif z_score >= 3.0:
            return AnomalySeverity.LOW
        else:
            return AnomalySeverity.INFO

    def calculate_expected_value(
        self,
        values: List[float],
        index: int
    ) -> float:
        """
        Calculate expected value at given index

        Args:
            values: List of metric values
            index: Index to calculate expected value for

        Returns:
            Expected value (mean of all values)
        """
        data = np.array(values, dtype=float)
        return float(np.mean(data))

    def calculate_confidence(
        self,
        values: List[float],
        z_score: float
    ) -> float:
        """
        Calculate confidence score for anomaly detection

        Args:
            values: List of metric values
            z_score: Z-score of the anomaly

        Returns:
            Confidence score between 0 and 1
        """
        # Higher z-score = higher confidence
        # More samples = higher confidence

        sample_size_factor = min(len(values) / 100.0, 1.0)  # Cap at 100 samples
        z_score_factor = min(z_score / 5.0, 1.0)  # Cap at z-score of 5

        # Combined confidence
        confidence = (sample_size_factor * 0.3) + (z_score_factor * 0.7)

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

            return {
                "mean": float(np.mean(data)),
                "median": float(np.median(data)),
                "std": float(np.std(data)),
                "min": float(np.min(data)),
                "max": float(np.max(data)),
                "count": len(data),
                "variance": float(np.var(data))
            }
        except Exception as e:
            self.logger.error(f"Error calculating statistics: {str(e)}")
            return {}
