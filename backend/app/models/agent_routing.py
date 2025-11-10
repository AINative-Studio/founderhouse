"""
Agent Routing Models
Pydantic models for AgentFlow orchestration and task routing
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class AgentType(str, Enum):
    """Types of AI agents in the system"""
    MEETING_ANALYST = "meeting_analyst"
    KPI_MONITOR = "kpi_monitor"
    BRIEFING_GENERATOR = "briefing_generator"
    RECOMMENDATION_ENGINE = "recommendation_engine"
    COMMUNICATION_HANDLER = "communication_handler"
    TASK_MANAGER = "task_manager"
    RESEARCH_ASSISTANT = "research_assistant"
    VOICE_PROCESSOR = "voice_processor"


class AgentTaskStatus(str, Enum):
    """Agent task processing status"""
    QUEUED = "queued"
    ASSIGNED = "assigned"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class AgentTaskPriority(str, Enum):
    """Task priority levels"""
    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AgentRouteRequest(BaseModel):
    """Request to route a task to an agent"""
    workspace_id: UUID
    founder_id: UUID
    task_type: str
    task_description: str
    priority: AgentTaskPriority = AgentTaskPriority.MEDIUM
    input_data: Dict[str, Any] = Field(default_factory=dict)
    context: Optional[Dict[str, Any]] = None
    preferred_agent: Optional[AgentType] = None
    deadline: Optional[datetime] = None
    dependencies: List[UUID] = Field(default_factory=list, description="IDs of tasks this depends on")

    model_config = ConfigDict(from_attributes=True)


class AgentTaskResponse(BaseModel):
    """Agent task record"""
    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    founder_id: UUID
    task_type: str
    task_description: str
    priority: AgentTaskPriority
    status: AgentTaskStatus
    assigned_agent: Optional[AgentType] = None
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    dependencies: List[UUID] = Field(default_factory=list)
    processing_time_ms: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    deadline: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AgentTaskCreate(BaseModel):
    """Create agent task record"""
    workspace_id: UUID
    founder_id: UUID
    task_type: str
    task_description: str
    priority: AgentTaskPriority
    status: AgentTaskStatus = AgentTaskStatus.QUEUED
    assigned_agent: Optional[AgentType] = None
    input_data: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[UUID] = Field(default_factory=list)
    deadline: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AgentTaskUpdate(BaseModel):
    """Update agent task record"""
    status: Optional[AgentTaskStatus] = None
    assigned_agent: Optional[AgentType] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: Optional[int] = None
    processing_time_ms: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AgentCollaborationRequest(BaseModel):
    """Request for cross-agent collaboration"""
    workspace_id: UUID
    founder_id: UUID
    primary_agent: AgentType
    collaborating_agents: List[AgentType]
    objective: str
    shared_context: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=300, ge=10, le=3600)

    model_config = ConfigDict(from_attributes=True)


class AgentCollaborationResponse(BaseModel):
    """Agent collaboration session record"""
    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    founder_id: UUID
    primary_agent: AgentType
    collaborating_agents: List[AgentType]
    objective: str
    status: AgentTaskStatus
    shared_context: Dict[str, Any] = Field(default_factory=dict)
    agent_outputs: Dict[str, Any] = Field(default_factory=dict)
    final_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AgentHealthStatus(BaseModel):
    """Agent health and availability status"""
    agent_type: AgentType
    is_available: bool
    current_load: int = Field(ge=0, description="Number of tasks currently processing")
    max_capacity: int = Field(default=10, description="Maximum concurrent tasks")
    average_processing_time_ms: Optional[int] = None
    success_rate: float = Field(ge=0.0, le=1.0, description="Success rate (0-1)")
    last_health_check: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class AgentMetrics(BaseModel):
    """Agent performance metrics"""
    agent_type: AgentType
    total_tasks_processed: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    average_processing_time_ms: float = 0.0
    current_queue_depth: int = 0
    uptime_percentage: float = Field(ge=0.0, le=100.0)

    model_config = ConfigDict(from_attributes=True)
