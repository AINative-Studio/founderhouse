"""
Workspace Management Endpoints
Multi-tenant workspace operations
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user, AuthUser, require_role
from app.core.dependencies import get_pagination_params
from app.models.workspace import (
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceUpdate,
    WorkspaceDetail
)
from app.services.workspace_service import WorkspaceService

router = APIRouter()


def get_workspace_service(db: Session = Depends(get_db)) -> WorkspaceService:
    """Dependency to get workspace service instance"""
    return WorkspaceService(db)


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Workspace"
)
async def create_workspace(
    workspace: WorkspaceCreate,
    current_user: AuthUser = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service)
):
    """
    Create a new workspace

    The authenticated user will be added as the workspace owner.

    **Request Body:**
    - name: Workspace name (required, 1-255 characters)

    **Returns:**
    - Created workspace with ID and metadata

    **Permissions:**
    - Any authenticated user can create a workspace
    """
    return await service.create_workspace(workspace, current_user.user_id)


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceDetail,
    summary="Get Workspace"
)
async def get_workspace(
    workspace_id: UUID,
    current_user: AuthUser = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service)
):
    """
    Get detailed workspace information

    **Path Parameters:**
    - workspace_id: Workspace UUID

    **Returns:**
    - Workspace details including:
      - Basic information
      - Member count
      - Founder count
      - Integration count

    **Permissions:**
    - User must be a member of the workspace
    """
    # TODO: Verify user is member of workspace
    workspace = await service.get_workspace_detail(workspace_id)
    return workspace


@router.get(
    "",
    response_model=List[WorkspaceResponse],
    summary="List Workspaces"
)
async def list_workspaces(
    pagination: dict = Depends(get_pagination_params),
    current_user: AuthUser = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service)
):
    """
    List workspaces accessible to the current user

    Returns all workspaces where the user is a member.

    **Query Parameters:**
    - skip: Number of records to skip (default: 0)
    - limit: Maximum records to return (default: 100, max: 1000)

    **Returns:**
    - List of workspace objects

    **Permissions:**
    - Returns only workspaces where user is a member
    """
    workspaces = await service.list_workspaces(
        current_user.user_id,
        skip=pagination["skip"],
        limit=pagination["limit"]
    )
    return workspaces


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="Update Workspace"
)
async def update_workspace(
    workspace_id: UUID,
    workspace_update: WorkspaceUpdate,
    current_user: AuthUser = Depends(require_role("admin")),
    service: WorkspaceService = Depends(get_workspace_service)
):
    """
    Update workspace information

    **Path Parameters:**
    - workspace_id: Workspace UUID

    **Request Body:**
    - name: Updated workspace name (optional)

    **Returns:**
    - Updated workspace object

    **Permissions:**
    - User must have admin or owner role in the workspace
    """
    # TODO: Verify user is admin/owner of workspace
    return await service.update_workspace(workspace_id, workspace_update)


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Workspace"
)
async def delete_workspace(
    workspace_id: UUID,
    current_user: AuthUser = Depends(require_role("owner")),
    service: WorkspaceService = Depends(get_workspace_service)
):
    """
    Delete a workspace

    **WARNING:** This will permanently delete the workspace and all associated data:
    - All members
    - All founders
    - All integrations
    - All communications, meetings, tasks, etc.

    This operation cannot be undone.

    **Path Parameters:**
    - workspace_id: Workspace UUID

    **Permissions:**
    - User must be the workspace owner

    **Recommendation:**
    - Consider implementing soft delete in production
    """
    # TODO: Verify user is owner of workspace
    await service.delete_workspace(workspace_id)
    return None
