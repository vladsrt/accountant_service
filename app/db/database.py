from typing import Annotated

from sqlalchemy import BIGINT, Identity
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, mapped_column
from sqlalchemy.pool import NullPool

from app.core.config import settings

# async engine
async_engine = create_async_engine(
    url=settings.DATABASE_URL_asyncpg,
    echo=(settings.ENVIRONMENT == "dev"),  # logs for dev enviroment
    max_overflow=10,
    hide_parameters=True,
)


def create_worker_engine() -> AsyncEngine:
    """Create a poolless async engine for Celery workers.

    Each call to asyncio.run() in a Celery task creates and destroys an event
    loop. A shared connection pool would bind connections to the dead loop,
    causing RuntimeError on the next task. NullPool disables pooling entirely
    so every task gets fresh connections that are closed on engine.dispose().
    """
    return create_async_engine(
        url=settings.DATABASE_URL_asyncpg,
        echo=False,
        hide_parameters=True,
        poolclass=NullPool,
    )


# Session factory
async_session_factory = async_sessionmaker(
    async_engine, autoflush=False, autocommit=False, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


# DRY dependency for FastApi
async def get_db():
    async with async_session_factory() as session:
        yield session


# Custom shortcut for models
bigint_pk = Annotated[int, mapped_column(BIGINT, Identity(always=True), primary_key=True)]
