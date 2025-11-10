"""
Pydantic Models for API Request/Response Validation
"""
from app.models.workspace import (
    WorkspaceBase,
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceUpdate
)
from app.models.founder import (
    FounderBase,
    FounderCreate,
    FounderResponse,
    FounderPreferences
)
from app.models.integration import (
    IntegrationBase,
    IntegrationCreate,
    IntegrationResponse,
    IntegrationStatus,
    IntegrationHealthCheck,
    ConnectionType,
    Platform
)
from app.models.kpi_metric import (
    KPIMetricBase,
    KPIMetricCreate,
    KPIMetricResponse,
    KPIDataPointCreate,
    KPIDataPointResponse,
    KPISnapshot,
    KPITimeSeriesResponse,
    MetricCategory,
    MetricUnit,
    AggregationPeriod
)
from app.models.anomaly import (
    AnomalyCreate,
    AnomalyResponse,
    TrendCreate,
    TrendResponse,
    AnomalyType,
    AnomalySeverity,
    TrendDirection,
    MetricAnalysis
)
from app.models.recommendation import (
    RecommendationCreate,
    RecommendationResponse,
    RecommendationFeedback,
    RecommendationImpact,
    RecommendationType,
    RecommendationPriority,
    RecommendationStatus,
    GenerateRecommendationRequest
)
from app.models.briefing import (
    BriefingCreate,
    BriefingResponse,
    BriefingType,
    BriefingStatus,
    MorningBriefContent,
    EveningWrapContent,
    InvestorSummaryContent,
    BriefingGenerateRequest,
    BriefingSchedule
)
from app.models.voice_command import (
    VoiceCommandRequest,
    VoiceCommandResponse,
    VoiceCommandStatus,
    VoiceCommandIntent,
    VoiceTranscriptionRequest,
    VoiceTranscriptionResponse
)
from app.models.loom_video import (
    LoomVideoIngestRequest,
    LoomVideoResponse,
    LoomVideoStatus,
    LoomVideoType,
    LoomSummarizeRequest,
    LoomVideoSummary
)
from app.models.discord_message import (
    DiscordStatusUpdateRequest,
    DiscordBriefingRequest,
    DiscordMessageResponse,
    DiscordMessageType,
    DiscordEmbed
)
from app.models.agent_routing import (
    AgentRouteRequest,
    AgentTaskResponse,
    AgentCollaborationRequest,
    AgentCollaborationResponse,
    AgentType,
    AgentTaskStatus,
    AgentTaskPriority,
    AgentHealthStatus
)
from app.models.feedback import (
    FeedbackSubmitRequest,
    FeedbackResponse,
    FeedbackType,
    FeedbackCategory,
    FeedbackStatus,
    FeedbackAnalytics
)

__all__ = [
    # Workspace models
    "WorkspaceBase",
    "WorkspaceCreate",
    "WorkspaceResponse",
    "WorkspaceUpdate",
    # Founder models
    "FounderBase",
    "FounderCreate",
    "FounderResponse",
    "FounderPreferences",
    # Integration models
    "IntegrationBase",
    "IntegrationCreate",
    "IntegrationResponse",
    "IntegrationStatus",
    "IntegrationHealthCheck",
    "ConnectionType",
    "Platform",
    # KPI models
    "KPIMetricBase",
    "KPIMetricCreate",
    "KPIMetricResponse",
    "KPIDataPointCreate",
    "KPIDataPointResponse",
    "KPISnapshot",
    "KPITimeSeriesResponse",
    "MetricCategory",
    "MetricUnit",
    "AggregationPeriod",
    # Anomaly models
    "AnomalyCreate",
    "AnomalyResponse",
    "TrendCreate",
    "TrendResponse",
    "AnomalyType",
    "AnomalySeverity",
    "TrendDirection",
    "MetricAnalysis",
    # Recommendation models
    "RecommendationCreate",
    "RecommendationResponse",
    "RecommendationFeedback",
    "RecommendationImpact",
    "RecommendationType",
    "RecommendationPriority",
    "RecommendationStatus",
    "GenerateRecommendationRequest",
    # Briefing models
    "BriefingCreate",
    "BriefingResponse",
    "BriefingType",
    "BriefingStatus",
    "MorningBriefContent",
    "EveningWrapContent",
    "InvestorSummaryContent",
    "BriefingGenerateRequest",
    "BriefingSchedule",
    # Voice Command models
    "VoiceCommandRequest",
    "VoiceCommandResponse",
    "VoiceCommandStatus",
    "VoiceCommandIntent",
    "VoiceTranscriptionRequest",
    "VoiceTranscriptionResponse",
    # Loom Video models
    "LoomVideoIngestRequest",
    "LoomVideoResponse",
    "LoomVideoStatus",
    "LoomVideoType",
    "LoomSummarizeRequest",
    "LoomVideoSummary",
    # Discord models
    "DiscordStatusUpdateRequest",
    "DiscordBriefingRequest",
    "DiscordMessageResponse",
    "DiscordMessageType",
    "DiscordEmbed",
    # Agent Routing models
    "AgentRouteRequest",
    "AgentTaskResponse",
    "AgentCollaborationRequest",
    "AgentCollaborationResponse",
    "AgentType",
    "AgentTaskStatus",
    "AgentTaskPriority",
    "AgentHealthStatus",
    # Feedback models
    "FeedbackSubmitRequest",
    "FeedbackResponse",
    "FeedbackType",
    "FeedbackCategory",
    "FeedbackStatus",
    "FeedbackAnalytics",
]
