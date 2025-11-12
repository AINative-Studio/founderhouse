"""
Prometheus Metrics Collection and Monitoring
Centralized metrics for observability and monitoring
"""
import time
from typing import Callable, Optional
from functools import wraps

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    Summary,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST
)

# Create a custom registry for application metrics
registry = CollectorRegistry()

# ============================================================================
# HTTP Request Metrics
# ============================================================================

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=registry
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=registry
)

http_request_size_bytes = Summary(
    'http_request_size_bytes',
    'HTTP request size in bytes',
    ['method', 'endpoint'],
    registry=registry
)

http_response_size_bytes = Summary(
    'http_response_size_bytes',
    'HTTP response size in bytes',
    ['method', 'endpoint'],
    registry=registry
)

# ============================================================================
# Database Metrics
# ============================================================================

db_queries_total = Counter(
    'db_queries_total',
    'Total database queries',
    ['operation', 'table', 'status'],
    registry=registry
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation', 'table'],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
    registry=registry
)

db_connections_active = Gauge(
    'db_connections_active',
    'Number of active database connections',
    registry=registry
)

db_connection_pool_size = Gauge(
    'db_connection_pool_size',
    'Database connection pool size',
    registry=registry
)

# ============================================================================
# Business Metrics
# ============================================================================

user_registrations_total = Counter(
    'user_registrations_total',
    'Total user registrations',
    registry=registry
)

user_logins_total = Counter(
    'user_logins_total',
    'Total user logins',
    ['status'],
    registry=registry
)

workspace_operations_total = Counter(
    'workspace_operations_total',
    'Total workspace operations',
    ['operation', 'status'],
    registry=registry
)

meeting_summaries_generated_total = Counter(
    'meeting_summaries_generated_total',
    'Total meeting summaries generated',
    ['source'],
    registry=registry
)

communication_aggregations_total = Counter(
    'communication_aggregations_total',
    'Total communication aggregations',
    ['source', 'status'],
    registry=registry
)

task_syncs_total = Counter(
    'task_syncs_total',
    'Total task synchronizations',
    ['source', 'direction', 'status'],
    registry=registry
)

vector_searches_total = Counter(
    'vector_searches_total',
    'Total vector searches performed',
    ['status'],
    registry=registry
)

vector_search_duration_seconds = Histogram(
    'vector_search_duration_seconds',
    'Vector search duration in seconds',
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0),
    registry=registry
)

# ============================================================================
# LLM Metrics
# ============================================================================

llm_requests_total = Counter(
    'llm_requests_total',
    'Total LLM API requests',
    ['provider', 'model', 'status'],
    registry=registry
)

llm_tokens_used_total = Counter(
    'llm_tokens_used_total',
    'Total LLM tokens used',
    ['provider', 'model', 'type'],
    registry=registry
)

llm_request_duration_seconds = Histogram(
    'llm_request_duration_seconds',
    'LLM request duration in seconds',
    ['provider', 'model'],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
    registry=registry
)

llm_cost_dollars = Counter(
    'llm_cost_dollars',
    'Total LLM cost in dollars',
    ['provider', 'model'],
    registry=registry
)

# ============================================================================
# MCP Integration Metrics
# ============================================================================

mcp_connections_total = Counter(
    'mcp_connections_total',
    'Total MCP server connections',
    ['server', 'status'],
    registry=registry
)

mcp_operations_total = Counter(
    'mcp_operations_total',
    'Total MCP operations',
    ['server', 'operation', 'status'],
    registry=registry
)

mcp_operation_duration_seconds = Histogram(
    'mcp_operation_duration_seconds',
    'MCP operation duration in seconds',
    ['server', 'operation'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
    registry=registry
)

# ============================================================================
# System Metrics
# ============================================================================

app_info = Info(
    'app_info',
    'Application information',
    registry=registry
)

active_users = Gauge(
    'active_users',
    'Number of active users',
    registry=registry
)

cache_hits_total = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_type'],
    registry=registry
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache_type'],
    registry=registry
)

background_tasks_total = Counter(
    'background_tasks_total',
    'Total background tasks executed',
    ['task_type', 'status'],
    registry=registry
)

errors_total = Counter(
    'errors_total',
    'Total application errors',
    ['error_type', 'severity'],
    registry=registry
)


# ============================================================================
# Utility Functions
# ============================================================================

def track_time(metric: Histogram, labels: Optional[dict] = None):
    """
    Decorator to track execution time of functions

    Args:
        metric: Prometheus Histogram metric
        labels: Optional labels to add to the metric
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def get_metrics() -> bytes:
    """
    Get all metrics in Prometheus format

    Returns:
        Metrics data in Prometheus text format
    """
    return generate_latest(registry)


def get_content_type() -> str:
    """
    Get the content type for metrics endpoint

    Returns:
        Content type string for Prometheus metrics
    """
    return CONTENT_TYPE_LATEST


def set_app_info(name: str, version: str, environment: str):
    """
    Set application information metric

    Args:
        name: Application name
        version: Application version
        environment: Deployment environment
    """
    app_info.info({
        'name': name,
        'version': version,
        'environment': environment
    })


# ============================================================================
# Metric Recording Helpers
# ============================================================================

class MetricsRecorder:
    """Helper class for recording metrics"""

    @staticmethod
    def record_http_request(method: str, endpoint: str, status: int, duration: float):
        """Record HTTP request metrics"""
        http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)

    @staticmethod
    def record_db_query(operation: str, table: str, status: str, duration: float):
        """Record database query metrics"""
        db_queries_total.labels(operation=operation, table=table, status=status).inc()
        db_query_duration_seconds.labels(operation=operation, table=table).observe(duration)

    @staticmethod
    def record_user_registration():
        """Record user registration"""
        user_registrations_total.inc()

    @staticmethod
    def record_user_login(success: bool):
        """Record user login attempt"""
        status = "success" if success else "failure"
        user_logins_total.labels(status=status).inc()

    @staticmethod
    def record_workspace_operation(operation: str, success: bool):
        """Record workspace operation"""
        status = "success" if success else "failure"
        workspace_operations_total.labels(operation=operation, status=status).inc()

    @staticmethod
    def record_meeting_summary(source: str):
        """Record meeting summary generation"""
        meeting_summaries_generated_total.labels(source=source).inc()

    @staticmethod
    def record_vector_search(duration: float, success: bool):
        """Record vector search operation"""
        status = "success" if success else "failure"
        vector_searches_total.labels(status=status).inc()
        vector_search_duration_seconds.observe(duration)

    @staticmethod
    def record_llm_request(provider: str, model: str, status: str, duration: float,
                          input_tokens: int = 0, output_tokens: int = 0, cost: float = 0.0):
        """Record LLM API request"""
        llm_requests_total.labels(provider=provider, model=model, status=status).inc()
        llm_request_duration_seconds.labels(provider=provider, model=model).observe(duration)

        if input_tokens > 0:
            llm_tokens_used_total.labels(provider=provider, model=model, type="input").inc(input_tokens)
        if output_tokens > 0:
            llm_tokens_used_total.labels(provider=provider, model=model, type="output").inc(output_tokens)
        if cost > 0.0:
            llm_cost_dollars.labels(provider=provider, model=model).inc(cost)

    @staticmethod
    def record_mcp_operation(server: str, operation: str, status: str, duration: float):
        """Record MCP server operation"""
        mcp_operations_total.labels(server=server, operation=operation, status=status).inc()
        mcp_operation_duration_seconds.labels(server=server, operation=operation).observe(duration)

    @staticmethod
    def record_error(error_type: str, severity: str = "error"):
        """Record application error"""
        errors_total.labels(error_type=error_type, severity=severity).inc()

    @staticmethod
    def update_active_users(count: int):
        """Update active users gauge"""
        active_users.set(count)

    @staticmethod
    def update_db_connections(active: int, pool_size: int):
        """Update database connection metrics"""
        db_connections_active.set(active)
        db_connection_pool_size.set(pool_size)


# Create a singleton instance
metrics = MetricsRecorder()
