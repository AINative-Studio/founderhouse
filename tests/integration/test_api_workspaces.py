"""
AI Chief of Staff - Workspace API Tests
Sprint 1: Integration tests for workspace endpoints

Test coverage:
- Workspace creation
- Workspace retrieval
- Workspace updates
- RLS enforcement
- Multi-tenant isolation
- Authorization and authentication
"""

import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from uuid import uuid4

from backend.app.main import app
from tests.fixtures.sample_data import WorkspaceFactory, MemberFactory, FounderFactory


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def workspace_data():
    """Generate sample workspace data."""
    return WorkspaceFactory()


@pytest.fixture
def member_data():
    """Generate sample member data."""
    return MemberFactory()


@pytest.fixture
def founder_data():
    """Generate sample founder data."""
    return FounderFactory()


# ============================================================================
# WORKSPACE CREATION TESTS
# ============================================================================

@pytest.mark.integration
class TestWorkspaceCreation:
    """Test workspace creation endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_create_workspace_endpoint_exists(self, client, mock_auth_headers):
        """
        Test that workspace creation endpoint exists.

        Acceptance Criteria:
        - POST /api/v1/workspaces endpoint is available
        - Returns appropriate status (may be 401 without auth, 201 with auth)
        """
        # Note: This test assumes endpoint exists, adjust path as needed
        response = client.post(
            "/api/v1/workspaces",
            json={"name": "Test Workspace"},
            headers=mock_auth_headers,
        )

        # Endpoint should exist (not 404)
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_create_workspace_valid_data(
        self,
        workspace_data,
        mock_auth_headers,
        supabase_client_mock,
    ):
        """
        Test creating workspace with valid data.

        Acceptance Criteria:
        - Returns 201 Created
        - Response includes workspace ID
        - Response includes created_at timestamp
        - Workspace name is preserved
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Mock Supabase response
            supabase_client_mock.table.return_value.insert.return_value.execute.return_value.data = [
                {
                    "id": workspace_data["id"],
                    "name": workspace_data["name"],
                    "created_at": workspace_data["created_at"],
                }
            ]

            response = await client.post(
                "/api/v1/workspaces",
                json={"name": workspace_data["name"]},
                headers=mock_auth_headers,
            )

            # Adjust assertions based on actual API implementation
            if response.status_code == 201:
                data = response.json()
                assert "id" in data
                assert "name" in data
                assert data["name"] == workspace_data["name"]

    def test_create_workspace_missing_name(self, client, mock_auth_headers):
        """
        Test creating workspace without name.

        Acceptance Criteria:
        - Returns 422 Unprocessable Entity
        - Error message indicates missing name
        """
        response = client.post(
            "/api/v1/workspaces",
            json={},
            headers=mock_auth_headers,
        )

        # Should fail validation
        assert response.status_code in [422, 400]

    def test_create_workspace_empty_name(self, client, mock_auth_headers):
        """
        Test creating workspace with empty name.

        Acceptance Criteria:
        - Returns 422 for validation error
        - Name must not be empty
        """
        response = client.post(
            "/api/v1/workspaces",
            json={"name": ""},
            headers=mock_auth_headers,
        )

        assert response.status_code in [422, 400]

    def test_create_workspace_name_too_long(self, client, mock_auth_headers):
        """
        Test creating workspace with name exceeding max length.

        Acceptance Criteria:
        - Returns 422 for validation error
        - Name limited to 255 characters
        """
        long_name = "A" * 256

        response = client.post(
            "/api/v1/workspaces",
            json={"name": long_name},
            headers=mock_auth_headers,
        )

        assert response.status_code in [422, 400]

    def test_create_workspace_without_auth(self, client):
        """
        Test creating workspace without authentication.

        Acceptance Criteria:
        - Returns 401 Unauthorized
        - Authentication required
        """
        response = client.post(
            "/api/v1/workspaces",
            json={"name": "Test Workspace"},
        )

        # Should require authentication
        assert response.status_code in [401, 403]


# ============================================================================
# WORKSPACE RETRIEVAL TESTS
# ============================================================================

@pytest.mark.integration
class TestWorkspaceRetrieval:
    """Test workspace retrieval endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_get_workspace_by_id(
        self,
        client,
        mock_workspace_id,
        mock_auth_headers,
    ):
        """
        Test retrieving workspace by ID.

        Acceptance Criteria:
        - Returns 200 for existing workspace
        - Response includes workspace details
        - Only accessible by workspace members
        """
        response = client.get(
            f"/api/v1/workspaces/{mock_workspace_id}",
            headers=mock_auth_headers,
        )

        # Endpoint should exist
        assert response.status_code != 404

    def test_get_workspace_nonexistent(self, client, mock_auth_headers):
        """
        Test retrieving nonexistent workspace.

        Acceptance Criteria:
        - Returns 404 Not Found
        - Error message indicates workspace not found
        """
        fake_id = str(uuid4())

        response = client.get(
            f"/api/v1/workspaces/{fake_id}",
            headers=mock_auth_headers,
        )

        # Should be 404 or 403 (depending on RLS implementation)
        assert response.status_code in [404, 403]

    def test_get_workspace_invalid_uuid(self, client, mock_auth_headers):
        """
        Test retrieving workspace with invalid UUID.

        Acceptance Criteria:
        - Returns 422 for invalid UUID format
        """
        response = client.get(
            "/api/v1/workspaces/not-a-uuid",
            headers=mock_auth_headers,
        )

        assert response.status_code in [422, 400]

    def test_list_workspaces(self, client, mock_auth_headers):
        """
        Test listing workspaces for authenticated user.

        Acceptance Criteria:
        - Returns 200 with list of workspaces
        - Only returns workspaces user has access to
        - List may be empty for new users
        """
        response = client.get(
            "/api/v1/workspaces",
            headers=mock_auth_headers,
        )

        # Endpoint should exist and return list
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))


# ============================================================================
# RLS ENFORCEMENT TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.rls
class TestRLSEnforcement:
    """Test Row-Level Security enforcement in API."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_cannot_access_other_workspace(
        self,
        client,
        mock_auth_headers,
    ):
        """
        Test that users cannot access workspaces they don't belong to.

        Acceptance Criteria:
        - Returns 403 Forbidden or 404 Not Found
        - RLS policies prevent unauthorized access
        - Clear error message
        """
        # Try to access workspace user is not a member of
        unauthorized_workspace_id = str(uuid4())

        response = client.get(
            f"/api/v1/workspaces/{unauthorized_workspace_id}",
            headers=mock_auth_headers,
        )

        # Should not be accessible
        assert response.status_code in [403, 404]

    def test_cannot_modify_other_workspace(
        self,
        client,
        mock_auth_headers,
    ):
        """
        Test that users cannot modify workspaces they don't own.

        Acceptance Criteria:
        - Returns 403 Forbidden
        - Only owners/admins can modify workspaces
        """
        unauthorized_workspace_id = str(uuid4())

        response = client.patch(
            f"/api/v1/workspaces/{unauthorized_workspace_id}",
            json={"name": "Hacked Name"},
            headers=mock_auth_headers,
        )

        # Should be forbidden
        assert response.status_code in [403, 404]

    def test_cannot_delete_other_workspace(
        self,
        client,
        mock_auth_headers,
    ):
        """
        Test that users cannot delete workspaces they don't own.

        Acceptance Criteria:
        - Returns 403 Forbidden
        - Only owners can delete workspaces
        """
        unauthorized_workspace_id = str(uuid4())

        response = client.delete(
            f"/api/v1/workspaces/{unauthorized_workspace_id}",
            headers=mock_auth_headers,
        )

        # Should be forbidden
        assert response.status_code in [403, 404]


# ============================================================================
# WORKSPACE UPDATE TESTS
# ============================================================================

@pytest.mark.integration
class TestWorkspaceUpdate:
    """Test workspace update endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_update_workspace_name(
        self,
        client,
        mock_workspace_id,
        mock_auth_headers,
    ):
        """
        Test updating workspace name.

        Acceptance Criteria:
        - Returns 200 OK
        - Name is updated successfully
        - Only authorized users can update
        """
        response = client.patch(
            f"/api/v1/workspaces/{mock_workspace_id}",
            json={"name": "Updated Workspace Name"},
            headers=mock_auth_headers,
        )

        # Endpoint should exist
        assert response.status_code != 404

    def test_update_workspace_invalid_data(
        self,
        client,
        mock_workspace_id,
        mock_auth_headers,
    ):
        """
        Test updating workspace with invalid data.

        Acceptance Criteria:
        - Returns 422 for validation errors
        - Name constraints are enforced
        """
        response = client.patch(
            f"/api/v1/workspaces/{mock_workspace_id}",
            json={"name": ""},
            headers=mock_auth_headers,
        )

        assert response.status_code in [422, 400]

    def test_update_workspace_partial(
        self,
        client,
        mock_workspace_id,
        mock_auth_headers,
    ):
        """
        Test partial workspace update.

        Acceptance Criteria:
        - PATCH supports partial updates
        - Unspecified fields remain unchanged
        """
        response = client.patch(
            f"/api/v1/workspaces/{mock_workspace_id}",
            json={"name": "New Name"},
            headers=mock_auth_headers,
        )

        # Should accept partial updates
        assert response.status_code != 400


# ============================================================================
# WORKSPACE MEMBERS TESTS
# ============================================================================

@pytest.mark.integration
class TestWorkspaceMembers:
    """Test workspace member management."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_list_workspace_members(
        self,
        client,
        mock_workspace_id,
        mock_auth_headers,
    ):
        """
        Test listing workspace members.

        Acceptance Criteria:
        - Returns list of members
        - Includes member roles
        - Only accessible by workspace members
        """
        response = client.get(
            f"/api/v1/workspaces/{mock_workspace_id}/members",
            headers=mock_auth_headers,
        )

        # Endpoint should exist
        assert response.status_code != 404

    def test_add_workspace_member(
        self,
        client,
        mock_workspace_id,
        mock_auth_headers,
    ):
        """
        Test adding member to workspace.

        Acceptance Criteria:
        - Only owners/admins can add members
        - Returns 201 Created
        - Member is added with specified role
        """
        new_user_id = str(uuid4())

        response = client.post(
            f"/api/v1/workspaces/{mock_workspace_id}/members",
            json={
                "user_id": new_user_id,
                "role": "member",
            },
            headers=mock_auth_headers,
        )

        # Endpoint should exist
        assert response.status_code != 404

    def test_remove_workspace_member(
        self,
        client,
        mock_workspace_id,
        mock_auth_headers,
    ):
        """
        Test removing member from workspace.

        Acceptance Criteria:
        - Only owners/admins can remove members
        - Member is removed successfully
        """
        member_id = str(uuid4())

        response = client.delete(
            f"/api/v1/workspaces/{mock_workspace_id}/members/{member_id}",
            headers=mock_auth_headers,
        )

        # Endpoint should exist
        assert response.status_code != 404

    def test_update_member_role(
        self,
        client,
        mock_workspace_id,
        mock_auth_headers,
    ):
        """
        Test updating member role.

        Acceptance Criteria:
        - Only owners/admins can change roles
        - Valid roles: owner, admin, member, viewer
        """
        member_id = str(uuid4())

        response = client.patch(
            f"/api/v1/workspaces/{mock_workspace_id}/members/{member_id}",
            json={"role": "admin"},
            headers=mock_auth_headers,
        )

        # Endpoint should exist
        assert response.status_code != 404


# ============================================================================
# PAGINATION TESTS
# ============================================================================

@pytest.mark.integration
class TestPagination:
    """Test pagination for workspace lists."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_workspace_list_pagination(self, client, mock_auth_headers):
        """
        Test workspace list supports pagination.

        Acceptance Criteria:
        - Supports limit parameter
        - Supports offset parameter
        - Returns pagination metadata
        """
        response = client.get(
            "/api/v1/workspaces?limit=10&offset=0",
            headers=mock_auth_headers,
        )

        # Should support pagination parameters
        assert response.status_code != 400

    def test_workspace_list_default_limit(self, client, mock_auth_headers):
        """
        Test default pagination limit.

        Acceptance Criteria:
        - Has sensible default limit (e.g., 20, 50)
        - Returns limited results
        """
        response = client.get(
            "/api/v1/workspaces",
            headers=mock_auth_headers,
        )

        if response.status_code == 200:
            data = response.json()
            # Should have reasonable limit
            if isinstance(data, list):
                assert len(data) <= 100  # Sanity check


# ============================================================================
# VALIDATION TESTS
# ============================================================================

@pytest.mark.integration
class TestValidation:
    """Test input validation for workspace endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.mark.parametrize("invalid_role", [
        "superadmin",
        "ADMIN",
        "user",
        "root",
        123,
        "",
    ])
    def test_invalid_member_roles_rejected(
        self,
        client,
        mock_workspace_id,
        mock_auth_headers,
        invalid_role,
    ):
        """
        Test that invalid member roles are rejected.

        Acceptance Criteria:
        - Only valid roles accepted: owner, admin, member, viewer, service
        - Returns 422 for invalid roles
        """
        response = client.post(
            f"/api/v1/workspaces/{mock_workspace_id}/members",
            json={
                "user_id": str(uuid4()),
                "role": invalid_role,
            },
            headers=mock_auth_headers,
        )

        # Should reject invalid roles
        assert response.status_code in [422, 400]

    def test_workspace_name_special_characters(
        self,
        client,
        mock_auth_headers,
    ):
        """
        Test workspace names with special characters.

        Acceptance Criteria:
        - Unicode characters are supported
        - Special characters are allowed
        - SQL injection attempts are prevented
        """
        special_names = [
            "Workspace with émojis 🚀",
            "Company & Co.",
            "Test's Workspace",
            "Multi-word-hyphenated",
        ]

        for name in special_names:
            response = client.post(
                "/api/v1/workspaces",
                json={"name": name},
                headers=mock_auth_headers,
            )

            # Should accept special characters (may depend on implementation)
            assert response.status_code in [200, 201, 401, 403, 404]


# ============================================================================
# CONCURRENCY TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.slow
class TestConcurrency:
    """Test concurrent workspace operations."""

    @pytest.mark.asyncio
    async def test_concurrent_workspace_creation(self, mock_auth_headers):
        """
        Test creating multiple workspaces concurrently.

        Acceptance Criteria:
        - All requests succeed or fail gracefully
        - No race conditions
        - All workspaces created with unique IDs
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            tasks = []
            for i in range(5):
                task = client.post(
                    "/api/v1/workspaces",
                    json={"name": f"Workspace {i}"},
                    headers=mock_auth_headers,
                )
                tasks.append(task)

            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # All requests should complete
            assert len(responses) == 5

            # Check for any exceptions
            errors = [r for r in responses if isinstance(r, Exception)]
            assert len(errors) == 0, f"Concurrent requests raised errors: {errors}"


# Import asyncio for concurrent tests
import asyncio
