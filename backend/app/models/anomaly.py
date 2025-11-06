"""
Anomaly Models
Represents detected anomalies and trends in KPI data
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


class AnomalyType(str, Enum):
    """Types of anomalies"""
    SPIKE = "spike"
    DROP = "drop"
    TREND_CHANGE = "trend_change"
    STATISTICAL_OUTLIER = "statistical_outlier"
    SEASONAL_DEVIATION = "seasonal_deviation"
    THRESHOLD_BREACH = "threshold_breach"


class AnomalySeverity(str, Enum):
    """Anomaly severity levels"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DetectionMethod(str, Enum):
    """Anomaly detection methods"""
    ZSCORE = "zscore"
    IQR = "iqr"
    MOVING_AVERAGE = "moving_average"
    SEASONAL_DECOMPOSITION = "seasonal_decomposition"
    THRESHOLD = "threshold"
    MACHINE_LEARNING = "machine_learning"


class TrendDirection(str, Enum):
    """Trend direction"""
    UP = "up"
    DOWN = "down"
    STABLE = "stable"
    VOLATILE = "volatile"


class AnomalyBase(BaseModel):
    """Base anomaly model"""
    metric_id: UUID = Field(..., description="Associated metric ID")
    anomaly_type: AnomalyType = Field(..., description="Type of anomaly")
    severity: AnomalySeverity = Field(..., description="Severity level")
    detection_method: DetectionMethod = Field(..., description="Detection method used")


class AnomalyCreate(AnomalyBase):
    """Model for creating an anomaly"""
    workspace_id: UUID = Field(..., description="Workspace ID")
    data_point_id: UUID = Field(..., description="Associated data point ID")
    expected_value: float = Field(..., description="Expected/predicted value")
    actual_value: float = Field(..., description="Actual observed value")
    deviation: float = Field(..., description="Deviation from expected (percentage or absolute)")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in detection (0-1)")
    context: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Contextual information about the anomaly"
    )
    is_acknowledged: bool = Field(default=False, description="Whether anomaly has been acknowledged")


class AnomalyUpdate(BaseModel):
    """Model for updating an anomaly"""
    is_acknowledged: Optional[bool] = None
    severity: Optional[AnomalySeverity] = None
    notes: Optional[str] = None
    resolved_at: Optional[datetime] = None


class AnomalyResponse(AnomalyBase):
    """Response model for anomaly"""
    id: UUID = Field(..., description="Anomaly ID")
    workspace_id: UUID = Field(..., description="Workspace ID")
    data_point_id: UUID = Field(..., description="Associated data point ID")
    expected_value: float = Field(..., description="Expected value")
    actual_value: float = Field(..., description="Actual value")
    deviation: float = Field(..., description="Deviation from expected")
    confidence_score: float = Field(..., description="Confidence score (0-1)")
    context: Dict[str, Any] = Field(default_factory=dict)
    is_acknowledged: bool = Field(..., description="Acknowledged status")
    notes: Optional[str] = None
    detected_at: datetime = Field(..., description="Detection timestamp")
    resolved_at: Optional[datetime] = None
    created_at: datetime = Field(..., description="Creation timestamp")

    # Related data (populated via joins)
    metric_name: Optional[str] = None
    metric_category: Optional[str] = None

    class Config:
        from_attributes = True


class TrendBase(BaseModel):
    """Base trend model"""
    metric_id: UUID = Field(..., description="Associated metric ID")
    direction: TrendDirection = Field(..., description="Trend direction")
    period: str = Field(..., description="Time period (WoW, MoM, QoQ, YoY)")


class TrendCreate(TrendBase):
    """Model for creating a trend"""
    workspace_id: UUID = Field(..., description="Workspace ID")
    start_date: datetime = Field(..., description="Trend start date")
    end_date: datetime = Field(..., description="Trend end date")
    start_value: float = Field(..., description="Starting value")
    end_value: float = Field(..., description="Ending value")
    percentage_change: float = Field(..., description="Percentage change")
    absolute_change: float = Field(..., description="Absolute change")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in trend")
    is_significant: bool = Field(
        default=False,
        description="Whether trend is statistically significant"
    )
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class TrendResponse(TrendBase):
    """Response model for trend"""
    id: UUID = Field(..., description="Trend ID")
    workspace_id: UUID = Field(..., description="Workspace ID")
    start_date: datetime = Field(..., description="Trend start date")
    end_date: datetime = Field(..., description="Trend end date")
    start_value: float = Field(..., description="Starting value")
    end_value: float = Field(..., description="Ending value")
    percentage_change: float = Field(..., description="Percentage change")
    absolute_change: float = Field(..., description="Absolute change")
    confidence_score: float = Field(..., description="Confidence score")
    is_significant: bool = Field(..., description="Statistical significance")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(..., description="Creation timestamp")

    # Related data
    metric_name: Optional[str] = None
    metric_category: Optional[str] = None

    class Config:
        from_attributes = True


class DetectionConfig(BaseModel):
    """Configuration for anomaly detection"""
    method: DetectionMethod
    sensitivity: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Detection sensitivity (0-1, higher = more sensitive)"
    )
    threshold: Optional[float] = Field(None, description="Threshold value for threshold-based detection")
    window_size: int = Field(default=30, description="Window size for rolling calculations")
    seasonal_period: Optional[int] = Field(None, description="Seasonal period for decomposition")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Method-specific parameters"
    )


class AnomalyListRequest(BaseModel):
    """Request model for listing anomalies"""
    workspace_id: UUID
    metric_ids: Optional[List[UUID]] = None
    severity: Optional[List[AnomalySeverity]] = None
    anomaly_type: Optional[List[AnomalyType]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_acknowledged: Optional[bool] = None
    limit: int = Field(default=50, le=100)
    offset: int = Field(default=0, ge=0)


class AnomalyListResponse(BaseModel):
    """Response model for listing anomalies"""
    anomalies: List[AnomalyResponse] = Field(default_factory=list)
    total_count: int
    has_more: bool
    filters_applied: Dict[str, Any] = Field(default_factory=dict)


class TrendListRequest(BaseModel):
    """Request model for listing trends"""
    workspace_id: UUID
    metric_ids: Optional[List[UUID]] = None
    direction: Optional[List[TrendDirection]] = None
    period: Optional[str] = None
    is_significant: Optional[bool] = None
    limit: int = Field(default=50, le=100)
    offset: int = Field(default=0, ge=0)


class TrendListResponse(BaseModel):
    """Response model for listing trends"""
    trends: List[TrendResponse] = Field(default_factory=list)
    total_count: int
    has_more: bool
    filters_applied: Dict[str, Any] = Field(default_factory=dict)


class MetricAnalysis(BaseModel):
    """Comprehensive metric analysis"""
    metric_id: UUID
    metric_name: str
    time_range: Dict[str, datetime]
    current_value: float
    previous_value: float
    change: Dict[str, float] = Field(
        ...,
        description="Change information (absolute, percentage, direction)"
    )
    anomalies: List[AnomalyResponse] = Field(default_factory=list)
    trends: List[TrendResponse] = Field(default_factory=list)
    statistics: Dict[str, float] = Field(
        default_factory=dict,
        description="Statistical measures"
    )
    forecast: Optional[Dict[str, Any]] = Field(
        None,
        description="Forecast data if available"
    )
    insights: List[str] = Field(
        default_factory=list,
        description="Generated insights"
    )
