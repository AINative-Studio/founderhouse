"""
Tests for OAuth Service
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import UUID, uuid4
from datetime import datetime, timedelta

from app.services.oauth_service import OAuthService
from app.core.oauth_config import OAuthProvider


@pytest.fixture
def mock_db():
    """Mock Supabase database client"""
    return Mock()


@pytest.fixture
def oauth_service(mock_db):
    """Create OAuth service instance"""
    return OAuthService(mock_db)


class TestOAuthService:
    """Test OAuth service functionality"""

    def test_generate_authorization_url(self, oauth_service):
        """Test OAuth authorization URL generation"""
        workspace_id = uuid4()

        auth_url = oauth_service.generate_authorization_url(
            provider=OAuthProvider.ZOOM,
            client_id="test_client_id",
            client_secret="test_secret",
            redirect_uri="http://localhost:8000/callback",
            workspace_id=workspace_id
        )

        assert "zoom.us/oauth/authorize" in auth_url
        assert "client_id=test_client_id" in auth_url
        assert "state=" in auth_url
        assert "scope=" in auth_url

    def test_validate_state_success(self, oauth_service):
        """Test successful state validation"""
        workspace_id = uuid4()
        state = "test_state_123"

        # Store state
        oauth_service._oauth_states[state] = {
            "provider": "zoom",
            "workspace_id": str(workspace_id),
            "created_at": datetime.utcnow().isoformat(),
            "redirect_uri": "http://localhost:8000/callback",
            "client_id": "test_client_id",
            "client_secret": "test_secret"
        }

        # Validate state
        state_data = oauth_service.validate_state(state)

        assert state_data["workspace_id"] == str(workspace_id)
        assert state_data["provider"] == "zoom"

    def test_validate_state_invalid(self, oauth_service):
        """Test invalid state validation"""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            oauth_service.validate_state("invalid_state")

        assert exc_info.value.status_code == 400

    def test_validate_state_expired(self, oauth_service):
        """Test expired state validation"""
        from fastapi import HTTPException

        workspace_id = uuid4()
        state = "test_state_123"

        # Store state with old timestamp
        old_time = datetime.utcnow() - timedelta(minutes=20)
        oauth_service._oauth_states[state] = {
            "provider": "zoom",
            "workspace_id": str(workspace_id),
            "created_at": old_time.isoformat(),
            "redirect_uri": "http://localhost:8000/callback",
            "client_id": "test_client_id",
            "client_secret": "test_secret"
        }

        with pytest.raises(HTTPException) as exc_info:
            oauth_service.validate_state(state)

        assert exc_info.value.status_code == 400
        assert "expired" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens(self, oauth_service):
        """Test exchanging authorization code for tokens"""
        workspace_id = uuid4()
        state = "test_state_123"
        code = "test_authorization_code"

        # Store state
        oauth_service._oauth_states[state] = {
            "provider": "zoom",
            "workspace_id": str(workspace_id),
            "created_at": datetime.utcnow().isoformat(),
            "redirect_uri": "http://localhost:8000/callback",
            "client_id": "test_client_id",
            "client_secret": "test_secret"
        }

        # Mock HTTP client
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "test_access_token",
                "refresh_token": "test_refresh_token",
                "token_type": "Bearer",
                "expires_in": 3600
            }
            mock_post.return_value = mock_response

            result = await oauth_service.exchange_code_for_tokens(
                provider=OAuthProvider.ZOOM,
                code=code,
                state=state
            )

            assert result["access_token"] == "test_access_token"
            assert result["refresh_token"] == "test_refresh_token"
            assert result["workspace_id"] == str(workspace_id)
            assert "expires_at" in result

    @pytest.mark.asyncio
    async def test_refresh_access_token(self, oauth_service):
        """Test refreshing access token"""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "token_type": "Bearer",
                "expires_in": 3600
            }
            mock_post.return_value = mock_response

            result = await oauth_service.refresh_access_token(
                provider=OAuthProvider.ZOOM,
                refresh_token="old_refresh_token",
                client_id="test_client_id",
                client_secret="test_secret"
            )

            assert result["access_token"] == "new_access_token"
            assert "expires_at" in result

    @pytest.mark.asyncio
    async def test_revoke_token(self, oauth_service):
        """Test revoking OAuth token"""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            result = await oauth_service.revoke_token(
                provider=OAuthProvider.ZOOM,
                token="test_token",
                client_id="test_client_id",
                client_secret="test_secret"
            )

            assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
