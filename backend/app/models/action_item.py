"""
Action Item Data Models
Extracted from meeting transcripts
"""
from datetime import datetime
from typing import Optional, List
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ActionItemStatus(str, Enum):
    """Action item status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ActionItemPriority(str, Enum):
    """Action item priority levels"""
    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class ActionItemSource(str, Enum):
    """Source of action item extraction"""
    LLM = "llm"
    REGEX = "regex"
    MANUAL = "manual"
    HYBRID = "hybrid"  # Both LLM and regex


class ActionItem(BaseModel):
    """Action item extracted from meeting"""
    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    founder_id: UUID
    meeting_id: UUID

    # Content
    description: str
    context: Optional[str] = None  # Surrounding transcript context

    # Assignment
    assignee_name: Optional[str] = None
    assignee_email: Optional[str] = None
    mentioned_by: Optional[str] = None  # Who mentioned this action

    # Status and priority
    status: ActionItemStatus = ActionItemStatus.PENDING
    priority: ActionItemPriority = ActionItemPriority.NORMAL

    # Timing
    due_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Source tracking
    source: ActionItemSource = ActionItemSource.LLM
    confidence_score: float = 0.0  # 0.0 to 1.0
    transcript_chunk_index: Optional[int] = None
    timestamp_in_meeting: Optional[float] = None  # seconds from start

    # Task integration
    task_id: Optional[UUID] = None  # Link to Monday/Notion task
    task_platform: Optional[str] = None  # monday, notion
    task_url: Optional[str] = None

    # Tags
    tags: List[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "meeting_id": "123e4567-e89b-12d3-a456-426614174000",
                "description": "Follow up with marketing team on Q4 campaign",
                "assignee_name": "Jane Smith",
                "priority": "high",
                "confidence_score": 0.92
            }
        }


class ActionItemCreate(BaseModel):
    """Schema for creating an action item"""
    workspace_id: UUID
    founder_id: UUID
    meeting_id: UUID
    description: str
    assignee_name: Optional[str] = None
    assignee_email: Optional[str] = None
    priority: ActionItemPriority = ActionItemPriority.NORMAL
    due_date: Optional[datetime] = None
    context: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class ActionItemUpdate(BaseModel):
    """Schema for updating an action item"""
    description: Optional[str] = None
    assignee_name: Optional[str] = None
    assignee_email: Optional[str] = None
    status: Optional[ActionItemStatus] = None
    priority: Optional[ActionItemPriority] = None
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None


class ConvertToTaskRequest(BaseModel):
    """Request to convert action item to task"""
    action_item_id: UUID
    platform: str = "monday"  # monday, notion
    board_id: Optional[str] = None
    additional_metadata: Optional[dict] = None
