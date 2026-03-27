from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, mapped_column
from sqlalchemy import BIGINT, Identity
from typing import Annotated

from app.core.config import settings

# async engine
async_engine = create_async_engine(
    url=settings.DATABASE_URL_asyncpg,
    echo=(settings.ENVIRONMENT == "dev"), # logs for dev enviroment
    max_overflow=10,
    hide_parameters=True
) 

# Session factory
async_session_factory = async_sessionmaker(
    async_engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass
 
# DRY dependency for FastApi
async def get_db():    
    async with async_session_factory() as session:
        yield session
    
# Custom shortcut for models
bigint_pk = Annotated[int, mapped_column(BIGINT, Identity(always=True), primary_key=True)]