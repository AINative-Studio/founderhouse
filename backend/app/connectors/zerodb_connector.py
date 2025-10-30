"""
ZeroDB MCP Connector
Handles vector storage and semantic search
"""
from typing import Dict, Any, List, Optional

from app.connectors.base_connector import BaseConnector, ConnectorResponse, ConnectorStatus, ConnectorError


class ZeroDBConnector(BaseConnector):
    """Connector for ZeroDB vector storage"""

    @property
    def platform_name(self) -> str:
        return "zerodb"

    @property
    def base_url(self) -> str:
        # ZeroDB typically uses direct PostgreSQL connection with pgvector
        # This connector provides a REST-like interface for consistency
        return self.config.get("base_url", "http://localhost:5432")

    async def test_connection(self) -> ConnectorResponse:
        """Test connection to ZeroDB"""
        try:
            self.validate_credentials()
            # Test by attempting a simple health check
            return ConnectorResponse(
                status=ConnectorStatus.SUCCESS,
                data={"connected": True, "vector_engine": "pgvector"},
                metadata={"platform": self.platform_name}
            )
        except Exception as e:
            self.logger.error(f"ZeroDB connection test failed: {str(e)}")
            return ConnectorResponse(
                status=ConnectorStatus.ERROR,
                error=str(e),
                metadata={"platform": self.platform_name}
            )

    async def get_user_info(self) -> ConnectorResponse:
        """Get database user information"""
        return ConnectorResponse(
            status=ConnectorStatus.SUCCESS,
            data={"database": "zerodb", "engine": "pgvector"},
            metadata={"platform": self.platform_name}
        )

    async def store_embedding(
        self,
        collection: str,
        document_id: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConnectorResponse:
        """
        Store an embedding vector

        Args:
            collection: Collection name
            document_id: Unique document identifier
            embedding: Vector embedding
            metadata: Optional document metadata

        Returns:
            ConnectorResponse with storage result
        """
        json_data = {
            "collection": collection,
            "document_id": document_id,
            "embedding": embedding,
            "metadata": metadata or {}
        }
        return await self.make_request("POST", "/embeddings", json=json_data)

    async def search_similar(
        self,
        collection: str,
        query_embedding: List[float],
        limit: int = 10,
        threshold: float = 0.7,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> ConnectorResponse:
        """
        Search for similar embeddings

        Args:
            collection: Collection to search in
            query_embedding: Query vector
            limit: Number of results to return
            threshold: Minimum similarity threshold
            filter_metadata: Optional metadata filters

        Returns:
            ConnectorResponse with search results
        """
        json_data = {
            "collection": collection,
            "query_embedding": query_embedding,
            "limit": limit,
            "threshold": threshold
        }
        if filter_metadata:
            json_data["filter"] = filter_metadata

        return await self.make_request("POST", "/search", json=json_data)

    async def get_embedding(
        self,
        collection: str,
        document_id: str
    ) -> ConnectorResponse:
        """
        Get a specific embedding

        Args:
            collection: Collection name
            document_id: Document identifier

        Returns:
            ConnectorResponse with embedding data
        """
        params = {"collection": collection}
        return await self.make_request("GET", f"/embeddings/{document_id}", params=params)

    async def delete_embedding(
        self,
        collection: str,
        document_id: str
    ) -> ConnectorResponse:
        """
        Delete an embedding

        Args:
            collection: Collection name
            document_id: Document identifier

        Returns:
            ConnectorResponse with deletion status
        """
        params = {"collection": collection}
        return await self.make_request("DELETE", f"/embeddings/{document_id}", params=params)

    async def list_collections(self) -> ConnectorResponse:
        """
        List all collections

        Returns:
            ConnectorResponse with collections list
        """
        return await self.make_request("GET", "/collections")

    async def create_collection(
        self,
        name: str,
        dimension: int = 1536,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConnectorResponse:
        """
        Create a new collection

        Args:
            name: Collection name
            dimension: Vector dimension
            metadata: Optional collection metadata

        Returns:
            ConnectorResponse with created collection
        """
        json_data = {
            "name": name,
            "dimension": dimension,
            "metadata": metadata or {}
        }
        return await self.make_request("POST", "/collections", json=json_data)

    async def get_collection_stats(self, collection: str) -> ConnectorResponse:
        """
        Get collection statistics

        Args:
            collection: Collection name

        Returns:
            ConnectorResponse with collection stats
        """
        return await self.make_request("GET", f"/collections/{collection}/stats")
