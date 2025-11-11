"""
Comprehensive tests for ZeroDB Client
Tests all operations: memory, vector, table, event, and admin
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import httpx

from app.zerodb_client import ZeroDBClient, get_zerodb


class TestZeroDBClient:
    """Test suite for ZeroDB client operations"""

    @pytest.fixture
    def mock_httpx_client(self):
        """Mock httpx AsyncClient"""
        mock = MagicMock()
        mock.post = AsyncMock()
        mock.get = AsyncMock()
        mock.delete = AsyncMock()
        mock.patch = AsyncMock()
        mock.aclose = AsyncMock()
        return mock

    @pytest.fixture
    def zerodb_client(self, mock_httpx_client):
        """Create ZeroDB client with mocked HTTP client"""
        with patch('app.zerodb_client.httpx.AsyncClient', return_value=mock_httpx_client):
            client = ZeroDBClient()
            client._client = mock_httpx_client
            return client

    @pytest.mark.asyncio
    async def test_ensure_authenticated_success(self, zerodb_client, mock_httpx_client):
        """Test successful authentication"""
        # Mock login response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "test_token_123",
            "expires_in": 1800
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        token = await zerodb_client._ensure_authenticated()

        assert token == "test_token_123"
        assert zerodb_client._access_token == "test_token_123"
        mock_httpx_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_authenticated_cached(self, zerodb_client):
        """Test that cached token is used when valid"""
        # Set a valid token
        zerodb_client._access_token = "cached_token"
        zerodb_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        token = await zerodb_client._ensure_authenticated()

        assert token == "cached_token"

    @pytest.mark.asyncio
    async def test_ensure_authenticated_refresh(self, zerodb_client, mock_httpx_client):
        """Test token refresh when expired"""
        # Set expired token
        zerodb_client._access_token = "expired_token"
        zerodb_client._token_expires_at = datetime.utcnow() - timedelta(hours=1)

        # Mock new login
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "new_token",
            "expires_in": 1800
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        token = await zerodb_client._ensure_authenticated()

        assert token == "new_token"

    @pytest.mark.asyncio
    async def test_ensure_authenticated_http_error(self, zerodb_client, mock_httpx_client):
        """Test authentication failure"""
        mock_httpx_client.post.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=MagicMock(),
            response=MagicMock(status_code=401)
        )

        with pytest.raises(httpx.HTTPStatusError):
            await zerodb_client._ensure_authenticated()

    def test_get_headers(self, zerodb_client):
        """Test header generation"""
        headers = zerodb_client._get_headers("test_token")

        assert headers["Authorization"] == "Bearer test_token"
        assert headers["Content-Type"] == "application/json"
        assert "X-Project-ID" in headers

    # ==================== MEMORY OPERATIONS ====================

    @pytest.mark.asyncio
    async def test_store_memory_success(self, zerodb_client, mock_httpx_client):
        """Test storing memory"""
        # Mock authentication
        zerodb_client._access_token = "test_token"
        zerodb_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        # Mock store response
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "mem_123", "content": "test memory"}
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        result = await zerodb_client.store_memory(
            content="test memory",
            role="user",
            session_id="session_1",
            agent_id="agent_1",
            metadata={"key": "value"}
        )

        assert result["id"] == "mem_123"
        assert result["content"] == "test memory"
        mock_httpx_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_memory_minimal(self, zerodb_client, mock_httpx_client):
        """Test storing memory with minimal parameters"""
        zerodb_client._access_token = "test_token"
        zerodb_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "mem_456"}
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        result = await zerodb_client.store_memory(content="minimal memory")

        assert result["id"] == "mem_456"

    @pytest.mark.asyncio
    async def test_search_memory_success(self, zerodb_client, mock_httpx_client):
        """Test searching memory"""
        zerodb_client._access_token = "test_token"
        zerodb_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"id": "mem_1", "content": "result 1", "score": 0.95},
            {"id": "mem_2", "content": "result 2", "score": 0.85}
        ]
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        results = await zerodb_client.search_memory(
            query="test query",
            session_id="session_1",
            limit=10
        )

        assert len(results) == 2
        assert results[0]["score"] == 0.95

    @pytest.mark.asyncio
    async def test_search_memory_with_filters(self, zerodb_client, mock_httpx_client):
        """Test searching memory with all filters"""
        zerodb_client._access_token = "test_token"
        zerodb_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        await zerodb_client.search_memory(
            query="test",
            session_id="session_1",
            agent_id="agent_1",
            role="user",
            limit=5
        )

        # Verify parameters were passed
        call_args = mock_httpx_client.get.call_args
        assert call_args[1]["params"]["query"] == "test"
        assert call_args[1]["params"]["session_id"] == "session_1"
        assert call_args[1]["params"]["agent_id"] == "agent_1"
        assert call_args[1]["params"]["role"] == "user"

    @pytest.mark.asyncio
    async def test_get_context_success(self, zerodb_client, mock_httpx_client):
        """Test getting session context"""
        zerodb_client._access_token = "test_token"
        zerodb_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "session_id": "session_1",
            "messages": [{"role": "user", "content": "Hello"}],
            "token_count": 10
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        result = await zerodb_client.get_context(
            session_id="session_1",
            max_tokens=8192
        )

        assert result["session_id"] == "session_1"
        assert result["token_count"] == 10

    # ==================== VECTOR OPERATIONS ====================

    @pytest.mark.asyncio
    async def test_store_vector_success(self, zerodb_client, mock_httpx_client):
        """Test storing vector"""
        zerodb_client._access_token = "test_token"
        zerodb_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        # Create 1536-dimensional vector
        vector = [0.1] * 1536

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "vec_123"}
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        result = await zerodb_client.store_vector(
            vector_embedding=vector,
            document="test document",
            metadata={"source": "test"},
            namespace="default"
        )

        assert result["id"] == "vec_123"

    @pytest.mark.asyncio
    async def test_store_vector_wrong_dimension(self, zerodb_client):
        """Test storing vector with wrong dimensions"""
        wrong_vector = [0.1] * 100  # Wrong size

        with pytest.raises(ValueError, match="exactly 1536 dimensions"):
            await zerodb_client.store_vector(
                vector_embedding=wrong_vector,
                document="test"
            )

    @pytest.mark.asyncio
    async def test_batch_upsert_vectors_success(self, zerodb_client, mock_httpx_client):
        """Test batch upserting vectors"""
        zerodb_client._access_token = "test_token"
        zerodb_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        vectors = [
            {"vector": [0.1] * 1536, "document": "doc1", "metadata": {}},
            {"vector": [0.2] * 1536, "document": "doc2", "metadata": {}}
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = {"success": 2, "failed": 0, "ids": ["vec_1", "vec_2"]}
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        result = await zerodb_client.batch_upsert_vectors(vectors)

        assert result["success"] == 2
        assert len(result["ids"]) == 2

    @pytest.mark.asyncio
    async def test_search_vectors_success(self, zerodb_client, mock_httpx_client):
        """Test vector similarity search"""
        zerodb_client._access_token = "test_token"
        zerodb_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        query_vector = [0.1] * 1536

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"id": "vec_1", "document": "doc1", "score": 0.95},
            {"id": "vec_2", "document": "doc2", "score": 0.85}
        ]
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        results = await zerodb_client.search_vectors(
            query_vector=query_vector,
            namespace="default",
            limit=10,
            threshold=0.7
        )

        assert len(results) == 2
        assert results[0]["score"] == 0.95

    @pytest.mark.asyncio
    async def test_delete_vector_success(self, zerodb_client, mock_httpx_client):
        """Test deleting vector"""
        zerodb_client._access_token = "test_token"
        zerodb_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.delete.return_value = mock_response

        result = await zerodb_client.delete_vector("vec_123")

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_get_vector_success(self, zerodb_client, mock_httpx_client):
        """Test getting vector by ID"""
        zerodb_client._access_token = "test_token"
        zerodb_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "vec_123",
            "vector": [0.1] * 1536,
            "document": "test doc"
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        result = await zerodb_client.get_vector("vec_123")

        assert result["id"] == "vec_123"
        assert len(result["vector"]) == 1536

    # ==================== TABLE OPERATIONS ====================

    @pytest.mark.asyncio
    async def test_create_table_success(self, zerodb_client, mock_httpx_client):
        """Test creating table"""
        zerodb_client._access_token = "test_token"
        zerodb_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        mock_response = MagicMock()
        mock_response.json.return_value = {"name": "test_table", "created": True}
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        result = await zerodb_client.create_table(
            table_name="test_table",
            schema={"id": "string", "value": "number"}
        )

        assert result["name"] == "test_table"

    @pytest.mark.asyncio
    async def test_insert_row_success(self, zerodb_client, mock_httpx_client):
        """Test inserting row"""
        zerodb_client._access_token = "test_token"
        zerodb_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "row_123", "data": {"key": "value"}}
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        result = await zerodb_client.insert_row(
            table_name="test_table",
            data={"key": "value"}
        )

        assert result["id"] == "row_123"

    @pytest.mark.asyncio
    async def test_query_table_success(self, zerodb_client, mock_httpx_client):
        """Test querying table"""
        zerodb_client._access_token = "test_token"
        zerodb_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"id": "row_1", "data": "test1"},
            {"id": "row_2", "data": "test2"}
        ]
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        results = await zerodb_client.query_table(
            table_name="test_table",
            filters={"status": "active"},
            limit=100
        )

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_update_row_success(self, zerodb_client, mock_httpx_client):
        """Test updating row"""
        zerodb_client._access_token = "test_token"
        zerodb_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "row_123", "updated": True}
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.patch.return_value = mock_response

        result = await zerodb_client.update_row(
            table_name="test_table",
            row_id="row_123",
            data={"status": "updated"}
        )

        assert result["updated"] is True

    @pytest.mark.asyncio
    async def test_delete_row_success(self, zerodb_client, mock_httpx_client):
        """Test deleting row"""
        zerodb_client._access_token = "test_token"
        zerodb_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        mock_response = MagicMock()
        mock_response.json.return_value = {"deleted": True}
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.delete.return_value = mock_response

        result = await zerodb_client.delete_row("test_table", "row_123")

        assert result["deleted"] is True

    # ==================== EVENT OPERATIONS ====================

    @pytest.mark.asyncio
    async def test_publish_event_success(self, zerodb_client, mock_httpx_client):
        """Test publishing event"""
        zerodb_client._access_token = "test_token"
        zerodb_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        mock_response = MagicMock()
        mock_response.json.return_value = {"event_id": "evt_123", "published": True}
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        result = await zerodb_client.publish_event(
            event_type="user.created",
            payload={"user_id": "123", "email": "test@example.com"},
            topic="users"
        )

        assert result["event_id"] == "evt_123"

    @pytest.mark.asyncio
    async def test_subscribe_to_events_success(self, zerodb_client, mock_httpx_client):
        """Test subscribing to events"""
        zerodb_client._access_token = "test_token"
        zerodb_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        mock_response = MagicMock()
        mock_response.json.return_value = {"subscription_id": "sub_123", "topic": "users"}
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        result = await zerodb_client.subscribe_to_events(
            topic="users",
            callback_url="https://example.com/webhook"
        )

        assert result["subscription_id"] == "sub_123"

    # ==================== ADMIN OPERATIONS ====================

    @pytest.mark.asyncio
    async def test_health_check_success(self, zerodb_client, mock_httpx_client):
        """Test health check"""
        zerodb_client._access_token = "test_token"
        zerodb_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "healthy",
            "uptime": 12345,
            "version": "1.0.0"
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        result = await zerodb_client.health_check()

        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_get_project_usage_success(self, zerodb_client, mock_httpx_client):
        """Test getting project usage"""
        zerodb_client._access_token = "test_token"
        zerodb_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "memory_usage": 1024,
            "vector_count": 500,
            "api_calls": 1000
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        result = await zerodb_client.get_project_usage()

        assert result["vector_count"] == 500

    @pytest.mark.asyncio
    async def test_close_client(self, zerodb_client, mock_httpx_client):
        """Test closing client"""
        await zerodb_client.close()

        mock_httpx_client.aclose.assert_called_once()

    # ==================== ERROR HANDLING ====================

    @pytest.mark.asyncio
    async def test_http_error_handling(self, zerodb_client, mock_httpx_client):
        """Test HTTP error handling"""
        zerodb_client._access_token = "test_token"
        zerodb_client._token_expires_at = datetime.utcnow() + timedelta(hours=1)

        mock_httpx_client.post.side_effect = httpx.HTTPStatusError(
            "500 Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500)
        )

        with pytest.raises(httpx.HTTPStatusError):
            await zerodb_client.store_memory("test")

    def test_get_zerodb_dependency(self):
        """Test FastAPI dependency injection"""
        client = get_zerodb()
        assert isinstance(client, ZeroDBClient)
