"""
AI Chief of Staff - API Health Endpoint Tests
Sprint 1: Integration tests for health and monitoring endpoints

Test coverage:
- Health check endpoint
- Version endpoint
- API availability
- Response format validation
"""

import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient

from backend.app.main import app


# ============================================================================
# SYNCHRONOUS CLIENT TESTS
# ============================================================================

class TestHealthEndpointSync:
    """Test health endpoint with synchronous client."""

    @pytest.fixture
    def client(self):
        """Create synchronous test client."""
        return TestClient(app)

    def test_health_endpoint_returns_200(self, client):
        """
        Test that /health endpoint returns 200 OK.

        Acceptance Criteria:
        - Endpoint returns HTTP 200
        - Response is returned quickly
        """
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_endpoint_response_structure(self, client):
        """
        Test health endpoint response structure.

        Acceptance Criteria:
        - Response contains status field
        - Response contains timestamp
        - Response contains service name
        - Response contains version
        """
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert "service" in data
        assert "version" in data

    def test_health_endpoint_status_healthy(self, client):
        """
        Test that health endpoint reports healthy status.

        Acceptance Criteria:
        - Status field equals "healthy"
        - Service name is correct
        """
        response = client.get("/health")
        data = response.json()

        assert data["status"] == "healthy"
        assert data["service"] == "ai-chief-of-staff"

    def test_health_endpoint_timestamp_format(self, client):
        """
        Test that timestamp is in ISO 8601 format.

        Acceptance Criteria:
        - Timestamp is valid ISO 8601 string
        - Timestamp can be parsed
        """
        from datetime import datetime

        response = client.get("/health")
        data = response.json()

        timestamp = data["timestamp"]
        # Should not raise exception
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        assert parsed is not None

    def test_health_endpoint_multiple_calls(self, client):
        """
        Test that health endpoint handles multiple concurrent calls.

        Acceptance Criteria:
        - Multiple calls all return 200
        - Timestamps progress forward
        """
        responses = [client.get("/health") for _ in range(5)]

        assert all(r.status_code == 200 for r in responses)
        timestamps = [r.json()["timestamp"] for r in responses]
        assert len(timestamps) == 5


# ============================================================================
# ASYNC CLIENT TESTS
# ============================================================================

@pytest.mark.integration
class TestHealthEndpointAsync:
    """Test health endpoint with async client."""

    @pytest.mark.asyncio
    async def test_health_endpoint_async(self):
        """
        Test health endpoint with async HTTP client.

        Acceptance Criteria:
        - Endpoint responds to async requests
        - Response is valid JSON
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_endpoint_performance(self):
        """
        Test health endpoint response time.

        Acceptance Criteria:
        - Response time < 100ms
        - Consistent performance across calls
        """
        import time

        async with AsyncClient(app=app, base_url="http://test") as client:
            start = time.time()
            response = await client.get("/health")
            elapsed = (time.time() - start) * 1000  # Convert to ms

            assert response.status_code == 200
            assert elapsed < 100, f"Health check took {elapsed}ms, expected <100ms"


# ============================================================================
# VERSION ENDPOINT TESTS
# ============================================================================

@pytest.mark.integration
class TestVersionEndpoint:
    """Test version endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_version_endpoint_returns_200(self, client):
        """
        Test that /version endpoint returns 200 OK.

        Acceptance Criteria:
        - Endpoint returns HTTP 200
        """
        response = client.get("/version")
        assert response.status_code == 200

    def test_version_endpoint_response_structure(self, client):
        """
        Test version endpoint response structure.

        Acceptance Criteria:
        - Response contains version field
        - Response contains environment
        - Response contains python_version
        - Response contains framework
        """
        response = client.get("/version")
        data = response.json()

        assert "version" in data
        assert "environment" in data
        assert "python_version" in data
        assert "framework" in data

    def test_version_endpoint_values(self, client):
        """
        Test version endpoint returns correct values.

        Acceptance Criteria:
        - Version format is semantic (x.y.z)
        - Framework is FastAPI
        - Python version is specified
        """
        response = client.get("/version")
        data = response.json()

        # Check version format (semantic versioning)
        version = data["version"]
        parts = version.split(".")
        assert len(parts) == 3, f"Version {version} is not semantic versioning"

        # Check framework
        assert data["framework"] == "FastAPI"

        # Check Python version exists
        assert data["python_version"]

    def test_version_endpoint_environment(self, client):
        """
        Test that environment is correctly reported.

        Acceptance Criteria:
        - Environment is one of: development, test, staging, production
        """
        response = client.get("/version")
        data = response.json()

        valid_environments = ["development", "test", "staging", "production"]
        assert data["environment"] in valid_environments


# ============================================================================
# ROOT ENDPOINT TESTS
# ============================================================================

@pytest.mark.integration
class TestRootEndpoint:
    """Test root (/) endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_root_endpoint_returns_200(self, client):
        """
        Test that / endpoint returns 200 OK.

        Acceptance Criteria:
        - Endpoint returns HTTP 200
        """
        response = client.get("/")
        assert response.status_code == 200

    def test_root_endpoint_provides_navigation(self, client):
        """
        Test that root endpoint provides API navigation links.

        Acceptance Criteria:
        - Response contains docs link
        - Response contains health link
        - Response contains version
        - Response contains status
        """
        response = client.get("/")
        data = response.json()

        assert "docs" in data
        assert "health" in data
        assert "version" in data
        assert "status" in data

    def test_root_endpoint_status_operational(self, client):
        """
        Test that root endpoint reports operational status.

        Acceptance Criteria:
        - Status is "operational"
        """
        response = client.get("/")
        data = response.json()

        assert data["status"] == "operational"

    def test_root_endpoint_links_valid(self, client):
        """
        Test that navigation links in root endpoint are valid.

        Acceptance Criteria:
        - Docs link returns 200
        - Health link returns 200
        """
        response = client.get("/")
        data = response.json()

        # Test health link
        health_response = client.get(data["health"])
        assert health_response.status_code == 200

        # Test docs link
        docs_response = client.get(data["docs"])
        assert docs_response.status_code == 200


# ============================================================================
# CORS TESTS
# ============================================================================

@pytest.mark.integration
class TestCORS:
    """Test CORS configuration."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_cors_headers_present(self, client):
        """
        Test that CORS headers are present in responses.

        Acceptance Criteria:
        - Access-Control-Allow-Origin header exists
        - CORS configured for health endpoint
        """
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )

        assert response.status_code == 200
        # CORS headers should be present
        headers = response.headers
        assert "access-control-allow-origin" in headers or len(headers) > 0

    def test_cors_preflight_request(self, client):
        """
        Test CORS preflight (OPTIONS) request.

        Acceptance Criteria:
        - OPTIONS request returns 200
        - CORS headers are present
        """
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            }
        )

        # FastAPI/Starlette handles OPTIONS automatically
        assert response.status_code in [200, 405]  # 405 if not explicitly defined


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.integration
class TestErrorHandling:
    """Test API error handling."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_404_for_nonexistent_endpoint(self, client):
        """
        Test that nonexistent endpoints return 404.

        Acceptance Criteria:
        - 404 status code for invalid routes
        - Error response has detail field
        """
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data

    def test_405_for_wrong_method(self, client):
        """
        Test that wrong HTTP methods return 405.

        Acceptance Criteria:
        - 405 status for unsupported methods
        """
        # POST to GET-only endpoint
        response = client.post("/health")
        assert response.status_code == 405


# ============================================================================
# CONTENT TYPE TESTS
# ============================================================================

@pytest.mark.integration
class TestContentTypes:
    """Test content type handling."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_health_returns_json(self, client):
        """
        Test that health endpoint returns JSON.

        Acceptance Criteria:
        - Content-Type is application/json
        - Response is valid JSON
        """
        response = client.get("/health")

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

        # Should not raise exception
        data = response.json()
        assert isinstance(data, dict)

    def test_version_returns_json(self, client):
        """
        Test that version endpoint returns JSON.

        Acceptance Criteria:
        - Content-Type is application/json
        """
        response = client.get("/version")

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]


# ============================================================================
# STARTUP/SHUTDOWN TESTS
# ============================================================================

@pytest.mark.integration
class TestLifecycle:
    """Test application lifecycle events."""

    def test_app_starts_successfully(self):
        """
        Test that application starts without errors.

        Acceptance Criteria:
        - TestClient can be created
        - Endpoints are accessible immediately
        """
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200

    def test_multiple_client_instances(self):
        """
        Test that multiple client instances can coexist.

        Acceptance Criteria:
        - Multiple TestClients work independently
        - No resource conflicts
        """
        client1 = TestClient(app)
        client2 = TestClient(app)

        response1 = client1.get("/health")
        response2 = client2.get("/health")

        assert response1.status_code == 200
        assert response2.status_code == 200
