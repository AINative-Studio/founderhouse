"""
Tests for Prometheus Monitoring Integration
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.monitoring import (
    metrics,
    get_metrics,
    set_app_info,
    http_requests_total,
    http_request_duration_seconds,
    user_registrations_total,
    user_logins_total,
    workspace_operations_total,
    llm_requests_total,
    llm_tokens_used_total,
    vector_searches_total,
    mcp_operations_total,
    errors_total,
    active_users
)


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


class TestMetricsEndpoint:
    """Test cases for the /metrics endpoint"""

    def test_metrics_endpoint_exists(self, client):
        """Test that /metrics endpoint is accessible"""
        response = client.get("/api/v1/metrics")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")

    def test_metrics_format(self, client):
        """Test that metrics are in Prometheus format"""
        response = client.get("/api/v1/metrics")
        metrics_text = response.text

        # Check for Prometheus format markers
        assert "# HELP" in metrics_text
        assert "# TYPE" in metrics_text

        # Check for expected metrics
        assert "http_requests_total" in metrics_text
        assert "http_request_duration_seconds" in metrics_text
        assert "user_registrations_total" in metrics_text
        assert "app_info" in metrics_text

    def test_metrics_endpoint_records_http_metrics(self, client):
        """Test that accessing /metrics records HTTP metrics"""
        # Make multiple requests
        for _ in range(3):
            client.get("/api/v1/health")

        response = client.get("/api/v1/metrics")
        metrics_text = response.text

        # Check that health endpoint requests were recorded
        assert 'endpoint="/api/v1/health"' in metrics_text
        assert 'method="GET"' in metrics_text
        assert 'status="200"' in metrics_text

    def test_http_metrics_include_all_endpoints(self, client):
        """Test that all endpoints including /metrics are tracked"""
        # Make requests to various endpoints
        client.get("/api/v1/health")
        response = client.get("/api/v1/metrics")
        metrics_text = response.text

        # Verify that both endpoints are tracked
        assert 'endpoint="/api/v1/health"' in metrics_text
        # Note: The metrics endpoint itself is also tracked, which is acceptable
        # as it provides visibility into how often metrics are being scraped


class TestMetricsRecorder:
    """Test cases for the MetricsRecorder class"""

    def test_record_user_registration(self):
        """Test recording user registration"""
        initial_value = user_registrations_total._value._value

        metrics.record_user_registration()

        new_value = user_registrations_total._value._value
        assert new_value == initial_value + 1

    def test_record_user_login_success(self):
        """Test recording successful user login"""
        metrics.record_user_login(success=True)

        # Get metrics output
        metrics_output = get_metrics().decode('utf-8')
        assert 'user_logins_total{status="success"}' in metrics_output

    def test_record_user_login_failure(self):
        """Test recording failed user login"""
        metrics.record_user_login(success=False)

        # Get metrics output
        metrics_output = get_metrics().decode('utf-8')
        assert 'user_logins_total{status="failure"}' in metrics_output

    def test_record_workspace_operation(self):
        """Test recording workspace operations"""
        metrics.record_workspace_operation("create", success=True)
        metrics.record_workspace_operation("delete", success=False)

        metrics_output = get_metrics().decode('utf-8')
        assert 'workspace_operations_total{operation="create",status="success"}' in metrics_output
        assert 'workspace_operations_total{operation="delete",status="failure"}' in metrics_output

    def test_record_vector_search(self):
        """Test recording vector search operations"""
        metrics.record_vector_search(duration=0.5, success=True)
        metrics.record_vector_search(duration=1.2, success=False)

        metrics_output = get_metrics().decode('utf-8')
        assert 'vector_searches_total{status="success"}' in metrics_output
        assert 'vector_searches_total{status="failure"}' in metrics_output
        assert 'vector_search_duration_seconds' in metrics_output

    def test_record_llm_request(self):
        """Test recording LLM API requests"""
        metrics.record_llm_request(
            provider="openai",
            model="gpt-4",
            status="success",
            duration=2.5,
            input_tokens=100,
            output_tokens=200,
            cost=0.05
        )

        metrics_output = get_metrics().decode('utf-8')
        assert 'llm_requests_total{model="gpt-4",provider="openai",status="success"}' in metrics_output
        assert 'llm_tokens_used_total{model="gpt-4",provider="openai",type="input"}' in metrics_output
        assert 'llm_tokens_used_total{model="gpt-4",provider="openai",type="output"}' in metrics_output
        assert 'llm_cost_dollars' in metrics_output

    def test_record_mcp_operation(self):
        """Test recording MCP operations"""
        metrics.record_mcp_operation(
            server="zoom",
            operation="list_meetings",
            status="success",
            duration=1.0
        )

        metrics_output = get_metrics().decode('utf-8')
        assert 'mcp_operations_total{operation="list_meetings",server="zoom",status="success"}' in metrics_output
        assert 'mcp_operation_duration_seconds' in metrics_output

    def test_record_error(self):
        """Test recording application errors"""
        metrics.record_error(error_type="ValidationError", severity="warning")
        metrics.record_error(error_type="DatabaseError", severity="error")

        metrics_output = get_metrics().decode('utf-8')
        assert 'errors_total{error_type="ValidationError",severity="warning"}' in metrics_output
        assert 'errors_total{error_type="DatabaseError",severity="error"}' in metrics_output

    def test_update_active_users(self):
        """Test updating active users gauge"""
        metrics.update_active_users(42)

        assert active_users._value._value == 42

        metrics.update_active_users(100)
        assert active_users._value._value == 100

    def test_update_db_connections(self):
        """Test updating database connection metrics"""
        metrics.update_db_connections(active=5, pool_size=10)

        metrics_output = get_metrics().decode('utf-8')
        assert 'db_connections_active 5.0' in metrics_output
        assert 'db_connection_pool_size 10.0' in metrics_output


class TestAppInfo:
    """Test cases for application info metric"""

    def test_set_app_info(self):
        """Test setting application information"""
        set_app_info(
            name="AI Chief of Staff",
            version="1.0.0",
            environment="test"
        )

        metrics_output = get_metrics().decode('utf-8')
        assert 'app_info' in metrics_output
        assert 'name="AI Chief of Staff"' in metrics_output
        assert 'version="1.0.0"' in metrics_output
        assert 'environment="test"' in metrics_output


class TestPrometheusMiddleware:
    """Test cases for Prometheus middleware"""

    def test_middleware_tracks_successful_requests(self, client):
        """Test that middleware tracks successful requests"""
        # Make a request
        response = client.get("/api/v1/health")
        assert response.status_code == 200

        # Check metrics
        metrics_output = get_metrics().decode('utf-8')
        assert 'http_requests_total' in metrics_output
        assert 'endpoint="/api/v1/health"' in metrics_output
        assert 'method="GET"' in metrics_output
        assert 'status="200"' in metrics_output

    def test_middleware_tracks_404_errors(self, client):
        """Test that middleware tracks 404 errors"""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404

        metrics_output = get_metrics().decode('utf-8')
        assert 'status="404"' in metrics_output

    def test_middleware_tracks_request_duration(self, client):
        """Test that middleware tracks request duration"""
        client.get("/api/v1/health")

        metrics_output = get_metrics().decode('utf-8')
        assert 'http_request_duration_seconds' in metrics_output
        assert 'endpoint="/api/v1/health"' in metrics_output

    def test_middleware_normalizes_uuid_paths(self, client):
        """Test that middleware normalizes UUID paths"""
        # This would normally track the actual UUID
        # but the middleware should normalize it to {id}
        test_uuid = "123e4567-e89b-12d3-a456-426614174000"
        client.get(f"/api/v1/workspaces/{test_uuid}")

        metrics_output = get_metrics().decode('utf-8')
        # Check that the path is normalized
        assert '/api/v1/workspaces/{id}' in metrics_output or \
               'endpoint="/api/v1/workspaces/{id}"' in metrics_output


class TestMetricsIntegration:
    """Integration tests for the complete monitoring stack"""

    def test_complete_metrics_workflow(self, client):
        """Test complete metrics collection workflow"""
        # Set up app info
        set_app_info(
            name="AI Chief of Staff",
            version="1.0.0",
            environment="test"
        )

        # Simulate various operations
        metrics.record_user_registration()
        metrics.record_user_login(success=True)
        metrics.record_workspace_operation("create", success=True)
        metrics.record_meeting_summary("zoom")
        metrics.record_vector_search(duration=0.3, success=True)
        metrics.record_llm_request("openai", "gpt-4", "success", 1.5, 50, 100, 0.01)
        metrics.record_mcp_operation("slack", "list_channels", "success", 0.8)

        # Make HTTP requests
        client.get("/api/v1/health")
        client.get("/api/v1/health")

        # Get all metrics
        metrics_output = get_metrics().decode('utf-8')

        # Verify all metrics are present
        assert 'app_info' in metrics_output
        assert 'http_requests_total' in metrics_output
        assert 'user_registrations_total' in metrics_output
        assert 'user_logins_total' in metrics_output
        assert 'workspace_operations_total' in metrics_output
        assert 'meeting_summaries_generated_total' in metrics_output
        assert 'vector_searches_total' in metrics_output
        assert 'llm_requests_total' in metrics_output
        assert 'mcp_operations_total' in metrics_output

    def test_metrics_persistence_across_requests(self, client):
        """Test that metrics persist across multiple requests"""
        # Record some metrics
        metrics.record_user_registration()

        # Make multiple requests to metrics endpoint
        response1 = client.get("/api/v1/metrics")
        response2 = client.get("/api/v1/metrics")

        # Both responses should contain the recorded metric
        assert 'user_registrations_total' in response1.text
        assert 'user_registrations_total' in response2.text
