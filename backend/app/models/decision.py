"""
Decision Data Models
Key decisions extracted from meetings
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DecisionType(str, Enum):
    """Type of decision made"""
    STRATEGIC = "strategic"
    TACTICAL = "tactical"
    OPERATIONAL = "operational"
    HIRING = "hiring"
    PRODUCT = "product"
    MARKETING = "marketing"
    FINANCIAL = "financial"
    OTHER = "other"


class DecisionStatus(str, Enum):
    """Decision implementation status"""
    PROPOSED = "proposed"
    AGREED = "agreed"
    IN_PROGRESS = "in_progress"
    IMPLEMENTED = "implemented"
    REVERSED = "reversed"


class DecisionImpact(str, Enum):
    """Expected impact level"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Decision(BaseModel):
    """Decision entity extracted from meetings"""
    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    founder_id: UUID
    meeting_id: UUID

    # Content
    title: str  # Short summary
    description: str  # Full context
    rationale: Optional[str] = None  # Why this decision was made

    # Classification
    decision_type: DecisionType = DecisionType.OTHER
    status: DecisionStatus = DecisionStatus.PROPOSED
    impact: DecisionImpact = DecisionImpact.MEDIUM

    # Context
    context: Optional[str] = None  # Surrounding transcript
    alternatives_considered: List[str] = Field(default_factory=list)

    # People involved
    decision_maker: Optional[str] = None
    stakeholders: List[str] = Field(default_factory=list)

    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    implementation_deadline: Optional[datetime] = None
    implemented_at: Optional[datetime] = None

    # Source tracking
    confidence_score: float = 0.0  # 0.0 to 1.0
    transcript_chunk_index: Optional[int] = None
    timestamp_in_meeting: Optional[float] = None  # seconds from start

    # Related items
    related_action_items: List[UUID] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

    # Follow-up
    follow_up_needed: bool = False
    follow_up_notes: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "meeting_id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Pivot to B2B sales model",
                "description": "After analyzing Q3 metrics, team agreed to focus on enterprise customers",
                "decision_type": "strategic",
                "impact": "critical",
                "decision_maker": "CEO",
                "confidence_score": 0.95
            }
        }


class DecisionCreate(BaseModel):
    """Schema for creating a decision"""
    workspace_id: UUID
    founder_id: UUID
    meeting_id: UUID
    title: str
    description: str
    decision_type: DecisionType = DecisionType.OTHER
    impact: DecisionImpact = DecisionImpact.MEDIUM
    decision_maker: Optional[str] = None
    stakeholders: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class DecisionUpdate(BaseModel):
    """Schema for updating a decision"""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[DecisionStatus] = None
    impact: Optional[DecisionImpact] = None
    implementation_deadline: Optional[datetime] = None
    follow_up_needed: Optional[bool] = None
    follow_up_notes: Optional[str] = None
