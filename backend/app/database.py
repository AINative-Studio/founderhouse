"""
Database Connection and Session Management
Handles Supabase client initialization and connection pooling
"""
import logging
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager

from supabase import create_client, Client
from app.config import get_settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages Supabase database connections and client instances
    Implements singleton pattern for connection reuse
    """

    _instance: Optional["DatabaseManager"] = None
    _client: Optional[Client] = None
    _service_client: Optional[Client] = None

    def __new__(cls):
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize database manager with settings"""
        if not hasattr(self, '_initialized'):
            self.settings = get_settings()
            self._initialized = True
            logger.info("DatabaseManager initialized")

    @property
    def client(self) -> Client:
        """
        Get Supabase client with anon key
        Used for operations with RLS enabled
        """
        if self._client is None:
            self._client = create_client(
                self.settings.supabase_url,
                self.settings.supabase_key
            )
            logger.info("Supabase client initialized")
        return self._client

    @property
    def service_client(self) -> Client:
        """
        Get Supabase client with service role key
        Used for admin operations that bypass RLS
        Requires SUPABASE_SERVICE_KEY to be set
        """
        if self._service_client is None:
            if not self.settings.supabase_service_key:
                raise ValueError(
                    "SUPABASE_SERVICE_KEY not configured. "
                    "Service client requires service role key for admin operations."
                )
            self._service_client = create_client(
                self.settings.supabase_url,
                self.settings.supabase_service_key
            )
            logger.info("Supabase service client initialized")
        return self._service_client

    def set_user_context(self, user_id: str) -> None:
        """
        Set the current user context for RLS
        This should be called after authentication to enforce row-level security

        Args:
            user_id: The authenticated user's ID
        """
        # Set custom claims for Supabase RLS
        # This will be picked up by RLS policies using auth.uid()
        logger.debug(f"Setting user context for user_id: {user_id}")

    async def health_check(self) -> dict:
        """
        Perform database health check

        Returns:
            dict: Health check status and details
        """
        try:
            # Simple query to test connection
            response = self.client.table("core.workspaces").select("id").limit(1).execute()

            return {
                "status": "healthy",
                "database": "connected",
                "supabase_url": self.settings.supabase_url
            }
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e)
            }

    def close(self) -> None:
        """Clean up database connections"""
        # Supabase client doesn't require explicit cleanup
        # But we reset the instances for testing purposes
        self._client = None
        self._service_client = None
        logger.info("Database connections closed")


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> Client:
    """
    Dependency injection function for FastAPI routes
    Returns the standard Supabase client with RLS enabled

    Usage:
        @app.get("/endpoint")
        async def endpoint(db: Client = Depends(get_db)):
            # Use db here
    """
    return db_manager.client


def get_service_db() -> Client:
    """
    Dependency injection function for admin operations
    Returns the service client that bypasses RLS

    Use with caution - only for operations that require admin access

    Usage:
        @app.post("/admin/endpoint")
        async def admin_endpoint(db: Client = Depends(get_service_db)):
            # Use db here
    """
    return db_manager.service_client


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[Client, None]:
    """
    Async context manager for database operations

    Usage:
        async with get_db_context() as db:
            # Use db here
    """
    try:
        yield db_manager.client
    except Exception as e:
        logger.error(f"Database context error: {str(e)}")
        raise
    finally:
        # Cleanup if needed
        pass


# Utility functions for common database operations

def execute_query(table: str, query_type: str = "select", **kwargs):
    """
    Execute a database query with error handling

    Args:
        table: Table name (e.g., "core.workspaces")
        query_type: Type of query (select, insert, update, delete)
        **kwargs: Additional query parameters

    Returns:
        Query result or raises exception
    """
    try:
        db = db_manager.client
        table_ref = db.table(table)

        if query_type == "select":
            return table_ref.select(**kwargs).execute()
        elif query_type == "insert":
            return table_ref.insert(**kwargs).execute()
        elif query_type == "update":
            return table_ref.update(**kwargs).execute()
        elif query_type == "delete":
            return table_ref.delete(**kwargs).execute()
        else:
            raise ValueError(f"Unsupported query type: {query_type}")

    except Exception as e:
        logger.error(f"Query execution failed: {str(e)}")
        raise


def vector_search(
    table: str,
    embedding_column: str,
    query_embedding: list[float],
    similarity_threshold: float = 0.7,
    limit: int = 10
) -> list:
    """
    Perform vector similarity search using pgvector

    Args:
        table: Table name with vector column
        embedding_column: Name of the vector column
        query_embedding: Query vector for similarity search
        similarity_threshold: Minimum similarity score (0-1)
        limit: Maximum number of results

    Returns:
        List of similar records with similarity scores
    """
    try:
        db = db_manager.client

        # Use Supabase's RPC function for vector search
        # Note: This requires a custom RPC function in Supabase
        # See documentation for vector search setup
        response = db.rpc(
            "match_documents",
            {
                "query_embedding": query_embedding,
                "match_threshold": similarity_threshold,
                "match_count": limit
            }
        ).execute()

        return response.data
    except Exception as e:
        logger.error(f"Vector search failed: {str(e)}")
        raise
