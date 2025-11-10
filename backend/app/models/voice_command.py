"""
Voice Command Models
Pydantic models for voice command processing via ZeroVoice MCP
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class VoiceCommandStatus(str, Enum):
    """Voice command processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VoiceCommandIntent(str, Enum):
    """Recognized voice command intents"""
    CREATE_TASK = "create_task"
    SCHEDULE_MEETING = "schedule_meeting"
    GET_SUMMARY = "get_summary"
    CHECK_METRICS = "check_metrics"
    SEND_MESSAGE = "send_message"
    CREATE_NOTE = "create_note"
    GET_BRIEFING = "get_briefing"
    UPDATE_STATUS = "update_status"
    UNKNOWN = "unknown"


class VoiceTranscriptionRequest(BaseModel):
    """Request to transcribe audio"""
    workspace_id: UUID
    founder_id: UUID
    audio_url: Optional[str] = None
    audio_base64: Optional[str] = None
    language: str = Field(default="en-US", description="Language code for transcription")
    include_timestamps: bool = Field(default=False, description="Include word-level timestamps")

    model_config = ConfigDict(from_attributes=True)


class VoiceTranscriptionResponse(BaseModel):
    """Transcription result"""
    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    founder_id: UUID
    transcript: str
    confidence: float = Field(ge=0.0, le=1.0)
    language: str
    duration_seconds: Optional[float] = None
    word_timestamps: Optional[List[Dict[str, Any]]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class VoiceCommandRequest(BaseModel):
    """Request to process a voice command"""
    workspace_id: UUID
    founder_id: UUID
    transcript: Optional[str] = None
    audio_url: Optional[str] = None
    audio_base64: Optional[str] = None
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context for command processing")

    model_config = ConfigDict(from_attributes=True)


class VoiceCommandResponse(BaseModel):
    """Voice command processing result"""
    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    founder_id: UUID
    transcript: str
    intent: VoiceCommandIntent
    confidence: float = Field(ge=0.0, le=1.0)
    status: VoiceCommandStatus
    extracted_entities: Dict[str, Any] = Field(default_factory=dict)
    action_taken: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class VoiceCommandCreate(BaseModel):
    """Create voice command record"""
    workspace_id: UUID
    founder_id: UUID
    transcript: str
    intent: VoiceCommandIntent
    confidence: float
    status: VoiceCommandStatus = VoiceCommandStatus.PENDING
    extracted_entities: Dict[str, Any] = Field(default_factory=dict)
    audio_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class VoiceCommandUpdate(BaseModel):
    """Update voice command record"""
    status: Optional[VoiceCommandStatus] = None
    action_taken: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class VoiceCommandListResponse(BaseModel):
    """List of voice commands with pagination"""
    commands: List[VoiceCommandResponse]
    total_count: int
    has_more: bool
    filters_applied: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)
