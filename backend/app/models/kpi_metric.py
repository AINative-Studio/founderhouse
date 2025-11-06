"""
KPI Metric Models
Represents KPIs and metrics from Granola and other sources
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


class MetricCategory(str, Enum):
    """KPI category types"""
    REVENUE = "revenue"
    GROWTH = "growth"
    USER_ACQUISITION = "user_acquisition"
    RETENTION = "retention"
    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    CUSTOM = "custom"


class MetricUnit(str, Enum):
    """Metric unit types"""
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    COUNT = "count"
    RATIO = "ratio"
    DURATION = "duration"


class AggregationPeriod(str, Enum):
    """Time aggregation periods"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class KPIMetricBase(BaseModel):
    """Base KPI metric model"""
    name: str = Field(..., max_length=255, description="Metric name")
    display_name: str = Field(..., max_length=255, description="Human-readable metric name")
    category: MetricCategory = Field(..., description="Metric category")
    unit: MetricUnit = Field(..., description="Metric unit type")
    description: Optional[str] = Field(None, description="Metric description")


class KPIMetricCreate(KPIMetricBase):
    """Model for creating a KPI metric"""
    workspace_id: UUID = Field(..., description="Workspace ID")
    source_platform: str = Field(default="granola", description="Source platform")
    is_custom: bool = Field(default=False, description="Whether this is a custom metric")
    calculation_formula: Optional[str] = Field(None, description="Calculation formula for custom metrics")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class KPIMetricUpdate(BaseModel):
    """Model for updating KPI metric"""
    display_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class KPIMetricResponse(KPIMetricBase):
    """Response model for KPI metric"""
    id: UUID = Field(..., description="Metric ID")
    workspace_id: UUID = Field(..., description="Workspace ID")
    source_platform: str = Field(..., description="Source platform")
    is_custom: bool = Field(..., description="Whether this is a custom metric")
    is_active: bool = Field(default=True, description="Whether metric is active")
    calculation_formula: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class KPIDataPointBase(BaseModel):
    """Base KPI data point model"""
    value: float = Field(..., description="Metric value")
    timestamp: datetime = Field(..., description="Data point timestamp")


class KPIDataPointCreate(KPIDataPointBase):
    """Model for creating a KPI data point"""
    metric_id: UUID = Field(..., description="Associated metric ID")
    workspace_id: UUID = Field(..., description="Workspace ID")
    period: AggregationPeriod = Field(..., description="Aggregation period")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    source_id: Optional[str] = Field(None, description="External source ID")


class KPIDataPointResponse(KPIDataPointBase):
    """Response model for KPI data point"""
    id: UUID = Field(..., description="Data point ID")
    metric_id: UUID = Field(..., description="Associated metric ID")
    workspace_id: UUID = Field(..., description="Workspace ID")
    period: AggregationPeriod = Field(..., description="Aggregation period")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source_id: Optional[str] = None
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


class KPISnapshot(BaseModel):
    """Current snapshot of all KPIs"""
    workspace_id: UUID
    timestamp: datetime
    metrics: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of current metric values"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class KPITimeSeriesRequest(BaseModel):
    """Request model for KPI time series data"""
    metric_id: UUID
    start_date: datetime
    end_date: datetime
    period: Optional[AggregationPeriod] = AggregationPeriod.DAILY
    include_derived: bool = Field(default=False, description="Include derived metrics")


class KPITimeSeriesResponse(BaseModel):
    """Response model for KPI time series data"""
    metric_id: UUID
    metric_name: str
    category: MetricCategory
    unit: MetricUnit
    period: AggregationPeriod
    data_points: List[KPIDataPointResponse] = Field(default_factory=list)
    statistics: Optional[Dict[str, float]] = Field(
        None,
        description="Summary statistics (mean, median, min, max, std)"
    )
    trend: Optional[Dict[str, Any]] = Field(
        None,
        description="Trend information (direction, percentage_change)"
    )


class DerivedMetric(BaseModel):
    """Derived/calculated metric definition"""
    name: str
    display_name: str
    formula: str = Field(..., description="Calculation formula using metric names")
    depends_on: List[UUID] = Field(..., description="List of metric IDs this depends on")
    category: MetricCategory
    unit: MetricUnit
    description: Optional[str] = None


class MetricAlert(BaseModel):
    """Metric alert configuration"""
    metric_id: UUID
    condition: str = Field(..., description="Alert condition (e.g., '>10%', '<1000')")
    threshold: float
    enabled: bool = Field(default=True)
    notification_channels: List[str] = Field(default_factory=list)


class SyncStatus(BaseModel):
    """KPI sync status"""
    workspace_id: UUID
    last_sync_at: Optional[datetime] = None
    next_sync_at: Optional[datetime] = None
    status: str = Field(..., description="Sync status: success, error, in_progress")
    metrics_synced: int = Field(default=0)
    errors: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
