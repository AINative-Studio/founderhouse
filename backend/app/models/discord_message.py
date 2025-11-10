"""
Discord Message Models
Pydantic models for Discord integration and notifications
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class DiscordMessageType(str, Enum):
    """Type of Discord message"""
    STATUS_UPDATE = "status_update"
    BRIEFING = "briefing"
    ALERT = "alert"
    NOTIFICATION = "notification"
    ANNOUNCEMENT = "announcement"


class DiscordMessageStatus(str, Enum):
    """Message delivery status"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SCHEDULED = "scheduled"


class DiscordChannelType(str, Enum):
    """Discord channel types"""
    TEXT = "text"
    DM = "dm"
    THREAD = "thread"


class DiscordStatusUpdateRequest(BaseModel):
    """Request to post a status update to Discord"""
    workspace_id: UUID
    founder_id: UUID
    channel_id: Optional[str] = Field(None, description="Discord channel ID")
    channel_name: Optional[str] = Field(None, description="Discord channel name")
    message: str
    embed: Optional[Dict[str, Any]] = Field(None, description="Discord embed object")
    mentions: List[str] = Field(default_factory=list, description="User IDs to mention")
    thread_name: Optional[str] = Field(None, description="Create a thread with this name")

    model_config = ConfigDict(from_attributes=True)


class DiscordBriefingRequest(BaseModel):
    """Request to send a briefing to Discord"""
    workspace_id: UUID
    founder_id: UUID
    briefing_id: Optional[UUID] = None
    channel_id: Optional[str] = None
    channel_name: Optional[str] = Field(default="daily-briefings")
    include_metrics: bool = Field(default=True)
    include_action_items: bool = Field(default=True)
    mention_team: bool = Field(default=False)

    model_config = ConfigDict(from_attributes=True)


class DiscordMessageResponse(BaseModel):
    """Discord message record"""
    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    founder_id: UUID
    message_type: DiscordMessageType
    channel_id: str
    channel_name: Optional[str] = None
    message_content: str
    discord_message_id: Optional[str] = None
    status: DiscordMessageStatus
    embed_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class DiscordMessageCreate(BaseModel):
    """Create Discord message record"""
    workspace_id: UUID
    founder_id: UUID
    message_type: DiscordMessageType
    channel_id: str
    channel_name: Optional[str] = None
    message_content: str
    status: DiscordMessageStatus = DiscordMessageStatus.PENDING
    embed_data: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class DiscordMessageUpdate(BaseModel):
    """Update Discord message record"""
    status: Optional[DiscordMessageStatus] = None
    discord_message_id: Optional[str] = None
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DiscordEmbed(BaseModel):
    """Discord embed structure"""
    title: Optional[str] = None
    description: Optional[str] = None
    color: Optional[int] = Field(None, description="Decimal color code")
    fields: List[Dict[str, Any]] = Field(default_factory=list)
    footer: Optional[Dict[str, str]] = None
    timestamp: Optional[datetime] = None
    thumbnail: Optional[Dict[str, str]] = None
    author: Optional[Dict[str, str]] = None

    model_config = ConfigDict(from_attributes=True)


class DiscordWebhookConfig(BaseModel):
    """Discord webhook configuration"""
    workspace_id: UUID
    channel_id: str
    webhook_url: str
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)
