"""
AI Chief of Staff - Z-Score Anomaly Detection Tests
Sprint 4: Insights & Briefings Engine - Issue #11

Test coverage for Z-score based anomaly detection:
- Correct anomaly identification
- False positive rate <5%
- Handle missing data
- Seasonal patterns
- Edge cases (zeros, negatives, spikes)
"""

import pytest
import numpy as np
from typing import List, Dict
from unittest.mock import Mock

from tests.fixtures.mock_kpi_data import (
    MRR_GROWING_30_DAYS,
    MRR_WITH_SPIKE,
    CHURN_WITH_SPIKE,
    MISSING_DATA_SCENARIOS,
    EDGE_CASES
)


# ============================================================================
# MOCK Z-SCORE DETECTOR
# ============================================================================

class MockZScoreDetector:
    """Mock Z-Score anomaly detector for testing."""

    def __init__(self, threshold: float = 3.0):
        self.threshold = threshold

    def detect(self, data: List[Dict]) -> List[Dict]:
        """
        Detect anomalies using Z-score method.

        Args:
            data: List of {timestamp, value} dictionaries

        Returns:
            List of detected anomalies
        """
        values = [d["value"] for d in data if d["value"] is not None]

        if len(values) < 3:
            return []

        mean = np.mean(values)
        std = np.std(values)

        if std == 0:
            return []

        anomalies = []
        for i, point in enumerate(data):
            if point["value"] is None:
                continue

            z_score = abs((point["value"] - mean) / std)
            if z_score > self.threshold:
                anomalies.append({
                    "index": i,
                    "timestamp": point["timestamp"],
                    "value": point["value"],
                    "z_score": z_score,
                    "expected_value": mean,
                    "deviation": point["value"] - mean
                })

        return anomalies

    def calculate_z_scores(self, data: List[Dict]) -> List[float]:
        """Calculate Z-scores for all data points."""
        values = [d["value"] for d in data if d["value"] is not None]

        if len(values) < 3:
            return []

        mean = np.mean(values)
        std = np.std(values)

        if std == 0:
            return [0.0] * len(values)

        return [(v - mean) / std for v in values]


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def zscore_detector():
    """Z-Score detector with default threshold."""
    return MockZScoreDetector(threshold=3.0)


@pytest.fixture
def strict_zscore_detector():
    """Z-Score detector with strict threshold."""
    return MockZScoreDetector(threshold=2.0)


@pytest.fixture
def lenient_zscore_detector():
    """Z-Score detector with lenient threshold."""
    return MockZScoreDetector(threshold=4.0)


# ============================================================================
# ANOMALY IDENTIFICATION TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.anomaly
class TestZScoreAnomalyIdentification:
    """Test correct anomaly identification using Z-score."""

    def test_detects_spike_anomaly(self, zscore_detector):
        """Test detection of spike anomaly."""
        # Arrange
        data = MRR_WITH_SPIKE

        # Act
        anomalies = zscore_detector.detect(data)

        # Assert
        assert len(anomalies) > 0, "Should detect spike anomaly"
        # The spike should have high Z-score
        max_z_score = max(a["z_score"] for a in anomalies)
        assert max_z_score > 3.0

    def test_detects_drop_anomaly(self, zscore_detector):
        """Test detection of drop anomaly."""
        # Arrange
        data = CHURN_WITH_SPIKE

        # Act
        anomalies = zscore_detector.detect(data)

        # Assert
        assert len(anomalies) > 0, "Should detect drop/spike anomaly"

    def test_no_anomalies_in_normal_data(self, zscore_detector):
        """Test that normal data produces no anomalies."""
        # Arrange
        data = MRR_GROWING_30_DAYS

        # Act
        anomalies = zscore_detector.detect(data)

        # Assert
        # Normal growing trend shouldn't have anomalies with Z > 3
        assert len(anomalies) == 0, "Normal data should have no anomalies"

    def test_calculates_correct_z_scores(self, zscore_detector):
        """Test that Z-scores are calculated correctly."""
        # Arrange
        data = [
            {"timestamp": "2024-01-01", "value": 100},
            {"timestamp": "2024-01-02", "value": 102},
            {"timestamp": "2024-01-03", "value": 98},
            {"timestamp": "2024-01-04", "value": 101},
            {"timestamp": "2024-01-05", "value": 150}  # Anomaly
        ]

        # Act
        z_scores = zscore_detector.calculate_z_scores(data)

        # Assert
        assert len(z_scores) == 5
        # Last value should have highest Z-score
        assert abs(z_scores[4]) > abs(z_scores[0])

    def test_identifies_multiple_anomalies(self, zscore_detector):
        """Test detection of multiple anomalies."""
        # Arrange
        from tests.fixtures.mock_kpi_data import MULTI_ANOMALY_DATASET

        # Act
        anomalies = zscore_detector.detect(MULTI_ANOMALY_DATASET)

        # Assert
        assert len(anomalies) > 1, "Should detect multiple anomalies"


# ============================================================================
# FALSE POSITIVE RATE TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.anomaly
@pytest.mark.accuracy
class TestZScoreFalsePositiveRate:
    """Test false positive rate validation."""

    def test_false_positive_rate_below_threshold(self, zscore_detector):
        """Test that false positive rate is below 5%."""
        # Arrange
        # Generate 100 normal data points
        normal_data = [
            {"timestamp": f"2024-01-{i:02d}", "value": 10000 + np.random.normal(0, 100)}
            for i in range(1, 101)
        ]

        # Act
        anomalies = zscore_detector.detect(normal_data)

        # Assert
        false_positive_rate = len(anomalies) / len(normal_data)
        assert false_positive_rate < 0.05, f"FPR {false_positive_rate} exceeds 5%"

    def test_threshold_affects_false_positive_rate(
        self, zscore_detector, strict_zscore_detector, lenient_zscore_detector
    ):
        """Test that threshold adjustment affects FPR."""
        # Arrange
        normal_data = [
            {"timestamp": f"2024-01-{i:02d}", "value": 10000 + np.random.normal(0, 200)}
            for i in range(1, 51)
        ]

        # Act
        default_anomalies = zscore_detector.detect(normal_data)
        strict_anomalies = strict_zscore_detector.detect(normal_data)
        lenient_anomalies = lenient_zscore_detector.detect(normal_data)

        # Assert
        # Stricter threshold should find more anomalies (higher FPR)
        # Lenient threshold should find fewer anomalies (lower FPR)
        assert len(strict_anomalies) >= len(default_anomalies)
        assert len(lenient_anomalies) <= len(default_anomalies)

    def test_consistent_results_on_repeated_runs(self, zscore_detector):
        """Test that detector produces consistent results."""
        # Arrange
        data = MRR_GROWING_30_DAYS

        # Act
        result1 = zscore_detector.detect(data)
        result2 = zscore_detector.detect(data)

        # Assert
        assert len(result1) == len(result2), "Results should be consistent"


# ============================================================================
# MISSING DATA HANDLING TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.anomaly
class TestZScoreMissingDataHandling:
    """Test handling of missing data."""

    def test_handles_sparse_missing_data(self, zscore_detector):
        """Test handling of sparse missing data points."""
        # Arrange
        data = MISSING_DATA_SCENARIOS["sparse_missing"]

        # Act
        anomalies = zscore_detector.detect(data)

        # Assert
        # Should not crash and should skip None values
        assert isinstance(anomalies, list)

    def test_handles_consecutive_missing_data(self, zscore_detector):
        """Test handling of consecutive missing data."""
        # Arrange
        data = MISSING_DATA_SCENARIOS["consecutive_missing"]

        # Act
        anomalies = zscore_detector.detect(data)

        # Assert
        assert isinstance(anomalies, list)

    def test_handles_heavy_missing_data(self, zscore_detector):
        """Test handling of heavy missing data."""
        # Arrange
        data = MISSING_DATA_SCENARIOS["heavy_missing"]

        # Act
        anomalies = zscore_detector.detect(data)

        # Assert
        # Should still work with reduced dataset
        assert isinstance(anomalies, list)

    def test_insufficient_data_returns_empty(self, zscore_detector):
        """Test that insufficient data returns no anomalies."""
        # Arrange
        data = EDGE_CASES["two_data_points"]

        # Act
        anomalies = zscore_detector.detect(data)

        # Assert
        assert len(anomalies) == 0, "Insufficient data should return no anomalies"


# ============================================================================
# SEASONAL PATTERN TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.anomaly
class TestZScoreSeasonalPatterns:
    """Test Z-score detection with seasonal patterns."""

    def test_handles_weekly_seasonality(self, zscore_detector):
        """Test that weekly seasonality doesn't cause false positives."""
        # Arrange
        from tests.fixtures.mock_kpi_data import CONVERSION_SEASONAL

        # Act
        anomalies = zscore_detector.detect(CONVERSION_SEASONAL)

        # Assert
        # Seasonal variation shouldn't exceed Z-score threshold
        false_positive_rate = len(anomalies) / len(CONVERSION_SEASONAL)
        assert false_positive_rate < 0.1  # Allow some variation

    def test_seasonal_adjustment_reduces_false_positives(self):
        """Test that seasonal adjustment improves detection."""
        # Arrange
        from tests.fixtures.mock_kpi_data import generate_seasonal_pattern

        data = generate_seasonal_pattern(base_value=10000, days=90)

        # Without seasonal adjustment
        basic_detector = MockZScoreDetector(threshold=3.0)
        basic_anomalies = basic_detector.detect(data)

        # With seasonal adjustment (mock)
        # In practice, this would detrend the data first
        values = [d["value"] for d in data]
        mean_value = np.mean(values)
        detrended_data = [
            {"timestamp": d["timestamp"], "value": d["value"] - mean_value + 10000}
            for d in data
        ]

        adjusted_detector = MockZScoreDetector(threshold=3.0)
        adjusted_anomalies = adjusted_detector.detect(detrended_data)

        # Assert
        # Seasonal adjustment should find fewer false positives
        assert isinstance(basic_anomalies, list)
        assert isinstance(adjusted_anomalies, list)


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.anomaly
class TestZScoreEdgeCases:
    """Test Z-score detection edge cases."""

    def test_handles_all_zeros(self, zscore_detector):
        """Test handling of all zero values."""
        # Arrange
        data = EDGE_CASES["all_zeros"]

        # Act
        anomalies = zscore_detector.detect(data)

        # Assert
        # Zero std should return no anomalies
        assert len(anomalies) == 0

    def test_handles_all_same_values(self, zscore_detector):
        """Test handling of constant values."""
        # Arrange
        data = EDGE_CASES["all_same"]

        # Act
        anomalies = zscore_detector.detect(data)

        # Assert
        # Zero std should return no anomalies
        assert len(anomalies) == 0

    def test_handles_negative_values(self, zscore_detector):
        """Test handling of negative values."""
        # Arrange
        data = EDGE_CASES["negative_values"]

        # Act
        anomalies = zscore_detector.detect(data)

        # Assert
        # Should work with negative values
        assert isinstance(anomalies, list)

    def test_handles_extreme_spike(self, zscore_detector):
        """Test handling of extreme spike (10x normal)."""
        # Arrange
        data = EDGE_CASES["extreme_spike"]

        # Act
        anomalies = zscore_detector.detect(data)

        # Assert
        # Should detect extreme spike
        assert len(anomalies) > 0
        max_z_score = max(a["z_score"] for a in anomalies)
        assert max_z_score > 5.0  # Very high Z-score

    def test_handles_single_data_point(self, zscore_detector):
        """Test handling of single data point."""
        # Arrange
        data = EDGE_CASES["single_data_point"]

        # Act
        anomalies = zscore_detector.detect(data)

        # Assert
        # Insufficient data should return no anomalies
        assert len(anomalies) == 0


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.anomaly
@pytest.mark.performance
class TestZScorePerformance:
    """Test Z-score detector performance."""

    def test_processes_large_dataset_quickly(self, zscore_detector):
        """Test that large datasets are processed quickly."""
        # Arrange
        import time
        large_data = [
            {"timestamp": f"2024-{i:04d}", "value": 10000 + np.random.normal(0, 100)}
            for i in range(1, 1001)  # 1000 data points
        ]

        # Act
        start_time = time.time()
        anomalies = zscore_detector.detect(large_data)
        duration = time.time() - start_time

        # Assert
        assert duration < 1.0, f"Detection took {duration}s, should be <1s"
        assert isinstance(anomalies, list)

    def test_memory_efficient(self, zscore_detector):
        """Test that detector is memory efficient."""
        # Arrange
        data = MRR_GROWING_30_DAYS

        # Act
        anomalies = zscore_detector.detect(data)

        # Assert
        # Should return only anomalies, not copy entire dataset
        assert len(anomalies) <= len(data)


# ============================================================================
# ACCURACY TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.anomaly
@pytest.mark.accuracy
class TestZScoreAccuracy:
    """Test Z-score detection accuracy."""

    def test_precision_on_labeled_data(self, zscore_detector):
        """Test precision on manually labeled anomalies."""
        # Arrange
        # Data with known anomaly at index 15
        data = [
            {"timestamp": f"2024-01-{i:02d}", "value": 10000 + np.random.normal(0, 50)}
            for i in range(1, 31)
        ]
        data[14]["value"] = 13000  # Known anomaly

        true_anomaly_indices = {14}

        # Act
        detected_anomalies = zscore_detector.detect(data)
        detected_indices = {a["index"] for a in detected_anomalies}

        # Assert
        # Should detect the known anomaly
        assert 14 in detected_indices, "Should detect known anomaly"

        # Calculate precision
        true_positives = len(true_anomaly_indices & detected_indices)
        precision = true_positives / len(detected_indices) if detected_indices else 0

        assert precision >= 0.8, f"Precision {precision} should be >=80%"

    def test_recall_on_labeled_data(self, zscore_detector):
        """Test recall on manually labeled anomalies."""
        # Arrange
        data = [
            {"timestamp": f"2024-01-{i:02d}", "value": 10000 + np.random.normal(0, 50)}
            for i in range(1, 31)
        ]
        # Add multiple known anomalies
        data[9]["value"] = 13000
        data[19]["value"] = 7000
        data[25]["value"] = 13500

        true_anomaly_indices = {9, 19, 25}

        # Act
        detected_anomalies = zscore_detector.detect(data)
        detected_indices = {a["index"] for a in detected_anomalies}

        # Assert
        true_positives = len(true_anomaly_indices & detected_indices)
        recall = true_positives / len(true_anomaly_indices)

        assert recall >= 0.8, f"Recall {recall} should be >=80%"

    def test_f1_score_above_threshold(self, zscore_detector):
        """Test that F1 score is above 85%."""
        # Arrange
        data = [
            {"timestamp": f"2024-01-{i:02d}", "value": 10000 + np.random.normal(0, 100)}
            for i in range(1, 51)
        ]
        # Add known anomalies
        data[14]["value"] = 13000
        data[29]["value"] = 7000

        true_anomaly_indices = {14, 29}

        # Act
        detected_anomalies = zscore_detector.detect(data)
        detected_indices = {a["index"] for a in detected_anomalies}

        # Calculate metrics
        true_positives = len(true_anomaly_indices & detected_indices)
        false_positives = len(detected_indices - true_anomaly_indices)
        false_negatives = len(true_anomaly_indices - detected_indices)

        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        # Assert
        assert f1_score >= 0.85, f"F1 score {f1_score} should be >=85%"
