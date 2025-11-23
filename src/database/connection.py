"""
Database connection management for API Key Management Service.

Provides async and sync database engines and sessions with connection pooling.
"""

from typing import AsyncGenerator, Generator, Optional
from contextlib import asynccontextmanager, contextmanager

from sqlalchemy import create_engine, Engine, text
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from src.config import get_settings
from src.logging_config import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Global engine instances
_async_engine: Optional[AsyncEngine] = None
_sync_engine: Optional[Engine] = None


def get_database_url(async_mode: bool = True) -> str:
    """
    Get database URL with appropriate driver.

    Args:
        async_mode: If True, returns asyncpg URL; otherwise psycopg2 URL

    Returns:
        Database connection URL
    """
    import re

    db_url = settings.database_url

    if not db_url:
        raise ValueError("DATABASE_URL not configured in environment")

    # Convert postgresql:// to postgresql+asyncpg:// for async
    # or postgresql+psycopg2:// for sync
    if async_mode:
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif not db_url.startswith("postgresql+asyncpg://"):
            logger.warning(
                f"Database URL doesn't start with postgresql://: {db_url[:20]}..."
            )

        # asyncpg doesn't support sslmode parameter in URL, remove it
        # SSL will be handled via connect_args
        if "?sslmode=" in db_url or "&sslmode=" in db_url:
            db_url = re.sub(r"[?&]sslmode=[^&]*", "", db_url)
            # Clean up any leftover ? or & at the end
            db_url = db_url.rstrip("?&")
    else:
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        elif not db_url.startswith("postgresql+psycopg2://"):
            logger.warning(
                f"Database URL doesn't start with postgresql://: {db_url[:20]}..."
            )

    return db_url


def get_engine(force_new: bool = False) -> Engine:
    """
    Get or create synchronous SQLAlchemy engine.

    Args:
        force_new: Force creation of a new engine

    Returns:
        SQLAlchemy Engine instance
    """
    global _sync_engine

    if _sync_engine is None or force_new:
        db_url = get_database_url(async_mode=False)

        # Connection pool settings
        pool_size = settings.db_pool_size if hasattr(settings, "db_pool_size") else 10
        max_overflow = (
            settings.db_max_overflow if hasattr(settings, "db_max_overflow") else 20
        )
        pool_timeout = (
            settings.db_pool_timeout if hasattr(settings, "db_pool_timeout") else 30
        )

        _sync_engine = create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_pre_ping=True,  # Verify connections before using
            echo=False,  # Set to True for SQL debugging
        )

        logger.info(f"Synchronous database engine created (pool_size={pool_size})")

    return _sync_engine


def get_async_engine(force_new: bool = False) -> AsyncEngine:
    """
    Get or create asynchronous SQLAlchemy engine.

    Args:
        force_new: Force creation of a new engine

    Returns:
        AsyncEngine instance
    """
    global _async_engine

    if _async_engine is None or force_new:
        db_url = get_database_url(async_mode=True)

        # For async engines with asyncpg, use connect_args for SSL
        connect_args = {}
        if "neon.tech" in db_url or "postgres" in db_url:
            # asyncpg SSL configuration
            connect_args["ssl"] = "require"

        # Use NullPool for async to avoid pool issues
        #         #         from sqlalchemy.pool import NullPool

        _async_engine = create_async_engine(
            db_url,
            poolclass=NullPool,  # NullPool for async
            connect_args=connect_args,
            echo=False,  # Set to True for SQL debugging
        )

        logger.info("Asynchronous database engine created with NullPool")

    return _async_engine


# Session factories
_async_session_factory: Optional[async_sessionmaker] = None
_sync_session_factory: Optional[sessionmaker] = None


def get_session_factory() -> sessionmaker:
    """Get or create synchronous session factory."""
    global _sync_session_factory

    if _sync_session_factory is None:
        engine = get_engine()
        _sync_session_factory = sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

    return _sync_session_factory


def get_async_session_factory() -> async_sessionmaker:
    """Get or create asynchronous session factory."""
    global _async_session_factory

    if _async_session_factory is None:
        engine = get_async_engine()
        _async_session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

    return _async_session_factory


@contextmanager
def get_sync_session() -> Generator[Session, None, None]:
    """
    Context manager for synchronous database session.

    Usage:
        with get_sync_session() as session:
            # Use session
            session.query(AKMAPIKey).all()
    """
    factory = get_session_factory()
    session = factory()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for asynchronous database session.

    This function is used as a FastAPI dependency and can be overridden in tests.

    Usage:
        @app.get("/endpoint")
        async def endpoint(session: AsyncSession = Depends(get_session)):
            # Use session
            result = await session.execute(select(AKMAPIKey))
    """
    factory = get_async_session_factory()
    session = factory()

    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for asynchronous database session.

    Usage:
        async with get_async_session() as session:
            # Use session
            result = await session.execute(select(AKMAPIKey))
    """
    factory = get_async_session_factory()
    session = factory()

    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def close_database_connections():
    """
    Close all database connections and dispose of engines.

    Should be called on application shutdown.
    """
    global _async_engine, _sync_engine

    if _async_engine:
        await _async_engine.dispose()
        _async_engine = None
        logger.info("Async database engine disposed")

    if _sync_engine:
        _sync_engine.dispose()
        _sync_engine = None
        logger.info("Sync database engine disposed")


async def check_database_connection() -> bool:
    """
    Check if database is accessible.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        async with get_async_session() as session:
            # Simple query to test connection
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False
