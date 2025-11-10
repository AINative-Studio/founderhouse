"""
Pytest configuration and fixtures
Sets up test environment and provides shared fixtures
"""
import os
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Load .env file first
from dotenv import load_dotenv
env_path = backend_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Set required environment variables for tests
os.environ.setdefault("ZERODB_EMAIL", os.getenv("ZERODB_EMAIL", "test@example.com"))
os.environ.setdefault("ZERODB_USERNAME", os.getenv("ZERODB_USERNAME", "test@example.com"))
os.environ.setdefault("ZERODB_PASSWORD", os.getenv("ZERODB_PASSWORD", "test-password"))
os.environ.setdefault("ZERODB_API_KEY", os.getenv("ZERODB_API_KEY", "test-api-key"))
os.environ.setdefault("ZERODB_PROJECT_ID", os.getenv("ZERODB_PROJECT_ID", "test-project-id"))
os.environ.setdefault("SECRET_KEY", os.getenv("SECRET_KEY", "test-secret-key-for-testing-only-minimum-32-chars"))

# Now safe to import app modules
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


@pytest.fixture
def mock_zerodb():
    """Mock ZeroDB client for testing"""
    from unittest.mock import AsyncMock, MagicMock

    mock_client = MagicMock()
    mock_client.store_memory = AsyncMock(return_value={"id": "test-memory-id"})
    mock_client.search_memory = AsyncMock(return_value=[])
    mock_client.store_vector = AsyncMock(return_value={"id": "test-vector-id"})
    mock_client.search_vectors = AsyncMock(return_value=[])
    mock_client.health_check = AsyncMock(return_value={"status": "healthy"})

    return mock_client
