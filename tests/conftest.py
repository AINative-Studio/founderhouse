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
# OAUTH FIXTURES (Sprint 2)
# ============================================================================

@pytest.fixture
def mock_oauth_state() -> dict:
    """Generate mock OAuth state parameter."""
    from tests.fixtures.integration_fixtures import OAuthStateFactory
    return OAuthStateFactory()


@pytest.fixture
def mock_oauth_token() -> dict:
    """Generate mock OAuth token."""
    from tests.fixtures.integration_fixtures import OAuthTokenFactory
    return OAuthTokenFactory()


@pytest.fixture
def mock_oauth_service() -> Mock:
    """Mock OAuth service for testing."""
    mock = Mock()
    mock.generate_authorization_url.return_value = (
        "https://zoom.us/oauth/authorize?client_id=test&state=abc123",
        "abc123"
    )
    mock.exchange_code_for_token.return_value = {
        "access_token": "mock_access_token",
        "refresh_token": "mock_refresh_token",
        "expires_in": 3600
    }
    mock.refresh_token.return_value = {
        "access_token": "mock_refreshed_token",
        "expires_in": 3600
    }
    mock.validate_state.return_value = True
    mock.is_token_expired.return_value = False
    return mock


@pytest.fixture
def mock_oauth_provider_configs() -> dict:
    """Mock OAuth provider configurations."""
    return {
        "zoom": {
            "client_id": "test_zoom_client_id",
            "client_secret": "test_zoom_client_secret",
            "authorization_url": "https://zoom.us/oauth/authorize",
            "token_url": "https://zoom.us/oauth/token",
            "scopes": ["meeting:read", "meeting:write"]
        },
        "slack": {
            "client_id": "test_slack_client_id",
            "client_secret": "test_slack_client_secret",
            "authorization_url": "https://slack.com/oauth/v2/authorize",
            "token_url": "https://slack.com/api/oauth.v2.access",
            "scopes": ["channels:read", "chat:write"]
        },
        "discord": {
            "client_id": "test_discord_client_id",
            "client_secret": "test_discord_client_secret",
            "authorization_url": "https://discord.com/api/oauth2/authorize",
            "token_url": "https://discord.com/api/oauth2/token",
            "scopes": ["bot", "messages.read"]
        }
    }


# ============================================================================
# HEALTH CHECK FIXTURES (Sprint 2)
# ============================================================================

@pytest.fixture
def mock_health_check_service() -> AsyncMock:
    """Mock health check service."""
    mock = AsyncMock()
    mock.check_integration.return_value = {
        "is_healthy": True,
        "status": "connected",
        "response_time_ms": 150,
        "error_message": None
    }
    mock.check_all_integrations.return_value = []
    mock.schedule_health_checks.return_value = True
    return mock


@pytest.fixture
def mock_scheduler() -> Mock:
    """Mock APScheduler for testing scheduled health checks."""
    mock = Mock()
    mock.add_job.return_value = None
    mock.remove_job.return_value = None
    mock.get_jobs.return_value = []
    mock.start.return_value = None
    mock.shutdown.return_value = None
    return mock


# ============================================================================
# MCP CONNECTOR FIXTURES (Sprint 2)
# ============================================================================

@pytest.fixture
def mock_base_connector() -> AsyncMock:
    """Mock base MCP connector."""
    mock = AsyncMock()
    mock.connect.return_value = {"status": "connected"}
    mock.disconnect.return_value = {"status": "disconnected"}
    mock.test_connection.return_value = True
    mock.health_check.return_value = {"is_healthy": True}
    mock.encrypt_credentials.return_value = b"encrypted_data"
    mock.decrypt_credentials.return_value = {"key": "value"}
    return mock


@pytest.fixture
def mock_zoom_connector() -> AsyncMock:
    """Mock Zoom MCP connector with enhanced functionality."""
    from tests.fixtures.mcp_responses import (
        get_zoom_user_info,
        get_zoom_meetings_list
    )

    mock = AsyncMock()
    mock.connect.return_value = {"status": "connected", "platform": "zoom"}
    mock.disconnect.return_value = {"status": "disconnected"}
    mock.fetch_meetings.return_value = get_zoom_meetings_list()
    mock.get_user_info.return_value = get_zoom_user_info()
    mock.health_check.return_value = {"status": "healthy", "is_healthy": True}
    mock.test_connection.return_value = True
    mock.refresh_token.return_value = {
        "access_token": "new_zoom_token",
        "expires_in": 3600
    }
    return mock


@pytest.fixture
def mock_slack_connector() -> AsyncMock:
    """Mock Slack MCP connector with enhanced functionality."""
    from tests.fixtures.mcp_responses import (
        get_slack_auth_test,
        get_slack_messages_list
    )

    mock = AsyncMock()
    mock.connect.return_value = {"status": "connected", "platform": "slack"}
    mock.disconnect.return_value = {"status": "disconnected"}
    mock.fetch_messages.return_value = get_slack_messages_list()
    mock.auth_test.return_value = get_slack_auth_test()
    mock.health_check.return_value = {"status": "healthy", "is_healthy": True}
    mock.test_connection.return_value = True
    return mock


@pytest.fixture
def mock_discord_connector() -> AsyncMock:
    """Mock Discord MCP connector with enhanced functionality."""
    from tests.fixtures.mcp_responses import (
        get_discord_user_info,
        get_discord_messages_list
    )

    mock = AsyncMock()
    mock.connect.return_value = {"status": "connected", "platform": "discord"}
    mock.disconnect.return_value = {"status": "disconnected"}
    mock.fetch_messages.return_value = get_discord_messages_list()
    mock.get_user_info.return_value = get_discord_user_info()
    mock.health_check.return_value = {"status": "healthy", "is_healthy": True}
    mock.test_connection.return_value = True
    return mock


@pytest.fixture
def mock_outlook_connector() -> AsyncMock:
    """Mock Outlook MCP connector."""
    from tests.fixtures.mcp_responses import (
        get_outlook_user_profile,
        get_outlook_messages_list
    )

    mock = AsyncMock()
    mock.connect.return_value = {"status": "connected", "platform": "outlook"}
    mock.disconnect.return_value = {"status": "disconnected"}
    mock.fetch_messages.return_value = get_outlook_messages_list()
    mock.get_user_profile.return_value = get_outlook_user_profile()
    mock.health_check.return_value = {"status": "healthy", "is_healthy": True}
    mock.test_connection.return_value = True
    return mock


@pytest.fixture
def mock_monday_connector() -> AsyncMock:
    """Mock Monday.com MCP connector."""
    from tests.fixtures.mcp_responses import (
        get_monday_user_info,
        get_monday_boards_list,
        get_monday_create_item_response
    )

    mock = AsyncMock()
    mock.connect.return_value = {"status": "connected", "platform": "monday"}
    mock.disconnect.return_value = {"status": "disconnected"}
    mock.get_user_info.return_value = get_monday_user_info()
    mock.fetch_boards.return_value = get_monday_boards_list()
    mock.create_task.return_value = get_monday_create_item_response()
    mock.health_check.return_value = {"status": "healthy", "is_healthy": True}
    mock.test_connection.return_value = True
    return mock


@pytest.fixture
def mock_connector_registry(
    mock_zoom_connector,
    mock_slack_connector,
    mock_discord_connector,
    mock_outlook_connector,
    mock_monday_connector
) -> dict:
    """Enhanced MCP connector registry with all connectors."""
    return {
        "zoom": mock_zoom_connector,
        "slack": mock_slack_connector,
        "discord": mock_discord_connector,
        "outlook": mock_outlook_connector,
        "monday": mock_monday_connector
    }


# ============================================================================
# INTEGRATION SERVICE FIXTURES (Sprint 2)
# ============================================================================

@pytest.fixture
def mock_integration_service(supabase_client_mock) -> Mock:
    """Mock integration service for testing."""
    from app.services.integration_service import IntegrationService

    mock = Mock(spec=IntegrationService)
    mock.db = supabase_client_mock
    mock.create_integration = AsyncMock()
    mock.get_integration = AsyncMock()
    mock.list_integrations = AsyncMock(return_value=[])
    mock.update_integration = AsyncMock()
    mock.delete_integration = AsyncMock(return_value=True)
    mock.check_integration_health = AsyncMock()
    mock.get_integration_status = AsyncMock()

    return mock


@pytest.fixture
def sample_integration(mock_workspace_id: str) -> dict:
    """Sample integration data for testing."""
    from tests.fixtures.integration_fixtures import IntegrationFactory
    return IntegrationFactory.connected(workspace_id=mock_workspace_id)


@pytest.fixture
def sample_oauth_token(sample_integration: dict) -> dict:
    """Sample OAuth token for testing."""
    from tests.fixtures.integration_fixtures import OAuthTokenFactory
    return OAuthTokenFactory(integration_id=sample_integration["id"])


@pytest.fixture
def sample_health_check(sample_integration: dict) -> dict:
    """Sample health check for testing."""
    from tests.fixtures.integration_fixtures import HealthCheckFactory
    return HealthCheckFactory.healthy(
        integration_id=sample_integration["id"],
        platform=sample_integration["platform"]
    )


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
    config.addinivalue_line("markers", "oauth: OAuth flow tests (Sprint 2)")
    config.addinivalue_line("markers", "health: Health monitoring tests (Sprint 2)")
    config.addinivalue_line("markers", "connector: MCP connector tests (Sprint 2)")
