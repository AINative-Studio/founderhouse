"""
Briefing Models
Represents daily briefings and summaries
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


class BriefingType(str, Enum):
    """Types of briefings"""
    MORNING = "morning"
    EVENING = "evening"
    WEEKLY = "weekly"
    INVESTOR = "investor"
    CUSTOM = "custom"


class BriefingStatus(str, Enum):
    """Briefing generation status"""
    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    DELIVERED = "delivered"
    FAILED = "failed"


class DeliveryChannel(str, Enum):
    """Briefing delivery channels"""
    EMAIL = "email"
    SLACK = "slack"
    DISCORD = "discord"
    IN_APP = "in_app"
    API = "api"


class BriefingSection(BaseModel):
    """Individual section within a briefing"""
    title: str = Field(..., max_length=255)
    content: str = Field(..., description="Section content")
    order: int = Field(..., description="Display order")
    section_type: str = Field(..., description="Section type (kpi, meetings, tasks, etc.)")
    data: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Structured data for the section"
    )
    importance: int = Field(default=1, ge=1, le=5, description="Section importance 1-5")


class BriefingBase(BaseModel):
    """Base briefing model"""
    briefing_type: BriefingType = Field(..., description="Type of briefing")
    title: str = Field(..., max_length=500, description="Briefing title")


class BriefingCreate(BriefingBase):
    """Model for creating a briefing"""
    workspace_id: UUID = Field(..., description="Workspace ID")
    founder_id: UUID = Field(..., description="Founder ID")
    start_date: datetime = Field(..., description="Start of reporting period")
    end_date: datetime = Field(..., description="End of reporting period")
    sections: List[BriefingSection] = Field(
        default_factory=list,
        description="Briefing sections"
    )
    summary: Optional[str] = Field(None, description="Executive summary")
    key_highlights: List[str] = Field(
        default_factory=list,
        description="Key highlights"
    )
    action_items: List[str] = Field(
        default_factory=list,
        description="Action items for the founder"
    )
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class BriefingUpdate(BaseModel):
    """Model for updating a briefing"""
    status: Optional[BriefingStatus] = None
    delivered_at: Optional[datetime] = None
    delivery_channels: Optional[List[DeliveryChannel]] = None
    metadata: Optional[Dict[str, Any]] = None


class BriefingResponse(BriefingBase):
    """Response model for briefing"""
    id: UUID = Field(..., description="Briefing ID")
    workspace_id: UUID = Field(..., description="Workspace ID")
    founder_id: UUID = Field(..., description="Founder ID")
    status: BriefingStatus = Field(..., description="Briefing status")
    start_date: datetime = Field(..., description="Start of reporting period")
    end_date: datetime = Field(..., description="End of reporting period")
    sections: List[BriefingSection] = Field(default_factory=list)
    summary: Optional[str] = None
    key_highlights: List[str] = Field(default_factory=list)
    action_items: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(..., description="Generation timestamp")
    delivered_at: Optional[datetime] = None
    delivery_channels: List[DeliveryChannel] = Field(default_factory=list)
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


class MorningBriefContent(BaseModel):
    """Structured content for morning brief"""
    greeting: str = Field(..., description="Personalized greeting")
    weather: Optional[Dict[str, Any]] = Field(None, description="Weather info if available")
    today_schedule: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Today's meetings and events"
    )
    overnight_updates: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Important updates since yesterday"
    )
    kpi_snapshot: Dict[str, Any] = Field(
        default_factory=dict,
        description="Current KPI values"
    )
    urgent_items: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Urgent items requiring attention"
    )
    recommendations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Top recommendations for today"
    )
    unread_summary: Dict[str, int] = Field(
        default_factory=dict,
        description="Unread message counts by platform"
    )


class EveningWrapContent(BaseModel):
    """Structured content for evening wrap"""
    summary: str = Field(..., description="Day summary")
    meetings_today: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Meetings held today"
    )
    tasks_completed: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Completed tasks"
    )
    tasks_pending: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Pending tasks"
    )
    kpi_changes: Dict[str, Any] = Field(
        default_factory=dict,
        description="KPI changes since morning"
    )
    new_insights: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="New insights generated today"
    )
    tomorrow_preview: Dict[str, Any] = Field(
        default_factory=dict,
        description="Preview of tomorrow's schedule"
    )
    reflection: Optional[str] = Field(
        None,
        description="AI-generated reflection on the day"
    )


class InvestorSummaryContent(BaseModel):
    """Structured content for investor summary"""
    executive_summary: str = Field(..., description="High-level summary")
    key_metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key business metrics"
    )
    growth_highlights: List[str] = Field(
        default_factory=list,
        description="Growth achievements"
    )
    challenges: List[str] = Field(
        default_factory=list,
        description="Current challenges"
    )
    financial_overview: Dict[str, Any] = Field(
        default_factory=dict,
        description="Financial summary"
    )
    product_updates: List[str] = Field(
        default_factory=list,
        description="Product developments"
    )
    team_updates: List[str] = Field(
        default_factory=list,
        description="Team and hiring updates"
    )
    asks: List[str] = Field(
        default_factory=list,
        description="Asks from investors"
    )
    next_milestones: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Upcoming milestones"
    )


class BriefingGenerateRequest(BaseModel):
    """Request to generate a briefing"""
    workspace_id: UUID
    founder_id: UUID
    briefing_type: BriefingType
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    include_sections: Optional[List[str]] = None
    exclude_sections: Optional[List[str]] = None
    delivery_channels: List[DeliveryChannel] = Field(default_factory=lambda: [DeliveryChannel.IN_APP])
    personalization: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Personalization preferences"
    )


class BriefingSchedule(BaseModel):
    """Schedule configuration for briefings"""
    workspace_id: UUID
    founder_id: UUID
    briefing_type: BriefingType
    enabled: bool = Field(default=True)
    schedule_time: str = Field(..., description="Time in HH:MM format")
    timezone: str = Field(default="UTC")
    delivery_channels: List[DeliveryChannel] = Field(default_factory=list)
    days_of_week: List[int] = Field(
        default_factory=lambda: list(range(7)),
        description="Days of week (0=Monday, 6=Sunday)"
    )
    customization: Optional[Dict[str, Any]] = Field(default_factory=dict)


class BriefingScheduleResponse(BriefingSchedule):
    """Response for briefing schedule"""
    id: UUID
    last_generated: Optional[datetime] = None
    next_scheduled: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BriefingTemplate(BaseModel):
    """Template for briefing generation"""
    name: str = Field(..., max_length=255)
    briefing_type: BriefingType
    sections: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Section configuration"
    )
    styling: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="HTML/CSS styling options"
    )
    is_default: bool = Field(default=False)


class BriefingListRequest(BaseModel):
    """Request model for listing briefings"""
    workspace_id: UUID
    founder_id: Optional[UUID] = None
    briefing_type: Optional[List[BriefingType]] = None
    status: Optional[List[BriefingStatus]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=50, le=100)
    offset: int = Field(default=0, ge=0)


class BriefingListResponse(BaseModel):
    """Response model for listing briefings"""
    briefings: List[BriefingResponse] = Field(default_factory=list)
    total_count: int
    has_more: bool
    filters_applied: Dict[str, Any] = Field(default_factory=dict)


class BriefingMetrics(BaseModel):
    """Metrics about briefing generation and delivery"""
    workspace_id: UUID
    total_generated: int = Field(default=0)
    total_delivered: int = Field(default=0)
    avg_generation_time_seconds: float = Field(default=0.0)
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    by_type: Dict[str, int] = Field(default_factory=dict)
    by_channel: Dict[str, int] = Field(default_factory=dict)
    period_start: datetime
    period_end: datetime
