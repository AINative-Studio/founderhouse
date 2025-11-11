"""
Integration tests for OAuth API endpoints
Tests OAuth2 authorization flows, token management, and callbacks
"""
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import status

from app.models.integration import Platform, IntegrationStatus, ConnectionType


@pytest.fixture
def mock_oauth_service():
    """Mock for OAuthService"""
    with patch('app.api.v1.oauth.OAuthService') as mock:
        service_instance = MagicMock()

        service_instance.generate_authorization_url = MagicMock(
            return_value="https://zoom.us/oauth/authorize?client_id=test&state=abc123"
        )

        service_instance.exchange_code_for_tokens = AsyncMock(return_value={
            "access_token": "access_token_123",
            "refresh_token": "refresh_token_456",
            "token_type": "Bearer",
            "expires_at": "2024-12-31T23:59:59",
            "scope": "meeting:read meeting:write",
            "workspace_id": str(uuid4())
        })

        service_instance.get_user_info = AsyncMock(return_value={
            "id": "user-123",
            "email": "user@example.com",
            "name": "Test User"
        })

        service_instance.check_token_validity = AsyncMock(return_value=True)
        service_instance.revoke_token = AsyncMock()

        mock.return_value = service_instance
        yield service_instance


@pytest.fixture
def mock_integration_service():
    """Mock for IntegrationService"""
    with patch('app.api.v1.oauth.IntegrationService') as mock:
        service_instance = MagicMock()

        # Mock integration
        mock_integration = MagicMock()
        mock_integration.id = uuid4()
        mock_integration.platform = Platform.ZOOM
        mock_integration.status = IntegrationStatus.CONNECTED
        mock_integration.metadata = {
            "access_token": "token_123",
            "refresh_token": "refresh_456"
        }

        service_instance.create_integration = AsyncMock(return_value=mock_integration)
        service_instance.get_integration = AsyncMock(return_value=mock_integration)
        service_instance.update_integration = AsyncMock(return_value=mock_integration)

        mock.return_value = service_instance
        yield service_instance


@pytest.fixture
def mock_settings():
    """Mock application settings"""
    with patch('app.api.v1.oauth.get_settings') as mock:
        settings = MagicMock()
        settings.zoom_client_id = "zoom_client_id"
        settings.zoom_client_secret = "zoom_client_secret"
        settings.slack_client_id = "slack_client_id"
        settings.slack_client_secret = "slack_client_secret"
        settings.discord_client_id = "discord_client_id"
        settings.discord_client_secret = "discord_client_secret"
        settings.api_v1_prefix = "/api/v1"
        settings.debug = True

        mock.return_value = settings
        yield settings


@pytest.fixture
def mock_oauth_provider():
    """Mock OAuth provider configuration"""
    with patch('app.api.v1.oauth.get_provider_for_platform') as mock:
        from app.core.oauth_config import OAuthProvider
        mock.return_value = OAuthProvider.ZOOM
        yield mock


class TestInitiateOAuth:
    """Tests for POST /oauth/{platform}/authorize endpoint"""

    @pytest.mark.asyncio
    async def test_initiate_zoom_oauth_success(
        self, client, mock_oauth_service, mock_oauth_provider, mock_settings
    ):
        """Test successful OAuth initiation for Zoom"""
        # Arrange
        platform = "zoom"

        # Act
        with patch('app.core.security.get_current_user') as mock_user:
            mock_user.return_value = MagicMock(user_id=uuid4())
            with patch('app.core.dependencies.get_workspace_id') as mock_workspace:
                mock_workspace.return_value = uuid4()
                response = client.post(f"/api/v1/oauth/{platform}/authorize")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "authorization_url" in data
        assert "state" in data
        assert data["platform"] == platform
        assert "zoom.us/oauth/authorize" in data["authorization_url"]

    @pytest.mark.asyncio
    async def test_initiate_slack_oauth_success(
        self, client, mock_oauth_service, mock_settings
    ):
        """Test successful OAuth initiation for Slack"""
        # Arrange
        platform = "slack"

        with patch('app.api.v1.oauth.get_provider_for_platform') as mock_provider:
            from app.core.oauth_config import OAuthProvider
            mock_provider.return_value = OAuthProvider.SLACK

            # Act
            with patch('app.core.security.get_current_user') as mock_user:
                mock_user.return_value = MagicMock(user_id=uuid4())
                with patch('app.core.dependencies.get_workspace_id') as mock_workspace:
                    mock_workspace.return_value = uuid4()
                    response = client.post(f"/api/v1/oauth/{platform}/authorize")

        # Assert
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_initiate_oauth_unsupported_platform(
        self, client, mock_settings
    ):
        """Test OAuth initiation with unsupported platform"""
        # Arrange
        platform = "unsupported_platform"

        with patch('app.api.v1.oauth.get_provider_for_platform') as mock_provider:
            mock_provider.return_value = None

            # Act
            with patch('app.core.security.get_current_user') as mock_user:
                mock_user.return_value = MagicMock(user_id=uuid4())
                with patch('app.core.dependencies.get_workspace_id') as mock_workspace:
                    mock_workspace.return_value = uuid4()
                    response = client.post(f"/api/v1/oauth/{platform}/authorize")

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_initiate_oauth_missing_credentials(
        self, client, mock_oauth_provider
    ):
        """Test OAuth initiation when credentials not configured"""
        # Arrange
        platform = "zoom"

        with patch('app.api.v1.oauth.get_settings') as mock_settings_call:
            settings = MagicMock()
            settings.zoom_client_id = None
            settings.zoom_client_secret = None
            mock_settings_call.return_value = settings

            # Act
            with patch('app.core.security.get_current_user') as mock_user:
                mock_user.return_value = MagicMock(user_id=uuid4())
                with patch('app.core.dependencies.get_workspace_id') as mock_workspace:
                    mock_workspace.return_value = uuid4()
                    response = client.post(f"/api/v1/oauth/{platform}/authorize")

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestOAuthCallback:
    """Tests for GET /oauth/{platform}/callback endpoint"""

    @pytest.mark.asyncio
    async def test_callback_success(
        self, client, mock_oauth_service, mock_integration_service, mock_oauth_provider
    ):
        """Test successful OAuth callback"""
        # Arrange
        platform = "zoom"
        code = "auth_code_123"
        state = "state_abc"

        # Act
        response = client.get(
            f"/api/v1/oauth/{platform}/callback",
            params={"code": code, "state": state},
            follow_redirects=False
        )

        # Assert
        assert response.status_code == status.HTTP_302_FOUND
        assert "success=true" in response.headers["location"]
        assert f"platform={platform}" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_callback_with_error(
        self, client, mock_oauth_provider
    ):
        """Test OAuth callback with error from provider"""
        # Arrange
        platform = "zoom"
        error = "access_denied"
        error_description = "User denied access"

        # Act
        response = client.get(
            f"/api/v1/oauth/{platform}/callback",
            params={"error": error, "error_description": error_description},
            follow_redirects=False
        )

        # Assert
        assert response.status_code == status.HTTP_302_FOUND
        assert f"error={error}" in response.headers["location"]
        assert f"platform={platform}" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_callback_token_exchange_failure(
        self, client, mock_oauth_service, mock_oauth_provider
    ):
        """Test callback when token exchange fails"""
        # Arrange
        platform = "zoom"
        code = "auth_code_123"
        state = "state_abc"

        mock_oauth_service.exchange_code_for_tokens = AsyncMock(
            side_effect=Exception("Token exchange failed")
        )

        # Act
        response = client.get(
            f"/api/v1/oauth/{platform}/callback",
            params={"code": code, "state": state},
            follow_redirects=False
        )

        # Assert
        assert response.status_code == status.HTTP_302_FOUND
        assert "error=callback_failed" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_callback_creates_integration(
        self, client, mock_oauth_service, mock_integration_service, mock_oauth_provider
    ):
        """Test that callback creates integration record"""
        # Arrange
        platform = "zoom"
        code = "auth_code_123"
        state = "state_abc"

        # Act
        response = client.get(
            f"/api/v1/oauth/{platform}/callback",
            params={"code": code, "state": state},
            follow_redirects=False
        )

        # Assert
        mock_integration_service.create_integration.assert_called_once()
        call_args = mock_integration_service.create_integration.call_args[0][0]
        assert call_args.connection_type == ConnectionType.MCP

    @pytest.mark.asyncio
    async def test_callback_slack_specific_data(
        self, client, mock_oauth_service, mock_integration_service
    ):
        """Test callback handles Slack-specific data"""
        # Arrange
        platform = "slack"
        code = "auth_code_123"
        state = "state_abc"

        # Add Slack-specific data to tokens
        mock_oauth_service.exchange_code_for_tokens = AsyncMock(return_value={
            "access_token": "xoxp-123",
            "refresh_token": "xoxr-456",
            "token_type": "Bearer",
            "workspace_id": str(uuid4()),
            "team_id": "T123456",
            "team_name": "Test Team",
            "user_id": "U123456"
        })

        with patch('app.api.v1.oauth.get_provider_for_platform') as mock_provider:
            from app.core.oauth_config import OAuthProvider
            mock_provider.return_value = OAuthProvider.SLACK

            # Act
            response = client.get(
                f"/api/v1/oauth/{platform}/callback",
                params={"code": code, "state": state},
                follow_redirects=False
            )

        # Assert
        assert response.status_code == status.HTTP_302_FOUND
        mock_integration_service.create_integration.assert_called_once()


class TestRefreshToken:
    """Tests for POST /oauth/{platform}/refresh endpoint"""

    @pytest.mark.asyncio
    async def test_refresh_token_success(
        self, client, mock_oauth_service, mock_integration_service, mock_oauth_provider
    ):
        """Test successful token refresh"""
        # Arrange
        platform = "zoom"
        integration_id = str(uuid4())

        # Act
        with patch('app.core.security.get_current_user') as mock_user:
            mock_user.return_value = MagicMock(user_id=uuid4())
            response = client.post(
                f"/api/v1/oauth/{platform}/refresh",
                params={"integration_id": integration_id}
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        mock_oauth_service.check_token_validity.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_token_failure(
        self, client, mock_oauth_service, mock_integration_service, mock_oauth_provider
    ):
        """Test token refresh failure"""
        # Arrange
        platform = "zoom"
        integration_id = str(uuid4())

        mock_oauth_service.check_token_validity = AsyncMock(return_value=False)

        # Act
        with patch('app.core.security.get_current_user') as mock_user:
            mock_user.return_value = MagicMock(user_id=uuid4())
            response = client.post(
                f"/api/v1/oauth/{platform}/refresh",
                params={"integration_id": integration_id}
            )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_refresh_token_service_error(
        self, client, mock_oauth_service, mock_integration_service, mock_oauth_provider
    ):
        """Test token refresh when service throws error"""
        # Arrange
        platform = "zoom"
        integration_id = str(uuid4())

        mock_oauth_service.check_token_validity = AsyncMock(
            side_effect=Exception("Token refresh error")
        )

        # Act
        with patch('app.core.security.get_current_user') as mock_user:
            mock_user.return_value = MagicMock(user_id=uuid4())
            response = client.post(
                f"/api/v1/oauth/{platform}/refresh",
                params={"integration_id": integration_id}
            )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestRevokeToken:
    """Tests for DELETE /oauth/{platform}/revoke endpoint"""

    @pytest.mark.asyncio
    async def test_revoke_token_success(
        self, client, mock_oauth_service, mock_integration_service, mock_oauth_provider
    ):
        """Test successful token revocation"""
        # Arrange
        platform = "zoom"
        integration_id = str(uuid4())

        # Act
        with patch('app.core.security.get_current_user') as mock_user:
            mock_user.return_value = MagicMock(user_id=uuid4())
            response = client.delete(
                f"/api/v1/oauth/{platform}/revoke",
                params={"integration_id": integration_id}
            )

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_oauth_service.revoke_token.assert_called()

    @pytest.mark.asyncio
    async def test_revoke_token_unsupported_platform(
        self, client, mock_integration_service
    ):
        """Test token revocation for unsupported platform"""
        # Arrange
        platform = "unsupported"
        integration_id = str(uuid4())

        with patch('app.api.v1.oauth.get_provider_for_platform') as mock_provider:
            mock_provider.return_value = None

            # Act
            with patch('app.core.security.get_current_user') as mock_user:
                mock_user.return_value = MagicMock(user_id=uuid4())
                response = client.delete(
                    f"/api/v1/oauth/{platform}/revoke",
                    params={"integration_id": integration_id}
                )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_revoke_token_updates_integration_status(
        self, client, mock_oauth_service, mock_integration_service, mock_oauth_provider
    ):
        """Test that revocation updates integration status"""
        # Arrange
        platform = "zoom"
        integration_id = str(uuid4())

        # Act
        with patch('app.core.security.get_current_user') as mock_user:
            mock_user.return_value = MagicMock(user_id=uuid4())
            response = client.delete(
                f"/api/v1/oauth/{platform}/revoke",
                params={"integration_id": integration_id}
            )

        # Assert
        mock_integration_service.update_integration.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_both_access_and_refresh_tokens(
        self, client, mock_oauth_service, mock_integration_service, mock_oauth_provider
    ):
        """Test that both access and refresh tokens are revoked"""
        # Arrange
        platform = "zoom"
        integration_id = str(uuid4())

        # Act
        with patch('app.core.security.get_current_user') as mock_user:
            mock_user.return_value = MagicMock(user_id=uuid4())
            response = client.delete(
                f"/api/v1/oauth/{platform}/revoke",
                params={"integration_id": integration_id}
            )

        # Assert
        # Should be called twice: once for access token, once for refresh token
        assert mock_oauth_service.revoke_token.call_count >= 1
