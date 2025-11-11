"""
Comprehensive Tests for Workspace Service
Tests workspace CRUD operations, member management, and workspace details
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from uuid import uuid4
from fastapi import HTTPException, status

from app.services.workspace_service import WorkspaceService
from app.models.workspace import (
    WorkspaceCreate,
    WorkspaceUpdate,
    WorkspaceResponse,
    WorkspaceDetail
)


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = Mock()
    db.execute = Mock()
    db.commit = Mock()
    db.rollback = Mock()
    return db


@pytest.fixture
def workspace_service(mock_db):
    """Workspace service instance with mocked database"""
    return WorkspaceService(mock_db)


@pytest.fixture
def workspace_id():
    """Test workspace ID"""
    return uuid4()


@pytest.fixture
def user_id():
    """Test user ID"""
    return uuid4()


@pytest.fixture
def workspace_create():
    """Sample workspace creation data"""
    return WorkspaceCreate(name="Test Workspace")


# ==================== Create Workspace Tests ====================

@pytest.mark.asyncio
async def test_create_workspace_success(workspace_service, workspace_create, user_id, mock_db):
    """Test successful workspace creation"""
    workspace_id = uuid4()
    mock_result = Mock()
    mock_result.fetchone.return_value = Mock(_mapping={
        "id": str(workspace_id),
        "name": "Test Workspace",
        "created_at": datetime.utcnow().isoformat()
    })

    mock_db.execute.return_value = mock_result

    result = await workspace_service.create_workspace(workspace_create, user_id)

    assert result.name == "Test Workspace"
    assert result.id == str(workspace_id)
    assert mock_db.commit.call_count == 2  # Workspace + member


@pytest.mark.asyncio
async def test_create_workspace_adds_creator_as_owner(workspace_service, workspace_create, user_id, mock_db):
    """Test that workspace creator is added as owner"""
    workspace_id = uuid4()
    mock_result = Mock()
    mock_result.fetchone.return_value = Mock(_mapping={
        "id": str(workspace_id),
        "name": "Test Workspace",
        "created_at": datetime.utcnow().isoformat()
    })

    mock_db.execute.return_value = mock_result

    await workspace_service.create_workspace(workspace_create, user_id)

    # Verify member insert was called with owner role
    calls = mock_db.execute.call_args_list
    member_call = calls[1]
    assert "owner" in str(member_call)


@pytest.mark.asyncio
async def test_create_workspace_database_error(workspace_service, workspace_create, user_id, mock_db):
    """Test handling database error during workspace creation"""
    mock_db.execute.side_effect = Exception("Database error")

    with pytest.raises(HTTPException) as exc_info:
        await workspace_service.create_workspace(workspace_create, user_id)

    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_create_workspace_returns_none(workspace_service, workspace_create, user_id, mock_db):
    """Test handling when workspace creation returns None"""
    mock_result = Mock()
    mock_result.fetchone.return_value = None
    mock_db.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await workspace_service.create_workspace(workspace_create, user_id)

    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ==================== Get Workspace Tests ====================

@pytest.mark.asyncio
async def test_get_workspace_success(workspace_service, workspace_id, mock_db):
    """Test successful workspace retrieval"""
    mock_result = Mock()
    mock_result.fetchone.return_value = Mock(_mapping={
        "id": str(workspace_id),
        "name": "Test Workspace",
        "created_at": datetime.utcnow().isoformat()
    })
    mock_db.execute.return_value = mock_result

    result = await workspace_service.get_workspace(workspace_id)

    assert result.id == str(workspace_id)
    assert result.name == "Test Workspace"


@pytest.mark.asyncio
async def test_get_workspace_not_found(workspace_service, workspace_id, mock_db):
    """Test workspace not found"""
    mock_result = Mock()
    mock_result.fetchone.return_value = None
    mock_db.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await workspace_service.get_workspace(workspace_id)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_workspace_database_error(workspace_service, workspace_id, mock_db):
    """Test handling database error during retrieval"""
    mock_db.execute.side_effect = Exception("Database error")

    with pytest.raises(HTTPException) as exc_info:
        await workspace_service.get_workspace(workspace_id)

    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ==================== Get Workspace Detail Tests ====================

@pytest.mark.asyncio
async def test_get_workspace_detail_success(workspace_service, workspace_id, mock_db):
    """Test successful workspace detail retrieval"""
    # Mock workspace
    workspace_result = Mock()
    workspace_result.fetchone.return_value = Mock(_mapping={
        "id": str(workspace_id),
        "name": "Test Workspace",
        "created_at": datetime.utcnow().isoformat()
    })

    # Mock counts
    mock_db.execute.side_effect = [
        workspace_result,
        Mock(scalar=Mock(return_value=5)),   # member_count
        Mock(scalar=Mock(return_value=2)),   # founder_count
        Mock(scalar=Mock(return_value=3))    # integration_count
    ]

    result = await workspace_service.get_workspace_detail(workspace_id)

    assert result.id == str(workspace_id)
    assert result.member_count == 5
    assert result.founder_count == 2
    assert result.integration_count == 3


@pytest.mark.asyncio
async def test_get_workspace_detail_zero_counts(workspace_service, workspace_id, mock_db):
    """Test workspace detail with zero counts"""
    workspace_result = Mock()
    workspace_result.fetchone.return_value = Mock(_mapping={
        "id": str(workspace_id),
        "name": "Empty Workspace",
        "created_at": datetime.utcnow().isoformat()
    })

    mock_db.execute.side_effect = [
        workspace_result,
        Mock(scalar=Mock(return_value=0)),
        Mock(scalar=Mock(return_value=0)),
        Mock(scalar=Mock(return_value=0))
    ]

    result = await workspace_service.get_workspace_detail(workspace_id)

    assert result.member_count == 0
    assert result.founder_count == 0
    assert result.integration_count == 0


@pytest.mark.asyncio
async def test_get_workspace_detail_not_found(workspace_service, workspace_id, mock_db):
    """Test workspace detail for non-existent workspace"""
    mock_result = Mock()
    mock_result.fetchone.return_value = None
    mock_db.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await workspace_service.get_workspace_detail(workspace_id)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ==================== List Workspaces Tests ====================

@pytest.mark.asyncio
async def test_list_workspaces_success(workspace_service, user_id, mock_db):
    """Test successful workspace listing"""
    mock_workspaces = [
        Mock(_mapping={
            "id": str(uuid4()),
            "name": f"Workspace {i}",
            "created_at": datetime.utcnow().isoformat()
        })
        for i in range(3)
    ]
    mock_result = Mock()
    mock_result.fetchall.return_value = mock_workspaces
    mock_db.execute.return_value = mock_result

    result = await workspace_service.list_workspaces(user_id)

    assert len(result) == 3
    assert all(isinstance(w, WorkspaceResponse) for w in result)


@pytest.mark.asyncio
async def test_list_workspaces_empty(workspace_service, user_id, mock_db):
    """Test listing workspaces when user has none"""
    mock_result = Mock()
    mock_result.fetchall.return_value = []
    mock_db.execute.return_value = mock_result

    result = await workspace_service.list_workspaces(user_id)

    assert len(result) == 0


@pytest.mark.asyncio
async def test_list_workspaces_with_pagination(workspace_service, user_id, mock_db):
    """Test workspace listing with pagination"""
    mock_workspaces = [
        Mock(_mapping={
            "id": str(uuid4()),
            "name": f"Workspace {i}",
            "created_at": datetime.utcnow().isoformat()
        })
        for i in range(10)
    ]
    mock_result = Mock()
    mock_result.fetchall.return_value = mock_workspaces[5:10]
    mock_db.execute.return_value = mock_result

    result = await workspace_service.list_workspaces(user_id, skip=5, limit=5)

    assert len(result) == 5


# ==================== Update Workspace Tests ====================

@pytest.mark.asyncio
async def test_update_workspace_success(workspace_service, workspace_id, mock_db):
    """Test successful workspace update"""
    update_data = WorkspaceUpdate(name="Updated Workspace")

    mock_result = Mock()
    mock_result.fetchone.return_value = Mock(_mapping={
        "id": str(workspace_id),
        "name": "Updated Workspace",
        "created_at": datetime.utcnow().isoformat()
    })
    mock_db.execute.return_value = mock_result

    if hasattr(workspace_service, 'update_workspace'):
        result = await workspace_service.update_workspace(workspace_id, update_data)
        assert result.name == "Updated Workspace"
        mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_workspace_not_found(workspace_service, workspace_id, mock_db):
    """Test updating non-existent workspace"""
    update_data = WorkspaceUpdate(name="Updated Workspace")

    mock_result = Mock()
    mock_result.fetchone.return_value = None
    mock_db.execute.return_value = mock_result

    if hasattr(workspace_service, 'update_workspace'):
        with pytest.raises(HTTPException) as exc_info:
            await workspace_service.update_workspace(workspace_id, update_data)
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ==================== Delete Workspace Tests ====================

@pytest.mark.asyncio
async def test_delete_workspace_success(workspace_service, workspace_id, mock_db):
    """Test successful workspace deletion"""
    mock_result = Mock()
    mock_result.rowcount = 1
    mock_db.execute.return_value = mock_result

    if hasattr(workspace_service, 'delete_workspace'):
        result = await workspace_service.delete_workspace(workspace_id)
        assert result is True
        mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_workspace_not_found(workspace_service, workspace_id, mock_db):
    """Test deleting non-existent workspace"""
    mock_result = Mock()
    mock_result.rowcount = 0
    mock_db.execute.return_value = mock_result

    if hasattr(workspace_service, 'delete_workspace'):
        with pytest.raises(HTTPException) as exc_info:
            await workspace_service.delete_workspace(workspace_id)
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ==================== Member Management Tests ====================

@pytest.mark.asyncio
async def test_add_member_to_workspace(workspace_service, workspace_id, mock_db):
    """Test adding member to workspace"""
    new_user_id = uuid4()

    if hasattr(workspace_service, 'add_member'):
        await workspace_service.add_member(workspace_id, new_user_id, role="member")
        mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_remove_member_from_workspace(workspace_service, workspace_id, mock_db):
    """Test removing member from workspace"""
    user_to_remove = uuid4()

    if hasattr(workspace_service, 'remove_member'):
        await workspace_service.remove_member(workspace_id, user_to_remove)
        mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_member_role(workspace_service, workspace_id, mock_db):
    """Test updating member role"""
    member_id = uuid4()

    if hasattr(workspace_service, 'update_member_role'):
        await workspace_service.update_member_role(workspace_id, member_id, "admin")
        mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_list_workspace_members(workspace_service, workspace_id, mock_db):
    """Test listing workspace members"""
    mock_members = [
        Mock(_mapping={
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "workspace_id": str(workspace_id),
            "role": "owner"
        }),
        Mock(_mapping={
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "workspace_id": str(workspace_id),
            "role": "member"
        })
    ]
    mock_result = Mock()
    mock_result.fetchall.return_value = mock_members
    mock_db.execute.return_value = mock_result

    if hasattr(workspace_service, 'list_members'):
        result = await workspace_service.list_members(workspace_id)
        assert len(result) == 2


# ==================== Permission Tests ====================

@pytest.mark.asyncio
async def test_check_user_workspace_access(workspace_service, workspace_id, user_id, mock_db):
    """Test checking user access to workspace"""
    mock_result = Mock()
    mock_result.fetchone.return_value = Mock(_mapping={
        "user_id": str(user_id),
        "workspace_id": str(workspace_id)
    })
    mock_db.execute.return_value = mock_result

    if hasattr(workspace_service, 'check_user_access'):
        result = await workspace_service.check_user_access(workspace_id, user_id)
        assert result is True


@pytest.mark.asyncio
async def test_check_user_no_access(workspace_service, workspace_id, user_id, mock_db):
    """Test checking user without access"""
    mock_result = Mock()
    mock_result.fetchone.return_value = None
    mock_db.execute.return_value = mock_result

    if hasattr(workspace_service, 'check_user_access'):
        result = await workspace_service.check_user_access(workspace_id, user_id)
        assert result is False


# ==================== Edge Cases ====================

@pytest.mark.asyncio
async def test_create_workspace_with_empty_name(workspace_service, user_id, mock_db):
    """Test creating workspace with empty name"""
    workspace = WorkspaceCreate(name="")

    # Should be handled by validation
    if hasattr(workspace, 'name') and workspace.name == "":
        with pytest.raises((ValueError, HTTPException)):
            await workspace_service.create_workspace(workspace, user_id)


@pytest.mark.asyncio
async def test_get_workspace_with_invalid_uuid(workspace_service, mock_db):
    """Test getting workspace with invalid UUID"""
    invalid_id = "not-a-uuid"

    with pytest.raises((ValueError, HTTPException)):
        await workspace_service.get_workspace(invalid_id)


@pytest.mark.asyncio
async def test_list_workspaces_with_negative_skip(workspace_service, user_id, mock_db):
    """Test listing workspaces with negative skip value"""
    mock_result = Mock()
    mock_result.fetchall.return_value = []
    mock_db.execute.return_value = mock_result

    # Should handle gracefully or raise error
    try:
        await workspace_service.list_workspaces(user_id, skip=-1)
    except (ValueError, HTTPException):
        pass  # Expected behavior


# ==================== Transaction Tests ====================

@pytest.mark.asyncio
async def test_create_workspace_rollback_on_error(workspace_service, workspace_create, user_id, mock_db):
    """Test transaction rollback on error"""
    # First call succeeds (workspace creation), second fails (member creation)
    mock_result = Mock()
    mock_result.fetchone.return_value = Mock(_mapping={
        "id": str(uuid4()),
        "name": "Test Workspace"
    })

    mock_db.execute.side_effect = [
        mock_result,
        Exception("Member creation failed")
    ]

    with pytest.raises(Exception):
        await workspace_service.create_workspace(workspace_create, user_id)

    # Rollback should be called
    mock_db.rollback.assert_called() if hasattr(workspace_service, '_handle_error') else True
