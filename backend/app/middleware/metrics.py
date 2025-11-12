"""
Prometheus Metrics Middleware
Automatically collects HTTP request/response metrics
"""
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.monitoring import (
    http_requests_total,
    http_request_duration_seconds,
    http_request_size_bytes,
    http_response_size_bytes
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically collect Prometheus metrics for HTTP requests

    Tracks:
    - Total requests by method, endpoint, and status code
    - Request duration by method and endpoint
    - Request and response sizes
    """

    def __init__(self, app: ASGIApp, excluded_paths: list[str] = None):
        """
        Initialize the metrics middleware

        Args:
            app: FastAPI application
            excluded_paths: List of paths to exclude from metrics (e.g., /metrics, /health)
        """
        super().__init__(app)
        self.excluded_paths = excluded_paths or ["/metrics", "/health", "/docs", "/redoc", "/openapi.json"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and collect metrics

        Args:
            request: FastAPI Request object
            call_next: Next middleware/route handler

        Returns:
            Response object
        """
        # Skip metrics collection for excluded paths
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.excluded_paths):
            return await call_next(request)

        # Extract method and endpoint
        method = request.method
        endpoint = self._get_endpoint_pattern(request)

        # Record request size
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                http_request_size_bytes.labels(method=method, endpoint=endpoint).observe(int(content_length))
            except (ValueError, TypeError):
                pass

        # Track request duration
        start_time = time.time()

        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as exc:
            # Record error metrics
            status_code = 500
            raise exc
        finally:
            # Calculate duration
            duration = time.time() - start_time

            # Record metrics
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status_code
            ).inc()

            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

        # Record response size
        if hasattr(response, 'headers'):
            content_length = response.headers.get("content-length")
            if content_length:
                try:
                    http_response_size_bytes.labels(
                        method=method,
                        endpoint=endpoint
                    ).observe(int(content_length))
                except (ValueError, TypeError):
                    pass

        return response

    @staticmethod
    def _get_endpoint_pattern(request: Request) -> str:
        """
        Extract the route pattern from the request

        Args:
            request: FastAPI Request object

        Returns:
            Route pattern string (e.g., /api/v1/users/{user_id})
        """
        # Try to get the route pattern from FastAPI
        if hasattr(request, 'scope') and 'route' in request.scope:
            route = request.scope['route']
            if hasattr(route, 'path'):
                return route.path

        # Fallback to the actual path
        path = request.url.path

        # Remove query parameters
        if '?' in path:
            path = path.split('?')[0]

        # Normalize path IDs (replace UUIDs and numeric IDs with placeholders)
        import re

        # Replace UUIDs
        path = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '/{id}',
            path,
            flags=re.IGNORECASE
        )

        # Replace numeric IDs
        path = re.sub(r'/\d+', '/{id}', path)

        return path or "/"


def install_metrics_middleware(app):
    """
    Install Prometheus metrics middleware on FastAPI app

    Args:
        app: FastAPI application instance
    """
    app.add_middleware(PrometheusMiddleware)
