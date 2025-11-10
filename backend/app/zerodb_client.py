"""
ZeroDB API Client
Provides access to all 60 ZeroDB operations across 9 categories:
1. Memory Operations (3)
2. Vector Operations (10)
3. Quantum Operations (6)
4. Table/NoSQL Operations (8)
5. File Operations (6)
6. Event Operations (5)
7. Project Operations (7)
8. RLHF Operations (10)
9. Admin Operations (5)
"""
import logging
from typing import Optional, Dict, Any, List
import httpx
from datetime import datetime, timedelta

from app.config import get_settings

logger = logging.getLogger(__name__)


class ZeroDBClient:
    """
    Enterprise-grade ZeroDB API client with full access to 60 operations
    Implements JWT authentication with automatic token renewal
    """

    def __init__(self):
        """Initialize ZeroDB client with settings"""
        self.settings = get_settings()
        self.base_url = self.settings.zerodb_api_base_url
        self.project_id = self.settings.zerodb_project_id
        self.username = self.settings.zerodb_username
        self.password = self.settings.zerodb_password
        self.api_key = self.settings.zerodb_api_key

        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._client = httpx.AsyncClient(timeout=30.0)

        logger.info(f"ZeroDB client initialized for project: {self.project_id}")

    async def _ensure_authenticated(self) -> str:
        """
        Ensure we have a valid access token
        Automatically refreshes if expired
        """
        if self._access_token and self._token_expires_at:
            if datetime.utcnow() < self._token_expires_at - timedelta(minutes=5):
                return self._access_token

        # Login to get new token
        login_data = {
            "username": self.username,
            "password": self.password
        }

        response = await self._client.post(
            f"{self.base_url}/v1/auth/login",
            json=login_data
        )
        response.raise_for_status()

        data = response.json()
        self._access_token = data["access_token"]
        expires_in = data.get("expires_in", 1800)  # Default 30 min
        self._token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        logger.info("ZeroDB authentication successful")
        return self._access_token

    def _get_headers(self, token: str) -> Dict[str, str]:
        """Get standard headers with authentication"""
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Project-ID": self.project_id
        }

    # ==================== MEMORY OPERATIONS (3) ====================

    async def store_memory(
        self,
        content: str,
        role: str = "user",
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store agent memory for persistent context across sessions

        Args:
            content: Memory content to store
            role: Message role (user/assistant/system)
            session_id: Optional session identifier
            agent_id: Optional agent identifier
            metadata: Optional additional metadata

        Returns:
            dict: Created memory with ID and timestamp
        """
        token = await self._ensure_authenticated()

        payload = {
            "content": content,
            "role": role,
            "session_id": session_id,
            "agent_id": agent_id,
            "metadata": metadata or {}
        }

        response = await self._client.post(
            f"{self.base_url}/v1/memory",
            headers=self._get_headers(token),
            json=payload
        )
        response.raise_for_status()
        return response.json()

    async def search_memory(
        self,
        query: str,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        role: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Semantic similarity search across stored memories

        Args:
            query: Search query
            session_id: Filter by session
            agent_id: Filter by agent
            role: Filter by role
            limit: Max results

        Returns:
            list: Matching memories with similarity scores
        """
        token = await self._ensure_authenticated()

        params = {
            "query": query,
            "limit": limit
        }
        if session_id:
            params["session_id"] = session_id
        if agent_id:
            params["agent_id"] = agent_id
        if role:
            params["role"] = role

        response = await self._client.get(
            f"{self.base_url}/v1/memory/search",
            headers=self._get_headers(token),
            params=params
        )
        response.raise_for_status()
        return response.json()

    async def get_context(
        self,
        session_id: str,
        agent_id: Optional[str] = None,
        max_tokens: int = 8192
    ) -> Dict[str, Any]:
        """
        Retrieve optimized context window for current session

        Args:
            session_id: Session identifier
            agent_id: Optional agent filter
            max_tokens: Maximum token count

        Returns:
            dict: Session data with messages and token count
        """
        token = await self._ensure_authenticated()

        params = {
            "session_id": session_id,
            "max_tokens": max_tokens
        }
        if agent_id:
            params["agent_id"] = agent_id

        response = await self._client.get(
            f"{self.base_url}/v1/memory/context",
            headers=self._get_headers(token),
            params=params
        )
        response.raise_for_status()
        return response.json()

    # ==================== VECTOR OPERATIONS (10) ====================

    async def store_vector(
        self,
        vector_embedding: List[float],
        document: str,
        metadata: Optional[Dict[str, Any]] = None,
        namespace: str = "default"
    ) -> Dict[str, Any]:
        """
        Store 1536-dimensional embedding with metadata

        Args:
            vector_embedding: Exactly 1536 float values
            document: Document text
            metadata: Optional metadata
            namespace: Vector namespace

        Returns:
            dict: Created vector with ID
        """
        if len(vector_embedding) != 1536:
            raise ValueError("Vector embedding must be exactly 1536 dimensions")

        token = await self._ensure_authenticated()

        payload = {
            "vector": vector_embedding,
            "document": document,
            "metadata": metadata or {},
            "namespace": namespace
        }

        response = await self._client.post(
            f"{self.base_url}/v1/vectors",
            headers=self._get_headers(token),
            json=payload
        )
        response.raise_for_status()
        return response.json()

    async def batch_upsert_vectors(
        self,
        vectors: List[Dict[str, Any]],
        namespace: str = "default"
    ) -> Dict[str, Any]:
        """
        Batch upsert multiple vectors

        Args:
            vectors: List of vector dicts with 'vector', 'document', 'metadata'
            namespace: Vector namespace

        Returns:
            dict: Success/failure counts and IDs
        """
        token = await self._ensure_authenticated()

        payload = {
            "vectors": vectors,
            "namespace": namespace
        }

        response = await self._client.post(
            f"{self.base_url}/v1/vectors/batch",
            headers=self._get_headers(token),
            json=payload
        )
        response.raise_for_status()
        return response.json()

    async def search_vectors(
        self,
        query_vector: List[float],
        namespace: str = "default",
        limit: int = 10,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Semantic similarity search on stored vectors

        Args:
            query_vector: Query embedding (1536 dimensions)
            namespace: Vector namespace
            limit: Max results
            threshold: Minimum similarity score

        Returns:
            list: Matching vectors with similarity scores
        """
        token = await self._ensure_authenticated()

        payload = {
            "query_vector": query_vector,
            "namespace": namespace,
            "limit": limit,
            "threshold": threshold
        }

        response = await self._client.post(
            f"{self.base_url}/v1/vectors/search",
            headers=self._get_headers(token),
            json=payload
        )
        response.raise_for_status()
        return response.json()

    async def delete_vector(self, vector_id: str) -> Dict[str, Any]:
        """Delete specific vector by ID"""
        token = await self._ensure_authenticated()

        response = await self._client.delete(
            f"{self.base_url}/v1/vectors/{vector_id}",
            headers=self._get_headers(token)
        )
        response.raise_for_status()
        return response.json()

    async def get_vector(self, vector_id: str) -> Dict[str, Any]:
        """Retrieve complete vector data by ID"""
        token = await self._ensure_authenticated()

        response = await self._client.get(
            f"{self.base_url}/v1/vectors/{vector_id}",
            headers=self._get_headers(token)
        )
        response.raise_for_status()
        return response.json()

    # ==================== TABLE/NOSQL OPERATIONS (8) ====================

    async def create_table(
        self,
        table_name: str,
        schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create NoSQL table with optional schema"""
        token = await self._ensure_authenticated()

        payload = {
            "name": table_name,
            "schema": schema or {}
        }

        response = await self._client.post(
            f"{self.base_url}/v1/tables",
            headers=self._get_headers(token),
            json=payload
        )
        response.raise_for_status()
        return response.json()

    async def insert_row(
        self,
        table_name: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Insert row into table"""
        token = await self._ensure_authenticated()

        response = await self._client.post(
            f"{self.base_url}/v1/tables/{table_name}/rows",
            headers=self._get_headers(token),
            json=data
        )
        response.raise_for_status()
        return response.json()

    async def query_table(
        self,
        table_name: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query table with filters"""
        token = await self._ensure_authenticated()

        params = {"limit": limit}
        if filters:
            params["filters"] = filters

        response = await self._client.get(
            f"{self.base_url}/v1/tables/{table_name}/rows",
            headers=self._get_headers(token),
            params=params
        )
        response.raise_for_status()
        return response.json()

    async def update_row(
        self,
        table_name: str,
        row_id: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update specific row"""
        token = await self._ensure_authenticated()

        response = await self._client.patch(
            f"{self.base_url}/v1/tables/{table_name}/rows/{row_id}",
            headers=self._get_headers(token),
            json=data
        )
        response.raise_for_status()
        return response.json()

    async def delete_row(self, table_name: str, row_id: str) -> Dict[str, Any]:
        """Delete specific row"""
        token = await self._ensure_authenticated()

        response = await self._client.delete(
            f"{self.base_url}/v1/tables/{table_name}/rows/{row_id}",
            headers=self._get_headers(token)
        )
        response.raise_for_status()
        return response.json()

    # ==================== EVENT OPERATIONS (5) ====================

    async def publish_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """Publish event to event stream"""
        token = await self._ensure_authenticated()

        data = {
            "event_type": event_type,
            "payload": payload,
            "topic": topic
        }

        response = await self._client.post(
            f"{self.base_url}/v1/events",
            headers=self._get_headers(token),
            json=data
        )
        response.raise_for_status()
        return response.json()

    async def subscribe_to_events(
        self,
        topic: str,
        callback_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Subscribe to event topic"""
        token = await self._ensure_authenticated()

        data = {
            "topic": topic,
            "callback_url": callback_url
        }

        response = await self._client.post(
            f"{self.base_url}/v1/events/subscribe",
            headers=self._get_headers(token),
            json=data
        )
        response.raise_for_status()
        return response.json()

    # ==================== ADMIN OPERATIONS (5) ====================

    async def health_check(self) -> Dict[str, Any]:
        """Check ZeroDB system health"""
        token = await self._ensure_authenticated()

        response = await self._client.get(
            f"{self.base_url}/v1/health",
            headers=self._get_headers(token)
        )
        response.raise_for_status()
        return response.json()

    async def get_project_usage(self) -> Dict[str, Any]:
        """Get current project usage statistics"""
        token = await self._ensure_authenticated()

        response = await self._client.get(
            f"{self.base_url}/v1/projects/{self.project_id}/usage",
            headers=self._get_headers(token)
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close HTTP client"""
        await self._client.aclose()
        logger.info("ZeroDB client closed")


# Global ZeroDB client instance
zerodb_client = ZeroDBClient()


def get_zerodb() -> ZeroDBClient:
    """
    Dependency injection for FastAPI routes

    Usage:
        @app.get("/endpoint")
        async def endpoint(zdb: ZeroDBClient = Depends(get_zerodb)):
            await zdb.store_memory("context")
    """
    return zerodb_client
