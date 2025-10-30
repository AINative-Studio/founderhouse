"""
Workspace Service
Business logic for workspace management
"""
import logging
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from supabase import Client
from fastapi import HTTPException, status

from app.models.workspace import (
    WorkspaceCreate,
    WorkspaceUpdate,
    WorkspaceResponse,
    WorkspaceDetail
)

logger = logging.getLogger(__name__)


class WorkspaceService:
    """Service for workspace operations"""

    def __init__(self, db: Client):
        """
        Initialize workspace service

        Args:
            db: Supabase database client
        """
        self.db = db

    async def create_workspace(
        self,
        workspace: WorkspaceCreate,
        creator_user_id: UUID
    ) -> WorkspaceResponse:
        """
        Create a new workspace

        Args:
            workspace: Workspace creation data
            creator_user_id: User ID of the workspace creator

        Returns:
            Created workspace

        Raises:
            HTTPException: If creation fails
        """
        try:
            # Create workspace
            workspace_data = {
                "name": workspace.name,
                "created_at": datetime.utcnow().isoformat()
            }

            response = self.db.table("core.workspaces").insert(workspace_data).execute()

            if not response.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create workspace"
                )

            created_workspace = response.data[0]

            # Add creator as workspace owner
            member_data = {
                "workspace_id": created_workspace["id"],
                "user_id": str(creator_user_id),
                "role": "owner",
                "created_at": datetime.utcnow().isoformat()
            }

            self.db.table("core.members").insert(member_data).execute()

            logger.info(f"Created workspace {created_workspace['id']} by user {creator_user_id}")

            return WorkspaceResponse(**created_workspace)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating workspace: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create workspace: {str(e)}"
            )

    async def get_workspace(self, workspace_id: UUID) -> WorkspaceResponse:
        """
        Get workspace by ID

        Args:
            workspace_id: Workspace UUID

        Returns:
            Workspace data

        Raises:
            HTTPException: If workspace not found
        """
        try:
            response = self.db.table("core.workspaces").select("*").eq(
                "id", str(workspace_id)
            ).execute()

            if not response.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Workspace {workspace_id} not found"
                )

            return WorkspaceResponse(**response.data[0])

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching workspace: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch workspace"
            )

    async def get_workspace_detail(self, workspace_id: UUID) -> WorkspaceDetail:
        """
        Get detailed workspace information with statistics

        Args:
            workspace_id: Workspace UUID

        Returns:
            Detailed workspace data

        Raises:
            HTTPException: If workspace not found
        """
        try:
            # Get workspace
            workspace = await self.get_workspace(workspace_id)

            # Get member count
            members_response = self.db.table("core.members").select(
                "id", count="exact"
            ).eq("workspace_id", str(workspace_id)).execute()
            member_count = members_response.count or 0

            # Get founder count
            founders_response = self.db.table("core.founders").select(
                "id", count="exact"
            ).eq("workspace_id", str(workspace_id)).execute()
            founder_count = founders_response.count or 0

            # Get integration count
            integrations_response = self.db.table("core.integrations").select(
                "id", count="exact"
            ).eq("workspace_id", str(workspace_id)).execute()
            integration_count = integrations_response.count or 0

            return WorkspaceDetail(
                **workspace.dict(),
                member_count=member_count,
                founder_count=founder_count,
                integration_count=integration_count
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching workspace detail: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch workspace details"
            )

    async def list_workspaces(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[WorkspaceResponse]:
        """
        List workspaces accessible by user

        Args:
            user_id: User UUID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of workspaces
        """
        try:
            # Get workspace IDs from memberships
            members_response = self.db.table("core.members").select(
                "workspace_id"
            ).eq("user_id", str(user_id)).execute()

            if not members_response.data:
                return []

            workspace_ids = [m["workspace_id"] for m in members_response.data]

            # Get workspaces
            response = self.db.table("core.workspaces").select("*").in_(
                "id", workspace_ids
            ).range(skip, skip + limit - 1).execute()

            return [WorkspaceResponse(**w) for w in response.data]

        except Exception as e:
            logger.error(f"Error listing workspaces: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list workspaces"
            )

    async def update_workspace(
        self,
        workspace_id: UUID,
        workspace_update: WorkspaceUpdate
    ) -> WorkspaceResponse:
        """
        Update workspace

        Args:
            workspace_id: Workspace UUID
            workspace_update: Update data

        Returns:
            Updated workspace

        Raises:
            HTTPException: If update fails
        """
        try:
            # Build update data (only include non-None fields)
            update_data = workspace_update.dict(exclude_unset=True)

            if not update_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No fields to update"
                )

            response = self.db.table("core.workspaces").update(update_data).eq(
                "id", str(workspace_id)
            ).execute()

            if not response.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Workspace {workspace_id} not found"
                )

            logger.info(f"Updated workspace {workspace_id}")
            return WorkspaceResponse(**response.data[0])

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating workspace: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update workspace"
            )

    async def delete_workspace(self, workspace_id: UUID) -> bool:
        """
        Delete workspace (soft delete recommended in production)

        Args:
            workspace_id: Workspace UUID

        Returns:
            True if deleted successfully

        Raises:
            HTTPException: If deletion fails
        """
        try:
            response = self.db.table("core.workspaces").delete().eq(
                "id", str(workspace_id)
            ).execute()

            if not response.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Workspace {workspace_id} not found"
                )

            logger.warning(f"Deleted workspace {workspace_id}")
            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting workspace: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete workspace"
            )
