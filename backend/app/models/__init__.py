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
]
