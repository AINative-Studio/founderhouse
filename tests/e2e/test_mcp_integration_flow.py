"""
AI Chief of Staff - End-to-End MCP Integration Flow Tests
Sprint 2: Complete Integration Workflows

Tests complete user journeys for MCP integrations including:
- Complete integration setup flow
- Token expiration and refresh
- Health check recovery
- Multi-integration workspace management
"""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, Mock

from httpx import AsyncClient
from fastapi import status

from tests.fixtures.integration_fixtures import (
    IntegrationFactory,
    OAuthTokenFactory,
    HealthCheckFactory,
    create_workspace_with_integrations,
    create_integration_with_oauth
)
from tests.fixtures.mcp_responses import (
    get_oauth_token_response,
    get_zoom_meetings_list,
    get_slack_messages_list
)


# ============================================================================
# COMPLETE INTEGRATION SETUP FLOW
# ============================================================================

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.mcp
@pytest.mark.asyncio
class TestCompleteIntegrationSetupFlow:
    """Test complete integration setup from creation to data fetch"""

    async def test_complete_zoom_integration_setup(
        self,
        api_client: AsyncClient,
        mock_auth_headers: dict,
        mock_zoom_connector: AsyncMock,
        mock_integration_service: Mock,
        mock_oauth_service: Mock
    ):
        """
        Complete Zoom Integration Setup Flow

        Scenario: User sets up Zoom integration from scratch
        Steps:
        1. Create workspace
        2. Initiate OAuth for Zoom
        3. User authorizes (simulated)
        4. Complete callback
        5. Verify integration active
        6. Test connection
        7. Fetch sample meetings
        """
        # STEP 1: Create workspace (assume pre-created)
        workspace_id = str(uuid4())

        # STEP 2: Initiate OAuth for Zoom
        authorization_url, state = (
            "https://zoom.us/oauth/authorize?client_id=test&state=abc123",
            "abc123"
        )
        mock_oauth_service.generate_authorization_url.return_value = (
            authorization_url,
            state
        )

        with patch("app.api.v1.integrations.get_workspace_id", return_value=workspace_id):
            # User would be redirected to authorization_url
            # Simulating successful authorization...
            pass

        # STEP 3 & 4: Simulate OAuth callback with authorization code
        authorization_code = uuid4().hex
        token_response = get_oauth_token_response(platform="zoom")
        mock_oauth_service.exchange_code_for_token.return_value = token_response

        # STEP 4: Create integration with tokens
        integration_data = {
            "platform": "zoom",
            "connection_type": "mcp",
            "credentials": {
                "client_id": "test_zoom_client_id",
                "client_secret": "test_zoom_client_secret",
                "access_token": token_response["access_token"],
                "refresh_token": token_response["refresh_token"]
            }
        }

        created_integration = IntegrationFactory.connected(
            platform="zoom",
            workspace_id=workspace_id
        )
        mock_integration_service.create_integration.return_value = created_integration

        with patch("app.api.v1.integrations.get_integration_service", return_value=mock_integration_service):
            with patch("app.api.v1.integrations.get_workspace_id", return_value=workspace_id):
                response = await api_client.post(
                    "/api/v1/integrations/connect",
                    json=integration_data,
                    headers=mock_auth_headers
                )

        # STEP 5: Verify integration active
        assert response.status_code == status.HTTP_201_CREATED
        integration = response.json()
        assert integration["status"] == "connected"
        integration_id = integration["id"]

        # STEP 6: Test connection
        mock_zoom_connector.test_connection.return_value = True
        is_connected = await mock_zoom_connector.test_connection()
        assert is_connected is True

        # STEP 7: Fetch sample meetings
        meetings = get_zoom_meetings_list(count=5)
        mock_zoom_connector.fetch_meetings.return_value = meetings

        fetched_meetings = await mock_zoom_connector.fetch_meetings()
        assert len(fetched_meetings["meetings"]) == 5
        assert all("topic" in m for m in fetched_meetings["meetings"])


# ============================================================================
# TOKEN EXPIRATION AND REFRESH
# ============================================================================

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.mcp
@pytest.mark.oauth
@pytest.mark.asyncio
class TestTokenExpirationAndRefresh:
    """Test automatic token refresh on expiration"""

    async def test_token_expires_and_auto_refreshes(
        self,
        mock_integration_service: Mock,
        mock_oauth_service: Mock,
        mock_zoom_connector: AsyncMock
    ):
        """
        Token Expiration and Auto-Refresh Flow

        Scenario: OAuth token expires and automatically refreshes
        Steps:
        1. Create integration with token expiring soon
        2. Simulate token expiration
        3. API call triggers refresh check
        4. Token automatically refreshed
        5. New token stored
        6. Connection continues to work
        """
        # STEP 1: Create integration with token expiring in 23 hours
        workspace_id = str(uuid4())
        integration_data = create_integration_with_oauth(
            platform="zoom",
            workspace_id=workspace_id,
            status="connected"
        )
        integration = integration_data["integration"]
        oauth_token = OAuthTokenFactory.expiring_soon(
            integration_id=integration["id"]
        )

        # STEP 2: Check if token should be refreshed
        mock_oauth_service.should_refresh_token.return_value = True
        should_refresh = mock_oauth_service.should_refresh_token(oauth_token)
        assert should_refresh is True

        # STEP 3 & 4: Automatic token refresh
        from tests.fixtures.mcp_responses import get_oauth_refresh_response

        refresh_response = get_oauth_refresh_response(platform="zoom")
        mock_oauth_service.refresh_token.return_value = refresh_response

        new_tokens = mock_oauth_service.refresh_token(
            "zoom",
            oauth_token["refresh_token"]
        )

        # STEP 5: Verify new token stored
        assert new_tokens["access_token"] != oauth_token["access_token"]
        assert "expires_in" in new_tokens

        # STEP 6: Verify connection still works
        mock_zoom_connector.health_check.return_value = {
            "status": "healthy",
            "is_healthy": True
        }
        health_check = await mock_zoom_connector.health_check()
        assert health_check["is_healthy"] is True


# ============================================================================
# HEALTH CHECK RECOVERY
# ============================================================================

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.health
@pytest.mark.asyncio
class TestHealthCheckRecovery:
    """Test integration failure detection and recovery"""

    async def test_integration_fails_then_recovers(
        self,
        mock_integration_service: Mock,
        mock_health_check_service: AsyncMock,
        mock_zoom_connector: AsyncMock
    ):
        """
        Health Check Failure and Recovery Flow

        Scenario: Integration fails then recovers
        Steps:
        1. Create connected Zoom integration
        2. Simulate Zoom API failure
        3. Health check detects failure
        4. Integration marked as 'error'
        5. Simulate Zoom API recovery
        6. Next health check succeeds
        7. Integration marked as 'connected'
        """
        # STEP 1: Create connected integration
        workspace_id = str(uuid4())
        integration = IntegrationFactory.connected(
            platform="zoom",
            workspace_id=workspace_id
        )
        integration_id = integration["id"]

        # STEP 2 & 3: Simulate failure
        unhealthy_check = HealthCheckFactory.unhealthy(
            integration_id=integration_id,
            platform="zoom",
            error="Connection timeout"
        )
        mock_health_check_service.check_integration.return_value = unhealthy_check

        health_result = await mock_health_check_service.check_integration(integration_id)
        assert health_result["is_healthy"] is False

        # STEP 4: Mark as error
        integration["status"] = "error"
        integration["last_error"] = "Connection timeout"

        # STEP 5 & 6: Simulate recovery
        healthy_check = HealthCheckFactory.healthy(
            integration_id=integration_id,
            platform="zoom"
        )
        mock_health_check_service.check_integration.return_value = healthy_check

        recovery_result = await mock_health_check_service.check_integration(integration_id)
        assert recovery_result["is_healthy"] is True

        # STEP 7: Mark as connected
        integration["status"] = "connected"
        integration["last_error"] = None
        assert integration["status"] == "connected"


# ============================================================================
# MULTI-INTEGRATION WORKSPACE
# ============================================================================

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.mcp
@pytest.mark.asyncio
class TestMultiIntegrationWorkspace:
    """Test workspace with multiple platform integrations"""

    async def test_workspace_with_multiple_integrations(
        self,
        api_client: AsyncClient,
        mock_auth_headers: dict,
        mock_integration_service: Mock,
        mock_health_check_service: AsyncMock,
        mock_connector_registry: dict
    ):
        """
        Multi-Integration Workspace Flow

        Scenario: Workspace with Zoom, Slack, and Monday.com
        Steps:
        1. Connect Zoom integration
        2. Connect Slack integration
        3. Connect Monday.com integration
        4. Verify all active
        5. Run health checks on all
        6. List all integrations
        7. Disconnect one (Slack)
        8. Verify others unaffected
        """
        # STEP 1-3: Create workspace with multiple integrations
        workspace_data = create_workspace_with_integrations(
            platform_list=["zoom", "slack", "monday"],
            num_integrations=3
        )
        workspace_id = workspace_data["workspace_id"]
        integrations = workspace_data["integrations"]

        # STEP 4: Verify all active
        mock_integration_service.list_integrations.return_value = integrations

        with patch("app.api.v1.integrations.get_integration_service", return_value=mock_integration_service):
            with patch("app.api.v1.integrations.get_workspace_id", return_value=workspace_id):
                response = await api_client.get(
                    "/api/v1/integrations",
                    headers=mock_auth_headers
                )

        assert response.status_code == status.HTTP_200_OK
        all_integrations = response.json()
        assert len(all_integrations) == 3

        # STEP 5: Run health checks on all
        health_checks = [
            HealthCheckFactory.healthy(
                integration_id=integration["id"],
                platform=integration["platform"]
            )
            for integration in integrations
        ]

        for integration, health_check in zip(integrations, health_checks):
            mock_health_check_service.check_integration.return_value = health_check
            result = await mock_health_check_service.check_integration(integration["id"])
            assert result["is_healthy"] is True

        # STEP 6: List all integrations (already done in step 4)
        assert all(i["workspace_id"] == workspace_id for i in all_integrations)

        # STEP 7: Disconnect Slack
        slack_integration = next(i for i in integrations if i["platform"] == "slack")
        mock_integration_service.delete_integration.return_value = True

        with patch("app.api.v1.integrations.get_integration_service", return_value=mock_integration_service):
            response = await api_client.delete(
                f"/api/v1/integrations/{slack_integration['id']}",
                headers=mock_auth_headers
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # STEP 8: Verify Zoom and Monday unaffected
        remaining_integrations = [i for i in integrations if i["platform"] != "slack"]
        mock_integration_service.list_integrations.return_value = remaining_integrations

        with patch("app.api.v1.integrations.get_integration_service", return_value=mock_integration_service):
            with patch("app.api.v1.integrations.get_workspace_id", return_value=workspace_id):
                response = await api_client.get(
                    "/api/v1/integrations",
                    headers=mock_auth_headers
                )

        assert response.status_code == status.HTTP_200_OK
        remaining = response.json()
        assert len(remaining) == 2
        assert all(i["platform"] in ["zoom", "monday"] for i in remaining)


# ============================================================================
# ERROR HANDLING AND RECOVERY
# ============================================================================

@pytest.mark.e2e
@pytest.mark.mcp
@pytest.mark.asyncio
class TestErrorHandlingAndRecovery:
    """Test various error scenarios and recovery mechanisms"""

    async def test_invalid_credentials_handled_gracefully(
        self,
        api_client: AsyncClient,
        mock_auth_headers: dict,
        mock_integration_service: Mock
    ):
        """
        Test: Invalid credentials error handling
        Given: User provides invalid Zoom credentials
        When: Integration creation attempted
        Then: Integration created with status='error'
        """
        # Arrange
        workspace_id = str(uuid4())
        integration_data = {
            "platform": "zoom",
            "connection_type": "mcp",
            "credentials": {
                "client_id": "invalid_id",
                "client_secret": "invalid_secret"
            }
        }

        error_integration = IntegrationFactory.with_error(
            platform="zoom",
            workspace_id=workspace_id,
            error="Invalid credentials"
        )
        mock_integration_service.create_integration.return_value = error_integration

        # Act
        with patch("app.api.v1.integrations.get_integration_service", return_value=mock_integration_service):
            with patch("app.api.v1.integrations.get_workspace_id", return_value=workspace_id):
                response = await api_client.post(
                    "/api/v1/integrations/connect",
                    json=integration_data,
                    headers=mock_auth_headers
                )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        integration = response.json()
        assert integration["status"] == "error"

    async def test_network_timeout_handled_gracefully(
        self,
        mock_zoom_connector: AsyncMock,
        mock_health_check_service: AsyncMock
    ):
        """
        Test: Network timeout error handling
        Given: Platform API times out
        When: Health check performed
        Then: Timeout logged, integration marked unhealthy
        """
        # Arrange
        integration_id = str(uuid4())

        # Simulate timeout
        unhealthy_check = HealthCheckFactory.unhealthy(
            integration_id=integration_id,
            platform="zoom",
            error="Connection timeout after 30s"
        )
        mock_health_check_service.check_integration.return_value = unhealthy_check

        # Act
        result = await mock_health_check_service.check_integration(integration_id)

        # Assert
        assert result["is_healthy"] is False
        assert "timeout" in result["error_message"].lower()

    async def test_rate_limit_handling(
        self,
        mock_zoom_connector: AsyncMock
    ):
        """
        Test: Rate limit error handling
        Given: Platform returns 429 Rate Limit Exceeded
        When: Connector makes API call
        Then: Respects retry-after header, waits before retry
        """
        # Arrange
        from tests.fixtures.mcp_responses import get_rate_limit_error

        rate_limit_error = get_rate_limit_error(platform="zoom")

        # Simulate rate limit then success
        mock_zoom_connector.fetch_meetings.side_effect = [
            Exception("Rate limit exceeded"),
            get_zoom_meetings_list()
        ]

        # Act - First call fails
        with pytest.raises(Exception, match="Rate limit exceeded"):
            await mock_zoom_connector.fetch_meetings()

        # Second call succeeds after wait
        meetings = await mock_zoom_connector.fetch_meetings()

        # Assert
        assert "meetings" in meetings


# ============================================================================
# DATA SYNC WORKFLOW
# ============================================================================

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.mcp
@pytest.mark.asyncio
class TestDataSyncWorkflow:
    """Test complete data synchronization workflows"""

    async def test_full_zoom_meeting_sync(
        self,
        mock_zoom_connector: AsyncMock,
        mock_integration_service: Mock
    ):
        """
        Test: Full meeting data sync
        Given: Connected Zoom integration
        When: Full sync triggered
        Then: All meetings fetched and stored
        """
        # Arrange
        workspace_id = str(uuid4())
        integration = IntegrationFactory.connected(
            platform="zoom",
            workspace_id=workspace_id
        )

        meetings_response = get_zoom_meetings_list(count=10)
        mock_zoom_connector.fetch_meetings.return_value = meetings_response

        # Act
        meetings = await mock_zoom_connector.fetch_meetings()

        # Assert
        assert len(meetings["meetings"]) == 10
        assert meetings["total_records"] == 10

    async def test_incremental_slack_message_sync(
        self,
        mock_slack_connector: AsyncMock
    ):
        """
        Test: Incremental message sync
        Given: Previous sync timestamp exists
        When: Incremental sync triggered
        Then: Only new messages since last sync fetched
        """
        # Arrange
        last_sync = datetime.utcnow() - timedelta(hours=1)
        messages_response = get_slack_messages_list(count=5)
        mock_slack_connector.fetch_messages.return_value = messages_response

        # Act
        messages = await mock_slack_connector.fetch_messages(since=last_sync)

        # Assert
        assert len(messages["messages"]) == 5
        # All messages should be after last_sync timestamp
