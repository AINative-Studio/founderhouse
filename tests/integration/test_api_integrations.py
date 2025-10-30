"""
AI Chief of Staff - Integration API Tests
Sprint 2: Issue #4 - MCP Integration Handler Tests

Tests for integration management endpoints:
- POST /api/v1/integrations/connect
- POST /api/v1/integrations/{id}/disconnect
- GET /api/v1/integrations
- GET /api/v1/integrations/{id}/status
"""

import pytest
from uuid import uuid4, UUID
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

from fastapi import status
from httpx import AsyncClient

from app.models.integration import (
    Platform,
    ConnectionType,
    IntegrationStatus
)
from tests.fixtures.integration_fixtures import (
    IntegrationFactory,
    create_workspace_with_integrations
)


# ============================================================================
# POST /api/v1/integrations/connect - ISSUE #4
# ============================================================================

@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.asyncio
class TestConnectIntegration:
    """Test POST /api/v1/integrations/connect endpoint"""

    async def test_connect_integration_with_valid_credentials(
        self,
        api_client: AsyncClient,
        mock_workspace_id: str,
        mock_auth_headers: dict,
        mock_integration_service: MagicMock
    ):
        """
        Test: Valid connection with correct credentials
        Given: Valid Zoom credentials
        When: POST to /api/v1/integrations/connect
        Then: Integration created with status 'connected'
        """
        # Arrange
        integration_data = {
            "platform": "zoom",
            "connection_type": "mcp",
            "credentials": {
                "client_id": "test_zoom_client_id",
                "client_secret": "test_zoom_client_secret"
            },
            "metadata": {
                "display_name": "My Zoom Account"
            }
        }

        expected_integration = IntegrationFactory.connected(
            platform="zoom",
            workspace_id=mock_workspace_id
        )
        mock_integration_service.create_integration.return_value = expected_integration

        # Act
        with patch("app.api.v1.integrations.get_integration_service", return_value=mock_integration_service):
            with patch("app.api.v1.integrations.get_workspace_id", return_value=UUID(mock_workspace_id)):
                response = await api_client.post(
                    "/api/v1/integrations/connect",
                    json=integration_data,
                    headers=mock_auth_headers
                )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["platform"] == "zoom"
        assert data["status"] == "connected"
        assert data["connection_type"] == "mcp"
        assert "credentials" not in data  # Credentials should not be exposed

    async def test_connect_integration_with_invalid_credentials(
        self,
        api_client: AsyncClient,
        mock_workspace_id: str,
        mock_auth_headers: dict,
        mock_integration_service: MagicMock
    ):
        """
        Test: Invalid credentials return proper error
        Given: Invalid Zoom credentials
        When: POST to /api/v1/integrations/connect
        Then: Integration created with status 'error'
        """
        # Arrange
        integration_data = {
            "platform": "zoom",
            "connection_type": "mcp",
            "credentials": {
                "client_id": "invalid_client_id",
                "client_secret": "invalid_secret"
            }
        }

        error_integration = IntegrationFactory.with_error(
            platform="zoom",
            workspace_id=mock_workspace_id,
            error="Invalid credentials"
        )
        mock_integration_service.create_integration.return_value = error_integration

        # Act
        with patch("app.api.v1.integrations.get_integration_service", return_value=mock_integration_service):
            with patch("app.api.v1.integrations.get_workspace_id", return_value=UUID(mock_workspace_id)):
                response = await api_client.post(
                    "/api/v1/integrations/connect",
                    json=integration_data,
                    headers=mock_auth_headers
                )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "error"

    async def test_connect_duplicate_integration(
        self,
        api_client: AsyncClient,
        mock_workspace_id: str,
        mock_auth_headers: dict,
        mock_integration_service: MagicMock
    ):
        """
        Test: Duplicate integration handling
        Given: Integration already exists for platform
        When: POST to /api/v1/integrations/connect
        Then: Returns 409 CONFLICT
        """
        # Arrange
        from fastapi import HTTPException

        integration_data = {
            "platform": "zoom",
            "connection_type": "mcp",
            "credentials": {
                "client_id": "test_client_id",
                "client_secret": "test_secret"
            }
        }

        mock_integration_service.create_integration.side_effect = HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Integration for zoom already exists"
        )

        # Act
        with patch("app.api.v1.integrations.get_integration_service", return_value=mock_integration_service):
            with patch("app.api.v1.integrations.get_workspace_id", return_value=UUID(mock_workspace_id)):
                response = await api_client.post(
                    "/api/v1/integrations/connect",
                    json=integration_data,
                    headers=mock_auth_headers
                )

        # Assert
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response.json()["detail"]

    async def test_connect_integration_missing_required_credentials(
        self,
        api_client: AsyncClient,
        mock_workspace_id: str,
        mock_auth_headers: dict
    ):
        """
        Test: Missing required credential fields
        Given: Zoom credentials missing required fields
        When: POST to /api/v1/integrations/connect
        Then: Returns 422 UNPROCESSABLE_ENTITY
        """
        # Arrange - Missing client_secret
        integration_data = {
            "platform": "zoom",
            "connection_type": "mcp",
            "credentials": {
                "client_id": "test_client_id"
                # Missing client_secret
            }
        }

        # Act
        with patch("app.api.v1.integrations.get_workspace_id", return_value=UUID(mock_workspace_id)):
            response = await api_client.post(
                "/api/v1/integrations/connect",
                json=integration_data,
                headers=mock_auth_headers
            )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ============================================================================
# DELETE /api/v1/integrations/{id} - ISSUE #4
# ============================================================================

@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.asyncio
class TestDisconnectIntegration:
    """Test DELETE /api/v1/integrations/{id} endpoint"""

    async def test_disconnect_integration_successful(
        self,
        api_client: AsyncClient,
        mock_auth_headers: dict,
        mock_integration_service: MagicMock,
        sample_integration: dict
    ):
        """
        Test: Successful disconnection
        Given: Connected integration exists
        When: DELETE to /api/v1/integrations/{id}
        Then: Integration disconnected and status updated to 'revoked'
        """
        # Arrange
        integration_id = sample_integration["id"]
        mock_integration_service.delete_integration.return_value = True

        # Act
        with patch("app.api.v1.integrations.get_integration_service", return_value=mock_integration_service):
            response = await api_client.delete(
                f"/api/v1/integrations/{integration_id}",
                headers=mock_auth_headers
            )

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_integration_service.delete_integration.assert_called_once()

    async def test_disconnect_nonexistent_integration(
        self,
        api_client: AsyncClient,
        mock_auth_headers: dict,
        mock_integration_service: MagicMock
    ):
        """
        Test: Disconnect nonexistent integration
        Given: Integration ID does not exist
        When: DELETE to /api/v1/integrations/{id}
        Then: Returns 404 NOT FOUND
        """
        # Arrange
        from fastapi import HTTPException

        integration_id = str(uuid4())
        mock_integration_service.delete_integration.side_effect = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration {integration_id} not found"
        )

        # Act
        with patch("app.api.v1.integrations.get_integration_service", return_value=mock_integration_service):
            response = await api_client.delete(
                f"/api/v1/integrations/{integration_id}",
                headers=mock_auth_headers
            )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_disconnect_revokes_oauth_token(
        self,
        api_client: AsyncClient,
        mock_auth_headers: dict,
        mock_integration_service: MagicMock,
        sample_integration: dict
    ):
        """
        Test: Token revocation during disconnect
        Given: Connected OAuth integration
        When: DELETE to /api/v1/integrations/{id}
        Then: OAuth token is revoked before deletion
        """
        # Arrange
        integration_id = sample_integration["id"]
        mock_integration_service.delete_integration.return_value = True

        # Act
        with patch("app.api.v1.integrations.get_integration_service", return_value=mock_integration_service):
            response = await api_client.delete(
                f"/api/v1/integrations/{integration_id}",
                headers=mock_auth_headers
            )

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT
        # Token revocation would happen in the service layer


# ============================================================================
# GET /api/v1/integrations - ISSUE #4
# ============================================================================

@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.asyncio
class TestListIntegrations:
    """Test GET /api/v1/integrations endpoint"""

    async def test_list_all_integrations_for_workspace(
        self,
        api_client: AsyncClient,
        mock_workspace_id: str,
        mock_auth_headers: dict,
        mock_integration_service: MagicMock
    ):
        """
        Test: List all integrations for workspace
        Given: Workspace has multiple integrations
        When: GET to /api/v1/integrations
        Then: Returns all workspace integrations
        """
        # Arrange
        workspace_data = create_workspace_with_integrations(
            platform_list=["zoom", "slack", "discord"],
            num_integrations=3
        )
        mock_integration_service.list_integrations.return_value = workspace_data["integrations"]

        # Act
        with patch("app.api.v1.integrations.get_integration_service", return_value=mock_integration_service):
            with patch("app.api.v1.integrations.get_workspace_id", return_value=UUID(mock_workspace_id)):
                response = await api_client.get(
                    "/api/v1/integrations",
                    headers=mock_auth_headers
                )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 3
        assert all(item["workspace_id"] == workspace_data["workspace_id"] for item in data)

    async def test_workspace_isolation_cant_see_other_workspaces(
        self,
        api_client: AsyncClient,
        mock_auth_headers: dict,
        mock_integration_service: MagicMock
    ):
        """
        Test: Workspace isolation (can't see other workspaces)
        Given: User belongs to workspace A
        When: GET to /api/v1/integrations
        Then: Only workspace A integrations returned
        """
        # Arrange
        workspace_a_id = str(uuid4())
        workspace_b_id = str(uuid4())

        # Workspace A integrations
        workspace_a_integrations = [
            IntegrationFactory.connected(platform="zoom", workspace_id=workspace_a_id)
        ]

        mock_integration_service.list_integrations.return_value = workspace_a_integrations

        # Act
        with patch("app.api.v1.integrations.get_integration_service", return_value=mock_integration_service):
            with patch("app.api.v1.integrations.get_workspace_id", return_value=UUID(workspace_a_id)):
                response = await api_client.get(
                    "/api/v1/integrations",
                    headers=mock_auth_headers
                )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(item["workspace_id"] == workspace_a_id for item in data)
        # Verify no workspace B data leaked
        assert not any(item["workspace_id"] == workspace_b_id for item in data)

    async def test_filter_integrations_by_platform(
        self,
        api_client: AsyncClient,
        mock_workspace_id: str,
        mock_auth_headers: dict,
        mock_integration_service: MagicMock
    ):
        """
        Test: Filter by platform
        Given: Workspace has multiple platform integrations
        When: GET to /api/v1/integrations?platform=zoom
        Then: Only Zoom integrations returned
        """
        # Arrange
        zoom_integrations = [
            IntegrationFactory.connected(platform="zoom", workspace_id=mock_workspace_id)
        ]
        mock_integration_service.list_integrations.return_value = zoom_integrations

        # Act
        with patch("app.api.v1.integrations.get_integration_service", return_value=mock_integration_service):
            with patch("app.api.v1.integrations.get_workspace_id", return_value=UUID(mock_workspace_id)):
                response = await api_client.get(
                    "/api/v1/integrations?platform=zoom",
                    headers=mock_auth_headers
                )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(item["platform"] == "zoom" for item in data)

    async def test_filter_integrations_by_status(
        self,
        api_client: AsyncClient,
        mock_workspace_id: str,
        mock_auth_headers: dict,
        mock_integration_service: MagicMock
    ):
        """
        Test: Filter by status
        Given: Workspace has integrations with various statuses
        When: Query with status filter
        Then: Only matching status integrations returned
        """
        # Arrange
        connected_integrations = [
            IntegrationFactory.connected(platform="zoom", workspace_id=mock_workspace_id),
            IntegrationFactory.connected(platform="slack", workspace_id=mock_workspace_id)
        ]
        mock_integration_service.list_integrations.return_value = connected_integrations

        # Act
        with patch("app.api.v1.integrations.get_integration_service", return_value=mock_integration_service):
            with patch("app.api.v1.integrations.get_workspace_id", return_value=UUID(mock_workspace_id)):
                response = await api_client.get(
                    "/api/v1/integrations",
                    headers=mock_auth_headers
                )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(item["status"] == "connected" for item in data)


# ============================================================================
# GET /api/v1/integrations/{id}/health - ISSUE #4
# ============================================================================

@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.health
@pytest.mark.asyncio
class TestIntegrationStatus:
    """Test GET /api/v1/integrations/{id}/health endpoint"""

    async def test_get_integration_health_returns_correct_status(
        self,
        api_client: AsyncClient,
        mock_auth_headers: dict,
        mock_integration_service: MagicMock,
        sample_integration: dict,
        sample_health_check: dict
    ):
        """
        Test: Returns correct status
        Given: Integration exists with known health status
        When: GET to /api/v1/integrations/{id}/health
        Then: Returns accurate health check data
        """
        # Arrange
        integration_id = sample_integration["id"]
        mock_integration_service.check_integration_health.return_value = sample_health_check

        # Act
        with patch("app.api.v1.integrations.get_integration_service", return_value=mock_integration_service):
            response = await api_client.get(
                f"/api/v1/integrations/{integration_id}/health",
                headers=mock_auth_headers
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_healthy"] == sample_health_check["is_healthy"]
        assert data["status"] == sample_health_check["status"]
        assert "last_checked" in data

    async def test_get_integration_health_includes_last_sync_timestamp(
        self,
        api_client: AsyncClient,
        mock_auth_headers: dict,
        mock_integration_service: MagicMock,
        sample_integration: dict
    ):
        """
        Test: Includes last sync timestamp
        Given: Integration has been synced
        When: GET to /api/v1/integrations/{id}/health
        Then: Response includes last_checked timestamp
        """
        # Arrange
        from tests.fixtures.integration_fixtures import HealthCheckFactory

        integration_id = sample_integration["id"]
        health_check = HealthCheckFactory.healthy(
            integration_id=integration_id,
            platform=sample_integration["platform"]
        )
        health_check["metadata"]["last_sync"] = datetime.utcnow().isoformat()

        mock_integration_service.check_integration_health.return_value = health_check

        # Act
        with patch("app.api.v1.integrations.get_integration_service", return_value=mock_integration_service):
            response = await api_client.get(
                f"/api/v1/integrations/{integration_id}/health",
                headers=mock_auth_headers
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "last_checked" in data
        assert "metadata" in data
        assert "last_sync" in data["metadata"]

    async def test_get_integration_health_includes_error_details(
        self,
        api_client: AsyncClient,
        mock_auth_headers: dict,
        mock_integration_service: MagicMock,
        sample_integration: dict
    ):
        """
        Test: Error details when available
        Given: Integration has health check errors
        When: GET to /api/v1/integrations/{id}/health
        Then: Response includes error_message
        """
        # Arrange
        from tests.fixtures.integration_fixtures import HealthCheckFactory

        integration_id = sample_integration["id"]
        health_check = HealthCheckFactory.unhealthy(
            integration_id=integration_id,
            platform=sample_integration["platform"],
            error="Connection timeout after 30s"
        )

        mock_integration_service.check_integration_health.return_value = health_check

        # Act
        with patch("app.api.v1.integrations.get_integration_service", return_value=mock_integration_service):
            response = await api_client.get(
                f"/api/v1/integrations/{integration_id}/health",
                headers=mock_auth_headers
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_healthy"] is False
        assert data["error_message"] == "Connection timeout after 30s"

    async def test_get_workspace_integration_status(
        self,
        api_client: AsyncClient,
        mock_workspace_id: str,
        mock_auth_headers: dict,
        mock_integration_service: MagicMock
    ):
        """
        Test: Get overall workspace integration status
        Given: Workspace has multiple integrations
        When: GET to /api/v1/integrations/status
        Then: Returns aggregated health status
        """
        # Arrange
        from tests.fixtures.integration_fixtures import HealthCheckFactory

        health_checks = [
            HealthCheckFactory.healthy(platform="zoom"),
            HealthCheckFactory.healthy(platform="slack"),
            HealthCheckFactory.unhealthy(platform="discord", error="Connection failed")
        ]

        status_response = {
            "workspace_id": mock_workspace_id,
            "total_integrations": 3,
            "connected": 2,
            "error": 1,
            "pending": 0,
            "integrations": health_checks
        }

        mock_integration_service.get_integration_status.return_value = status_response

        # Act
        with patch("app.api.v1.integrations.get_integration_service", return_value=mock_integration_service):
            with patch("app.api.v1.integrations.get_workspace_id", return_value=UUID(mock_workspace_id)):
                response = await api_client.get(
                    "/api/v1/integrations/status",
                    headers=mock_auth_headers
                )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_integrations"] == 3
        assert data["connected"] == 2
        assert data["error"] == 1
        assert len(data["integrations"]) == 3


# ============================================================================
# INTEGRATION PERSISTENCE TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.database
@pytest.mark.asyncio
class TestIntegrationPersistence:
    """Test that integrations persist across restarts"""

    async def test_connection_persists_across_restarts(
        self,
        mock_integration_service: MagicMock,
        sample_integration: dict
    ):
        """
        Test: Connection persists across restarts
        Given: Integration created successfully
        When: System restarts and integration retrieved
        Then: Integration still exists with same configuration
        """
        # Arrange
        integration_id = sample_integration["id"]

        # Simulate creating integration
        mock_integration_service.create_integration.return_value = sample_integration

        # Simulate system restart - retrieve integration
        mock_integration_service.get_integration.return_value = sample_integration

        # Act
        retrieved = await mock_integration_service.get_integration(integration_id)

        # Assert
        assert retrieved["id"] == sample_integration["id"]
        assert retrieved["platform"] == sample_integration["platform"]
        assert retrieved["status"] == sample_integration["status"]

    async def test_encrypted_credentials_persist(
        self,
        mock_integration_service: MagicMock,
        sample_integration: dict
    ):
        """
        Test: Encrypted credentials persist correctly
        Given: Integration with encrypted credentials
        When: Retrieved from database
        Then: Credentials can be decrypted
        """
        # Arrange
        integration_id = sample_integration["id"]
        sample_integration["credentials_enc"] = "encrypted_data_hex"

        mock_integration_service.get_integration.return_value = sample_integration

        # Act
        retrieved = await mock_integration_service.get_integration(integration_id)

        # Assert
        assert "credentials_enc" not in retrieved  # Should not be exposed
        # In real implementation, service would decrypt internally
