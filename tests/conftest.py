"""
AI Chief of Staff - Test Configuration and Fixtures
Sprint 1: Core infrastructure testing setup

This module provides pytest fixtures for:
- Database connections and cleanup
- Supabase client mocking
- MCP integration mocking
- Test data factories
- Authentication mocking
"""

import asyncio
import os
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest
import pytest_asyncio
from faker import Faker
from httpx import AsyncClient
from supabase import Client, create_client

# Initialize Faker for test data
fake = Faker()


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create an instance of the default event loop for the test session.
    Ensures async tests run properly.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# ENVIRONMENT CONFIGURATION
# ============================================================================

@pytest.fixture(scope="session")
def test_env() -> dict:
    """Test environment configuration."""
    return {
        "ENVIRONMENT": "test",
        "SUPABASE_URL": os.getenv("SUPABASE_URL", "http://localhost:54321"),
        "SUPABASE_KEY": os.getenv("SUPABASE_KEY", "test_key_placeholder"),
        "POSTGRES_HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "POSTGRES_PORT": os.getenv("POSTGRES_PORT", "54322"),
        "POSTGRES_DB": os.getenv("POSTGRES_DB", "postgres"),
        "POSTGRES_USER": os.getenv("POSTGRES_USER", "postgres"),
        "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD", "postgres"),
    }


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest_asyncio.fixture
async def db_connection(test_env: dict) -> AsyncGenerator:
    """
    Provides an async database connection for testing.
    Automatically rolls back transactions after each test.
    """
    try:
        import asyncpg

        conn = await asyncpg.connect(
            host=test_env["POSTGRES_HOST"],
            port=int(test_env["POSTGRES_PORT"]),
            database=test_env["POSTGRES_DB"],
            user=test_env["POSTGRES_USER"],
            password=test_env["POSTGRES_PASSWORD"],
        )

        # Begin transaction
        transaction = conn.transaction()
        await transaction.start()

        yield conn

        # Rollback transaction to clean up
        await transaction.rollback()
        await conn.close()

    except Exception as e:
        pytest.skip(f"Database connection unavailable: {e}")


@pytest.fixture
def supabase_client_mock() -> Mock:
    """
    Mock Supabase client for testing without actual database.
    Provides standard Supabase API methods.
    """
    mock_client = MagicMock(spec=Client)

    # Mock table() chain
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table

    # Mock common query methods
    mock_table.select.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.delete.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.neq.return_value = mock_table
    mock_table.gt.return_value = mock_table
    mock_table.lt.return_value = mock_table
    mock_table.gte.return_value = mock_table
    mock_table.lte.return_value = mock_table
    mock_table.like.return_value = mock_table
    mock_table.ilike.return_value = mock_table
    mock_table.is_.return_value = mock_table
    mock_table.in_.return_value = mock_table
    mock_table.contains.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.limit.return_value = mock_table
    mock_table.single.return_value = mock_table

    # Mock execute
    mock_table.execute.return_value.data = []

    return mock_client


@pytest_asyncio.fixture
async def supabase_client(test_env: dict) -> Client:
    """
    Real Supabase client for integration tests.
    Only use when testing actual Supabase functionality.
    """
    try:
        client = create_client(
            test_env["SUPABASE_URL"],
            test_env["SUPABASE_KEY"]
        )
        yield client
    except Exception as e:
        pytest.skip(f"Supabase client unavailable: {e}")


# ============================================================================
# WORKSPACE FIXTURES
# ============================================================================

@pytest.fixture
def mock_workspace_id() -> str:
    """Generate a mock workspace ID."""
    return str(uuid4())


@pytest.fixture
def mock_user_id() -> str:
    """Generate a mock user ID."""
    return str(uuid4())


@pytest.fixture
def mock_founder_id() -> str:
    """Generate a mock founder ID."""
    return str(uuid4())


@pytest.fixture
def sample_workspace(mock_workspace_id: str) -> dict:
    """Sample workspace data for testing."""
    return {
        "id": mock_workspace_id,
        "name": fake.company(),
        "created_at": fake.iso8601(),
    }


@pytest.fixture
def sample_member(mock_workspace_id: str, mock_user_id: str) -> dict:
    """Sample member data for testing."""
    return {
        "id": str(uuid4()),
        "workspace_id": mock_workspace_id,
        "user_id": mock_user_id,
        "role": "admin",
        "created_at": fake.iso8601(),
    }


@pytest.fixture
def sample_founder(mock_workspace_id: str, mock_user_id: str, mock_founder_id: str) -> dict:
    """Sample founder data for testing."""
    return {
        "id": mock_founder_id,
        "workspace_id": mock_workspace_id,
        "user_id": mock_user_id,
        "display_name": fake.name(),
        "email": fake.email(),
        "preferences": {},
        "created_at": fake.iso8601(),
    }


# ============================================================================
# MCP INTEGRATION MOCKS
# ============================================================================

@pytest.fixture
def mock_zoom_mcp() -> AsyncMock:
    """Mock Zoom MCP integration."""
    mock = AsyncMock()
    mock.connect.return_value = {"status": "connected", "platform": "zoom"}
    mock.disconnect.return_value = {"status": "disconnected"}
    mock.fetch_meetings.return_value = []
    mock.health_check.return_value = {"status": "healthy"}
    return mock


@pytest.fixture
def mock_slack_mcp() -> AsyncMock:
    """Mock Slack MCP integration."""
    mock = AsyncMock()
    mock.connect.return_value = {"status": "connected", "platform": "slack"}
    mock.disconnect.return_value = {"status": "disconnected"}
    mock.fetch_messages.return_value = []
    mock.health_check.return_value = {"status": "healthy"}
    return mock


@pytest.fixture
def mock_fireflies_mcp() -> AsyncMock:
    """Mock Fireflies MCP integration."""
    mock = AsyncMock()
    mock.connect.return_value = {"status": "connected", "platform": "fireflies"}
    mock.disconnect.return_value = {"status": "disconnected"}
    mock.fetch_transcripts.return_value = []
    mock.health_check.return_value = {"status": "healthy"}
    return mock


@pytest.fixture
def mock_monday_mcp() -> AsyncMock:
    """Mock Monday.com MCP integration."""
    mock = AsyncMock()
    mock.connect.return_value = {"status": "connected", "platform": "monday"}
    mock.disconnect.return_value = {"status": "disconnected"}
    mock.create_task.return_value = {"id": "mock_task_id", "status": "created"}
    mock.health_check.return_value = {"status": "healthy"}
    return mock


@pytest.fixture
def mock_granola_mcp() -> AsyncMock:
    """Mock Granola MCP integration."""
    mock = AsyncMock()
    mock.connect.return_value = {"status": "connected", "platform": "granola"}
    mock.disconnect.return_value = {"status": "disconnected"}
    mock.fetch_kpis.return_value = {
        "mrr": 10000,
        "cac": 500,
        "churn": 0.05,
        "conversion_rate": 0.15,
    }
    mock.health_check.return_value = {"status": "healthy"}
    return mock


@pytest.fixture
def mock_mcp_registry(
    mock_zoom_mcp,
    mock_slack_mcp,
    mock_fireflies_mcp,
    mock_monday_mcp,
    mock_granola_mcp,
) -> dict:
    """Registry of all MCP mocks."""
    return {
        "zoom": mock_zoom_mcp,
        "slack": mock_slack_mcp,
        "fireflies": mock_fireflies_mcp,
        "monday": mock_monday_mcp,
        "granola": mock_granola_mcp,
    }


# ============================================================================
# AUTHENTICATION FIXTURES
# ============================================================================

@pytest.fixture
def mock_auth_token() -> str:
    """Mock JWT authentication token."""
    return "mock_jwt_token_" + fake.uuid4()


@pytest.fixture
def mock_auth_headers(mock_auth_token: str) -> dict:
    """Mock authentication headers."""
    return {
        "Authorization": f"Bearer {mock_auth_token}",
        "Content-Type": "application/json",
    }


@pytest.fixture
def mock_authenticated_user(mock_user_id: str) -> dict:
    """Mock authenticated user data."""
    return {
        "id": mock_user_id,
        "email": fake.email(),
        "role": "authenticated",
        "app_metadata": {},
        "user_metadata": {
            "display_name": fake.name(),
        },
    }


# ============================================================================
# API CLIENT FIXTURES
# ============================================================================

@pytest_asyncio.fixture
async def api_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP client for API testing.
    Use this to test FastAPI endpoints.
    """
    async with AsyncClient(base_url="http://testserver") as client:
        yield client


# ============================================================================
# VECTOR/EMBEDDING FIXTURES
# ============================================================================

@pytest.fixture
def mock_embedding() -> list[float]:
    """
    Generate a mock embedding vector (1536 dimensions for OpenAI).
    """
    import numpy as np
    return np.random.rand(1536).tolist()


@pytest.fixture
def mock_embedding_service() -> Mock:
    """Mock embedding service for vector generation."""
    mock = Mock()
    mock.generate_embedding.return_value = [0.1] * 1536
    mock.cosine_similarity.return_value = 0.95
    return mock


# ============================================================================
# EVENT LOGGING FIXTURES
# ============================================================================

@pytest.fixture
def sample_event(mock_workspace_id: str) -> dict:
    """Sample event data for testing."""
    return {
        "id": str(uuid4()),
        "workspace_id": mock_workspace_id,
        "actor_type": "user",
        "actor_id": str(uuid4()),
        "event_type": "workspace.created",
        "payload": {
            "action": "create",
            "entity": "workspace",
            "details": {"name": fake.company()},
        },
        "linked_entity": "workspace",
        "linked_id": mock_workspace_id,
        "created_at": fake.iso8601(),
    }


# ============================================================================
# TEST DATA CLEANUP
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_after_test():
    """
    Automatically runs after each test to clean up resources.
    """
    yield
    # Add any global cleanup logic here
    pass


# ============================================================================
# TEST MARKERS
# ============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "database: Tests requiring database")
    config.addinivalue_line("markers", "mcp: Tests involving MCP integrations")
    config.addinivalue_line("markers", "rls: Row-level security tests")
    config.addinivalue_line("markers", "vector: Vector/embedding tests")
