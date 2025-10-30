"""
OAuth Endpoints
OAuth2 authorization flow for MCP integrations
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from supabase import Client

from app.database import get_db
from app.core.security import get_current_user, AuthUser
from app.core.dependencies import get_workspace_id
from app.core.oauth_config import OAuthProvider, get_provider_for_platform
from app.services.oauth_service import OAuthService
from app.services.integration_service import IntegrationService
from app.models.integration import (
    IntegrationCreate,
    IntegrationResponse,
    Platform,
    ConnectionType,
    IntegrationStatus
)
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


def get_oauth_service(db: Client = Depends(get_db)) -> OAuthService:
    """Dependency to get OAuth service instance"""
    return OAuthService(db)


def get_integration_service(db: Client = Depends(get_db)) -> IntegrationService:
    """Dependency to get integration service instance"""
    return IntegrationService(db)


class OAuthInitiateRequest(BaseModel):
    """Request to initiate OAuth flow"""
    platform: Platform
    redirect_uri: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "platform": "zoom",
                "redirect_uri": "https://yourapp.com/oauth/callback"
            }
        }


class OAuthInitiateResponse(BaseModel):
    """Response with OAuth authorization URL"""
    authorization_url: str
    state: str
    platform: str

    class Config:
        json_schema_extra = {
            "example": {
                "authorization_url": "https://zoom.us/oauth/authorize?client_id=...&state=...",
                "state": "random_state_string",
                "platform": "zoom"
            }
        }


@router.post(
    "/{platform}/authorize",
    response_model=OAuthInitiateResponse,
    summary="Initiate OAuth Authorization"
)
async def initiate_oauth(
    platform: Platform,
    workspace_id: UUID = Depends(get_workspace_id),
    current_user: AuthUser = Depends(get_current_user),
    oauth_service: OAuthService = Depends(get_oauth_service)
):
    """
    Initiate OAuth 2.0 authorization flow for a platform

    **Process:**
    1. Generate authorization URL with state parameter
    2. Return URL to frontend
    3. Frontend redirects user to authorization URL
    4. User grants permissions on platform
    5. Platform redirects back to callback URL

    **Path Parameters:**
    - platform: Platform to authorize (zoom, slack, discord, etc.)

    **Returns:**
    - Authorization URL to redirect user to
    - State parameter for CSRF protection

    **Example:**
    ```
    POST /api/v1/oauth/zoom/authorize

    Response:
    {
      "authorization_url": "https://zoom.us/oauth/authorize?...",
      "state": "abc123...",
      "platform": "zoom"
    }
    ```

    **Next Step:**
    - Redirect user to authorization_url
    - Handle callback at /oauth/{platform}/callback
    """
    try:
        # Get provider for platform
        provider = get_provider_for_platform(platform.value)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Platform {platform} does not support OAuth"
            )

        # Get OAuth credentials from settings
        client_id = None
        client_secret = None

        if platform == Platform.ZOOM:
            client_id = settings.zoom_client_id
            client_secret = settings.zoom_client_secret
        elif platform == Platform.SLACK:
            client_id = settings.slack_client_id
            client_secret = settings.slack_client_secret
        elif platform == Platform.DISCORD:
            # Discord uses bot token, but we still need OAuth for user connections
            client_id = settings.discord_client_id
            client_secret = settings.discord_client_secret
        # Add more platforms as needed

        if not client_id or not client_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"OAuth not configured for {platform}. Contact administrator."
            )

        # Generate redirect URI
        redirect_uri = f"{settings.api_v1_prefix}/oauth/{platform.value}/callback"
        if not redirect_uri.startswith("http"):
            # In development, use localhost
            base_url = "http://localhost:8000" if settings.debug else "https://api.yourdomain.com"
            redirect_uri = f"{base_url}{redirect_uri}"

        # Generate authorization URL
        auth_url = oauth_service.generate_authorization_url(
            provider=provider,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            workspace_id=workspace_id,
            state_data={
                "user_id": str(current_user.user_id),
                "platform": platform.value
            }
        )

        # Extract state from URL
        import urllib.parse
        parsed = urllib.parse.urlparse(auth_url)
        params = urllib.parse.parse_qs(parsed.query)
        state = params.get("state", [""])[0]

        logger.info(f"Initiated OAuth flow for {platform} - workspace {workspace_id}")

        return OAuthInitiateResponse(
            authorization_url=auth_url,
            state=state,
            platform=platform.value
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating OAuth: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate OAuth: {str(e)}"
        )


@router.get(
    "/{platform}/callback",
    summary="OAuth Callback Handler"
)
async def oauth_callback(
    platform: Platform,
    code: str = Query(..., description="Authorization code from OAuth provider"),
    state: str = Query(..., description="State parameter for CSRF protection"),
    error: Optional[str] = Query(None, description="Error from OAuth provider"),
    error_description: Optional[str] = Query(None, description="Error description"),
    oauth_service: OAuthService = Depends(get_oauth_service),
    integration_service: IntegrationService = Depends(get_integration_service),
    db: Client = Depends(get_db)
):
    """
    Handle OAuth callback from platform

    This endpoint is called by the OAuth provider after user authorization.
    It exchanges the authorization code for access tokens and creates the integration.

    **Path Parameters:**
    - platform: Platform that triggered the callback

    **Query Parameters:**
    - code: Authorization code (from OAuth provider)
    - state: State parameter for validation
    - error: Optional error from provider
    - error_description: Optional error description

    **Returns:**
    - Redirect to frontend with success or error

    **Flow:**
    1. Validate state parameter
    2. Exchange code for tokens
    3. Store tokens securely
    4. Create integration record
    5. Redirect to frontend

    **Note:**
    - This is typically called by the OAuth provider, not directly by frontend
    - Redirects user back to frontend after processing
    """
    try:
        # Check for OAuth errors
        if error:
            logger.error(f"OAuth error from {platform}: {error} - {error_description}")
            # Redirect to frontend with error
            return RedirectResponse(
                url=f"http://localhost:3000/integrations?error={error}&platform={platform.value}",
                status_code=status.HTTP_302_FOUND
            )

        # Get provider
        provider = get_provider_for_platform(platform.value)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Platform {platform} does not support OAuth"
            )

        # Exchange code for tokens
        tokens = await oauth_service.exchange_code_for_tokens(
            provider=provider,
            code=code,
            state=state
        )

        # Get workspace_id from state
        workspace_id = UUID(tokens["workspace_id"])

        # Get user info from platform
        user_info = await oauth_service.get_user_info(
            provider=provider,
            access_token=tokens["access_token"],
            client_id="",  # Not needed for user info request
            client_secret=""
        )

        # Prepare credentials
        credentials = {
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token"),
            "token_type": tokens.get("token_type", "Bearer"),
            "expires_at": tokens.get("expires_at"),
            "scope": tokens.get("scope")
        }

        # Add platform-specific data
        if platform == Platform.SLACK:
            credentials["team_id"] = tokens.get("team_id")
            credentials["team_name"] = tokens.get("team_name")
            credentials["user_id"] = tokens.get("user_id")

        # Prepare metadata
        metadata = {
            **tokens,
            "user_info": user_info,
            "oauth_provider": provider.value,
            "connected_via": "oauth"
        }

        # Create integration
        integration_create = IntegrationCreate(
            workspace_id=workspace_id,
            founder_id=None,
            platform=platform,
            connection_type=ConnectionType.MCP,
            credentials=credentials,
            metadata=metadata
        )

        integration = await integration_service.create_integration(integration_create)

        logger.info(f"OAuth integration created: {integration.id} for {platform}")

        # Redirect to frontend with success
        return RedirectResponse(
            url=f"http://localhost:3000/integrations?success=true&platform={platform.value}&integration_id={integration.id}",
            status_code=status.HTTP_302_FOUND
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}")
        # Redirect to frontend with error
        return RedirectResponse(
            url=f"http://localhost:3000/integrations?error=callback_failed&platform={platform.value}",
            status_code=status.HTTP_302_FOUND
        )


@router.post(
    "/{platform}/refresh",
    response_model=IntegrationResponse,
    summary="Refresh OAuth Token"
)
async def refresh_oauth_token(
    platform: Platform,
    integration_id: UUID,
    current_user: AuthUser = Depends(get_current_user),
    oauth_service: OAuthService = Depends(get_oauth_service),
    integration_service: IntegrationService = Depends(get_integration_service)
):
    """
    Manually refresh OAuth access token

    **Path Parameters:**
    - platform: Platform to refresh token for

    **Query Parameters:**
    - integration_id: Integration ID

    **Returns:**
    - Updated integration with new tokens

    **Use Cases:**
    - Manual token refresh before expiration
    - Recovering from expired tokens
    - Testing token refresh flow

    **Note:**
    - Tokens are automatically refreshed by health check system
    - Manual refresh is typically not needed
    """
    try:
        # Check token validity and refresh if needed
        is_valid = await oauth_service.check_token_validity(
            integration_id=integration_id,
            auto_refresh=True
        )

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token refresh failed"
            )

        # Return updated integration
        integration = await integration_service.get_integration(integration_id)

        logger.info(f"Token refreshed for integration {integration_id}")

        return integration

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh token: {str(e)}"
        )


@router.delete(
    "/{platform}/revoke",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke OAuth Token"
)
async def revoke_oauth_token(
    platform: Platform,
    integration_id: UUID,
    current_user: AuthUser = Depends(get_current_user),
    oauth_service: OAuthService = Depends(get_oauth_service),
    integration_service: IntegrationService = Depends(get_integration_service),
    db: Client = Depends(get_db)
):
    """
    Revoke OAuth tokens for an integration

    **Path Parameters:**
    - platform: Platform to revoke tokens for

    **Query Parameters:**
    - integration_id: Integration ID

    **Actions:**
    1. Revoke access token on platform
    2. Revoke refresh token on platform
    3. Update integration status to 'revoked'
    4. Log revocation event

    **Returns:**
    - 204 No Content on success

    **Note:**
    - This revokes tokens on the platform side
    - Integration record is kept for audit purposes
    - Use DELETE /integrations/{id} to completely remove integration
    """
    try:
        # Get integration
        integration = await integration_service.get_integration(integration_id)

        # Get provider
        provider = get_provider_for_platform(platform.value)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Platform {platform} does not support OAuth"
            )

        # Get tokens from integration
        # Note: In production, decrypt credentials from database
        metadata = integration.metadata
        access_token = metadata.get("access_token", "")
        refresh_token = metadata.get("refresh_token", "")

        # Get OAuth credentials
        client_id = ""
        client_secret = ""
        # ... get from settings based on platform

        # Revoke access token
        if access_token:
            await oauth_service.revoke_token(
                provider=provider,
                token=access_token,
                client_id=client_id,
                client_secret=client_secret,
                token_type="access_token"
            )

        # Revoke refresh token
        if refresh_token:
            await oauth_service.revoke_token(
                provider=provider,
                token=refresh_token,
                client_id=client_id,
                client_secret=client_secret,
                token_type="refresh_token"
            )

        # Update integration status
        from app.models.integration import IntegrationUpdate
        await integration_service.update_integration(
            integration_id,
            IntegrationUpdate(status=IntegrationStatus.REVOKED)
        )

        logger.info(f"Revoked OAuth tokens for integration {integration_id}")

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token revocation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke token: {str(e)}"
        )
