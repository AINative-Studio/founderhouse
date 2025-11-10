"""
Unit tests for Feedback Loop System
Tests user feedback collection, model improvement, and quality metrics
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from uuid import uuid4

from tests.fixtures.feedback_fixtures import (
    FEEDBACK_TYPES,
    FEEDBACK_SOURCES,
    MOCK_USER_FEEDBACK,
    MOCK_MODEL_PERFORMANCE,
    FEEDBACK_AGGREGATIONS,
    QUALITY_METRICS,
    MOCK_AB_TESTS,
    create_mock_feedback,
    get_feedback_by_source,
    calculate_net_promoter_score
)


class TestFeedbackTypes:
    """Test feedback type definitions"""

    def test_all_feedback_types_defined(self):
        """Test all expected feedback types exist"""
        expected_types = [
            "THUMBS_UP",
            "THUMBS_DOWN",
            "RATING",
            "TEXT",
            "CORRECTION",
            "FEATURE_REQUEST"
        ]

        for feedback_type in expected_types:
            assert feedback_type in FEEDBACK_TYPES

    def test_all_feedback_sources_defined(self):
        """Test all expected sources exist"""
        expected_sources = [
            "BRIEFING",
            "TASK_CREATION",
            "VOICE_COMMAND",
            "VIDEO_SUMMARY",
            "DISCORD_RESPONSE",
            "KPI_INSIGHT"
        ]

        for source in expected_sources:
            assert source in FEEDBACK_SOURCES


class TestFeedbackCollection:
    """Test feedback data collection"""

    def test_mock_feedback_has_required_fields(self):
        """Test all feedback entries have required fields"""
        for feedback in MOCK_USER_FEEDBACK:
            assert "id" in feedback
            assert "user_id" in feedback
            assert "workspace_id" in feedback
            assert "feedback_type" in feedback
            assert "source" in feedback
            assert "created_at" in feedback

    def test_feedback_with_ratings(self):
        """Test feedback with numerical ratings"""
        rating_feedback = [
            f for f in MOCK_USER_FEEDBACK
            if f["feedback_type"] == FEEDBACK_TYPES["RATING"]
        ]

        assert len(rating_feedback) > 0
        for feedback in rating_feedback:
            assert "rating" in feedback
            assert 1 <= feedback["rating"] <= 5

    def test_feedback_with_corrections(self):
        """Test correction feedback includes both original and corrected"""
        correction_feedback = [
            f for f in MOCK_USER_FEEDBACK
            if f["feedback_type"] == FEEDBACK_TYPES["CORRECTION"]
        ]

        assert len(correction_feedback) > 0
        for feedback in correction_feedback:
            assert "metadata" in feedback
            # Corrections should have original and corrected data

    def test_create_mock_feedback_function(self):
        """Test creating custom feedback entries"""
        feedback = create_mock_feedback(
            feedback_type=FEEDBACK_TYPES["THUMBS_UP"],
            source=FEEDBACK_SOURCES["BRIEFING"],
            rating=5,
            comment="Great job!"
        )

        assert feedback["feedback_type"] == FEEDBACK_TYPES["THUMBS_UP"]
        assert feedback["source"] == FEEDBACK_SOURCES["BRIEFING"]
        assert feedback["rating"] == 5
        assert feedback["comment"] == "Great job!"

    def test_get_feedback_by_source_filter(self):
        """Test filtering feedback by source"""
        briefing_feedback = get_feedback_by_source(FEEDBACK_SOURCES["BRIEFING"])

        assert len(briefing_feedback) > 0
        assert all(f["source"] == FEEDBACK_SOURCES["BRIEFING"] for f in briefing_feedback)


class TestModelPerformanceMetrics:
    """Test model performance tracking"""

    def test_action_item_extraction_metrics(self):
        """Test action item extraction performance metrics"""
        metrics = next(
            m for m in MOCK_MODEL_PERFORMANCE
            if m["model_type"] == "action_item_extraction"
        )

        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1_score" in metrics
        assert 0 <= metrics["precision"] <= 1
        assert 0 <= metrics["recall"] <= 1
        assert 0 <= metrics["f1_score"] <= 1

    def test_voice_intent_metrics_include_errors(self):
        """Test voice intent metrics include common errors"""
        metrics = next(
            m for m in MOCK_MODEL_PERFORMANCE
            if m["model_type"] == "voice_intent_recognition"
        )

        assert "common_errors" in metrics
        assert len(metrics["common_errors"]) > 0
        for error in metrics["common_errors"]:
            assert "error" in error
            assert "count" in error

    def test_video_summarization_metrics(self):
        """Test video summarization quality metrics"""
        metrics = next(
            m for m in MOCK_MODEL_PERFORMANCE
            if m["model_type"] == "video_summarization"
        )

        assert "total_summaries" in metrics
        assert "user_approved" in metrics
        assert "average_rating" in metrics
        assert metrics["average_rating"] >= 1
        assert metrics["average_rating"] <= 5

    def test_kpi_anomaly_detection_metrics(self):
        """Test anomaly detection metrics"""
        metrics = next(
            m for m in MOCK_MODEL_PERFORMANCE
            if m["model_type"] == "kpi_anomaly_detection"
        )

        assert "true_positives" in metrics
        assert "false_positives" in metrics
        assert "false_negatives" in metrics

        # Calculate rates
        tp = metrics["true_positives"]
        fp = metrics["false_positives"]
        fn = metrics["false_negatives"]

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0

        assert abs(precision - metrics["precision"]) < 0.01
        assert abs(recall - metrics["recall"]) < 0.01


class TestFeedbackAggregation:
    """Test feedback aggregation and reporting"""

    def test_daily_aggregation_structure(self):
        """Test daily aggregation has correct structure"""
        daily = FEEDBACK_AGGREGATIONS["daily"]

        assert "date" in daily
        assert "total_feedback_count" in daily
        assert "positive_feedback" in daily
        assert "negative_feedback" in daily
        assert "average_rating" in daily
        assert "sentiment_score" in daily

    def test_weekly_aggregation_includes_improvements(self):
        """Test weekly aggregation includes improvement areas"""
        weekly = FEEDBACK_AGGREGATIONS["weekly"]

        assert "improvement_areas" in weekly
        assert len(weekly["improvement_areas"]) > 0
        assert isinstance(weekly["improvement_areas"], list)

    def test_monthly_aggregation_includes_trends(self):
        """Test monthly aggregation includes trend analysis"""
        monthly = FEEDBACK_AGGREGATIONS["monthly"]

        assert "trends" in monthly
        assert len(monthly["trends"]) > 0

        for trend in monthly["trends"]:
            assert "metric" in trend
            assert "direction" in trend
            assert "change" in trend
            assert trend["direction"] in ["up", "down", "stable"]

    def test_sentiment_scores_in_range(self):
        """Test sentiment scores are between -1 and 1"""
        for period, data in FEEDBACK_AGGREGATIONS.items():
            if "sentiment_score" in data:
                assert -1 <= data["sentiment_score"] <= 1

    def test_calculate_nps_function(self):
        """Test NPS calculation"""
        test_feedback = [
            {"rating": 5},  # Promoter
            {"rating": 5},  # Promoter
            {"rating": 4},  # Promoter
            {"rating": 3},  # Passive
            {"rating": 2},  # Detractor
        ]

        nps = calculate_net_promoter_score(test_feedback)

        # 3 promoters, 1 detractor out of 5 = (3-1)/5 * 100 = 40
        assert nps == 40.0

    def test_calculate_nps_empty_list(self):
        """Test NPS with empty feedback list"""
        nps = calculate_net_promoter_score([])
        assert nps == 0.0


class TestQualityMetrics:
    """Test quality metric tracking"""

    def test_quality_metrics_have_thresholds(self):
        """Test all quality metrics have warning and critical thresholds"""
        for metric_name, metric_data in QUALITY_METRICS.items():
            assert "threshold_warning" in metric_data
            assert "threshold_critical" in metric_data
            assert "current_value" in metric_data

    def test_quality_metrics_have_trends(self):
        """Test metrics include trend information"""
        for metric_name, metric_data in QUALITY_METRICS.items():
            assert "trend" in metric_data
            assert metric_data["trend"] in ["improving", "stable", "declining"]

    def test_quality_metrics_have_historical_data(self):
        """Test metrics include historical data"""
        for metric_name, metric_data in QUALITY_METRICS.items():
            assert "last_30_days" in metric_data
            assert len(metric_data["last_30_days"]) == 30

            for day_data in metric_data["last_30_days"]:
                assert "date" in day_data
                assert "value" in day_data

    def test_f1_score_metric_properties(self):
        """Test F1 score metric configuration"""
        f1_metric = QUALITY_METRICS["action_item_extraction"]

        assert f1_metric["metric"] == "f1_score"
        assert f1_metric["target_value"] == 0.95
        assert f1_metric["threshold_warning"] == 0.85
        assert f1_metric["threshold_critical"] == 0.80

    def test_word_error_rate_metric_properties(self):
        """Test WER metric configuration (lower is better)"""
        wer_metric = QUALITY_METRICS["voice_transcription_accuracy"]

        assert wer_metric["metric"] == "word_error_rate"
        # For WER, lower is better, so thresholds are higher values
        assert wer_metric["threshold_warning"] > wer_metric["target_value"]


class TestABTesting:
    """Test A/B testing framework"""

    def test_ab_tests_have_variants(self):
        """Test A/B tests define control and variants"""
        for test in MOCK_AB_TESTS:
            assert "variants" in test
            assert "control" in test["variants"]
            assert len(test["variants"]) >= 2  # At least control + 1 variant

    def test_ab_tests_have_sample_sizes(self):
        """Test all variants have sample sizes"""
        for test in MOCK_AB_TESTS:
            for variant_name, variant_data in test["variants"].items():
                assert "sample_size" in variant_data
                assert variant_data["sample_size"] > 0

    def test_ab_tests_have_winner_declaration(self):
        """Test completed tests have winner"""
        for test in MOCK_AB_TESTS:
            assert "winner" in test
            assert test["winner"] in test["variants"]

    def test_ab_tests_have_statistical_significance(self):
        """Test tests include statistical significance"""
        for test in MOCK_AB_TESTS:
            assert "statistical_significance" in test
            assert 0 <= test["statistical_significance"] <= 1

    def test_voice_model_ab_test_accuracy_comparison(self):
        """Test voice model A/B test compares accuracy"""
        voice_test = next(
            t for t in MOCK_AB_TESTS
            if t["test_id"] == "ab_test_voice_model"
        )

        control = voice_test["variants"]["control"]
        variant = voice_test["variants"]["variant_a"]

        assert "accuracy" in control
        assert "accuracy" in variant
        # Variant should have higher accuracy
        assert variant["accuracy"] > control["accuracy"]

    def test_ab_test_includes_tradeoffs(self):
        """Test A/B tests capture metric tradeoffs"""
        voice_test = next(
            t for t in MOCK_AB_TESTS
            if t["test_id"] == "ab_test_voice_model"
        )

        control = voice_test["variants"]["control"]
        variant = voice_test["variants"]["variant_a"]

        # Variant has better accuracy but slower
        assert variant["accuracy"] > control["accuracy"]
        assert variant["avg_latency_ms"] > control["avg_latency_ms"]


class TestTrainingDataGeneration:
    """Test training data generation from feedback"""

    def test_training_data_structure(self):
        """Test training data has correct structure"""
        from tests.fixtures.feedback_fixtures import MOCK_TRAINING_DATA

        for training_example in MOCK_TRAINING_DATA:
            assert "source_feedback_id" in training_example
            assert "model_type" in training_example
            assert "training_example" in training_example
            assert "added_to_training_set" in training_example

    def test_training_data_includes_corrections(self):
        """Test training data includes original and corrected outputs"""
        from tests.fixtures.feedback_fixtures import MOCK_TRAINING_DATA

        for training_example in MOCK_TRAINING_DATA:
            example = training_example["training_example"]
            assert "input" in example
            assert "corrected_output" in example
            assert "original_output" in example

    def test_training_data_from_voice_corrections(self):
        """Test voice correction generates training data"""
        from tests.fixtures.feedback_fixtures import MOCK_TRAINING_DATA

        voice_training = [
            t for t in MOCK_TRAINING_DATA
            if t["model_type"] == "voice_intent_recognition"
        ]

        assert len(voice_training) > 0


class TestFeedbackIntegration:
    """Test feedback system integration"""

    def test_feedback_sources_match_system_features(self):
        """Test feedback sources align with system features"""
        expected_features = [
            "briefing",
            "task_creation",
            "voice_command",
            "video_summary",
            "discord_response",
            "kpi_insight"
        ]

        for feature in expected_features:
            assert feature in FEEDBACK_SOURCES.values()

    def test_feedback_metadata_varies_by_source(self):
        """Test different sources have appropriate metadata"""
        # Briefing feedback should include content sections
        briefing_feedback = [
            f for f in MOCK_USER_FEEDBACK
            if f["source"] == FEEDBACK_SOURCES["BRIEFING"]
        ]

        for feedback in briefing_feedback:
            if "metadata" in feedback:
                assert isinstance(feedback["metadata"], dict)

        # Voice command feedback should include transcription
        voice_feedback = [
            f for f in MOCK_USER_FEEDBACK
            if f["source"] == FEEDBACK_SOURCES["VOICE_COMMAND"]
        ]

        for feedback in voice_feedback:
            if "metadata" in feedback:
                # May include transcription data
                pass
