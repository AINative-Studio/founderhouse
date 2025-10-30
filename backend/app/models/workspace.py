"""
Workspace Models
Multi-tenant workspace for founders and team members
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, validator


class WorkspaceBase(BaseModel):
    """Base workspace model with common fields"""
    name: str = Field(..., min_length=1, max_length=255, description="Workspace name")


class WorkspaceCreate(WorkspaceBase):
    """Model for creating a new workspace"""
    # Inherits name from WorkspaceBase
    # Additional fields can be added here if needed during creation
    pass


class WorkspaceUpdate(BaseModel):
    """Model for updating workspace fields"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Updated workspace name")


class WorkspaceResponse(WorkspaceBase):
    """Response model for workspace data"""
    id: UUID = Field(..., description="Unique workspace identifier")
    created_at: datetime = Field(..., description="Workspace creation timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Acme Startup",
                "created_at": "2025-10-30T10:00:00Z"
            }
        }


class WorkspaceMember(BaseModel):
    """Workspace member model"""
    id: UUID
    workspace_id: UUID
    user_id: UUID
    role: str = Field(..., description="Member role: owner, admin, member, viewer, service")
    created_at: datetime

    @validator("role")
    def validate_role(cls, v):
        """Validate role value"""
        allowed_roles = ["owner", "admin", "member", "viewer", "service"]
        if v not in allowed_roles:
            raise ValueError(f"Role must be one of: {allowed_roles}")
        return v

    class Config:
        from_attributes = True


class WorkspaceDetail(WorkspaceResponse):
    """Detailed workspace information including statistics"""
    member_count: int = Field(default=0, description="Number of workspace members")
    founder_count: int = Field(default=0, description="Number of founders")
    integration_count: int = Field(default=0, description="Number of connected integrations")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Acme Startup",
                "created_at": "2025-10-30T10:00:00Z",
                "member_count": 5,
                "founder_count": 2,
                "integration_count": 8
            }
        }
