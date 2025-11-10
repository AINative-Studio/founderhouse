"""
Loom Video Models
Pydantic models for Loom video ingestion and summarization
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl, ConfigDict


class LoomVideoStatus(str, Enum):
    """Video processing status"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    SUMMARIZING = "summarizing"
    COMPLETED = "completed"
    FAILED = "failed"


class LoomVideoType(str, Enum):
    """Type of Loom video content"""
    PRODUCT_DEMO = "product_demo"
    TEAM_UPDATE = "team_update"
    TUTORIAL = "tutorial"
    STANDUP = "standup"
    PRESENTATION = "presentation"
    FEEDBACK = "feedback"
    OTHER = "other"


class LoomVideoIngestRequest(BaseModel):
    """Request to ingest a Loom video"""
    workspace_id: UUID
    founder_id: UUID
    video_url: HttpUrl
    video_id: Optional[str] = Field(None, description="Loom video ID")
    title: Optional[str] = None
    description: Optional[str] = None
    video_type: LoomVideoType = LoomVideoType.OTHER
    auto_summarize: bool = Field(default=True, description="Automatically generate summary")
    notify_on_complete: bool = Field(default=False, description="Send notification when processing completes")

    model_config = ConfigDict(from_attributes=True)


class LoomVideoSummary(BaseModel):
    """Video summary content"""
    executive_summary: str
    key_points: List[str]
    action_items: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    participants: List[str] = Field(default_factory=list)
    duration_minutes: Optional[int] = None
    transcript_length: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class LoomVideoResponse(BaseModel):
    """Loom video record"""
    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    founder_id: UUID
    video_id: str
    video_url: str
    title: Optional[str] = None
    description: Optional[str] = None
    video_type: LoomVideoType
    status: LoomVideoStatus
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    transcript: Optional[str] = None
    summary: Optional[LoomVideoSummary] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LoomVideoCreate(BaseModel):
    """Create Loom video record"""
    workspace_id: UUID
    founder_id: UUID
    video_id: str
    video_url: str
    title: Optional[str] = None
    description: Optional[str] = None
    video_type: LoomVideoType = LoomVideoType.OTHER
    status: LoomVideoStatus = LoomVideoStatus.PENDING

    model_config = ConfigDict(from_attributes=True)


class LoomVideoUpdate(BaseModel):
    """Update Loom video record"""
    status: Optional[LoomVideoStatus] = None
    transcript: Optional[str] = None
    summary: Optional[LoomVideoSummary] = None
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LoomSummarizeRequest(BaseModel):
    """Request to summarize a Loom video"""
    include_action_items: bool = Field(default=True)
    include_topics: bool = Field(default=True)
    max_summary_length: int = Field(default=500, ge=100, le=2000)

    model_config = ConfigDict(from_attributes=True)


class LoomVideoListResponse(BaseModel):
    """List of Loom videos with pagination"""
    videos: List[LoomVideoResponse]
    total_count: int
    has_more: bool
    filters_applied: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)
