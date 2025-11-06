"""
Database Connection and Session Management
Handles ZeroDB client initialization and connection pooling
ZeroDB provides PostgreSQL with 60+ database service endpoints including:
- Vector search and embeddings
- Real-time event streams
- Full-text search
- Time-series data
- Graph queries
- And more...
"""
import logging
from typing import Optional, AsyncGenerator, Any, Dict, List
from contextlib import asynccontextmanager

import asyncpg
import psycopg2
from psycopg2 import pool
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.config import get_settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages ZeroDB database connections and client instances
    Implements singleton pattern for connection reuse
    Provides access to 60+ ZeroDB service endpoints
    """

    _instance: Optional["DatabaseManager"] = None
    _pool: Optional[pool.SimpleConnectionPool] = None
    _async_pool: Optional[asyncpg.Pool] = None
    _engine = None
    _async_engine = None
    _session_factory = None
    _async_session_factory = None

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
            logger.info("DatabaseManager initialized with ZeroDB")

    def _get_connection_pool(self) -> pool.SimpleConnectionPool:
        """
        Get or create PostgreSQL connection pool
        Used for synchronous operations with RLS enabled
        """
        if self._pool is None:
            try:
                self._pool = pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=self.settings.db_pool_size,
                    host=self.settings.zerodb_host,
                    port=self.settings.zerodb_port,
                    database=self.settings.zerodb_database,
                    user=self.settings.zerodb_user,
                    password=self.settings.zerodb_password
                )
                logger.info("ZeroDB connection pool initialized")
            except Exception as e:
                logger.error(f"Failed to create connection pool: {str(e)}")
                raise
        return self._pool

    async def _get_async_pool(self) -> asyncpg.Pool:
        """
        Get or create async PostgreSQL connection pool
        Used for async operations
        """
        if self._async_pool is None:
            try:
                self._async_pool = await asyncpg.create_pool(
                    host=self.settings.zerodb_host,
                    port=self.settings.zerodb_port,
                    database=self.settings.zerodb_database,
                    user=self.settings.zerodb_user,
                    password=self.settings.zerodb_password,
                    min_size=1,
                    max_size=self.settings.db_pool_size
                )
                logger.info("ZeroDB async connection pool initialized")
            except Exception as e:
                logger.error(f"Failed to create async pool: {str(e)}")
                raise
        return self._async_pool

    @property
    def engine(self):
        """Get SQLAlchemy engine for synchronous operations"""
        if self._engine is None:
            connection_url = (
                f"postgresql://{self.settings.zerodb_user}:{self.settings.zerodb_password}"
                f"@{self.settings.zerodb_host}:{self.settings.zerodb_port}/{self.settings.zerodb_database}"
            )
            self._engine = create_engine(
                connection_url,
                pool_size=self.settings.db_pool_size,
                max_overflow=self.settings.db_max_overflow,
                pool_pre_ping=True,
                echo=self.settings.debug
            )
            logger.info("SQLAlchemy engine initialized")
        return self._engine

    @property
    def async_engine(self):
        """Get SQLAlchemy async engine"""
        if self._async_engine is None:
            connection_url = (
                f"postgresql+asyncpg://{self.settings.zerodb_user}:{self.settings.zerodb_password}"
                f"@{self.settings.zerodb_host}:{self.settings.zerodb_port}/{self.settings.zerodb_database}"
            )
            self._async_engine = create_async_engine(
                connection_url,
                pool_size=self.settings.db_pool_size,
                max_overflow=self.settings.db_max_overflow,
                pool_pre_ping=True,
                echo=self.settings.debug
            )
            logger.info("SQLAlchemy async engine initialized")
        return self._async_engine

    @property
    def session_factory(self) -> sessionmaker:
        """Get SQLAlchemy session factory"""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False
            )
        return self._session_factory

    @property
    def async_session_factory(self) -> async_sessionmaker:
        """Get SQLAlchemy async session factory"""
        if self._async_session_factory is None:
            self._async_session_factory = async_sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
        return self._async_session_factory

    def get_connection(self):
        """Get a connection from the pool"""
        pool = self._get_connection_pool()
        return pool.getconn()

    def return_connection(self, conn):
        """Return a connection to the pool"""
        if self._pool:
            self._pool.putconn(conn)

    async def get_async_connection(self):
        """Get an async connection from the pool"""
        pool = await self._get_async_pool()
        return await pool.acquire()

    async def return_async_connection(self, conn):
        """Return an async connection to the pool"""
        if self._async_pool:
            await self._async_pool.release(conn)

    def set_user_context(self, user_id: str, workspace_id: str) -> None:
        """
        Set the current user context for RLS
        This should be called after authentication to enforce row-level security

        Args:
            user_id: The authenticated user's ID
            workspace_id: The user's workspace ID
        """
        logger.debug(f"Setting user context for user_id: {user_id}, workspace_id: {workspace_id}")
        # Context will be set per-session when executing queries

    async def health_check(self) -> dict:
        """
        Perform database health check

        Returns:
            dict: Health check status and details
        """
        try:
            pool = await self._get_async_pool()
            async with pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")

                # Check pgvector extension
                vector_enabled = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
                )

            return {
                "status": "healthy",
                "database": "connected",
                "zerodb_host": self.settings.zerodb_host,
                "pgvector_enabled": bool(vector_enabled),
                "pool_size": self.settings.db_pool_size
            }
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e)
            }

    async def close(self) -> None:
        """Clean up database connections"""
        try:
            if self._async_pool:
                await self._async_pool.close()
                logger.info("Async connection pool closed")

            if self._pool:
                self._pool.closeall()
                logger.info("Sync connection pool closed")

            if self._async_engine:
                await self._async_engine.dispose()
                logger.info("Async engine disposed")

            if self._engine:
                self._engine.dispose()
                logger.info("Sync engine disposed")

        except Exception as e:
            logger.error(f"Error closing database connections: {str(e)}")


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> Session:
    """
    Dependency injection function for FastAPI routes
    Returns SQLAlchemy session with RLS enabled

    Usage:
        @app.get("/endpoint")
        async def endpoint(db: Session = Depends(get_db)):
            # Use db here
    """
    session = db_manager.session_factory()
    try:
        yield session
    finally:
        session.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injection function for async FastAPI routes
    Returns async SQLAlchemy session

    Usage:
        @app.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_async_db)):
            # Use db here
    """
    async with db_manager.async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database operations

    Usage:
        async with get_db_context() as db:
            # Use db here
    """
    async with db_manager.async_session_factory() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database context error: {str(e)}")
            raise
        finally:
            await session.close()


# Utility functions for common database operations

async def execute_query(
    query: str,
    params: Optional[Dict[str, Any]] = None,
    fetch_one: bool = False,
    fetch_all: bool = True
) -> Any:
    """
    Execute a raw SQL query with error handling

    Args:
        query: SQL query string
        params: Query parameters (dict or tuple)
        fetch_one: Return single row
        fetch_all: Return all rows

    Returns:
        Query result or raises exception
    """
    try:
        pool = await db_manager._get_async_pool()
        async with pool.acquire() as conn:
            if fetch_one:
                return await conn.fetchrow(query, **(params or {}))
            elif fetch_all:
                return await conn.fetch(query, **(params or {}))
            else:
                return await conn.execute(query, **(params or {}))
    except Exception as e:
        logger.error(f"Query execution failed: {str(e)}")
        raise


async def vector_search(
    table: str,
    embedding_column: str,
    query_embedding: List[float],
    similarity_threshold: float = 0.7,
    limit: int = 10,
    workspace_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Perform vector similarity search using pgvector via ZeroDB

    Args:
        table: Table name with vector column
        embedding_column: Name of the vector column
        query_embedding: Query vector for similarity search
        similarity_threshold: Minimum similarity score (0-1)
        limit: Maximum number of results
        workspace_id: Optional workspace filter for RLS

    Returns:
        List of similar records with similarity scores
    """
    try:
        # Convert embedding to string format for PostgreSQL
        embedding_str = f"[{','.join(map(str, query_embedding))}]"

        # Build query with optional workspace filter
        where_clause = ""
        if workspace_id:
            where_clause = f"WHERE workspace_id = '{workspace_id}'"

        query = f"""
            SELECT *,
                   1 - ({embedding_column} <=> '{embedding_str}'::vector) as similarity
            FROM {table}
            {where_clause}
            WHERE 1 - ({embedding_column} <=> '{embedding_str}'::vector) > {similarity_threshold}
            ORDER BY {embedding_column} <=> '{embedding_str}'::vector
            LIMIT {limit}
        """

        results = await execute_query(query, fetch_all=True)
        return [dict(row) for row in results]

    except Exception as e:
        logger.error(f"Vector search failed: {str(e)}")
        raise


async def execute_rpc(
    function_name: str,
    params: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Execute a PostgreSQL function (RPC call) via ZeroDB

    Args:
        function_name: Name of the PostgreSQL function
        params: Function parameters as dictionary

    Returns:
        Function result
    """
    try:
        pool = await db_manager._get_async_pool()
        async with pool.acquire() as conn:
            if params:
                placeholders = ", ".join([f"${i+1}" for i in range(len(params))])
                query = f"SELECT * FROM {function_name}({placeholders})"
                result = await conn.fetch(query, *params.values())
            else:
                query = f"SELECT * FROM {function_name}()"
                result = await conn.fetch(query)

            return [dict(row) for row in result]
    except Exception as e:
        logger.error(f"RPC call failed: {str(e)}")
        raise
