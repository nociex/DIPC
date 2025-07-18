"""Database connection and configuration utilities."""

import logging
import time
from typing import Generator, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager, asynccontextmanager

from ..config import settings

logger = logging.getLogger(__name__)

# Create async SQLAlchemy engine with connection pooling
async_engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.environment == "development",
)

# Create sync SQLAlchemy engine for migrations and admin tasks
sync_engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.environment == "development",
)

# Create async SessionLocal class
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Create sync SessionLocal class for migrations
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# Create Base class for models
Base = declarative_base()


async def get_db_session():
    """
    Async dependency to get database session for FastAPI.
    
    Yields:
        AsyncSession: SQLAlchemy async database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_db() -> Generator[Session, None, None]:
    """
    Sync dependency to get database session.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def get_async_db_session():
    """
    Async context manager for database sessions.
    
    Yields:
        AsyncSession: SQLAlchemy async database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@contextmanager
def get_sync_db_session():
    """
    Sync context manager for database sessions.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database by creating all tables.
    
    This function should be called on application startup.
    """
    try:
        # Import all models to ensure they are registered with Base
        from . import models  # noqa: F401
        
        # Create all tables
        Base.metadata.create_all(bind=sync_engine)
        logger.info("Database tables created successfully")
        
    except SQLAlchemyError as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def get_database_health() -> Dict[str, Any]:
    """
    Async database health check for FastAPI.
    
    Returns:
        Dict[str, Any]: Health check results with status and details
    """
    start_time = time.time()
    health_status = {
        "healthy": False,
        "database": "postgresql",
        "response_time": 0.0,
        "connection_pool": {},
        "error": None
    }
    
    try:
        async with AsyncSessionLocal() as session:
            # Test basic connectivity
            result = await session.execute(text("SELECT 1 as health_check"))
            row = result.fetchone()
            if row and row[0] == 1:
                health_status["healthy"] = True
            
            # Get connection pool information
            pool = async_engine.pool
            health_status["connection_pool"] = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalid()
            }
            
            # Test database version
            version_result = await session.execute(text("SELECT version()"))
            version_row = version_result.fetchone()
            if version_row:
                health_status["version"] = version_row[0]
            
    except SQLAlchemyError as e:
        health_status["error"] = str(e)
        logger.error(f"Database health check failed: {e}")
    except Exception as e:
        health_status["error"] = f"Unexpected error: {str(e)}"
        logger.error(f"Unexpected error during database health check: {e}")
    
    health_status["response_time"] = time.time() - start_time
    return health_status


def check_db_health() -> dict:
    """
    Check database health and connectivity.
    
    Returns:
        dict: Health check results with status and details
    """
    health_status = {
        "status": "unhealthy",
        "database": "postgresql",
        "connection_pool": {},
        "error": None
    }
    
    try:
        with SessionLocal() as db:
            # Test basic connectivity
            result = db.execute(text("SELECT 1 as health_check"))
            if result.fetchone()[0] == 1:
                health_status["status"] = "healthy"
            
            # Get connection pool information
            pool = sync_engine.pool
            health_status["connection_pool"] = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalid()
            }
            
            # Test database version
            version_result = db.execute(text("SELECT version()"))
            health_status["version"] = version_result.fetchone()[0]
            
    except SQLAlchemyError as e:
        health_status["error"] = str(e)
        logger.error(f"Database health check failed: {e}")
    except Exception as e:
        health_status["error"] = f"Unexpected error: {str(e)}"
        logger.error(f"Unexpected error during database health check: {e}")
    
    return health_status


def get_db_stats() -> dict:
    """
    Get database statistics and metrics.
    
    Returns:
        dict: Database statistics
    """
    stats = {
        "tables": {},
        "connection_info": {},
        "error": None
    }
    
    try:
        with SessionLocal() as db:
            # Get table row counts
            table_stats_query = text("""
                SELECT 
                    schemaname,
                    tablename,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes,
                    n_live_tup as live_rows,
                    n_dead_tup as dead_rows
                FROM pg_stat_user_tables
                WHERE schemaname = 'public'
            """)
            
            result = db.execute(table_stats_query)
            for row in result:
                stats["tables"][row.tablename] = {
                    "inserts": row.inserts,
                    "updates": row.updates,
                    "deletes": row.deletes,
                    "live_rows": row.live_rows,
                    "dead_rows": row.dead_rows
                }
            
            # Get connection information
            connection_info_query = text("""
                SELECT 
                    count(*) as total_connections,
                    count(*) FILTER (WHERE state = 'active') as active_connections,
                    count(*) FILTER (WHERE state = 'idle') as idle_connections
                FROM pg_stat_activity
                WHERE datname = current_database()
            """)
            
            result = db.execute(connection_info_query)
            row = result.fetchone()
            stats["connection_info"] = {
                "total_connections": row.total_connections,
                "active_connections": row.active_connections,
                "idle_connections": row.idle_connections
            }
            
    except SQLAlchemyError as e:
        stats["error"] = str(e)
        logger.error(f"Failed to get database stats: {e}")
    except Exception as e:
        stats["error"] = f"Unexpected error: {str(e)}"
        logger.error(f"Unexpected error getting database stats: {e}")
    
    return stats


async def close_db_connections():
    """
    Close all database connections.
    
    This should be called on application shutdown.
    """
    try:
        await async_engine.dispose()
        sync_engine.dispose()
        logger.info("Database connections closed successfully")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")


# Database transaction utilities
@contextmanager
def db_transaction():
    """
    Context manager for database transactions with automatic rollback on error.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database transaction rolled back due to error: {e}")
        raise
    finally:
        db.close()


def execute_raw_sql(query: str, params: dict = None) -> list:
    """
    Execute raw SQL query safely.
    
    Args:
        query: SQL query string
        params: Query parameters
        
    Returns:
        list: Query results
    """
    try:
        with SessionLocal() as db:
            result = db.execute(text(query), params or {})
            return result.fetchall()
    except SQLAlchemyError as e:
        logger.error(f"Failed to execute raw SQL: {e}")
        raise