import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncEngine,
)
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

logger = logging.getLogger("shorts_api.database")


class Base(DeclarativeBase):
    """Base model class for all SQLAlchemy declarative models."""
    pass


def get_engine() -> AsyncEngine:
    """Creates the async engine based on configuration."""
    db_url = settings.DATABASE_URL
    # For SQLite async compatibility during tests or fallback
    connect_args = {}
    if "sqlite" in db_url:
        connect_args = {"check_same_thread": False}

    return create_async_engine(
        db_url,
        echo=settings.DEBUG,
        future=True,
        connect_args=connect_args,
    )


engine: AsyncEngine = get_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding an async database session.
    Automatically handles commit and rollback on exceptions.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as exc:
            await session.rollback()
            logger.error(f"Database session rolled back due to error: {exc}")
            raise
        finally:
            await session.close()
