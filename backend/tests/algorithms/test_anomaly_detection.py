"""
Comprehensive tests for Anomaly Detection Algorithms
Tests IQR, Z-Score, Trend, and Seasonal Decomposition detectors
"""
import pytest
import numpy as np
from datetime import datetime, timedelta

from app.algorithms.iqr_detector import IQRDetector
from app.algorithms.zscore_detector import ZScoreDetector
from app.models.anomaly import AnomalyType, AnomalySeverity


# ==================== IQR DETECTOR TESTS ====================

class TestIQRDetector:
    """Test suite for IQR-based anomaly detection"""

    @pytest.fixture
    def detector(self):
        """Create IQR detector with default settings"""
        return IQRDetector(multiplier=1.5, min_samples=10)

    @pytest.fixture
    def normal_data(self):
        """Normal distribution data"""
        return [50, 52, 48, 51, 49, 53, 47, 50, 52, 48, 51, 49]

    @pytest.fixture
    def data_with_spike(self):
        """Data with a spike anomaly"""
        return [50, 52, 48, 51, 49, 53, 47, 50, 100, 48, 51, 49]

    @pytest.fixture
    def data_with_drop(self):
        """Data with a drop anomaly"""
        return [50, 52, 48, 51, 49, 53, 47, 5, 52, 48, 51, 49]

    def test_detect_no_anomalies(self, detector, normal_data):
        """Test detection with no anomalies"""
        anomalies = detector.detect(normal_data)

        assert len(anomalies) == 0

    def test_detect_spike_anomaly(self, detector, data_with_spike):
        """Test detection of spike anomaly"""
        anomalies = detector.detect(data_with_spike)

        assert len(anomalies) > 0
        idx, deviation, anomaly_type, severity = anomalies[0]
        assert anomaly_type == AnomalyType.SPIKE
        assert idx == 8  # Position of spike

    def test_detect_drop_anomaly(self, detector, data_with_drop):
        """Test detection of drop anomaly"""
        anomalies = detector.detect(data_with_drop)

        assert len(anomalies) > 0
        idx, deviation, anomaly_type, severity = anomalies[0]
        assert anomaly_type == AnomalyType.DROP
        assert idx == 7  # Position of drop

    def test_detect_multiple_anomalies(self, detector):
        """Test detection of multiple anomalies"""
        data = [50, 52, 100, 51, 49, 10, 47, 50, 52, 48, 51, 49]
        anomalies = detector.detect(data)

        assert len(anomalies) == 2
        # Should detect both spike and drop

    def test_insufficient_samples(self, detector):
        """Test with insufficient samples"""
        data = [50, 52, 48]  # Less than min_samples
        anomalies = detector.detect(data)

        assert len(anomalies) == 0

    def test_severity_levels(self, detector):
        """Test severity calculation"""
        # Critical severity (3.0+ IQR units)
        assert detector._calculate_severity(3.5) == AnomalySeverity.CRITICAL

        # High severity (2.0-3.0 IQR units)
        assert detector._calculate_severity(2.5) == AnomalySeverity.HIGH

        # Medium severity (1.0-2.0 IQR units)
        assert detector._calculate_severity(1.5) == AnomalySeverity.MEDIUM

        # Low severity (0.5-1.0 IQR units)
        assert detector._calculate_severity(0.75) == AnomalySeverity.LOW

        # Info severity (<0.5 IQR units)
        assert detector._calculate_severity(0.25) == AnomalySeverity.INFO

    def test_calculate_expected_range(self, detector, normal_data):
        """Test expected range calculation"""
        lower, upper = detector.calculate_expected_range(normal_data)

        assert lower < upper
        assert all(lower <= v <= upper for v in normal_data)

    def test_calculate_confidence(self, detector, normal_data):
        """Test confidence calculation"""
        # High deviation should give high confidence
        confidence_high = detector.calculate_confidence(normal_data, deviation=3.0)
        assert confidence_high > 0.7

        # Low deviation should give lower confidence
        confidence_low = detector.calculate_confidence(normal_data, deviation=0.5)
        assert confidence_low < confidence_high

        # More samples should increase confidence
        more_samples = normal_data * 10
        confidence_more = detector.calculate_confidence(more_samples, deviation=2.0)
        confidence_less = detector.calculate_confidence(normal_data, deviation=2.0)
        assert confidence_more >= confidence_less

    def test_get_statistics(self, detector, normal_data):
        """Test statistics calculation"""
        stats = detector.get_statistics(normal_data)

        assert "q1" in stats
        assert "median" in stats
        assert "q3" in stats
        assert "iqr" in stats
        assert "lower_bound" in stats
        assert "upper_bound" in stats
        assert "min" in stats
        assert "max" in stats
        assert "count" in stats

        assert stats["count"] == len(normal_data)
        assert stats["min"] == min(normal_data)
        assert stats["max"] == max(normal_data)

    def test_is_outlier(self, detector, normal_data):
        """Test single value outlier check"""
        # Normal value should not be outlier
        assert detector.is_outlier(50, normal_data) is False

        # Extreme value should be outlier
        assert detector.is_outlier(200, normal_data) is True
        assert detector.is_outlier(-50, normal_data) is True

    def test_different_multipliers(self):
        """Test different IQR multipliers"""
        data = [50, 52, 48, 51, 49, 53, 47, 80, 52, 48, 51, 49]

        # Stricter detection (smaller multiplier)
        strict_detector = IQRDetector(multiplier=1.0)
        strict_anomalies = strict_detector.detect(data)

        # Lenient detection (larger multiplier)
        lenient_detector = IQRDetector(multiplier=3.0)
        lenient_anomalies = lenient_detector.detect(data)

        # Stricter should find more anomalies
        assert len(strict_anomalies) >= len(lenient_anomalies)

    def test_empty_data(self, detector):
        """Test with empty data"""
        anomalies = detector.detect([])
        assert len(anomalies) == 0

    def test_constant_data(self, detector):
        """Test with constant values (zero variance)"""
        data = [50] * 20
        anomalies = detector.detect(data)

        # All values are the same, no outliers
        assert len(anomalies) == 0


# ==================== Z-SCORE DETECTOR TESTS ====================

class TestZScoreDetector:
    """Test suite for Z-Score based anomaly detection"""

    @pytest.fixture
    def detector(self):
        """Create Z-Score detector with default settings"""
        return ZScoreDetector(threshold=3.0, min_samples=10)

    @pytest.fixture
    def normal_data(self):
        """Normal distribution data"""
        np.random.seed(42)
        return list(np.random.normal(100, 10, 50))

    @pytest.fixture
    def data_with_spike(self):
        """Data with spike anomaly"""
        np.random.seed(42)
        data = list(np.random.normal(100, 10, 50))
        data[25] = 200  # Add spike
        return data

    @pytest.fixture
    def data_with_drop(self):
        """Data with drop anomaly"""
        np.random.seed(42)
        data = list(np.random.normal(100, 10, 50))
        data[25] = 20  # Add drop
        return data

    def test_detect_no_anomalies(self, detector, normal_data):
        """Test detection with no anomalies"""
        anomalies = detector.detect(normal_data)

        # Should have few or no anomalies in normal distribution
        assert len(anomalies) < 3

    def test_detect_spike_anomaly(self, detector, data_with_spike):
        """Test detection of spike anomaly"""
        anomalies = detector.detect(data_with_spike)

        assert len(anomalies) > 0

        # Find the spike
        spike_found = False
        for idx, z_score, anomaly_type, severity in anomalies:
            if idx == 25:
                assert anomaly_type == AnomalyType.SPIKE
                assert z_score > 3.0
                spike_found = True
                break

        assert spike_found

    def test_detect_drop_anomaly(self, detector, data_with_drop):
        """Test detection of drop anomaly"""
        anomalies = detector.detect(data_with_drop)

        assert len(anomalies) > 0

        # Find the drop
        drop_found = False
        for idx, z_score, anomaly_type, severity in anomalies:
            if idx == 25:
                assert anomaly_type == AnomalyType.DROP
                assert z_score > 3.0
                drop_found = True
                break

        assert drop_found

    def test_insufficient_samples(self, detector):
        """Test with insufficient samples"""
        data = [50, 52, 48]
        anomalies = detector.detect(data)

        assert len(anomalies) == 0

    def test_severity_levels(self, detector):
        """Test severity calculation"""
        # Critical severity (>=5.0)
        assert detector._calculate_severity(5.5) == AnomalySeverity.CRITICAL

        # High severity (>=4.0)
        assert detector._calculate_severity(4.5) == AnomalySeverity.HIGH

        # Medium severity (>=3.5)
        assert detector._calculate_severity(3.7) == AnomalySeverity.MEDIUM

        # Low severity (>=3.0)
        assert detector._calculate_severity(3.2) == AnomalySeverity.LOW

        # Info severity (<3.0)
        assert detector._calculate_severity(2.5) == AnomalySeverity.INFO

    def test_calculate_expected_value(self, detector, normal_data):
        """Test expected value calculation"""
        expected = detector.calculate_expected_value(normal_data, 0)

        # Should be close to mean of data
        mean = np.mean(normal_data)
        assert abs(expected - mean) < 0.1

    def test_calculate_confidence(self, detector, normal_data):
        """Test confidence calculation"""
        # High z-score should give high confidence
        confidence_high = detector.calculate_confidence(normal_data, z_score=5.0)
        assert confidence_high > 0.7

        # Low z-score should give lower confidence
        confidence_low = detector.calculate_confidence(normal_data, z_score=3.0)
        assert confidence_low < confidence_high

        # More samples should increase confidence
        more_samples = normal_data * 3
        confidence_more = detector.calculate_confidence(more_samples, z_score=4.0)
        confidence_less = detector.calculate_confidence(normal_data, z_score=4.0)
        assert confidence_more >= confidence_less

    def test_get_statistics(self, detector, normal_data):
        """Test statistics calculation"""
        stats = detector.get_statistics(normal_data)

        assert "mean" in stats
        assert "median" in stats
        assert "std" in stats
        assert "min" in stats
        assert "max" in stats
        assert "count" in stats
        assert "variance" in stats

        assert stats["count"] == len(normal_data)
        assert stats["min"] == min(normal_data)
        assert stats["max"] == max(normal_data)

    def test_constant_data(self, detector):
        """Test with constant values (zero std)"""
        data = [50] * 20
        anomalies = detector.detect(data)

        # Zero standard deviation, no anomalies can be detected
        assert len(anomalies) == 0

    def test_different_thresholds(self):
        """Test different z-score thresholds"""
        np.random.seed(42)
        data = list(np.random.normal(100, 10, 50))
        data[25] = 160  # Moderate anomaly

        # Stricter threshold
        strict_detector = ZScoreDetector(threshold=2.5)
        strict_anomalies = strict_detector.detect(data)

        # Lenient threshold
        lenient_detector = ZScoreDetector(threshold=4.0)
        lenient_anomalies = lenient_detector.detect(data)

        # Stricter should find more anomalies
        assert len(strict_anomalies) >= len(lenient_anomalies)

    def test_empty_data(self, detector):
        """Test with empty data"""
        anomalies = detector.detect([])
        assert len(anomalies) == 0

    def test_single_extreme_value(self, detector):
        """Test detection of single extreme outlier"""
        data = [100] * 20 + [1000] + [100] * 20
        anomalies = detector.detect(data)

        assert len(anomalies) > 0

        # Should detect the extreme value at index 20
        extreme_found = any(idx == 20 for idx, _, _, _ in anomalies)
        assert extreme_found


# ==================== EDGE CASES AND INTEGRATION ====================

class TestAnomalyDetectionEdgeCases:
    """Test edge cases and integration scenarios"""

    def test_iqr_vs_zscore_comparison(self):
        """Compare IQR and Z-Score on same dataset"""
        # Create data with outliers
        np.random.seed(42)
        data = list(np.random.normal(100, 10, 50))
        data[10] = 200  # Spike
        data[30] = 20   # Drop

        iqr_detector = IQRDetector()
        zscore_detector = ZScoreDetector()

        iqr_anomalies = iqr_detector.detect(data)
        zscore_anomalies = zscore_detector.detect(data)

        # Both should detect the outliers
        assert len(iqr_anomalies) > 0
        assert len(zscore_anomalies) > 0

    def test_with_timestamps(self):
        """Test detection with timestamps"""
        values = [50, 52, 100, 51, 49, 53, 47, 50, 52, 48, 51, 49]
        timestamps = [datetime.utcnow() + timedelta(hours=i) for i in range(len(values))]

        detector = IQRDetector()
        anomalies = detector.detect(values, timestamps)

        assert len(anomalies) > 0

    def test_very_large_dataset(self):
        """Test with large dataset"""
        np.random.seed(42)
        data = list(np.random.normal(1000, 100, 1000))
        data[500] = 2000  # Add anomaly

        detector = ZScoreDetector()
        anomalies = detector.detect(data)

        assert len(anomalies) > 0

    def test_negative_values(self):
        """Test with negative values"""
        data = [-50, -52, -48, -51, -49, -100, -47, -50, -52, -48, -51, -49]

        iqr_detector = IQRDetector()
        anomalies = iqr_detector.detect(data)

        assert len(anomalies) > 0

    def test_mixed_positive_negative(self):
        """Test with mixed positive and negative values"""
        data = [50, -40, 45, -42, 48, -45, 100, -38, 52, -41, 51, -43]

        zscore_detector = ZScoreDetector()
        anomalies = zscore_detector.detect(data)

        # Should handle mixed values correctly
        assert isinstance(anomalies, list)

    def test_floating_point_precision(self):
        """Test with high precision floating point values"""
        data = [50.123456, 52.987654, 48.111111, 51.222222, 49.333333,
                53.444444, 47.555555, 150.666666, 52.777777, 48.888888]

        detector = IQRDetector()
        anomalies = detector.detect(data)

        assert len(anomalies) > 0

    def test_confidence_bounds(self):
        """Test that confidence is always between 0 and 1"""
        data = [50] * 20

        iqr_detector = IQRDetector()
        zscore_detector = ZScoreDetector()

        # Test various deviation values
        for deviation in [0.1, 1.0, 5.0, 10.0]:
            iqr_conf = iqr_detector.calculate_confidence(data, deviation)
            assert 0.0 <= iqr_conf <= 1.0

            zscore_conf = zscore_detector.calculate_confidence(data, deviation)
            assert 0.0 <= zscore_conf <= 1.0

    def test_statistics_consistency(self):
        """Test that statistics are consistent across detectors"""
        np.random.seed(42)
        data = list(np.random.normal(100, 15, 100))

        iqr_detector = IQRDetector()
        zscore_detector = ZScoreDetector()

        iqr_stats = iqr_detector.get_statistics(data)
        zscore_stats = zscore_detector.get_statistics(data)

        # Both should report same basic stats
        assert iqr_stats["count"] == zscore_stats["count"]
        assert iqr_stats["min"] == zscore_stats["min"]
        assert iqr_stats["max"] == zscore_stats["max"]
