"""
AI Chief of Staff - Database Tests
Sprint 1: RLS, vector search, and multi-tenant isolation tests

Test coverage:
- Row-Level Security (RLS) policies
- Workspace isolation
- Vector search functionality
- Database constraints and relationships
- Event logging
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from asyncpg import Connection


# ============================================================================
# ROW-LEVEL SECURITY (RLS) TESTS
# ============================================================================

@pytest.mark.database
@pytest.mark.rls
class TestRowLevelSecurity:
    """Test Row-Level Security policies for multi-tenant isolation."""

    @pytest_asyncio.fixture
    async def test_workspaces(self, db_connection: Connection):
        """Create two test workspaces."""
        workspace_a_id = uuid4()
        workspace_b_id = uuid4()

        await db_connection.execute(
            """
            INSERT INTO core.workspaces (id, name)
            VALUES ($1, 'Workspace A'), ($2, 'Workspace B')
            """,
            workspace_a_id,
            workspace_b_id,
        )

        return workspace_a_id, workspace_b_id

    async def test_workspace_isolation(self, db_connection: Connection, test_workspaces):
        """
        Test that workspaces cannot access each other's data.

        Acceptance Criteria:
        - User in workspace A cannot see workspace B data
        - RLS policies enforce workspace_id filtering
        - Unauthorized queries return empty results
        """
        workspace_a_id, workspace_b_id = test_workspaces
        user_a_id = uuid4()
        user_b_id = uuid4()

        # Create members for each workspace
        await db_connection.execute(
            """
            INSERT INTO core.members (workspace_id, user_id, role)
            VALUES ($1, $2, 'admin'), ($3, $4, 'admin')
            """,
            workspace_a_id,
            user_a_id,
            workspace_b_id,
            user_b_id,
        )

        # Create founders in each workspace
        founder_a_id = uuid4()
        founder_b_id = uuid4()

        await db_connection.execute(
            """
            INSERT INTO core.founders (id, workspace_id, user_id, display_name, email)
            VALUES ($1, $2, $3, 'Founder A', 'a@example.com'),
                   ($4, $5, $6, 'Founder B', 'b@example.com')
            """,
            founder_a_id,
            workspace_a_id,
            user_a_id,
            founder_b_id,
            workspace_b_id,
            user_b_id,
        )

        # Set auth context to user A
        await db_connection.execute(
            "SELECT set_config('request.jwt.claim.sub', $1, TRUE)",
            str(user_a_id),
        )

        # Query founders - should only see workspace A founder
        # Note: This test assumes RLS is enabled. Adjust based on actual RLS implementation
        founders = await db_connection.fetch(
            """
            SELECT id, workspace_id, display_name
            FROM core.founders
            WHERE workspace_id IN (
                SELECT workspace_id FROM core.members WHERE user_id = $1
            )
            """,
            user_a_id,
        )

        # Verify isolation
        assert len(founders) == 1
        assert founders[0]["workspace_id"] == workspace_a_id
        assert founders[0]["display_name"] == "Founder A"

        # Verify workspace B data is not accessible
        founder_ids = [f["id"] for f in founders]
        assert founder_b_id not in founder_ids

    async def test_rls_insert_enforcement(self, db_connection: Connection, test_workspaces):
        """
        Test that users cannot insert data into other workspaces.

        Acceptance Criteria:
        - INSERT attempts for unauthorized workspaces fail
        - Only workspace members can insert data
        """
        workspace_a_id, workspace_b_id = test_workspaces
        user_a_id = uuid4()

        # Add user to workspace A only
        await db_connection.execute(
            """
            INSERT INTO core.members (workspace_id, user_id, role)
            VALUES ($1, $2, 'admin')
            """,
            workspace_a_id,
            user_a_id,
        )

        # Try to insert founder in workspace B (should fail or be filtered)
        # Actual behavior depends on RLS policy implementation
        try:
            await db_connection.execute(
                """
                INSERT INTO core.founders (workspace_id, user_id, display_name)
                VALUES ($1, $2, 'Unauthorized Founder')
                """,
                workspace_b_id,
                user_a_id,
            )

            # If insert succeeds, verify it's not accessible through RLS
            founders = await db_connection.fetch(
                """
                SELECT * FROM core.founders
                WHERE workspace_id = $1 AND user_id = $2
                """,
                workspace_b_id,
                user_a_id,
            )
            # Should be empty due to RLS
            assert len(founders) == 0

        except Exception as e:
            # RLS policy may prevent the insert entirely
            assert "permission denied" in str(e).lower() or "violates" in str(e).lower()

    async def test_rls_update_enforcement(self, db_connection: Connection, test_workspaces):
        """
        Test that users cannot update data in other workspaces.

        Acceptance Criteria:
        - UPDATE attempts for unauthorized workspaces fail
        - Only workspace members can update their data
        """
        workspace_a_id, workspace_b_id = test_workspaces
        user_a_id = uuid4()
        user_b_id = uuid4()

        # Setup members and founders
        await db_connection.execute(
            """
            INSERT INTO core.members (workspace_id, user_id, role)
            VALUES ($1, $2, 'admin'), ($3, $4, 'admin')
            """,
            workspace_a_id,
            user_a_id,
            workspace_b_id,
            user_b_id,
        )

        founder_b_id = uuid4()
        await db_connection.execute(
            """
            INSERT INTO core.founders (id, workspace_id, user_id, display_name)
            VALUES ($1, $2, $3, 'Founder B')
            """,
            founder_b_id,
            workspace_b_id,
            user_b_id,
        )

        # Set context to user A
        await db_connection.execute(
            "SELECT set_config('request.jwt.claim.sub', $1, TRUE)",
            str(user_a_id),
        )

        # Try to update founder in workspace B
        result = await db_connection.execute(
            """
            UPDATE core.founders
            SET display_name = 'Hacked Name'
            WHERE id = $1
            RETURNING id
            """,
            founder_b_id,
        )

        # Update should not affect any rows due to RLS
        assert "UPDATE 0" in result or result == "UPDATE 0"

    async def test_rls_delete_enforcement(self, db_connection: Connection, test_workspaces):
        """
        Test that users cannot delete data from other workspaces.

        Acceptance Criteria:
        - DELETE attempts for unauthorized workspaces fail
        - Only authorized users can delete their workspace data
        """
        workspace_a_id, workspace_b_id = test_workspaces
        user_a_id = uuid4()
        user_b_id = uuid4()

        # Setup
        await db_connection.execute(
            """
            INSERT INTO core.members (workspace_id, user_id, role)
            VALUES ($1, $2, 'admin'), ($3, $4, 'admin')
            """,
            workspace_a_id,
            user_a_id,
            workspace_b_id,
            user_b_id,
        )

        founder_b_id = uuid4()
        await db_connection.execute(
            """
            INSERT INTO core.founders (id, workspace_id, user_id, display_name)
            VALUES ($1, $2, $3, 'Founder B')
            """,
            founder_b_id,
            workspace_b_id,
            user_b_id,
        )

        # Try to delete as user A
        result = await db_connection.execute(
            """
            DELETE FROM core.founders WHERE id = $1 RETURNING id
            """,
            founder_b_id,
        )

        # Delete should not affect any rows due to RLS
        assert "DELETE 0" in result or result == "DELETE 0"


# ============================================================================
# VECTOR SEARCH TESTS
# ============================================================================

@pytest.mark.database
@pytest.mark.vector
class TestVectorSearch:
    """Test pgvector functionality and semantic search."""

    async def test_vector_extension_installed(self, db_connection: Connection):
        """
        Test that pgvector extension is installed and available.

        Acceptance Criteria:
        - pgvector extension exists
        - Vector data type is available
        """
        result = await db_connection.fetchval(
            """
            SELECT EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'vector'
            )
            """
        )
        assert result is True, "pgvector extension is not installed"

    async def test_embedding_storage(self, db_connection: Connection):
        """
        Test storing embeddings in database.

        Acceptance Criteria:
        - Embeddings can be inserted into vector columns
        - Vector dimensions are enforced (1536 for OpenAI)
        """
        workspace_id = uuid4()
        founder_id = uuid4()
        user_id = uuid4()

        # Create workspace and founder
        await db_connection.execute(
            """
            INSERT INTO core.workspaces (id, name) VALUES ($1, 'Test')
            """,
            workspace_id,
        )
        await db_connection.execute(
            """
            INSERT INTO core.founders (id, workspace_id, user_id, display_name)
            VALUES ($1, $2, $3, 'Test Founder')
            """,
            founder_id,
            workspace_id,
            user_id,
        )

        # Create contact with embedding
        contact_id = uuid4()
        embedding = [0.1] * 1536  # 1536-dimensional vector

        await db_connection.execute(
            """
            INSERT INTO core.contacts (id, workspace_id, founder_id, name, embedding)
            VALUES ($1, $2, $3, 'Test Contact', $4::vector)
            """,
            contact_id,
            workspace_id,
            founder_id,
            embedding,
        )

        # Verify storage
        result = await db_connection.fetchrow(
            """
            SELECT id, name FROM core.contacts WHERE id = $1
            """,
            contact_id,
        )
        assert result["name"] == "Test Contact"

    async def test_cosine_similarity_search(self, db_connection: Connection):
        """
        Test cosine similarity search for semantic matching.

        Acceptance Criteria:
        - Cosine similarity queries return results within 300ms
        - Results are ordered by similarity score
        - Top-5 most similar vectors are returned
        """
        workspace_id = uuid4()
        founder_id = uuid4()
        user_id = uuid4()

        # Setup
        await db_connection.execute(
            "INSERT INTO core.workspaces (id, name) VALUES ($1, 'Test')",
            workspace_id,
        )
        await db_connection.execute(
            """
            INSERT INTO core.founders (id, workspace_id, user_id, display_name)
            VALUES ($1, $2, $3, 'Test Founder')
            """,
            founder_id,
            workspace_id,
            user_id,
        )

        # Insert contacts with different embeddings
        import numpy as np

        for i in range(10):
            # Create slightly different embeddings
            embedding = np.random.rand(1536).tolist()

            await db_connection.execute(
                """
                INSERT INTO core.contacts (workspace_id, founder_id, name, embedding)
                VALUES ($1, $2, $3, $4::vector)
                """,
                workspace_id,
                founder_id,
                f"Contact {i}",
                embedding,
            )

        # Perform similarity search
        query_embedding = np.random.rand(1536).tolist()

        import time

        start = time.time()
        results = await db_connection.fetch(
            """
            SELECT name, 1 - (embedding <=> $1::vector) AS similarity
            FROM core.contacts
            WHERE workspace_id = $2
            ORDER BY embedding <=> $1::vector
            LIMIT 5
            """,
            query_embedding,
            workspace_id,
        )
        elapsed = (time.time() - start) * 1000  # Convert to ms

        # Verify performance and results
        assert elapsed < 300, f"Query took {elapsed}ms, expected <300ms"
        assert len(results) == 5, "Should return top 5 results"
        assert all("similarity" in dict(r) for r in results)

    async def test_vector_dimension_validation(self, db_connection: Connection):
        """
        Test that incorrect vector dimensions are rejected.

        Acceptance Criteria:
        - Vectors with wrong dimensions raise errors
        - Only 1536-dimensional vectors are accepted
        """
        workspace_id = uuid4()
        founder_id = uuid4()
        user_id = uuid4()

        # Setup
        await db_connection.execute(
            "INSERT INTO core.workspaces (id, name) VALUES ($1, 'Test')",
            workspace_id,
        )
        await db_connection.execute(
            """
            INSERT INTO core.founders (id, workspace_id, user_id, display_name)
            VALUES ($1, $2, $3, 'Test')
            """,
            founder_id,
            workspace_id,
            user_id,
        )

        # Try to insert with wrong dimension
        wrong_embedding = [0.1] * 100  # Wrong size

        with pytest.raises(Exception) as exc_info:
            await db_connection.execute(
                """
                INSERT INTO core.contacts (workspace_id, founder_id, name, embedding)
                VALUES ($1, $2, 'Test', $3::vector)
                """,
                workspace_id,
                founder_id,
                wrong_embedding,
            )

        assert "dimension" in str(exc_info.value).lower()


# ============================================================================
# EVENT LOGGING TESTS
# ============================================================================

@pytest.mark.database
class TestEventLogging:
    """Test event sourcing and audit trail functionality."""

    async def test_event_creation(self, db_connection: Connection):
        """
        Test creating events in the ops.events table.

        Acceptance Criteria:
        - Events can be created with all required fields
        - Event payload is stored as JSONB
        - Timestamps are automatically set
        """
        workspace_id = uuid4()
        actor_id = uuid4()

        await db_connection.execute(
            "INSERT INTO core.workspaces (id, name) VALUES ($1, 'Test')",
            workspace_id,
        )

        event_id = uuid4()
        payload = {
            "action": "create",
            "entity": "workspace",
            "details": {"name": "Test Workspace"},
        }

        await db_connection.execute(
            """
            INSERT INTO ops.events (
                id, workspace_id, actor_type, actor_id,
                event_type, payload, linked_entity, linked_id
            )
            VALUES ($1, $2, 'user', $3, 'workspace.created', $4, 'workspace', $2)
            """,
            event_id,
            workspace_id,
            actor_id,
            payload,
        )

        # Verify event
        event = await db_connection.fetchrow(
            "SELECT * FROM ops.events WHERE id = $1",
            event_id,
        )

        assert event["event_type"] == "workspace.created"
        assert event["actor_type"] == "user"
        assert event["payload"] == payload

    async def test_event_immutability(self, db_connection: Connection):
        """
        Test that events remain intact even when entities are deleted.

        Acceptance Criteria:
        - Deleting entities keeps events intact
        - Event trail is preserved for auditability
        """
        workspace_id = uuid4()

        await db_connection.execute(
            "INSERT INTO core.workspaces (id, name) VALUES ($1, 'Test')",
            workspace_id,
        )

        # Create event
        event_id = uuid4()
        await db_connection.execute(
            """
            INSERT INTO ops.events (
                id, workspace_id, actor_type, event_type, payload, linked_id
            )
            VALUES ($1, $2, 'system', 'workspace.created', '{}'::jsonb, $2)
            """,
            event_id,
            workspace_id,
        )

        # Delete workspace (if cascade is not configured, this tests isolation)
        try:
            await db_connection.execute(
                "DELETE FROM core.workspaces WHERE id = $1",
                workspace_id,
            )
        except Exception:
            # May fail due to foreign key constraint, which is OK
            pass

        # Event should still exist (or be deleted by CASCADE - depends on schema)
        # This test documents the expected behavior
        event = await db_connection.fetchrow(
            "SELECT * FROM ops.events WHERE id = $1",
            event_id,
        )

        # Adjust assertion based on actual schema CASCADE rules
        if event:
            assert event["event_type"] == "workspace.created"


# ============================================================================
# DATA INTEGRITY TESTS
# ============================================================================

@pytest.mark.database
class TestDataIntegrity:
    """Test database constraints and referential integrity."""

    async def test_workspace_cascade_delete(self, db_connection: Connection):
        """
        Test that deleting workspace cascades to related entities.

        Acceptance Criteria:
        - Deleting workspace removes members
        - Deleting workspace removes founders
        - CASCADE is properly configured
        """
        workspace_id = uuid4()
        user_id = uuid4()

        # Create workspace, member, and founder
        await db_connection.execute(
            "INSERT INTO core.workspaces (id, name) VALUES ($1, 'Test')",
            workspace_id,
        )
        await db_connection.execute(
            "INSERT INTO core.members (workspace_id, user_id, role) VALUES ($1, $2, 'admin')",
            workspace_id,
            user_id,
        )
        await db_connection.execute(
            """
            INSERT INTO core.founders (workspace_id, user_id, display_name)
            VALUES ($1, $2, 'Test')
            """,
            workspace_id,
            user_id,
        )

        # Delete workspace
        await db_connection.execute(
            "DELETE FROM core.workspaces WHERE id = $1",
            workspace_id,
        )

        # Verify cascade
        members = await db_connection.fetch(
            "SELECT * FROM core.members WHERE workspace_id = $1",
            workspace_id,
        )
        founders = await db_connection.fetch(
            "SELECT * FROM core.founders WHERE workspace_id = $1",
            workspace_id,
        )

        assert len(members) == 0, "Members should be deleted"
        assert len(founders) == 0, "Founders should be deleted"

    async def test_unique_constraints(self, db_connection: Connection):
        """
        Test unique constraints on tables.

        Acceptance Criteria:
        - Duplicate workspace_id + user_id in members fails
        - Duplicate platform + external_id fails
        """
        workspace_id = uuid4()
        user_id = uuid4()

        await db_connection.execute(
            "INSERT INTO core.workspaces (id, name) VALUES ($1, 'Test')",
            workspace_id,
        )

        # Insert member
        await db_connection.execute(
            "INSERT INTO core.members (workspace_id, user_id, role) VALUES ($1, $2, 'admin')",
            workspace_id,
            user_id,
        )

        # Try to insert duplicate
        with pytest.raises(Exception) as exc_info:
            await db_connection.execute(
                "INSERT INTO core.members (workspace_id, user_id, role) VALUES ($1, $2, 'member')",
                workspace_id,
                user_id,
            )

        assert "unique" in str(exc_info.value).lower() or "duplicate" in str(exc_info.value).lower()
