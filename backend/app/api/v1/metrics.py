"""
Prometheus Metrics Endpoint
Exposes application metrics for Prometheus scraping
"""
from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse

from app.core.monitoring import get_metrics, get_content_type

router = APIRouter()


@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    summary="Prometheus Metrics",
    description="""
    Exposes application metrics in Prometheus format for scraping.

    **Available Metrics:**

    ## HTTP Metrics
    - `http_requests_total`: Total HTTP requests by method, endpoint, and status
    - `http_request_duration_seconds`: HTTP request duration histogram
    - `http_request_size_bytes`: HTTP request size summary
    - `http_response_size_bytes`: HTTP response size summary

    ## Database Metrics
    - `db_queries_total`: Total database queries by operation, table, and status
    - `db_query_duration_seconds`: Database query duration histogram
    - `db_connections_active`: Number of active database connections
    - `db_connection_pool_size`: Database connection pool size

    ## Business Metrics
    - `user_registrations_total`: Total user registrations
    - `user_logins_total`: Total user logins by status
    - `workspace_operations_total`: Total workspace operations
    - `meeting_summaries_generated_total`: Total meeting summaries
    - `communication_aggregations_total`: Total communication aggregations
    - `task_syncs_total`: Total task synchronizations
    - `vector_searches_total`: Total vector searches
    - `vector_search_duration_seconds`: Vector search duration histogram

    ## LLM Metrics
    - `llm_requests_total`: Total LLM API requests by provider, model, and status
    - `llm_tokens_used_total`: Total LLM tokens used by provider, model, and type
    - `llm_request_duration_seconds`: LLM request duration histogram
    - `llm_cost_dollars`: Total LLM cost in dollars

    ## MCP Integration Metrics
    - `mcp_connections_total`: Total MCP server connections
    - `mcp_operations_total`: Total MCP operations
    - `mcp_operation_duration_seconds`: MCP operation duration histogram

    ## System Metrics
    - `app_info`: Application information
    - `active_users`: Number of active users
    - `cache_hits_total`: Total cache hits
    - `cache_misses_total`: Total cache misses
    - `background_tasks_total`: Total background tasks executed
    - `errors_total`: Total application errors

    **Usage:**

    Configure Prometheus to scrape this endpoint:
    ```yaml
    scrape_configs:
      - job_name: 'ai-chief-of-staff'
        static_configs:
          - targets: ['localhost:9000']
        metrics_path: '/api/v1/metrics'
    ```

    **Note:** This endpoint is publicly accessible and does not require authentication.
    It's designed to be scraped by Prometheus at regular intervals.
    """,
    tags=["monitoring"],
    include_in_schema=True
)
async def prometheus_metrics():
    """
    Expose Prometheus metrics

    Returns:
        Metrics in Prometheus text format
    """
    metrics_data = get_metrics()
    return Response(content=metrics_data, media_type=get_content_type())
