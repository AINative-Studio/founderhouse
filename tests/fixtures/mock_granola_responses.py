"""
AI Chief of Staff - Mock Granola MCP Responses
Sprint 4: Insights & Briefings Engine

Mock responses from the Granola MCP for testing KPI ingestion:
- Standard KPI pull
- Custom KPI pull
- Historical data
- Error responses
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import uuid4


# ============================================================================
# SUCCESSFUL RESPONSES
# ============================================================================

def get_standard_kpis_response() -> Dict:
    """
    Mock response for standard KPI pull from Granola MCP.
    Includes: MRR, CAC, churn, conversion, runway.
    """
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "mrr": {
                "value": 52500.00,
                "unit": "usd",
                "timestamp": datetime.utcnow().isoformat(),
                "change_7d": 5.2,
                "change_30d": 12.8,
                "confidence": 0.98
            },
            "arr": {
                "value": 630000.00,
                "unit": "usd",
                "timestamp": datetime.utcnow().isoformat(),
                "change_7d": 5.2,
                "change_30d": 12.8,
                "confidence": 0.98
            },
            "cac": {
                "value": 485.00,
                "unit": "usd",
                "timestamp": datetime.utcnow().isoformat(),
                "change_7d": -2.1,
                "change_30d": -5.4,
                "confidence": 0.95
            },
            "churn_rate": {
                "value": 0.048,
                "unit": "percent",
                "timestamp": datetime.utcnow().isoformat(),
                "change_7d": -0.5,
                "change_30d": -1.2,
                "confidence": 0.92
            },
            "conversion_rate": {
                "value": 0.152,
                "unit": "percent",
                "timestamp": datetime.utcnow().isoformat(),
                "change_7d": 1.8,
                "change_30d": 3.5,
                "confidence": 0.94
            },
            "runway_months": {
                "value": 18.5,
                "unit": "months",
                "timestamp": datetime.utcnow().isoformat(),
                "change_7d": 0.0,
                "change_30d": -0.5,
                "confidence": 0.97
            },
            "ltv": {
                "value": 2500.00,
                "unit": "usd",
                "timestamp": datetime.utcnow().isoformat(),
                "change_7d": 2.3,
                "change_30d": 5.8,
                "confidence": 0.90
            },
            "burn_rate": {
                "value": 24500.00,
                "unit": "usd",
                "timestamp": datetime.utcnow().isoformat(),
                "change_7d": -1.2,
                "change_30d": -3.5,
                "confidence": 0.96
            },
            "gross_margin": {
                "value": 0.72,
                "unit": "percent",
                "timestamp": datetime.utcnow().isoformat(),
                "change_7d": 0.5,
                "change_30d": 1.2,
                "confidence": 0.93
            },
            "net_revenue_retention": {
                "value": 1.15,
                "unit": "ratio",
                "timestamp": datetime.utcnow().isoformat(),
                "change_7d": 1.0,
                "change_30d": 2.5,
                "confidence": 0.91
            }
        },
        "metadata": {
            "source": "granola",
            "sync_id": str(uuid4()),
            "data_quality": "high",
            "last_updated": datetime.utcnow().isoformat()
        }
    }


def get_custom_kpis_response(workspace_id: str) -> Dict:
    """
    Mock response for custom KPI pull from Granola MCP.
    """
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "trial_to_paid_conversion": {
                "value": 0.28,
                "unit": "percent",
                "timestamp": datetime.utcnow().isoformat(),
                "confidence": 0.89,
                "custom": True,
                "formula": "(paid_users / trial_users) * 100"
            },
            "activation_rate": {
                "value": 0.65,
                "unit": "percent",
                "timestamp": datetime.utcnow().isoformat(),
                "confidence": 0.92,
                "custom": True,
                "formula": "(activated_users / signups) * 100"
            },
            "feature_adoption_score": {
                "value": 7.2,
                "unit": "score",
                "timestamp": datetime.utcnow().isoformat(),
                "confidence": 0.85,
                "custom": True,
                "formula": "weighted_average(feature_usage)"
            }
        },
        "metadata": {
            "source": "granola",
            "workspace_id": workspace_id,
            "custom_kpis": True,
            "sync_id": str(uuid4())
        }
    }


def get_historical_kpis_response(
    metric_name: str,
    days: int = 30
) -> Dict:
    """
    Mock response for historical KPI data from Granola MCP.

    Args:
        metric_name: Name of the metric
        days: Number of days of historical data

    Returns:
        Mock historical data response
    """
    data_points = []
    base_value = 10000.0 if metric_name == "mrr" else 500.0

    for i in range(days):
        timestamp = datetime.utcnow() - timedelta(days=days - i)
        # Simulate slight growth
        value = base_value * (1 + 0.001 * i)
        data_points.append({
            "timestamp": timestamp.isoformat(),
            "value": round(value, 2)
        })

    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "metric_name": metric_name,
            "data_points": data_points,
            "period": {
                "start": (datetime.utcnow() - timedelta(days=days)).isoformat(),
                "end": datetime.utcnow().isoformat(),
                "days": days
            }
        },
        "metadata": {
            "source": "granola",
            "historical": True,
            "sync_id": str(uuid4())
        }
    }


def get_derived_metrics_response() -> Dict:
    """
    Mock response for derived metrics calculation.
    """
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "ltv_to_cac_ratio": {
                "value": 5.15,
                "unit": "ratio",
                "timestamp": datetime.utcnow().isoformat(),
                "derived_from": ["ltv", "cac"],
                "formula": "ltv / cac",
                "confidence": 0.93
            },
            "magic_number": {
                "value": 0.75,
                "unit": "ratio",
                "timestamp": datetime.utcnow().isoformat(),
                "derived_from": ["mrr", "cac"],
                "formula": "(current_quarter_arr - previous_quarter_arr) / sales_marketing_spend",
                "confidence": 0.88
            },
            "payback_period": {
                "value": 8.2,
                "unit": "months",
                "timestamp": datetime.utcnow().isoformat(),
                "derived_from": ["cac", "mrr", "gross_margin"],
                "formula": "cac / (average_monthly_revenue * gross_margin)",
                "confidence": 0.90
            }
        },
        "metadata": {
            "source": "granola",
            "derived": True,
            "sync_id": str(uuid4())
        }
    }


def get_fresh_data_response() -> Dict:
    """
    Mock response with very fresh data (< 6 hours old).
    """
    fresh_timestamp = datetime.utcnow() - timedelta(hours=2)

    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "mrr": {
                "value": 52500.00,
                "unit": "usd",
                "timestamp": fresh_timestamp.isoformat(),
                "confidence": 0.98
            }
        },
        "metadata": {
            "source": "granola",
            "data_freshness_hours": 2.0,
            "sync_id": str(uuid4())
        }
    }


def get_stale_data_response() -> Dict:
    """
    Mock response with stale data (> 6 hours old).
    """
    stale_timestamp = datetime.utcnow() - timedelta(hours=10)

    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "mrr": {
                "value": 52500.00,
                "unit": "usd",
                "timestamp": stale_timestamp.isoformat(),
                "confidence": 0.98
            }
        },
        "metadata": {
            "source": "granola",
            "data_freshness_hours": 10.0,
            "sync_id": str(uuid4())
        },
        "warnings": [
            "Data is older than recommended threshold (>6 hours)"
        ]
    }


# ============================================================================
# ERROR RESPONSES
# ============================================================================

def get_authentication_error_response() -> Dict:
    """Mock response for authentication failure."""
    return {
        "status": "error",
        "error": {
            "code": "AUTHENTICATION_FAILED",
            "message": "Invalid API credentials",
            "type": "authentication_error"
        },
        "timestamp": datetime.utcnow().isoformat()
    }


def get_rate_limit_error_response() -> Dict:
    """Mock response for rate limiting."""
    return {
        "status": "error",
        "error": {
            "code": "RATE_LIMIT_EXCEEDED",
            "message": "API rate limit exceeded. Retry after 60 seconds.",
            "type": "rate_limit_error",
            "retry_after": 60
        },
        "timestamp": datetime.utcnow().isoformat()
    }


def get_not_found_error_response() -> Dict:
    """Mock response for metric not found."""
    return {
        "status": "error",
        "error": {
            "code": "METRIC_NOT_FOUND",
            "message": "Requested metric does not exist",
            "type": "not_found_error"
        },
        "timestamp": datetime.utcnow().isoformat()
    }


def get_validation_error_response() -> Dict:
    """Mock response for validation error."""
    return {
        "status": "error",
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Invalid metric parameters",
            "type": "validation_error",
            "details": {
                "field": "date_range",
                "issue": "Date range exceeds maximum allowed (365 days)"
            }
        },
        "timestamp": datetime.utcnow().isoformat()
    }


def get_timeout_error_response() -> Dict:
    """Mock response for request timeout."""
    return {
        "status": "error",
        "error": {
            "code": "REQUEST_TIMEOUT",
            "message": "Request timed out after 30 seconds",
            "type": "timeout_error"
        },
        "timestamp": datetime.utcnow().isoformat()
    }


def get_server_error_response() -> Dict:
    """Mock response for server error."""
    return {
        "status": "error",
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred on the server",
            "type": "server_error"
        },
        "timestamp": datetime.utcnow().isoformat()
    }


def get_partial_data_response() -> Dict:
    """
    Mock response with partial data (some metrics missing).
    """
    return {
        "status": "partial_success",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "mrr": {
                "value": 52500.00,
                "unit": "usd",
                "timestamp": datetime.utcnow().isoformat(),
                "confidence": 0.98
            },
            "cac": {
                "value": 485.00,
                "unit": "usd",
                "timestamp": datetime.utcnow().isoformat(),
                "confidence": 0.95
            }
        },
        "warnings": [
            "Failed to fetch: churn_rate (data source unavailable)",
            "Failed to fetch: conversion_rate (data source unavailable)"
        ],
        "metadata": {
            "source": "granola",
            "sync_id": str(uuid4()),
            "partial_data": True,
            "success_rate": 0.5
        }
    }


def get_missing_data_response(metric_name: str) -> Dict:
    """
    Mock response indicating missing data for a specific metric.
    """
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            metric_name: {
                "value": None,
                "unit": "usd",
                "timestamp": datetime.utcnow().isoformat(),
                "confidence": 0.0,
                "missing": True,
                "reason": "Insufficient data for calculation"
            }
        },
        "metadata": {
            "source": "granola",
            "sync_id": str(uuid4())
        }
    }


# ============================================================================
# SYNC STATUS RESPONSES
# ============================================================================

def get_sync_in_progress_response(sync_id: str) -> Dict:
    """Mock response for sync in progress."""
    return {
        "status": "in_progress",
        "sync_id": sync_id,
        "progress": 0.45,
        "started_at": (datetime.utcnow() - timedelta(minutes=2)).isoformat(),
        "estimated_completion": (datetime.utcnow() + timedelta(minutes=3)).isoformat()
    }


def get_sync_completed_response(sync_id: str) -> Dict:
    """Mock response for completed sync."""
    return {
        "status": "completed",
        "sync_id": sync_id,
        "progress": 1.0,
        "started_at": (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
        "completed_at": datetime.utcnow().isoformat(),
        "metrics_synced": 10,
        "errors": 0
    }


def get_sync_failed_response(sync_id: str) -> Dict:
    """Mock response for failed sync."""
    return {
        "status": "failed",
        "sync_id": sync_id,
        "progress": 0.3,
        "started_at": (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
        "failed_at": datetime.utcnow().isoformat(),
        "error": {
            "code": "SYNC_FAILED",
            "message": "Connection lost during sync",
            "type": "sync_error"
        }
    }


# ============================================================================
# BATCH RESPONSES
# ============================================================================

def get_batch_kpis_response(metric_names: List[str]) -> Dict:
    """
    Mock response for batch KPI fetch.

    Args:
        metric_names: List of metric names to fetch

    Returns:
        Mock batch response
    """
    data = {}
    standard_kpis = get_standard_kpis_response()["data"]

    for metric_name in metric_names:
        if metric_name in standard_kpis:
            data[metric_name] = standard_kpis[metric_name]

    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat(),
        "data": data,
        "metadata": {
            "source": "granola",
            "sync_id": str(uuid4()),
            "requested_metrics": len(metric_names),
            "returned_metrics": len(data)
        }
    }


# ============================================================================
# CONNECTION TEST RESPONSES
# ============================================================================

def get_connection_success_response() -> Dict:
    """Mock response for successful connection test."""
    return {
        "status": "success",
        "connected": True,
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": {
            "platform": "granola",
            "version": "1.0.0",
            "health": "healthy"
        }
    }


def get_connection_failed_response() -> Dict:
    """Mock response for failed connection test."""
    return {
        "status": "error",
        "connected": False,
        "error": {
            "code": "CONNECTION_FAILED",
            "message": "Unable to establish connection to Granola API",
            "type": "connection_error"
        },
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================================
# HEALTH CHECK RESPONSES
# ============================================================================

def get_health_check_healthy_response() -> Dict:
    """Mock response for healthy status."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "database": "healthy",
            "api": "healthy",
            "data_pipeline": "healthy"
        },
        "uptime_seconds": 86400,
        "last_sync": (datetime.utcnow() - timedelta(hours=4)).isoformat()
    }


def get_health_check_degraded_response() -> Dict:
    """Mock response for degraded status."""
    return {
        "status": "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "database": "healthy",
            "api": "degraded",
            "data_pipeline": "healthy"
        },
        "warnings": [
            "API response times elevated (avg: 2.5s)"
        ],
        "uptime_seconds": 86400,
        "last_sync": (datetime.utcnow() - timedelta(hours=8)).isoformat()
    }
