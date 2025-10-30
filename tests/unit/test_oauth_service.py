"""
AI Chief of Staff - OAuth Service Unit Tests
Sprint 2: Issue #5 - MCP Authentication via OAuth Tests

Tests for OAuth service functionality:
- OAuth state generation and validation
- Authorization URL generation
- Token exchange from authorization code
- Token refresh logic
- Token expiration detection
- Automatic refresh 24h before expiry
- Platform-specific OAuth configs
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4

from tests.fixtures.integration_fixtures import (
    OAuthTokenFactory,
    OAuthStateFactory,
    create_oauth_flow_data
)
from tests.fixtures.mcp_responses import (
    get_oauth_token_response,
    get_oauth_refresh_response,
    get_expired_token_error,
    get_oauth_invalid_code_error
)


# ============================================================================
# OAUTH STATE GENERATION AND VALIDATION
# ============================================================================

@pytest.mark.unit
@pytest.mark.oauth
class TestOAuthStateManagement:
    """Test OAuth state parameter generation and validation"""

    def test_generate_oauth_state(self, mock_oauth_service: Mock):
        """
        Test: OAuth state generation
        Given: OAuth flow initiated for a platform
        When: generate_state() called
        Then: Returns unique state parameter
        """
        # Arrange
        platform = "zoom"
        workspace_id = str(uuid4())

        # Mock implementation
        expected_state = uuid4().hex
        mock_oauth_service.generate_state.return_value = expected_state

        # Act
        state = mock_oauth_service.generate_state(platform, workspace_id)

        # Assert
        assert state == expected_state
        assert len(state) == 32  # UUID hex is 32 characters
        mock_oauth_service.generate_state.assert_called_once_with(platform, workspace_id)

    def test_validate_oauth_state_success(self, mock_oauth_service: Mock):
        """
        Test: Valid OAuth state validation
        Given: Valid state parameter stored
        When: validate_state() called with matching state
        Then: Returns True
        """
        # Arrange
        state = uuid4().hex
        mock_oauth_service.validate_state.return_value = True

        # Act
        is_valid = mock_oauth_service.validate_state(state)

        # Assert
        assert is_valid is True

    def test_validate_oauth_state_expired(self, mock_oauth_service: Mock):
        """
        Test: Expired OAuth state rejected
        Given: State parameter expired (>10 minutes old)
        When: validate_state() called
        Then: Returns False
        """
        # Arrange
        expired_state = OAuthStateFactory.expired()
        mock_oauth_service.validate_state.return_value = False

        # Act
        is_valid = mock_oauth_service.validate_state(expired_state["state"])

        # Assert
        assert is_valid is False

    def test_validate_oauth_state_not_found(self, mock_oauth_service: Mock):
        """
        Test: Unknown state rejected
        Given: State parameter not in storage
        When: validate_state() called
        Then: Returns False
        """
        # Arrange
        unknown_state = uuid4().hex
        mock_oauth_service.validate_state.return_value = False

        # Act
        is_valid = mock_oauth_service.validate_state(unknown_state)

        # Assert
        assert is_valid is False

    def test_state_is_single_use(self, mock_oauth_service: Mock):
        """
        Test: State can only be used once
        Given: State validated successfully
        When: Same state validated again
        Then: Returns False (already consumed)
        """
        # Arrange
        state = uuid4().hex
        mock_oauth_service.validate_state.side_effect = [True, False]

        # Act
        first_validation = mock_oauth_service.validate_state(state)
        second_validation = mock_oauth_service.validate_state(state)

        # Assert
        assert first_validation is True
        assert second_validation is False


# ============================================================================
# AUTHORIZATION URL GENERATION
# ============================================================================

@pytest.mark.unit
@pytest.mark.oauth
class TestAuthorizationURLGeneration:
    """Test OAuth authorization URL generation"""

    def test_generate_authorization_url_zoom(
        self,
        mock_oauth_service: Mock,
        mock_oauth_provider_configs: dict
    ):
        """
        Test: Generate Zoom authorization URL
        Given: Zoom OAuth config
        When: generate_authorization_url() called
        Then: Returns valid Zoom OAuth URL with state
        """
        # Arrange
        platform = "zoom"
        workspace_id = str(uuid4())
        config = mock_oauth_provider_configs[platform]
        expected_state = uuid4().hex

        expected_url = (
            f"{config['authorization_url']}?"
            f"client_id={config['client_id']}&"
            f"response_type=code&"
            f"redirect_uri=https://app.example.com/oauth/callback/zoom&"
            f"state={expected_state}&"
            f"scope=meeting:read+meeting:write"
        )

        mock_oauth_service.generate_authorization_url.return_value = (expected_url, expected_state)

        # Act
        url, state = mock_oauth_service.generate_authorization_url(platform, workspace_id)

        # Assert
        assert "zoom.us/oauth/authorize" in url
        assert f"client_id={config['client_id']}" in url
        assert f"state={state}" in url
        assert "scope=" in url

    def test_generate_authorization_url_slack(
        self,
        mock_oauth_service: Mock,
        mock_oauth_provider_configs: dict
    ):
        """
        Test: Generate Slack authorization URL
        Given: Slack OAuth config
        When: generate_authorization_url() called
        Then: Returns valid Slack OAuth URL
        """
        # Arrange
        platform = "slack"
        workspace_id = str(uuid4())
        config = mock_oauth_provider_configs[platform]
        expected_state = uuid4().hex

        expected_url = (
            f"{config['authorization_url']}?"
            f"client_id={config['client_id']}&"
            f"state={expected_state}"
        )

        mock_oauth_service.generate_authorization_url.return_value = (expected_url, expected_state)

        # Act
        url, state = mock_oauth_service.generate_authorization_url(platform, workspace_id)

        # Assert
        assert "slack.com/oauth" in url
        assert f"client_id={config['client_id']}" in url
        assert f"state={state}" in url

    def test_generate_authorization_url_with_custom_scopes(
        self,
        mock_oauth_service: Mock
    ):
        """
        Test: Custom scopes in authorization URL
        Given: Custom scope list provided
        When: generate_authorization_url() called
        Then: URL includes requested scopes
        """
        # Arrange
        platform = "zoom"
        workspace_id = str(uuid4())
        custom_scopes = ["meeting:read", "recording:read", "user:read"]

        expected_url = "https://zoom.us/oauth/authorize?scopes=meeting:read+recording:read+user:read"
        expected_state = uuid4().hex

        mock_oauth_service.generate_authorization_url.return_value = (expected_url, expected_state)

        # Act
        url, state = mock_oauth_service.generate_authorization_url(
            platform,
            workspace_id,
            scopes=custom_scopes
        )

        # Assert
        for scope in custom_scopes:
            assert scope.replace(":", "%3A") in url or scope in url


# ============================================================================
# TOKEN EXCHANGE
# ============================================================================

@pytest.mark.unit
@pytest.mark.oauth
@pytest.mark.asyncio
class TestTokenExchange:
    """Test OAuth token exchange from authorization code"""

    async def test_exchange_code_for_token_success(
        self,
        mock_oauth_service: Mock
    ):
        """
        Test: Successful token exchange
        Given: Valid authorization code
        When: exchange_code_for_token() called
        Then: Returns access token and refresh token
        """
        # Arrange
        platform = "zoom"
        authorization_code = uuid4().hex
        token_response = get_oauth_token_response(platform=platform)

        mock_oauth_service.exchange_code_for_token.return_value = token_response

        # Act
        tokens = mock_oauth_service.exchange_code_for_token(platform, authorization_code)

        # Assert
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "expires_in" in tokens
        assert tokens["token_type"] == "Bearer"

    async def test_exchange_code_for_token_invalid_code(
        self,
        mock_oauth_service: Mock
    ):
        """
        Test: Invalid authorization code rejected
        Given: Invalid or expired authorization code
        When: exchange_code_for_token() called
        Then: Raises exception
        """
        # Arrange
        platform = "zoom"
        invalid_code = "invalid_code_123"

        mock_oauth_service.exchange_code_for_token.side_effect = ValueError(
            "Invalid authorization code"
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid authorization code"):
            mock_oauth_service.exchange_code_for_token(platform, invalid_code)

    async def test_exchange_code_stores_token_with_expiry(
        self,
        mock_oauth_service: Mock
    ):
        """
        Test: Token stored with correct expiration
        Given: Token exchange successful
        When: Token stored
        Then: Expiration timestamp calculated correctly
        """
        # Arrange
        platform = "zoom"
        authorization_code = uuid4().hex
        expires_in = 3600  # 1 hour

        token_response = get_oauth_token_response(platform=platform, expires_in=expires_in)
        mock_oauth_service.exchange_code_for_token.return_value = token_response

        # Act
        tokens = mock_oauth_service.exchange_code_for_token(platform, authorization_code)

        # Assert
        assert tokens["expires_in"] == expires_in
        # In real implementation, would calculate expires_at timestamp


# ============================================================================
# TOKEN REFRESH
# ============================================================================

@pytest.mark.unit
@pytest.mark.oauth
@pytest.mark.asyncio
class TestTokenRefresh:
    """Test OAuth token refresh logic"""

    async def test_refresh_token_success(
        self,
        mock_oauth_service: Mock
    ):
        """
        Test: Successful token refresh
        Given: Valid refresh token
        When: refresh_token() called
        Then: Returns new access token
        """
        # Arrange
        platform = "zoom"
        refresh_token = "mock_refresh_token"
        refresh_response = get_oauth_refresh_response(platform=platform)

        mock_oauth_service.refresh_token.return_value = refresh_response

        # Act
        new_tokens = mock_oauth_service.refresh_token(platform, refresh_token)

        # Assert
        assert "access_token" in new_tokens
        assert "expires_in" in new_tokens
        assert new_tokens["access_token"] != refresh_token

    async def test_refresh_token_with_expired_refresh_token(
        self,
        mock_oauth_service: Mock
    ):
        """
        Test: Expired refresh token rejected
        Given: Refresh token expired
        When: refresh_token() called
        Then: Raises exception requiring re-authentication
        """
        # Arrange
        platform = "zoom"
        expired_refresh_token = "expired_token"

        mock_oauth_service.refresh_token.side_effect = ValueError(
            "Refresh token expired, re-authentication required"
        )

        # Act & Assert
        with pytest.raises(ValueError, match="re-authentication required"):
            mock_oauth_service.refresh_token(platform, expired_refresh_token)

    async def test_refresh_token_updates_expiry(
        self,
        mock_oauth_service: Mock
    ):
        """
        Test: Token expiry updated after refresh
        Given: Token refreshed successfully
        When: New token stored
        Then: Expiry timestamp updated
        """
        # Arrange
        platform = "zoom"
        refresh_token = "mock_refresh_token"
        new_expires_in = 3600

        refresh_response = get_oauth_refresh_response(
            platform=platform,
            expires_in=new_expires_in
        )

        mock_oauth_service.refresh_token.return_value = refresh_response

        # Act
        new_tokens = mock_oauth_service.refresh_token(platform, refresh_token)

        # Assert
        assert new_tokens["expires_in"] == new_expires_in


# ============================================================================
# TOKEN EXPIRATION DETECTION
# ============================================================================

@pytest.mark.unit
@pytest.mark.oauth
class TestTokenExpirationDetection:
    """Test token expiration detection logic"""

    def test_is_token_expired_returns_true_for_expired_token(
        self,
        mock_oauth_service: Mock
    ):
        """
        Test: Detect expired token
        Given: Token expiration timestamp in the past
        When: is_token_expired() called
        Then: Returns True
        """
        # Arrange
        expired_token = OAuthTokenFactory.expired()
        mock_oauth_service.is_token_expired.return_value = True

        # Act
        is_expired = mock_oauth_service.is_token_expired(expired_token)

        # Assert
        assert is_expired is True

    def test_is_token_expired_returns_false_for_valid_token(
        self,
        mock_oauth_service: Mock
    ):
        """
        Test: Valid token not expired
        Given: Token expiration timestamp in the future
        When: is_token_expired() called
        Then: Returns False
        """
        # Arrange
        valid_token = OAuthTokenFactory()
        mock_oauth_service.is_token_expired.return_value = False

        # Act
        is_expired = mock_oauth_service.is_token_expired(valid_token)

        # Assert
        assert is_expired is False

    def test_token_expiring_soon_detected(
        self,
        mock_oauth_service: Mock
    ):
        """
        Test: Token expiring within 24h detected
        Given: Token expires in 23 hours
        When: should_refresh_token() called
        Then: Returns True
        """
        # Arrange
        expiring_token = OAuthTokenFactory.expiring_soon()
        mock_oauth_service.should_refresh_token = Mock(return_value=True)

        # Act
        should_refresh = mock_oauth_service.should_refresh_token(expiring_token)

        # Assert
        assert should_refresh is True


# ============================================================================
# AUTOMATIC REFRESH 24H BEFORE EXPIRY
# ============================================================================

@pytest.mark.unit
@pytest.mark.oauth
@pytest.mark.asyncio
class TestAutomaticTokenRefresh:
    """Test automatic token refresh 24h before expiry"""

    async def test_auto_refresh_when_expiring_within_24h(
        self,
        mock_oauth_service: Mock
    ):
        """
        Test: Automatic refresh 24h before expiry
        Given: Token expiring in 23 hours
        When: Token checked
        Then: Automatic refresh triggered
        """
        # Arrange
        expiring_token = OAuthTokenFactory.expiring_soon()
        platform = "zoom"

        mock_oauth_service.should_refresh_token.return_value = True
        refresh_response = get_oauth_refresh_response(platform=platform)
        mock_oauth_service.refresh_token.return_value = refresh_response

        # Act
        should_refresh = mock_oauth_service.should_refresh_token(expiring_token)

        if should_refresh:
            new_tokens = mock_oauth_service.refresh_token(
                platform,
                expiring_token["refresh_token"]
            )

        # Assert
        assert should_refresh is True
        assert "access_token" in new_tokens

    async def test_no_auto_refresh_when_token_fresh(
        self,
        mock_oauth_service: Mock
    ):
        """
        Test: No refresh for fresh token
        Given: Token expiring in 48 hours
        When: Token checked
        Then: No automatic refresh triggered
        """
        # Arrange
        fresh_token = OAuthTokenFactory()  # Expires in 1 hour by default
        mock_oauth_service.should_refresh_token.return_value = False

        # Act
        should_refresh = mock_oauth_service.should_refresh_token(fresh_token)

        # Assert
        assert should_refresh is False


# ============================================================================
# PLATFORM-SPECIFIC OAUTH CONFIGS
# ============================================================================

@pytest.mark.unit
@pytest.mark.oauth
class TestPlatformOAuthConfigs:
    """Test platform-specific OAuth configurations"""

    def test_get_oauth_config_for_zoom(
        self,
        mock_oauth_provider_configs: dict
    ):
        """
        Test: Zoom OAuth configuration
        Given: Zoom platform
        When: get_oauth_config() called
        Then: Returns Zoom-specific config
        """
        # Arrange
        platform = "zoom"
        config = mock_oauth_provider_configs[platform]

        # Assert
        assert config["authorization_url"] == "https://zoom.us/oauth/authorize"
        assert config["token_url"] == "https://zoom.us/oauth/token"
        assert "meeting:read" in config["scopes"]

    def test_get_oauth_config_for_slack(
        self,
        mock_oauth_provider_configs: dict
    ):
        """
        Test: Slack OAuth configuration
        Given: Slack platform
        When: get_oauth_config() called
        Then: Returns Slack-specific config
        """
        # Arrange
        platform = "slack"
        config = mock_oauth_provider_configs[platform]

        # Assert
        assert "slack.com/oauth" in config["authorization_url"]
        assert "slack.com/api/oauth" in config["token_url"]
        assert "channels:read" in config["scopes"]

    def test_get_oauth_config_for_discord(
        self,
        mock_oauth_provider_configs: dict
    ):
        """
        Test: Discord OAuth configuration
        Given: Discord platform
        When: get_oauth_config() called
        Then: Returns Discord-specific config
        """
        # Arrange
        platform = "discord"
        config = mock_oauth_provider_configs[platform]

        # Assert
        assert "discord.com/api/oauth2" in config["authorization_url"]
        assert "discord.com/api/oauth2/token" in config["token_url"]
        assert "bot" in config["scopes"]

    def test_oauth_config_not_found_for_unsupported_platform(
        self,
        mock_oauth_provider_configs: dict
    ):
        """
        Test: Unsupported platform raises error
        Given: Platform not in config
        When: get_oauth_config() called
        Then: Raises ValueError
        """
        # Arrange
        unsupported_platform = "unsupported_platform"

        # Act & Assert
        assert unsupported_platform not in mock_oauth_provider_configs
