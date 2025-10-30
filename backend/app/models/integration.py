"""
Integration Models
MCP and API integrations for external platforms
"""
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from enum import Enum
from pydantic import BaseModel, Field, validator


class Platform(str, Enum):
    """Supported integration platforms"""
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


class ConnectionType(str, Enum):
    """Type of integration connection"""
    MCP = "mcp"  # Model Context Protocol
    API = "api"  # Direct API integration


class IntegrationStatus(str, Enum):
    """Integration connection status"""
    CONNECTED = "connected"
    ERROR = "error"
    REVOKED = "revoked"
    PENDING = "pending"


class IntegrationBase(BaseModel):
    """Base integration model"""
    platform: Platform = Field(..., description="Integration platform")
    connection_type: ConnectionType = Field(default=ConnectionType.MCP, description="Connection type")


class IntegrationCreate(IntegrationBase):
    """Model for creating a new integration"""
    workspace_id: UUID = Field(..., description="Workspace ID")
    founder_id: Optional[UUID] = Field(None, description="Founder ID (optional for workspace-level integrations)")
    credentials: Dict[str, Any] = Field(..., description="Integration credentials (will be encrypted)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @validator("credentials")
    def validate_credentials(cls, v, values):
        """Validate credentials based on platform"""
        if not v:
            raise ValueError("Credentials cannot be empty")

        platform = values.get("platform")
        required_fields = {
            Platform.ZOOM: ["client_id", "client_secret"],
            Platform.SLACK: ["access_token", "team_id"],
            Platform.DISCORD: ["bot_token"],
            Platform.MONDAY: ["api_token"],
            Platform.NOTION: ["access_token"],
        }

        if platform in required_fields:
            missing = [field for field in required_fields[platform] if field not in v]
            if missing:
                raise ValueError(f"Missing required credential fields for {platform}: {missing}")

        return v


class IntegrationUpdate(BaseModel):
    """Model for updating integration"""
    status: Optional[IntegrationStatus] = None
    credentials: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class IntegrationResponse(IntegrationBase):
    """Response model for integration data"""
    id: UUID = Field(..., description="Unique integration identifier")
    workspace_id: UUID
    founder_id: Optional[UUID] = None
    status: IntegrationStatus = Field(..., description="Current integration status")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    connected_at: Optional[datetime] = Field(None, description="Timestamp when integration was connected")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Don't expose credentials in response
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "850e8400-e29b-41d4-a716-446655440003",
                "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
                "founder_id": "650e8400-e29b-41d4-a716-446655440001",
                "platform": "zoom",
                "connection_type": "mcp",
                "status": "connected",
                "metadata": {
                    "account_id": "abc123",
                    "display_name": "Zoom Integration"
                },
                "connected_at": "2025-10-30T10:15:00Z",
                "updated_at": "2025-10-30T10:15:00Z"
            }
        }


class IntegrationHealthCheck(BaseModel):
    """Health check response for an integration"""
    integration_id: UUID
    platform: Platform
    status: IntegrationStatus
    is_healthy: bool = Field(..., description="Whether the integration is functioning properly")
    last_checked: datetime = Field(..., description="Timestamp of last health check")
    error_message: Optional[str] = Field(None, description="Error message if unhealthy")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional health check data")

    class Config:
        json_schema_extra = {
            "example": {
                "integration_id": "850e8400-e29b-41d4-a716-446655440003",
                "platform": "zoom",
                "status": "connected",
                "is_healthy": True,
                "last_checked": "2025-10-30T12:00:00Z",
                "error_message": None,
                "metadata": {
                    "api_version": "v2",
                    "rate_limit_remaining": 4500
                }
            }
        }


class IntegrationConnectRequest(BaseModel):
    """Request model for connecting a new integration"""
    platform: Platform
    connection_type: ConnectionType = ConnectionType.MCP
    credentials: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "platform": "zoom",
                "connection_type": "mcp",
                "credentials": {
                    "client_id": "your_zoom_client_id",
                    "client_secret": "your_zoom_client_secret",
                    "redirect_uri": "https://yourapp.com/callback"
                },
                "metadata": {
                    "display_name": "My Zoom Account"
                }
            }
        }


class IntegrationStatusResponse(BaseModel):
    """Response model for integration status endpoint"""
    workspace_id: UUID
    total_integrations: int
    connected: int
    error: int
    pending: int
    integrations: list[IntegrationHealthCheck]

    class Config:
        json_schema_extra = {
            "example": {
                "workspace_id": "550e8400-e29b-41d4-a716-446655440000",
                "total_integrations": 8,
                "connected": 7,
                "error": 1,
                "pending": 0,
                "integrations": [
                    {
                        "integration_id": "850e8400-e29b-41d4-a716-446655440003",
                        "platform": "zoom",
                        "status": "connected",
                        "is_healthy": True,
                        "last_checked": "2025-10-30T12:00:00Z",
                        "error_message": None,
                        "metadata": {}
                    }
                ]
            }
        }
