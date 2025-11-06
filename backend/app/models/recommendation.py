"""
Recommendation Models
Represents AI-generated strategic recommendations
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


class RecommendationType(str, Enum):
    """Types of recommendations"""
    STRATEGIC = "strategic"
    OPERATIONAL = "operational"
    FINANCIAL = "financial"
    MARKETING = "marketing"
    SALES = "sales"
    PRODUCT = "product"
    HIRING = "hiring"
    COST_OPTIMIZATION = "cost_optimization"


class RecommendationPriority(str, Enum):
    """Recommendation priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class RecommendationStatus(str, Enum):
    """Recommendation lifecycle status"""
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    IMPLEMENTED = "implemented"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ImpactLevel(str, Enum):
    """Expected impact level"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    TRANSFORMATIONAL = "transformational"


class RecommendationBase(BaseModel):
    """Base recommendation model"""
    title: str = Field(..., max_length=500, description="Recommendation title")
    recommendation_type: RecommendationType = Field(..., description="Type of recommendation")
    priority: RecommendationPriority = Field(..., description="Priority level")
    description: str = Field(..., description="Detailed recommendation description")


class RecommendationCreate(RecommendationBase):
    """Model for creating a recommendation"""
    workspace_id: UUID = Field(..., description="Workspace ID")
    founder_id: UUID = Field(..., description="Founder ID")
    source_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Source data used to generate recommendation"
    )
    related_metrics: List[UUID] = Field(
        default_factory=list,
        description="Related metric IDs"
    )
    related_anomalies: List[UUID] = Field(
        default_factory=list,
        description="Related anomaly IDs"
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="AI confidence in recommendation (0-1)"
    )
    expected_impact: ImpactLevel = Field(..., description="Expected impact level")
    actionable_steps: List[str] = Field(
        default_factory=list,
        description="Specific actionable steps"
    )
    success_metrics: List[str] = Field(
        default_factory=list,
        description="Metrics to track success"
    )
    estimated_effort: Optional[str] = Field(
        None,
        description="Estimated effort (e.g., '2 weeks', '1 month')"
    )
    estimated_cost: Optional[float] = Field(None, description="Estimated implementation cost")
    deadline: Optional[datetime] = Field(None, description="Recommended deadline")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class RecommendationUpdate(BaseModel):
    """Model for updating a recommendation"""
    status: Optional[RecommendationStatus] = None
    priority: Optional[RecommendationPriority] = None
    notes: Optional[str] = None
    actual_impact: Optional[ImpactLevel] = None
    implemented_at: Optional[datetime] = None


class RecommendationResponse(RecommendationBase):
    """Response model for recommendation"""
    id: UUID = Field(..., description="Recommendation ID")
    workspace_id: UUID = Field(..., description="Workspace ID")
    founder_id: UUID = Field(..., description="Founder ID")
    status: RecommendationStatus = Field(..., description="Current status")
    source_data: Dict[str, Any] = Field(default_factory=dict)
    related_metrics: List[UUID] = Field(default_factory=list)
    related_anomalies: List[UUID] = Field(default_factory=list)
    confidence_score: float = Field(..., description="Confidence score")
    expected_impact: ImpactLevel = Field(..., description="Expected impact")
    actual_impact: Optional[ImpactLevel] = None
    actionable_steps: List[str] = Field(default_factory=list)
    success_metrics: List[str] = Field(default_factory=list)
    estimated_effort: Optional[str] = None
    estimated_cost: Optional[float] = None
    deadline: Optional[datetime] = None
    notes: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = None
    implemented_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RecommendationFeedback(BaseModel):
    """User feedback on recommendations"""
    recommendation_id: UUID
    founder_id: UUID
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5")
    is_helpful: bool
    feedback_text: Optional[str] = None
    was_implemented: bool = Field(default=False)
    actual_outcome: Optional[str] = Field(
        None,
        description="Actual outcome after implementation"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RecommendationImpact(BaseModel):
    """Track implementation impact of recommendations"""
    recommendation_id: UUID
    workspace_id: UUID
    metrics_before: Dict[str, float] = Field(
        default_factory=dict,
        description="Metric values before implementation"
    )
    metrics_after: Dict[str, float] = Field(
        default_factory=dict,
        description="Metric values after implementation"
    )
    improvement: Dict[str, float] = Field(
        default_factory=dict,
        description="Calculated improvements"
    )
    roi: Optional[float] = Field(None, description="Return on investment")
    time_to_impact: Optional[int] = Field(None, description="Days to see impact")
    implementation_date: datetime
    measurement_date: datetime
    notes: Optional[str] = None


class RecommendationListRequest(BaseModel):
    """Request model for listing recommendations"""
    workspace_id: UUID
    founder_id: Optional[UUID] = None
    recommendation_type: Optional[List[RecommendationType]] = None
    status: Optional[List[RecommendationStatus]] = None
    priority: Optional[List[RecommendationPriority]] = None
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    include_expired: bool = Field(default=False)
    limit: int = Field(default=50, le=100)
    offset: int = Field(default=0, ge=0)


class RecommendationListResponse(BaseModel):
    """Response model for listing recommendations"""
    recommendations: List[RecommendationResponse] = Field(default_factory=list)
    total_count: int
    has_more: bool
    filters_applied: Dict[str, Any] = Field(default_factory=dict)


class GenerateRecommendationRequest(BaseModel):
    """Request to generate new recommendations"""
    workspace_id: UUID
    founder_id: UUID
    focus_areas: Optional[List[RecommendationType]] = None
    include_metrics: Optional[List[UUID]] = None
    include_anomalies: Optional[List[UUID]] = None
    time_range_days: int = Field(default=30, description="Days of historical data to analyze")
    min_confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    max_recommendations: int = Field(default=5, le=10)


class GenerateRecommendationResponse(BaseModel):
    """Response from recommendation generation"""
    workspace_id: UUID
    founder_id: UUID
    recommendations: List[RecommendationResponse] = Field(default_factory=list)
    analysis_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Summary of analysis performed"
    )
    data_sources_used: List[str] = Field(
        default_factory=list,
        description="Data sources used in generation"
    )
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class RecommendationContext(BaseModel):
    """Context for recommendation generation"""
    kpi_data: Dict[str, Any] = Field(default_factory=dict)
    anomalies: List[Dict[str, Any]] = Field(default_factory=list)
    trends: List[Dict[str, Any]] = Field(default_factory=list)
    recent_meetings: List[Dict[str, Any]] = Field(default_factory=list)
    sentiment_analysis: Optional[Dict[str, Any]] = None
    industry_benchmarks: Optional[Dict[str, Any]] = None
    historical_recommendations: List[Dict[str, Any]] = Field(default_factory=list)


class RecommendationPattern(BaseModel):
    """Recognized pattern for recommendations"""
    pattern_type: str
    frequency: int = Field(..., description="How often this pattern occurs")
    avg_confidence: float = Field(..., description="Average confidence when pattern is present")
    avg_impact: ImpactLevel
    success_rate: float = Field(..., ge=0.0, le=1.0, description="Historical success rate")
    example_recommendations: List[str] = Field(default_factory=list)
