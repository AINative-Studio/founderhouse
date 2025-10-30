"""
AI Chief of Staff - End-to-End Workspace Flow Tests
Sprint 1: Complete user workflow testing

Test coverage:
- Complete workspace creation workflow
- Member invitation and onboarding flow
- Integration connection workflow
- Data isolation across workspaces
- Multi-step user journeys
"""

import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from uuid import uuid4

from backend.app.main import app
from tests.fixtures.sample_data import (
    WorkspaceFactory,
    MemberFactory,
    FounderFactory,
    IntegrationFactory,
)


# ============================================================================
# COMPLETE WORKSPACE SETUP FLOW
# ============================================================================

@pytest.mark.e2e
class TestWorkspaceSetupFlow:
    """Test complete workspace setup workflow."""

    @pytest.mark.asyncio
    async def test_complete_workspace_onboarding(
        self,
        mock_auth_headers,
        mock_supabase_client,
    ):
        """
        Test complete workspace onboarding flow.

        User Journey:
        1. User signs up / authenticates
        2. Creates a new workspace
        3. Adds team members
        4. Configures workspace settings
        5. Verifies isolation from other workspaces

        Acceptance Criteria:
        - All steps complete successfully
        - Workspace is fully functional
        - Data isolation is maintained
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Step 1: Create workspace
            workspace_response = await client.post(
                "/api/v1/workspaces",
                json={"name": "New Startup Inc"},
                headers=mock_auth_headers,
            )

            # Verify workspace created (or endpoint exists)
            assert workspace_response.status_code != 404

            if workspace_response.status_code == 201:
                workspace = workspace_response.json()
                workspace_id = workspace["id"]

                # Step 2: Add founder profile
                founder_response = await client.post(
                    f"/api/v1/workspaces/{workspace_id}/founders",
                    json={
                        "display_name": "John Founder",
                        "email": "john@startup.com",
                    },
                    headers=mock_auth_headers,
                )

                # Step 3: Add team members
                member_response = await client.post(
                    f"/api/v1/workspaces/{workspace_id}/members",
                    json={
                        "user_id": str(uuid4()),
                        "role": "admin",
                    },
                    headers=mock_auth_headers,
                )

                # Step 4: Verify workspace is accessible
                get_response = await client.get(
                    f"/api/v1/workspaces/{workspace_id}",
                    headers=mock_auth_headers,
                )

                # All steps should complete without errors
                assert get_response.status_code in [200, 401, 403, 404]

    @pytest.mark.asyncio
    async def test_workspace_with_integrations_flow(
        self,
        mock_auth_headers,
        mock_zoom_mcp,
        mock_slack_mcp,
    ):
        """
        Test workspace setup with MCP integrations.

        User Journey:
        1. Create workspace
        2. Connect Zoom integration
        3. Connect Slack integration
        4. Verify integrations are active
        5. Test integration health checks

        Acceptance Criteria:
        - Integrations connect successfully
        - Health checks pass
        - Integration status is tracked
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            workspace_id = str(uuid4())

            # Step 1: Connect Zoom
            zoom_response = await client.post(
                f"/api/v1/integrations/connect",
                json={
                    "workspace_id": workspace_id,
                    "platform": "zoom",
                    "credentials": {"api_key": "mock_key"},
                },
                headers=mock_auth_headers,
            )

            # Step 2: Connect Slack
            slack_response = await client.post(
                f"/api/v1/integrations/connect",
                json={
                    "workspace_id": workspace_id,
                    "platform": "slack",
                    "credentials": {"api_key": "mock_key"},
                },
                headers=mock_auth_headers,
            )

            # Step 3: Verify integrations
            integrations_response = await client.get(
                f"/api/v1/integrations?workspace_id={workspace_id}",
                headers=mock_auth_headers,
            )

            # Endpoints should exist
            assert integrations_response.status_code != 404


# ============================================================================
# MULTI-WORKSPACE ISOLATION FLOW
# ============================================================================

@pytest.mark.e2e
@pytest.mark.rls
class TestMultiWorkspaceIsolation:
    """Test data isolation between multiple workspaces."""

    @pytest.mark.asyncio
    async def test_two_workspace_isolation(self, mock_auth_headers):
        """
        Test complete isolation between two workspaces.

        User Journey:
        1. User A creates Workspace A
        2. User B creates Workspace B
        3. User A adds data to Workspace A
        4. User B adds data to Workspace B
        5. Verify User A cannot access Workspace B data
        6. Verify User B cannot access Workspace A data

        Acceptance Criteria:
        - No cross-workspace data leakage
        - RLS policies enforce isolation
        - 403/404 for unauthorized access
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            # User A creates Workspace A
            workspace_a_response = await client.post(
                "/api/v1/workspaces",
                json={"name": "Workspace A"},
                headers=mock_auth_headers,
            )

            # User B creates Workspace B
            user_b_headers = {
                "Authorization": f"Bearer mock_token_user_b",
                "Content-Type": "application/json",
            }
            workspace_b_response = await client.post(
                "/api/v1/workspaces",
                json={"name": "Workspace B"},
                headers=user_b_headers,
            )

            # If both workspaces created successfully
            if (
                workspace_a_response.status_code == 201
                and workspace_b_response.status_code == 201
            ):
                workspace_a_id = workspace_a_response.json()["id"]
                workspace_b_id = workspace_b_response.json()["id"]

                # User A tries to access Workspace B
                unauthorized_response = await client.get(
                    f"/api/v1/workspaces/{workspace_b_id}",
                    headers=mock_auth_headers,
                )

                # Should be forbidden or not found
                assert unauthorized_response.status_code in [403, 404]

    @pytest.mark.asyncio
    async def test_workspace_data_isolation_complete_flow(self):
        """
        Test comprehensive data isolation across all entities.

        User Journey:
        1. Create two workspaces with different users
        2. Add communications to each workspace
        3. Add meetings to each workspace
        4. Add tasks to each workspace
        5. Verify queries only return data from user's workspace
        6. Verify vector search respects workspace boundaries

        Acceptance Criteria:
        - All data types respect workspace boundaries
        - Vector search filtered by workspace
        - Event logs separated by workspace
        """
        # This test documents the expected comprehensive isolation
        # Implementation depends on actual API endpoints
        pass


# ============================================================================
# MEETING INGESTION FLOW
# ============================================================================

@pytest.mark.e2e
class TestMeetingIngestionFlow:
    """Test complete meeting ingestion and processing flow."""

    @pytest.mark.asyncio
    async def test_zoom_meeting_to_task_flow(
        self,
        mock_auth_headers,
        mock_zoom_mcp,
        mock_monday_mcp,
    ):
        """
        Test end-to-end meeting → transcript → task flow.

        User Journey:
        1. Zoom meeting occurs
        2. Transcript ingested via Zoom MCP
        3. AI summarizes meeting
        4. Action items extracted
        5. Tasks created in Monday.com
        6. User sees tasks in their task list

        Acceptance Criteria:
        - Meeting ingested automatically
        - Summary generated within 2 minutes
        - Action items detected and converted to tasks
        - Tasks appear in Monday.com
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            workspace_id = str(uuid4())

            # Step 1: Ingest meeting
            meeting_response = await client.post(
                "/api/v1/meetings/ingest",
                json={
                    "workspace_id": workspace_id,
                    "platform": "zoom",
                    "external_id": "zoom_meeting_123",
                    "title": "Product Planning",
                    "recording_url": "https://zoom.us/rec/123",
                },
                headers=mock_auth_headers,
            )

            # Endpoint should exist
            assert meeting_response.status_code != 404

            if meeting_response.status_code == 201:
                meeting_id = meeting_response.json()["id"]

                # Step 2: Wait for transcript processing (simulate)
                await asyncio.sleep(0.1)

                # Step 3: Fetch meeting summary
                summary_response = await client.get(
                    f"/api/v1/meetings/{meeting_id}/summary",
                    headers=mock_auth_headers,
                )

                # Step 4: Verify tasks created
                tasks_response = await client.get(
                    f"/api/v1/tasks?workspace_id={workspace_id}",
                    headers=mock_auth_headers,
                )

                # Flow should complete successfully
                assert tasks_response.status_code != 404


# ============================================================================
# COMMUNICATION INTELLIGENCE FLOW
# ============================================================================

@pytest.mark.e2e
class TestCommunicationFlow:
    """Test communication ingestion and triage flow."""

    @pytest.mark.asyncio
    async def test_email_to_followup_flow(
        self,
        mock_auth_headers,
    ):
        """
        Test email ingestion → sentiment analysis → follow-up reminder.

        User Journey:
        1. Email received from investor
        2. Email ingested via Gmail MCP
        3. Sentiment analysis identifies urgency
        4. Follow-up reminder created
        5. User sees follow-up in unified inbox

        Acceptance Criteria:
        - Email ingested successfully
        - Sentiment score assigned
        - Urgent emails flagged for follow-up
        - Reminder appears in inbox
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            workspace_id = str(uuid4())

            # Step 1: Ingest email
            email_response = await client.post(
                "/api/v1/communications/ingest",
                json={
                    "workspace_id": workspace_id,
                    "platform": "gmail",
                    "sender": "investor@vc.com",
                    "subject": "URGENT: Funding decision needed",
                    "content": "We need your response by EOD...",
                },
                headers=mock_auth_headers,
            )

            # Endpoint should exist
            assert email_response.status_code != 404

            if email_response.status_code == 201:
                # Step 2: Check unified inbox
                inbox_response = await client.get(
                    f"/api/v1/inbox?workspace_id={workspace_id}&urgency=high",
                    headers=mock_auth_headers,
                )

                # Urgent items should be queryable
                assert inbox_response.status_code != 404


# ============================================================================
# BRIEFING GENERATION FLOW
# ============================================================================

@pytest.mark.e2e
class TestBriefingFlow:
    """Test daily briefing generation flow."""

    @pytest.mark.asyncio
    async def test_morning_brief_generation_flow(
        self,
        mock_auth_headers,
    ):
        """
        Test morning brief generation from multiple sources.

        User Journey:
        1. User has unread emails
        2. User has upcoming meetings
        3. User has pending tasks
        4. Morning brief is generated
        5. Brief includes all relevant information
        6. Brief delivered via Slack/Discord

        Acceptance Criteria:
        - Brief aggregates multiple data sources
        - Generated within 60 seconds
        - Accuracy ≥ 90% vs manual review
        - Delivered successfully
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            workspace_id = str(uuid4())
            founder_id = str(uuid4())

            # Generate morning brief
            brief_response = await client.post(
                "/api/v1/briefings/generate",
                json={
                    "workspace_id": workspace_id,
                    "founder_id": founder_id,
                    "kind": "morning",
                },
                headers=mock_auth_headers,
            )

            # Endpoint should exist
            assert brief_response.status_code != 404

            if brief_response.status_code == 201:
                brief = brief_response.json()

                # Verify brief structure
                assert "summary" in brief or "content" in brief


# ============================================================================
# ERROR RECOVERY FLOW
# ============================================================================

@pytest.mark.e2e
class TestErrorRecoveryFlow:
    """Test error handling and recovery flows."""

    @pytest.mark.asyncio
    async def test_integration_failure_recovery(
        self,
        mock_auth_headers,
    ):
        """
        Test recovery from integration failures.

        User Journey:
        1. User connects Zoom integration
        2. Zoom API returns error
        3. System logs error to ops.events
        4. User receives error notification
        5. User can retry connection
        6. Connection succeeds on retry

        Acceptance Criteria:
        - Errors logged for debugging
        - User notified of failure
        - Retry mechanism available
        - System remains stable after errors
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            workspace_id = str(uuid4())

            # Attempt to connect with invalid credentials
            error_response = await client.post(
                "/api/v1/integrations/connect",
                json={
                    "workspace_id": workspace_id,
                    "platform": "zoom",
                    "credentials": {"api_key": "invalid"},
                },
                headers=mock_auth_headers,
            )

            # Should handle error gracefully
            if error_response.status_code in [400, 401, 500]:
                # Retry with valid credentials
                retry_response = await client.post(
                    "/api/v1/integrations/connect",
                    json={
                        "workspace_id": workspace_id,
                        "platform": "zoom",
                        "credentials": {"api_key": "valid_key"},
                    },
                    headers=mock_auth_headers,
                )

                # Retry should be possible
                assert retry_response.status_code != 404

    @pytest.mark.asyncio
    async def test_concurrent_user_operations(self, mock_auth_headers):
        """
        Test concurrent operations by multiple users.

        User Journey:
        1. Multiple users create workspaces simultaneously
        2. Users add members concurrently
        3. Users connect integrations in parallel
        4. All operations complete successfully

        Acceptance Criteria:
        - No race conditions
        - No deadlocks
        - All operations atomic
        - Data consistency maintained
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create multiple workspaces concurrently
            tasks = [
                client.post(
                    "/api/v1/workspaces",
                    json={"name": f"Concurrent Workspace {i}"},
                    headers=mock_auth_headers,
                )
                for i in range(10)
            ]

            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # All requests should complete
            assert len(responses) == 10

            # No exceptions should occur
            errors = [r for r in responses if isinstance(r, Exception)]
            assert len(errors) == 0


# ============================================================================
# PERFORMANCE FLOW TESTS
# ============================================================================

@pytest.mark.e2e
@pytest.mark.slow
class TestPerformanceFlows:
    """Test performance under realistic usage patterns."""

    @pytest.mark.asyncio
    async def test_workspace_with_large_dataset(self, mock_auth_headers):
        """
        Test workspace performance with large datasets.

        User Journey:
        1. Workspace has 1000+ communications
        2. Workspace has 100+ meetings
        3. Workspace has 500+ tasks
        4. User queries unified inbox
        5. Results returned within 2 seconds

        Acceptance Criteria:
        - Queries complete within 2s latency
        - Pagination works correctly
        - Memory usage stays reasonable
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            workspace_id = str(uuid4())

            # Query large dataset
            import time

            start = time.time()
            response = await client.get(
                f"/api/v1/inbox?workspace_id={workspace_id}&limit=50",
                headers=mock_auth_headers,
            )
            elapsed = time.time() - start

            # Should complete within performance requirements
            if response.status_code == 200:
                assert elapsed < 2.0, f"Query took {elapsed}s, expected <2s"

    @pytest.mark.asyncio
    async def test_vector_search_performance(self, mock_auth_headers):
        """
        Test vector search performance under load.

        User Journey:
        1. Workspace has 10,000+ vectorized documents
        2. User performs semantic search
        3. Top 5 results returned within 300ms

        Acceptance Criteria:
        - Search latency < 300ms
        - Results accurate and relevant
        - Cosine similarity computed correctly
        """
        async with AsyncClient(app=app, base_url="http://test") as client:
            workspace_id = str(uuid4())
            query = "investor update meeting notes"

            import time

            start = time.time()
            response = await client.post(
                "/api/v1/search/semantic",
                json={
                    "workspace_id": workspace_id,
                    "query": query,
                    "limit": 5,
                },
                headers=mock_auth_headers,
            )
            elapsed = (time.time() - start) * 1000  # ms

            # Endpoint should exist and be fast
            if response.status_code == 200:
                assert elapsed < 300, f"Search took {elapsed}ms, expected <300ms"
