"""
Comprehensive tests for database layer - app/database.py
Tests all database functionality including:
- DatabaseManager singleton pattern
- Connection pool management (sync and async)
- SQLAlchemy engine and session creation
- Health checks and connection lifecycle
- Utility functions (execute_query, vector_search, execute_rpc)
- Dependency injection helpers
- Error handling and edge cases

Target: 90%+ coverage of database.py (from 38% baseline)
"""
import asyncio
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch, call
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg
import psycopg2
from psycopg2 import pool as psycopg2_pool
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Import the module under test
from app.database import (
    DatabaseManager,
    db_manager,
    get_db,
    get_async_db,
    get_db_context,
    execute_query,
    vector_search,
    execute_rpc,
    get_supabase_client,
)


# Fixtures for mocking settings
@pytest.fixture
def mock_settings():
    """Mock settings with all required database configuration"""
    settings = Mock()
    settings.zerodb_host = "localhost"
    settings.zerodb_port = 5432
    settings.zerodb_database = "test_db"
    settings.zerodb_user = "test_user"
    settings.zerodb_username = "test_user"
    settings.zerodb_password = "test_password"
    settings.db_pool_size = 10
    settings.db_max_overflow = 20
    settings.debug = False
    return settings


@pytest.fixture
def clean_database_manager():
    """Reset DatabaseManager singleton state between tests"""
    # Clear singleton instance
    DatabaseManager._instance = None
    DatabaseManager._pool = None
    DatabaseManager._async_pool = None
    DatabaseManager._engine = None
    DatabaseManager._async_engine = None
    DatabaseManager._session_factory = None
    DatabaseManager._async_session_factory = None
    yield
    # Clean up after test
    DatabaseManager._instance = None
    DatabaseManager._pool = None
    DatabaseManager._async_pool = None
    DatabaseManager._engine = None
    DatabaseManager._async_engine = None
    DatabaseManager._session_factory = None
    DatabaseManager._async_session_factory = None


class TestDatabaseManagerSingleton:
    """Test DatabaseManager singleton pattern implementation"""

    def test_singleton_pattern(self, clean_database_manager, mock_settings):
        """Test that DatabaseManager implements singleton correctly"""
        with patch('app.database.get_settings', return_value=mock_settings):
            manager1 = DatabaseManager()
            manager2 = DatabaseManager()

            assert manager1 is manager2
            assert id(manager1) == id(manager2)

    def test_initialization_only_once(self, clean_database_manager, mock_settings):
        """Test that __init__ only runs once due to _initialized flag"""
        with patch('app.database.get_settings', return_value=mock_settings):
            manager = DatabaseManager()
            assert hasattr(manager, '_initialized')
            assert manager._initialized is True
            assert manager.settings == mock_settings

    def test_multiple_init_calls_same_settings(self, clean_database_manager, mock_settings):
        """Test that multiple instantiations use the same settings"""
        with patch('app.database.get_settings', return_value=mock_settings) as mock_get_settings:
            manager1 = DatabaseManager()
            manager2 = DatabaseManager()
            manager3 = DatabaseManager()

            # get_settings should only be called once
            assert mock_get_settings.call_count == 1
            assert manager1.settings is manager2.settings is manager3.settings


class TestConnectionPoolManagement:
    """Test synchronous connection pool creation and management"""

    def test_get_connection_pool_creates_new_pool(self, clean_database_manager, mock_settings):
        """Test that _get_connection_pool creates a new pool if none exists"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.pool.SimpleConnectionPool') as mock_pool_class:
                mock_pool = Mock()
                mock_pool_class.return_value = mock_pool

                manager = DatabaseManager()
                result = manager._get_connection_pool()

                assert result is mock_pool
                mock_pool_class.assert_called_once_with(
                    minconn=1,
                    maxconn=mock_settings.db_pool_size,
                    host=mock_settings.zerodb_host,
                    port=mock_settings.zerodb_port,
                    database=mock_settings.zerodb_database,
                    user=mock_settings.zerodb_user,
                    password=mock_settings.zerodb_password
                )

    def test_get_connection_pool_reuses_existing(self, clean_database_manager, mock_settings):
        """Test that _get_connection_pool reuses existing pool"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.pool.SimpleConnectionPool') as mock_pool_class:
                mock_pool = Mock()
                mock_pool_class.return_value = mock_pool

                manager = DatabaseManager()
                pool1 = manager._get_connection_pool()
                pool2 = manager._get_connection_pool()

                assert pool1 is pool2
                assert mock_pool_class.call_count == 1

    def test_get_connection_pool_error_handling(self, clean_database_manager, mock_settings):
        """Test error handling when pool creation fails"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.pool.SimpleConnectionPool') as mock_pool_class:
                mock_pool_class.side_effect = Exception("Connection failed")

                manager = DatabaseManager()
                with pytest.raises(Exception) as exc_info:
                    manager._get_connection_pool()

                assert "Connection failed" in str(exc_info.value)

    def test_get_connection(self, clean_database_manager, mock_settings):
        """Test getting a connection from the pool"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.pool.SimpleConnectionPool') as mock_pool_class:
                mock_pool = Mock()
                mock_conn = Mock()
                mock_pool.getconn.return_value = mock_conn
                mock_pool_class.return_value = mock_pool

                manager = DatabaseManager()
                conn = manager.get_connection()

                assert conn is mock_conn
                mock_pool.getconn.assert_called_once()

    def test_return_connection(self, clean_database_manager, mock_settings):
        """Test returning a connection to the pool"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.pool.SimpleConnectionPool') as mock_pool_class:
                mock_pool = Mock()
                mock_conn = Mock()
                mock_pool_class.return_value = mock_pool

                manager = DatabaseManager()
                manager._get_connection_pool()  # Initialize pool
                manager.return_connection(mock_conn)

                mock_pool.putconn.assert_called_once_with(mock_conn)

    def test_return_connection_no_pool(self, clean_database_manager, mock_settings):
        """Test returning connection when no pool exists"""
        with patch('app.database.get_settings', return_value=mock_settings):
            manager = DatabaseManager()
            mock_conn = Mock()

            # Should not raise error
            manager.return_connection(mock_conn)


class TestAsyncConnectionPoolManagement:
    """Test asynchronous connection pool creation and management"""

    @pytest.mark.asyncio
    async def test_get_async_pool_creates_new_pool(self, clean_database_manager, mock_settings):
        """Test that _get_async_pool creates a new pool if none exists"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
                mock_pool = AsyncMock()
                mock_create_pool.return_value = mock_pool

                manager = DatabaseManager()
                result = await manager._get_async_pool()

                assert result is mock_pool
                mock_create_pool.assert_called_once_with(
                    host=mock_settings.zerodb_host,
                    port=mock_settings.zerodb_port,
                    database=mock_settings.zerodb_database,
                    user=mock_settings.zerodb_user,
                    password=mock_settings.zerodb_password,
                    min_size=1,
                    max_size=mock_settings.db_pool_size
                )

    @pytest.mark.asyncio
    async def test_get_async_pool_reuses_existing(self, clean_database_manager, mock_settings):
        """Test that _get_async_pool reuses existing pool"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
                mock_pool = AsyncMock()
                mock_create_pool.return_value = mock_pool

                manager = DatabaseManager()
                pool1 = await manager._get_async_pool()
                pool2 = await manager._get_async_pool()

                assert pool1 is pool2
                assert mock_create_pool.call_count == 1

    @pytest.mark.asyncio
    async def test_get_async_pool_error_handling(self, clean_database_manager, mock_settings):
        """Test error handling when async pool creation fails"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
                mock_create_pool.side_effect = Exception("Async connection failed")

                manager = DatabaseManager()
                with pytest.raises(Exception) as exc_info:
                    await manager._get_async_pool()

                assert "Async connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_async_connection(self, clean_database_manager, mock_settings):
        """Test getting an async connection from the pool"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
                mock_pool = AsyncMock()
                mock_conn = AsyncMock()
                mock_pool.acquire = AsyncMock(return_value=mock_conn)
                mock_create_pool.return_value = mock_pool

                manager = DatabaseManager()
                conn = await manager.get_async_connection()

                assert conn is mock_conn
                mock_pool.acquire.assert_called_once()

    @pytest.mark.asyncio
    async def test_return_async_connection(self, clean_database_manager, mock_settings):
        """Test returning an async connection to the pool"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
                mock_pool = AsyncMock()
                mock_conn = AsyncMock()
                mock_pool.release = AsyncMock()
                mock_create_pool.return_value = mock_pool

                manager = DatabaseManager()
                await manager._get_async_pool()  # Initialize pool
                await manager.return_async_connection(mock_conn)

                mock_pool.release.assert_called_once_with(mock_conn)

    @pytest.mark.asyncio
    async def test_return_async_connection_no_pool(self, clean_database_manager, mock_settings):
        """Test returning async connection when no pool exists"""
        with patch('app.database.get_settings', return_value=mock_settings):
            manager = DatabaseManager()
            mock_conn = AsyncMock()

            # Should not raise error
            await manager.return_async_connection(mock_conn)


class TestSQLAlchemyEngines:
    """Test SQLAlchemy engine creation (sync and async)"""

    def test_engine_property_creates_engine(self, clean_database_manager, mock_settings):
        """Test that engine property creates SQLAlchemy engine"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.create_engine') as mock_create_engine:
                mock_engine = Mock()
                mock_create_engine.return_value = mock_engine

                manager = DatabaseManager()
                engine = manager.engine

                assert engine is mock_engine
                expected_url = (
                    f"postgresql://{mock_settings.zerodb_user}:{mock_settings.zerodb_password}"
                    f"@{mock_settings.zerodb_host}:{mock_settings.zerodb_port}/{mock_settings.zerodb_database}"
                )
                mock_create_engine.assert_called_once_with(
                    expected_url,
                    pool_size=mock_settings.db_pool_size,
                    max_overflow=mock_settings.db_max_overflow,
                    pool_pre_ping=True,
                    echo=mock_settings.debug
                )

    def test_engine_property_reuses_existing(self, clean_database_manager, mock_settings):
        """Test that engine property reuses existing engine"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.create_engine') as mock_create_engine:
                mock_engine = Mock()
                mock_create_engine.return_value = mock_engine

                manager = DatabaseManager()
                engine1 = manager.engine
                engine2 = manager.engine

                assert engine1 is engine2
                assert mock_create_engine.call_count == 1

    def test_async_engine_property_creates_engine(self, clean_database_manager, mock_settings):
        """Test that async_engine property creates async SQLAlchemy engine"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.create_async_engine') as mock_create_async_engine:
                mock_engine = Mock()
                mock_create_async_engine.return_value = mock_engine

                manager = DatabaseManager()
                engine = manager.async_engine

                assert engine is mock_engine
                expected_url = (
                    f"postgresql+asyncpg://{mock_settings.zerodb_user}:{mock_settings.zerodb_password}"
                    f"@{mock_settings.zerodb_host}:{mock_settings.zerodb_port}/{mock_settings.zerodb_database}"
                )
                mock_create_async_engine.assert_called_once_with(
                    expected_url,
                    pool_size=mock_settings.db_pool_size,
                    max_overflow=mock_settings.db_max_overflow,
                    pool_pre_ping=True,
                    echo=mock_settings.debug
                )

    def test_async_engine_property_reuses_existing(self, clean_database_manager, mock_settings):
        """Test that async_engine property reuses existing engine"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.create_async_engine') as mock_create_async_engine:
                mock_engine = Mock()
                mock_create_async_engine.return_value = mock_engine

                manager = DatabaseManager()
                engine1 = manager.async_engine
                engine2 = manager.async_engine

                assert engine1 is engine2
                assert mock_create_async_engine.call_count == 1

    def test_engine_with_debug_enabled(self, clean_database_manager, mock_settings):
        """Test engine creation with debug mode enabled"""
        mock_settings.debug = True

        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.create_engine') as mock_create_engine:
                mock_engine = Mock()
                mock_create_engine.return_value = mock_engine

                manager = DatabaseManager()
                _ = manager.engine

                call_kwargs = mock_create_engine.call_args[1]
                assert call_kwargs['echo'] is True


class TestSessionFactories:
    """Test SQLAlchemy session factory creation"""

    def test_session_factory_property(self, clean_database_manager, mock_settings):
        """Test that session_factory property creates sessionmaker"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.create_engine') as mock_create_engine:
                with patch('app.database.sessionmaker') as mock_sessionmaker:
                    mock_engine = Mock()
                    mock_create_engine.return_value = mock_engine
                    mock_factory = Mock()
                    mock_sessionmaker.return_value = mock_factory

                    manager = DatabaseManager()
                    factory = manager.session_factory

                    assert factory is mock_factory
                    mock_sessionmaker.assert_called_once_with(
                        bind=mock_engine,
                        autocommit=False,
                        autoflush=False
                    )

    def test_session_factory_reuses_existing(self, clean_database_manager, mock_settings):
        """Test that session_factory property reuses existing factory"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.create_engine'):
                with patch('app.database.sessionmaker') as mock_sessionmaker:
                    mock_factory = Mock()
                    mock_sessionmaker.return_value = mock_factory

                    manager = DatabaseManager()
                    factory1 = manager.session_factory
                    factory2 = manager.session_factory

                    assert factory1 is factory2
                    assert mock_sessionmaker.call_count == 1

    def test_async_session_factory_property(self, clean_database_manager, mock_settings):
        """Test that async_session_factory property creates async sessionmaker"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.create_async_engine') as mock_create_async_engine:
                with patch('app.database.async_sessionmaker') as mock_async_sessionmaker:
                    mock_engine = Mock()
                    mock_create_async_engine.return_value = mock_engine
                    mock_factory = Mock()
                    mock_async_sessionmaker.return_value = mock_factory

                    manager = DatabaseManager()
                    factory = manager.async_session_factory

                    assert factory is mock_factory
                    mock_async_sessionmaker.assert_called_once_with(
                        bind=mock_engine,
                        class_=AsyncSession,
                        autocommit=False,
                        autoflush=False,
                        expire_on_commit=False
                    )

    def test_async_session_factory_reuses_existing(self, clean_database_manager, mock_settings):
        """Test that async_session_factory property reuses existing factory"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.create_async_engine'):
                with patch('app.database.async_sessionmaker') as mock_async_sessionmaker:
                    mock_factory = Mock()
                    mock_async_sessionmaker.return_value = mock_factory

                    manager = DatabaseManager()
                    factory1 = manager.async_session_factory
                    factory2 = manager.async_session_factory

                    assert factory1 is factory2
                    assert mock_async_sessionmaker.call_count == 1


class TestUserContext:
    """Test RLS user context management"""

    def test_set_user_context(self, clean_database_manager, mock_settings):
        """Test setting user context for RLS"""
        with patch('app.database.get_settings', return_value=mock_settings):
            manager = DatabaseManager()

            # Should not raise error
            manager.set_user_context("user-123", "workspace-456")

    def test_set_user_context_with_different_values(self, clean_database_manager, mock_settings):
        """Test setting user context with various values"""
        with patch('app.database.get_settings', return_value=mock_settings):
            manager = DatabaseManager()

            # Test with different user IDs and workspace IDs
            manager.set_user_context("user-1", "ws-1")
            manager.set_user_context("user-2", "ws-2")
            manager.set_user_context("", "")


class TestHealthCheck:
    """Test database health check functionality"""

    @pytest.mark.asyncio
    async def test_health_check_success(self, clean_database_manager, mock_settings):
        """Test successful health check"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
                # Create mock connection and pool
                mock_conn = AsyncMock()
                mock_conn.fetchval = AsyncMock(side_effect=[1, True])  # SELECT 1, then vector check

                mock_pool = AsyncMock()
                mock_pool.acquire = MagicMock(return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_conn),
                    __aexit__=AsyncMock()
                ))
                mock_create_pool.return_value = mock_pool

                manager = DatabaseManager()
                result = await manager.health_check()

                assert result["status"] == "healthy"
                assert result["database"] == "connected"
                assert result["zerodb_host"] == mock_settings.zerodb_host
                assert result["pgvector_enabled"] is True
                assert result["pool_size"] == mock_settings.db_pool_size

    @pytest.mark.asyncio
    async def test_health_check_no_pgvector(self, clean_database_manager, mock_settings):
        """Test health check when pgvector is not enabled"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
                mock_conn = AsyncMock()
                mock_conn.fetchval = AsyncMock(side_effect=[1, False])  # SELECT 1, no vector

                mock_pool = AsyncMock()
                mock_pool.acquire = MagicMock(return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_conn),
                    __aexit__=AsyncMock()
                ))
                mock_create_pool.return_value = mock_pool

                manager = DatabaseManager()
                result = await manager.health_check()

                assert result["status"] == "healthy"
                assert result["pgvector_enabled"] is False

    @pytest.mark.asyncio
    async def test_health_check_failure(self, clean_database_manager, mock_settings):
        """Test health check when database connection fails"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
                mock_create_pool.side_effect = Exception("Connection timeout")

                manager = DatabaseManager()
                result = await manager.health_check()

                assert result["status"] == "unhealthy"
                assert result["database"] == "disconnected"
                assert "Connection timeout" in result["error"]

    @pytest.mark.asyncio
    async def test_health_check_query_failure(self, clean_database_manager, mock_settings):
        """Test health check when query execution fails"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
                mock_conn = AsyncMock()
                mock_conn.fetchval = AsyncMock(side_effect=Exception("Query failed"))

                mock_pool = AsyncMock()
                mock_pool.acquire = MagicMock(return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_conn),
                    __aexit__=AsyncMock()
                ))
                mock_create_pool.return_value = mock_pool

                manager = DatabaseManager()
                result = await manager.health_check()

                assert result["status"] == "unhealthy"
                # The actual error could be about vector_enabled or query failed
                assert "error" in result


class TestConnectionCleanup:
    """Test database connection cleanup"""

    @pytest.mark.asyncio
    async def test_close_all_connections(self, clean_database_manager, mock_settings):
        """Test closing all database connections"""
        with patch('app.database.get_settings', return_value=mock_settings):
            mock_async_pool = AsyncMock()
            mock_async_pool.close = AsyncMock()

            mock_sync_pool = Mock()
            mock_sync_pool.closeall = Mock()

            mock_async_engine = AsyncMock()
            mock_async_engine.dispose = AsyncMock()

            mock_sync_engine = Mock()
            mock_sync_engine.dispose = Mock()

            manager = DatabaseManager()
            manager._async_pool = mock_async_pool
            manager._pool = mock_sync_pool
            manager._async_engine = mock_async_engine
            manager._engine = mock_sync_engine

            await manager.close()

            mock_async_pool.close.assert_called_once()
            mock_sync_pool.closeall.assert_called_once()
            mock_async_engine.dispose.assert_called_once()
            mock_sync_engine.dispose.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_no_connections(self, clean_database_manager, mock_settings):
        """Test close when no connections exist"""
        with patch('app.database.get_settings', return_value=mock_settings):
            manager = DatabaseManager()

            # Should not raise error
            await manager.close()

    @pytest.mark.asyncio
    async def test_close_with_errors(self, clean_database_manager, mock_settings):
        """Test close handles errors gracefully"""
        with patch('app.database.get_settings', return_value=mock_settings):
            mock_async_pool = AsyncMock()
            mock_async_pool.close = AsyncMock(side_effect=Exception("Close failed"))

            manager = DatabaseManager()
            manager._async_pool = mock_async_pool

            # Should not raise error, just log it
            await manager.close()


class TestDependencyInjection:
    """Test FastAPI dependency injection helpers"""

    def test_get_db_yields_session(self, clean_database_manager, mock_settings):
        """Test get_db generator yields session and closes it"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.db_manager') as mock_manager:
                mock_session = Mock(spec=Session)
                mock_manager.session_factory.return_value = mock_session

                # Use the generator
                gen = get_db()
                session = next(gen)

                assert session is mock_session

                # Finish the generator
                try:
                    next(gen)
                except StopIteration:
                    pass

                mock_session.close.assert_called_once()

    def test_get_db_closes_on_error(self, clean_database_manager, mock_settings):
        """Test get_db closes session even on error"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.db_manager') as mock_manager:
                mock_session = Mock(spec=Session)
                mock_manager.session_factory.return_value = mock_session

                gen = get_db()
                session = next(gen)

                # Simulate error by throwing exception into generator
                try:
                    gen.throw(Exception("Test error"))
                except Exception:
                    pass

                mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_async_db_yields_session(self, clean_database_manager, mock_settings):
        """Test get_async_db async generator yields session"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.db_manager') as mock_manager:
                mock_session = AsyncMock(spec=AsyncSession)
                mock_session.close = AsyncMock()

                # Create a proper async context manager
                @asynccontextmanager
                async def mock_factory():
                    yield mock_session

                mock_manager.async_session_factory.return_value = mock_factory()

                # Use the async generator
                gen = get_async_db()
                session = await gen.__anext__()

                assert session is mock_session

                # Finish the generator
                try:
                    await gen.__anext__()
                except StopAsyncIteration:
                    pass

                mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_db_context_success(self, clean_database_manager, mock_settings):
        """Test get_db_context async context manager"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.db_manager') as mock_manager:
                mock_session = AsyncMock(spec=AsyncSession)
                mock_session.close = AsyncMock()

                @asynccontextmanager
                async def mock_factory():
                    yield mock_session

                mock_manager.async_session_factory.return_value = mock_factory()

                async with get_db_context() as session:
                    assert session is mock_session

                mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_db_context_with_exception(self, clean_database_manager, mock_settings):
        """Test get_db_context rolls back on exception"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.db_manager') as mock_manager:
                mock_session = AsyncMock(spec=AsyncSession)
                mock_session.rollback = AsyncMock()
                mock_session.close = AsyncMock()

                @asynccontextmanager
                async def mock_factory():
                    yield mock_session

                mock_manager.async_session_factory.return_value = mock_factory()

                with pytest.raises(ValueError):
                    async with get_db_context() as session:
                        raise ValueError("Test error")

                mock_session.rollback.assert_called_once()
                mock_session.close.assert_called_once()


class TestExecuteQuery:
    """Test execute_query utility function"""

    @pytest.mark.asyncio
    async def test_execute_query_fetch_all(self, clean_database_manager, mock_settings):
        """Test execute_query with fetch_all=True"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.db_manager') as mock_manager:
                mock_row1 = {"id": 1, "name": "test1"}
                mock_row2 = {"id": 2, "name": "test2"}

                mock_conn = AsyncMock()
                mock_conn.fetch = AsyncMock(return_value=[mock_row1, mock_row2])

                mock_pool = AsyncMock()
                mock_pool.acquire = MagicMock(return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_conn),
                    __aexit__=AsyncMock()
                ))

                mock_manager._get_async_pool = AsyncMock(return_value=mock_pool)

                result = await execute_query("SELECT * FROM test")

                assert result == [mock_row1, mock_row2]
                mock_conn.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_query_fetch_one(self, clean_database_manager, mock_settings):
        """Test execute_query with fetch_one=True"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.db_manager') as mock_manager:
                mock_row = {"id": 1, "name": "test"}

                mock_conn = AsyncMock()
                mock_conn.fetchrow = AsyncMock(return_value=mock_row)

                mock_pool = AsyncMock()
                mock_pool.acquire = MagicMock(return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_conn),
                    __aexit__=AsyncMock()
                ))

                mock_manager._get_async_pool = AsyncMock(return_value=mock_pool)

                result = await execute_query("SELECT * FROM test LIMIT 1", fetch_one=True, fetch_all=False)

                assert result == mock_row
                mock_conn.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_query_execute_only(self, clean_database_manager, mock_settings):
        """Test execute_query with fetch_one=False and fetch_all=False"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.db_manager') as mock_manager:
                mock_conn = AsyncMock()
                mock_conn.execute = AsyncMock(return_value="INSERT 0 1")

                mock_pool = AsyncMock()
                mock_pool.acquire = MagicMock(return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_conn),
                    __aexit__=AsyncMock()
                ))

                mock_manager._get_async_pool = AsyncMock(return_value=mock_pool)

                result = await execute_query("INSERT INTO test VALUES (1)", fetch_one=False, fetch_all=False)

                assert result == "INSERT 0 1"
                mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_query_with_params(self, clean_database_manager, mock_settings):
        """Test execute_query with parameters"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.db_manager') as mock_manager:
                mock_conn = AsyncMock()
                mock_conn.fetch = AsyncMock(return_value=[])

                mock_pool = AsyncMock()
                mock_pool.acquire = MagicMock(return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_conn),
                    __aexit__=AsyncMock()
                ))

                mock_manager._get_async_pool = AsyncMock(return_value=mock_pool)

                params = {"id": 1, "name": "test"}
                await execute_query("SELECT * FROM test WHERE id = :id", params=params)

                # Verify params were passed
                call_args = mock_conn.fetch.call_args
                assert call_args is not None

    @pytest.mark.asyncio
    async def test_execute_query_error(self, clean_database_manager, mock_settings):
        """Test execute_query handles errors"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.db_manager') as mock_manager:
                # Make _get_async_pool raise the exception directly
                mock_manager._get_async_pool = AsyncMock(side_effect=Exception("Query failed"))

                with pytest.raises(Exception) as exc_info:
                    await execute_query("SELECT * FROM test")

                assert "Query failed" in str(exc_info.value)


class TestVectorSearch:
    """Test vector_search utility function"""

    @pytest.mark.asyncio
    async def test_vector_search_basic(self, clean_database_manager, mock_settings):
        """Test basic vector search"""
        with patch('app.database.execute_query', new_callable=AsyncMock) as mock_execute:
            mock_row1 = {"id": 1, "content": "test1", "similarity": 0.9}
            mock_row2 = {"id": 2, "content": "test2", "similarity": 0.85}
            mock_execute.return_value = [mock_row1, mock_row2]

            embedding = [0.1, 0.2, 0.3]
            result = await vector_search(
                table="documents",
                embedding_column="embedding",
                query_embedding=embedding,
                similarity_threshold=0.7,
                limit=10
            )

            assert len(result) == 2
            assert result[0]["similarity"] == 0.9
            assert result[1]["similarity"] == 0.85

    @pytest.mark.asyncio
    async def test_vector_search_with_workspace(self, clean_database_manager, mock_settings):
        """Test vector search with workspace filter"""
        with patch('app.database.execute_query', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = []

            embedding = [0.1, 0.2, 0.3]
            await vector_search(
                table="documents",
                embedding_column="embedding",
                query_embedding=embedding,
                workspace_id="workspace-123"
            )

            # Verify query contains workspace filter
            call_args = mock_execute.call_args[0]
            query = call_args[0]
            assert "workspace_id" in query
            assert "workspace-123" in query

    @pytest.mark.asyncio
    async def test_vector_search_empty_results(self, clean_database_manager, mock_settings):
        """Test vector search with no results"""
        with patch('app.database.execute_query', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = []

            embedding = [0.1, 0.2, 0.3]
            result = await vector_search(
                table="documents",
                embedding_column="embedding",
                query_embedding=embedding
            )

            assert result == []

    @pytest.mark.asyncio
    async def test_vector_search_error(self, clean_database_manager, mock_settings):
        """Test vector search error handling"""
        with patch('app.database.execute_query', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = Exception("Vector search failed")

            embedding = [0.1, 0.2, 0.3]
            with pytest.raises(Exception) as exc_info:
                await vector_search(
                    table="documents",
                    embedding_column="embedding",
                    query_embedding=embedding
                )

            assert "Vector search failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_vector_search_custom_threshold(self, clean_database_manager, mock_settings):
        """Test vector search with custom similarity threshold"""
        with patch('app.database.execute_query', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = []

            embedding = [0.1, 0.2, 0.3]
            await vector_search(
                table="documents",
                embedding_column="embedding",
                query_embedding=embedding,
                similarity_threshold=0.9,
                limit=5
            )

            call_args = mock_execute.call_args[0]
            query = call_args[0]
            assert "0.9" in query
            assert "LIMIT 5" in query


class TestExecuteRPC:
    """Test execute_rpc utility function"""

    @pytest.mark.asyncio
    async def test_execute_rpc_without_params(self, clean_database_manager, mock_settings):
        """Test RPC call without parameters"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.db_manager') as mock_manager:
                mock_row = {"result": "success"}

                mock_conn = AsyncMock()
                mock_conn.fetch = AsyncMock(return_value=[mock_row])

                mock_pool = AsyncMock()
                mock_pool.acquire = MagicMock(return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_conn),
                    __aexit__=AsyncMock()
                ))

                mock_manager._get_async_pool = AsyncMock(return_value=mock_pool)

                result = await execute_rpc("my_function")

                assert len(result) == 1
                assert result[0]["result"] == "success"

                # Verify query format
                call_args = mock_conn.fetch.call_args[0]
                query = call_args[0]
                assert "SELECT * FROM my_function()" in query

    @pytest.mark.asyncio
    async def test_execute_rpc_with_params(self, clean_database_manager, mock_settings):
        """Test RPC call with parameters"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.db_manager') as mock_manager:
                mock_conn = AsyncMock()
                mock_conn.fetch = AsyncMock(return_value=[])

                mock_pool = AsyncMock()
                mock_pool.acquire = MagicMock(return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_conn),
                    __aexit__=AsyncMock()
                ))

                mock_manager._get_async_pool = AsyncMock(return_value=mock_pool)

                params = {"id": 1, "name": "test"}
                await execute_rpc("my_function", params=params)

                # Verify query has placeholders
                call_args = mock_conn.fetch.call_args[0]
                query = call_args[0]
                assert "SELECT * FROM my_function(" in query
                assert "$1" in query

    @pytest.mark.asyncio
    async def test_execute_rpc_error(self, clean_database_manager, mock_settings):
        """Test RPC call error handling"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.db_manager') as mock_manager:
                # Make _get_async_pool raise the exception directly
                mock_manager._get_async_pool = AsyncMock(side_effect=Exception("RPC failed"))

                with pytest.raises(Exception) as exc_info:
                    await execute_rpc("my_function")

                assert "RPC failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_rpc_multiple_params(self, clean_database_manager, mock_settings):
        """Test RPC call with multiple parameters"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.db_manager') as mock_manager:
                mock_conn = AsyncMock()
                mock_conn.fetch = AsyncMock(return_value=[])

                mock_pool = AsyncMock()
                mock_pool.acquire = MagicMock(return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_conn),
                    __aexit__=AsyncMock()
                ))

                mock_manager._get_async_pool = AsyncMock(return_value=mock_pool)

                params = {"id": 1, "name": "test", "active": True}
                await execute_rpc("my_function", params=params)

                # Verify fetch was called (query + param values)
                mock_conn.fetch.assert_called_once()


class TestSupabaseClient:
    """Test legacy Supabase client function"""

    def test_get_supabase_client_returns_none(self):
        """Test that get_supabase_client returns None (deprecated)"""
        result = get_supabase_client()
        assert result is None

    def test_get_supabase_client_multiple_calls(self):
        """Test multiple calls to deprecated function"""
        result1 = get_supabase_client()
        result2 = get_supabase_client()
        assert result1 is None
        assert result2 is None


class TestGlobalDatabaseManager:
    """Test global db_manager instance"""

    def test_global_db_manager_is_singleton(self, clean_database_manager, mock_settings):
        """Test that global db_manager uses singleton pattern"""
        with patch('app.database.get_settings', return_value=mock_settings):
            # The global db_manager was created before our test fixture reset the singleton
            # So we test that any new DatabaseManager instance is the same singleton
            from app.database import DatabaseManager
            manager1 = DatabaseManager()
            manager2 = DatabaseManager()

            assert isinstance(manager1, DatabaseManager)
            assert isinstance(manager2, DatabaseManager)
            assert manager1 is manager2


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_connection_pool_with_invalid_settings(self, clean_database_manager):
        """Test connection pool creation with invalid settings"""
        invalid_settings = Mock()
        invalid_settings.zerodb_host = None
        invalid_settings.zerodb_port = None
        invalid_settings.zerodb_database = None
        invalid_settings.zerodb_user = None
        invalid_settings.zerodb_password = None
        invalid_settings.db_pool_size = 10

        with patch('app.database.get_settings', return_value=invalid_settings):
            with patch('app.database.pool.SimpleConnectionPool') as mock_pool_class:
                mock_pool_class.side_effect = TypeError("Invalid connection parameters")

                manager = DatabaseManager()
                with pytest.raises(TypeError):
                    manager._get_connection_pool()

    def test_engine_creation_with_special_characters_in_password(self, clean_database_manager, mock_settings):
        """Test engine creation with special characters in password"""
        mock_settings.zerodb_password = "p@ssw0rd!#$%"

        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.create_engine') as mock_create_engine:
                mock_engine = Mock()
                mock_create_engine.return_value = mock_engine

                manager = DatabaseManager()
                _ = manager.engine

                call_args = mock_create_engine.call_args[0]
                url = call_args[0]
                assert "p@ssw0rd!#$%" in url

    @pytest.mark.asyncio
    async def test_health_check_with_none_pool(self, clean_database_manager, mock_settings):
        """Test health check when pool creation returns None"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
                mock_create_pool.return_value = None

                manager = DatabaseManager()
                result = await manager.health_check()

                assert result["status"] == "unhealthy"

    def test_session_factory_uses_correct_engine(self, clean_database_manager, mock_settings):
        """Test that session factory binds to the correct engine"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.create_engine') as mock_create_engine:
                with patch('app.database.sessionmaker') as mock_sessionmaker:
                    mock_engine = Mock()
                    mock_engine.id = "test-engine-123"
                    mock_create_engine.return_value = mock_engine

                    manager = DatabaseManager()
                    _ = manager.session_factory

                    call_kwargs = mock_sessionmaker.call_args[1]
                    assert call_kwargs['bind'] is mock_engine
                    assert call_kwargs['bind'].id == "test-engine-123"

    @pytest.mark.asyncio
    async def test_concurrent_pool_access(self, clean_database_manager, mock_settings):
        """Test concurrent access to async pool"""
        with patch('app.database.get_settings', return_value=mock_settings):
            with patch('app.database.asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
                mock_pool = AsyncMock()
                mock_create_pool.return_value = mock_pool

                manager = DatabaseManager()

                # Simulate concurrent access
                results = await asyncio.gather(
                    manager._get_async_pool(),
                    manager._get_async_pool(),
                    manager._get_async_pool()
                )

                # All should return the same pool
                assert all(r is mock_pool for r in results)
                # Pool should only be created once
                assert mock_create_pool.call_count == 1
