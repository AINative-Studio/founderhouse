"""
Feedback Models
Pydantic models for user feedback and improvement loops
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class FeedbackType(str, Enum):
    """Type of feedback"""
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    IMPROVEMENT = "improvement"
    PRAISE = "praise"
    COMPLAINT = "complaint"
    SUGGESTION = "suggestion"
    QUESTION = "question"


class FeedbackCategory(str, Enum):
    """Feedback category"""
    BRIEFINGS = "briefings"
    MEETINGS = "meetings"
    KPI_TRACKING = "kpi_tracking"
    RECOMMENDATIONS = "recommendations"
    VOICE_COMMANDS = "voice_commands"
    INTEGRATIONS = "integrations"
    UI_UX = "ui_ux"
    PERFORMANCE = "performance"
    OTHER = "other"


class FeedbackStatus(str, Enum):
    """Feedback processing status"""
    NEW = "new"
    UNDER_REVIEW = "under_review"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class FeedbackSentiment(str, Enum):
    """Sentiment analysis result"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class FeedbackSubmitRequest(BaseModel):
    """Request to submit feedback"""
    workspace_id: UUID
    founder_id: UUID
    feedback_type: FeedbackType
    category: FeedbackCategory
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context (page URL, feature used, etc.)")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating 1-5 if applicable")
    attachments: List[str] = Field(default_factory=list, description="URLs to screenshots or files")
    contact_for_followup: bool = Field(default=True)

    model_config = ConfigDict(from_attributes=True)


class FeedbackResponse(BaseModel):
    """Feedback record"""
    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    founder_id: UUID
    feedback_type: FeedbackType
    category: FeedbackCategory
    title: str
    description: str
    status: FeedbackStatus
    sentiment: Optional[FeedbackSentiment] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    rating: Optional[int] = None
    attachments: List[str] = Field(default_factory=list)
    contact_for_followup: bool = True
    admin_notes: Optional[str] = None
    priority_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="AI-generated priority score")
    related_tasks: List[UUID] = Field(default_factory=list, description="Related agent tasks created from this feedback")
    upvotes: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FeedbackCreate(BaseModel):
    """Create feedback record"""
    workspace_id: UUID
    founder_id: UUID
    feedback_type: FeedbackType
    category: FeedbackCategory
    title: str
    description: str
    status: FeedbackStatus = FeedbackStatus.NEW
    sentiment: Optional[FeedbackSentiment] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    rating: Optional[int] = None
    attachments: List[str] = Field(default_factory=list)
    contact_for_followup: bool = True

    model_config = ConfigDict(from_attributes=True)


class FeedbackUpdate(BaseModel):
    """Update feedback record"""
    status: Optional[FeedbackStatus] = None
    sentiment: Optional[FeedbackSentiment] = None
    admin_notes: Optional[str] = None
    priority_score: Optional[float] = None
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FeedbackListResponse(BaseModel):
    """List of feedback with pagination"""
    feedback_items: List[FeedbackResponse]
    total_count: int
    has_more: bool
    filters_applied: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class FeedbackAnalytics(BaseModel):
    """Aggregated feedback analytics"""
    total_feedback: int
    by_type: Dict[str, int]
    by_category: Dict[str, int]
    by_status: Dict[str, int]
    by_sentiment: Dict[str, int]
    average_rating: Optional[float] = None
    trending_topics: List[str] = Field(default_factory=list)
    top_requested_features: List[Dict[str, Any]] = Field(default_factory=list)
    resolution_time_avg_hours: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)
