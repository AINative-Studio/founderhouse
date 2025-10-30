"""
OAuth Service
Generic OAuth2 client implementation with token management
"""
import logging
import secrets
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from urllib.parse import urlencode
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from supabase import Client

from app.core.oauth_config import (
    OAuthProvider,
    OAuthConfig,
    get_oauth_config,
    get_provider_for_platform
)
from app.models.integration import Platform, IntegrationStatus

logger = logging.getLogger(__name__)


class OAuthService:
    """Service for OAuth2 authentication and token management"""

    def __init__(self, db: Client):
        """
        Initialize OAuth service

        Args:
            db: Supabase database client
        """
        self.db = db
        # Store OAuth states in memory (in production, use Redis or database)
        self._oauth_states: Dict[str, Dict[str, Any]] = {}

    def generate_authorization_url(
        self,
        provider: OAuthProvider,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        workspace_id: UUID,
        state_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate OAuth authorization URL

        Args:
            provider: OAuth provider
            client_id: OAuth client ID
            client_secret: OAuth client secret
            redirect_uri: Redirect URI for OAuth callback
            workspace_id: Workspace ID for this OAuth flow
            state_data: Additional data to store in state

        Returns:
            Authorization URL to redirect user to

        Raises:
            ValueError: If configuration is invalid
        """
        try:
            # Get OAuth configuration
            config = get_oauth_config(provider, client_id, client_secret, redirect_uri)

            # Generate state parameter for CSRF protection
            state = secrets.token_urlsafe(32)

            # Store state with workspace_id and additional data
            self._oauth_states[state] = {
                "provider": provider.value,
                "workspace_id": str(workspace_id),
                "created_at": datetime.utcnow().isoformat(),
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_secret": client_secret,
                **(state_data or {})
            }

            # Build authorization URL
            params = {
                "client_id": config.client_id,
                "redirect_uri": config.redirect_uri,
                "response_type": "code",
                "state": state,
                "scope": " ".join(config.scopes) if config.scopes else ""
            }

            # Add extra parameters for specific providers
            params.update(config.extra_params)

            # Remove empty values
            params = {k: v for k, v in params.items() if v}

            authorization_url = f"{config.authorization_url}?{urlencode(params)}"

            logger.info(f"Generated authorization URL for {provider} provider")
            return authorization_url

        except Exception as e:
            logger.error(f"Error generating authorization URL: {str(e)}")
            raise ValueError(f"Failed to generate authorization URL: {str(e)}")

    def validate_state(self, state: str) -> Dict[str, Any]:
        """
        Validate OAuth state parameter

        Args:
            state: State parameter from OAuth callback

        Returns:
            State data dictionary

        Raises:
            HTTPException: If state is invalid or expired
        """
        if state not in self._oauth_states:
            logger.warning(f"Invalid OAuth state parameter: {state}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OAuth state parameter"
            )

        state_data = self._oauth_states[state]

        # Check if state is expired (15 minutes)
        created_at = datetime.fromisoformat(state_data["created_at"])
        if datetime.utcnow() - created_at > timedelta(minutes=15):
            del self._oauth_states[state]
            logger.warning(f"Expired OAuth state parameter: {state}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth state parameter has expired"
            )

        return state_data

    async def exchange_code_for_tokens(
        self,
        provider: OAuthProvider,
        code: str,
        state: str
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens

        Args:
            provider: OAuth provider
            code: Authorization code from OAuth callback
            state: State parameter for validation

        Returns:
            Dictionary containing tokens and metadata

        Raises:
            HTTPException: If token exchange fails
        """
        try:
            # Validate state
            state_data = self.validate_state(state)

            # Get OAuth configuration
            config = get_oauth_config(
                provider,
                state_data["client_id"],
                state_data["client_secret"],
                state_data["redirect_uri"]
            )

            # Prepare token request
            token_data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": config.redirect_uri,
                "client_id": config.client_id,
                "client_secret": config.client_secret
            }

            # Make token request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    config.token_url,
                    data=token_data,
                    headers={"Accept": "application/json"},
                    timeout=30.0
                )

                if response.status_code != 200:
                    logger.error(
                        f"Token exchange failed for {provider}: "
                        f"{response.status_code} - {response.text}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to exchange authorization code: {response.text}"
                    )

                tokens = response.json()

            # Clean up state
            del self._oauth_states[state]

            # Calculate token expiration
            expires_in = tokens.get("expires_in", 3600)
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            result = {
                "access_token": tokens.get("access_token"),
                "refresh_token": tokens.get("refresh_token"),
                "token_type": tokens.get("token_type", "Bearer"),
                "expires_at": expires_at.isoformat(),
                "expires_in": expires_in,
                "scope": tokens.get("scope", " ".join(config.scopes)),
                "workspace_id": state_data["workspace_id"],
                "provider": provider.value
            }

            # Add provider-specific data
            if provider == OAuthProvider.SLACK:
                result["team_id"] = tokens.get("team", {}).get("id")
                result["team_name"] = tokens.get("team", {}).get("name")
                result["user_id"] = tokens.get("authed_user", {}).get("id")

            logger.info(f"Successfully exchanged code for tokens: {provider}")
            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error exchanging code for tokens: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to exchange authorization code: {str(e)}"
            )

    async def refresh_access_token(
        self,
        provider: OAuthProvider,
        refresh_token: str,
        client_id: str,
        client_secret: str
    ) -> Dict[str, Any]:
        """
        Refresh access token using refresh token

        Args:
            provider: OAuth provider
            refresh_token: Refresh token
            client_id: OAuth client ID
            client_secret: OAuth client secret

        Returns:
            New tokens dictionary

        Raises:
            HTTPException: If token refresh fails
        """
        try:
            # Get OAuth configuration (use a dummy redirect_uri as it's not needed for refresh)
            config = get_oauth_config(
                provider,
                client_id,
                client_secret,
                "http://localhost:8000/callback"
            )

            # Prepare refresh request
            refresh_data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": config.client_id,
                "client_secret": config.client_secret
            }

            # Make refresh request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    config.token_url,
                    data=refresh_data,
                    headers={"Accept": "application/json"},
                    timeout=30.0
                )

                if response.status_code != 200:
                    logger.error(
                        f"Token refresh failed for {provider}: "
                        f"{response.status_code} - {response.text}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=f"Failed to refresh access token: {response.text}"
                    )

                tokens = response.json()

            # Calculate token expiration
            expires_in = tokens.get("expires_in", 3600)
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            result = {
                "access_token": tokens.get("access_token"),
                "refresh_token": tokens.get("refresh_token", refresh_token),  # Some providers don't return new refresh token
                "token_type": tokens.get("token_type", "Bearer"),
                "expires_at": expires_at.isoformat(),
                "expires_in": expires_in,
                "scope": tokens.get("scope")
            }

            logger.info(f"Successfully refreshed access token: {provider}")
            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error refreshing access token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to refresh access token: {str(e)}"
            )

    async def revoke_token(
        self,
        provider: OAuthProvider,
        token: str,
        client_id: str,
        client_secret: str,
        token_type: str = "access_token"
    ) -> bool:
        """
        Revoke OAuth token

        Args:
            provider: OAuth provider
            token: Token to revoke
            client_id: OAuth client ID
            client_secret: OAuth client secret
            token_type: Type of token (access_token or refresh_token)

        Returns:
            True if revocation successful

        Raises:
            HTTPException: If token revocation fails
        """
        try:
            # Get OAuth configuration
            config = get_oauth_config(
                provider,
                client_id,
                client_secret,
                "http://localhost:8000/callback"
            )

            if not config.revoke_url:
                logger.warning(f"No revoke URL configured for {provider}")
                return True  # Some providers don't support revocation

            # Prepare revocation request
            revoke_data = {
                "token": token,
                "token_type_hint": token_type,
                "client_id": config.client_id,
                "client_secret": config.client_secret
            }

            # Make revocation request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    config.revoke_url,
                    data=revoke_data,
                    headers={"Accept": "application/json"},
                    timeout=30.0
                )

                # Some providers return 200, others 204
                if response.status_code not in [200, 204]:
                    logger.warning(
                        f"Token revocation returned unexpected status for {provider}: "
                        f"{response.status_code}"
                    )

            logger.info(f"Successfully revoked token: {provider}")
            return True

        except Exception as e:
            logger.error(f"Error revoking token: {str(e)}")
            # Don't raise exception for revocation failures
            return False

    async def get_user_info(
        self,
        provider: OAuthProvider,
        access_token: str,
        client_id: str,
        client_secret: str
    ) -> Dict[str, Any]:
        """
        Get user information from OAuth provider

        Args:
            provider: OAuth provider
            access_token: Access token
            client_id: OAuth client ID
            client_secret: OAuth client secret

        Returns:
            User information dictionary

        Raises:
            HTTPException: If user info request fails
        """
        try:
            # Get OAuth configuration
            config = get_oauth_config(
                provider,
                client_id,
                client_secret,
                "http://localhost:8000/callback"
            )

            if not config.user_info_url:
                logger.warning(f"No user info URL configured for {provider}")
                return {}

            # Make user info request
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    config.user_info_url,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json"
                    },
                    timeout=30.0
                )

                if response.status_code != 200:
                    logger.error(
                        f"User info request failed for {provider}: "
                        f"{response.status_code} - {response.text}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to get user info: {response.text}"
                    )

                user_info = response.json()

            logger.info(f"Successfully retrieved user info: {provider}")
            return user_info

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting user info: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get user info: {str(e)}"
            )

    async def check_token_validity(
        self,
        integration_id: UUID,
        auto_refresh: bool = True
    ) -> bool:
        """
        Check if access token is valid and refresh if needed

        Args:
            integration_id: Integration ID
            auto_refresh: Automatically refresh expired tokens

        Returns:
            True if token is valid (or was successfully refreshed)

        Raises:
            HTTPException: If token validation/refresh fails
        """
        try:
            # Get integration from database
            response = self.db.table("core.integrations").select("*").eq(
                "id", str(integration_id)
            ).execute()

            if not response.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Integration {integration_id} not found"
                )

            integration = response.data[0]

            # Check if integration has OAuth credentials
            metadata = integration.get("metadata", {})
            expires_at_str = metadata.get("expires_at")

            if not expires_at_str:
                # No expiration info, assume valid
                return True

            # Check if token is expired
            expires_at = datetime.fromisoformat(expires_at_str)
            if datetime.utcnow() < expires_at:
                # Token is still valid
                return True

            # Token is expired
            if not auto_refresh:
                logger.warning(f"Token expired for integration {integration_id}")
                return False

            # Try to refresh token
            refresh_token = metadata.get("refresh_token")
            if not refresh_token:
                logger.error(f"No refresh token available for integration {integration_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token expired and no refresh token available"
                )

            # Get provider
            platform = integration["platform"]
            provider = get_provider_for_platform(platform)
            if not provider:
                logger.error(f"Platform {platform} does not support OAuth")
                return False

            # Get OAuth credentials from environment or config
            # In production, these should be stored securely
            client_id = metadata.get("client_id", "")
            client_secret = metadata.get("client_secret", "")

            # Refresh the token
            new_tokens = await self.refresh_access_token(
                provider,
                refresh_token,
                client_id,
                client_secret
            )

            # Update integration with new tokens
            updated_metadata = {**metadata, **new_tokens}
            self.db.table("core.integrations").update({
                "metadata": updated_metadata,
                "status": IntegrationStatus.CONNECTED.value,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", str(integration_id)).execute()

            logger.info(f"Successfully refreshed token for integration {integration_id}")
            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error checking token validity: {str(e)}")
            return False
