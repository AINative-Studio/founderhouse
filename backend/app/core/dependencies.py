"""
Dependency Injection Utilities
Common dependencies used across API endpoints
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user, AuthUser

logger = logging.getLogger(__name__)


async def get_workspace_id(
    workspace_id: Optional[UUID] = Query(None, description="Workspace ID filter"),
    current_user: AuthUser = Depends(get_current_user)
) -> UUID:
    """
    Get workspace ID from query parameter or user token

    Args:
        workspace_id: Optional workspace ID from query
        current_user: Current authenticated user

    Returns:
        Workspace UUID

    Raises:
        HTTPException: If workspace ID is not provided and not in token
    """
    if workspace_id:
        # Verify user has access to this workspace
        # In production, query database to check membership
        return workspace_id

    if current_user.workspace_id:
        return current_user.workspace_id

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Workspace ID is required"
    )


async def get_founder_id(
    founder_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
) -> UUID:
    """
    Validate founder ID and check user access

    Args:
        founder_id: Founder UUID to validate
        db: Database client
        current_user: Current authenticated user

    Returns:
        Validated founder UUID

    Raises:
        HTTPException: If founder not found or access denied
    """
    try:
        # Query founder from database
        from sqlalchemy import text
        result = db.execute(
            text('SELECT * FROM "core"."founders" WHERE id = :founder_id'),
            {"founder_id": str(founder_id)}
        )
        founder = result.fetchone()

        if not founder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Founder {founder_id} not found"
            )

        # Verify user has access to this founder's workspace
        if current_user.workspace_id and str(current_user.workspace_id) != founder.workspace_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this founder"
            )

        return founder_id

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating founder ID: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate founder ID"
        )


class PaginationParams:
    """Pagination parameters for list endpoints"""

    def __init__(
        self,
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
    ):
        self.skip = skip
        self.limit = limit


async def get_pagination_params(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return")
) -> dict:
    """
    Get pagination parameters

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        Dictionary with pagination parameters
    """
    return {
        "skip": skip,
        "limit": limit
    }


class FilterParams:
    """Common filter parameters"""

    def __init__(
        self,
        search: Optional[str] = Query(None, description="Search query"),
        sort_by: Optional[str] = Query(None, description="Field to sort by"),
        sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order: asc or desc")
    ):
        self.search = search
        self.sort_by = sort_by
        self.sort_order = sort_order


async def validate_uuid(value: str, field_name: str = "id") -> UUID:
    """
    Validate and convert string to UUID

    Args:
        value: String value to validate
        field_name: Name of the field (for error messages)

    Returns:
        UUID object

    Raises:
        HTTPException: If value is not a valid UUID
    """
    try:
        return UUID(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name} format. Must be a valid UUID."
        )


def verify_workspace_member(required_role: Optional[str] = None):
    """
    Factory function to create workspace membership verification dependency

    Args:
        required_role: Optional minimum role required (owner, admin, member, viewer)

    Returns:
        Dependency function
    """
    async def verify_membership(
        workspace_id: UUID = Depends(get_workspace_id),
        current_user: AuthUser = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> bool:
        """Verify user is a member of the workspace with required role"""
        try:
            # Query workspace membership
            from sqlalchemy import text
            result = db.execute(
                text('SELECT * FROM "core"."members" WHERE workspace_id = :workspace_id AND user_id = :user_id'),
                {"workspace_id": str(workspace_id), "user_id": str(current_user.user_id)}
            )
            member = result.fetchone()

            if not member:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this workspace"
                )

            # Check role if required
            if required_role:
                role_hierarchy = {
                    "owner": 4,
                    "admin": 3,
                    "member": 2,
                    "viewer": 1
                }

                member_level = role_hierarchy.get(member.role, 0)
                required_level = role_hierarchy.get(required_role, 0)

                if member_level < required_level:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Insufficient permissions. Required role: {required_role}"
                    )

            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error verifying workspace membership: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to verify workspace access"
            )

    return verify_membership
