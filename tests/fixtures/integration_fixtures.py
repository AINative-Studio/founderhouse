"""
AI Chief of Staff - Integration Test Data Factories
Sprint 2: MCP Integration Framework Testing

Factory classes for generating integration-specific test data including
OAuth tokens, health checks, and connector configurations.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import uuid4

import factory
from faker import Faker

from tests.fixtures.mcp_responses import (
    get_oauth_token_response,
    get_zoom_user_info,
    get_slack_auth_test,
    get_discord_user_info
)

fake = Faker()


# ============================================================================
# OAUTH TOKEN FACTORIES
# ============================================================================

class OAuthTokenFactory(factory.Factory):
    """Factory for generating OAuth token test data"""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid4()))
    integration_id = factory.LazyFunction(lambda: str(uuid4()))
    access_token = factory.LazyAttribute(lambda obj: f"mock_access_token_{uuid4().hex[:16]}")
    refresh_token = factory.LazyAttribute(lambda obj: f"mock_refresh_token_{uuid4().hex[:16]}")
    token_type = "Bearer"
    expires_at = factory.LazyFunction(lambda: (datetime.utcnow() + timedelta(hours=1)).isoformat())
    scope = factory.LazyFunction(lambda: " ".join(["read", "write", fake.word()]))
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())
    updated_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())

    @classmethod
    def expired(cls, **kwargs):
        """Create an expired OAuth token"""
        return cls(
            expires_at=(datetime.utcnow() - timedelta(hours=1)).isoformat(),
            **kwargs
        )

    @classmethod
    def expiring_soon(cls, **kwargs):
        """Create a token expiring within 24 hours"""
        return cls(
            expires_at=(datetime.utcnow() + timedelta(hours=23)).isoformat(),
            **kwargs
        )

    @classmethod
    def for_platform(cls, platform: str, **kwargs):
        """Create OAuth token for a specific platform"""
        return cls(
            access_token=f"mock_{platform}_access_token_{uuid4().hex[:16]}",
            refresh_token=f"mock_{platform}_refresh_token_{uuid4().hex[:16]}",
            **kwargs
        )


class OAuthStateFactory(factory.Factory):
    """Factory for generating OAuth state parameter test data"""

    class Meta:
        model = dict

    state = factory.LazyFunction(lambda: uuid4().hex)
    workspace_id = factory.LazyFunction(lambda: str(uuid4()))
    platform = factory.Iterator(["zoom", "slack", "discord", "outlook", "monday", "notion"])
    redirect_uri = factory.LazyAttribute(
        lambda obj: f"https://app.example.com/oauth/callback/{obj.platform}"
    )
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())
    expires_at = factory.LazyFunction(lambda: (datetime.utcnow() + timedelta(minutes=10)).isoformat())

    @classmethod
    def expired(cls, **kwargs):
        """Create an expired OAuth state"""
        return cls(
            expires_at=(datetime.utcnow() - timedelta(minutes=1)).isoformat(),
            **kwargs
        )


# ============================================================================
# INTEGRATION HEALTH CHECK FACTORIES
# ============================================================================

class HealthCheckFactory(factory.Factory):
    """Factory for generating health check test data"""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid4()))
    integration_id = factory.LazyFunction(lambda: str(uuid4()))
    platform = factory.Iterator(["zoom", "slack", "discord", "outlook", "monday", "notion", "granola"])
    status = factory.Iterator(["connected", "error", "pending"])
    is_healthy = factory.LazyAttribute(lambda obj: obj.status == "connected")
    last_checked = factory.LazyFunction(lambda: datetime.utcnow().isoformat())
    error_message = factory.LazyAttribute(
        lambda obj: None if obj.is_healthy else f"Connection failed for {obj.platform}"
    )
    response_time_ms = factory.LazyFunction(lambda: fake.random_int(50, 500))
    metadata = factory.LazyFunction(lambda: {
        "api_version": "v2",
        "rate_limit_remaining": fake.random_int(1000, 5000),
        "last_sync": datetime.utcnow().isoformat()
    })
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())

    @classmethod
    def healthy(cls, **kwargs):
        """Create a healthy health check"""
        return cls(
            status="connected",
            is_healthy=True,
            error_message=None,
            response_time_ms=fake.random_int(50, 200),
            **kwargs
        )

    @classmethod
    def unhealthy(cls, error: str = "Connection timeout", **kwargs):
        """Create an unhealthy health check"""
        return cls(
            status="error",
            is_healthy=False,
            error_message=error,
            response_time_ms=None,
            **kwargs
        )

    @classmethod
    def with_rate_limit(cls, **kwargs):
        """Create a health check with rate limit warning"""
        return cls(
            status="connected",
            is_healthy=True,
            metadata={
                "api_version": "v2",
                "rate_limit_remaining": 10,  # Low remaining
                "rate_limit_total": 5000,
                "rate_limit_reset": (datetime.utcnow() + timedelta(hours=1)).isoformat()
            },
            **kwargs
        )


# ============================================================================
# CONNECTOR CONFIGURATION FACTORIES
# ============================================================================

class ConnectorConfigFactory(factory.Factory):
    """Factory for generating connector configuration test data"""

    class Meta:
        model = dict

    platform = factory.Iterator(["zoom", "slack", "discord", "outlook", "monday", "notion", "granola"])
    base_url = factory.LazyAttribute(lambda obj: f"https://api.{obj.platform}.com")
    api_version = factory.Iterator(["v1", "v2", "v3"])
    timeout = factory.LazyFunction(lambda: fake.random_int(10, 60))
    max_retries = factory.LazyFunction(lambda: fake.random_int(3, 5))
    rate_limit = factory.LazyFunction(lambda: fake.random_int(100, 1000))
    scopes = factory.LazyFunction(lambda: ["read", "write", fake.word()])
    webhook_url = factory.LazyAttribute(
        lambda obj: f"https://app.example.com/webhooks/{obj.platform}"
    )

    @classmethod
    def for_zoom(cls, **kwargs):
        """Create Zoom connector configuration"""
        return cls(
            platform="zoom",
            base_url="https://api.zoom.us/v2",
            api_version="v2",
            scopes=["meeting:read", "meeting:write", "user:read"],
            **kwargs
        )

    @classmethod
    def for_slack(cls, **kwargs):
        """Create Slack connector configuration"""
        return cls(
            platform="slack",
            base_url="https://slack.com/api",
            api_version="v1",
            scopes=["channels:read", "chat:write", "users:read"],
            **kwargs
        )

    @classmethod
    def for_discord(cls, **kwargs):
        """Create Discord connector configuration"""
        return cls(
            platform="discord",
            base_url="https://discord.com/api/v10",
            api_version="v10",
            scopes=["bot", "messages.read", "guilds"],
            **kwargs
        )


# ============================================================================
# ENHANCED INTEGRATION FACTORY
# ============================================================================

class IntegrationFactory(factory.Factory):
    """
    Enhanced integration factory with MCP-specific fields
    Extends the base IntegrationFactory from sample_data.py
    """

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid4()))
    workspace_id = factory.LazyFunction(lambda: str(uuid4()))
    founder_id = factory.LazyFunction(lambda: str(uuid4()))
    platform = factory.Iterator([
        "gmail", "outlook", "slack", "discord", "zoom",
        "loom", "fireflies", "otter", "monday", "notion", "granola"
    ])
    connection_type = factory.Iterator(["mcp", "api"])
    status = factory.Iterator(["connected", "error", "revoked", "pending"])
    credentials_enc = factory.LazyFunction(lambda: uuid4().hex)
    metadata = factory.LazyFunction(lambda: {
        "oauth_version": "2.0",
        "scopes": ["read", "write"],
        "last_sync": datetime.utcnow().isoformat(),
        "sync_enabled": True
    })
    connected_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())
    updated_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())

    # OAuth-specific fields
    access_token_expires_at = factory.LazyFunction(
        lambda: (datetime.utcnow() + timedelta(hours=1)).isoformat()
    )
    last_health_check = factory.LazyFunction(lambda: datetime.utcnow().isoformat())
    health_check_count = factory.LazyFunction(lambda: fake.random_int(0, 100))
    error_count = 0
    last_error = None

    @classmethod
    def connected(cls, platform: str = "zoom", **kwargs):
        """Create a connected integration"""
        return cls(
            platform=platform,
            status="connected",
            connected_at=datetime.utcnow().isoformat(),
            error_count=0,
            last_error=None,
            **kwargs
        )

    @classmethod
    def with_error(cls, platform: str = "zoom", error: str = "Connection failed", **kwargs):
        """Create an integration with error status"""
        return cls(
            platform=platform,
            status="error",
            error_count=fake.random_int(1, 10),
            last_error=error,
            **kwargs
        )

    @classmethod
    def revoked(cls, platform: str = "zoom", **kwargs):
        """Create a revoked integration"""
        return cls(
            platform=platform,
            status="revoked",
            connected_at=None,
            **kwargs
        )

    @classmethod
    def pending(cls, platform: str = "zoom", **kwargs):
        """Create a pending integration"""
        return cls(
            platform=platform,
            status="pending",
            connected_at=None,
            **kwargs
        )

    @classmethod
    def with_expired_token(cls, platform: str = "zoom", **kwargs):
        """Create an integration with expired OAuth token"""
        return cls(
            platform=platform,
            status="error",
            access_token_expires_at=(datetime.utcnow() - timedelta(hours=1)).isoformat(),
            error_count=1,
            last_error="Token expired",
            **kwargs
        )


# ============================================================================
# WEBHOOK EVENT FACTORIES
# ============================================================================

class WebhookEventFactory(factory.Factory):
    """Factory for generating webhook event test data"""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid4()))
    integration_id = factory.LazyFunction(lambda: str(uuid4()))
    event_type = factory.Iterator([
        "meeting.created",
        "meeting.started",
        "meeting.ended",
        "message.sent",
        "task.created",
        "task.completed"
    ])
    payload = factory.LazyFunction(lambda: {
        "object": {
            "id": str(uuid4()),
            "type": fake.word(),
            "timestamp": datetime.utcnow().isoformat()
        }
    })
    received_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())
    processed = factory.LazyFunction(lambda: fake.boolean())
    processed_at = factory.LazyAttribute(
        lambda obj: datetime.utcnow().isoformat() if obj.processed else None
    )
    signature = factory.LazyFunction(lambda: uuid4().hex)


# ============================================================================
# SYNC JOB FACTORIES
# ============================================================================

class SyncJobFactory(factory.Factory):
    """Factory for generating sync job test data"""

    class Meta:
        model = dict

    id = factory.LazyFunction(lambda: str(uuid4()))
    integration_id = factory.LazyFunction(lambda: str(uuid4()))
    sync_type = factory.Iterator(["full", "incremental", "delta"])
    status = factory.Iterator(["pending", "running", "completed", "failed"])
    started_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())
    completed_at = factory.LazyAttribute(
        lambda obj: datetime.utcnow().isoformat() if obj.status == "completed" else None
    )
    records_synced = factory.LazyFunction(lambda: fake.random_int(0, 1000))
    records_failed = factory.LazyFunction(lambda: fake.random_int(0, 10))
    error_message = factory.LazyAttribute(
        lambda obj: f"Sync error: {fake.sentence()}" if obj.status == "failed" else None
    )

    @classmethod
    def completed(cls, records: int = 100, **kwargs):
        """Create a completed sync job"""
        return cls(
            status="completed",
            completed_at=datetime.utcnow().isoformat(),
            records_synced=records,
            records_failed=0,
            error_message=None,
            **kwargs
        )

    @classmethod
    def failed(cls, error: str = "Sync failed", **kwargs):
        """Create a failed sync job"""
        return cls(
            status="failed",
            completed_at=datetime.utcnow().isoformat(),
            records_synced=0,
            records_failed=fake.random_int(1, 100),
            error_message=error,
            **kwargs
        )


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_integration_with_oauth(
    platform: str = "zoom",
    workspace_id: str = None,
    status: str = "connected"
) -> Dict[str, Any]:
    """
    Create a complete integration with OAuth token

    Args:
        platform: Platform name
        workspace_id: Workspace ID
        status: Integration status

    Returns:
        Dictionary with integration and OAuth token
    """
    integration = IntegrationFactory(
        platform=platform,
        workspace_id=workspace_id or str(uuid4()),
        status=status
    )

    oauth_token = OAuthTokenFactory.for_platform(
        platform=platform,
        integration_id=integration["id"]
    )

    return {
        "integration": integration,
        "oauth_token": oauth_token
    }


def create_integration_with_health_check(
    platform: str = "zoom",
    is_healthy: bool = True
) -> Dict[str, Any]:
    """
    Create an integration with health check data

    Args:
        platform: Platform name
        is_healthy: Whether integration is healthy

    Returns:
        Dictionary with integration and health check
    """
    integration = IntegrationFactory(
        platform=platform,
        status="connected" if is_healthy else "error"
    )

    health_check = (
        HealthCheckFactory.healthy(integration_id=integration["id"], platform=platform)
        if is_healthy
        else HealthCheckFactory.unhealthy(integration_id=integration["id"], platform=platform)
    )

    return {
        "integration": integration,
        "health_check": health_check
    }


def create_workspace_with_integrations(
    platform_list: list[str] = None,
    num_integrations: int = 3
) -> Dict[str, Any]:
    """
    Create a workspace with multiple integrations

    Args:
        platform_list: List of platforms (auto-generated if None)
        num_integrations: Number of integrations to create

    Returns:
        Dictionary with workspace and integrations
    """
    workspace_id = str(uuid4())

    if not platform_list:
        platform_list = ["zoom", "slack", "discord", "outlook", "monday"][:num_integrations]

    integrations = []
    for platform in platform_list:
        integration = IntegrationFactory.connected(
            platform=platform,
            workspace_id=workspace_id
        )
        integrations.append(integration)

    return {
        "workspace_id": workspace_id,
        "integrations": integrations
    }


def create_oauth_flow_data(platform: str = "zoom") -> Dict[str, Any]:
    """
    Create complete OAuth flow test data

    Args:
        platform: Platform name

    Returns:
        Dictionary with OAuth state, code, and tokens
    """
    state = OAuthStateFactory(platform=platform)
    authorization_code = uuid4().hex
    token_response = get_oauth_token_response(platform=platform)

    return {
        "state": state,
        "authorization_code": authorization_code,
        "token_response": token_response,
        "redirect_uri": state["redirect_uri"]
    }
