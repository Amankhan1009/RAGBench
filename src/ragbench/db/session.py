"""Event-loop aware Async SQLAlchemy engine and session factory for Neon PostgreSQL."""
import asyncio
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ragbench.core.config import settings
from ragbench.core.logging import logger

_engine_loop_pair: tuple[AsyncEngine, asyncio.AbstractEventLoop] | None = None


def get_engine() -> AsyncEngine:
    """Retrieve or create an AsyncEngine bound strictly to the current running event loop."""
    global _engine_loop_pair
    current_loop = asyncio.get_running_loop()

    if _engine_loop_pair is not None:
        engine, loop = _engine_loop_pair
        if loop is current_loop:
            return engine

    db_url = settings.async_database_url
    is_postgres = db_url.startswith("postgresql")

    engine_kwargs = {
        "echo": (settings.ENVIRONMENT == "development"),
    }

    if is_postgres:
        engine_kwargs.update({
            "pool_pre_ping": True,
            "pool_recycle": 300,
            "pool_size": 10,
            "max_overflow": 20,
        })

    new_engine = create_async_engine(db_url, **engine_kwargs)
    _engine_loop_pair = (new_engine, current_loop)
    return new_engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Retrieve an async sessionmaker bound to the loop's engine."""
    return async_sessionmaker(
        bind=get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as exc:
            await session.rollback()
            logger.error(f"Database session error: {exc}")
            raise
        finally:
            await session.close()
