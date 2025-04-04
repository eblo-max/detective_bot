from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import logging

from sqlalchemy import select, and_, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.case import Case, CaseStatus, UserCase
from bot.database.repositories.base_repository import BaseRepository
from bot.database.repositories.user_repository import cache_result

logger = logging.getLogger(__name__)


class CaseRepository(BaseRepository[Case]):
    """Репозиторий для работы с делами."""

    def __init__(self, session: AsyncSession):
        """Инициализация репозитория."""
        super().__init__(session, Case)

    @cache_result(ttl_seconds=300)
    async def get_active_cases(self) -> List[Case]:
        """Получить все активные дела."""
        try:
            query = select(Case).where(Case.status == CaseStatus.ACTIVE)
            result = await self.session.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Ошибка при получении активных дел: {e}")
            raise

    @cache_result(ttl_seconds=300)
    async def get_case_by_id(self, case_id: int) -> Optional[Case]:
        """Получить дело по ID."""
        try:
            query = select(Case).where(Case.id == case_id)
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Ошибка при получении дела по ID: {e}")
            raise

    @cache_result(ttl_seconds=300)
    async def create_case(
        self,
        title: str,
        description: str,
        difficulty: int,
        reward: int,
        evidence: Optional[Dict[str, Any]] = None,
        suspects: Optional[List[Dict[str, Any]]] = None,
    ) -> Case:
        """Создать новое дело."""
        try:
            case = Case(
                title=title,
                description=description,
                difficulty=difficulty,
                reward=reward,
                status=CaseStatus.ACTIVE,
                evidence=evidence or {},
                suspects=suspects or [],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            async with self.session.begin():
                self.session.add(case)
                await self.session.commit()
                await self.session.refresh(case)

            logger.info(f"Создано новое дело: {case.title}")
            return case

        except Exception as e:
            logger.error(f"Ошибка при создании дела: {e}")
            raise

    @cache_result(ttl_seconds=300)
    async def update_case_status(
        self, case_id: int, status: CaseStatus
    ) -> Optional[Case]:
        """Обновить статус дела."""
        try:
            case = await self.get_case_by_id(case_id)
            if not case:
                return None

            async with self.session.begin():
                case.status = status
                case.updated_at = datetime.now(timezone.utc)
                await self.session.commit()
                await self.session.refresh(case)

            logger.info(f"Обновлен статус дела {case_id} на {status}")
            return case

        except Exception as e:
            logger.error(f"Ошибка при обновлении статуса дела: {e}")
            raise

    @cache_result(ttl_seconds=300)
    async def add_evidence(
        self, case_id: int, evidence: Dict[str, Any]
    ) -> Optional[Case]:
        """Добавить улику в дело."""
        try:
            case = await self.get_case_by_id(case_id)
            if not case:
                return None

            async with self.session.begin():
                case.add_evidence(evidence)
                case.updated_at = datetime.now(timezone.utc)
                await self.session.commit()
                await self.session.refresh(case)

            logger.info(f"Добавлена улика в дело {case_id}")
            return case

        except Exception as e:
            logger.error(f"Ошибка при добавлении улики: {e}")
            raise

    @cache_result(ttl_seconds=300)
    async def add_suspect(
        self, case_id: int, suspect: Dict[str, Any]
    ) -> Optional[Case]:
        """Добавить подозреваемого в дело."""
        try:
            case = await self.get_case_by_id(case_id)
            if not case:
                return None

            async with self.session.begin():
                case.add_suspect(suspect)
                case.updated_at = datetime.now(timezone.utc)
                await self.session.commit()
                await self.session.refresh(case)

            logger.info(f"Добавлен подозреваемый в дело {case_id}")
            return case

        except Exception as e:
            logger.error(f"Ошибка при добавлении подозреваемого: {e}")
            raise

    @cache_result(ttl_seconds=300)
    async def get_user_cases(self, user_id: int) -> List[UserCase]:
        """Получить дела пользователя."""
        try:
            query = select(UserCase).where(UserCase.user_id == user_id)
            result = await self.session.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Ошибка при получении дел пользователя: {e}")
            raise

    @cache_result(ttl_seconds=300)
    async def get_user_case(self, user_id: int, case_id: int) -> Optional[UserCase]:
        """Получить дело пользователя по ID."""
        try:
            query = select(UserCase).where(
                and_(UserCase.user_id == user_id, UserCase.case_id == case_id)
            )
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Ошибка при получении дела пользователя: {e}")
            raise

    @cache_result(ttl_seconds=300)
    async def get_top_cases(self, limit: int = 10) -> List[Case]:
        """Получить топ дел по сложности."""
        try:
            query = select(Case).order_by(desc(Case.difficulty)).limit(limit)
            result = await self.session.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Ошибка при получении топ дел: {e}")
            raise

    @cache_result(ttl_seconds=300)
    async def search_cases(
        self,
        query: str,
        difficulty: Optional[int] = None,
        status: Optional[CaseStatus] = None,
        limit: int = 10,
    ) -> List[Case]:
        """Поиск дел."""
        try:
            conditions = [
                or_(
                    Case.title.ilike(f"%{query}%"),
                    Case.description.ilike(f"%{query}%"),
                )
            ]

            if difficulty is not None:
                conditions.append(Case.difficulty == difficulty)
            if status is not None:
                conditions.append(Case.status == status)

            query = select(Case).where(and_(*conditions)).limit(limit)
            result = await self.session.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Ошибка при поиске дел: {e}")
            raise
