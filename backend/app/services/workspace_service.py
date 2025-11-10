"""
Workspace Service
Business logic for workspace management
"""
import logging
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import text
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

    def __init__(self, db: Session):
        """
        Initialize workspace service

        Args:
            db: SQLAlchemy database session
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
            query = text('''
                INSERT INTO "core"."workspaces" (name, created_at)
                VALUES (:name, :created_at)
                RETURNING *
            ''')
            result = self.db.execute(query, {
                "name": workspace.name,
                "created_at": datetime.utcnow().isoformat()
            })
            self.db.commit()
            created_workspace = result.fetchone()

            if not created_workspace:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create workspace"
                )

            # Convert to dict
            workspace_dict = dict(created_workspace._mapping)

            # Add creator as workspace owner
            member_query = text('''
                INSERT INTO "core"."members" (workspace_id, user_id, role, created_at)
                VALUES (:workspace_id, :user_id, :role, :created_at)
            ''')
            self.db.execute(member_query, {
                "workspace_id": workspace_dict["id"],
                "user_id": str(creator_user_id),
                "role": "owner",
                "created_at": datetime.utcnow().isoformat()
            })
            self.db.commit()

            logger.info(f"Created workspace {workspace_dict['id']} by user {creator_user_id}")

            return WorkspaceResponse(**workspace_dict)

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
            query = text('SELECT * FROM "core"."workspaces" WHERE id = :id')
            result = self.db.execute(query, {"id": str(workspace_id)})
            workspace = result.fetchone()

            if not workspace:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Workspace {workspace_id} not found"
                )

            return WorkspaceResponse(**dict(workspace._mapping))

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
            member_query = text('SELECT COUNT(*) FROM "core"."members" WHERE workspace_id = :workspace_id')
            member_result = self.db.execute(member_query, {"workspace_id": str(workspace_id)})
            member_count = member_result.scalar() or 0

            # Get founder count
            founder_query = text('SELECT COUNT(*) FROM "core"."founders" WHERE workspace_id = :workspace_id')
            founder_result = self.db.execute(founder_query, {"workspace_id": str(workspace_id)})
            founder_count = founder_result.scalar() or 0

            # Get integration count
            integration_query = text('SELECT COUNT(*) FROM "core"."integrations" WHERE workspace_id = :workspace_id')
            integration_result = self.db.execute(integration_query, {"workspace_id": str(workspace_id)})
            integration_count = integration_result.scalar() or 0

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
            member_query = text('SELECT workspace_id FROM "core"."members" WHERE user_id = :user_id')
            member_result = self.db.execute(member_query, {"user_id": str(user_id)})
            members = member_result.fetchall()

            if not members:
                return []

            workspace_ids = [m.workspace_id for m in members]

            # Get workspaces
            # Convert list to tuple for SQL IN clause
            workspace_query = text('''
                SELECT * FROM "core"."workspaces"
                WHERE id = ANY(:workspace_ids)
                LIMIT :limit OFFSET :skip
            ''')
            workspace_result = self.db.execute(workspace_query, {
                "workspace_ids": workspace_ids,
                "limit": limit,
                "skip": skip
            })
            workspaces = workspace_result.fetchall()

            return [WorkspaceResponse(**dict(w._mapping)) for w in workspaces]

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

            # Build UPDATE query dynamically
            set_clauses = []
            params = {"id": str(workspace_id)}

            for key, value in update_data.items():
                set_clauses.append(f"{key} = :{key}")
                params[key] = value

            set_clause = ", ".join(set_clauses)
            query = text(f'UPDATE "core"."workspaces" SET {set_clause} WHERE id = :id RETURNING *')

            result = self.db.execute(query, params)
            self.db.commit()
            workspace = result.fetchone()

            if not workspace:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Workspace {workspace_id} not found"
                )

            logger.info(f"Updated workspace {workspace_id}")
            return WorkspaceResponse(**dict(workspace._mapping))

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
            query = text('DELETE FROM "core"."workspaces" WHERE id = :id RETURNING *')
            result = self.db.execute(query, {"id": str(workspace_id)})
            self.db.commit()
            deleted = result.fetchone()

            if not deleted:
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
