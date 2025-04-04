"""Модуль для работы с базой данных."""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import configure_mappers

from bot.core.config import config
from bot.database.models.base import Base
from bot.database.models.user import User, UserStats
from bot.database.models.achievement import Achievement, UserAchievement
from bot.database.models.relationship import Relationship
from bot.database.models.investigation import Investigation
from bot.database.models.case import Case, UserCase
from bot.database.models.resources import Energy, Inventory, Reputation
from bot.database.models.news import News
from bot.database.models.skill import Skill, UserSkill

# Создаем движок базы данных
engine = create_async_engine(
    config.DATABASE_URL,
    echo=False,
)

# Создаем фабрику сессий
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Для обратной совместимости
SessionLocal = async_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Получение сессии базы данных"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Инициализация базы данных"""
    # Конфигурируем все мапперы
    configure_mappers()

    async with engine.begin() as conn:
        # Удаляем существующие таблицы
        await conn.run_sync(Base.metadata.drop_all)

        # Создаем таблицы заново
        await conn.run_sync(Base.metadata.create_all)

    print("База данных успешно инициализирована")


async def create_tables() -> None:
    """Создание всех таблиц"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
