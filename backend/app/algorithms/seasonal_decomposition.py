"""
Seasonal Decomposition
Time-series decomposition for seasonal pattern detection
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import numpy as np


logger = logging.getLogger(__name__)


class SeasonalDecomposer:
    """
    Seasonal decomposition for time-series analysis

    Decomposes time-series into trend, seasonal, and residual components
    Uses simple moving average approach (lighter alternative to STL)
    """

    def __init__(
        self,
        seasonal_period: int = 7,  # 7 for weekly seasonality
        min_samples: int = 14
    ):
        """
        Initialize seasonal decomposer

        Args:
            seasonal_period: Length of seasonal cycle (e.g., 7 for weekly)
            min_samples: Minimum number of samples required
        """
        self.seasonal_period = seasonal_period
        self.min_samples = min_samples
        self.logger = logging.getLogger(__name__)

    def decompose(
        self,
        values: List[float],
        timestamps: Optional[List[datetime]] = None
    ) -> Dict[str, Any]:
        """
        Decompose time-series into components

        Args:
            values: List of metric values
            timestamps: Optional list of timestamps

        Returns:
            Dictionary with trend, seasonal, and residual components
        """
        if len(values) < self.min_samples:
            self.logger.warning(
                f"Insufficient samples for decomposition: {len(values)} < {self.min_samples}"
            )
            return {
                "trend": values,
                "seasonal": [0] * len(values),
                "residual": [0] * len(values),
                "error": "Insufficient samples"
            }

        try:
            data = np.array(values, dtype=float)

            # Calculate trend using moving average
            trend = self._calculate_trend(data)

            # Detrend the data
            detrended = data - trend

            # Calculate seasonal component
            seasonal = self._calculate_seasonal(detrended)

            # Calculate residual
            residual = data - trend - seasonal

            return {
                "original": data.tolist(),
                "trend": trend.tolist(),
                "seasonal": seasonal.tolist(),
                "residual": residual.tolist(),
                "seasonal_strength": float(self._calculate_seasonal_strength(seasonal, residual)),
                "trend_strength": float(self._calculate_trend_strength(trend, residual))
            }

        except Exception as e:
            self.logger.error(f"Error in seasonal decomposition: {str(e)}")
            return {
                "trend": values,
                "seasonal": [0] * len(values),
                "residual": [0] * len(values),
                "error": str(e)
            }

    def _calculate_trend(self, data: np.ndarray) -> np.ndarray:
        """
        Calculate trend component using centered moving average

        Args:
            data: Input data array

        Returns:
            Trend component array
        """
        # Use moving average with window size = seasonal_period
        window_size = self.seasonal_period

        # Pad data at edges
        trend = np.zeros_like(data)

        for i in range(len(data)):
            start_idx = max(0, i - window_size // 2)
            end_idx = min(len(data), i + window_size // 2 + 1)
            trend[i] = np.mean(data[start_idx:end_idx])

        return trend

    def _calculate_seasonal(self, detrended: np.ndarray) -> np.ndarray:
        """
        Calculate seasonal component

        Args:
            detrended: Detrended data

        Returns:
            Seasonal component array
        """
        seasonal = np.zeros_like(detrended)

        # Calculate average for each position in cycle
        seasonal_averages = np.zeros(self.seasonal_period)

        for i in range(self.seasonal_period):
            indices = range(i, len(detrended), self.seasonal_period)
            if indices:
                seasonal_averages[i] = np.mean([detrended[idx] for idx in indices if idx < len(detrended)])

        # Center the seasonal component (mean = 0)
        seasonal_averages -= np.mean(seasonal_averages)

        # Tile the seasonal pattern
        full_cycles = len(detrended) // self.seasonal_period
        remainder = len(detrended) % self.seasonal_period

        seasonal = np.tile(seasonal_averages, full_cycles)
        if remainder > 0:
            seasonal = np.concatenate([seasonal, seasonal_averages[:remainder]])

        return seasonal

    def _calculate_seasonal_strength(
        self,
        seasonal: np.ndarray,
        residual: np.ndarray
    ) -> float:
        """
        Calculate strength of seasonal component

        Args:
            seasonal: Seasonal component
            residual: Residual component

        Returns:
            Seasonal strength (0 to 1)
        """
        try:
            var_seasonal = np.var(seasonal)
            var_residual = np.var(residual)

            if var_seasonal + var_residual == 0:
                return 0.0

            strength = var_seasonal / (var_seasonal + var_residual)
            return min(max(strength, 0.0), 1.0)

        except Exception as e:
            self.logger.error(f"Error calculating seasonal strength: {str(e)}")
            return 0.0

    def _calculate_trend_strength(
        self,
        trend: np.ndarray,
        residual: np.ndarray
    ) -> float:
        """
        Calculate strength of trend component

        Args:
            trend: Trend component
            residual: Residual component

        Returns:
            Trend strength (0 to 1)
        """
        try:
            var_trend = np.var(trend)
            var_residual = np.var(residual)

            if var_trend + var_residual == 0:
                return 0.0

            strength = var_trend / (var_trend + var_residual)
            return min(max(strength, 0.0), 1.0)

        except Exception as e:
            self.logger.error(f"Error calculating trend strength: {str(e)}")
            return 0.0

    def detect_seasonal_anomalies(
        self,
        values: List[float],
        timestamps: Optional[List[datetime]] = None,
        threshold: float = 2.0
    ) -> List[Tuple[int, float]]:
        """
        Detect anomalies based on seasonal decomposition

        Anomalies are detected in the residual component

        Args:
            values: List of metric values
            timestamps: Optional list of timestamps
            threshold: Standard deviation threshold for residuals

        Returns:
            List of tuples (index, residual_value)
        """
        anomalies = []

        try:
            decomposition = self.decompose(values, timestamps)

            if "error" in decomposition:
                return anomalies

            residuals = np.array(decomposition["residual"])

            # Calculate threshold based on residual statistics
            mean_residual = np.mean(residuals)
            std_residual = np.std(residuals)

            if std_residual == 0:
                return anomalies

            # Find points where residual exceeds threshold
            for i, residual in enumerate(residuals):
                z_score = abs((residual - mean_residual) / std_residual)

                if z_score > threshold:
                    anomalies.append((i, float(residual)))

        except Exception as e:
            self.logger.error(f"Error detecting seasonal anomalies: {str(e)}")

        return anomalies

    def adjust_for_seasonality(
        self,
        values: List[float],
        timestamps: Optional[List[datetime]] = None
    ) -> List[float]:
        """
        Remove seasonal component from data

        Args:
            values: List of metric values
            timestamps: Optional list of timestamps

        Returns:
            Seasonally adjusted values
        """
        try:
            decomposition = self.decompose(values, timestamps)

            if "error" in decomposition:
                return values

            # Return original - seasonal
            data = np.array(decomposition["original"])
            seasonal = np.array(decomposition["seasonal"])

            adjusted = data - seasonal

            return adjusted.tolist()

        except Exception as e:
            self.logger.error(f"Error adjusting for seasonality: {str(e)}")
            return values

    def predict_seasonal_pattern(
        self,
        values: List[float],
        periods_ahead: int = 7
    ) -> List[float]:
        """
        Predict future values based on seasonal pattern

        Args:
            values: Historical values
            periods_ahead: Number of periods to predict

        Returns:
            List of predicted values
        """
        try:
            decomposition = self.decompose(values)

            if "error" in decomposition:
                return [values[-1]] * periods_ahead

            # Get last trend value and seasonal pattern
            trend = decomposition["trend"]
            seasonal = decomposition["seasonal"]

            last_trend = trend[-1]

            # Extend seasonal pattern
            predictions = []
            seasonal_pattern = seasonal[-self.seasonal_period:]

            for i in range(periods_ahead):
                seasonal_idx = i % self.seasonal_period
                predicted = last_trend + seasonal_pattern[seasonal_idx]
                predictions.append(float(predicted))

            return predictions

        except Exception as e:
            self.logger.error(f"Error predicting seasonal pattern: {str(e)}")
            return [values[-1]] * periods_ahead if values else [0.0] * periods_ahead
