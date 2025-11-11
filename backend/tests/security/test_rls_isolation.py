"""
RLS Policy Isolation Tests

This module tests Row-Level Security (RLS) policies to ensure:
1. Complete workspace isolation (no data leakage between workspaces)
2. Role-based access control works correctly
3. Founders can only access their own data
4. Admins have proper elevated permissions

Sprint 6 - Security, Testing & Launch
"""
import pytest
from uuid import uuid4, UUID
from datetime import datetime
from typing import Dict, Any, List, Optional

# Mock workspace and founder IDs for testing
WORKSPACE_A_ID = uuid4()
WORKSPACE_B_ID = uuid4()
FOUNDER_A1_ID = uuid4()
FOUNDER_A2_ID = uuid4()
FOUNDER_B1_ID = uuid4()


class MockDatabase:
    """Mock database for testing RLS policies without actual DB connection"""

    def __init__(self):
        self.current_user_id: Optional[UUID] = None
        self.workspaces: Dict[UUID, Dict[str, Any]] = {}
        self.members: List[Dict[str, Any]] = []
        self.founders: List[Dict[str, Any]] = []
        self.communications: List[Dict[str, Any]] = []
        self.meetings: List[Dict[str, Any]] = []
        self.insights: List[Dict[str, Any]] = []
        self.briefings: List[Dict[str, Any]] = []

    def set_current_user(self, user_id: UUID):
        """Simulate setting the current authenticated user"""
        self.current_user_id = user_id

    def get_user_workspaces(self) -> List[UUID]:
        """
        Simulate auth.user_workspaces() function
        Returns workspaces the current user is a member of
        """
        return [
            m["workspace_id"]
            for m in self.members
            if m["user_id"] == self.current_user_id
        ]

    def has_workspace_role(self, workspace_id: UUID, role: str) -> bool:
        """
        Simulate auth.has_workspace_role() function
        Check if user has specific role in workspace
        """
        user_workspaces = self.get_user_workspaces()
        if workspace_id not in user_workspaces:
            return False

        for member in self.members:
            if (
                member["user_id"] == self.current_user_id
                and member["workspace_id"] == workspace_id
            ):
                # Owners always have all permissions
                if member["role"] == "owner":
                    return True
                return member["role"] == role

        return False

    def is_workspace_admin(self, workspace_id: UUID) -> bool:
        """
        Simulate auth.is_workspace_admin() function
        Check if user is owner or admin
        """
        return self.has_workspace_role(workspace_id, "owner") or self.has_workspace_role(
            workspace_id, "admin"
        )

    def get_founder_id(self, workspace_id: UUID) -> Optional[UUID]:
        """
        Simulate auth.get_founder_id() function
        Get founder_id for current user in workspace
        """
        for founder in self.founders:
            if (
                founder["user_id"] == self.current_user_id
                and founder["workspace_id"] == workspace_id
            ):
                return founder["id"]
        return None

    def apply_rls_filter(
        self, items: List[Dict[str, Any]], filter_type: str = "workspace"
    ) -> List[Dict[str, Any]]:
        """
        Apply RLS filter to items based on workspace membership
        """
        user_workspaces = self.get_user_workspaces()

        if filter_type == "workspace":
            return [item for item in items if item.get("workspace_id") in user_workspaces]
        elif filter_type == "founder":
            filtered = []
            for item in items:
                workspace_id = item.get("workspace_id")
                if workspace_id not in user_workspaces:
                    continue

                # Allow if user is founder of this item
                founder_id = self.get_founder_id(workspace_id)
                if item.get("founder_id") == founder_id:
                    filtered.append(item)
                # Allow if user is admin
                elif self.is_workspace_admin(workspace_id):
                    filtered.append(item)

            return filtered

        return []


@pytest.fixture
def mock_db():
    """Create a mock database with test data"""
    db = MockDatabase()

    # Create test data for two isolated workspaces
    # Workspace A
    user_a1_id = uuid4()
    user_a2_id = uuid4()

    db.workspaces[WORKSPACE_A_ID] = {
        "id": WORKSPACE_A_ID,
        "name": "Workspace A",
        "created_at": datetime.utcnow(),
    }

    db.members.extend(
        [
            {
                "id": uuid4(),
                "workspace_id": WORKSPACE_A_ID,
                "user_id": user_a1_id,
                "role": "owner",
            },
            {
                "id": uuid4(),
                "workspace_id": WORKSPACE_A_ID,
                "user_id": user_a2_id,
                "role": "member",
            },
        ]
    )

    db.founders.extend(
        [
            {
                "id": FOUNDER_A1_ID,
                "workspace_id": WORKSPACE_A_ID,
                "user_id": user_a1_id,
                "name": "Founder A1",
            },
            {
                "id": FOUNDER_A2_ID,
                "workspace_id": WORKSPACE_A_ID,
                "user_id": user_a2_id,
                "name": "Founder A2",
            },
        ]
    )

    # Workspace B
    user_b1_id = uuid4()

    db.workspaces[WORKSPACE_B_ID] = {
        "id": WORKSPACE_B_ID,
        "name": "Workspace B",
        "created_at": datetime.utcnow(),
    }

    db.members.append(
        {
            "id": uuid4(),
            "workspace_id": WORKSPACE_B_ID,
            "user_id": user_b1_id,
            "role": "owner",
        }
    )

    db.founders.append(
        {
            "id": FOUNDER_B1_ID,
            "workspace_id": WORKSPACE_B_ID,
            "user_id": user_b1_id,
            "name": "Founder B1",
        }
    )

    # Add communications data
    db.communications.extend(
        [
            {
                "id": uuid4(),
                "workspace_id": WORKSPACE_A_ID,
                "founder_id": FOUNDER_A1_ID,
                "platform": "slack",
                "content": "Message in workspace A",
            },
            {
                "id": uuid4(),
                "workspace_id": WORKSPACE_B_ID,
                "founder_id": FOUNDER_B1_ID,
                "platform": "slack",
                "content": "Message in workspace B",
            },
        ]
    )

    # Add meetings data
    db.meetings.extend(
        [
            {
                "id": uuid4(),
                "workspace_id": WORKSPACE_A_ID,
                "founder_id": FOUNDER_A1_ID,
                "title": "Meeting in workspace A",
            },
            {
                "id": uuid4(),
                "workspace_id": WORKSPACE_B_ID,
                "founder_id": FOUNDER_B1_ID,
                "title": "Meeting in workspace B",
            },
        ]
    )

    # Add insights data
    db.insights.extend(
        [
            {
                "id": uuid4(),
                "workspace_id": WORKSPACE_A_ID,
                "founder_id": FOUNDER_A1_ID,
                "type": "kpi",
                "content": {"metric": "revenue", "value": 100000},
            },
            {
                "id": uuid4(),
                "workspace_id": WORKSPACE_B_ID,
                "founder_id": FOUNDER_B1_ID,
                "type": "kpi",
                "content": {"metric": "revenue", "value": 50000},
            },
        ]
    )

    # Add briefings data
    db.briefings.extend(
        [
            {
                "id": uuid4(),
                "workspace_id": WORKSPACE_A_ID,
                "founder_id": FOUNDER_A1_ID,
                "briefing_type": "morning",
                "content": {"summary": "Morning brief for workspace A"},
            },
            {
                "id": uuid4(),
                "workspace_id": WORKSPACE_B_ID,
                "founder_id": FOUNDER_B1_ID,
                "briefing_type": "morning",
                "content": {"summary": "Morning brief for workspace B"},
            },
        ]
    )

    # Store user IDs for testing
    db.user_a1_id = user_a1_id
    db.user_a2_id = user_a2_id
    db.user_b1_id = user_b1_id

    return db


class TestWorkspaceIsolation:
    """Test workspace-level isolation"""

    def test_user_can_only_see_own_workspace_communications(self, mock_db):
        """Users in workspace A should not see workspace B communications"""
        # User from workspace A
        mock_db.set_current_user(mock_db.user_a1_id)
        filtered = mock_db.apply_rls_filter(mock_db.communications, "workspace")

        assert len(filtered) == 1
        assert filtered[0]["workspace_id"] == WORKSPACE_A_ID
        assert "workspace A" in filtered[0]["content"]

    def test_user_cannot_see_other_workspace_communications(self, mock_db):
        """Users in workspace B should not see workspace A communications"""
        # User from workspace B
        mock_db.set_current_user(mock_db.user_b1_id)
        filtered = mock_db.apply_rls_filter(mock_db.communications, "workspace")

        assert len(filtered) == 1
        assert filtered[0]["workspace_id"] == WORKSPACE_B_ID
        assert "workspace B" in filtered[0]["content"]

    def test_workspace_isolation_meetings(self, mock_db):
        """Test meeting data isolation between workspaces"""
        # User A1
        mock_db.set_current_user(mock_db.user_a1_id)
        filtered_a = mock_db.apply_rls_filter(mock_db.meetings, "workspace")

        assert len(filtered_a) == 1
        assert filtered_a[0]["workspace_id"] == WORKSPACE_A_ID

        # User B1
        mock_db.set_current_user(mock_db.user_b1_id)
        filtered_b = mock_db.apply_rls_filter(mock_db.meetings, "workspace")

        assert len(filtered_b) == 1
        assert filtered_b[0]["workspace_id"] == WORKSPACE_B_ID

        # Verify no overlap
        assert filtered_a[0]["id"] != filtered_b[0]["id"]

    def test_workspace_isolation_insights(self, mock_db):
        """Test insight data isolation between workspaces"""
        # User A1 - should see $100k revenue
        mock_db.set_current_user(mock_db.user_a1_id)
        filtered_a = mock_db.apply_rls_filter(mock_db.insights, "workspace")

        assert len(filtered_a) == 1
        assert filtered_a[0]["content"]["value"] == 100000

        # User B1 - should see $50k revenue
        mock_db.set_current_user(mock_db.user_b1_id)
        filtered_b = mock_db.apply_rls_filter(mock_db.insights, "workspace")

        assert len(filtered_b) == 1
        assert filtered_b[0]["content"]["value"] == 50000

    def test_workspace_isolation_briefings(self, mock_db):
        """Test briefing data isolation between workspaces"""
        # User A1
        mock_db.set_current_user(mock_db.user_a1_id)
        filtered_a = mock_db.apply_rls_filter(mock_db.briefings, "workspace")

        assert len(filtered_a) == 1
        assert "workspace A" in filtered_a[0]["content"]["summary"]

        # User B1
        mock_db.set_current_user(mock_db.user_b1_id)
        filtered_b = mock_db.apply_rls_filter(mock_db.briefings, "workspace")

        assert len(filtered_b) == 1
        assert "workspace B" in filtered_b[0]["content"]["summary"]


class TestFounderIsolation:
    """Test founder-level isolation within workspaces"""

    def test_founder_can_see_own_communications(self, mock_db):
        """Founders can see their own communications"""
        mock_db.set_current_user(mock_db.user_a1_id)
        filtered = mock_db.apply_rls_filter(mock_db.communications, "founder")

        assert len(filtered) == 1
        assert filtered[0]["founder_id"] == FOUNDER_A1_ID

    def test_non_admin_cannot_see_other_founder_data(self, mock_db):
        """Non-admin members cannot see other founders' data in same workspace"""
        # User A2 is a member (not admin) in workspace A
        mock_db.set_current_user(mock_db.user_a2_id)

        # Should not see Founder A1's communications
        filtered = mock_db.apply_rls_filter(mock_db.communications, "founder")

        # User A2 has no communications, so should see empty list
        assert len(filtered) == 0


class TestRoleBasedAccess:
    """Test role-based access control"""

    def test_owner_has_admin_privileges(self, mock_db):
        """Owners should have admin privileges"""
        mock_db.set_current_user(mock_db.user_a1_id)

        assert mock_db.is_workspace_admin(WORKSPACE_A_ID) is True
        assert mock_db.has_workspace_role(WORKSPACE_A_ID, "owner") is True

    def test_member_lacks_admin_privileges(self, mock_db):
        """Regular members should not have admin privileges"""
        mock_db.set_current_user(mock_db.user_a2_id)

        assert mock_db.is_workspace_admin(WORKSPACE_A_ID) is False
        assert mock_db.has_workspace_role(WORKSPACE_A_ID, "member") is True
        assert mock_db.has_workspace_role(WORKSPACE_A_ID, "owner") is False

    def test_user_has_no_access_to_other_workspace(self, mock_db):
        """Users should have no access to workspaces they're not members of"""
        mock_db.set_current_user(mock_db.user_a1_id)

        # User A1 should not have any role in workspace B
        assert mock_db.is_workspace_admin(WORKSPACE_B_ID) is False
        assert mock_db.has_workspace_role(WORKSPACE_B_ID, "owner") is False
        assert mock_db.has_workspace_role(WORKSPACE_B_ID, "member") is False

    def test_get_founder_id_returns_correct_id(self, mock_db):
        """get_founder_id should return correct founder ID for user in workspace"""
        mock_db.set_current_user(mock_db.user_a1_id)

        founder_id = mock_db.get_founder_id(WORKSPACE_A_ID)
        assert founder_id == FOUNDER_A1_ID

        # Should return None for workspace user is not in
        founder_id_b = mock_db.get_founder_id(WORKSPACE_B_ID)
        assert founder_id_b is None


class TestCrossWorkspaceLeakage:
    """Test for potential data leakage across workspaces"""

    def test_no_leakage_in_communications(self, mock_db):
        """Ensure no communication leakage between workspaces"""
        # Check workspace A user
        mock_db.set_current_user(mock_db.user_a1_id)
        filtered_a = mock_db.apply_rls_filter(mock_db.communications, "workspace")

        # Should only see workspace A data
        workspace_ids_a = {comm["workspace_id"] for comm in filtered_a}
        assert workspace_ids_a == {WORKSPACE_A_ID}
        assert WORKSPACE_B_ID not in workspace_ids_a

        # Check workspace B user
        mock_db.set_current_user(mock_db.user_b1_id)
        filtered_b = mock_db.apply_rls_filter(mock_db.communications, "workspace")

        # Should only see workspace B data
        workspace_ids_b = {comm["workspace_id"] for comm in filtered_b}
        assert workspace_ids_b == {WORKSPACE_B_ID}
        assert WORKSPACE_A_ID not in workspace_ids_b

    def test_no_leakage_in_meetings(self, mock_db):
        """Ensure no meeting leakage between workspaces"""
        mock_db.set_current_user(mock_db.user_a1_id)
        filtered_a = mock_db.apply_rls_filter(mock_db.meetings, "workspace")

        mock_db.set_current_user(mock_db.user_b1_id)
        filtered_b = mock_db.apply_rls_filter(mock_db.meetings, "workspace")

        # No overlap in meeting IDs
        ids_a = {m["id"] for m in filtered_a}
        ids_b = {m["id"] for m in filtered_b}
        assert ids_a.isdisjoint(ids_b)

    def test_no_leakage_in_insights(self, mock_db):
        """Ensure no insight leakage between workspaces"""
        mock_db.set_current_user(mock_db.user_a1_id)
        filtered_a = mock_db.apply_rls_filter(mock_db.insights, "workspace")

        mock_db.set_current_user(mock_db.user_b1_id)
        filtered_b = mock_db.apply_rls_filter(mock_db.insights, "workspace")

        # Verify different revenue values (no leakage)
        revenue_a = filtered_a[0]["content"]["value"]
        revenue_b = filtered_b[0]["content"]["value"]
        assert revenue_a != revenue_b
        assert revenue_a == 100000
        assert revenue_b == 50000

    def test_no_leakage_in_briefings(self, mock_db):
        """Ensure no briefing leakage between workspaces"""
        mock_db.set_current_user(mock_db.user_a1_id)
        filtered_a = mock_db.apply_rls_filter(mock_db.briefings, "workspace")

        mock_db.set_current_user(mock_db.user_b1_id)
        filtered_b = mock_db.apply_rls_filter(mock_db.briefings, "workspace")

        # Verify different briefing content (no leakage)
        summary_a = filtered_a[0]["content"]["summary"]
        summary_b = filtered_b[0]["content"]["summary"]
        assert "workspace A" in summary_a
        assert "workspace B" in summary_b
        assert summary_a != summary_b


class TestSecurityEdgeCases:
    """Test security edge cases and potential attack vectors"""

    def test_unauthenticated_user_sees_nothing(self, mock_db):
        """Unauthenticated users (current_user_id = None) should see no data"""
        mock_db.set_current_user(None)

        filtered_comms = mock_db.apply_rls_filter(mock_db.communications, "workspace")
        filtered_meetings = mock_db.apply_rls_filter(mock_db.meetings, "workspace")
        filtered_insights = mock_db.apply_rls_filter(mock_db.insights, "workspace")

        assert len(filtered_comms) == 0
        assert len(filtered_meetings) == 0
        assert len(filtered_insights) == 0

    def test_deleted_member_loses_access(self, mock_db):
        """When a member is removed, they should lose access"""
        # Initially user A2 has access
        mock_db.set_current_user(mock_db.user_a2_id)
        assert len(mock_db.get_user_workspaces()) == 1

        # Remove user A2 from workspace A
        mock_db.members = [
            m for m in mock_db.members if m["user_id"] != mock_db.user_a2_id
        ]

        # User A2 should now have no access
        assert len(mock_db.get_user_workspaces()) == 0
        filtered = mock_db.apply_rls_filter(mock_db.communications, "workspace")
        assert len(filtered) == 0

    def test_cannot_access_with_random_workspace_id(self, mock_db):
        """Users cannot access data by guessing workspace IDs"""
        random_workspace_id = uuid4()

        mock_db.set_current_user(mock_db.user_a1_id)

        # Add fake data with random workspace ID
        fake_comm = {
            "id": uuid4(),
            "workspace_id": random_workspace_id,
            "founder_id": uuid4(),
            "content": "Secret data",
        }
        mock_db.communications.append(fake_comm)

        # User A1 should not see this data
        filtered = mock_db.apply_rls_filter(mock_db.communications, "workspace")

        # Should only see original workspace A communication
        assert len(filtered) == 1
        assert filtered[0]["workspace_id"] == WORKSPACE_A_ID
        assert "Secret data" not in filtered[0]["content"]
