"""
Comprehensive tests for OAuth Service
Covers authorization flow, token exchange, refresh, revocation, and error handling
for all supported OAuth providers (Slack, Zoom, Google, Discord, etc.)
"""
import pytest
import json
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from urllib.parse import parse_qs, urlparse

from fastapi import HTTPException, status

from app.services.oauth_service import OAuthService
from app.core.oauth_config import OAuthProvider, OAuthConfig
from app.models.integration import Platform, IntegrationStatus


def create_mock_oauth_config(provider, client_id, client_secret, redirect_uri):
    """Helper to create mock OAuthConfig objects"""
    config_map = {
        OAuthProvider.SLACK: {
            "authorization_url": "https://slack.com/oauth/v2/authorize",
            "token_url": "https://slack.com/api/oauth.v2.access",
            "revoke_url": "https://slack.com/api/auth.revoke",
            "user_info_url": "https://slack.com/api/auth.test",
            "scopes": ["channels:history", "chat:write"]
        },
        OAuthProvider.ZOOM: {
            "authorization_url": "https://zoom.us/oauth/authorize",
            "token_url": "https://zoom.us/oauth/token",
            "revoke_url": "https://zoom.us/oauth/revoke",
            "user_info_url": "https://api.zoom.us/v2/users/me",
            "scopes": ["meeting:read"]
        },
        OAuthProvider.GOOGLE: {
            "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "revoke_url": "https://oauth2.googleapis.com/revoke",
            "user_info_url": "https://www.googleapis.com/oauth2/v2/userinfo",
            "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
            "extra_params": {"access_type": "offline", "prompt": "consent"}
        },
        OAuthProvider.DISCORD: {
            "authorization_url": "https://discord.com/api/oauth2/authorize",
            "token_url": "https://discord.com/api/oauth2/token",
            "revoke_url": "https://discord.com/api/oauth2/token/revoke",
            "user_info_url": "https://discord.com/api/users/@me",
            "scopes": ["identify", "guilds"]
        },
        OAuthProvider.NOTION: {
            "authorization_url": "https://api.notion.com/v1/oauth/authorize",
            "token_url": "https://api.notion.com/v1/oauth/token",
            "user_info_url": "https://api.notion.com/v1/users/me",
            "scopes": []
        },
        OAuthProvider.MICROSOFT: {
            "authorization_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            "user_info_url": "https://graph.microsoft.com/v1.0/me",
            "scopes": ["https://graph.microsoft.com/Mail.Read"]
        },
        OAuthProvider.MONDAY: {
            "authorization_url": "https://auth.monday.com/oauth2/authorize",
            "token_url": "https://auth.monday.com/oauth2/token",
            "user_info_url": "https://api.monday.com/v2",
            "scopes": ["boards:read"]
        },
        OAuthProvider.LOOM: {
            "authorization_url": "https://www.loom.com/oauth/authorize",
            "token_url": "https://www.loom.com/oauth/token",
            "user_info_url": "https://www.loom.com/api/v1/users/me",
            "scopes": ["video.read"]
        }
    }

    config_data = config_map.get(provider, {})
    return OAuthConfig(
        provider=provider,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        **config_data
    )


class TestOAuthServiceAuthorizationFlow:
    """Test OAuth authorization URL generation"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return Mock()

    @pytest.fixture
    def oauth_service(self, mock_db):
        """Create OAuthService instance"""
        return OAuthService(mock_db)

    @pytest.fixture
    def workspace_id(self):
        """Generate workspace ID"""
        return uuid4()

    def test_generate_authorization_url_slack(self, oauth_service, workspace_id):
        """Test Slack authorization URL generation"""
        # Arrange
        client_id = "slack-client-id"
        client_secret = "slack-secret"
        redirect_uri = "http://localhost:8000/oauth/callback"

        mock_config = create_mock_oauth_config(OAuthProvider.SLACK, client_id, client_secret, redirect_uri)

        with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
            # Act
            auth_url = oauth_service.generate_authorization_url(
                provider=OAuthProvider.SLACK,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                workspace_id=workspace_id
            )

            # Assert
            assert "https://slack.com/oauth/v2/authorize" in auth_url
            assert f"client_id={client_id}" in auth_url
            assert "response_type=code" in auth_url
            assert "state=" in auth_url

            # Extract and verify state was stored
            parsed_url = urlparse(auth_url)
            params = parse_qs(parsed_url.query)
            state = params["state"][0]
            assert state in oauth_service._oauth_states
            assert oauth_service._oauth_states[state]["provider"] == "slack"
            assert oauth_service._oauth_states[state]["workspace_id"] == str(workspace_id)

    def test_generate_authorization_url_zoom(self, oauth_service, workspace_id):
        """Test Zoom authorization URL generation"""
        # Arrange
        client_id = "zoom-client-id"
        client_secret = "zoom-secret"
        redirect_uri = "http://localhost:8000/oauth/callback"

        mock_config = create_mock_oauth_config(OAuthProvider.ZOOM, client_id, client_secret, redirect_uri)

        with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
            # Act
            auth_url = oauth_service.generate_authorization_url(
                provider=OAuthProvider.ZOOM,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                workspace_id=workspace_id
            )

            # Assert
            assert "https://zoom.us/oauth/authorize" in auth_url
            assert f"client_id={client_id}" in auth_url
            assert "scope=" in auth_url

    def test_generate_authorization_url_google(self, oauth_service, workspace_id):
        """Test Google OAuth authorization URL with extra params"""
        # Arrange
        client_id = "google-client-id"
        client_secret = "google-secret"
        redirect_uri = "http://localhost:8000/oauth/callback"

        mock_config = create_mock_oauth_config(OAuthProvider.GOOGLE, client_id, client_secret, redirect_uri)

        with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
            # Act
            auth_url = oauth_service.generate_authorization_url(
                provider=OAuthProvider.GOOGLE,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                workspace_id=workspace_id
            )

            # Assert
            assert "https://accounts.google.com/o/oauth2/v2/auth" in auth_url
            assert "access_type=offline" in auth_url
            assert "prompt=consent" in auth_url

    def test_generate_authorization_url_with_state_data(self, oauth_service, workspace_id):
        """Test authorization URL generation with additional state data"""
        # Arrange
        client_id = "client-id"
        client_secret = "secret"
        redirect_uri = "http://localhost:8000/oauth/callback"
        state_data = {"user_id": "user-123", "workspace_role": "admin"}

        mock_config = create_mock_oauth_config(OAuthProvider.SLACK, client_id, client_secret, redirect_uri)

        with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
            # Act
            auth_url = oauth_service.generate_authorization_url(
                provider=OAuthProvider.SLACK,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                workspace_id=workspace_id,
                state_data=state_data
            )

            # Assert
            parsed_url = urlparse(auth_url)
            params = parse_qs(parsed_url.query)
            state = params["state"][0]

            stored_state = oauth_service._oauth_states[state]
            assert stored_state["user_id"] == "user-123"
            assert stored_state["workspace_role"] == "admin"

    def test_generate_authorization_url_invalid_provider(self, oauth_service, workspace_id):
        """Test authorization URL generation with invalid provider"""
        # Arrange
        with patch("app.services.oauth_service.get_oauth_config", side_effect=ValueError("Unsupported provider")):
            # Act & Assert
            with pytest.raises(ValueError, match="Failed to generate authorization URL"):
                oauth_service.generate_authorization_url(
                    provider="invalid_provider",  # type: ignore
                    client_id="id",
                    client_secret="secret",
                    redirect_uri="http://localhost:8000/oauth/callback",
                    workspace_id=workspace_id
                )

    def test_generate_authorization_url_all_providers(self, oauth_service, workspace_id):
        """Test authorization URL generation for all supported providers"""
        # Arrange
        providers = [
            OAuthProvider.SLACK,
            OAuthProvider.ZOOM,
            OAuthProvider.GOOGLE,
            OAuthProvider.DISCORD,
            OAuthProvider.MICROSOFT,
            OAuthProvider.NOTION,
            OAuthProvider.MONDAY,
            OAuthProvider.LOOM
        ]

        # Act & Assert
        for provider in providers:
            mock_config = create_mock_oauth_config(provider, "test-client", "test-secret", "http://localhost")
            with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
                auth_url = oauth_service.generate_authorization_url(
                    provider=provider,
                    client_id="test-client",
                    client_secret="test-secret",
                    redirect_uri="http://localhost:8000/callback",
                    workspace_id=workspace_id
                )
                assert "state=" in auth_url
                assert "client_id=test-client" in auth_url


class TestOAuthServiceStateValidation:
    """Test OAuth state parameter validation"""

    @pytest.fixture
    def oauth_service(self):
        """Create OAuthService instance"""
        return OAuthService(Mock())

    def test_validate_state_valid(self, oauth_service):
        """Test validation of valid state parameter"""
        # Arrange
        state = "valid-state-token"
        workspace_id = uuid4()
        state_data = {
            "provider": "slack",
            "workspace_id": str(workspace_id),
            "created_at": datetime.utcnow().isoformat(),
            "redirect_uri": "http://localhost:8000/callback",
            "client_id": "client-id",
            "client_secret": "secret"
        }
        oauth_service._oauth_states[state] = state_data

        # Act
        result = oauth_service.validate_state(state)

        # Assert
        assert result["provider"] == "slack"
        assert result["workspace_id"] == str(workspace_id)

    def test_validate_state_invalid(self, oauth_service):
        """Test validation of invalid state parameter"""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            oauth_service.validate_state("invalid-state")

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid or expired" in exc_info.value.detail

    def test_validate_state_expired(self, oauth_service):
        """Test validation of expired state parameter"""
        # Arrange
        state = "expired-state"
        # Create state that's 16 minutes old (> 15 minute expiration)
        old_time = datetime.utcnow() - timedelta(minutes=16)
        oauth_service._oauth_states[state] = {
            "provider": "slack",
            "workspace_id": str(uuid4()),
            "created_at": old_time.isoformat(),
            "redirect_uri": "http://localhost",
            "client_id": "id",
            "client_secret": "secret"
        }

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            oauth_service.validate_state(state)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "expired" in exc_info.value.detail
        assert state not in oauth_service._oauth_states  # Expired state cleaned up

    def test_validate_state_just_before_expiration(self, oauth_service):
        """Test validation of state just before expiration"""
        # Arrange
        state = "nearly-expired"
        # Create state that's 14 minutes old (< 15 minute expiration)
        old_time = datetime.utcnow() - timedelta(minutes=14, seconds=59)
        state_data = {
            "provider": "slack",
            "workspace_id": str(uuid4()),
            "created_at": old_time.isoformat(),
            "redirect_uri": "http://localhost",
            "client_id": "id",
            "client_secret": "secret"
        }
        oauth_service._oauth_states[state] = state_data

        # Act
        result = oauth_service.validate_state(state)

        # Assert
        assert result is not None
        assert state in oauth_service._oauth_states


class TestOAuthServiceTokenExchange:
    """Test OAuth token exchange flow"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return Mock()

    @pytest.fixture
    def oauth_service(self, mock_db):
        """Create OAuthService instance"""
        return OAuthService(mock_db)

    @pytest.fixture
    def setup_oauth_state(self, oauth_service):
        """Helper to setup valid OAuth state"""
        def _setup(provider=OAuthProvider.SLACK):
            state = "test-state-123"
            workspace_id = uuid4()
            client_id = "test-client-id"
            client_secret = "test-secret"
            redirect_uri = "http://localhost:8000/callback"

            oauth_service._oauth_states[state] = {
                "provider": provider.value,
                "workspace_id": str(workspace_id),
                "created_at": datetime.utcnow().isoformat(),
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_secret": client_secret
            }
            return state, workspace_id, client_id, client_secret, redirect_uri
        return _setup

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_slack(self, oauth_service, setup_oauth_state):
        """Test token exchange for Slack"""
        # Arrange
        state, workspace_id, client_id, client_secret, redirect_uri = setup_oauth_state(OAuthProvider.SLACK)
        code = "auth-code-123"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "xoxb-slack-token",
            "token_type": "bot",
            "scope": "chat:write users:read",
            "bot_user_id": "U123456",
            "app_id": "A123456",
            "team": {
                "id": "T123456",
                "name": "My Workspace"
            },
            "authed_user": {
                "id": "U789012"
            }
        }

        mock_config = create_mock_oauth_config(OAuthProvider.SLACK, client_id, client_secret, redirect_uri)

        with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

                # Act
                result = await oauth_service.exchange_code_for_tokens(
                    provider=OAuthProvider.SLACK,
                    code=code,
                    state=state
                )

        # Assert
        assert result["access_token"] == "xoxb-slack-token"
        assert result["token_type"] == "bot"
        assert result["team_id"] == "T123456"
        assert result["team_name"] == "My Workspace"
        assert result["user_id"] == "U789012"
        assert "expires_at" in result
        assert state not in oauth_service._oauth_states  # State cleaned up

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_google(self, oauth_service, setup_oauth_state):
        """Test token exchange for Google"""
        # Arrange
        state, workspace_id, client_id, client_secret, redirect_uri = setup_oauth_state(OAuthProvider.GOOGLE)
        code = "google-auth-code"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "ya29.google-token",
            "expires_in": 3599,
            "refresh_token": "1//google-refresh-token",
            "scope": "https://www.googleapis.com/auth/gmail.readonly",
            "token_type": "Bearer"
        }

        mock_config = create_mock_oauth_config(OAuthProvider.GOOGLE, client_id, client_secret, redirect_uri)

        with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

                # Act
                result = await oauth_service.exchange_code_for_tokens(
                    provider=OAuthProvider.GOOGLE,
                    code=code,
                    state=state
                )

        # Assert
        assert result["access_token"] == "ya29.google-token"
        assert result["refresh_token"] == "1//google-refresh-token"
        assert result["expires_in"] == 3599

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_zoom(self, oauth_service, setup_oauth_state):
        """Test token exchange for Zoom"""
        # Arrange
        state, workspace_id, client_id, client_secret, redirect_uri = setup_oauth_state(OAuthProvider.ZOOM)
        code = "zoom-auth-code"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "zoom-access-token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "zoom-refresh-token"
        }

        mock_config = create_mock_oauth_config(OAuthProvider.ZOOM, client_id, client_secret, redirect_uri)

        with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

                # Act
                result = await oauth_service.exchange_code_for_tokens(
                    provider=OAuthProvider.ZOOM,
                    code=code,
                    state=state
                )

        # Assert
        assert result["access_token"] == "zoom-access-token"
        assert result["refresh_token"] == "zoom-refresh-token"
        assert result["provider"] == "zoom"

    @pytest.mark.asyncio
    async def test_exchange_code_invalid_state(self, oauth_service):
        """Test token exchange with invalid state"""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await oauth_service.exchange_code_for_tokens(
                provider=OAuthProvider.SLACK,
                code="code",
                state="invalid-state"
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_exchange_code_token_endpoint_error(self, oauth_service, setup_oauth_state):
        """Test token exchange when token endpoint returns error"""
        # Arrange
        state, workspace_id, client_id, client_secret, redirect_uri = setup_oauth_state()
        code = "code"

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid authorization code"

        mock_config = create_mock_oauth_config(OAuthProvider.SLACK, client_id, client_secret, redirect_uri)

        with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

                # Act & Assert
                with pytest.raises(HTTPException) as exc_info:
                    await oauth_service.exchange_code_for_tokens(
                        provider=OAuthProvider.SLACK,
                        code=code,
                        state=state
                    )

                assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_exchange_code_network_error(self, oauth_service, setup_oauth_state):
        """Test token exchange with network error"""
        # Arrange
        state, workspace_id, client_id, client_secret, redirect_uri = setup_oauth_state()
        code = "code"

        mock_config = create_mock_oauth_config(OAuthProvider.SLACK, client_id, client_secret, redirect_uri)

        with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    side_effect=Exception("Network error")
                )

                # Act & Assert
                with pytest.raises(HTTPException) as exc_info:
                    await oauth_service.exchange_code_for_tokens(
                        provider=OAuthProvider.SLACK,
                        code=code,
                        state=state
                    )

                assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestOAuthServiceTokenRefresh:
    """Test OAuth token refresh flow"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return Mock()

    @pytest.fixture
    def oauth_service(self, mock_db):
        """Create OAuthService instance"""
        return OAuthService(mock_db)

    @pytest.mark.asyncio
    async def test_refresh_access_token_slack(self, oauth_service):
        """Test token refresh for Slack"""
        # Arrange
        provider = OAuthProvider.SLACK
        refresh_token = "xoxe-slack-refresh-token"
        client_id = "client-id"
        client_secret = "secret"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "xoxb-new-token",
            "token_type": "bot",
            "expires_in": 3600,
            "scope": "chat:write"
        }

        mock_config = create_mock_oauth_config(provider, client_id, client_secret, "http://localhost")

        with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

                # Act
                result = await oauth_service.refresh_access_token(
                    provider=provider,
                    refresh_token=refresh_token,
                    client_id=client_id,
                    client_secret=client_secret
                )

        # Assert
        assert result["access_token"] == "xoxb-new-token"
        assert result["refresh_token"] == refresh_token  # Slack may not return new refresh_token

    @pytest.mark.asyncio
    async def test_refresh_access_token_google(self, oauth_service):
        """Test token refresh for Google"""
        # Arrange
        provider = OAuthProvider.GOOGLE
        refresh_token = "google-refresh-token"
        client_id = "google-client-id"
        client_secret = "google-secret"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "ya29.new-google-token",
            "expires_in": 3599,
            "token_type": "Bearer"
        }

        mock_config = create_mock_oauth_config(provider, client_id, client_secret, "http://localhost")

        with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

                # Act
                result = await oauth_service.refresh_access_token(
                    provider=provider,
                    refresh_token=refresh_token,
                    client_id=client_id,
                    client_secret=client_secret
                )

        # Assert
        assert result["access_token"] == "ya29.new-google-token"
        assert result["expires_in"] == 3599

    @pytest.mark.asyncio
    async def test_refresh_access_token_zoom(self, oauth_service):
        """Test token refresh for Zoom"""
        # Arrange
        provider = OAuthProvider.ZOOM
        refresh_token = "zoom-refresh-token"
        client_id = "zoom-id"
        client_secret = "zoom-secret"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "zoom-new-access-token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "zoom-new-refresh-token"
        }

        mock_config = create_mock_oauth_config(provider, client_id, client_secret, "http://localhost")

        with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

                # Act
                result = await oauth_service.refresh_access_token(
                    provider=provider,
                    refresh_token=refresh_token,
                    client_id=client_id,
                    client_secret=client_secret
                )

        # Assert
        assert result["access_token"] == "zoom-new-access-token"
        assert result["refresh_token"] == "zoom-new-refresh-token"

    @pytest.mark.asyncio
    async def test_refresh_access_token_endpoint_error(self, oauth_service):
        """Test token refresh when endpoint returns error"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Invalid refresh token"

        mock_config = create_mock_oauth_config(OAuthProvider.SLACK, "id", "secret", "http://localhost")

        with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

                # Act & Assert
                with pytest.raises(HTTPException) as exc_info:
                    await oauth_service.refresh_access_token(
                        provider=OAuthProvider.SLACK,
                        refresh_token="invalid-token",
                        client_id="id",
                        client_secret="secret"
                    )

                assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_refresh_access_token_network_error(self, oauth_service):
        """Test token refresh with network error"""
        # Arrange
        mock_config = create_mock_oauth_config(OAuthProvider.GOOGLE, "id", "secret", "http://localhost")

        with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    side_effect=Exception("Connection timeout")
                )

                # Act & Assert
                with pytest.raises(HTTPException) as exc_info:
                    await oauth_service.refresh_access_token(
                        provider=OAuthProvider.GOOGLE,
                        refresh_token="token",
                        client_id="id",
                        client_secret="secret"
                    )

                assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestOAuthServiceTokenRevocation:
    """Test OAuth token revocation"""

    @pytest.fixture
    def oauth_service(self):
        """Create OAuthService instance"""
        return OAuthService(Mock())

    @pytest.mark.asyncio
    async def test_revoke_token_slack_success(self, oauth_service):
        """Test successful token revocation for Slack"""
        # Arrange
        access_token = "xoxb-token-to-revoke"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}

        mock_config = create_mock_oauth_config(OAuthProvider.SLACK, "id", "secret", "http://localhost")

        with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

                # Act
                result = await oauth_service.revoke_token(
                    provider=OAuthProvider.SLACK,
                    token=access_token,
                    client_id="id",
                    client_secret="secret"
                )

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_revoke_token_google_204_response(self, oauth_service):
        """Test token revocation with 204 No Content response"""
        # Arrange
        access_token = "google-token"

        mock_response = Mock()
        mock_response.status_code = 204

        mock_config = create_mock_oauth_config(OAuthProvider.GOOGLE, "id", "secret", "http://localhost")

        with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

                # Act
                result = await oauth_service.revoke_token(
                    provider=OAuthProvider.GOOGLE,
                    token=access_token,
                    client_id="id",
                    client_secret="secret"
                )

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_revoke_token_no_revoke_url(self, oauth_service):
        """Test token revocation when provider has no revoke URL"""
        # Arrange - Notion doesn't have a revoke URL
        mock_config = create_mock_oauth_config(OAuthProvider.NOTION, "id", "secret", "http://localhost")
        mock_config.revoke_url = None

        with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
            # Act
            result = await oauth_service.revoke_token(
                provider=OAuthProvider.NOTION,
                token="token",
                client_id="id",
                client_secret="secret"
            )

        # Assert
        assert result is True  # Returns True even without revoke URL

    @pytest.mark.asyncio
    async def test_revoke_token_network_error(self, oauth_service):
        """Test token revocation with network error (should not raise)"""
        # Arrange
        mock_config = create_mock_oauth_config(OAuthProvider.SLACK, "id", "secret", "http://localhost")

        with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    side_effect=Exception("Network error")
                )

                # Act
                result = await oauth_service.revoke_token(
                    provider=OAuthProvider.SLACK,
                    token="token",
                    client_id="id",
                    client_secret="secret"
                )

        # Assert
        assert result is False  # Returns False on error, doesn't raise

    @pytest.mark.asyncio
    async def test_revoke_token_unexpected_status_code(self, oauth_service):
        """Test token revocation with unexpected status code"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 500

        mock_config = create_mock_oauth_config(OAuthProvider.ZOOM, "id", "secret", "http://localhost")

        with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

                # Act - Should still return True despite unexpected status
                result = await oauth_service.revoke_token(
                    provider=OAuthProvider.ZOOM,
                    token="token",
                    client_id="id",
                    client_secret="secret"
                )

        # Assert
        assert result is True


class TestOAuthServiceUserInfo:
    """Test OAuth user info retrieval"""

    @pytest.fixture
    def oauth_service(self):
        """Create OAuthService instance"""
        return OAuthService(Mock())

    @pytest.mark.asyncio
    async def test_get_user_info_slack(self, oauth_service):
        """Test getting user info from Slack"""
        # Arrange
        access_token = "xoxb-token"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": True,
            "url": "https://acme.slack.com/",
            "team": "Acme Inc",
            "user": "paddington",
            "team_id": "T123456",
            "user_id": "U123456"
        }

        mock_config = create_mock_oauth_config(OAuthProvider.SLACK, "id", "secret", "http://localhost")

        with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

                # Act
                result = await oauth_service.get_user_info(
                    provider=OAuthProvider.SLACK,
                    access_token=access_token,
                    client_id="id",
                    client_secret="secret"
                )

        # Assert
        assert result["user_id"] == "U123456"
        assert result["team_id"] == "T123456"

    @pytest.mark.asyncio
    async def test_get_user_info_google(self, oauth_service):
        """Test getting user info from Google"""
        # Arrange
        access_token = "ya29.token"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "user-123",
            "email": "user@example.com",
            "verified_email": True,
            "name": "John Doe",
            "picture": "https://example.com/photo.jpg"
        }

        mock_config = create_mock_oauth_config(OAuthProvider.GOOGLE, "id", "secret", "http://localhost")

        with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

                # Act
                result = await oauth_service.get_user_info(
                    provider=OAuthProvider.GOOGLE,
                    access_token=access_token,
                    client_id="id",
                    client_secret="secret"
                )

        # Assert
        assert result["email"] == "user@example.com"
        assert result["id"] == "user-123"

    @pytest.mark.asyncio
    async def test_get_user_info_zoom(self, oauth_service):
        """Test getting user info from Zoom"""
        # Arrange
        access_token = "zoom-token"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "user-id",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "pic_url": "https://example.com/pic.jpg"
        }

        mock_config = create_mock_oauth_config(OAuthProvider.ZOOM, "id", "secret", "http://localhost")

        with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

                # Act
                result = await oauth_service.get_user_info(
                    provider=OAuthProvider.ZOOM,
                    access_token=access_token,
                    client_id="id",
                    client_secret="secret"
                )

        # Assert
        assert result["email"] == "john@example.com"

    @pytest.mark.asyncio
    async def test_get_user_info_no_user_info_url(self, oauth_service):
        """Test getting user info when provider has no user_info_url"""
        # Arrange
        mock_config = create_mock_oauth_config(OAuthProvider.NOTION, "id", "secret", "http://localhost")
        mock_config.user_info_url = None

        with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
            # Act
            result = await oauth_service.get_user_info(
                provider=OAuthProvider.NOTION,
                access_token="token",
                client_id="id",
                client_secret="secret"
            )

        # Assert
        assert result == {}  # Returns empty dict if no user_info_url

    @pytest.mark.asyncio
    async def test_get_user_info_unauthorized(self, oauth_service):
        """Test getting user info with invalid access token"""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_config = create_mock_oauth_config(OAuthProvider.SLACK, "id", "secret", "http://localhost")

        with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

                # Act & Assert
                with pytest.raises(HTTPException) as exc_info:
                    await oauth_service.get_user_info(
                        provider=OAuthProvider.SLACK,
                        access_token="invalid-token",
                        client_id="id",
                        client_secret="secret"
                    )

                assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_get_user_info_network_error(self, oauth_service):
        """Test getting user info with network error"""
        # Arrange
        mock_config = create_mock_oauth_config(OAuthProvider.GOOGLE, "id", "secret", "http://localhost")

        with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                    side_effect=Exception("Connection failed")
                )

                # Act & Assert
                with pytest.raises(HTTPException) as exc_info:
                    await oauth_service.get_user_info(
                        provider=OAuthProvider.GOOGLE,
                        access_token="token",
                        client_id="id",
                        client_secret="secret"
                    )

                assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestOAuthServiceTokenValidity:
    """Test OAuth token validity checking and auto-refresh"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        db = Mock()
        db.execute = Mock()
        db.commit = Mock()
        return db

    @pytest.fixture
    def oauth_service(self, mock_db):
        """Create OAuthService instance"""
        return OAuthService(mock_db)

    @pytest.mark.asyncio
    async def test_check_token_validity_valid_token(self, oauth_service, mock_db):
        """Test checking validity of non-expired token"""
        # Arrange
        integration_id = uuid4()
        future_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()

        mock_row = Mock()
        mock_row._mapping = {
            "id": str(integration_id),
            "platform": "slack",
            "metadata": {
                "expires_at": future_time
            }
        }

        mock_result = Mock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Act
        result = await oauth_service.check_token_validity(integration_id)

        # Assert
        assert result is True
        mock_db.execute.assert_called()

    @pytest.mark.asyncio
    async def test_check_token_validity_no_expiration(self, oauth_service, mock_db):
        """Test checking validity when token has no expiration"""
        # Arrange
        integration_id = uuid4()

        mock_row = Mock()
        mock_row._mapping = {
            "id": str(integration_id),
            "platform": "slack",
            "metadata": {}  # No expires_at
        }

        mock_result = Mock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Act
        result = await oauth_service.check_token_validity(integration_id)

        # Assert
        assert result is True  # Assume valid if no expiration

    @pytest.mark.asyncio
    async def test_check_token_validity_integration_not_found(self, oauth_service, mock_db):
        """Test checking validity when integration doesn't exist"""
        # Arrange
        integration_id = uuid4()

        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await oauth_service.check_token_validity(integration_id)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_check_token_validity_expired_no_refresh(self, oauth_service, mock_db):
        """Test checking validity of expired token without auto-refresh"""
        # Arrange
        integration_id = uuid4()
        past_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()

        mock_row = Mock()
        mock_row._mapping = {
            "id": str(integration_id),
            "platform": "slack",
            "metadata": {
                "expires_at": past_time
            }
        }

        mock_result = Mock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Act
        result = await oauth_service.check_token_validity(integration_id, auto_refresh=False)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_check_token_validity_expired_no_refresh_token(self, oauth_service, mock_db):
        """Test checking validity when token is expired and no refresh token available"""
        # Arrange
        integration_id = uuid4()
        past_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()

        mock_row = Mock()
        mock_row._mapping = {
            "id": str(integration_id),
            "platform": "slack",
            "metadata": {
                "expires_at": past_time
                # No refresh_token
            }
        }

        mock_result = Mock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await oauth_service.check_token_validity(integration_id, auto_refresh=True)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_check_token_validity_expired_unsupported_platform(self, oauth_service, mock_db):
        """Test checking validity for unsupported OAuth platform"""
        # Arrange
        integration_id = uuid4()
        past_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()

        mock_row = Mock()
        mock_row._mapping = {
            "id": str(integration_id),
            "platform": "fireflies",  # Not OAuth-based
            "metadata": {
                "expires_at": past_time,
                "refresh_token": "token"
            }
        }

        mock_result = Mock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Act
        result = await oauth_service.check_token_validity(integration_id, auto_refresh=True)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_check_token_validity_auto_refresh_success(self, oauth_service, mock_db):
        """Test automatic token refresh on expired token"""
        # Arrange
        integration_id = uuid4()
        past_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()

        mock_row = Mock()
        mock_row._mapping = {
            "id": str(integration_id),
            "platform": "gmail",  # Use 'gmail' which maps to GOOGLE provider
            "metadata": {
                "expires_at": past_time,
                "refresh_token": "google-refresh-token",
                "client_id": "google-client-id",
                "client_secret": "google-secret"
            }
        }

        # First execute call returns the integration
        # Second execute call for the update will return None
        mock_result = Mock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Mock the refresh token response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "ya29.new-token",
            "expires_in": 3600,
            "token_type": "Bearer"
        }

        mock_config = create_mock_oauth_config(OAuthProvider.GOOGLE, "google-client-id", "google-secret", "http://localhost")

        with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
            with patch("app.services.oauth_service.get_provider_for_platform", return_value=OAuthProvider.GOOGLE):
                with patch("httpx.AsyncClient") as mock_client:
                    mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

                    # Act
                    result = await oauth_service.check_token_validity(integration_id, auto_refresh=True)

        # Assert
        assert result is True
        # Verify that database operations were called
        assert mock_db.execute.call_count >= 1
        mock_db.commit.assert_called()


class TestOAuthServiceEdgeCases:
    """Test edge cases and error conditions"""

    @pytest.fixture
    def oauth_service(self):
        """Create OAuthService instance"""
        return OAuthService(Mock())

    def test_generate_authorization_url_no_scopes(self, oauth_service):
        """Test authorization URL with provider that has no scopes"""
        # Arrange
        workspace_id = uuid4()
        mock_config = create_mock_oauth_config(OAuthProvider.NOTION, "notion-client", "notion-secret", "http://localhost")

        with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
            # Act
            auth_url = oauth_service.generate_authorization_url(
                provider=OAuthProvider.NOTION,
                client_id="notion-client",
                client_secret="notion-secret",
                redirect_uri="http://localhost",
                workspace_id=workspace_id
            )

            # Assert
            assert "state=" in auth_url
            assert "client_id=" in auth_url

    def test_state_cleanup_on_successful_validation(self, oauth_service):
        """Test that state is cleaned up after successful exchange"""
        # Arrange
        state = "test-state"
        oauth_service._oauth_states[state] = {
            "provider": "slack",
            "workspace_id": str(uuid4()),
            "created_at": datetime.utcnow().isoformat(),
            "redirect_uri": "http://localhost",
            "client_id": "id",
            "client_secret": "secret"
        }

        # Act
        oauth_service.validate_state(state)

        # Assert - state should still exist after validate (cleanup is during exchange)
        assert state in oauth_service._oauth_states

    @pytest.mark.asyncio
    async def test_multiple_providers_concurrent_exchange(self, oauth_service):
        """Test handling multiple provider token exchanges"""
        # Arrange
        states = {}
        providers_to_test = [OAuthProvider.SLACK, OAuthProvider.ZOOM, OAuthProvider.GOOGLE]

        for provider in providers_to_test:
            state = f"state-{provider.value}"
            states[provider] = state
            oauth_service._oauth_states[state] = {
                "provider": provider.value,
                "workspace_id": str(uuid4()),
                "created_at": datetime.utcnow().isoformat(),
                "redirect_uri": "http://localhost",
                "client_id": "id",
                "client_secret": "secret"
            }

        # Act & Assert
        for provider, state in states.items():
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": f"{provider.value}-token",
                "token_type": "Bearer",
                "expires_in": 3600
            }

            mock_config = create_mock_oauth_config(provider, "id", "secret", "http://localhost")

            with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
                with patch("httpx.AsyncClient") as mock_client:
                    mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

                    result = await oauth_service.exchange_code_for_tokens(
                        provider=provider,
                        code="code",
                        state=state
                    )

                    assert provider.value in result["access_token"]

    def test_authorization_url_all_params_included(self, oauth_service):
        """Test that all necessary parameters are included in authorization URL"""
        # Arrange
        workspace_id = uuid4()
        client_id = "test-client"
        mock_config = create_mock_oauth_config(OAuthProvider.SLACK, client_id, "secret", "http://localhost")

        with patch("app.services.oauth_service.get_oauth_config", return_value=mock_config):
            # Act
            auth_url = oauth_service.generate_authorization_url(
                provider=OAuthProvider.SLACK,
                client_id=client_id,
                client_secret="secret",
                redirect_uri="http://localhost:8000/callback",
                workspace_id=workspace_id
            )

            # Assert
            parsed_url = urlparse(auth_url)
            params = parse_qs(parsed_url.query)

            assert "client_id" in params
            assert "state" in params
            assert "response_type" in params
            assert params["response_type"][0] == "code"
            assert params["client_id"][0] == client_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
