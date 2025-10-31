"""
Meeting Data Models
Handles meeting data, transcripts, and metadata
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MeetingSource(str, Enum):
    """Source platform for meeting data"""
    ZOOM = "zoom"
    FIREFLIES = "fireflies"
    OTTER = "otter"
    LOOM = "loom"
    MANUAL = "manual"


class MeetingStatus(str, Enum):
    """Meeting processing status"""
    PENDING = "pending"
    INGESTING = "ingesting"
    TRANSCRIBING = "transcribing"
    SUMMARIZING = "summarizing"
    COMPLETED = "completed"
    FAILED = "failed"


class TranscriptChunk(BaseModel):
    """Individual transcript chunk with speaker and timing"""
    text: str
    speaker_name: Optional[str] = None
    speaker_email: Optional[str] = None
    start_time: Optional[float] = None  # seconds
    end_time: Optional[float] = None  # seconds
    chunk_index: int = 0


class MeetingParticipant(BaseModel):
    """Meeting participant information"""
    name: str
    email: Optional[str] = None
    role: Optional[str] = None  # host, participant, guest
    join_time: Optional[datetime] = None
    leave_time: Optional[datetime] = None
    duration: Optional[int] = None  # seconds


class MeetingMetadata(BaseModel):
    """Additional meeting metadata"""
    duration: Optional[int] = None  # seconds
    recording_url: Optional[str] = None
    audio_url: Optional[str] = None
    video_url: Optional[str] = None
    transcript_url: Optional[str] = None
    platform_id: Optional[str] = None  # ID in source platform
    platform_data: Dict[str, Any] = Field(default_factory=dict)


class Meeting(BaseModel):
    """Meeting entity"""
    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    founder_id: UUID

    # Basic info
    title: str
    source: MeetingSource
    status: MeetingStatus = MeetingStatus.PENDING

    # Timing
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Participants
    host_name: Optional[str] = None
    host_email: Optional[str] = None
    participants: List[MeetingParticipant] = Field(default_factory=list)
    participant_count: int = 0

    # Content
    transcript: Optional[str] = None
    transcript_chunks: List[TranscriptChunk] = Field(default_factory=list)

    # Metadata
    metadata: MeetingMetadata = Field(default_factory=MeetingMetadata)

    # Vector embeddings
    embedding: Optional[List[float]] = None

    # Processing info
    ingestion_started_at: Optional[datetime] = None
    ingestion_completed_at: Optional[datetime] = None
    summarization_started_at: Optional[datetime] = None
    summarization_completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "workspace_id": "123e4567-e89b-12d3-a456-426614174000",
                "founder_id": "123e4567-e89b-12d3-a456-426614174001",
                "title": "Product Strategy Meeting",
                "source": "zoom",
                "status": "completed",
                "host_name": "John Doe",
                "host_email": "john@example.com",
                "participant_count": 5
            }
        }


class MeetingCreate(BaseModel):
    """Schema for creating a new meeting"""
    workspace_id: UUID
    founder_id: UUID
    title: str
    source: MeetingSource
    scheduled_at: Optional[datetime] = None
    host_name: Optional[str] = None
    host_email: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MeetingUpdate(BaseModel):
    """Schema for updating a meeting"""
    title: Optional[str] = None
    status: Optional[MeetingStatus] = None
    transcript: Optional[str] = None
    transcript_chunks: Optional[List[TranscriptChunk]] = None
    participants: Optional[List[MeetingParticipant]] = None
    metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class MeetingIngestRequest(BaseModel):
    """Request schema for manual meeting ingestion"""
    workspace_id: UUID
    founder_id: UUID
    source: MeetingSource
    platform_id: str  # ID in the source platform
    force_refresh: bool = False  # Re-ingest even if already exists


class MeetingIngestResponse(BaseModel):
    """Response schema for meeting ingestion"""
    meeting_id: UUID
    status: MeetingStatus
    message: str
    duplicate: bool = False
    ingestion_time_ms: Optional[int] = None
