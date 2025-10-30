"""
Pytest configuration and fixtures
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import get_settings


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def test_settings():
    """Get test settings"""
    return get_settings()


@pytest.fixture
def auth_headers():
    """Create authentication headers for testing"""
    # In real tests, create a valid JWT token
    return {
        "Authorization": "Bearer test_token_here"
    }
