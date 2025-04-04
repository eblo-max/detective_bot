from typing import List, Optional
import logging

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.news import News
from bot.database.repositories.base_repository import BaseRepository
from bot.database.repositories.user_repository import cache_result

logger = logging.getLogger(__name__)


class NewsRepository(BaseRepository[News]):
    """Репозиторий для работы с новостями."""

    def __init__(self, session: AsyncSession):
        """Инициализация репозитория."""
        super().__init__(session, News)

    @cache_result(ttl_seconds=300)
    async def create(self, title: str, description: str) -> News:
        """Создать новую новость."""
        try:
            news = News(title=title, description=description)

            async with self.session.begin():
                self.session.add(news)
                await self.session.commit()
                await self.session.refresh(news)

            logger.info(f"Создана новая новость: {news.title}")
            return news

        except Exception as e:
            logger.error(f"Ошибка при создании новости: {e}")
            raise

    @cache_result(ttl_seconds=300)
    async def get_latest(self, limit: int = 5) -> List[News]:
        """Получить последние новости."""
        try:
            query = (
                select(News)
                .where(News.is_active == True)
                .order_by(desc(News.created_at))
                .limit(limit)
            )
            result = await self.session.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Ошибка при получении последних новостей: {e}")
            raise

    @cache_result(ttl_seconds=300)
    async def get_by_id(self, news_id: int) -> Optional[News]:
        """Получить новость по ID."""
        try:
            query = select(News).where(News.id == news_id)
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Ошибка при получении новости по ID: {e}")
            raise

    @cache_result(ttl_seconds=300)
    async def deactivate(self, news_id: int) -> Optional[News]:
        """Деактивировать новость."""
        try:
            news = await self.get_by_id(news_id)
            if not news:
                return None

            async with self.session.begin():
                news.is_active = False
                await self.session.commit()
                await self.session.refresh(news)

            logger.info(f"Деактивирована новость: {news.title}")
            return news

        except Exception as e:
            logger.error(f"Ошибка при деактивации новости: {e}")
            raise

    @cache_result(ttl_seconds=300)
    async def get_news_by_id(self, news_id: str) -> Optional[News]:
        """Получить новость по ID."""
        try:
            query = select(News).where(News.id == news_id)
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Ошибка при получении новости по ID: {e}")
            raise
