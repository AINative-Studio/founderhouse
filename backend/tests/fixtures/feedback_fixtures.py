"""
Feedback loop test fixtures
Mock data for user feedback, model improvement, and quality metrics
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List
from uuid import uuid4


# Feedback Types
FEEDBACK_TYPES = {
    "THUMBS_UP": "thumbs_up",
    "THUMBS_DOWN": "thumbs_down",
    "RATING": "rating",
    "TEXT": "text_feedback",
    "CORRECTION": "correction",
    "FEATURE_REQUEST": "feature_request"
}


# Feedback Sources
FEEDBACK_SOURCES = {
    "BRIEFING": "briefing",
    "TASK_CREATION": "task_creation",
    "VOICE_COMMAND": "voice_command",
    "VIDEO_SUMMARY": "video_summary",
    "DISCORD_RESPONSE": "discord_response",
    "KPI_INSIGHT": "kpi_insight"
}


# Mock User Feedback
MOCK_USER_FEEDBACK = [
    {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "workspace_id": str(uuid4()),
        "feedback_type": FEEDBACK_TYPES["THUMBS_UP"],
        "source": FEEDBACK_SOURCES["BRIEFING"],
        "source_id": str(uuid4()),
        "rating": 5,
        "comment": "The daily briefing was very accurate and helpful",
        "created_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
        "metadata": {
            "briefing_type": "daily",
            "content_sections": ["priorities", "kpi_alerts", "action_items"]
        }
    },
    {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "workspace_id": str(uuid4()),
        "feedback_type": FEEDBACK_TYPES["THUMBS_DOWN"],
        "source": FEEDBACK_SOURCES["TASK_CREATION"],
        "source_id": str(uuid4()),
        "rating": 2,
        "comment": "Task was created with wrong priority - should have been urgent",
        "created_at": (datetime.utcnow() - timedelta(hours=6)).isoformat(),
        "metadata": {
            "task_platform": "monday",
            "assigned_priority": "normal",
            "expected_priority": "urgent"
        }
    },
    {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "workspace_id": str(uuid4()),
        "feedback_type": FEEDBACK_TYPES["CORRECTION"],
        "source": FEEDBACK_SOURCES["VOICE_COMMAND"],
        "source_id": str(uuid4()),
        "rating": 3,
        "comment": "Voice command misunderstood - I said 'Sarah' not 'Sara'",
        "created_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
        "metadata": {
            "original_transcription": "Send report to Sara",
            "corrected_transcription": "Send report to Sarah",
            "intent": "create_task"
        }
    },
    {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "workspace_id": str(uuid4()),
        "feedback_type": FEEDBACK_TYPES["RATING"],
        "source": FEEDBACK_SOURCES["VIDEO_SUMMARY"],
        "source_id": str(uuid4()),
        "rating": 5,
        "comment": "Excellent summary - captured all key points",
        "created_at": (datetime.utcnow() - timedelta(hours=12)).isoformat(),
        "metadata": {
            "video_id": "video_1_sprint_review",
            "summary_length": "medium",
            "included_action_items": True
        }
    },
    {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "workspace_id": str(uuid4()),
        "feedback_type": FEEDBACK_TYPES["FEATURE_REQUEST"],
        "source": FEEDBACK_SOURCES["DISCORD_RESPONSE"],
        "source_id": str(uuid4()),
        "rating": 4,
        "comment": "Would love to see support for Slack in addition to Discord",
        "created_at": (datetime.utcnow() - timedelta(days=3)).isoformat(),
        "metadata": {
            "requested_feature": "slack_integration",
            "use_case": "team_notifications"
        }
    },
    {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "workspace_id": str(uuid4()),
        "feedback_type": FEEDBACK_TYPES["THUMBS_UP"],
        "source": FEEDBACK_SOURCES["KPI_INSIGHT"],
        "source_id": str(uuid4()),
        "rating": 5,
        "comment": "KPI anomaly detection caught an issue we would have missed",
        "created_at": (datetime.utcnow() - timedelta(days=2)).isoformat(),
        "metadata": {
            "kpi_metric": "churn_rate",
            "anomaly_type": "sudden_increase",
            "severity": "high"
        }
    }
]


# Model Performance Feedback
MOCK_MODEL_PERFORMANCE = [
    {
        "model_type": "action_item_extraction",
        "total_extractions": 1523,
        "user_confirmed": 1387,
        "user_rejected": 89,
        "user_corrected": 47,
        "precision": 0.91,
        "recall": 0.94,
        "f1_score": 0.925,
        "average_confidence": 0.87,
        "updated_at": datetime.utcnow().isoformat()
    },
    {
        "model_type": "voice_intent_recognition",
        "total_commands": 892,
        "correctly_interpreted": 838,
        "misinterpreted": 54,
        "precision": 0.94,
        "recall": 0.92,
        "f1_score": 0.93,
        "average_confidence": 0.89,
        "common_errors": [
            {"error": "name_confusion", "count": 23},
            {"error": "date_parsing", "count": 18},
            {"error": "ambiguous_intent", "count": 13}
        ],
        "updated_at": datetime.utcnow().isoformat()
    },
    {
        "model_type": "video_summarization",
        "total_summaries": 234,
        "user_approved": 212,
        "user_edited": 18,
        "user_rejected": 4,
        "average_rating": 4.3,
        "key_point_accuracy": 0.89,
        "action_item_accuracy": 0.92,
        "updated_at": datetime.utcnow().isoformat()
    },
    {
        "model_type": "kpi_anomaly_detection",
        "total_checks": 4567,
        "anomalies_detected": 127,
        "true_positives": 115,
        "false_positives": 12,
        "false_negatives": 8,
        "precision": 0.91,
        "recall": 0.93,
        "f1_score": 0.92,
        "updated_at": datetime.utcnow().isoformat()
    }
]


# Feedback Aggregations
FEEDBACK_AGGREGATIONS = {
    "daily": {
        "date": datetime.utcnow().date().isoformat(),
        "total_feedback_count": 45,
        "positive_feedback": 32,
        "negative_feedback": 8,
        "neutral_feedback": 5,
        "average_rating": 4.2,
        "sentiment_score": 0.78,
        "top_issues": [
            {"issue": "priority_classification", "count": 5},
            {"issue": "name_recognition", "count": 3}
        ]
    },
    "weekly": {
        "week_start": (datetime.utcnow() - timedelta(days=7)).date().isoformat(),
        "week_end": datetime.utcnow().date().isoformat(),
        "total_feedback_count": 234,
        "positive_feedback": 187,
        "negative_feedback": 32,
        "neutral_feedback": 15,
        "average_rating": 4.4,
        "sentiment_score": 0.82,
        "improvement_areas": [
            "voice_command_accuracy",
            "priority_inference",
            "date_parsing"
        ]
    },
    "monthly": {
        "month": datetime.utcnow().strftime("%Y-%m"),
        "total_feedback_count": 892,
        "positive_feedback": 723,
        "negative_feedback": 108,
        "neutral_feedback": 61,
        "average_rating": 4.3,
        "sentiment_score": 0.81,
        "trends": [
            {"metric": "overall_satisfaction", "direction": "up", "change": 0.08},
            {"metric": "voice_accuracy", "direction": "up", "change": 0.12},
            {"metric": "task_routing_accuracy", "direction": "stable", "change": 0.02}
        ]
    }
}


# Training Data from Feedback
MOCK_TRAINING_DATA = [
    {
        "id": str(uuid4()),
        "source_feedback_id": MOCK_USER_FEEDBACK[2]["id"],
        "model_type": "voice_intent_recognition",
        "training_example": {
            "input": "Send report to Sara",
            "corrected_output": {
                "intent": "create_task",
                "entities": {
                    "action": "send",
                    "object": "report",
                    "recipient": "Sarah"  # Corrected
                }
            },
            "original_output": {
                "intent": "create_task",
                "entities": {
                    "action": "send",
                    "object": "report",
                    "recipient": "Sara"  # Original error
                }
            }
        },
        "added_to_training_set": True,
        "created_at": (datetime.utcnow() - timedelta(hours=2)).isoformat()
    },
    {
        "id": str(uuid4()),
        "source_feedback_id": MOCK_USER_FEEDBACK[1]["id"],
        "model_type": "priority_classification",
        "training_example": {
            "input": "Task was created with wrong priority - should have been urgent",
            "corrected_output": {
                "priority": "urgent",
                "confidence": 0.95
            },
            "original_output": {
                "priority": "normal",
                "confidence": 0.78
            },
            "context": {
                "keywords": ["wrong", "should have been urgent"],
                "task_content": "Security vulnerability found in production"
            }
        },
        "added_to_training_set": True,
        "created_at": (datetime.utcnow() - timedelta(hours=6)).isoformat()
    }
]


# Quality Metrics
QUALITY_METRICS = {
    "action_item_extraction": {
        "metric": "f1_score",
        "current_value": 0.925,
        "target_value": 0.95,
        "threshold_warning": 0.85,
        "threshold_critical": 0.80,
        "trend": "improving",
        "last_30_days": [
            {"date": (datetime.utcnow() - timedelta(days=i)).date().isoformat(), "value": 0.925 - (i * 0.002)}
            for i in range(30)
        ]
    },
    "voice_transcription_accuracy": {
        "metric": "word_error_rate",
        "current_value": 0.08,
        "target_value": 0.05,
        "threshold_warning": 0.12,
        "threshold_critical": 0.15,
        "trend": "improving",
        "last_30_days": [
            {"date": (datetime.utcnow() - timedelta(days=i)).date().isoformat(), "value": 0.08 + (i * 0.001)}
            for i in range(30)
        ]
    },
    "user_satisfaction": {
        "metric": "average_rating",
        "current_value": 4.3,
        "target_value": 4.5,
        "threshold_warning": 3.5,
        "threshold_critical": 3.0,
        "trend": "stable",
        "last_30_days": [
            {"date": (datetime.utcnow() - timedelta(days=i)).date().isoformat(), "value": 4.3 + (0.1 if i % 5 == 0 else 0)}
            for i in range(30)
        ]
    }
}


# A/B Test Results
MOCK_AB_TESTS = [
    {
        "test_id": "ab_test_voice_model",
        "name": "Voice Recognition Model Comparison",
        "variants": {
            "control": {
                "model": "whisper-base",
                "sample_size": 450,
                "accuracy": 0.92,
                "avg_latency_ms": 1200,
                "user_satisfaction": 4.1
            },
            "variant_a": {
                "model": "whisper-large",
                "sample_size": 442,
                "accuracy": 0.96,
                "avg_latency_ms": 2100,
                "user_satisfaction": 4.4
            }
        },
        "winner": "variant_a",
        "statistical_significance": 0.98,
        "started_at": (datetime.utcnow() - timedelta(days=14)).isoformat(),
        "ended_at": (datetime.utcnow() - timedelta(days=2)).isoformat()
    },
    {
        "test_id": "ab_test_summary_length",
        "name": "Video Summary Length Test",
        "variants": {
            "control": {
                "summary_length": "short",
                "sample_size": 120,
                "user_rating": 3.8,
                "completion_rate": 0.95
            },
            "variant_a": {
                "summary_length": "medium",
                "sample_size": 114,
                "user_rating": 4.3,
                "completion_rate": 0.87
            }
        },
        "winner": "variant_a",
        "statistical_significance": 0.94,
        "started_at": (datetime.utcnow() - timedelta(days=21)).isoformat(),
        "ended_at": (datetime.utcnow() - timedelta(days=7)).isoformat()
    }
]


def create_mock_feedback(
    feedback_type: str,
    source: str,
    rating: int = 4,
    comment: str = ""
) -> Dict[str, Any]:
    """Create a mock feedback entry"""
    return {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "workspace_id": str(uuid4()),
        "feedback_type": feedback_type,
        "source": source,
        "source_id": str(uuid4()),
        "rating": rating,
        "comment": comment,
        "created_at": datetime.utcnow().isoformat(),
        "metadata": {}
    }


def get_feedback_by_source(source: str) -> List[Dict[str, Any]]:
    """Get all feedback for a specific source"""
    return [
        feedback for feedback in MOCK_USER_FEEDBACK
        if feedback["source"] == source
    ]


def calculate_net_promoter_score(feedback_list: List[Dict[str, Any]]) -> float:
    """Calculate NPS from feedback ratings"""
    if not feedback_list:
        return 0.0

    promoters = sum(1 for f in feedback_list if f.get("rating", 0) >= 4)
    detractors = sum(1 for f in feedback_list if f.get("rating", 0) <= 2)
    total = len(feedback_list)

    return ((promoters - detractors) / total) * 100 if total > 0 else 0.0
