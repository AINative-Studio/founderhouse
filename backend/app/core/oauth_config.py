"""
OAuth Configuration
Platform-specific OAuth2 configurations for MCP integrations
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class OAuthProvider(str, Enum):
    """Supported OAuth providers"""
    ZOOM = "zoom"
    SLACK = "slack"
    DISCORD = "discord"
    MICROSOFT = "microsoft"  # For Outlook/Office 365
    MONDAY = "monday"
    NOTION = "notion"
    GOOGLE = "google"  # For Gmail
    LOOM = "loom"


class OAuthConfig(BaseModel):
    """OAuth configuration for a platform"""
    provider: OAuthProvider
    client_id: str
    client_secret: str
    authorization_url: str
    token_url: str
    scopes: List[str]
    redirect_uri: str
    revoke_url: Optional[str] = None
    user_info_url: Optional[str] = None
    extra_params: Dict[str, str] = Field(default_factory=dict)


# OAuth Configuration Templates
# These use environment variables that should be set in .env

ZOOM_OAUTH_CONFIG = {
    "provider": OAuthProvider.ZOOM,
    "authorization_url": "https://zoom.us/oauth/authorize",
    "token_url": "https://zoom.us/oauth/token",
    "revoke_url": "https://zoom.us/oauth/revoke",
    "user_info_url": "https://api.zoom.us/v2/users/me",
    "scopes": [
        "meeting:read",
        "meeting:write",
        "recording:read",
        "user:read",
        "webinar:read"
    ]
}

SLACK_OAUTH_CONFIG = {
    "provider": OAuthProvider.SLACK,
    "authorization_url": "https://slack.com/oauth/v2/authorize",
    "token_url": "https://slack.com/api/oauth.v2.access",
    "revoke_url": "https://slack.com/api/auth.revoke",
    "user_info_url": "https://slack.com/api/auth.test",
    "scopes": [
        "channels:history",
        "channels:read",
        "chat:write",
        "users:read",
        "team:read",
        "im:history",
        "mpim:history",
        "groups:history"
    ]
}

DISCORD_OAUTH_CONFIG = {
    "provider": OAuthProvider.DISCORD,
    "authorization_url": "https://discord.com/api/oauth2/authorize",
    "token_url": "https://discord.com/api/oauth2/token",
    "revoke_url": "https://discord.com/api/oauth2/token/revoke",
    "user_info_url": "https://discord.com/api/users/@me",
    "scopes": [
        "identify",
        "guilds",
        "guilds.members.read",
        "messages.read",
        "bot"
    ]
}

MICROSOFT_OAUTH_CONFIG = {
    "provider": OAuthProvider.MICROSOFT,
    "authorization_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
    "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
    "user_info_url": "https://graph.microsoft.com/v1.0/me",
    "scopes": [
        "https://graph.microsoft.com/Mail.Read",
        "https://graph.microsoft.com/Mail.Send",
        "https://graph.microsoft.com/Calendars.Read",
        "https://graph.microsoft.com/Calendars.ReadWrite",
        "https://graph.microsoft.com/User.Read",
        "offline_access"
    ]
}

MONDAY_OAUTH_CONFIG = {
    "provider": OAuthProvider.MONDAY,
    "authorization_url": "https://auth.monday.com/oauth2/authorize",
    "token_url": "https://auth.monday.com/oauth2/token",
    "user_info_url": "https://api.monday.com/v2",
    "scopes": [
        "boards:read",
        "boards:write",
        "workspaces:read",
        "users:read"
    ]
}

NOTION_OAUTH_CONFIG = {
    "provider": OAuthProvider.NOTION,
    "authorization_url": "https://api.notion.com/v1/oauth/authorize",
    "token_url": "https://api.notion.com/v1/oauth/token",
    "user_info_url": "https://api.notion.com/v1/users/me",
    "scopes": []  # Notion uses basic auth scope
}

GOOGLE_OAUTH_CONFIG = {
    "provider": OAuthProvider.GOOGLE,
    "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
    "token_url": "https://oauth2.googleapis.com/token",
    "revoke_url": "https://oauth2.googleapis.com/revoke",
    "user_info_url": "https://www.googleapis.com/oauth2/v2/userinfo",
    "scopes": [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile"
    ],
    "extra_params": {
        "access_type": "offline",
        "prompt": "consent"
    }
}

LOOM_OAUTH_CONFIG = {
    "provider": OAuthProvider.LOOM,
    "authorization_url": "https://www.loom.com/oauth/authorize",
    "token_url": "https://www.loom.com/oauth/token",
    "user_info_url": "https://www.loom.com/api/v1/users/me",
    "scopes": [
        "video.read",
        "video.write",
        "user.read"
    ]
}


# Provider configuration mapping
OAUTH_CONFIGS: Dict[OAuthProvider, Dict] = {
    OAuthProvider.ZOOM: ZOOM_OAUTH_CONFIG,
    OAuthProvider.SLACK: SLACK_OAUTH_CONFIG,
    OAuthProvider.DISCORD: DISCORD_OAUTH_CONFIG,
    OAuthProvider.MICROSOFT: MICROSOFT_OAUTH_CONFIG,
    OAuthProvider.MONDAY: MONDAY_OAUTH_CONFIG,
    OAuthProvider.NOTION: NOTION_OAUTH_CONFIG,
    OAuthProvider.GOOGLE: GOOGLE_OAUTH_CONFIG,
    OAuthProvider.LOOM: LOOM_OAUTH_CONFIG,
}


def get_oauth_config(provider: OAuthProvider, client_id: str, client_secret: str, redirect_uri: str) -> OAuthConfig:
    """
    Get OAuth configuration for a provider

    Args:
        provider: OAuth provider
        client_id: OAuth client ID
        client_secret: OAuth client secret
        redirect_uri: OAuth redirect URI

    Returns:
        Complete OAuth configuration

    Raises:
        ValueError: If provider is not supported
    """
    if provider not in OAUTH_CONFIGS:
        raise ValueError(f"Unsupported OAuth provider: {provider}")

    config_template = OAUTH_CONFIGS[provider]

    return OAuthConfig(
        provider=provider,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        **config_template
    )


# Platform to OAuth provider mapping (for platforms that use OAuth)
PLATFORM_OAUTH_MAPPING = {
    "zoom": OAuthProvider.ZOOM,
    "slack": OAuthProvider.SLACK,
    "discord": OAuthProvider.DISCORD,
    "outlook": OAuthProvider.MICROSOFT,
    "monday": OAuthProvider.MONDAY,
    "notion": OAuthProvider.NOTION,
    "gmail": OAuthProvider.GOOGLE,
    "loom": OAuthProvider.LOOM,
}


def get_provider_for_platform(platform: str) -> Optional[OAuthProvider]:
    """
    Get OAuth provider for a platform

    Args:
        platform: Platform name (zoom, slack, etc.)

    Returns:
        OAuth provider if platform supports OAuth, None otherwise
    """
    return PLATFORM_OAUTH_MAPPING.get(platform.lower())
