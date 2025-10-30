"""
Tests for health check endpoints
"""
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Test health check endpoint returns 200"""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert "timestamp" in data
    assert "version" in data


def test_version_endpoint(client: TestClient):
    """Test version endpoint returns correct format"""
    response = client.get("/version")
    assert response.status_code == 200

    data = response.json()
    assert "version" in data
    assert "api_version" in data
    assert "environment" in data


def test_ping_endpoint(client: TestClient):
    """Test simple ping endpoint"""
    response = client.get("/ping")
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "pong"
    assert "timestamp" in data


def test_root_endpoint(client: TestClient):
    """Test root endpoint returns API info"""
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "AI Chief of Staff API"
    assert "version" in data
    assert "docs" in data
    assert "health" in data
