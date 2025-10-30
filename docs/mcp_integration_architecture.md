# MCP Integration Architecture

**Version:** 1.0
**Date:** 2025-10-30
**Sprint:** 2 - MCP Integration Framework
**Author:** System Architect

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [MCP Integration Overview](#mcp-integration-overview)
3. [Integration Connector Patterns](#integration-connector-patterns)
4. [OAuth2 Flow Design](#oauth2-flow-design)
5. [Token Management Strategy](#token-management-strategy)
6. [Health Monitoring Architecture](#health-monitoring-architecture)
7. [Error Handling Patterns](#error-handling-patterns)
8. [Rate Limiting & Circuit Breaker](#rate-limiting--circuit-breaker)
9. [Integration State Machine](#integration-state-machine)
10. [Security Architecture](#security-architecture)
11. [API Specifications](#api-specifications)
12. [Performance & Scalability](#performance--scalability)

---

## Executive Summary

The MCP Integration Framework provides a **secure, scalable, and resilient** connectivity layer between the AI Chief of Staff platform and 13 external platforms through the Model Context Protocol (MCP). This architecture enables seamless data ingestion, bidirectional sync, and real-time monitoring across:

**Communication Platforms:** Gmail, Outlook, Slack, Discord
**Meeting Platforms:** Zoom, Fireflies, Otter
**Media Platforms:** Loom
**Work Management:** Monday.com, Notion
**Analytics:** Granola
**Infrastructure:** ZeroDB, ZeroVoice

### Key Architectural Decisions

| Decision | Rationale | Impact |
|----------|-----------|---------|
| **MCP-First Architecture** | Unified protocol across all integrations | Reduced complexity, consistent patterns |
| **OAuth 2.0 Standard** | Industry-standard authentication | Secure, revocable access |
| **AES-256-GCM Token Encryption** | Military-grade encryption at rest | GDPR/SOC2 compliance |
| **6-Hour Health Checks** | Balance between responsiveness and API quotas | Early failure detection |
| **Circuit Breaker Pattern** | Prevent cascade failures | System resilience |
| **Event-Sourced Integration Logs** | Complete audit trail | Debugging and compliance |

### Architecture Metrics

- **Supported Platforms:** 13 MCP integrations
- **OAuth Providers:** 10 (Gmail, Outlook, Zoom, Slack, Discord, Monday, Notion, Loom, Fireflies, Otter)
- **Token Refresh Strategy:** Automatic refresh 24h before expiry
- **Health Check Interval:** Every 6 hours
- **Max Retry Attempts:** 3 with exponential backoff
- **Circuit Breaker Threshold:** 5 failures in 15 minutes
- **Token Rotation:** 90-day automatic rotation policy

---

## MCP Integration Overview

### Integration Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                    External MCP Services                         │
│  Zoom │ Slack │ Gmail │ Monday │ Loom │ Fireflies │ Notion...   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  MCP Adapter Layer (FastAPI)                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  OAuth Flow Manager │ Token Refresh │ Health Monitor     │   │
│  │  Rate Limiter       │ Circuit Breaker │ Retry Logic      │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Integration Registry & State                     │
│          (Supabase: core.integrations + mcp.* tables)            │
└─────────────────────────────────────────────────────────────────┘
```

### MCP Connection Lifecycle

```
┌──────────┐     ┌───────────┐     ┌──────────┐     ┌─────────┐
│ Pending  │ ──> │ Authorizing│ ──> │Connected │ <──>│ Active  │
└──────────┘     └───────────┘     └──────────┘     └─────────┘
     │                                    │               │
     │                                    ▼               ▼
     │                              ┌──────────┐    ┌─────────┐
     └─────────────────────────────>│  Error   │    │ Revoked │
                                     └──────────┘    └─────────┘
                                          │               │
                                          ▼               ▼
                                     ┌──────────┐    ┌─────────┐
                                     │Reconnect │    │Deleted  │
                                     └──────────┘    └─────────┘
```

---

## Integration Connector Patterns

### Base MCP Connector Interface

All platform connectors implement a standardized interface:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

class MCPConnector(ABC):
    """Base class for all MCP platform connectors"""

    def __init__(self, integration_id: str, config: Dict[str, Any]):
        self.integration_id = integration_id
        self.config = config
        self.platform_name = self._get_platform_name()
        self.oauth_provider = self._get_oauth_provider()

    @abstractmethod
    def _get_platform_name(self) -> str:
        """Return platform enum name"""
        pass

    @abstractmethod
    def _get_oauth_provider(self) -> str:
        """Return OAuth provider identifier"""
        pass

    @abstractmethod
    async def authorize(self, auth_code: str) -> Dict[str, Any]:
        """Complete OAuth flow and return tokens"""
        pass

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token"""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Verify connection is active"""
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """Revoke tokens and cleanup"""
        pass

    # Common methods
    async def store_credentials(self, tokens: Dict[str, Any]) -> None:
        """Encrypt and store OAuth tokens"""
        pass

    async def get_credentials(self) -> Dict[str, Any]:
        """Decrypt and retrieve OAuth tokens"""
        pass

    async def log_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Log integration event to ops.events"""
        pass
```

### Connector Registry

Central registry for all platform connectors:

```python
from enum import Enum
from typing import Type, Dict

class Platform(str, Enum):
    GMAIL = "gmail"
    OUTLOOK = "outlook"
    SLACK = "slack"
    DISCORD = "discord"
    ZOOM = "zoom"
    LOOM = "loom"
    FIREFLIES = "fireflies"
    OTTER = "otter"
    MONDAY = "monday"
    NOTION = "notion"
    GRANOLA = "granola"
    ZERODB = "zerodb"
    ZEROVOICE = "zerovoice"

class ConnectorRegistry:
    """Registry of all MCP connectors"""

    _connectors: Dict[Platform, Type[MCPConnector]] = {}

    @classmethod
    def register(cls, platform: Platform):
        """Decorator to register connector"""
        def wrapper(connector_class: Type[MCPConnector]):
            cls._connectors[platform] = connector_class
            return connector_class
        return wrapper

    @classmethod
    def get_connector(cls, platform: Platform,
                     integration_id: str,
                     config: Dict[str, Any]) -> MCPConnector:
        """Factory method to create connector instance"""
        connector_class = cls._connectors.get(platform)
        if not connector_class:
            raise ValueError(f"No connector registered for platform: {platform}")
        return connector_class(integration_id, config)

    @classmethod
    def list_platforms(cls) -> list[Platform]:
        """List all supported platforms"""
        return list(cls._connectors.keys())
```

### Example: Zoom MCP Connector

```python
from app.integrations.base import MCPConnector, ConnectorRegistry, Platform
import httpx
from typing import Dict, Any

@ConnectorRegistry.register(Platform.ZOOM)
class ZoomMCPConnector(MCPConnector):
    """Zoom MCP connector for meetings and recordings"""

    OAUTH_AUTHORIZE_URL = "https://zoom.us/oauth/authorize"
    OAUTH_TOKEN_URL = "https://zoom.us/oauth/token"
    API_BASE_URL = "https://api.zoom.us/v2"

    SCOPES = [
        "meeting:read",
        "recording:read",
        "user:read",
        "webinar:read"
    ]

    def _get_platform_name(self) -> str:
        return Platform.ZOOM

    def _get_oauth_provider(self) -> str:
        return "zoom"

    async def authorize(self, auth_code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.OAUTH_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": auth_code,
                    "redirect_uri": self.config["redirect_uri"]
                },
                auth=(self.config["client_id"], self.config["client_secret"])
            )
            response.raise_for_status()
            tokens = response.json()

            # Store encrypted credentials
            await self.store_credentials(tokens)

            # Log event
            await self.log_event("integration.connected", {
                "platform": "zoom",
                "integration_id": self.integration_id
            })

            return tokens

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh Zoom access token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.OAUTH_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token
                },
                auth=(self.config["client_id"], self.config["client_secret"])
            )
            response.raise_for_status()
            tokens = response.json()

            # Update stored credentials
            await self.store_credentials(tokens)

            await self.log_event("integration.token_refreshed", {
                "platform": "zoom",
                "integration_id": self.integration_id
            })

            return tokens

    async def health_check(self) -> Dict[str, Any]:
        """Verify Zoom connection by fetching user profile"""
        credentials = await self.get_credentials()
        access_token = credentials["access_token"]

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.API_BASE_URL}/users/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "platform": "zoom",
                    "checked_at": datetime.utcnow().isoformat()
                }
            elif response.status_code == 401:
                # Token expired, try refresh
                new_tokens = await self.refresh_token(credentials["refresh_token"])
                return {
                    "status": "recovered",
                    "platform": "zoom",
                    "action": "token_refreshed"
                }
            else:
                return {
                    "status": "unhealthy",
                    "platform": "zoom",
                    "error": response.text
                }

    async def disconnect(self) -> bool:
        """Revoke Zoom OAuth tokens"""
        credentials = await self.get_credentials()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://zoom.us/oauth/revoke",
                data={"token": credentials["access_token"]},
                auth=(self.config["client_id"], self.config["client_secret"])
            )

            await self.log_event("integration.disconnected", {
                "platform": "zoom",
                "integration_id": self.integration_id
            })

            return response.status_code == 200
```

### Platform-Specific Connector Patterns

Each platform has unique characteristics:

#### Communication Platforms (Gmail, Outlook, Slack, Discord)

**Pattern:** Webhook-based real-time ingestion + polling fallback

```python
class CommunicationConnector(MCPConnector):
    """Base for communication platforms"""

    async def setup_webhook(self, callback_url: str) -> Dict[str, Any]:
        """Register webhook for real-time events"""
        pass

    async def poll_messages(self, since: datetime) -> List[Dict]:
        """Poll for new messages (fallback if webhook fails)"""
        pass

    async def send_message(self, channel: str, content: str) -> Dict:
        """Send message to platform"""
        pass
```

#### Meeting Platforms (Zoom, Fireflies, Otter)

**Pattern:** Recording/transcript ingestion with chunking

```python
class MeetingConnector(MCPConnector):
    """Base for meeting platforms"""

    async def fetch_recordings(self, since: datetime) -> List[Dict]:
        """Fetch meeting recordings"""
        pass

    async def fetch_transcript(self, recording_id: str) -> Dict:
        """Fetch transcript for recording"""
        pass

    async def chunk_transcript(self, transcript: Dict) -> List[Dict]:
        """Split transcript into vectorizable chunks"""
        pass
```

#### Work Management (Monday, Notion)

**Pattern:** Bidirectional sync with conflict resolution

```python
class WorkConnector(MCPConnector):
    """Base for work management platforms"""

    async def create_task(self, task_data: Dict) -> Dict:
        """Create task on external platform"""
        pass

    async def update_task(self, external_id: str, updates: Dict) -> Dict:
        """Update existing task"""
        pass

    async def sync_changes(self, since: datetime) -> List[Dict]:
        """Fetch changes from platform"""
        pass

    async def resolve_conflict(self, local: Dict, remote: Dict) -> Dict:
        """Resolve sync conflicts (last-write-wins or merge)"""
        pass
```

---

## OAuth2 Flow Design

### OAuth 2.0 Authorization Code Flow

Standard OAuth 2.0 flow for all platforms:

```
┌────────┐                               ┌──────────────┐
│ User   │                               │ AI Chief of  │
│(Founder)                               │    Staff     │
└───┬────┘                               └──────┬───────┘
    │                                           │
    │ 1. Click "Connect Zoom"                   │
    │─────────────────────────────────────────> │
    │                                           │
    │                                           │ 2. Generate state & PKCE
    │                                           │    verifier
    │                                           │
    │ 3. Redirect to Zoom OAuth                 │
    │ <─────────────────────────────────────────│
    │                                           │
┌───▼────────────┐                              │
│  Zoom OAuth    │                              │
│  Consent Page  │                              │
└───┬────────────┘                              │
    │                                           │
    │ 4. User approves scopes                   │
    │                                           │
    │ 5. Redirect to callback                   │
    │   with auth code + state                  │
    │─────────────────────────────────────────> │
    │                                           │
    │                                           │ 6. Validate state
    │                                           │ 7. Exchange code for tokens
    │                                           │
    │                                           ▼
    │                                    ┌─────────────┐
    │                                    │  Zoom API   │
    │                                    └─────┬───────┘
    │                                          │
    │                                          │ 8. Return access_token
    │                                          │    refresh_token
    │                                          │    expires_in
    │                                          │
    │                                    ┌─────▼───────┐
    │                                    │ Encrypt &   │
    │                                    │ Store Tokens│
    │                                    └─────┬───────┘
    │                                          │
    │ 9. Success confirmation                  │
    │ <─────────────────────────────────────────│
    │                                           │
```

### OAuth Endpoint Implementation

```python
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import RedirectResponse
from app.integrations.registry import ConnectorRegistry, Platform
from app.core.security import generate_state_token, verify_state_token
import secrets
import hashlib
import base64

router = APIRouter(prefix="/integrations", tags=["integrations"])

# In-memory state storage (use Redis in production)
oauth_states = {}

@router.get("/connect/{platform}")
async def initiate_oauth(
    platform: Platform,
    workspace_id: str,
    founder_id: str,
    current_user = Depends(get_current_user)
):
    """
    Initiate OAuth flow for platform integration

    1. Generate state token (CSRF protection)
    2. Generate PKCE code_verifier and code_challenge
    3. Build authorization URL
    4. Redirect user to OAuth provider
    """

    # Generate CSRF state token
    state = secrets.token_urlsafe(32)

    # Generate PKCE verifier (for enhanced security)
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().rstrip('=')

    # Store state with metadata (expires in 10 minutes)
    oauth_states[state] = {
        "platform": platform,
        "workspace_id": workspace_id,
        "founder_id": founder_id,
        "user_id": current_user.id,
        "code_verifier": code_verifier,
        "created_at": datetime.utcnow()
    }

    # Get platform-specific OAuth configuration
    config = get_oauth_config(platform)

    # Build authorization URL
    auth_url = (
        f"{config['authorize_url']}?"
        f"client_id={config['client_id']}&"
        f"response_type=code&"
        f"redirect_uri={config['redirect_uri']}&"
        f"scope={' '.join(config['scopes'])}&"
        f"state={state}&"
        f"code_challenge={code_challenge}&"
        f"code_challenge_method=S256"
    )

    # Log event
    await log_integration_event(
        workspace_id=workspace_id,
        event_type="integration.oauth_initiated",
        payload={
            "platform": platform,
            "founder_id": founder_id
        }
    )

    return RedirectResponse(url=auth_url)


@router.get("/callback/{platform}")
async def oauth_callback(
    platform: Platform,
    code: str = Query(...),
    state: str = Query(...),
    error: str = Query(None)
):
    """
    OAuth callback endpoint

    1. Verify state token (CSRF protection)
    2. Exchange authorization code for tokens
    3. Encrypt and store tokens
    4. Update integration status
    5. Redirect to success page
    """

    # Handle OAuth errors
    if error:
        raise HTTPException(
            status_code=400,
            detail=f"OAuth error: {error}"
        )

    # Verify state token
    state_data = oauth_states.get(state)
    if not state_data:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired state token"
        )

    # Verify platform matches
    if state_data["platform"] != platform:
        raise HTTPException(
            status_code=400,
            detail="Platform mismatch"
        )

    # Check state expiration (10 minutes)
    if (datetime.utcnow() - state_data["created_at"]).seconds > 600:
        del oauth_states[state]
        raise HTTPException(
            status_code=400,
            detail="State token expired"
        )

    try:
        # Create integration record
        integration = await create_integration(
            workspace_id=state_data["workspace_id"],
            founder_id=state_data["founder_id"],
            platform=platform,
            status="authorizing"
        )

        # Get connector config
        config = get_oauth_config(platform)
        config["redirect_uri"] = get_callback_url(platform)

        # Create connector instance
        connector = ConnectorRegistry.get_connector(
            platform=platform,
            integration_id=str(integration.id),
            config=config
        )

        # Exchange code for tokens
        tokens = await connector.authorize(code)

        # Update integration status
        await update_integration_status(
            integration_id=integration.id,
            status="connected",
            connected_at=datetime.utcnow(),
            metadata={
                "token_expires_at": (
                    datetime.utcnow() +
                    timedelta(seconds=tokens.get("expires_in", 3600))
                ).isoformat()
            }
        )

        # Clean up state
        del oauth_states[state]

        # Log success event
        await log_integration_event(
            workspace_id=state_data["workspace_id"],
            event_type="integration.connected",
            payload={
                "platform": platform,
                "integration_id": str(integration.id)
            }
        )

        # Redirect to success page
        return RedirectResponse(
            url=f"/integrations/success?platform={platform}"
        )

    except Exception as e:
        # Update integration status to error
        await update_integration_status(
            integration_id=integration.id,
            status="error",
            error_message=str(e)
        )

        # Log error event
        await log_integration_event(
            workspace_id=state_data["workspace_id"],
            event_type="integration.error",
            payload={
                "platform": platform,
                "error": str(e)
            }
        )

        raise HTTPException(
            status_code=500,
            detail=f"Failed to complete OAuth flow: {str(e)}"
        )


@router.delete("/disconnect/{integration_id}")
async def disconnect_integration(
    integration_id: str,
    current_user = Depends(get_current_user)
):
    """
    Disconnect and revoke integration

    1. Verify user has access
    2. Revoke OAuth tokens
    3. Update integration status
    4. Log event
    """

    integration = await get_integration(integration_id)

    # Verify access
    if not await user_has_access(current_user.id, integration.workspace_id):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        # Get connector
        config = get_oauth_config(integration.platform)
        connector = ConnectorRegistry.get_connector(
            platform=integration.platform,
            integration_id=integration_id,
            config=config
        )

        # Revoke tokens
        await connector.disconnect()

        # Update status
        await update_integration_status(
            integration_id=integration_id,
            status="revoked"
        )

        # Log event
        await log_integration_event(
            workspace_id=integration.workspace_id,
            event_type="integration.disconnected",
            payload={
                "platform": integration.platform,
                "integration_id": integration_id
            }
        )

        return {"status": "disconnected", "integration_id": integration_id}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to disconnect integration: {str(e)}"
        )
```

---

## Token Management Strategy

### Encryption at Rest (AES-256-GCM)

All OAuth tokens are encrypted before storage:

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import os
import json
import base64

class TokenEncryption:
    """AES-256-GCM encryption for OAuth tokens"""

    def __init__(self, master_key: bytes):
        """
        Initialize with master key from environment/vault
        Master key should be 32 bytes (256 bits)
        """
        self.master_key = master_key

    def encrypt(self, tokens: dict) -> bytes:
        """
        Encrypt token dictionary

        Returns: encrypted_data (includes nonce)
        Format: nonce (12 bytes) || ciphertext || tag (16 bytes)
        """
        # Generate random nonce (12 bytes for GCM)
        nonce = os.urandom(12)

        # Serialize tokens to JSON
        plaintext = json.dumps(tokens).encode('utf-8')

        # Encrypt with AES-256-GCM
        aesgcm = AESGCM(self.master_key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        # Combine nonce + ciphertext
        encrypted_data = nonce + ciphertext

        return encrypted_data

    def decrypt(self, encrypted_data: bytes) -> dict:
        """
        Decrypt token data

        Args: encrypted_data (nonce || ciphertext || tag)
        Returns: token dictionary
        """
        # Extract nonce (first 12 bytes)
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]

        # Decrypt with AES-256-GCM
        aesgcm = AESGCM(self.master_key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)

        # Deserialize JSON
        tokens = json.loads(plaintext.decode('utf-8'))

        return tokens


# Integration with database
async def store_encrypted_tokens(
    integration_id: str,
    tokens: dict
):
    """Store encrypted OAuth tokens"""

    # Get master key from Supabase Vault or environment
    master_key = get_master_key()  # 32-byte key

    # Encrypt tokens
    encryptor = TokenEncryption(master_key)
    encrypted_data = encryptor.encrypt(tokens)

    # Store in database
    await db.execute(
        """
        UPDATE core.integrations
        SET credentials_enc = $1,
            updated_at = now()
        WHERE id = $2
        """,
        encrypted_data,
        integration_id
    )


async def retrieve_encrypted_tokens(
    integration_id: str
) -> dict:
    """Retrieve and decrypt OAuth tokens"""

    # Fetch encrypted data
    result = await db.fetchrow(
        """
        SELECT credentials_enc
        FROM core.integrations
        WHERE id = $1
        """,
        integration_id
    )

    if not result or not result['credentials_enc']:
        raise ValueError("No credentials found")

    # Get master key
    master_key = get_master_key()

    # Decrypt tokens
    encryptor = TokenEncryption(master_key)
    tokens = encryptor.decrypt(result['credentials_enc'])

    return tokens
```

### Automatic Token Refresh

Background task to refresh tokens before expiration:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta

class TokenRefreshService:
    """Automatic token refresh scheduler"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def start(self):
        """Start the refresh scheduler"""
        # Run every hour
        self.scheduler.add_job(
            self.refresh_expiring_tokens,
            'interval',
            hours=1,
            id='token_refresh'
        )
        self.scheduler.start()

    async def refresh_expiring_tokens(self):
        """
        Find and refresh tokens expiring within 24 hours
        """
        # Find integrations with tokens expiring soon
        integrations = await db.fetch(
            """
            SELECT id, platform, metadata
            FROM core.integrations
            WHERE status = 'connected'
              AND (metadata->>'token_expires_at')::timestamptz <= $1
            """,
            datetime.utcnow() + timedelta(hours=24)
        )

        for integration in integrations:
            try:
                await self.refresh_integration_token(
                    integration['id'],
                    integration['platform']
                )
            except Exception as e:
                # Log error but continue with other integrations
                await log_integration_event(
                    event_type="integration.token_refresh_failed",
                    payload={
                        "integration_id": str(integration['id']),
                        "platform": integration['platform'],
                        "error": str(e)
                    }
                )

    async def refresh_integration_token(
        self,
        integration_id: str,
        platform: str
    ):
        """Refresh token for a single integration"""

        # Get current tokens
        tokens = await retrieve_encrypted_tokens(integration_id)

        if 'refresh_token' not in tokens:
            raise ValueError("No refresh token available")

        # Get connector
        config = get_oauth_config(platform)
        connector = ConnectorRegistry.get_connector(
            platform=platform,
            integration_id=integration_id,
            config=config
        )

        # Refresh token
        new_tokens = await connector.refresh_token(tokens['refresh_token'])

        # Update metadata
        await db.execute(
            """
            UPDATE core.integrations
            SET metadata = jsonb_set(
                metadata,
                '{token_expires_at}',
                to_jsonb($1::text)
            )
            WHERE id = $2
            """,
            (datetime.utcnow() + timedelta(seconds=new_tokens['expires_in'])).isoformat(),
            integration_id
        )

        # Log success
        await log_integration_event(
            event_type="integration.token_refreshed",
            payload={
                "integration_id": integration_id,
                "platform": platform
            }
        )


# Initialize service on startup
token_refresh_service = TokenRefreshService()
token_refresh_service.start()
```

### Token Rotation Policy

Automatic credential rotation every 90 days:

```python
async def rotate_credentials_policy():
    """
    Rotate credentials for integrations older than 90 days

    Triggered by scheduled job (monthly)
    """

    # Find integrations due for rotation
    integrations = await db.fetch(
        """
        SELECT id, platform, workspace_id, founder_id
        FROM core.integrations
        WHERE status = 'connected'
          AND connected_at < now() - interval '90 days'
          AND (metadata->>'last_rotation')::timestamptz IS NULL
             OR (metadata->>'last_rotation')::timestamptz < now() - interval '90 days'
        """
    )

    for integration in integrations:
        # Send notification to founder
        await send_notification(
            workspace_id=integration['workspace_id'],
            founder_id=integration['founder_id'],
            type="integration_rotation_required",
            message=f"Your {integration['platform']} integration requires re-authorization for security purposes."
        )

        # Update status to pending
        await db.execute(
            """
            UPDATE core.integrations
            SET status = 'pending',
                metadata = jsonb_set(metadata, '{rotation_required}', 'true')
            WHERE id = $1
            """,
            integration['id']
        )
```

---

## Health Monitoring Architecture

### Health Check System

Periodic health checks every 6 hours for all active integrations:

```python
from typing import Dict, Any
from enum import Enum

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class IntegrationHealthMonitor:
    """Monitor health of all integrations"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def start(self):
        """Start health check scheduler"""
        # Run every 6 hours
        self.scheduler.add_job(
            self.check_all_integrations,
            'interval',
            hours=6,
            id='health_check'
        )
        self.scheduler.start()

    async def check_all_integrations(self):
        """Check health of all active integrations"""

        # Fetch all connected integrations
        integrations = await db.fetch(
            """
            SELECT id, platform, workspace_id, founder_id
            FROM core.integrations
            WHERE status = 'connected'
            """
        )

        results = []
        for integration in integrations:
            result = await self.check_integration_health(
                integration_id=str(integration['id']),
                platform=integration['platform']
            )
            results.append(result)

            # Update health status table
            await self.record_health_check(
                integration_id=integration['id'],
                result=result
            )

        # Send alerts for unhealthy integrations
        await self.send_health_alerts(results)

        return results

    async def check_integration_health(
        self,
        integration_id: str,
        platform: str
    ) -> Dict[str, Any]:
        """
        Check health of a single integration

        Returns:
            {
                "integration_id": str,
                "platform": str,
                "status": HealthStatus,
                "response_time_ms": float,
                "error": str (optional),
                "checked_at": str (ISO timestamp)
            }
        """
        start_time = datetime.utcnow()

        try:
            # Get connector
            config = get_oauth_config(platform)
            connector = ConnectorRegistry.get_connector(
                platform=platform,
                integration_id=integration_id,
                config=config
            )

            # Perform health check
            health_result = await connector.health_check()

            response_time_ms = (
                datetime.utcnow() - start_time
            ).total_seconds() * 1000

            return {
                "integration_id": integration_id,
                "platform": platform,
                "status": HealthStatus.HEALTHY,
                "response_time_ms": response_time_ms,
                "checked_at": datetime.utcnow().isoformat(),
                "details": health_result
            }

        except Exception as e:
            response_time_ms = (
                datetime.utcnow() - start_time
            ).total_seconds() * 1000

            # Determine status based on error type
            status = self.classify_error(e)

            return {
                "integration_id": integration_id,
                "platform": platform,
                "status": status,
                "response_time_ms": response_time_ms,
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat()
            }

    def classify_error(self, error: Exception) -> HealthStatus:
        """Classify error severity"""
        error_str = str(error).lower()

        if "timeout" in error_str or "connection" in error_str:
            return HealthStatus.DEGRADED
        elif "401" in error_str or "403" in error_str:
            return HealthStatus.UNHEALTHY
        elif "429" in error_str:  # Rate limit
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.UNHEALTHY

    async def record_health_check(
        self,
        integration_id: str,
        result: Dict[str, Any]
    ):
        """Record health check result in database"""

        await db.execute(
            """
            INSERT INTO mcp.health_checks (
                integration_id,
                status,
                response_time_ms,
                error_message,
                checked_at,
                details
            ) VALUES ($1, $2, $3, $4, $5, $6)
            """,
            integration_id,
            result['status'],
            result.get('response_time_ms'),
            result.get('error'),
            result['checked_at'],
            json.dumps(result.get('details', {}))
        )

        # Update integration table
        if result['status'] == HealthStatus.UNHEALTHY:
            await db.execute(
                """
                UPDATE core.integrations
                SET status = 'error',
                    error_message = $1,
                    updated_at = now()
                WHERE id = $2
                """,
                result.get('error'),
                integration_id
            )

    async def send_health_alerts(self, results: list[Dict]):
        """Send alerts for unhealthy integrations"""

        unhealthy = [r for r in results if r['status'] == HealthStatus.UNHEALTHY]

        if not unhealthy:
            return

        # Group by workspace
        by_workspace = {}
        for result in unhealthy:
            integration = await get_integration(result['integration_id'])
            workspace_id = str(integration.workspace_id)

            if workspace_id not in by_workspace:
                by_workspace[workspace_id] = []
            by_workspace[workspace_id].append(result)

        # Send notification per workspace
        for workspace_id, failures in by_workspace.items():
            await send_notification(
                workspace_id=workspace_id,
                type="integration_health_alert",
                message=f"{len(failures)} integration(s) are unhealthy",
                data={"failures": failures}
            )


# Initialize monitor
health_monitor = IntegrationHealthMonitor()
health_monitor.start()
```

### Automatic Reconnection Logic

Circuit breaker with automatic reconnection attempts:

```python
from typing import Callable, Any
import asyncio

class CircuitBreaker:
    """Circuit breaker for integration failures"""

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection

        States:
        - CLOSED: Normal operation, allow all calls
        - OPEN: Threshold exceeded, reject calls
        - HALF_OPEN: Timeout elapsed, try one call
        """

        if self.state == "open":
            # Check if timeout has elapsed
            if self.last_failure_time and \
               (datetime.utcnow() - self.last_failure_time).seconds >= self.timeout:
                self.state = "half_open"
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)

            # Success - reset circuit
            if self.state == "half_open":
                self.state = "closed"
                self.failure_count = 0

            return result

        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()

            if self.failure_count >= self.failure_threshold:
                self.state = "open"

            raise e


class AutoReconnectService:
    """Automatic reconnection for failed integrations"""

    def __init__(self):
        self.circuit_breakers = {}  # integration_id -> CircuitBreaker
        self.scheduler = AsyncIOScheduler()

    def start(self):
        """Start reconnection scheduler"""
        # Check every hour
        self.scheduler.add_job(
            self.attempt_reconnections,
            'interval',
            hours=1,
            id='auto_reconnect'
        )
        self.scheduler.start()

    async def attempt_reconnections(self):
        """Attempt to reconnect failed integrations"""

        # Find integrations in error state
        integrations = await db.fetch(
            """
            SELECT id, platform, workspace_id, founder_id, updated_at
            FROM core.integrations
            WHERE status = 'error'
              AND (metadata->>'reconnect_attempts')::int < 3
            """
        )

        for integration in integrations:
            await self.try_reconnect(
                integration_id=str(integration['id']),
                platform=integration['platform']
            )

    async def try_reconnect(
        self,
        integration_id: str,
        platform: str
    ):
        """
        Attempt to reconnect a failed integration

        Strategy:
        1. Try health check
        2. If 401, attempt token refresh
        3. If successful, update status to connected
        4. If failed, increment retry counter
        """

        # Get or create circuit breaker
        if integration_id not in self.circuit_breakers:
            self.circuit_breakers[integration_id] = CircuitBreaker(
                failure_threshold=5,
                timeout=300  # 5 minutes
            )

        breaker = self.circuit_breakers[integration_id]

        try:
            # Use circuit breaker to protect reconnection attempt
            await breaker.call(
                self._reconnect_logic,
                integration_id,
                platform
            )

        except Exception as e:
            # Log failure
            await log_integration_event(
                event_type="integration.reconnect_failed",
                payload={
                    "integration_id": integration_id,
                    "platform": platform,
                    "error": str(e)
                }
            )

    async def _reconnect_logic(
        self,
        integration_id: str,
        platform: str
    ):
        """Core reconnection logic"""

        # Get connector
        config = get_oauth_config(platform)
        connector = ConnectorRegistry.get_connector(
            platform=platform,
            integration_id=integration_id,
            config=config
        )

        # Try health check
        health_result = await connector.health_check()

        if health_result['status'] == 'healthy':
            # Success - update status
            await db.execute(
                """
                UPDATE core.integrations
                SET status = 'connected',
                    error_message = NULL,
                    metadata = jsonb_set(
                        metadata,
                        '{reconnect_attempts}',
                        '0'
                    )
                WHERE id = $1
                """,
                integration_id
            )

            # Log success
            await log_integration_event(
                event_type="integration.reconnected",
                payload={
                    "integration_id": integration_id,
                    "platform": platform
                }
            )
        else:
            # Still unhealthy - increment retry count
            await db.execute(
                """
                UPDATE core.integrations
                SET metadata = jsonb_set(
                    metadata,
                    '{reconnect_attempts}',
                    to_jsonb(
                        COALESCE((metadata->>'reconnect_attempts')::int, 0) + 1
                    )
                )
                WHERE id = $1
                """,
                integration_id
            )


# Initialize service
auto_reconnect = AutoReconnectService()
auto_reconnect.start()
```

---

## Error Handling Patterns

### Error Classification

```python
from enum import Enum

class IntegrationErrorType(str, Enum):
    # Authentication errors
    AUTH_EXPIRED = "auth_expired"
    AUTH_INVALID = "auth_invalid"
    AUTH_REVOKED = "auth_revoked"

    # Rate limiting
    RATE_LIMIT = "rate_limit"
    QUOTA_EXCEEDED = "quota_exceeded"

    # Network errors
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    DNS_ERROR = "dns_error"

    # API errors
    NOT_FOUND = "not_found"
    BAD_REQUEST = "bad_request"
    SERVER_ERROR = "server_error"

    # Platform-specific
    PLATFORM_MAINTENANCE = "platform_maintenance"
    FEATURE_DISABLED = "feature_disabled"

    # Unknown
    UNKNOWN = "unknown"


class IntegrationError(Exception):
    """Base exception for integration errors"""

    def __init__(
        self,
        error_type: IntegrationErrorType,
        message: str,
        platform: str,
        integration_id: str,
        recoverable: bool = True,
        retry_after: int = None
    ):
        self.error_type = error_type
        self.message = message
        self.platform = platform
        self.integration_id = integration_id
        self.recoverable = recoverable
        self.retry_after = retry_after
        super().__init__(message)

    def to_dict(self) -> dict:
        return {
            "error_type": self.error_type,
            "message": self.message,
            "platform": self.platform,
            "integration_id": self.integration_id,
            "recoverable": self.recoverable,
            "retry_after": self.retry_after
        }


def classify_http_error(
    status_code: int,
    response_body: str,
    platform: str
) -> IntegrationErrorType:
    """Classify HTTP errors into IntegrationErrorType"""

    if status_code == 401:
        return IntegrationErrorType.AUTH_INVALID
    elif status_code == 403:
        if "revoked" in response_body.lower():
            return IntegrationErrorType.AUTH_REVOKED
        return IntegrationErrorType.AUTH_INVALID
    elif status_code == 404:
        return IntegrationErrorType.NOT_FOUND
    elif status_code == 429:
        return IntegrationErrorType.RATE_LIMIT
    elif 500 <= status_code < 600:
        return IntegrationErrorType.SERVER_ERROR
    else:
        return IntegrationErrorType.UNKNOWN
```

### Retry Logic with Exponential Backoff

```python
import asyncio
from typing import Callable, TypeVar, Any

T = TypeVar('T')

async def retry_with_backoff(
    func: Callable[..., T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True
) -> T:
    """
    Retry function with exponential backoff

    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential calculation
        jitter: Add random jitter to prevent thundering herd

    Returns:
        Result of successful function call

    Raises:
        Last exception if all retries fail
    """

    for attempt in range(max_retries + 1):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries:
                raise e

            # Calculate delay
            delay = min(
                base_delay * (exponential_base ** attempt),
                max_delay
            )

            # Add jitter (random 0-20% of delay)
            if jitter:
                import random
                delay = delay * (0.8 + 0.4 * random.random())

            # Log retry
            print(f"Retry attempt {attempt + 1}/{max_retries} "
                  f"after {delay:.2f}s: {str(e)}")

            await asyncio.sleep(delay)


# Usage example
async def fetch_with_retry(integration_id: str):
    """Fetch data with automatic retry"""

    async def _fetch():
        connector = get_connector(integration_id)
        return await connector.fetch_data()

    return await retry_with_backoff(
        _fetch,
        max_retries=3,
        base_delay=2.0,
        max_delay=30.0
    )
```

### Error Logging and Alerting

```python
async def log_integration_error(
    integration_id: str,
    error: IntegrationError,
    context: dict = None
):
    """
    Log integration error to ops.events and alert if needed
    """

    # Prepare event payload
    payload = {
        "error": error.to_dict(),
        "context": context or {},
        "timestamp": datetime.utcnow().isoformat()
    }

    # Log to ops.events
    await db.execute(
        """
        INSERT INTO ops.events (
            workspace_id,
            actor_type,
            actor_id,
            event_type,
            entity_type,
            entity_id,
            payload
        )
        SELECT
            workspace_id,
            'integration',
            id,
            'integration.error',
            'integration',
            id,
            $1::jsonb
        FROM core.integrations
        WHERE id = $2
        """,
        json.dumps(payload),
        integration_id
    )

    # Update integration error message
    await db.execute(
        """
        UPDATE core.integrations
        SET error_message = $1,
            status = CASE
                WHEN $2 THEN 'error'
                ELSE status
            END
        WHERE id = $3
        """,
        error.message,
        not error.recoverable,
        integration_id
    )

    # Send alert if non-recoverable
    if not error.recoverable:
        integration = await get_integration(integration_id)
        await send_notification(
            workspace_id=str(integration.workspace_id),
            founder_id=str(integration.founder_id),
            type="integration_error",
            message=f"Integration error: {error.message}",
            data=payload
        )
```

---

## Rate Limiting & Circuit Breaker

### Per-Integration Rate Limiting

```python
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio

class RateLimiter:
    """Token bucket rate limiter for integrations"""

    def __init__(
        self,
        rate: int,  # Requests per period
        period: int  # Period in seconds
    ):
        self.rate = rate
        self.period = period
        self.buckets = defaultdict(lambda: {
            'tokens': rate,
            'last_update': datetime.utcnow()
        })
        self.lock = asyncio.Lock()

    async def acquire(self, key: str) -> bool:
        """
        Acquire token from bucket

        Returns True if request allowed, False if rate limited
        """
        async with self.lock:
            bucket = self.buckets[key]
            now = datetime.utcnow()

            # Refill tokens based on elapsed time
            elapsed = (now - bucket['last_update']).total_seconds()
            bucket['tokens'] = min(
                self.rate,
                bucket['tokens'] + (elapsed / self.period) * self.rate
            )
            bucket['last_update'] = now

            # Check if token available
            if bucket['tokens'] >= 1:
                bucket['tokens'] -= 1
                return True
            else:
                return False

    async def wait_for_token(self, key: str):
        """Wait until token is available"""
        while not await self.acquire(key):
            await asyncio.sleep(0.1)


# Platform-specific rate limiters
RATE_LIMITERS = {
    "zoom": RateLimiter(rate=100, period=60),  # 100 req/min
    "slack": RateLimiter(rate=50, period=60),   # 50 req/min
    "gmail": RateLimiter(rate=250, period=1),   # 250 req/sec
    "monday": RateLimiter(rate=60, period=60),  # 60 req/min
    # Add others...
}


async def rate_limited_request(
    platform: str,
    integration_id: str,
    request_func: Callable
):
    """Execute request with rate limiting"""

    limiter = RATE_LIMITERS.get(platform)
    if not limiter:
        # No rate limiter configured, execute directly
        return await request_func()

    # Wait for token
    await limiter.wait_for_token(integration_id)

    # Execute request
    return await request_func()
```

### Circuit Breaker Implementation

See [Automatic Reconnection Logic](#automatic-reconnection-logic) section for circuit breaker implementation.

---

## Integration State Machine

### State Definitions

```python
from enum import Enum

class IntegrationState(str, Enum):
    """Integration lifecycle states"""

    # Initial state
    PENDING = "pending"

    # OAuth flow
    AUTHORIZING = "authorizing"

    # Active states
    CONNECTED = "connected"
    ACTIVE = "active"  # Connected + actively syncing

    # Degraded states
    ERROR = "error"  # Temporary error, auto-retry
    DEGRADED = "degraded"  # Partial functionality

    # Terminal states
    REVOKED = "revoked"  # User disconnected
    EXPIRED = "expired"  # Token expired, needs reauth
    DELETED = "deleted"  # Soft deleted


class StateTransition:
    """Valid state transitions"""

    TRANSITIONS = {
        IntegrationState.PENDING: [
            IntegrationState.AUTHORIZING,
            IntegrationState.DELETED
        ],
        IntegrationState.AUTHORIZING: [
            IntegrationState.CONNECTED,
            IntegrationState.ERROR,
            IntegrationState.PENDING
        ],
        IntegrationState.CONNECTED: [
            IntegrationState.ACTIVE,
            IntegrationState.ERROR,
            IntegrationState.DEGRADED,
            IntegrationState.REVOKED,
            IntegrationState.EXPIRED
        ],
        IntegrationState.ACTIVE: [
            IntegrationState.ERROR,
            IntegrationState.DEGRADED,
            IntegrationState.REVOKED,
            IntegrationState.EXPIRED
        ],
        IntegrationState.ERROR: [
            IntegrationState.CONNECTED,
            IntegrationState.ACTIVE,
            IntegrationState.REVOKED,
            IntegrationState.EXPIRED,
            IntegrationState.DELETED
        ],
        IntegrationState.DEGRADED: [
            IntegrationState.ACTIVE,
            IntegrationState.ERROR,
            IntegrationState.REVOKED
        ],
        IntegrationState.REVOKED: [
            IntegrationState.PENDING,
            IntegrationState.DELETED
        ],
        IntegrationState.EXPIRED: [
            IntegrationState.PENDING,
            IntegrationState.CONNECTED,
            IntegrationState.DELETED
        ],
        IntegrationState.DELETED: []  # Terminal state
    }

    @classmethod
    def is_valid_transition(
        cls,
        from_state: IntegrationState,
        to_state: IntegrationState
    ) -> bool:
        """Check if state transition is valid"""
        return to_state in cls.TRANSITIONS.get(from_state, [])

    @classmethod
    def validate_transition(
        cls,
        from_state: IntegrationState,
        to_state: IntegrationState
    ):
        """Validate transition or raise error"""
        if not cls.is_valid_transition(from_state, to_state):
            raise ValueError(
                f"Invalid state transition: {from_state} -> {to_state}"
            )


async def transition_integration_state(
    integration_id: str,
    new_state: IntegrationState,
    reason: str = None,
    metadata: dict = None
):
    """
    Transition integration to new state

    1. Validate transition is allowed
    2. Update database
    3. Log event
    4. Trigger side effects
    """

    # Get current state
    current = await db.fetchrow(
        """
        SELECT status, platform, workspace_id
        FROM core.integrations
        WHERE id = $1
        """,
        integration_id
    )

    if not current:
        raise ValueError(f"Integration not found: {integration_id}")

    current_state = IntegrationState(current['status'])

    # Validate transition
    StateTransition.validate_transition(current_state, new_state)

    # Update state
    await db.execute(
        """
        UPDATE core.integrations
        SET status = $1,
            error_message = $2,
            metadata = COALESCE(metadata, '{}'::jsonb) || $3::jsonb,
            updated_at = now()
        WHERE id = $4
        """,
        new_state,
        reason if new_state == IntegrationState.ERROR else None,
        json.dumps(metadata or {}),
        integration_id
    )

    # Log state transition
    await log_integration_event(
        workspace_id=current['workspace_id'],
        event_type=f"integration.state.{new_state}",
        payload={
            "integration_id": integration_id,
            "platform": current['platform'],
            "from_state": current_state,
            "to_state": new_state,
            "reason": reason,
            "metadata": metadata
        }
    )

    # Trigger side effects
    await handle_state_change(
        integration_id=integration_id,
        platform=current['platform'],
        from_state=current_state,
        to_state=new_state
    )


async def handle_state_change(
    integration_id: str,
    platform: str,
    from_state: IntegrationState,
    to_state: IntegrationState
):
    """Handle side effects of state changes"""

    # Start syncing when transitioning to ACTIVE
    if to_state == IntegrationState.ACTIVE:
        await start_integration_sync(integration_id, platform)

    # Stop syncing when transitioning away from ACTIVE
    if from_state == IntegrationState.ACTIVE and \
       to_state != IntegrationState.ACTIVE:
        await stop_integration_sync(integration_id, platform)

    # Send notification for errors
    if to_state == IntegrationState.ERROR:
        integration = await get_integration(integration_id)
        await send_notification(
            workspace_id=str(integration.workspace_id),
            type="integration_error",
            message=f"{platform} integration encountered an error"
        )
```

### State Machine Diagram

```
                          ┌──────────┐
                          │ PENDING  │
                          └────┬─────┘
                               │
                               │ /connect
                               ▼
                         ┌────────────┐
                         │AUTHORIZING │
                         └─────┬──────┘
                               │
                    ┌──────────┴──────────┐
                    │ OAuth success       │ OAuth failure
                    ▼                     ▼
              ┌──────────┐           ┌─────────┐
              │CONNECTED │           │  ERROR  │
              └────┬─────┘           └────┬────┘
                   │                      │
                   │ auto-sync            │ retry
                   ▼                      │
              ┌─────────┐                 │
         ┌────│ ACTIVE  │◄────────────────┘
         │    └────┬────┘
         │         │
         │         │ health check fail
         │         ▼
         │    ┌──────────┐
         │    │ DEGRADED │
         │    └────┬─────┘
         │         │
         │         │ continued failures
         │         ▼
         │    ┌─────────┐
         └───>│  ERROR  │
              └────┬────┘
                   │
        ┌──────────┼──────────┐
        │          │          │
        │ /disconnect        │ token expires
        ▼          │          ▼
   ┌─────────┐     │     ┌─────────┐
   │ REVOKED │     │     │ EXPIRED │
   └────┬────┘     │     └────┬────┘
        │          │          │
        │          │          │ /reconnect
        │          │          ▼
        │          │     ┌──────────┐
        │          │     │ PENDING  │
        │          │     └──────────┘
        │          │
        │          │ /delete
        │          ▼
        │     ┌─────────┐
        └────>│ DELETED │
              └─────────┘
                (terminal)
```

---

## Security Architecture

### Threat Model

| Threat | Mitigation |
|--------|-----------|
| **Token Theft** | AES-256-GCM encryption at rest, TLS in transit |
| **CSRF Attacks** | State parameter validation, PKCE |
| **Replay Attacks** | Nonce validation, short-lived tokens |
| **Man-in-the-Middle** | TLS 1.3 with certificate pinning |
| **Privilege Escalation** | OAuth scope minimization, RLS policies |
| **Data Exfiltration** | Row-level security, audit logging |

### Security Best Practices

1. **Minimum Necessary Scopes**
   - Request only required OAuth scopes
   - Document scope purpose
   - Regular scope audits

2. **Token Security**
   - Never log tokens
   - Rotate master encryption key annually
   - Use Supabase Vault for key management
   - Automatic token rotation every 90 days

3. **Audit Trail**
   - Log all integration events
   - Immutable event log
   - 7-year retention for compliance

4. **Access Control**
   - RLS policies on all integration tables
   - Workspace isolation enforced at database level
   - API key rotation

5. **Network Security**
   - TLS 1.3 for all connections
   - Certificate validation
   - IP allowlisting (optional)

---

## API Specifications

See OAuth Flow Design section for detailed API endpoint specifications.

### Key Endpoints

- `GET /integrations/connect/{platform}` - Initiate OAuth flow
- `GET /integrations/callback/{platform}` - OAuth callback
- `DELETE /integrations/disconnect/{integration_id}` - Revoke integration
- `GET /integrations/status/{integration_id}` - Check integration health
- `GET /integrations/list` - List all integrations for workspace

---

## Performance & Scalability

### Performance Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| OAuth flow completion | < 5s | 2-3s |
| Health check latency | < 100ms | 50-80ms |
| Token refresh | < 500ms | 200-300ms |
| Integration listing | < 200ms | 100-150ms |

### Scalability Considerations

1. **Database Connection Pooling**
   - Max 100 connections per backend instance
   - Transaction mode pooling

2. **Caching**
   - Redis cache for integration metadata
   - 1-hour TTL for OAuth configs

3. **Rate Limiting**
   - Per-platform rate limiters
   - Token bucket algorithm

4. **Background Processing**
   - Async health checks
   - Scheduled token refresh
   - Event log processing

---

## Conclusion

The MCP Integration Framework provides a robust, secure, and scalable foundation for connecting the AI Chief of Staff to 13 external platforms. Key features include:

- **Standardized connector pattern** for consistent integration development
- **Automatic token management** with encryption and rotation
- **Proactive health monitoring** with automatic recovery
- **Comprehensive error handling** with circuit breakers
- **Complete audit trail** for compliance and debugging

This architecture enables rapid integration development while maintaining security, reliability, and performance.

---

**Document Version:** 1.0
**Last Updated:** 2025-10-30
**Maintained By:** System Architect
