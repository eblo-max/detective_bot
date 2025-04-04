from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from sqlalchemy import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.achievement import Achievement, UserAchievement
from bot.database.repositories.base_repository import BaseRepository


class AchievementRepository(BaseRepository[Achievement]):
    """Репозиторий для работы с достижениями."""

    def __init__(self, session: AsyncSession):
        """Инициализация репозитория."""
        super().__init__(session, Achievement)

    async def get_achievement_by_id(self, achievement_id: str) -> Optional[Achievement]:
        """Получить достижение по ID."""
        query = select(Achievement).where(Achievement.id == achievement_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_achievement(
        self,
        id: str,
        name: str,
        description: str,
        category: str,
        requirements: Optional[Dict[str, Any]] = None,
        reward: Optional[Dict[str, Any]] = None,
    ) -> Achievement:
        """Создать новое достижение."""
        achievement = Achievement(
            id=id,
            name=name,
            description=description,
            category=category,
            requirements=requirements or {},
            reward=reward or {},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.session.add(achievement)
        await self.session.commit()
        await self.session.refresh(achievement)
        return achievement

    async def get_user_achievements(self, user_id: int) -> List[UserAchievement]:
        """Получить достижения пользователя."""
        query = select(UserAchievement).where(UserAchievement.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_user_achievement(
        self, user_id: int, achievement_id: str
    ) -> Optional[UserAchievement]:
        """Получить достижение пользователя по ID."""
        query = select(UserAchievement).where(
            and_(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement_id,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def unlock_achievement(
        self, user_id: int, achievement_id: str
    ) -> Optional[UserAchievement]:
        """Разблокировать достижение пользователя."""
        achievement = await self.get_achievement_by_id(achievement_id)
        if not achievement:
            return None

        user_achievement = UserAchievement(
            user_id=user_id,
            achievement_id=achievement_id,
            unlocked_at=datetime.now(timezone.utc),
        )
        self.session.add(user_achievement)
        await self.session.commit()
        await self.session.refresh(user_achievement)
        return user_achievement

    async def get_achievements_by_category(self, category: str) -> List[Achievement]:
        """Получить достижения по категории."""
        query = select(Achievement).where(Achievement.category == category)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_top_achievements(self, limit: int = 10) -> List[Achievement]:
        """Получить топ достижений по количеству разблокировок."""
        query = (
            select(Achievement)
            .join(UserAchievement)
            .group_by(Achievement.id)
            .order_by(desc(UserAchievement.id))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def search_achievements(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> List[Achievement]:
        """Поиск достижений."""
        conditions = [
            or_(
                Achievement.name.ilike(f"%{query}%"),
                Achievement.description.ilike(f"%{query}%"),
            )
        ]

        if category is not None:
            conditions.append(Achievement.category == category)

        query = select(Achievement).where(and_(*conditions)).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_achievement_progress(
        self, user_id: int, achievement_id: str
    ) -> Optional[Dict[str, Any]]:
        """Получить прогресс достижения пользователя."""
        achievement = await self.get_achievement_by_id(achievement_id)
        if not achievement:
            return None

        user_achievement = await self.get_user_achievement(user_id, achievement_id)
        if not user_achievement:
            return {
                "achievement": achievement.to_dict(),
                "progress": 0,
                "is_unlocked": False,
            }

        return {
            "achievement": achievement.to_dict(),
            "progress": user_achievement.progress,
            "is_unlocked": True,
            "unlocked_at": user_achievement.unlocked_at.isoformat(),
        }
