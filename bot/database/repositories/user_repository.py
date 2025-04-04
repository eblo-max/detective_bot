import logging
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.database.models.achievement import Achievement, UserAchievement
from bot.database.models.case import Case, UserCase
from bot.database.models.energy import Energy
from bot.database.models.inventory import Inventory
from bot.database.models.relationship import Relationship, RelationshipStatus
from bot.database.models.reputation import Reputation
from bot.database.models.skill import Skill, UserSkill, SkillType
from bot.database.models.user import User, UserStats, UserStatus
from bot.database.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


def cache_result(ttl_seconds: int = 300):
    """Декоратор для кэширования результатов методов."""

    def decorator(func):
        cache = {}

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Создаем ключ кэша из имени функции и аргументов
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            # Проверяем наличие данных в кэше
            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if datetime.now() - timestamp < timedelta(seconds=ttl_seconds):
                    return result
                else:
                    # Удаляем устаревшие данные
                    del cache[cache_key]

            # Выполняем метод и сохраняем результат
            result = await func(*args, **kwargs)
            cache[cache_key] = (result, datetime.now())

            return result

        # Добавляем метод для инвалидации кэша
        wrapper.invalidate_cache = lambda: cache.clear()

        return wrapper

    return decorator


class UserRepository(BaseRepository[User]):
    """Репозиторий для работы с пользователями."""

    def __init__(self, session: AsyncSession):
        """Инициализация репозитория."""
        super().__init__(session, User)
        self._cache = {}
        self._cache_timestamps = {}

    @cache_result(ttl_seconds=300)
    async def create_user(
        self,
        telegram_id: int,
        username: str = None,
        first_name: str = None,
        last_name: str = None,
    ) -> User:
        """Создает нового пользователя"""
        try:
            created_at = datetime.now(timezone.utc)

            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                created_at=created_at,
                status=UserStatus.ACTIVE,
            )

            user_stats = UserStats(
                user_id=user.id,
                level=1,
                experience=0,
                solved_cases=0,
                perfect_cases=0,
                failed_cases=0,
                total_reward=0,
            )

            # Создаем базовые навыки
            observation_skill = UserSkill(
                user_id=user.id,
                skill_id=SkillType.OBSERVATION.value,
                level=1,
                experience=0,
            )
            deduction_skill = UserSkill(
                user_id=user.id,
                skill_id=SkillType.DEDUCTION.value,
                level=1,
                experience=0,
            )
            interrogation_skill = UserSkill(
                user_id=user.id,
                skill_id=SkillType.INTERROGATION.value,
                level=1,
                experience=0,
            )

            async with self.session.begin():
                self.session.add(user)
                self.session.add(user_stats)
                self.session.add(observation_skill)
                self.session.add(deduction_skill)
                self.session.add(interrogation_skill)
                await self.session.commit()
                await self.session.refresh(user)

            logger.info(f"Создан новый пользователь: {user.telegram_id}")
            return user

        except Exception as e:
            logger.error(f"Ошибка при создании пользователя: {e}")
            raise

    @cache_result(ttl_seconds=300)
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Получает пользователя по Telegram ID."""
        try:
            query = select(User).where(User.telegram_id == telegram_id)
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя по Telegram ID: {e}")
            raise

    @cache_result(ttl_seconds=300)
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Получает пользователя по ID."""
        try:
            query = select(User).where(User.id == user_id)
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя по ID: {e}")
            raise

    @cache_result(ttl_seconds=300)
    async def update_user_status(
        self, user_id: int, status: UserStatus
    ) -> Optional[User]:
        """Обновляет статус пользователя."""
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return None

            async with self.session.begin():
                user.status = status
                await self.session.commit()
                await self.session.refresh(user)

            logger.info(f"Обновлен статус пользователя {user_id} на {status}")
            return user

        except Exception as e:
            logger.error(f"Ошибка при обновлении статуса пользователя: {e}")
            raise

    @cache_result(ttl_seconds=300)
    async def update_user_energy(
        self, user_id: int, energy_change: int
    ) -> Optional[User]:
        """Обновляет энергию пользователя."""
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return None

            async with self.session.begin():
                # Обновляем энергию
                user.energy.current = max(
                    0, min(user.energy.max_energy, user.energy.current + energy_change)
                )
                user.energy.last_update = datetime.now(timezone.utc)
                await self.session.commit()
                await self.session.refresh(user)

            return user

        except Exception as e:
            logger.error(f"Ошибка при обновлении энергии пользователя: {e}")
            raise

    async def add_achievement(
        self, user_id: int, achievement_id: str, progress: Optional[int] = None
    ) -> Optional[User]:
        """Добавляет достижение пользователю."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None

        # Проверяем, есть ли уже такое достижение
        existing_achievement = next(
            (a for a in user.achievements if a.achievement_id == achievement_id), None
        )

        if existing_achievement:
            if progress is not None:
                existing_achievement.progress = progress
        else:
            user.achievements.append(
                UserAchievement(
                    user_id=user_id,
                    achievement_id=achievement_id,
                    unlocked_at=datetime.now(timezone.utc),
                )
            )

        await self.session.commit()
        await self.session.refresh(user)

        # Инвалидируем кэш
        self.invalidate_cache()

        logger.info(f"Добавлено достижение {achievement_id} пользователю {user_id}")
        return user

    async def update_skill(
        self, user_id: int, skill_name: str, experience: int
    ) -> Optional[User]:
        """Обновляет навык пользователя."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None

        skill = next((s for s in user.skills if s.skill.name == skill_name), None)
        if not skill:
            return None

        skill.add_experience(experience)
        await self.session.commit()
        await self.session.refresh(user)

        # Инвалидируем кэш
        self.invalidate_cache()

        logger.info(
            f"Обновлен навык {skill_name} пользователя {user_id}: +{experience}"
        )
        return user

    def invalidate_cache(self) -> None:
        """Очищает кэш."""
        self._cache.clear()
        self._cache_timestamps.clear()

    async def get_top_players(self, limit: int = 10) -> List[User]:
        """Получает топ игроков."""
        query = (
            select(User)
            .join(UserStats)
            .order_by(desc(UserStats.experience))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_user_statistics(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает полную статистику пользователя."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None

        return {
            "level": user.stats.level,
            "experience": user.stats.experience,
            "solved_cases": user.stats.solved_cases,
            "perfect_cases": user.stats.perfect_cases,
            "failed_cases": user.stats.failed_cases,
            "total_reward": user.stats.total_reward,
            "energy": {
                "current": user.energy.current,
                "max": user.energy.max_energy,
            },
            "reputation": {
                "level": user.reputation.level,
                "points": user.reputation.points,
                "rank": user.reputation.rank,
            },
            "skills": [
                {
                    "name": skill.skill.name,
                    "level": skill.level,
                    "experience": skill.experience,
                }
                for skill in user.skills
            ],
            "achievements": [
                {
                    "id": achievement.achievement_id,
                    "name": achievement.name,
                    "description": achievement.description,
                    "unlocked_at": (
                        achievement.unlocked_at.isoformat()
                        if achievement.unlocked_at
                        else None
                    ),
                }
                for achievement in user.achievements
            ],
        }

    async def get_user_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Алиас для get_user_statistics для обратной совместимости."""
        return await self.get_user_statistics(user_id)

    async def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получает таблицу лидеров."""
        query = (
            select(User)
            .join(UserStats)
            .order_by(desc(UserStats.experience))
            .limit(limit)
        )
        result = await self.session.execute(query)
        users = result.scalars().all()

        return [
            {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "level": user.stats.level,
                "experience": user.stats.experience,
                "solved_cases": user.stats.solved_cases,
                "perfect_cases": user.stats.perfect_cases,
                "total_reward": user.stats.total_reward,
                "rank": user.reputation.rank,
            }
            for user in users
        ]

    async def get_user_achievements(self, user_id: int) -> List[UserAchievement]:
        """Получает достижения пользователя."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return []
        return user.achievements

    async def add_case(self, user_id: int, case_id: int) -> Optional[UserCase]:
        """Добавляет дело пользователю."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None

        case = await self.session.get(Case, case_id)
        if not case:
            return None

        user_case = UserCase(
            user_id=user_id,
            case_id=case_id,
            status="not_started",
            created_at=datetime.now(timezone.utc),
        )

        self.session.add(user_case)
        await self.session.commit()
        await self.session.refresh(user_case)

        return user_case

    async def complete_case(self, user_id: int, case_id: int) -> Optional[UserCase]:
        """Завершает дело пользователя."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None

        case = await self.session.get(Case, case_id)
        if not case:
            return None

        user_case = next((uc for uc in user.cases if uc.case_id == case_id), None)
        if not user_case:
            return None

        user_case.status = "completed"
        user_case.completed_at = datetime.now(timezone.utc)

        # Обновляем статистику
        user.stats.solved_cases += 1
        user.stats.total_reward += case.reward

        await self.session.commit()
        await self.session.refresh(user_case)

        return user_case

    async def search_users(
        self, query: str, limit: int = 10, min_level: Optional[int] = None
    ) -> List[User]:
        """Поиск пользователей."""
        conditions = [
            or_(
                User.username.ilike(f"%{query}%"),
                User.first_name.ilike(f"%{query}%"),
            )
        ]

        if min_level is not None:
            conditions.append(UserStats.level >= min_level)

        query = select(User).join(UserStats).where(and_(*conditions)).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_users_by_achievement(
        self, achievement_id: str, limit: int = 10
    ) -> List[User]:
        """Получает пользователей с определенным достижением."""
        query = (
            select(User)
            .join(UserAchievement)
            .where(UserAchievement.achievement_id == achievement_id)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_users_by_skill_level(
        self, skill_name: str, min_level: int, limit: int = 10
    ) -> List[User]:
        """Получает пользователей с определенным уровнем навыка."""
        query = (
            select(User)
            .join(UserSkill)
            .join(Skill)
            .where(
                and_(
                    Skill.name == skill_name,
                    UserSkill.level >= min_level,
                )
            )
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
