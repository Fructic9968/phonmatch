"""Асинхронное подключение к PostgreSQL и управление сессиями."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import Settings
from db.models import Base

settings = Settings()
engine = create_async_engine(settings.DATABASE_URL)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Открыть сессию; вызывающий код управляет транзакцией."""
    async with async_session_factory() as session:
        yield session


async def init_db() -> None:
    """Создать отсутствующие таблицы; изменения схемы выполняются через Alembic."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
