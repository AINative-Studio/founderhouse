"""
Meeting Summary Data Models
AI-generated summaries and insights
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class SummarizationMethod(str, Enum):
    """Method used for summarization"""
    EXTRACTIVE = "extractive"
    ABSTRACTIVE = "abstractive"
    HYBRID = "hybrid"
    MULTI_STAGE = "multi_stage"


class SentimentScore(str, Enum):
    """Overall meeting sentiment"""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


class MeetingSummary(BaseModel):
    """AI-generated meeting summary"""
    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    founder_id: UUID
    meeting_id: UUID

    # Summary content
    executive_summary: str  # 2-3 sentence overview
    detailed_summary: Optional[str] = None  # Full summary
    key_points: List[str] = Field(default_factory=list)
    topics_discussed: List[str] = Field(default_factory=list)

    # Sentiment analysis
    overall_sentiment: Optional[SentimentScore] = None
    sentiment_details: Dict[str, Any] = Field(default_factory=dict)

    # Generated content
    action_items_count: int = 0
    decisions_count: int = 0
    follow_ups_count: int = 0

    # Metadata
    summarization_method: SummarizationMethod = SummarizationMethod.MULTI_STAGE
    llm_provider: Optional[str] = None  # openai, anthropic, deepseek, ollama
    llm_model: Optional[str] = None  # gpt-4, claude-3-5-sonnet, etc.

    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Quality metrics
    confidence_score: float = 0.0
    processing_time_ms: Optional[int] = None
    token_usage: Optional[int] = None
    cost_usd: Optional[float] = None

    # Error handling
    status: str = "completed"  # processing, completed, failed
    error_message: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "meeting_id": "123e4567-e89b-12d3-a456-426614174000",
                "executive_summary": "Team discussed Q4 product roadmap and agreed to prioritize enterprise features",
                "key_points": [
                    "Enterprise features prioritized for Q4",
                    "Marketing budget increased by 20%",
                    "Hiring freeze extended through January"
                ],
                "action_items_count": 7,
                "decisions_count": 3,
                "llm_provider": "anthropic",
                "llm_model": "claude-3-5-sonnet"
            }
        }


class FollowUp(BaseModel):
    """Follow-up item identified from meeting"""
    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    founder_id: UUID
    meeting_id: UUID

    description: str
    person: Optional[str] = None  # Who should follow up
    target: Optional[str] = None  # With whom
    context: Optional[str] = None

    due_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    completed: bool = False
    completed_at: Optional[datetime] = None

    confidence_score: float = 0.0


class SummaryGenerationRequest(BaseModel):
    """Request to generate meeting summary"""
    meeting_id: UUID
    force_regenerate: bool = False
    llm_provider: Optional[str] = None  # Override default provider
    include_sentiment: bool = True
    extract_action_items: bool = True
    extract_decisions: bool = True
    extract_follow_ups: bool = True


class SummaryGenerationResponse(BaseModel):
    """Response from summary generation"""
    summary_id: UUID
    meeting_id: UUID
    status: str
    message: str
    processing_time_ms: int
    cost_usd: Optional[float] = None
