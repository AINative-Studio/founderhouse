"""
AI Chief of Staff - Model Validation Tests
Sprint 1: Unit tests for Pydantic models

Test coverage:
- Model instantiation and validation
- Field constraints and data types
- Serialization/deserialization
- Edge cases and error conditions
"""

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from backend.app.models.workspace import (
    WorkspaceBase,
    WorkspaceCreate,
    WorkspaceUpdate,
    WorkspaceResponse,
    WorkspaceMember,
    WorkspaceDetail,
)


# ============================================================================
# WORKSPACE BASE MODEL TESTS
# ============================================================================

class TestWorkspaceBase:
    """Test WorkspaceBase model validation."""

    def test_valid_workspace_name(self):
        """Test creating workspace with valid name."""
        workspace = WorkspaceBase(name="Acme Startup")
        assert workspace.name == "Acme Startup"

    def test_workspace_name_required(self):
        """Test that workspace name is required."""
        with pytest.raises(ValidationError) as exc_info:
            WorkspaceBase()

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("name",) for error in errors)
        assert any(error["type"] == "missing" for error in errors)

    def test_workspace_name_min_length(self):
        """Test workspace name minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            WorkspaceBase(name="")

        errors = exc_info.value.errors()
        assert any("name" in str(error["loc"]) for error in errors)

    def test_workspace_name_max_length(self):
        """Test workspace name maximum length validation."""
        long_name = "A" * 256
        with pytest.raises(ValidationError) as exc_info:
            WorkspaceBase(name=long_name)

        errors = exc_info.value.errors()
        assert any("name" in str(error["loc"]) for error in errors)

    def test_workspace_name_exactly_255_chars(self):
        """Test workspace name with exactly 255 characters."""
        name_255 = "A" * 255
        workspace = WorkspaceBase(name=name_255)
        assert len(workspace.name) == 255

    @pytest.mark.parametrize("name", [
        "Simple Name",
        "Name-with-dashes",
        "Name_with_underscores",
        "Name123",
        "Name with spaces and 123",
        "éñtürnátíønál",  # Unicode characters
    ])
    def test_workspace_various_valid_names(self, name: str):
        """Test workspace creation with various valid name formats."""
        workspace = WorkspaceBase(name=name)
        assert workspace.name == name


# ============================================================================
# WORKSPACE CREATE MODEL TESTS
# ============================================================================

class TestWorkspaceCreate:
    """Test WorkspaceCreate model."""

    def test_workspace_create_valid(self):
        """Test creating WorkspaceCreate with valid data."""
        workspace = WorkspaceCreate(name="Test Workspace")
        assert workspace.name == "Test Workspace"

    def test_workspace_create_inherits_validation(self):
        """Test that WorkspaceCreate inherits WorkspaceBase validation."""
        with pytest.raises(ValidationError):
            WorkspaceCreate(name="")


# ============================================================================
# WORKSPACE UPDATE MODEL TESTS
# ============================================================================

class TestWorkspaceUpdate:
    """Test WorkspaceUpdate model."""

    def test_workspace_update_with_name(self):
        """Test updating workspace name."""
        update = WorkspaceUpdate(name="Updated Name")
        assert update.name == "Updated Name"

    def test_workspace_update_optional_name(self):
        """Test that name is optional in update."""
        update = WorkspaceUpdate()
        assert update.name is None

    def test_workspace_update_validates_name_if_provided(self):
        """Test that name validation applies if name is provided."""
        with pytest.raises(ValidationError):
            WorkspaceUpdate(name="")


# ============================================================================
# WORKSPACE RESPONSE MODEL TESTS
# ============================================================================

class TestWorkspaceResponse:
    """Test WorkspaceResponse model."""

    def test_workspace_response_valid(self):
        """Test creating WorkspaceResponse with all fields."""
        workspace_id = uuid4()
        created_at = datetime.utcnow()

        workspace = WorkspaceResponse(
            id=workspace_id,
            name="Test Workspace",
            created_at=created_at,
        )

        assert workspace.id == workspace_id
        assert workspace.name == "Test Workspace"
        assert workspace.created_at == created_at

    def test_workspace_response_uuid_validation(self):
        """Test UUID field validation."""
        with pytest.raises(ValidationError) as exc_info:
            WorkspaceResponse(
                id="not-a-uuid",
                name="Test",
                created_at=datetime.utcnow(),
            )

        errors = exc_info.value.errors()
        assert any("id" in str(error["loc"]) for error in errors)

    def test_workspace_response_datetime_validation(self):
        """Test datetime field validation."""
        workspace = WorkspaceResponse(
            id=uuid4(),
            name="Test",
            created_at="2025-10-30T10:00:00Z",  # String datetime
        )
        assert isinstance(workspace.created_at, datetime)

    def test_workspace_response_serialization(self):
        """Test model serialization to dict."""
        workspace_id = uuid4()
        workspace = WorkspaceResponse(
            id=workspace_id,
            name="Test Workspace",
            created_at=datetime.utcnow(),
        )

        data = workspace.model_dump()
        assert data["name"] == "Test Workspace"
        assert isinstance(data["id"], UUID)
        assert isinstance(data["created_at"], datetime)

    def test_workspace_response_json_serialization(self):
        """Test model serialization to JSON."""
        workspace = WorkspaceResponse(
            id=uuid4(),
            name="Test Workspace",
            created_at=datetime.utcnow(),
        )

        json_str = workspace.model_dump_json()
        assert "Test Workspace" in json_str
        assert isinstance(json_str, str)


# ============================================================================
# WORKSPACE MEMBER MODEL TESTS
# ============================================================================

class TestWorkspaceMember:
    """Test WorkspaceMember model."""

    def test_workspace_member_valid(self):
        """Test creating valid workspace member."""
        member = WorkspaceMember(
            id=uuid4(),
            workspace_id=uuid4(),
            user_id=uuid4(),
            role="admin",
            created_at=datetime.utcnow(),
        )

        assert member.role == "admin"
        assert isinstance(member.id, UUID)

    @pytest.mark.parametrize("role", ["owner", "admin", "member", "viewer", "service"])
    def test_workspace_member_valid_roles(self, role: str):
        """Test all valid member roles."""
        member = WorkspaceMember(
            id=uuid4(),
            workspace_id=uuid4(),
            user_id=uuid4(),
            role=role,
            created_at=datetime.utcnow(),
        )
        assert member.role == role

    def test_workspace_member_invalid_role(self):
        """Test invalid role raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            WorkspaceMember(
                id=uuid4(),
                workspace_id=uuid4(),
                user_id=uuid4(),
                role="superadmin",  # Invalid role
                created_at=datetime.utcnow(),
            )

        errors = exc_info.value.errors()
        assert any("role" in str(error["loc"]) for error in errors)

    def test_workspace_member_role_case_sensitive(self):
        """Test that role validation is case-sensitive."""
        with pytest.raises(ValidationError):
            WorkspaceMember(
                id=uuid4(),
                workspace_id=uuid4(),
                user_id=uuid4(),
                role="ADMIN",  # Wrong case
                created_at=datetime.utcnow(),
            )


# ============================================================================
# WORKSPACE DETAIL MODEL TESTS
# ============================================================================

class TestWorkspaceDetail:
    """Test WorkspaceDetail model."""

    def test_workspace_detail_valid(self):
        """Test creating WorkspaceDetail with all fields."""
        detail = WorkspaceDetail(
            id=uuid4(),
            name="Test Workspace",
            created_at=datetime.utcnow(),
            member_count=5,
            founder_count=2,
            integration_count=8,
        )

        assert detail.member_count == 5
        assert detail.founder_count == 2
        assert detail.integration_count == 8

    def test_workspace_detail_default_counts(self):
        """Test default values for count fields."""
        detail = WorkspaceDetail(
            id=uuid4(),
            name="Test Workspace",
            created_at=datetime.utcnow(),
        )

        assert detail.member_count == 0
        assert detail.founder_count == 0
        assert detail.integration_count == 0

    def test_workspace_detail_negative_counts(self):
        """Test that negative counts are allowed (may need future validation)."""
        # Note: Current model doesn't validate for negative numbers
        # This test documents the current behavior
        detail = WorkspaceDetail(
            id=uuid4(),
            name="Test Workspace",
            created_at=datetime.utcnow(),
            member_count=-1,
        )
        assert detail.member_count == -1


# ============================================================================
# SERIALIZATION & DESERIALIZATION TESTS
# ============================================================================

class TestSerialization:
    """Test model serialization and deserialization."""

    def test_workspace_from_dict(self):
        """Test creating workspace from dictionary."""
        data = {
            "id": str(uuid4()),
            "name": "Test Workspace",
            "created_at": "2025-10-30T10:00:00Z",
        }

        workspace = WorkspaceResponse(**data)
        assert workspace.name == "Test Workspace"

    def test_workspace_to_dict(self):
        """Test converting workspace to dictionary."""
        workspace = WorkspaceResponse(
            id=uuid4(),
            name="Test Workspace",
            created_at=datetime.utcnow(),
        )

        data = workspace.model_dump()
        assert "id" in data
        assert "name" in data
        assert "created_at" in data

    def test_workspace_json_round_trip(self):
        """Test JSON serialization and deserialization."""
        original = WorkspaceResponse(
            id=uuid4(),
            name="Test Workspace",
            created_at=datetime.utcnow(),
        )

        json_str = original.model_dump_json()
        restored = WorkspaceResponse.model_validate_json(json_str)

        assert original.name == restored.name


# ============================================================================
# PROPERTY-BASED TESTS (Using Hypothesis)
# ============================================================================

from hypothesis import given, strategies as st


class TestPropertyBased:
    """Property-based tests using Hypothesis."""

    @given(st.text(min_size=1, max_size=255))
    def test_workspace_accepts_any_valid_string(self, name: str):
        """Test workspace accepts any string within length constraints."""
        # Filter out strings that are just whitespace
        if name.strip():
            workspace = WorkspaceBase(name=name)
            assert workspace.name == name

    @given(st.text(min_size=256))
    def test_workspace_rejects_too_long_names(self, name: str):
        """Test workspace rejects names that are too long."""
        with pytest.raises(ValidationError):
            WorkspaceBase(name=name)
